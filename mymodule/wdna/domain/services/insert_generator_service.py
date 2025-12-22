# sql_generator_service.py
"""
Service: generar comandos SQL (ClickHouse INSERTs) a partir de un Excel en crudo.

Entrada (API):
- excel_bytes: bytes del XLSX
- entity: str
- sheet_name: str (por defecto 'ETLs')

Salida:
- sql_bytes: bytes (utf-8) con el contenido del .sql
- meta: info útil (insert_count, skipped, etc.)

NOTA: "Tablas de pm hay que añadirle el _hour" lo dejo como TODO configurable
porque depende de tu naming real (y no quiero romperte tablas si no es exactamente así).
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
from collections import defaultdict

import pandas as pd


@dataclass(frozen=True)
class SqlGeneratorConfig:
    vendor_dbs: Dict[str, str] = None  # se rellena en __post_init__
    skip_aliases: Tuple[str, ...] = (
        "cell_id", "enb_agg", "enb_id", "date", "timestamp", "vendor",
        "source_type", "product_vertical", "country", "domain", "product / vertical"
    )
    id_fields: Tuple[str, ...] = ("cell_id", "enb_agg", "enb_id", "date")
    base_fields: Tuple[str, ...] = (
        "product_vertical", "country", "domain", "cell_id", "enb_agg", "enb_id",
        "timestamp", "vendor", "source_type"
    )

    # Columnas esperadas en la hoja ETLs (la que sale del primer servicio)
    # OJO: aquí deben coincidir con tu Excel real.
    col_vendor: str = "Vendor"
    col_entity: str = "Entidad"
    col_term_alias: str = "Term alias"
    col_term_code: str = "Term code"
    col_table: str = "db_table_source"
    col_formula: str = "FORMULA SQL"
    col_hierarchy: str = "hierarchy"
    col_fix: str = "Corregir"
    col_source_type: str = "Source type"
    col_product_vertical: str = "Product / Vertical"
    col_country: str = "Country"
    col_domain: str = "Domain"

    # Si quieres aplicar el sufijo _hour a tablas PM:
    pm_table_suffix: str = ""  # pon "_hour" si lo quieres forzar

    def __post_init__(self):
        if self.vendor_dbs is None:
            object.__setattr__(self, "vendor_dbs", {
                "NOKIA": "wdna_att_nokia4g",
                "SAMSUNG": "wdna_att_samsung4g",
                "ERICSSON": "wdna_att_ericsson4g",
                "HUAWEI": "wdna_att_huawei4g",
            })


@dataclass(frozen=True)
class SqlGeneratorMeta:
    entity: str
    sheet_name: str
    insert_count: int
    skipped: List[str]
    processed_rows: int


class SqlGeneratorService:
    def __init__(self, config: SqlGeneratorConfig | None = None) -> None:
        self.config = config or SqlGeneratorConfig()

    @staticmethod
    def _norm(x: Any) -> str:
        return str(x).strip().lower()

    def _get_field(self, row: pd.Series, col: str) -> Optional[str]:
        val = row.get(col)
        if pd.notna(val):
            return str(val).strip()
        return None

    def _timestamp_fx(self, source_type: str, date_field: str) -> str:
        if source_type == "PM":
            return (
                f"toDateTime(concat(toString(t.{date_field}), ' ', "
                "leftPad(toString(t.TIME), 2, '0'), ':', "
                "leftPad(toString(t.PERIOD_DURATION), 2, '0'), ':00'))"
            )
        return f"toDateTime(toString(t.{date_field}))"

    def _trans_fx(self, formula: str) -> str:
        fx = formula.replace("IFNULL(", "ifNull(")
        # tabla.campo -> t.campo
        fx = re.sub(r"[A-Za-z_][A-Za-z0-9_]*\.([A-Za-z_][A-Za-z0-9_]*)", r"t.\1", fx)
        return fx

    def _format_insert(
            self,
            entity: str,
            dest: List[str],
            src: List[str],
            db: str,
            table: str,
            group_by: Optional[str] = None,
    ) -> str:
        lines = [f"INSERT INTO {entity}_raw ("]
        for i, field in enumerate(dest):
            coma = "," if i < len(dest) - 1 else ""
            lines.append(f"    {field}{coma}")
        lines.append(")")
        lines.append("SELECT")
        for i, field in enumerate(src):
            coma = "," if i < len(src) - 1 else ""
            lines.append(f"    {field}{coma}")

        lines.append(f"FROM {db}.{table} AS t")
        if group_by:
            lines.append(f"GROUP BY {group_by};")
        else:
            lines[-1] += ";"
        return "\n".join(lines)

    def _apply_pm_suffix_if_needed(self, table: str, source_type: str) -> str:
        # Solo si config.pm_table_suffix está definido y source_type == 'PM'
        if self.config.pm_table_suffix and source_type == "PM":
            if not table.endswith(self.config.pm_table_suffix):
                return f"{table}{self.config.pm_table_suffix}"
        return table

    def _extract_metadata(self, row: pd.Series) -> Optional[Dict[str, str]]:
        cfg = self.config
        field_map = {
            "source_type": cfg.col_source_type,
            "product_vertical": cfg.col_product_vertical,
            "country": cfg.col_country,
            "domain": cfg.col_domain,
        }
        meta: Dict[str, str] = {}
        for key, col in field_map.items():
            val = self._get_field(row, col)
            if val is None:
                return None
            meta[key] = val
        return meta

    def _build_id_mappings(self, df: pd.DataFrame) -> Dict[str, Dict[str, Dict[str, str]]]:
        cfg = self.config
        mappings = defaultdict(lambda: defaultdict(dict))
        for _, row in df.iterrows():
            vendor = self._get_field(row, cfg.col_vendor)
            alias = self._get_field(row, cfg.col_term_alias)
            code = self._get_field(row, cfg.col_term_code)
            table = self._get_field(row, cfg.col_table)

            if vendor and table and alias in cfg.id_fields and code:
                for tname in str(table).split(","):
                    mappings[vendor][tname.strip()][alias] = code
        return mappings

    def _get_id_map(self, id_mappings, vendor: str, table: str) -> Optional[Dict[str, str]]:
        cfg = self.config
        id_map = id_mappings.get(vendor, {}).get(table, {})
        for field in cfg.id_fields:
            if field not in id_map:
                return None
        return id_map

    def _base_cols(self, meta: Dict[str, str], id_map: Dict[str, str], vendor: str) -> Tuple[List[str], List[str]]:
        cfg = self.config
        ts = self._timestamp_fx(meta["source_type"], id_map["date"])
        dest = list(cfg.base_fields)
        src = [
            f"'{meta['product_vertical']}'",
            f"'{meta['country']}'",
            f"'{meta['domain']}'",
            f"t.{id_map['cell_id']}",
            f"t.{id_map['enb_agg']}",
            f"t.{id_map['enb_id']}",
            ts,
            f"'{vendor}'",
            f"'{meta['source_type']}'",
        ]
        return dest, src

    def _filter_simple_fields(self, vendor_df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config
        mask = (
                vendor_df[cfg.col_formula].isna()
                & vendor_df[cfg.col_table].notna()
                & ~vendor_df[cfg.col_table].str.contains(",", na=True)
        )
        return vendor_df[mask]

    def _filter_kpi_fields(self, vendor_df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config
        mask = (
                vendor_df[cfg.col_formula].notna()
                & (vendor_df[cfg.col_fix].isna() | (vendor_df[cfg.col_fix] != "y"))
                & vendor_df[cfg.col_hierarchy].notna()
                & vendor_df[cfg.col_table].notna()
                & ~vendor_df[cfg.col_table].str.contains(",", na=True)
        )
        return vendor_df[mask]

    def _simple_fields_sql(self, df: pd.DataFrame, entity: str, id_mappings, skipped: List[str]) -> List[str]:
        cfg = self.config
        sql_lines: List[str] = ["-- CAMPOS SIN FORMULA SQL\n"]

        for vendor, db in cfg.vendor_dbs.items():
            vendor_df = df[df[cfg.col_vendor] == vendor]
            filtered = self._filter_simple_fields(vendor_df)

            by_table = defaultdict(list)
            table_meta: Dict[str, Dict[str, str]] = {}

            for _, row in filtered.iterrows():
                table = self._get_field(row, cfg.col_table)
                alias = self._get_field(row, cfg.col_term_alias)
                code = self._get_field(row, cfg.col_term_code)

                if not table or not alias or not code:
                    continue

                if alias not in cfg.skip_aliases:
                    by_table[table].append((alias, code))

                    if table not in table_meta:
                        meta = self._extract_metadata(row)
                        if meta:
                            table_meta[table] = meta

            for table, fields in by_table.items():
                if table not in table_meta:
                    skipped.append(f"SIMPLE {vendor}/{table}: faltan metadatos")
                    continue

                meta = table_meta[table]
                table_eff = self._apply_pm_suffix_if_needed(table, meta["source_type"])

                id_map = self._get_id_map(id_mappings, vendor, table)
                if not id_map:
                    skipped.append(f"SIMPLE {vendor}/{table}: faltan campos ID")
                    continue

                dest, src = self._base_cols(meta, id_map, vendor)

                for alias, code in fields:
                    dest.append(alias)
                    src.append(f"t.{code}")

                sql_lines.append(f"-- {vendor} / {table_eff} ({len(fields)} campos)")
                sql_lines.append(self._format_insert(entity, dest, src, db, table_eff))
                sql_lines.append("")

        return sql_lines

    def _kpi_fields_sql(self, df: pd.DataFrame, entity: str, id_mappings, skipped: List[str]) -> List[str]:
        cfg = self.config
        sql_lines: List[str] = ["\n-- CAMPOS CON FORMULA SQL (KPIs)\n"]

        for vendor, db in cfg.vendor_dbs.items():
            vendor_df = df[df[cfg.col_vendor] == vendor]
            filtered = self._filter_kpi_fields(vendor_df)

            by_table_hierarchy = defaultdict(list)
            table_meta: Dict[Tuple[str, str], Dict[str, str]] = {}

            for _, row in filtered.iterrows():
                table = self._get_field(row, cfg.col_table)
                alias = self._get_field(row, cfg.col_term_alias)
                formula = self._get_field(row, cfg.col_formula)
                hierarchy = self._get_field(row, cfg.col_hierarchy)

                if not table or not alias or not formula or not hierarchy:
                    continue

                key = (table, hierarchy)

                if alias not in cfg.skip_aliases:
                    by_table_hierarchy[key].append((alias, formula))

                    if key not in table_meta:
                        meta = self._extract_metadata(row)
                        if meta:
                            meta["hierarchy"] = hierarchy
                            table_meta[key] = meta

            for (table, hierarchy), fields in by_table_hierarchy.items():
                key = (table, hierarchy)
                if key not in table_meta:
                    skipped.append(f"KPI {vendor}/{table} (h:{hierarchy}): faltan metadatos")
                    continue

                meta = table_meta[key]
                table_eff = self._apply_pm_suffix_if_needed(table, meta["source_type"])

                id_map = self._get_id_map(id_mappings, vendor, table)
                if not id_map:
                    skipped.append(f"KPI {vendor}/{table} (h:{hierarchy}): faltan campos ID")
                    continue

                dest, src = self._base_cols(meta, id_map, vendor)

                for alias, formula in fields:
                    dest.append(alias)
                    adapted = self._trans_fx(formula)
                    src.append(f"{adapted} AS {alias}")

                hierarchy_fields = [f.strip() for f in hierarchy.split(",")]

                if meta["source_type"] == "PM":
                    time_fields = [id_map["date"], "TIME", "PERIOD_DURATION"]
                else:
                    time_fields = [id_map["date"]]

                group_by = ", ".join([f"t.{f}" for f in hierarchy_fields + time_fields])

                sql_lines.append(f"-- {vendor} / {table_eff} ({len(fields)} KPIs, hierarchy: {hierarchy})")
                sql_lines.append(self._format_insert(entity, dest, src, db, table_eff, group_by))
                sql_lines.append("")

        return sql_lines

    def generate_sql_from_excel_path(
            self,
            input_path: str | Path,
            entity: str,
            sheet_name: str = "ETLs",
    ) -> Tuple[Path, SqlGeneratorMeta]:
        """
        Lee un XLSX desde disco, genera un .sql en ./results/ y devuelve su path.
        """
        input_path = Path(input_path)

        if not input_path.exists():
            raise ValueError(f"El fichero no existe: {input_path}")

        try:
            df = pd.read_excel(input_path, sheet_name=sheet_name)
        except Exception as e:
            raise ValueError(f"No se pudo leer el Excel '{input_path}' (sheet='{sheet_name}'): {e}") from e

        cfg = self.config
        if cfg.col_entity not in df.columns:
            raise ValueError(f"No existe la columna '{cfg.col_entity}' en la hoja '{sheet_name}'")

        df = df[df[cfg.col_entity].astype(str).str.strip().str.lower() == self._norm(entity)].copy()
        if df.empty:
            raise ValueError(f"No hay filas para la entidad '{entity}' en la hoja '{sheet_name}'")

        id_mappings = self._build_id_mappings(df)

        skipped: List[str] = []
        sql_lines: List[str] = []
        sql_lines.extend(self._simple_fields_sql(df, entity, id_mappings, skipped))
        sql_lines.extend(self._kpi_fields_sql(df, entity, id_mappings, skipped))

        sql_text = "\n".join(sql_lines)
        insert_count = sum(1 for line in sql_lines if line.startswith("INSERT"))

        # ✅ output en results/
        results_dir = input_path.parent / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        output_path = results_dir / f"{entity.lower()}_inserts_v1.sql"
        output_path.write_text(sql_text, encoding="utf-8")

        meta = SqlGeneratorMeta(
            entity=entity,
            sheet_name=sheet_name,
            insert_count=insert_count,
            skipped=skipped,
            processed_rows=len(df),
        )
        return output_path, meta

