# Deployment and local setup

DataFlowX is designed to use an existing local PostgreSQL installation by default. Docker is used for Airflow and the dashboard, but PostgreSQL does not have to run in Docker.

## 1. Recommended setup: local PostgreSQL + local Python

1. Start PostgreSQL.
2. Create the two databases used by the project:

```sql
CREATE DATABASE dataflowx;
CREATE DATABASE airflow;
```

`dataflowx` stores application/raw/warehouse/audit data. `airflow` stores only Airflow metadata.

3. Copy `.env.example` to `.env` and set your PostgreSQL password. On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

4. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ".[dev]"
```

5. Initialize DataFlowX:

```powershell
python -m dataflowx.cli init-db
python scripts/health_check.py
```

6. Generate demo data:

```powershell
python scripts/generate_data.py --scale sample
```

7. Run the complete pipeline:

```powershell
python -m dataflowx.cli pipeline
```

The product API is attempted first and automatically falls back to `data/raw/products.csv` when the API is unavailable. This keeps local/CI runs reproducible even without network access.

## 2. Run individual pipeline stages

```powershell
python -m dataflowx.cli validate
python -m dataflowx.cli ingest
python -m dataflowx.cli quality
python -m dataflowx.cli transform
```

For dbt directly:

```powershell
dbt debug --project-dir dbt --profiles-dir dbt
dbt build --project-dir dbt --profiles-dir dbt
```

The repository-local `dbt/profiles.yml` contains no credentials; it reads the `DATABASE_*` environment variables.

## 3. Run the Streamlit dashboard locally

```powershell
streamlit run dashboard/app.py
```

Open `http://localhost:8501`. The dashboard reads from `warehouse.*` only, so run the pipeline at least once first.

## 4. Run Airflow in Docker while keeping your local PostgreSQL

The default Compose file is deliberately configured for this setup.

Start the services:

```powershell
docker compose up -d airflow-init airflow-webserver airflow-scheduler dashboard
```

Open:

- Airflow: `http://localhost:8080`
- Dashboard: `http://localhost:8501`

Airflow connects to the separate `airflow` database. The DAG's DataFlowX tasks connect to the `dataflowx` database.

On Windows/macOS, `host.docker.internal` lets containers reach PostgreSQL on the host. The Compose file also adds the Docker host-gateway mapping for Linux.

The example `.env` uses `admin` / `admin` for the local Airflow account. Change these values before sharing the project.

## 5. Optional: run PostgreSQL in Docker too

If you want a completely containerized local environment:

```powershell
docker compose --profile docker-db up -d postgres airflow-init airflow-webserver airflow-scheduler dashboard
```

This starts PostgreSQL 16 and creates the `dataflowx` and `airflow` databases automatically. The same Python code and dbt project are used; only connection settings change through Compose environment overrides.

To remove the disposable Docker database volume:

```powershell
docker compose --profile docker-db down -v
```

## 6. CI

GitHub Actions starts a temporary PostgreSQL service and injects test credentials through environment variables. No local `.env` or database password is committed.

## 7. Production/cloud direction

Cloud deployment is intentionally not implemented. A production extension could move PostgreSQL to a managed service, object storage to a cloud landing zone, and Airflow to a managed/container platform. Those should be described as future work unless actually deployed.
