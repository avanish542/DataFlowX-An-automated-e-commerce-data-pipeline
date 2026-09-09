-- Product analysis queries against warehouse.fact_sales / dim_product.

-- Top 10 products by revenue
select
    p.product_id,
    p.product_name,
    p.category,
    sum(f.total_amount) as product_revenue,
    sum(f.quantity) as units_sold
from warehouse.fact_sales f
join warehouse.dim_product p on f.product_key = p.product_key
group by p.product_id, p.product_name, p.category
order by product_revenue desc
limit 10;

-- Best performing categories by revenue and units sold
select
    p.category,
    sum(f.total_amount) as category_revenue,
    sum(f.quantity) as units_sold,
    count(distinct f.order_id) as orders_containing_category
from warehouse.fact_sales f
join warehouse.dim_product p on f.product_key = p.product_key
group by p.category
order by category_revenue desc;
