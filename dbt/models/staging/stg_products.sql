select
    product_id,
    trim(product_name) as product_name,
    coalesce(trim(category), 'Uncategorized') as category,
    price,
    store_id,
    created_at,
    updated_at
from {{ source('raw', 'products') }}
