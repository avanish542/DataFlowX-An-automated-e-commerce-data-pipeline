-- The fact grain is one row per order line item. This query should return
-- zero rows; any duplicate (order_id, order_item_id) means the grain was
-- accidentally changed by a join or source duplication.

select order_id, order_item_id
from {{ ref('fact_sales') }}
group by order_id, order_item_id
having count(*) > 1
