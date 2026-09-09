"""
Type coercion and simple derived columns.

Applied after cleaning and before loading, so raw tables receive
consistent types even when the source CSV/JSON/API returns strings for
numbers or dates.
"""

import pandas as pd

from dataflowx.utils.logger import get_logger

logger = get_logger(__name__)


def coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert columns to numeric, turning unparsable values into NaN."""
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def coerce_dates(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert columns to dates, turning unparsable values into NaT."""
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df


def add_line_total(
    df: pd.DataFrame,
    quantity_col: str = "quantity",
    unit_price_col: str = "unit_price",
    discount_col: str = "discount",
    output_col: str = "line_total",
) -> pd.DataFrame:
    """Add a computed line-item total: quantity * unit_price - discount."""
    df = df.copy()
    discount = df[discount_col] if discount_col in df.columns else 0
    df[output_col] = (df[quantity_col] * df[unit_price_col]) - discount
    return df
