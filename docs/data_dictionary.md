# Data Dictionary

Covers the tables a developer or analyst is most likely to query. Full
DDL is in `db/init/03_tables.sql` and `dbt/models/marts/*.sql`.

## raw.customers (bronze)

| column | type | nullable | key | description | example |
|---|---|---|---|---|---|
| customer_id | BIGINT | no | PK | Natural key from source | 10023 |
| first_name | TEXT | no | | Customer's first name | Ananya |
| last_name | TEXT | no | | Customer's last name | Iyer |
| email | TEXT | no | | Lowercased, trimmed on ingest | ananya@example.com |
| phone | TEXT | yes | | Contact number | +91-9812345678 |
| city / state / country | TEXT | yes | | Address fields | Bengaluru / Karnataka / India |
| signup_date | DATE | yes | | Date the customer signed up | 2024-03-12 |
| created_at / updated_at | TIMESTAMPTZ | no | | Row bookkeeping (upsert-managed) | 2026-09-08 10:00:00+00 |

## raw.order_items (bronze)

| column | type | nullable | key | description | example |
|---|---|---|---|---|---|
| order_item_id | BIGINT | no | PK | Natural key from source | 500213 |
| order_id | BIGINT | no | FK -> raw.orders | Parent order | 88213 |
| product_id | BIGINT | no | FK -> raw.products | Product sold | 4021 |
| quantity | INTEGER | no | | Units purchased, must be > 0 | 2 |
| unit_price | NUMERIC(12,2) | no | | Price per unit at time of sale | 499.00 |
| discount | NUMERIC(12,2) | no | | Discount applied to the line | 25.00 |

## warehouse.fact_sales (gold)

Grain: **one row per product line item within one order** (one row of
`raw.order_items`, enriched with dimension keys).

| column | type | nullable | key | description | example |
|---|---|---|---|---|---|
| sale_id | BIGSERIAL | no | PK | Surrogate key | 1 |
| order_id | BIGINT | no | natural key | Source order id | 88213 |
| order_item_id | BIGINT | no | natural key | Source line item id | 500213 |
| customer_key | BIGINT | no | FK -> dim_customer | Surrogate key of the buyer | 305 |
| product_key | BIGINT | no | FK -> dim_product | Surrogate key of the product sold | 88 |
| store_key | BIGINT | yes | FK -> dim_store | Surrogate key of the fulfilling store | 12 |
| date_key | INTEGER | no | FK -> dim_date | Order date, as YYYYMMDD | 20260315 |
| quantity | INTEGER | no | | Units purchased | 2 |
| unit_price | NUMERIC(12,2) | no | | Price per unit | 499.00 |
| discount | NUMERIC(12,2) | no | | Discount applied | 25.00 |
| tax | NUMERIC(12,2) | no | | Not present in source data; defaults to 0 | 0.00 |
| total_amount | NUMERIC(12,2) | no | | `quantity * unit_price - discount` | 973.00 |
| payment_status | TEXT | no | | Latest payment attempt's status for this order | success |

## warehouse.dim_customer / dim_product / dim_store

Each is a simple surrogate-key dimension: `*_key` (surrogate, used in
joins) and `*_id` (natural key from source, unique). See
`docs/database_design.md` for why surrogate keys are used.

## warehouse.dim_date

Standard calendar dimension, one row per day from 2023-01-01 to
2027-12-31, with `date_key` as `YYYYMMDD` (e.g. `20260315`).

## audit.pipeline_runs

| column | type | description |
|---|---|---|
| run_id | BIGSERIAL | Surrogate key |
| pipeline_name | TEXT | e.g. `full-pipeline`, `ecommerce_pipeline` |
| status | TEXT | `running`, `success`, or `failed` |
| watermark_start / watermark_end | TIMESTAMPTZ | Used for incremental loading |
| records_processed | INTEGER | Rows ingested during this run |

## audit.rejected_records

| column | type | description |
|---|---|---|
| record_id | BIGSERIAL | Surrogate key |
| source | TEXT | e.g. `csv:orders.csv`, `api:products` |
| table_name | TEXT | Intended destination table |
| record_data | JSONB | The offending row, preserved for review |
| reason | TEXT | Why it was rejected |
