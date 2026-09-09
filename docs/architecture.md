# Architecture

DataFlowX is a batch pipeline that moves e-commerce data through four
layers - bronze (raw), staging, gold (warehouse), and analytics - and
exposes the result through SQL and a Streamlit dashboard.

## 1. High-level architecture

```mermaid
graph LR
    A[CSV / JSON / REST API] --> B[Python Ingestion<br/>src/dataflowx/ingestion]
    B --> C[(raw schema<br/>bronze)]
    C --> D[dbt staging models]
    D --> E[Data Quality Checks]
    E --> F[dbt marts<br/>star schema]
    F --> G[(warehouse schema<br/>gold)]
    G --> H[SQL Analytics]
    G --> I[Streamlit Dashboard]
```

## 2. Data pipeline (bronze -> silver -> gold)

```mermaid
graph TD
    subgraph Sources
        S1[customers.csv]
        S2[stores.csv]
        S3[products - REST API]
        S4[orders.csv]
        S5[order_items.csv]
        S6[payments.json]
    end

    S1 & S2 & S3 & S4 & S5 & S6 --> V[Validate: schema + business rules]
    V -->|valid rows| RAW[(raw.* bronze tables)]
    V -->|invalid rows| REJ[(audit.rejected_records)]

    RAW --> STG[dbt staging models<br/>staging schema]
    STG --> DQ{Data Quality Checks<br/>audit.data_quality_results}
    DQ -->|critical failure| STOP[Pipeline stops]
    DQ -->|pass / warning| MARTS[dbt marts<br/>warehouse schema]
    MARTS --> GOLD[(warehouse.dim_* / fact_sales)]
```

## 3. Airflow DAG

```mermaid
graph TD
    A[check_source_files] --> B[start_run]
    B --> C[ingest_to_raw]
    C --> D[run_quality_checks]
    D --> E[run_dbt_staging]
    E --> F[run_dbt_marts]
    F --> G[warehouse_validation<br/>dbt test]
    G --> H[update_pipeline_metadata]
```

`ingest_to_raw` covers extract, validate, and load together rather than
as three separate Airflow tasks - see the docstring in
`airflow/dags/ecommerce_pipeline.py` for why (passing bulk DataFrames
through XCom is an anti-pattern).

## 4. Star schema

```mermaid
erDiagram
    dim_customer ||--o{ fact_sales : "customer_key"
    dim_product  ||--o{ fact_sales : "product_key"
    dim_store    ||--o{ fact_sales : "store_key"
    dim_date     ||--o{ fact_sales : "date_key"

    dim_customer {
        bigint customer_key PK
        bigint customer_id
        text first_name
        text last_name
        text email
    }
    dim_product {
        bigint product_key PK
        bigint product_id
        text product_name
        text category
        numeric price
    }
    dim_store {
        bigint store_key PK
        bigint store_id
        text store_name
    }
    dim_date {
        int date_key PK
        date full_date
        int year
        int month
    }
    fact_sales {
        bigint sale_id PK
        bigint order_id
        bigint order_item_id
        bigint customer_key FK
        bigint product_key FK
        bigint store_key FK
        int date_key FK
        int quantity
        numeric total_amount
        text payment_status
    }
```

## 5. Data lineage

```mermaid
graph LR
    raw.customers --> stg_customers --> dim_customer --> fact_sales
    raw.products --> stg_products --> dim_product --> fact_sales
    raw.stores --> stg_stores --> dim_store --> fact_sales
    raw.orders --> stg_orders --> int_order_metrics --> fact_sales
    raw.order_items --> stg_order_items --> int_order_metrics
    raw.payments --> stg_payments --> fact_sales
    fact_sales --> dashboard[Streamlit Dashboard]
    fact_sales --> sql_analytics[sql/analytics/*.sql]
```

## Why this stack

- **PostgreSQL** - one database plays the role of raw/staging/warehouse
  storage, which is enough at this data volume and keeps the project
  approachable.
- **Airflow** - orchestrates dependencies, retries, and scheduling; the
  DAG stays thin and calls into `src/dataflowx`.
- **dbt** - SQL transformations (staging -> marts) are declarative,
  testable, and version-controlled, which is easier to reason about than
  ad-hoc Python-generated SQL for this kind of transformation.
- **Docker Compose** - reproducible local environment; not required if
  you already have PostgreSQL and just want to run the Python pipeline.
