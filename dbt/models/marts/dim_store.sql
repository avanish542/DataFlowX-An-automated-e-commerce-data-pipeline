{{ config(materialized='table') }}

select
    row_number() over (order by store_id) as store_key,
    store_id,
    store_name,
    city,
    state,
    country,
    now() as created_at,
    now() as updated_at
from {{ ref('stg_stores') }}
