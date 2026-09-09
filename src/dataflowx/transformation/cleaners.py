"""
Data cleaning.

Small, composable pandas functions that standardize raw source data
before it is validated and loaded. These handle the "messy but not
technically invalid" problems: extra whitespace, inconsistent casing,
and exact duplicate rows.
"""

import pandas as pd

from dataflowx.utils.logger import get_logger

logger = get_logger(__name__)


def trim_whitespace(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Strip leading/trailing whitespace from text columns."""
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
    return df


def standardize_text_case(df: pd.DataFrame, columns: list[str], case: str = "title") -> pd.DataFrame:
    """Normalize casing for text columns (e.g. city names, statuses)."""
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            continue
        series = df[col].astype("string")
        if case == "title":
            df[col] = series.str.title()
        elif case == "lower":
            df[col] = series.str.lower()
        elif case == "upper":
            df[col] = series.str.upper()
    return df


def drop_exact_duplicates(df: pd.DataFrame, subset: list[str] | None = None) -> pd.DataFrame:
    """Drop exact duplicate rows and log how many were removed."""
    before = len(df)
    deduped = df.drop_duplicates(subset=subset, keep="first")
    removed = before - len(deduped)
    if removed:
        logger.info("Dropped %d duplicate row(s)", removed)
    return deduped


def normalize_emails(df: pd.DataFrame, column: str = "email") -> pd.DataFrame:
    """Lowercase and strip email addresses so 'A@x.com' and 'a@x.com' match."""
    df = df.copy()
    if column in df.columns:
        df[column] = df[column].astype("string").str.strip().str.lower()
    return df
