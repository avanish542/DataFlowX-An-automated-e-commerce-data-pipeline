"""
Centralized logging configuration.

Every module gets a logger via `get_logger(__name__)` instead of calling
print(). Log format includes timestamp, level and the originating module
so pipeline runs can be traced through logs/pipeline.log.
"""

import logging
import sys
from pathlib import Path

from dataflowx.config.settings import settings

LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
LOG_FILE = LOG_DIR / "pipeline.log"

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def _configure_root_logger() -> None:
    global _configured
    if _configured:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger("dataflowx")
    root.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger, e.g. get_logger(__name__)."""
    _configure_root_logger()
    # __name__ inside the package is already "dataflowx.xxx.yyy", so only
    # add the "dataflowx." prefix if the caller didn't already have it.
    logger_name = name if name.startswith("dataflowx") else f"dataflowx.{name}"
    return logging.getLogger(logger_name)
