"""Create the Airflow metadata database if it does not already exist."""

import os
import time

import psycopg2
from psycopg2 import sql


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


host = env("AIRFLOW_DB_HOST")
port = int(env("AIRFLOW_DB_PORT", "5432"))
user = env("AIRFLOW_DB_USER")
password = env("AIRFLOW_DB_PASSWORD")
database = env("AIRFLOW_DB_NAME", "airflow")
maintenance_db = env("AIRFLOW_DB_MAINTENANCE_DB", "postgres")

last_error: Exception | None = None
for attempt in range(1, 31):
    try:
        with psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=maintenance_db,
        ) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
                exists = cur.fetchone() is not None
                if not exists:
                    cur.execute(sql.SQL("CREATE DATABASE {}" ).format(sql.Identifier(database)))
                    print(f"Created PostgreSQL database: {database}")
                else:
                    print(f"PostgreSQL database already exists: {database}")
        break
    except psycopg2.OperationalError as exc:
        last_error = exc
        print(f"Waiting for PostgreSQL ({attempt}/30): {exc}")
        time.sleep(2)
else:
    raise RuntimeError("Could not connect to PostgreSQL after 30 attempts") from last_error
