{{ config(materialized='table') }}

select
    row_number() over (order by product_id) as product_key,
    product_id,
    product_name,
    category,
    price,
    now() as created_at,
    now() as updated_at
from {{ ref('stg_products') }}
