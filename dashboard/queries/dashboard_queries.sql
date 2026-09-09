-- Queries used by dashboard/app.py. Kept in one file so the dashboard
-- code stays about presentation, not SQL. Each query is delimited by a
-- name comment and loaded by name at runtime.

-- name: total_revenue
select coalesce(sum(total_amount), 0) as total_revenue from warehouse.fact_sales;

-- name: total_orders
select count(distinct order_id) as total_orders from warehouse.fact_sales;

-- name: total_customers
select count(*) as total_customers from warehouse.dim_customer;

-- name: average_order_value
select coalesce(sum(total_amount) / nullif(count(distinct order_id), 0), 0) as aov
from warehouse.fact_sales;

-- name: revenue_by_date
select d.full_date, sum(f.total_amount) as revenue
from warehouse.fact_sales f
join warehouse.dim_date d on f.date_key = d.date_key
group by d.full_date
order by d.full_date;

-- name: revenue_by_category
select p.category, sum(f.total_amount) as revenue
from warehouse.fact_sales f
join warehouse.dim_product p on f.product_key = p.product_key
group by p.category
order by revenue desc;

-- name: top_products
select p.product_name, sum(f.total_amount) as revenue
from warehouse.fact_sales f
join warehouse.dim_product p on f.product_key = p.product_key
group by p.product_name
order by revenue desc
limit 10;

-- name: top_customers
select c.first_name || ' ' || c.last_name as customer_name, sum(f.total_amount) as revenue
from warehouse.fact_sales f
join warehouse.dim_customer c on f.customer_key = c.customer_key
group by customer_name
order by revenue desc
limit 10;

-- name: payment_status_breakdown
select payment_status, count(*) as line_items
from warehouse.fact_sales
group by payment_status;

-- name: sales_by_store
select s.store_name, sum(f.total_amount) as revenue
from warehouse.fact_sales f
join warehouse.dim_store s on f.store_key = s.store_key
group by s.store_name
order by revenue desc;
