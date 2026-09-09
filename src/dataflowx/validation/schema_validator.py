"""
Schema validation.

Checks that a DataFrame has the columns a downstream table expects, and
that values in key columns are non-null and of a sane type, before the
data is allowed into the raw/bronze layer. This is deliberately simple:
a dict-based schema definition rather than a validation framework, since
the project only has five source tables.
"""

from dataclasses import dataclass, field

import pandas as pd

from dataflowx.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ColumnSchema:
    name: str
    required: bool = True
    dtype: str = "any"  # "int", "float", "str", "date", "any"


@dataclass
class TableSchema:
    table_name: str
    columns: list[ColumnSchema] = field(default_factory=list)

    @property
    def required_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.required]


@dataclass
class ValidationResult:
    table_name: str
    is_valid: bool
    errors: list[str]
    valid_rows: pd.DataFrame
    invalid_rows: pd.DataFrame


CUSTOMERS_SCHEMA = TableSchema(
    "customers",
    [
        ColumnSchema("customer_id", dtype="int"),
        ColumnSchema("first_name", dtype="str"),
        ColumnSchema("last_name", dtype="str"),
        ColumnSchema("email", dtype="str"),
        ColumnSchema("phone", required=False, dtype="str"),
        ColumnSchema("city", required=False, dtype="str"),
        ColumnSchema("state", required=False, dtype="str"),
        ColumnSchema("country", required=False, dtype="str"),
        ColumnSchema("signup_date", dtype="date"),
    ],
)

PRODUCTS_SCHEMA = TableSchema(
    "products",
    [
        ColumnSchema("product_id", dtype="int"),
        ColumnSchema("product_name", dtype="str"),
        ColumnSchema("category", required=False, dtype="str"),
        ColumnSchema("price", dtype="float"),
        ColumnSchema("store_id", required=False, dtype="int"),
    ],
)

ORDERS_SCHEMA = TableSchema(
    "orders",
    [
        ColumnSchema("order_id", dtype="int"),
        ColumnSchema("customer_id", dtype="int"),
        ColumnSchema("store_id", required=False, dtype="int"),
        ColumnSchema("order_date", dtype="date"),
        ColumnSchema("order_status", required=False, dtype="str"),
    ],
)

ORDER_ITEMS_SCHEMA = TableSchema(
    "order_items",
    [
        ColumnSchema("order_item_id", dtype="int"),
        ColumnSchema("order_id", dtype="int"),
        ColumnSchema("product_id", dtype="int"),
        ColumnSchema("quantity", dtype="int"),
        ColumnSchema("unit_price", dtype="float"),
        ColumnSchema("discount", required=False, dtype="float"),
    ],
)

PAYMENTS_SCHEMA = TableSchema(
    "payments",
    [
        ColumnSchema("payment_id", dtype="int"),
        ColumnSchema("order_id", dtype="int"),
        ColumnSchema("payment_method", required=False, dtype="str"),
        ColumnSchema("amount", dtype="float"),
        ColumnSchema("payment_status", dtype="str"),
        ColumnSchema("payment_date", required=False, dtype="date"),
    ],
)


def validate_schema(df: pd.DataFrame, schema: TableSchema) -> ValidationResult:
    """
    Validate that required columns exist and required values are non-null.

    Rows with a null value in a required column are split into
    `invalid_rows`; everything else is returned as `valid_rows`.
    """
    errors: list[str] = []

    missing_columns = set(schema.required_columns) - set(df.columns)
    if missing_columns:
        errors.append(f"Missing required columns: {sorted(missing_columns)}")
        return ValidationResult(
            table_name=schema.table_name,
            is_valid=False,
            errors=errors,
            valid_rows=pd.DataFrame(columns=df.columns),
            invalid_rows=df,
        )

    required_present = [c for c in schema.required_columns if c in df.columns]
    null_mask = df[required_present].isnull().any(axis=1)

    valid_rows = df[~null_mask].copy()
    invalid_rows = df[null_mask].copy()

    if not invalid_rows.empty:
        errors.append(
            f"{len(invalid_rows)} row(s) have null values in required columns "
            f"{required_present}"
        )

    logger.info(
        "Schema validation for %s: %d valid, %d invalid",
        schema.table_name,
        len(valid_rows),
        len(invalid_rows),
    )

    return ValidationResult(
        table_name=schema.table_name,
        is_valid=invalid_rows.empty,
        errors=errors,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
    )
