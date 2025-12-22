import click

from mymodule.common.configuration.config import configure_logging
from mymodule.wdna.controllers.wdna_controller import WdnaController


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx) -> None:  # pylint: disable=unused-argument
    configure_logging()




@main.command("master-to-etl")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False, path_type=str), required=True)
@click.argument("entity", type=click.STRING, required=True)
@click.option("--sheet-name", default="masterdata", show_default=True, type=click.STRING)
def master_to_etl(input_path: str, entity: str, sheet_name: str) -> None:
    """
    Genera el Excel ETL (2 hojas) a partir del masterdata.

    Output: <carpeta_input>/results/<entity>_extracted.xlsx
    """
    controller = WdnaController()
    output_path, meta = controller.master_to_etl(
        input_excel_path=input_path,
        entity=entity,
        sheet_name=sheet_name,
    )

    print(f"✅ Generado: {output_path}")
    print(
        f"Filas totales={meta.rows_total_input} | "
        f"Entidad={meta.rows_filtered_entity} | "
        f"Normal={meta.rows_normal} | "
        f"KPIs_of_KPIs={meta.rows_kpis_of_kpis}"
    )


@main.command("generate-sql")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False, path_type=str), required=True)
@click.argument("entity", type=click.STRING, required=True)
@click.option("--sheet-name", default="ETLs", show_default=True, type=click.STRING)
def generate_sql(input_path: str, entity: str, sheet_name: str) -> None:
    """
    Genera el fichero SQL de INSERTs a partir de la hoja ETLs.

    Output: <carpeta_input>/results/<entity>_inserts_v1.sql
    """
    controller = WdnaController()
    output_path, meta = controller.generate_sql(
        input_excel_path=input_path,
        entity=entity,
        sheet_name=sheet_name,
    )

    print(f"✅ Generado: {output_path}")
    print(f"INSERTs={meta.insert_count} | Filas procesadas={meta.processed_rows}")

    if meta.skipped:
        print(f"\n⚠ Skipped ({len(meta.skipped)}):")
        for s in meta.skipped:
            print(f" - {s}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
