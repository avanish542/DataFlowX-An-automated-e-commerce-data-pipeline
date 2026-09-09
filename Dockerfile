# FROM python:3.12-slim

# WORKDIR /app

# # System deps needed by psycopg2 at build time
# RUN apt-get update \
#     && apt-get install -y --no-install-recommends gcc libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY src/ src/
# COPY scripts/ scripts/
# COPY db/ db/
# COPY pyproject.toml .

# RUN pip install --no-cache-dir -e .

# ENV PYTHONUNBUFFERED=1

# ENTRYPOINT ["python", "-m", "dataflowx.cli"]
# CMD ["--help"]

FROM python:3.12-slim

WORKDIR /app

# System dependencies needed by psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/
COPY db/ db/
COPY dashboard/ dashboard/
COPY dbt/ dbt/
COPY pyproject.toml .

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "streamlit run dashboard/app.py --server.address=0.0.0.0 --server.port=${PORT:-10000}"]