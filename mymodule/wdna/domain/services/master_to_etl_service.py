# mymodule/wdna/domain/services/master_to_etl_service.py

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd


@dataclass(frozen=True)
class MasterToEtlConfig:
    source_cols: Tuple[str, ...] = (
        "Vendor",
        "entity",
        "Term Alias",
        "Term code",
        "schema_db",
        "db_table_source",
        "Data type",
        "hierarchy",
        "first_collection",
        "last_collection",
        "KPI formula",
        "Product / Vertical",
        "Country",
        "Domain",
        "Source type",
        "KPIs of KPIs",
    )

    col_mapping: Tuple[Tuple[Optional[str], str], ...] = (
        ("Vendor", "Vendor"),
        ("entity", "Entidad"),
        ("Term Alias", "Term alias"),
        ("Term code", "Term code"),
        (None, "Source"),
        ("schema_db", "schema_db"),
        ("db_table_source", "db_table_source"),
        ("Data type", "Tipo dato"),
        ("hierarchy", "hierarchy"),
        ("first_collection", "first_collection"),
        ("last_collection", "last_collection"),
        (None, "tracking"),
        ("KPI formula", "FORMULA SQL"),
        ("Product / Vertical", "Product / Vertical"),
        ("Country", "Country"),
        ("Domain", "Domain"),
        ("Source type", "Source type"),
        (None, "Corregir"),
    )

    entity_col: str = "entity"
    kpis_of_kpis_col: str = "KPIs of KPIs"
    kpis_of_kpis_yes_value: str = "yes"

    sort_by: Tuple[str, ...] = ("Term alias", "Vendor", "Entidad")

    sheet_normal: str = "Normal"
    sheet_kpis: str = "KPIs_of_KPIs"

    results_dirname: str = "results"  # 👈 NUEVO


@dataclass(frozen=True)
class MasterToEtlMeta:
    entity: str
    sheet_name: str
    rows_total_input: int
    rows_filtered_entity: int
    rows_normal: int
    rows_kpis_of_kpis: int
    used_engine: str = "openpyxl"


class MasterToEtlService:
    def __init__(self, config: MasterToEtlConfig | None = None) -> None:
        self.config = config or MasterToEtlConfig()

    @staticmethod
    def _norm(x: Any) -> str:
        return str(x).strip().lower()

    def _validate_required_columns(self, df: pd.DataFrame) -> None:
        missing = [c for c in self.config.source_cols if c not in df.columns]
        if missing:
            raise ValueError("Faltan columnas requeridas en el Excel de entrada: " + ", ".join(missing))

    def _filter_by_entity(self, df: pd.DataFrame, entity: str) -> pd.DataFrame:
        col = self.config.entity_col
        entity_norm = self._norm(entity)
        mask = df[col].apply(lambda v: self._norm(v) == entity_norm if pd.notna(v) else False)
        return df[mask].copy()

    def _split_kpis_kpis(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        col = self.config.kpis_of_kpis_col
        yes = self._norm(self.config.kpis_of_kpis_yes_value)
        mask_yes = df[col].apply(lambda v: self._norm(v) == yes if pd.notna(v) else False)
        return df[~mask_yes].copy(), df[mask_yes].copy()

    def _build_output_df(self, df: pd.DataFrame) -> pd.DataFrame:
        out: Dict[str, Any] = {}
        for src_col, dest_col in self.config.col_mapping:
            if src_col is None:
                out[dest_col] = [""] * len(df)
            else:
                out[dest_col] = df[src_col].values
        return pd.DataFrame(out)

    def process_excel_path(
            self,
            input_path: str | Path,
            entity: str,
            sheet_name: str,
    ) -> Tuple[Path, MasterToEtlMeta]:
        """
        Lee un XLSX desde disco, genera un XLSX en ./results/ y devuelve su path.
        """
        input_path = Path(input_path)

        if not input_path.exists():
            raise ValueError(f"El fichero no existe: {input_path}")

        try:
            df = pd.read_excel(input_path, sheet_name=sheet_name)
        except Exception as e:
            raise ValueError(f"No se pudo leer el Excel '{input_path}' (sheet='{sheet_name}'): {e}") from e

        self._validate_required_columns(df)

        df_filtered = self._filter_by_entity(df, entity)
        if df_filtered.empty:
            raise ValueError(f"No se encontraron filas para la entidad '{entity}'")

        df_normal, df_kpis = self._split_kpis_kpis(df_filtered)

        out_normal = self._build_output_df(df_normal)
        out_kpis = self._build_output_df(df_kpis)

        sort_cols = [c for c in self.config.sort_by if c in out_normal.columns]
        if sort_cols:
            out_normal = out_normal.sort_values(by=sort_cols)
            out_kpis = out_kpis.sort_values(by=sort_cols)

        # ✅ output en results/
        results_dir = input_path.parent / self.config.results_dirname
        results_dir.mkdir(parents=True, exist_ok=True)

        output_path = results_dir / f"{entity.lower()}_extracted.xlsx"

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            out_normal.to_excel(writer, sheet_name=self.config.sheet_normal, index=False)
            out_kpis.to_excel(writer, sheet_name=self.config.sheet_kpis, index=False)

        meta = MasterToEtlMeta(
            entity=entity,
            sheet_name=sheet_name,
            rows_total_input=len(df),
            rows_filtered_entity=len(df_filtered),
            rows_normal=len(out_normal),
            rows_kpis_of_kpis=len(out_kpis),
        )

        return output_path, meta
