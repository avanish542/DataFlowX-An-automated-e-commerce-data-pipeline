"""
Command-line interface for DataFlowX.

Usage:
    python -m dataflowx.cli init-db     # create schemas/tables from db/init/*.sql
    python -m dataflowx.cli ingest      # load raw sources into the raw schema
    python -m dataflowx.cli validate    # dry-run validation of source files (no DB writes)
    python -m dataflowx.cli transform   # run dbt (staging -> intermediate -> marts)
    python -m dataflowx.cli quality     # run data quality checks against raw tables
    python -m dataflowx.cli pipeline    # run the full pipeline end to end

Airflow calls the same underlying Python functions directly rather than
shelling out to this CLI - this CLI exists for local development and
manual runs.
"""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
from sqlalchemy import text

from dataflowx.config.settings import settings
from dataflowx.database.connection import check_connection, get_engine
from dataflowx.database.queries import (
    finish_pipeline_run,
    get_last_successful_watermark,
    start_pipeline_run,
)
from dataflowx.ingestion.ingestion_service import ingest_all
from dataflowx.ingestion.csv_loader import load_csv
from dataflowx.ingestion.json_loader import load_json
from dataflowx.utils.logger import get_logger
from dataflowx.validation.data_quality import RAW_LAYER_CHECKS, run_quality_checks
from dataflowx.validation.schema_validator import (
    CUSTOMERS_SCHEMA,
    ORDERS_SCHEMA,
    ORDER_ITEMS_SCHEMA,
    PAYMENTS_SCHEMA,
    PRODUCTS_SCHEMA,
    validate_schema,
)

logger = get_logger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_INIT_DIR = PROJECT_ROOT / "db" / "init"
DBT_DIR = PROJECT_ROOT / "dbt"


@click.group()
def cli() -> None:
    """DataFlowX - e-commerce data pipeline CLI."""


@cli.command("init-db")
def init_db() -> None:
    """Create schemas and tables by running db/init/*.sql in order."""
    if not check_connection():
        click.echo("Could not connect to PostgreSQL. Check your .env file.", err=True)
        sys.exit(1)

    engine = get_engine()
    sql_files = sorted(DB_INIT_DIR.glob("*.sql"))
    with engine.begin() as conn:
        for sql_file in sql_files:
            click.echo(f"Applying {sql_file.name} ...")
            conn.execute(text(sql_file.read_text()))
    click.echo("Database initialized.")


@cli.command("ingest")
def ingest() -> None:
    """Load raw source files into the raw (bronze) schema."""
    engine = get_engine()
    results = ingest_all(engine)
    for r in results:
        click.echo(f"{r.table_name:15s} loaded={r.rows_loaded:6d} rejected={r.rows_rejected}")


@cli.command("validate")
def validate() -> None:
    """Validate source files without writing to the database (dry run)."""
    sources = [
        ("customers.csv", CUSTOMERS_SCHEMA, load_csv),
        ("products.csv", PRODUCTS_SCHEMA, load_csv),
        ("orders.csv", ORDERS_SCHEMA, load_csv),
        ("order_items.csv", ORDER_ITEMS_SCHEMA, load_csv),
        ("payments.json", PAYMENTS_SCHEMA, load_json),
    ]
    any_failed = False
    for filename, schema, loader in sources:
        file_path = settings.raw_data_dir / filename
        if not file_path.exists():
            click.echo(f"{filename:20s} SKIPPED (file not found)")
            continue
        df = loader(file_path, required_columns=schema.required_columns)
        result = validate_schema(df, schema)
        status = "OK" if result.is_valid else "ISSUES FOUND"
        click.echo(
            f"{filename:20s} {status:15s} valid={len(result.valid_rows)} "
            f"invalid={len(result.invalid_rows)}"
        )
        any_failed = any_failed or not result.is_valid
    sys.exit(1 if any_failed else 0)


def _run_dbt(*args: str) -> int:
    """Run dbt with the repository-local profile, regardless of shell setup."""
    import os

    env = dict(os.environ)
    env["DBT_PROFILES_DIR"] = str(DBT_DIR)
    result = subprocess.run(
        [
            "dbt",
            *args,
            "--project-dir",
            str(DBT_DIR),
            "--profiles-dir",
            str(DBT_DIR),
        ],
        cwd=DBT_DIR,
        env=env,
    )
    return result.returncode


@cli.command("transform")
def transform() -> None:
    """Run dbt models (staging -> intermediate -> marts)."""
    sys.exit(_run_dbt("run"))


@cli.command("quality")
def quality() -> None:
    """Run data quality checks against the raw layer."""
    engine = get_engine()
    watermark_start = get_last_successful_watermark("adhoc-quality-check", engine)
    run_id = start_pipeline_run("adhoc-quality-check", watermark_start, engine)
    passed = run_quality_checks(RAW_LAYER_CHECKS, run_id, engine)
    finish_pipeline_run(run_id, engine, status="success" if passed else "failed")
    click.echo("All critical checks passed." if passed else "Critical checks FAILED.")
    sys.exit(0 if passed else 1)


@cli.command("pipeline")
def pipeline() -> None:
    """Run the full pipeline: ingest -> quality checks -> dbt transform -> dbt test."""
    engine = get_engine()
    watermark_start = get_last_successful_watermark("full-pipeline", engine)
    run_id = start_pipeline_run("full-pipeline", watermark_start, engine)

    try:
        results = ingest_all(engine)
        total_loaded = sum(r.rows_loaded for r in results)

        passed = run_quality_checks(RAW_LAYER_CHECKS, run_id, engine)
        if not passed:
            finish_pipeline_run(run_id, engine, status="failed", records_processed=total_loaded)
            click.echo("Pipeline stopped: critical data quality checks failed.", err=True)
            sys.exit(1)

        dbt_run = _run_dbt("run")
        if dbt_run != 0:
            finish_pipeline_run(run_id, engine, status="failed", records_processed=total_loaded)
            click.echo("Pipeline stopped: dbt run failed.", err=True)
            sys.exit(1)

        dbt_test = _run_dbt("test")

        finish_pipeline_run(
            run_id,
            engine,
            status="success" if dbt_test == 0 else "failed",
            records_processed=total_loaded,
            watermark_end=datetime.now(timezone.utc),
        )
        click.echo(f"Pipeline finished. {total_loaded} rows ingested.")
        sys.exit(0 if dbt_test == 0 else 1)

    except Exception as exc:
        logger.exception("Pipeline failed with an unexpected error")
        finish_pipeline_run(run_id, engine, status="failed", error_message=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    cli()
