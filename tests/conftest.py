"""
Shared pytest fixtures.

Sets dummy required environment variables before any dataflowx module is
imported, so unit tests (which don't touch a real database) can run in
CI or on a fresh machine without a .env file. Tests that need a real
PostgreSQL connection are marked and skipped when one isn't reachable -
see tests/integration/test_pipeline.py.
"""

import os

os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "dataflowx_test")
os.environ.setdefault("DATABASE_USER", "postgres")
os.environ.setdefault("DATABASE_PASSWORD", "test")
