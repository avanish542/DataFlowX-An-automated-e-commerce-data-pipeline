"""
Business rule validation.

Each function takes a DataFrame and returns (valid_rows, invalid_rows,
reason). These are simple, composable checks used by the ingestion
service to split "good" rows from rows that should be rejected and
logged to audit.rejected_records instead of loaded into raw tables.
"""

import pandas as pd

CheckOutcome = tuple[pd.DataFrame, pd.DataFrame, str]

VALID_PAYMENT_STATUSES = {"success", "failed", "pending", "refunded"}
VALID_ORDER_STATUSES = {"placed", "shipped", "delivered", "cancelled", "returned"}


def check_positive_quantity(df: pd.DataFrame, column: str = "quantity") -> CheckOutcome:
    mask = df[column] > 0
    return df[mask], df[~mask], f"{column} must be greater than 0"


def check_non_negative(df: pd.DataFrame, column: str) -> CheckOutcome:
    mask = df[column] >= 0
    return df[mask], df[~mask], f"{column} must not be negative"


def check_accepted_values(df: pd.DataFrame, column: str, allowed: set[str]) -> CheckOutcome:
    mask = df[column].isin(allowed)
    return df[mask], df[~mask], f"{column} must be one of {sorted(allowed)}"


def check_valid_date(df: pd.DataFrame, column: str) -> CheckOutcome:
    parsed = pd.to_datetime(df[column], errors="coerce")
    mask = parsed.notna()
    return df[mask], df[~mask], f"{column} is not a valid date"


def check_no_duplicate_ids(df: pd.DataFrame, id_column: str) -> CheckOutcome:
    duplicate_mask = df.duplicated(subset=[id_column], keep="first")
    return df[~duplicate_mask], df[duplicate_mask], f"duplicate {id_column}"


def check_discount_not_exceed_line_value(
    df: pd.DataFrame,
    quantity_column: str = "quantity",
    unit_price_column: str = "unit_price",
    discount_column: str = "discount",
) -> CheckOutcome:
    """Reject discounts larger than the gross value of the line item."""
    mask = df[discount_column] <= df[quantity_column] * df[unit_price_column]
    return (
        df[mask],
        df[~mask],
        f"{discount_column} must not exceed {quantity_column} * {unit_price_column}",
    )
