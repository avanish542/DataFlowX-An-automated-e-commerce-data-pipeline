-- =============================================================================
-- RAW SCHEMA (bronze layer)
-- Data lands here after ingestion + basic validation. Column types match the
-- validated source shape; this is not yet the analytical model.
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id     BIGINT PRIMARY KEY,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT,
    city            TEXT,
    state           TEXT,
    country         TEXT,
    signup_date     DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.stores (
    store_id        BIGINT PRIMARY KEY,
    store_name      TEXT NOT NULL,
    city            TEXT,
    state           TEXT,
    country         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.products (
    product_id      BIGINT PRIMARY KEY,
    product_name    TEXT NOT NULL,
    category        TEXT,
    price           NUMERIC(12, 2) NOT NULL,
    store_id        BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id        BIGINT PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    store_id        BIGINT,
    order_date      DATE NOT NULL,
    order_status    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.order_items (
    order_item_id   BIGINT PRIMARY KEY,
    order_id        BIGINT NOT NULL,
    product_id      BIGINT NOT NULL,
    quantity        INTEGER NOT NULL,
    unit_price      NUMERIC(12, 2) NOT NULL,
    discount        NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.payments (
    payment_id      BIGINT PRIMARY KEY,
    order_id        BIGINT NOT NULL,
    payment_method  TEXT,
    amount          NUMERIC(12, 2) NOT NULL,
    payment_status  TEXT NOT NULL,
    payment_date    DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_orders_customer_id ON raw.orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_raw_order_items_order_id ON raw.order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_raw_order_items_product_id ON raw.order_items (product_id);
CREATE INDEX IF NOT EXISTS idx_raw_payments_order_id ON raw.payments (order_id);
CREATE INDEX IF NOT EXISTS idx_raw_orders_updated_at ON raw.orders (updated_at);
CREATE INDEX IF NOT EXISTS idx_raw_customers_updated_at ON raw.customers (updated_at);

-- =============================================================================
-- WAREHOUSE SCHEMA (gold layer) - star schema
-- Built by dbt (dbt/models/marts). Defined here too so the database is
-- queryable and constrained even before dbt has run once.
--
-- Grain of fact_sales: one row = one product line item within one order
-- (i.e. one row of raw.order_items, enriched with dimension keys).
-- =============================================================================

CREATE TABLE IF NOT EXISTS warehouse.dim_customer (
    customer_key    BIGSERIAL PRIMARY KEY,      -- surrogate key
    customer_id     BIGINT NOT NULL UNIQUE,     -- natural key from source
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT NOT NULL,
    city            TEXT,
    state           TEXT,
    country         TEXT,
    signup_date     DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.dim_product (
    product_key     BIGSERIAL PRIMARY KEY,
    product_id      BIGINT NOT NULL UNIQUE,
    product_name    TEXT NOT NULL,
    category        TEXT,
    price           NUMERIC(12, 2) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.dim_store (
    store_key       BIGSERIAL PRIMARY KEY,
    store_id        BIGINT NOT NULL UNIQUE,
    store_name      TEXT NOT NULL,
    city            TEXT,
    state           TEXT,
    country         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_key        INTEGER PRIMARY KEY,        -- YYYYMMDD
    full_date       DATE NOT NULL UNIQUE,
    year             INTEGER NOT NULL,
    quarter          INTEGER NOT NULL,
    month            INTEGER NOT NULL,
    month_name       TEXT NOT NULL,
    day              INTEGER NOT NULL,
    day_of_week      INTEGER NOT NULL,           -- 0 = Monday .. 6 = Sunday
    day_name         TEXT NOT NULL,
    is_weekend       BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS warehouse.fact_sales (
    sale_id          BIGSERIAL PRIMARY KEY,       -- surrogate key
    order_id         BIGINT NOT NULL,             -- natural key
    order_item_id    BIGINT NOT NULL,             -- natural key
    customer_key     BIGINT NOT NULL REFERENCES warehouse.dim_customer (customer_key),
    product_key      BIGINT NOT NULL REFERENCES warehouse.dim_product (product_key),
    store_key        BIGINT REFERENCES warehouse.dim_store (store_key),
    date_key         INTEGER NOT NULL REFERENCES warehouse.dim_date (date_key),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price       NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    discount         NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (discount >= 0),
    tax              NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (tax >= 0),
    total_amount     NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    payment_status   TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (order_id, order_item_id)             -- idempotency: one row per line item
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_date_key ON warehouse.fact_sales (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer_key ON warehouse.fact_sales (customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product_key ON warehouse.fact_sales (product_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_store_key ON warehouse.fact_sales (store_key);

-- =============================================================================
-- AUDIT SCHEMA
-- Pipeline run metadata, data quality results and rejected records.
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit.pipeline_runs (
    run_id             BIGSERIAL PRIMARY KEY,
    pipeline_name      TEXT NOT NULL,
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at       TIMESTAMPTZ,
    status             TEXT NOT NULL DEFAULT 'running'
                            CHECK (status IN ('running', 'success', 'failed')),
    records_processed  INTEGER,
    watermark_start    TIMESTAMPTZ,
    watermark_end      TIMESTAMPTZ,
    error_message      TEXT
);

CREATE TABLE IF NOT EXISTS audit.data_quality_results (
    check_id           BIGSERIAL PRIMARY KEY,
    pipeline_run_id    BIGINT REFERENCES audit.pipeline_runs (run_id),
    table_name         TEXT NOT NULL,
    check_name         TEXT NOT NULL,
    status             TEXT NOT NULL CHECK (status IN ('pass', 'fail', 'warning')),
    failed_rows        INTEGER NOT NULL DEFAULT 0,
    checked_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit.rejected_records (
    record_id          BIGSERIAL PRIMARY KEY,
    source              TEXT NOT NULL,           -- e.g. 'csv:orders.csv'
    table_name          TEXT NOT NULL,           -- intended destination table
    record_data          JSONB NOT NULL,         -- the offending row, as JSON
    reason               TEXT NOT NULL,
    rejected_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dq_results_run_id ON audit.data_quality_results (pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_rejected_records_table ON audit.rejected_records (table_name);
