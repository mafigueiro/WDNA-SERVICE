# mymodule/wdna/application/controllers/wdna_controller.py

from __future__ import annotations

from pathlib import Path

from mymodule.wdna.domain.services.master_to_etl_service import (
    MasterToEtlService,
    MasterToEtlMeta,
)
from mymodule.wdna.domain.services.insert_generator_service import (
    SqlGeneratorService,
    SqlGeneratorMeta,
)


class WdnaController:
    def __init__(self) -> None:
        self._master_to_etl_service = MasterToEtlService()
        self._sql_generator_service = SqlGeneratorService()

    def master_to_etl(
            self,
            input_excel_path: str | Path,
            entity: str,
            sheet_name: str = "masterdata",
    ) -> tuple[Path, MasterToEtlMeta]:
        return self._master_to_etl_service.process_excel_path(
            input_path=input_excel_path,
            entity=entity,
            sheet_name=sheet_name,
        )

    def generate_sql(
            self,
            input_excel_path: str | Path,
            entity: str,
            sheet_name: str = "ETLs",
    ) -> tuple[Path, SqlGeneratorMeta]:
        return self._sql_generator_service.generate_sql_from_excel_path(
            input_path=input_excel_path,
            entity=entity,
            sheet_name=sheet_name,
        )