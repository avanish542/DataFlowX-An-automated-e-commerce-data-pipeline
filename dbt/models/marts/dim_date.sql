{{ config(materialized='table') }}

-- A plain calendar spine built with generate_series - no extra package
-- needed for something this simple. Range comfortably covers the
-- synthetic data's order dates plus room to grow.

with date_spine as (
    select generate_series(
        '2023-01-01'::date,
        '2027-12-31'::date,
        interval '1 day'
    )::date as full_date
)

select
    (to_char(full_date, 'YYYYMMDD'))::int as date_key,
    full_date,
    extract(year from full_date)::int as year,
    extract(quarter from full_date)::int as quarter,
    extract(month from full_date)::int as month,
    to_char(full_date, 'Month') as month_name,
    extract(day from full_date)::int as day,
    extract(isodow from full_date)::int - 1 as day_of_week,  -- 0 = Monday
    to_char(full_date, 'Day') as day_name,
    extract(isodow from full_date) in (6, 7) as is_weekend
from date_spine
