"""
Central place for reading configuration from environment variables.

Every other module in the project should import `settings` from here
instead of calling os.getenv() directly. This keeps configuration in one
place and makes it possible to switch between a local PostgreSQL install
and the Dockerized one purely through the .env file.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL

# Load .env from the project root if present. In CI / Docker, real
# environment variables are usually injected directly and this is a no-op.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def _get_required(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill in your values."
        )
    return value


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str

    @property
    def sqlalchemy_url(self) -> URL:
        # URL.create handles passwords containing characters such as @, :, /,
        # or # without requiring callers to URL-encode secrets manually.
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.name,
        )


@dataclass(frozen=True)
class Settings:
    database: DatabaseSettings
    log_level: str
    raw_data_dir: Path
    products_api_base_url: str
    products_api_timeout_seconds: int


def load_settings() -> Settings:
    """Build a Settings object from the current environment."""
    database = DatabaseSettings(
        host=_get_required("DATABASE_HOST"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        name=_get_required("DATABASE_NAME"),
        user=_get_required("DATABASE_USER"),
        password=_get_required("DATABASE_PASSWORD"),
    )
    raw_data_dir = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
    if not raw_data_dir.is_absolute():
        raw_data_dir = PROJECT_ROOT / raw_data_dir

    return Settings(
        database=database,
        log_level=os.getenv("LOG_LEVEL", "info"),
        raw_data_dir=raw_data_dir,
        products_api_base_url=os.getenv(
            "PRODUCTS_API_BASE_URL", "https://fakestoreapi.com"
        ),
        products_api_timeout_seconds=int(
            os.getenv("PRODUCTS_API_TIMEOUT_SECONDS", "10")
        ),
    )


# Loaded lazily on first import of this module by callers.
settings = load_settings()
