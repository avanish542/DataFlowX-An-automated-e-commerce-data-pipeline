-- Fails if any order in stg_orders has no corresponding line items in
-- fact_sales - this would indicate an order that never made it through
-- the pipeline correctly (e.g. all its items were rejected in ingestion).

select o.order_id
from {{ ref('stg_orders') }} o
left join {{ ref('fact_sales') }} f on o.order_id = f.order_id
where f.order_id is null
