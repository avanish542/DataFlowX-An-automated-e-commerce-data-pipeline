-- Staging models do light renaming/casting only. They stay 1:1 with the
-- source table - no joins, no aggregation. That happens in intermediate/marts.

select
    customer_id,
    trim(first_name) as first_name,
    trim(last_name) as last_name,
    lower(trim(email)) as email,
    phone,
    city,
    state,
    country,
    signup_date,
    created_at,
    updated_at
from {{ source('raw', 'customers') }}
