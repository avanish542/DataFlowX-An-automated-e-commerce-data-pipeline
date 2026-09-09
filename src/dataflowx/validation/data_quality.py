"""
Data quality framework.

Runs a set of SQL-based checks against tables already loaded into
PostgreSQL (typically the raw/bronze layer, but the same functions work
against staging or warehouse tables too). Each check writes its result to
audit.data_quality_results. Checks marked `critical=True` cause
run_quality_checks() to report failure, which the Airflow DAG uses to
stop the pipeline before bad data reaches the warehouse.
"""

from dataclasses import dataclass

from sqlalchemy import Engine, text

from dataflowx.database.queries import record_data_quality_result
from dataflowx.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QualityCheck:
    table_name: str
    check_name: str
    # SQL that returns the COUNT of rows that FAIL the check (0 = pass).
    failing_rows_sql: str
    critical: bool = True


# Checks run against the raw/bronze layer after ingestion.
RAW_LAYER_CHECKS: list[QualityCheck] = [
    QualityCheck(
        table_name="customers",
        check_name="no_duplicate_customer_id",
        failing_rows_sql="""
            SELECT COUNT(*) FROM (
                SELECT customer_id FROM raw.customers
                GROUP BY customer_id HAVING COUNT(*) > 1
            ) d
        """,
    ),
    QualityCheck(
        table_name="order_items",
        check_name="positive_quantity",
        failing_rows_sql="SELECT COUNT(*) FROM raw.order_items WHERE quantity <= 0",
    ),
    QualityCheck(
        table_name="order_items",
        check_name="non_negative_unit_price",
        failing_rows_sql="SELECT COUNT(*) FROM raw.order_items WHERE unit_price < 0",
    ),
    QualityCheck(
        table_name="order_items",
        check_name="non_negative_discount",
        failing_rows_sql="SELECT COUNT(*) FROM raw.order_items WHERE discount < 0",
    ),
    QualityCheck(
        table_name="order_items",
        check_name="discount_not_above_line_value",
        failing_rows_sql="""
            SELECT COUNT(*)
            FROM raw.order_items
            WHERE discount > quantity * unit_price
        """,
    ),
    QualityCheck(
        table_name="payments",
        check_name="valid_payment_status",
        failing_rows_sql="""
            SELECT COUNT(*) FROM raw.payments
            WHERE payment_status NOT IN ('success', 'failed', 'pending', 'refunded')
        """,
    ),
    QualityCheck(
        table_name="payments",
        check_name="non_negative_amount",
        failing_rows_sql="SELECT COUNT(*) FROM raw.payments WHERE amount < 0",
    ),
    QualityCheck(
        table_name="order_items",
        check_name="orphan_order_items",
        failing_rows_sql="""
            SELECT COUNT(*) FROM raw.order_items oi
            LEFT JOIN raw.orders o ON oi.order_id = o.order_id
            WHERE o.order_id IS NULL
        """,
        critical=False,  # worth knowing about, but shouldn't block the pipeline
    ),
    QualityCheck(
        table_name="orders",
        check_name="orphan_orders_missing_customer",
        failing_rows_sql="""
            SELECT COUNT(*) FROM raw.orders o
            LEFT JOIN raw.customers c ON o.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
        """,
        critical=False,
    ),
]


def run_quality_checks(
    checks: list[QualityCheck], pipeline_run_id: int, engine: Engine
) -> bool:
    """
    Run every check, record results to audit.data_quality_results, and
    return True only if all *critical* checks passed.
    """
    all_critical_passed = True

    with engine.connect() as conn:
        for check in checks:
            failed_rows = conn.execute(text(check.failing_rows_sql)).scalar_one()
            status = "pass" if failed_rows == 0 else ("fail" if check.critical else "warning")

            record_data_quality_result(
                pipeline_run_id=pipeline_run_id,
                table_name=check.table_name,
                check_name=check.check_name,
                status=status,
                failed_rows=failed_rows,
                engine=engine,
            )

            if status == "pass":
                logger.info("DQ check passed: %s.%s", check.table_name, check.check_name)
            elif status == "warning":
                logger.warning(
                    "DQ check warning: %s.%s (%d failing rows)",
                    check.table_name,
                    check.check_name,
                    failed_rows,
                )
            else:
                logger.error(
                    "DQ check FAILED: %s.%s (%d failing rows)",
                    check.table_name,
                    check.check_name,
                    failed_rows,
                )
                all_critical_passed = False

    return all_critical_passed
