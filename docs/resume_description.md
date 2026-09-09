# Resume Description

## A. Project title

**DataFlowX - End-to-End E-Commerce Data Engineering Pipeline**

## B. Resume bullets

- Designed and implemented an end-to-end ETL/ELT pipeline using Python,
  PostgreSQL, Apache Airflow, and dbt to process e-commerce data through
  bronze, staging, and gold (star schema) layers.
- Built a data quality framework with schema validation, business-rule
  checks, and SQL-based quality checks, logging every rejected record and
  quality check result to dedicated audit tables instead of dropping bad
  data silently.
- Modeled a star schema (`fact_sales` + 4 dimension tables) in dbt with
  documented grain, surrogate keys, and 20+ dbt tests (`not_null`,
  `unique`, `relationships`, `accepted_values`, plus 3 custom SQL tests).
- Implemented idempotent, upsert-based loading and a watermark-tracking
  audit trail (`audit.pipeline_runs`) so the pipeline can be safely
  re-run without creating duplicate records.
- Containerized the full stack (PostgreSQL, Airflow, Streamlit dashboard)
  with Docker Compose and set up GitHub Actions CI to lint, test, and
  validate the dbt build on every push.

## C. Technology stack

Python, SQL, PostgreSQL, Apache Airflow, dbt Core, Docker & Docker
Compose, pandas, pytest, Streamlit, GitHub Actions, Ruff, Black.

## D. Short project explanation

DataFlowX is a batch data pipeline that ingests e-commerce data from
CSV, JSON, and a REST API, validates and cleans it in Python, loads it
into a PostgreSQL bronze layer, transforms it with dbt into a star
schema, and serves the result through SQL analytics and a Streamlit
dashboard - orchestrated end to end by Apache Airflow.

## E. Architecture explanation

Source files/API -> Python ingestion (validation + cleaning) -> `raw`
schema (bronze) -> dbt staging models -> data quality checks -> dbt
marts (star schema, `warehouse` schema / gold) -> SQL analytics and
dashboard. See `docs/architecture.md` for diagrams.

## F. Engineering concepts demonstrated

ETL/ELT, batch processing, idempotency (upsert + unique constraints),
data validation and data quality frameworks, rejected-record handling,
dimensional modeling (star schema, fact/dimension tables, surrogate vs.
natural keys), SQL indexing, pipeline retries and failure handling,
centralized logging, environment-based configuration, unit + integration
testing, containerization, and CI/CD.

## G. Interview explanation

"I built a pipeline that pulls e-commerce data from three source types,
validates it before it ever reaches the database, models it into a star
schema with dbt, and tracks every pipeline run and rejected record in
audit tables so I can answer 'what happened last night' without digging
through logs. It's orchestrated with Airflow, containerized with Docker,
and has a CI pipeline that runs tests and a dbt build on every push."

Note: figures like "processes 50,000+ orders" describe the scale the
synthetic data generator (`scripts/generate_data.py --scale full`) is
designed to produce, not a claim about production traffic - this is a
portfolio project, not a live system with real users.
