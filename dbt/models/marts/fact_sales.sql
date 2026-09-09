{{ config(materialized='table') }}

-- Grain: one row in fact_sales = one product line item within one
-- customer order (i.e. one row of raw.order_items, enriched with
-- dimension keys and the order's payment status).
--
-- Tax is not present in the source data, so it defaults to 0 rather than
-- being fabricated - kept as a column for schema completeness /
-- future enhancement (see docs/database_design.md).

with latest_payment as (
    -- An order can have more than one payment attempt (e.g. a failed
    -- attempt followed by a successful retry). We take the most recent
    -- one as the order's effective payment status.
    select distinct on (order_id)
        order_id,
        payment_status
    from {{ ref('stg_payments') }}
    order by order_id, payment_date desc nulls last, payment_id desc
)

select
    row_number() over (order by oi.order_id, oi.order_item_id) as sale_id,
    oi.order_item_id as order_item_id,
    oi.order_id,
    dc.customer_key,
    dp.product_key,
    ds.store_key,
    dd.date_key,
    oi.quantity,
    oi.unit_price,
    oi.discount,
    0::numeric(12, 2) as tax,
    (oi.quantity * oi.unit_price - oi.discount) as total_amount,
    coalesce(lp.payment_status, 'pending') as payment_status,
    now() as created_at
from {{ ref('stg_order_items') }} oi
join {{ ref('stg_orders') }} o on oi.order_id = o.order_id
join {{ ref('dim_customer') }} dc on o.customer_id = dc.customer_id
join {{ ref('dim_product') }} dp on oi.product_id = dp.product_id
left join {{ ref('dim_store') }} ds on o.store_id = ds.store_id
join {{ ref('dim_date') }} dd on o.order_date = dd.full_date
left join latest_payment lp on o.order_id = lp.order_id
