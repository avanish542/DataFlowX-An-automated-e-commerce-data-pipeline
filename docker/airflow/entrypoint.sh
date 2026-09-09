#!/bin/bash
set -euo pipefail

python - <<'PY'
import os
from pathlib import Path
from urllib.parse import quote_plus

# Airflow's SQLAlchemy URL must encode credentials that contain URL-reserved
# characters. This keeps the user's normal PostgreSQL password valid.
os.environ["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"] = (
    f"postgresql+psycopg2://{quote_plus(os.environ['AIRFLOW_DB_USER'])}:"
    f"{quote_plus(os.environ['AIRFLOW_DB_PASSWORD'])}@"
    f"{os.environ['AIRFLOW_DB_HOST']}:{os.environ.get('AIRFLOW_DB_PORT', '5432')}/"
    f"{os.environ['AIRFLOW_DB_NAME']}"
)

profile_dir = Path(os.environ.get("DBT_PROFILES_DIR", "/opt/airflow/dbt-profile"))
profile_dir.mkdir(parents=True, exist_ok=True)
profile = f"""dataflowx:
  target: dev
  outputs:
    dev:
      type: postgres
      host: {os.environ['DATABASE_HOST']}
      port: {os.environ.get('DATABASE_PORT', '5432')}
      user: {os.environ['DATABASE_USER']}
      password: {os.environ['DATABASE_PASSWORD']}
      dbname: {os.environ['DATABASE_NAME']}
      schema: staging
      threads: 4
"""
(profile_dir / "profiles.yml").write_text(profile)
PY

exec /entrypoint "$@"
