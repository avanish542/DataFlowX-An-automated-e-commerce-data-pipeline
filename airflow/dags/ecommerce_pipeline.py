"""
DataFlowX e-commerce pipeline DAG.

This DAG is intentionally thin - every task calls a function that already
lives (and is unit tested) in src/dataflowx. The DAG's job is scheduling,
retries, dependencies and failure handling, not business logic.

Design note on task granularity:
The original design called for separate "validate_raw_data" and
"load_bronze" tasks. In practice, extract -> validate -> load is done as
one task per source table inside ingestion_service.py, because passing
full DataFrames between Airflow tasks via XCom is a known anti-pattern
(XCom is meant for small metadata, not bulk data) - splitting it further
would mean re-reading files or round-tripping large DataFrames through
the metadata database for no real benefit. The task graph below reflects
that: "ingest_to_raw" covers extract+validate+load together, and DAG-level
observability comes from the audit.pipeline_runs / audit.rejected_records
tables instead of Airflow logs alone.
"""

from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from dataflowx.config.settings import settings
from dataflowx.database.connection import get_engine
from dataflowx.database.queries import (
    finish_pipeline_run,
    get_last_successful_watermark,
    start_pipeline_run,
)
from dataflowx.ingestion.ingestion_service import ingest_all
from dataflowx.validation.data_quality import RAW_LAYER_CHECKS, run_quality_checks

PIPELINE_NAME = "ecommerce_pipeline"
DBT_PROJECT_DIR = "/opt/airflow/dbt"

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=30),
}


def check_source_files(**context) -> None:
    """Fail fast if an expected source file is missing."""
    expected_files = [
        "customers.csv",
        "stores.csv",
        "products.csv",
        "orders.csv",
        "order_items.csv",
        "payments.json",
    ]
    missing = [f for f in expected_files if not (settings.raw_data_dir / f).exists()]
    if missing:
        raise FileNotFoundError(f"Missing expected source files: {missing}")


def start_run(**context) -> None:
    engine = get_engine()
    run_id = start_pipeline_run(PIPELINE_NAME, datetime.now(timezone.utc), engine)
    context["ti"].xcom_push(key="run_id", value=run_id)


def ingest_to_raw(**context) -> None:
    engine = get_engine()
    results = ingest_all(engine)
    total_loaded = sum(r.rows_loaded for r in results)
    context["ti"].xcom_push(key="records_processed", value=total_loaded)


def run_quality_checks_task(**context) -> None:
    engine = get_engine()
    run_id = context["ti"].xcom_pull(key="run_id", task_ids="start_run")
    passed = run_quality_checks(RAW_LAYER_CHECKS, run_id, engine)
    if not passed:
        raise ValueError("Critical data quality checks failed on the raw layer")


def update_pipeline_metadata(**context) -> None:
    """
    Always runs (trigger_rule=all_done) so the pipeline run is marked
    success or failed regardless of which upstream task failed.
    """
    engine = get_engine()
    ti = context["ti"]
    run_id = ti.xcom_pull(key="run_id", task_ids="start_run")
    records_processed = ti.xcom_pull(key="records_processed", task_ids="ingest_to_raw") or 0

    dag_run = context["dag_run"]
    failed_tasks = [t for t in dag_run.get_task_instances() if t.state == "failed"]
    status = "failed" if failed_tasks else "success"

    finish_pipeline_run(
        run_id,
        engine,
        status=status,
        records_processed=records_processed,
        watermark_end=datetime.now(timezone.utc) if status == "success" else None,
    )


with DAG(
    dag_id="ecommerce_pipeline",
    description="Ingest -> validate -> bronze -> dbt staging -> quality -> dbt marts -> audit",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["dataflowx", "ecommerce"],
) as dag:

    t_check_source_files = PythonOperator(
        task_id="check_source_files",
        python_callable=check_source_files,
    )

    t_start_run = PythonOperator(
        task_id="start_run",
        python_callable=start_run,
    )

    t_ingest_to_raw = PythonOperator(
        task_id="ingest_to_raw",
        python_callable=ingest_to_raw,
    )

    t_run_quality_checks = PythonOperator(
        task_id="run_quality_checks",
        python_callable=run_quality_checks_task,
    )

    # dbt commands are run via BashOperator so the DAG doesn't need a dbt
    # Python API dependency; `dbt` runs the same commands a developer
    # would run locally (see docs/pipeline.md).
    t_run_dbt_staging = BashOperator(
        task_id="run_dbt_staging",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run --select path:models/staging path:models/intermediate",
    )

    t_run_dbt_marts = BashOperator(
        task_id="run_dbt_marts",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run --select path:models/marts",
    )

    t_warehouse_validation = BashOperator(
        task_id="warehouse_validation",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt test",
    )

    t_update_pipeline_metadata = PythonOperator(
        task_id="update_pipeline_metadata",
        python_callable=update_pipeline_metadata,
        trigger_rule="all_done",
    )

    (
        t_check_source_files
        >> t_start_run
        >> t_ingest_to_raw
        >> t_run_quality_checks
        >> t_run_dbt_staging
        >> t_run_dbt_marts
        >> t_warehouse_validation
        >> t_update_pipeline_metadata
    )
