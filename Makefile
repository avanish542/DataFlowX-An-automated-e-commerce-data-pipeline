.PHONY: install test lint format init-db health pipeline dashboard generate-data airflow-up airflow-down docker-db-up docker-db-down

install:
	pip install -r requirements.txt
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check src tests scripts airflow/dags
	black --check src tests scripts airflow/dags

format:
	black src tests scripts airflow/dags
	ruff check --fix src tests scripts airflow/dags

generate-data:
	python scripts/generate_data.py --scale sample

health:
	python scripts/health_check.py

init-db:
	python -m dataflowx.cli init-db

pipeline:
	python -m dataflowx.cli pipeline

dashboard:
	streamlit run dashboard/app.py

airflow-up:
	docker compose up -d airflow-init airflow-webserver airflow-scheduler

airflow-down:
	docker compose down

docker-db-up:
	docker compose --profile docker-db up -d postgres airflow-init airflow-webserver airflow-scheduler dashboard

docker-db-down:
	docker compose --profile docker-db down -v
