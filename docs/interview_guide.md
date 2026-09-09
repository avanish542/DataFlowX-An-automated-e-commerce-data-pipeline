# Interview Guide

Short, honest answers you can give in an interview, tied to what's
actually built in this repository.

**1. What is ETL?**
Extract, Transform, Load - pull data from a source, transform it into a
clean/usable shape, then load it into a destination. In this project:
extract from CSV/JSON/API, transform via Python cleaning + dbt SQL, load
into PostgreSQL.

**2. ETL vs ELT?**
ETL transforms data before loading it into the destination. ELT loads
raw data first, then transforms it in the destination using its own
compute. This project is closer to ELT: raw data is loaded into
PostgreSQL first (`raw` schema), and dbt transforms it in-database
afterward.

**3. Why PostgreSQL?**
It's free, widely used in industry, has proper transactions and
constraints, and is a realistic choice for a project at this scale - no
need for a distributed warehouse like Snowflake/BigQuery when the data
volume is in the tens of thousands to low millions of rows.

**4. Why Airflow?**
It's the most common open-source orchestrator, has explicit task
dependencies, retries, scheduling, and a visual UI to see run history -
useful for demonstrating orchestration concepts that generalize to any
scheduler.

**5. What is a DAG?**
A Directed Acyclic Graph - a set of tasks with dependencies and no
cycles, so there's always a valid order to execute them in.
`ecommerce_pipeline.py` defines one: check files -> ingest -> quality
checks -> dbt staging -> dbt marts -> dbt test -> update metadata.

**6. Why dbt?**
It makes SQL transformations version-controlled, testable, and
documented, with dependency management via `ref()`/`source()` instead of
hand-maintained view/table creation order. It also gives free lineage
and a consistent way to write tests.

**7. What is a star schema?**
A dimensional model with one central fact table (measurable events -
here, `fact_sales`) connected to several dimension tables (descriptive
attributes - `dim_customer`, `dim_product`, `dim_store`, `dim_date`) via
foreign keys. Optimized for analytical queries (aggregations, filters)
rather than transactional consistency.

**8. What is a fact table?**
A table of measurable business events, usually numeric and additive.
`fact_sales` holds one row per order line item, with measures like
`quantity`, `unit_price`, `total_amount`.

**9. What is a dimension table?**
A table of descriptive attributes used to filter or group facts -
`dim_customer` has name/city/country, `dim_product` has name/category.

**10. What is the grain of fact_sales?**
One row = one product line item within one order (one row of
`raw.order_items`, enriched with dimension keys). Defined explicitly in
`docs/database_design.md` and in the model's SQL comment.

**11. What is incremental loading?**
Only processing new or changed records instead of reprocessing
everything every run, usually using a timestamp column and a stored
"watermark" of the last successful run.

**12. What is a watermark?**
The timestamp of the last successfully processed record (or run).
Stored here in `audit.pipeline_runs.watermark_end`, read back by
`get_last_successful_watermark()` at the start of the next run.

**13. How did you prevent duplicate records?**
Two mechanisms: `INSERT ... ON CONFLICT DO UPDATE` (upsert) when loading
into `raw.*`, and a `UNIQUE (order_id, order_item_id)` constraint on
`warehouse.fact_sales`. Re-running the pipeline updates existing rows
instead of duplicating them.

**14. How did you handle bad data?**
Two layers: Python validation before loading (schema + business rules,
rejected rows go to `audit.rejected_records` with a reason instead of
being silently dropped), and SQL/dbt-based data quality checks after
loading (`audit.data_quality_results`), with critical checks able to
stop the pipeline.

**15. What happens when an Airflow task fails?**
It retries up to `retries=2` times with a delay, per `default_args`. If
it still fails, downstream tasks depending on it don't run, but
`update_pipeline_metadata` uses `trigger_rule="all_done"` so the run is
still marked `failed` in `audit.pipeline_runs` rather than left hanging.

**16. How did you implement data quality?**
See question 14 - a Python validation layer plus a SQL-based
`data_quality.py` framework with named checks, each recorded to an audit
table with a pass/fail/warning status.

**17. How would you scale this pipeline?**
For more volume: partition large tables (e.g. `fact_sales` by date),
move heavy joins/aggregations fully into dbt/SQL (already mostly true),
and consider a proper columnar warehouse (Snowflake/BigQuery/Redshift)
once single-node PostgreSQL becomes the bottleneck. For more sources:
the CSV/JSON/API loader pattern in `ingestion/` generalizes - add a new
loader function following the same shape.

**18. How would you handle 1 TB of data?**
Single-node PostgreSQL wouldn't be the right fit anymore. I'd move to a
distributed warehouse (Snowflake/BigQuery/Redshift) or a lakehouse
(Spark + object storage + a table format like Iceberg/Delta), and switch
from pandas-based row-by-row Python processing to something that can
process in parallel (Spark or a warehouse's own SQL engine). The Airflow
orchestration and dbt-based SQL modeling patterns would carry over
mostly unchanged.

**19. How would you migrate this to AWS?**
RDS for PostgreSQL as the warehouse, S3 as a landing zone for raw files
before ingestion, MWAA (managed Airflow) or Airflow on ECS for
orchestration, and Secrets Manager instead of a local `.env` file for
credentials. See `docs/deployment.md` - this is explicitly listed as a
future enhancement, not implemented here.

**20. How would you convert this to real-time processing?**
Replace batch file ingestion with a streaming source (Kafka/Kinesis),
process events with something like Flink or Spark Structured Streaming
instead of scheduled Airflow batches, and change the warehouse loading
pattern from batch upserts to continuous micro-batch or streaming
upserts. The star schema and data quality *concepts* stay the same - the
plumbing that gets data there changes.
