-- One row per order, with the order total and item count derived from
-- its line items. Used by int_customer_orders and by fact_sales for the
-- final line_total figure.

select
    oi.order_id,
    count(*) as item_count,
    sum(oi.quantity) as total_quantity,
    sum(oi.quantity * oi.unit_price - oi.discount) as order_subtotal
from {{ ref('stg_order_items') }} oi
group by oi.order_id
