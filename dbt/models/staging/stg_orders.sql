select
    order_id,
    customer_id,
    store_id,
    order_date,
    coalesce(order_status, 'unknown') as order_status,
    created_at,
    updated_at
from {{ source('raw', 'orders') }}
