"""
Audit and incremental-loading query helpers.

These functions wrap the SQL needed for:
  - starting/finishing a pipeline run (audit.pipeline_runs)
  - reading the watermark (the timestamp of the last successful run) so
    ingestion only pulls new/changed records
  - recording data quality check results (audit.data_quality_results)
  - recording rejected records instead of silently dropping them
"""

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import Engine, text

from dataflowx.utils.logger import get_logger

logger = get_logger(__name__)


def get_last_successful_watermark(pipeline_name: str, engine: Engine) -> datetime | None:
    """
    Return the watermark_end of the most recent successful run.

    Returns None on the first-ever run for this pipeline, which callers
    should treat as "process everything" (full load).
    """
    query = text(
        """
        SELECT watermark_end
        FROM audit.pipeline_runs
        WHERE pipeline_name = :pipeline_name
          AND status = 'success'
        ORDER BY completed_at DESC
        LIMIT 1
        """
    )
    with engine.connect() as conn:
        result = conn.execute(query, {"pipeline_name": pipeline_name}).fetchone()
    return result[0] if result else None


def start_pipeline_run(pipeline_name: str, watermark_start: datetime | None, engine: Engine) -> int:
    """Insert a 'running' row into audit.pipeline_runs and return its run_id."""
    query = text(
        """
        INSERT INTO audit.pipeline_runs (pipeline_name, started_at, status, watermark_start)
        VALUES (:pipeline_name, :started_at, 'running', :watermark_start)
        RETURNING run_id
        """
    )
    with engine.begin() as conn:
        run_id = conn.execute(
            query,
            {
                "pipeline_name": pipeline_name,
                "started_at": datetime.now(timezone.utc),
                "watermark_start": watermark_start,
            },
        ).scalar_one()
    logger.info("Started pipeline run %s (id=%d)", pipeline_name, run_id)
    return run_id


def finish_pipeline_run(
    run_id: int,
    engine: Engine,
    status: str,
    records_processed: int = 0,
    watermark_end: datetime | None = None,
    error_message: str | None = None,
) -> None:
    """Mark a pipeline run as success or failed."""
    if status not in ("success", "failed"):
        raise ValueError("status must be 'success' or 'failed'")

    query = text(
        """
        UPDATE audit.pipeline_runs
        SET completed_at = :completed_at,
            status = :status,
            records_processed = :records_processed,
            watermark_end = :watermark_end,
            error_message = :error_message
        WHERE run_id = :run_id
        """
    )
    with engine.begin() as conn:
        conn.execute(
            query,
            {
                "completed_at": datetime.now(timezone.utc),
                "status": status,
                "records_processed": records_processed,
                "watermark_end": watermark_end,
                "error_message": error_message,
                "run_id": run_id,
            },
        )
    logger.info(
        "Finished pipeline run id=%d status=%s records_processed=%d",
        run_id,
        status,
        records_processed,
    )


def record_data_quality_result(
    pipeline_run_id: int,
    table_name: str,
    check_name: str,
    status: str,
    failed_rows: int,
    engine: Engine,
) -> None:
    if status not in ("pass", "fail", "warning"):
        raise ValueError("status must be 'pass', 'fail' or 'warning'")

    query = text(
        """
        INSERT INTO audit.data_quality_results
            (pipeline_run_id, table_name, check_name, status, failed_rows)
        VALUES (:run_id, :table_name, :check_name, :status, :failed_rows)
        """
    )
    with engine.begin() as conn:
        conn.execute(
            query,
            {
                "run_id": pipeline_run_id,
                "table_name": table_name,
                "check_name": check_name,
                "status": status,
                "failed_rows": failed_rows,
            },
        )


def record_rejected_rows(
    rejected_df: pd.DataFrame,
    source: str,
    table_name: str,
    reason: str,
    engine: Engine,
) -> None:
    """Persist rejected rows to audit.rejected_records instead of dropping them."""
    if rejected_df.empty:
        return

    query = text(
        """
        INSERT INTO audit.rejected_records (source, table_name, record_data, reason)
        VALUES (:source, :table_name, :record_data, :reason)
        """
    )
    records: list[dict[str, Any]] = rejected_df.to_dict(orient="records")
    with engine.begin() as conn:
        for record in records:
            conn.execute(
                query,
                {
                    "source": source,
                    "table_name": table_name,
                    "record_data": json.dumps(record, default=str),
                    "reason": reason,
                },
            )
    logger.warning(
        "Recorded %d rejected rows for %s (%s): %s",
        len(records),
        table_name,
        source,
        reason,
    )
