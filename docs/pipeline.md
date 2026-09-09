# Pipeline

## Stages

```
source (CSV / JSON / API)
  -> ingestion (load + clean)
  -> validation (schema + business rules)
  -> raw / bronze (PostgreSQL)
  -> dbt staging (rename/type)
  -> data quality checks
  -> dbt marts (star schema) / gold
  -> analytics (SQL queries, dashboard)
```

Each stage is implemented in `src/dataflowx/` and is unit tested in
isolation (see `tests/unit/`). The Airflow DAG
(`airflow/dags/ecommerce_pipeline.py`) and the CLI (`dataflowx/cli.py`)
both call into the same functions - neither one contains business logic
of its own.

## Full load vs. incremental load

The current implementation does a **full load with upsert** rather than
a true incremental/watermark-filtered extract: `ingest_all()` always
reads the entire source file/API response, but `upsert_dataframe()`
writes it with `INSERT ... ON CONFLICT DO UPDATE`, so re-running the
pipeline against the same or overlapping data does not create duplicates
or fail on a primary key violation.

The watermark mechanism (`audit.pipeline_runs.watermark_start` /
`watermark_end`, `get_last_successful_watermark()` in
`database/queries.py`) records the last successful run timestamp and is
used as the next run's `watermark_start`. The current source readers still
perform a full read followed by an idempotent upsert; true row-level
watermark filtering is intentionally left as a future enhancement because
the demo CSV/JSON/API sources do not expose a reliable `updated_since`
contract.

## Idempotency

Running the pipeline twice in a row must not create duplicate business
records. Two things make that true here:

1. **Upserts, not appends.** `upsert_dataframe()` uses
   `INSERT ... ON CONFLICT (primary_key) DO UPDATE`, so loading the same
   `customer_id` twice updates the existing row instead of duplicating
   it.
2. **A uniqueness constraint on the fact table.**
   `warehouse.fact_sales` has `UNIQUE (order_id, order_item_id)`, so even
   if dbt's `fact_sales` model were rebuilt from scratch, the same
   business event never ends up as two fact rows.

## Retries and failure handling

- Airflow tasks are configured with `retries=2` and a `retry_delay` of 2
  minutes (`default_args` in the DAG).
- The REST API client (`api_client.py`) retries on connection errors and
  timeouts with exponential backoff (`utils/retry.py`), separately from
  Airflow's task-level retries.
- A **critical** data quality check failure stops the pipeline before
  bad data reaches `dbt run` for the marts (see
  `validation/data_quality.py` - `RAW_LAYER_CHECKS`). Non-critical
  checks are recorded as warnings and don't block the run.
- Every pipeline run is recorded in `audit.pipeline_runs` with a status
  of `running`, `success`, or `failed`, and (on the Airflow DAG)
  `update_pipeline_metadata` always runs, even if an earlier task failed,
  so a run is never left stuck in `running`.

## Rejected records

Rows that fail schema or business-rule validation are never silently
dropped. `record_rejected_rows()` writes them, with the reason, into
`audit.rejected_records` as JSON. A rejected row can be reviewed with:

```sql
select * from audit.rejected_records
where table_name = 'order_items'
order by rejected_at desc;
```

Rejected records aren't automatically reprocessed - they are meant to be
reviewed, and either fixed at the source and re-ingested, or accepted as
genuinely bad data. Automatic reprocessing is listed under Future
Enhancements.

## Pipeline audit trail

Every run - whether triggered by Airflow, the CLI, or a test - writes a
row to `audit.pipeline_runs`, and every data quality check writes a row
to `audit.data_quality_results`. This is what makes it possible to
answer "did last night's pipeline run succeed, and what did it process?"
without digging through log files.
