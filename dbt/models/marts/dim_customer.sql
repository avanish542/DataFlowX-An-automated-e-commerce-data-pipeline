{{ config(materialized='table') }}

select
    row_number() over (order by customer_id) as customer_key,
    customer_id,
    first_name,
    last_name,
    email,
    city,
    state,
    country,
    signup_date,
    now() as created_at,
    now() as updated_at
from {{ ref('stg_customers') }}
