"""
CSV ingestion.

Reads a raw CSV file from disk into a pandas DataFrame. This module only
handles *reading* the file - schema validation and data cleaning happen
later in the validation and transformation layers. Keeping this narrow
makes it easy to unit test and easy to reason about.
"""

from pathlib import Path

import pandas as pd

from dataflowx.utils.logger import get_logger

logger = get_logger(__name__)


class CsvFileNotFoundError(FileNotFoundError):
    """Raised when the expected source CSV file does not exist."""


class CsvLoadError(RuntimeError):
    """Raised when a CSV file exists but cannot be parsed."""


def load_csv(file_path: Path, required_columns: list[str] | None = None) -> pd.DataFrame:
    """
    Load a CSV file into a DataFrame.

    Args:
        file_path: path to the CSV file.
        required_columns: if given, raises CsvLoadError when any of these
            columns are missing from the file.

    Returns:
        The loaded DataFrame.
    """
    if not file_path.exists():
        raise CsvFileNotFoundError(f"CSV file not found: {file_path}")

    try:
        df = pd.read_csv(file_path)
    except pd.errors.ParserError as exc:
        raise CsvLoadError(f"Could not parse CSV file {file_path}: {exc}") from exc
    except pd.errors.EmptyDataError as exc:
        raise CsvLoadError(f"CSV file is empty: {file_path}") from exc

    if required_columns:
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise CsvLoadError(
                f"CSV file {file_path} is missing required columns: {sorted(missing)}"
            )

    logger.info("Loaded %d rows from %s", len(df), file_path.name)
    return df
