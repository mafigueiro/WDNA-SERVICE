# mymodule/wdna/application/controllers/wdna_controller.py

from __future__ import annotations

from pathlib import Path

from mymodule.wdna.domain.services.execute_insert_query import InsertExecutionResult, \
    ClickHouseIncrementalInsertService, ClickHouseConnConfig, IncrementalInsertConfig
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
        self._ch_incremental_service = ClickHouseIncrementalInsertService(
            conn_cfg=ClickHouseConnConfig(
                host="localhost",
                port=8123,
                username="default",
                password="",
                database="default",
            ),
            cfg=IncrementalInsertConfig(
                preferred_time_columns=("timestamp", "date"),
                insert_all_if_empty=True,
            ),
        )
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

def execute_sql_incremental(
        self,
        input_excel_path: str | Path,
) -> list[InsertExecutionResult]:
    """
    1) Genera el .sql desde el excel (results/<entity>_inserts_v1.sql)
    2) Reescribe/ejecuta cada INSERT de forma incremental en ClickHouse:
       - mira max(timestamp|date) en la tabla destino
       - añade WHERE para insertar solo nuevos
       - ejecuta todos los INSERTs
    3) Devuelve (sql_path, meta_sql, resultados_ejecución)
    """

    results = self._ch_incremental_service.run_sql_file_incremental(input_excel_path)

    return  results