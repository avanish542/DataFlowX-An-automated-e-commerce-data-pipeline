select
    store_id,
    trim(store_name) as store_name,
    city,
    state,
    country,
    created_at,
    updated_at
from {{ source('raw', 'stores') }}
