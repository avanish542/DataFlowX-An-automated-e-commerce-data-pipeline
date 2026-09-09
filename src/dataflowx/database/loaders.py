"""
Loading DataFrames into PostgreSQL.

These functions write pandas DataFrames into the `raw` schema (bronze
layer). They use pandas.DataFrame.to_sql with method="multi" for
reasonably efficient batch inserts without needing a separate COPY
implementation - fine at this project's data volume (tens of thousands
of rows, not millions).
"""

import pandas as pd
from sqlalchemy import Engine, text

from dataflowx.utils.logger import get_logger

logger = get_logger(__name__)

# Keep batches small enough to stay under PostgreSQL's bind-parameter limit
# when using to_sql(method="multi").
_INSERT_CHUNK_SIZE = 500


def load_dataframe_to_raw(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    if_exists: str = "append",
) -> int:
    """
    Write a DataFrame into a table in the `raw` schema.

    Args:
        df: data to load.
        table_name: target table name (without schema prefix).
        engine: SQLAlchemy engine.
        if_exists: "append" (default) or "replace".

    Returns:
        Number of rows written.
    """
    if df.empty:
        logger.warning("Skipping load into raw.%s - DataFrame is empty", table_name)
        return 0

    df.to_sql(
        name=table_name,
        con=engine,
        schema="raw",
        if_exists=if_exists,
        index=False,
        method="multi",
        chunksize=_INSERT_CHUNK_SIZE,
    )
    logger.info("Loaded %d rows into raw.%s", len(df), table_name)
    return len(df)


def truncate_raw_table(table_name: str, engine: Engine) -> None:
    """Remove all rows from a raw table (used before a full-refresh load)."""
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE raw.{table_name}"))
    logger.info("Truncated raw.%s", table_name)


def upsert_dataframe(
    df: pd.DataFrame,
    table_name: str,
    primary_key_columns: list[str],
    engine: Engine,
    schema: str = "raw",
) -> int:
    """
    Insert rows, updating existing rows on primary key conflict.

    This is what makes the pipeline idempotent: running ingestion twice
    with the same (or overlapping) data does not create duplicate rows or
    fail on a primary key violation - matching rows are simply updated.
    """
    if df.empty:
        logger.warning("Skipping upsert into %s.%s - DataFrame is empty", schema, table_name)
        return 0

    columns = list(df.columns)
    update_columns = [c for c in columns if c not in primary_key_columns]

    column_list = ", ".join(columns)
    placeholder_list = ", ".join(f":{c}" for c in columns)
    conflict_columns = ", ".join(primary_key_columns)
    update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_columns)

    if update_clause:
        update_clause += ", updated_at = now()" if "updated_at" in columns else ""

    stmt = text(
        f"""
        INSERT INTO {schema}.{table_name} ({column_list})
        VALUES ({placeholder_list})
        ON CONFLICT ({conflict_columns})
        DO UPDATE SET {update_clause if update_clause else conflict_columns.split(",")[0] + " = EXCLUDED." + conflict_columns.split(",")[0]}
        """
    )

    records = df.to_dict(orient="records")
    with engine.begin() as conn:
        for start in range(0, len(records), _INSERT_CHUNK_SIZE):
            batch = records[start : start + _INSERT_CHUNK_SIZE]
            conn.execute(stmt, batch)

    logger.info("Upserted %d rows into %s.%s", len(records), schema, table_name)
    return len(records)
