# DataFlowX

An end-to-end e-commerce data pipeline that ingests data from CSV, JSON
and a REST API, validates it, loads it into PostgreSQL, transforms it
with dbt into a star schema, and serves it through SQL analytics and a
Streamlit dashboard - orchestrated by Apache Airflow.

Built as a portfolio project for Associate/Junior Data Engineer roles.
See `docs/interview_guide.md` and `docs/resume_description.md` if you're
evaluating this as a candidate submission.

## 1. Project Overview

DataFlowX processes customers, products, stores, orders, order items and
payments through bronze (raw), staging, and gold (warehouse) layers,
with data quality checks and audit logging at each stage.

## 2. Business Problem

Answer standard e-commerce questions - total/daily/monthly revenue, top
products, top customers, average order value, payment success rate,
repeat customer rate, and more - from clean, analytics-ready data rather
than ad hoc queries against raw source files.

## 3. Architecture

```
CSV / JSON / REST API
        |
        v
Python Ingestion (validate + clean)
        |
        v
PostgreSQL raw schema (bronze)
        |
        v
dbt staging models
        |
        v
Data Quality Checks
        |
        v
dbt marts (star schema) -> warehouse schema (gold)
        |
        +--> SQL Analytics (sql/analytics/*.sql)
        +--> Streamlit Dashboard
```

Full diagrams (data lineage, DAG, star schema ERD) are in
`docs/architecture.md`.

## 4. Technology Stack

Python 3.12, PostgreSQL, pandas, Apache Airflow, dbt Core, Docker &
Docker Compose, Streamlit, pytest, Ruff, Black, GitHub Actions.

## 5. Features

- CSV, JSON, and REST API ingestion with retry/backoff and pagination
- Schema and business-rule validation, with rejected rows preserved
  (not dropped) in an audit table
- SQL-based data quality framework with critical/warning severities
- Star schema warehouse built with dbt, with dbt tests and custom SQL
  tests
- Idempotent, upsert-based loading (safe to re-run)
- Watermark-based pipeline run tracking (with full-read/upsert source ingestion)
- Airflow DAG orchestration
- Streamlit dashboard on the gold layer
- Dockerized Airflow + dashboard with optional PostgreSQL; local PostgreSQL is supported without a port conflict
- CI (lint, tests, dbt build) via GitHub Actions

## 6. Folder Structure

```
dataflowx/
├── airflow/dags/          Airflow DAG
├── data/raw/               Source files (generated, not committed)
├── db/init/                 PostgreSQL schema + table DDL
├── src/dataflowx/            Python package: ingestion, validation,
│                             transformation, database, CLI
├── dbt/                       dbt project: staging, intermediate, marts, tests
├── sql/analytics/               Ad hoc analytical SQL
├── dashboard/                    Streamlit app
├── tests/                         pytest unit + integration tests
├── scripts/                        generate_data.py, health_check.py
├── docs/                            This documentation set
├── docker-compose.yml / Dockerfile   Containerization
└── .github/workflows/                 CI
```

See the full listing with `tree -L 3` or open the repo in your editor -
every folder here has a real purpose (no filler directories).

## 7. Data Flow

Source -> ingestion (extract + validate + clean) -> `raw` (bronze) ->
dbt staging -> data quality checks -> dbt marts -> `warehouse` (gold) ->
SQL/dashboard. Details in `docs/pipeline.md`.

## 8. Database Design

Five PostgreSQL schemas (`raw`, `staging`, `warehouse`, `analytics`,
`audit`), proper types/constraints/indexes throughout. Full explanation
in `docs/database_design.md`, column-level detail in
`docs/data_dictionary.md`.

## 9. Star Schema

`warehouse.fact_sales` (grain: one row per order line item) with four
dimensions: `dim_customer`, `dim_product`, `dim_store`, `dim_date`. See
`docs/database_design.md` and the ERD in `docs/architecture.md`.

## 10. ETL Pipeline

Implemented in `src/dataflowx/` (ingestion, validation, transformation,
database) and `dbt/` (staging -> marts). See `docs/pipeline.md` for full
vs. incremental loading and idempotency.

## 11. Airflow

DAG at `airflow/dags/ecommerce_pipeline.py`:
`check_source_files -> start_run -> ingest_to_raw -> run_quality_checks
-> run_dbt_staging -> run_dbt_marts -> warehouse_validation ->
update_pipeline_metadata`. Runs `@daily` with retries and a 30-minute
execution timeout per task.

## 12. dbt

