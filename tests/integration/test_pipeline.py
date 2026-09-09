"""
Integration tests.

These need a real PostgreSQL database (schemas created via
`python -m dataflowx.cli init-db`). They are skipped automatically if the
database isn't reachable, so `pytest` still passes in environments
without PostgreSQL (e.g. a laptop with no local Docker running) - but
they should be run before considering the pipeline "done" on a machine
that does have PostgreSQL available.
"""

from datetime import datetime, timezone

import pandas as pd
import pytest

from dataflowx.database.connection import check_connection, get_engine
from dataflowx.database.loaders import upsert_dataframe
from dataflowx.database.queries import (
    finish_pipeline_run,
    get_last_successful_watermark,
    start_pipeline_run,
)

requires_db = pytest.mark.skipif(
    not check_connection(), reason="PostgreSQL is not reachable with current .env settings"
)


@requires_db
def test_database_connection_succeeds():
    assert check_connection() is True


@requires_db
def test_upsert_dataframe_is_idempotent():
    engine = get_engine()
    df = pd.DataFrame(
        {
            "customer_id": [999001],
            "first_name": ["Test"],
            "last_name": ["User"],
            "email": ["test.user@example.com"],
            "phone": [None],
            "city": [None],
            "state": [None],
            "country": [None],
            "signup_date": ["2024-01-01"],
        }
    )

    # Running the same upsert twice should not raise and should not
    # create a second row for the same customer_id.
    upsert_dataframe(df, "customers", ["customer_id"], engine)
    upsert_dataframe(df, "customers", ["customer_id"], engine)

    with engine.connect() as conn:
        count = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM raw.customers WHERE customer_id = 999001"
        ).scalar_one()

    assert count == 1

    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM raw.customers WHERE customer_id = 999001")


@requires_db
def test_pipeline_run_lifecycle_and_watermark():
    engine = get_engine()

    run_id = start_pipeline_run("test-pipeline", None, engine)
    assert run_id is not None

    watermark_before = get_last_successful_watermark("test-pipeline", engine)

    finish_pipeline_run(
        run_id,
        engine,
        status="success",
        records_processed=10,
        watermark_end=datetime.now(timezone.utc),
    )

    watermark_after = get_last_successful_watermark("test-pipeline", engine)
    assert watermark_after is not None
    assert watermark_after != watermark_before
