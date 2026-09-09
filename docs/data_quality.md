# Data Quality

Data quality is enforced at two points in the pipeline.

## 1. Before loading (Python validation layer)

`validation/schema_validator.py` and `validation/validation_rules.py`
check each source file before it's written to `raw.*`:

- required columns are present
- required fields are non-null
- IDs are not duplicated within the file
- business rules hold: `quantity > 0`, amounts `>= 0`, `payment_status`
  is one of the accepted values, dates are parseable

Rows that fail are split out and written to `audit.rejected_records`
with a reason - they never reach the `raw` schema. This is enforced in
`ingestion_service.py` for every source table.

## 2. After loading (SQL-based data quality framework)

`validation/data_quality.py` defines `RAW_LAYER_CHECKS`: a list of SQL
checks run against tables already in PostgreSQL, each writing a row to
`audit.data_quality_results` (`pass`, `fail`, or `warning`).

| Check | Table | Severity | What it catches |
|---|---|---|---|
| `no_duplicate_customer_id` | customers | critical | Duplicate natural keys that slipped past dedup |
| `positive_quantity` | order_items | critical | `quantity <= 0` |
| `non_negative_unit_price` | order_items | critical | Negative prices |
| `valid_payment_status` | payments | critical | Status outside the accepted set |
| `non_negative_amount` | payments | critical | Negative payment amounts |
| `orphan_order_items` | order_items | warning | Line items whose order was rejected upstream |
| `orphan_orders_missing_customer` | orders | warning | Orders whose customer was rejected upstream |

**Critical** checks failing stops the pipeline before `dbt run` builds
the marts (`run_quality_checks()` returns `False`, and both the CLI's
`pipeline` command and the Airflow DAG treat that as a hard stop).
**Warning** checks are recorded but don't block the run - they point at
real but non-fatal data issues (usually a side effect of an earlier
rejected row) worth reviewing in `audit.rejected_records`.

## 3. dbt tests (the same idea, expressed in dbt)

Once data reaches staging/marts, dbt's own tests
(`not_null`, `unique`, `relationships`, `accepted_values`, plus the two
custom singular tests in `dbt/tests/`) provide a second, independent
check on the exact same principles - schema integrity and referential
integrity - closer to the analytics layer. A couple of `relationships`
tests are deliberately set to `severity: warn` (see
`dbt/models/staging/_staging.yml`) for the same reason as the
`orphan_order_items` check above: an order/payment referencing a
rejected order is expected, not a pipeline bug.

## Why two layers instead of one

The Python layer runs *before* anything reaches `raw`, so it's what
populates `audit.rejected_records` with the actual offending rows. The
SQL/dbt layers run *after* loading and catch anything that the Python
layer wouldn't see in isolation - like referential integrity across
tables, which only makes sense to check once everything is in one place.
