FROM apache/airflow:2.9.3-python3.12

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow
RUN mkdir -p /opt/airflow/dbt-profile

COPY requirements.txt /tmp/dataflowx-requirements.txt
RUN pip install --no-cache-dir -r /tmp/dataflowx-requirements.txt

# Install the dataflowx package itself so DAGs can import dataflowx.
COPY pyproject.toml /opt/dataflowx/pyproject.toml
COPY src/ /opt/dataflowx/src/
RUN pip install --no-cache-dir -e /opt/dataflowx

COPY docker/airflow/init_airflow_db.py /opt/airflow/init_airflow_db.py
COPY docker/airflow/entrypoint.sh /opt/airflow/dataflowx-entrypoint.sh
RUN chmod +x /opt/airflow/dataflowx-entrypoint.sh

ENTRYPOINT ["/opt/airflow/dataflowx-entrypoint.sh"]
