-- DataFlowX schema layout
--
-- raw        : bronze layer - source data loaded with minimal changes
-- staging    : dbt staging models land here (renamed/typed, still row-per-source-row)
-- warehouse  : gold layer - star schema (dim_* and fact_sales)
-- analytics  : reporting-friendly views/tables built on top of warehouse
-- audit      : pipeline run metadata, data quality results, rejected records

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS audit;
