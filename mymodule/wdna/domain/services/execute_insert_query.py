# mymodule/wdna/domain/services/clickhouse_incremental_insert_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

import re

import clickhouse_connect


@dataclass(frozen=True)
class ClickHouseConnConfig:
    host: str = "localhost"
    port: int = 8123  # HTTP (clickhouse-connect usa HTTP)
    username: str = "default"
    password: str = ""
    database: str = "default"
    secure: bool = False
    # timeouts
    connect_timeout: int = 10
    send_receive_timeout: int = 300


@dataclass(frozen=True)
class IncrementalInsertConfig:
    # Columna "fecha" en la tabla destino (primero prueba timestamp; si no existe, date)
    preferred_time_columns: Tuple[str, ...] = ("timestamp", "date")
    # Si la tabla está vacía (MAX = NULL), ¿insertar todo?
    insert_all_if_empty: bool = True


@dataclass(frozen=True)
class InsertExecutionResult:
    table: str
    used_time_column: Optional[str]
    last_value: Optional[str]
    injected_where: bool
    executed: bool
    error: Optional[str] = None


class ClickHouseIncrementalInsertService:
    """
    Lee un .sql con múltiples INSERTs, para cada INSERT:
      - detecta tabla destino
      - consulta MAX(timestamp/date) en destino
      - inyecta WHERE <expr_timestamp> > last_value
      - ejecuta el INSERT
    """

    def __init__(
            self,
            conn_cfg: ClickHouseConnConfig,
            cfg: IncrementalInsertConfig | None = None,
    ) -> None:
        self.conn_cfg = conn_cfg
        self.cfg = cfg or IncrementalInsertConfig()

        self._client = clickhouse_connect.get_client(
            host=self.conn_cfg.host,
            port=self.conn_cfg.port,
            username=self.conn_cfg.username,
            password=self.conn_cfg.password,
            database=self.conn_cfg.database,
            secure=self.conn_cfg.secure,
            connect_timeout=self.conn_cfg.connect_timeout,
            send_receive_timeout=self.conn_cfg.send_receive_timeout,
        )

    # -------------------------
    # Public API
    # -------------------------

    def run_sql_file_incremental(self, sql_path: str | Path) -> List[InsertExecutionResult]:
        sql_path = Path(sql_path)
        if not sql_path.exists():
            raise ValueError(f"SQL file no existe: {sql_path}")

        sql_text = sql_path.read_text(encoding="utf-8")
        inserts = self._extract_insert_statements(sql_text)

        results: List[InsertExecutionResult] = []

        for insert_sql in inserts:
            try:
                table = self._parse_target_table(insert_sql)
                time_col = self._pick_time_column(table)
                last_val = self._get_last_value(table, time_col) if time_col else None

                # Si no hay columna temporal detectable:
                if not time_col:
                    # ejecuta tal cual
                    self._client.command(insert_sql)
                    results.append(
                        InsertExecutionResult(
                            table=table,
                            used_time_column=None,
                            last_value=None,
                            injected_where=False,
                            executed=True,
                        )
                    )
                    continue

                # Tabla vacía:
                if last_val is None:
                    if self.cfg.insert_all_if_empty:
                        self._client.command(insert_sql)
                        results.append(
                            InsertExecutionResult(
                                table=table,
                                used_time_column=time_col,
                                last_value=None,
                                injected_where=False,
                                executed=True,
                            )
                        )
                    else:
                        results.append(
                            InsertExecutionResult(
                                table=table,
                                used_time_column=time_col,
                                last_value=None,
                                injected_where=False,
                                executed=False,
                                error="Tabla vacía y insert_all_if_empty=False; no se ejecuta.",
                            )
                        )
                    continue

                # Construir WHERE incremental usando la expresión que genera el timestamp en el SELECT
                ts_expr = self._extract_time_expr_from_insert(insert_sql, time_col)

                # Si no se pudo extraer la expresión (caso raro), fallback:
                # intentamos filtrar por la columna del origen si existe un "t.<date>" simple
                if ts_expr is None:
                    # ejecuta tal cual para no romper
                    self._client.command(insert_sql)
                    results.append(
                        InsertExecutionResult(
                            table=table,
                            used_time_column=time_col,
                            last_value=last_val,
                            injected_where=False,
                            executed=True,
                            error="No se pudo extraer la expresión temporal del SELECT; ejecutado sin WHERE.",
                        )
                    )
                    continue

                updated_sql = self._inject_where(insert_sql, ts_expr, last_val)

                self._client.command(updated_sql)

                results.append(
                    InsertExecutionResult(
                        table=table,
                        used_time_column=time_col,
                        last_value=last_val,
                        injected_where=True,
                        executed=True,
                    )
                )

            except Exception as e:
                # Intenta recuperar tabla si posible
                table_guess = self._safe_table_guess(insert_sql)
                results.append(
                    InsertExecutionResult(
                        table=table_guess or "<unknown>",
                        used_time_column=None,
                        last_value=None,
                        injected_where=False,
                        executed=False,
                        error=str(e),
                    )
                )

        return results

    # -------------------------
    # Parsing / helpers
    # -------------------------

    @staticmethod
    def _extract_insert_statements(sql_text: str) -> List[str]:
        """
        Extrae cada statement que empiece por INSERT y termine en ';'
        Asumiendo que el generador termina cada INSERT con ';'
        """
        # Elimina \r y normaliza
        text = sql_text.replace("\r\n", "\n").replace("\r", "\n")

        # Captura "INSERT ... ;" incluyendo saltos de línea
        pattern = re.compile(r"(?is)\bINSERT\b.*?;\s*")
        return [m.group(0).strip() for m in pattern.finditer(text)]

    @staticmethod
    def _parse_target_table(insert_sql: str) -> str:
        """
        INSERT INTO <table> ( ... )
        """
        m = re.search(r"(?is)\bINSERT\s+INTO\s+([^\s(]+)\s*\(", insert_sql)
        if not m:
            raise ValueError("No pude detectar tabla destino en el INSERT.")
        return m.group(1).strip()

    def _pick_time_column(self, table: str) -> Optional[str]:
        """
        Elige la columna temporal existente en destino.
        """
        cols = self._get_table_columns(table)
        cols_l = {c.lower() for c in cols}

        for candidate in self.cfg.preferred_time_columns:
            if candidate.lower() in cols_l:
                # devuelve el nombre con la capitalización real si coincide
                for c in cols:
                    if c.lower() == candidate.lower():
                        return c
                return candidate  # fallback
        return None

    def _get_table_columns(self, table: str) -> List[str]:
        # DESCRIBE TABLE devuelve columnas en "name"
        rows = self._client.query(f"DESCRIBE TABLE {table}").result_rows
        # result_rows: [(name, type, default_type, default_expression, comment, codec_expression, ttl_expression), ...]
        return [r[0] for r in rows]

    def _get_last_value(self, table: str, time_col: str) -> Optional[str]:
        """
        Devuelve MAX(time_col) como string ISO 'YYYY-MM-DD HH:MM:SS' o 'YYYY-MM-DD'
        """
        q = f"SELECT max({time_col}) FROM {table}"
        val = self._client.query(q).result_rows[0][0]
        if val is None:
            return None

        # clickhouse-connect puede devolver datetime/date
        if isinstance(val, datetime):
            return val.strftime("%Y-%m-%d %H:%M:%S")
        # date
        try:
            return str(val)
        except Exception:
            return None

    @staticmethod
    def _extract_dest_and_src_lists(insert_sql: str) -> Tuple[List[str], List[str]]:
        """
        Dado el formato del generador:
            INSERT INTO table (
               col1,
               col2
            )
            SELECT
               expr1,
               expr2
            FROM ...
        Devuelve (dest_cols, src_exprs) con correspondencia posicional.
        """
        # Dest cols: entre "INSERT INTO ... (" y ")"
        m_dest = re.search(r"(?is)\bINSERT\s+INTO\s+[^\s(]+\s*\((.*?)\)\s*SELECT\b", insert_sql)
        if not m_dest:
            raise ValueError("No pude parsear lista de columnas destino.")
        dest_block = m_dest.group(1)

        # Src exprs: entre "SELECT" y "FROM"
        m_src = re.search(r"(?is)\bSELECT\b(.*?)\bFROM\b", insert_sql)
        if not m_src:
            raise ValueError("No pude parsear lista de expresiones fuente (SELECT ... FROM).")
        src_block = m_src.group(1)

        # limpiar y dividir por líneas con coma al final
        dest_cols = []
        for line in dest_block.splitlines():
            s = line.strip().rstrip(",")
            if s:
                dest_cols.append(s)

        src_exprs = []
        for line in src_block.splitlines():
            s = line.strip().rstrip(",")
            if not s:
                continue
            # ignora líneas tipo comentarios
            if s.startswith("--"):
                continue
            src_exprs.append(s)

        # OJO: en tu formato, cada expr está en su propia línea, esto encaja.
        if len(dest_cols) != len(src_exprs):
            raise ValueError(
                f"Destino y SELECT no tienen misma longitud: dest={len(dest_cols)} src={len(src_exprs)}"
            )

        return dest_cols, src_exprs

    def _extract_time_expr_from_insert(self, insert_sql: str, time_col: str) -> Optional[str]:
        """
        Busca qué expresión del SELECT corresponde al campo destino time_col.
        """
        dest_cols, src_exprs = self._extract_dest_and_src_lists(insert_sql)

        # buscar índice del campo temporal en destino
        idx = None
        for i, col in enumerate(dest_cols):
            if col.strip().lower() == time_col.strip().lower():
                idx = i
                break

        if idx is None:
            return None

        # expr correspondiente
        return src_exprs[idx].strip()

    @staticmethod
    def _inject_where(insert_sql: str, time_expr: str, last_value: str) -> str:
        """
        Inserta "WHERE <time_expr> > toDateTime('...')" antes de GROUP BY o antes del ';' final.
        Mantiene el resto igual.
        """
        # Decide si usar toDateTime o toDate según formato
        # Si last_value tiene hora -> toDateTime; si no -> toDate
        if " " in last_value:
            rhs = f"toDateTime('{last_value}')"
        else:
            rhs = f"toDate('{last_value}')"

        where_line = f"WHERE {time_expr} > {rhs}\n"

        # Si ya hay WHERE, no lo tocamos (evita duplicar lógica)
        if re.search(r"(?is)\bWHERE\b", insert_sql):
            return insert_sql

        # Inyectar antes de GROUP BY si existe
        m_gb = re.search(r"(?is)\bGROUP\s+BY\b", insert_sql)
        if m_gb:
            pos = m_gb.start()
            return insert_sql[:pos] + where_line + insert_sql[pos:]

        # Si no hay GROUP BY: insertar antes del ';' final
        m_end = re.search(r";\s*$", insert_sql)
        if not m_end:
            # fallback: añadir al final
            return insert_sql + "\n" + where_line

        pos = m_end.start()
        # insertar antes del ;
        return insert_sql[:pos] + "\n" + where_line + insert_sql[pos:]

    @staticmethod
    def _safe_table_guess(insert_sql: str) -> Optional[str]:
        try:
            return ClickHouseIncrementalInsertService._parse_target_table(insert_sql)
        except Exception:
            return None
