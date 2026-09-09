"""
PostgreSQL connection management.

One SQLAlchemy engine is created from settings.database and reused
everywhere. This is the only place that knows how to build a connection
string, so switching between a local PostgreSQL install and the Docker
Compose "postgres" service is purely a matter of editing .env.
"""

from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from dataflowx.config.settings import settings
from dataflowx.utils.logger import get_logger

logger = get_logger(__name__)

_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def get_engine() -> Engine:
    """Return a process-wide SQLAlchemy engine, creating it on first use."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database.sqlalchemy_url,
            pool_pre_ping=True,
            future=True,
        )
        logger.debug(
            "Created SQLAlchemy engine for %s:%s/%s",
            settings.database.host,
            settings.database.port,
            settings.database.name,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), future=True)
    return _SessionFactory


@contextmanager
def get_session() -> Iterator[Session]:
    """Context manager yielding a SQLAlchemy session with commit/rollback."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection() -> bool:
    """Return True if PostgreSQL is reachable with the current settings."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connection check failed: %s", exc)
        return False
