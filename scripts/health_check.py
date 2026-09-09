"""
Database health check.

Run this after setting up .env (and before running the pipeline) to
confirm PostgreSQL is reachable and the required schemas exist:

    python scripts/health_check.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text  # noqa: E402

from dataflowx.config.settings import settings  # noqa: E402
from dataflowx.database.connection import check_connection, get_engine  # noqa: E402

REQUIRED_SCHEMAS = ["raw", "staging", "warehouse", "analytics", "audit"]
REQUIRED_TABLES = [
    "raw.customers",
    "raw.stores",
    "raw.products",
    "raw.orders",
    "raw.order_items",
    "raw.payments",
    "audit.pipeline_runs",
    "audit.data_quality_results",
    "audit.rejected_records",
]


def main() -> int:
    print(f"Database:  {settings.database.name}")
    print(f"Host:      {settings.database.host}:{settings.database.port}")
    print(f"User:      {settings.database.user}")
    print("Password:  (hidden)")
    print()

    if not check_connection():
        print("Database connection: FAILED")
        print("Check that PostgreSQL is running and .env has the right credentials.")
        return 1

    print("Database connection: OK")

    engine = get_engine()
    with engine.connect() as conn:
        existing = {
            row[0]
            for row in conn.execute(
                text("SELECT schema_name FROM information_schema.schemata")
            )
        }

    missing = [s for s in REQUIRED_SCHEMAS if s not in existing]
    if missing:
        print(f"Required schemas: MISSING {missing}")
        print("Run: python -m dataflowx.cli init-db")
        return 1

    print(f"Required schemas: OK {REQUIRED_SCHEMAS}")

    with engine.connect() as conn:
        existing_tables = {
            f"{row.schema}.{row.table_name}"
            for row in conn.execute(
                text(
                    """
                    SELECT table_schema AS schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema IN ('raw', 'audit')
                    """
                )
            )
        }

    missing_tables = [table for table in REQUIRED_TABLES if table not in existing_tables]
    if missing_tables:
        print(f"Required tables: MISSING {missing_tables}")
        print("Run: python -m dataflowx.cli init-db")
        return 1

    print(f"Required tables: OK ({len(REQUIRED_TABLES)} checked)")
    print()
    print("Everything looks good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
