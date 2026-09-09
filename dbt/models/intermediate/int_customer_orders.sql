-- One row per customer who has placed at least one order, with lifetime
-- order count, total spend and first/last order dates. Feeds the
-- "repeat customer rate" and "most valuable customers" KPIs.

select
    o.customer_id,
    count(distinct o.order_id) as total_orders,
    sum(om.order_subtotal) as lifetime_spend,
    min(o.order_date) as first_order_date,
    max(o.order_date) as last_order_date
from {{ ref('stg_orders') }} o
join {{ ref('int_order_metrics') }} om on o.order_id = om.order_id
group by o.customer_id
