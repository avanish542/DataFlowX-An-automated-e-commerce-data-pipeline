select
    payment_id,
    order_id,
    payment_method,
    amount,
    payment_status,
    payment_date,
    created_at,
    updated_at
from {{ source('raw', 'payments') }}
