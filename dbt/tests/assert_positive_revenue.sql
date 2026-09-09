-- dbt convention: a singular test SELECT should return zero rows to pass.
-- This fails the build if any fact_sales row has negative revenue.

select *
from {{ ref('fact_sales') }}
where total_amount < 0