`dbt/models/staging` (1:1 with `raw`), `dbt/models/intermediate`
(order/customer rollups), and `dbt/models/marts` (the star schema).
The repository-local `dbt/profiles.yml` reads credentials from `.env`, so
no profile-copy step is required. `dbt test` runs schema tests plus two
custom tests in `dbt/tests/`.

## 13. Data Quality

Two layers: Python validation before loading, SQL/dbt checks after.
Full detail and the exact check list in `docs/data_quality.md`.

## 14. Incremental Loading

Watermark tracking is implemented (`audit.pipeline_runs`), and loading
is idempotent via upserts. See `docs/pipeline.md` for what's implemented
vs. what's a documented future enhancement.

## 15. Testing

```
pytest -v
```

Unit tests (`tests/unit/`) cover ingestion, validation, and
transformation logic with no database required. Integration tests
(`tests/integration/`) need PostgreSQL and auto-skip if it isn't
reachable.

## 16. Docker

The default Compose setup uses your existing PostgreSQL and starts Airflow + the dashboard:

```powershell
docker compose up -d airflow-init airflow-webserver airflow-scheduler dashboard
```

It does not start another PostgreSQL container, so it will not compete for port 5432.

If you want PostgreSQL inside Docker instead, set `DOCKER_DATABASE_HOST=postgres`
and `AIRFLOW_DB_HOST=postgres` in `.env`, then use the optional profile:

```powershell
docker compose --profile docker-db up -d postgres airflow-init airflow-webserver airflow-scheduler dashboard
```

See `docs/deployment.md` for the two modes.

## 17. PostgreSQL Setup

The recommended setup uses your existing local PostgreSQL installation.
Create the `dataflowx` database, configure `.env`, then run `init-db`.
Airflow uses a separate `airflow` database only for its metadata.
See `docs/deployment.md` for the optional all-Docker mode.

```sql
CREATE DATABASE dataflowx;
```

```
cp .env.example .env    # then fill in your credentials
python -m dataflowx.cli init-db
python scripts/health_check.py
```

## 18. Environment Variables

All credentials live in `.env` (never committed). Python/dbt use `DATABASE_*`.
Docker uses `DOCKER_DATABASE_HOST` to reach the host PostgreSQL, and Airflow
uses its separate `AIRFLOW_DB_*` settings.

## 19. Running the Pipeline

```bash
pip install -r requirements.txt
pip install -e .

# PowerShell: Copy-Item .env.example .env, then fill in your credentials
python -m dataflowx.cli init-db
python scripts/generate_data.py --scale sample

python -m dataflowx.cli pipeline     # ingest -> quality -> dbt run -> dbt test
```

Or step by step: `ingest`, `validate`, `quality`, `transform` (see
`python -m dataflowx.cli --help`).

## 20. Dashboard

```
streamlit run dashboard/app.py
```

Reads from `warehouse.*` only - run the pipeline at least once first.

## 21. Example SQL

```sql
-- Top 10 products by revenue
select p.product_name, sum(f.total_amount) as revenue
from warehouse.fact_sales f
join warehouse.dim_product p on f.product_key = p.product_key
group by p.product_name
order by revenue desc
limit 10;
```

More in `sql/analytics/`.

## 22. Troubleshooting

| Problem | Likely cause / fix |
|---|---|
| `RuntimeError: Missing required environment variable` | `.env` doesn't exist or is missing a value - copy `.env.example` to `.env` |
| `python scripts/health_check.py` fails to connect | PostgreSQL isn't running, or `DATABASE_HOST`/port/credentials are wrong |
| `init-db` runs but schemas are missing | Check you're pointed at the right database (`DATABASE_NAME`) |
| `dbt run` fails with a connection error | Run `dbt debug --project-dir dbt --profiles-dir dbt` and verify the `DATABASE_*` values in `.env` |
| Airflow containers can't reach your local Postgres | Set `DOCKER_DATABASE_HOST=host.docker.internal` and `AIRFLOW_DB_HOST=host.docker.internal`; also create the separate `airflow` database |
| `pytest` integration tests all skip | Expected if PostgreSQL isn't reachable - unit tests still run |

## 23. Future Enhancements

Explicitly **not** implemented (see `docs/deployment.md` for detail):
cloud deployment (AWS/Azure/GCP), streaming/real-time processing, a
distributed processing engine (Spark), SCD Type 2 dimension history, and
automatic reprocessing of rejected records. These are natural next steps
but are out of scope for this project's goals.

---

For a component-by-component breakdown suitable for an interview
walkthrough, see `docs/interview_guide.md`.
