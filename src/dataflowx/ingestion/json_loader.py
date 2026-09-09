"""
JSON ingestion.

Reads a raw JSON file (a list of records, or {"data": [...]}) into a
pandas DataFrame. Mirrors csv_loader.py so both source types are handled
the same way downstream.
"""

import json
from pathlib import Path

import pandas as pd

from dataflowx.utils.logger import get_logger

logger = get_logger(__name__)


class JsonFileNotFoundError(FileNotFoundError):
    """Raised when the expected source JSON file does not exist."""


class JsonLoadError(RuntimeError):
    """Raised when a JSON file exists but cannot be parsed into records."""


def load_json(file_path: Path, required_columns: list[str] | None = None) -> pd.DataFrame:
    """
    Load a JSON file into a DataFrame.

    Accepts either a top-level list of objects, or an object with a
    "data" key containing that list (a common REST API export shape).
    """
    if not file_path.exists():
        raise JsonFileNotFoundError(f"JSON file not found: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise JsonLoadError(f"Could not parse JSON file {file_path}: {exc}") from exc

    if isinstance(raw, dict) and "data" in raw:
        records = raw["data"]
    elif isinstance(raw, list):
        records = raw
    else:
        raise JsonLoadError(
            f"JSON file {file_path} must be a list of records or an object with a 'data' key"
        )

    if not records:
        raise JsonLoadError(f"JSON file {file_path} contains no records")

    df = pd.DataFrame(records)

    if required_columns:
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise JsonLoadError(
                f"JSON file {file_path} is missing required columns: {sorted(missing)}"
            )

    logger.info("Loaded %d rows from %s", len(df), file_path.name)
    return df
