select
    order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    coalesce(discount, 0) as discount,
    created_at,
    updated_at
from {{ source('raw', 'order_items') }}
