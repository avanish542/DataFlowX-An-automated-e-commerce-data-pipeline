-- Revenue analysis queries against warehouse.fact_sales.
-- These are meant to be run ad hoc (psql, a notebook, or a BI tool) - the
-- dashboard queries a similar but smaller set (see dashboard/queries/).

-- Total revenue
select sum(total_amount) as total_revenue
from warehouse.fact_sales;

-- Daily revenue
select
    d.full_date,
    sum(f.total_amount) as daily_revenue,
    count(distinct f.order_id) as order_count
from warehouse.fact_sales f
join warehouse.dim_date d on f.date_key = d.date_key
group by d.full_date
order by d.full_date;

-- Monthly revenue
select
    d.year,
    d.month,
    d.month_name,
    sum(f.total_amount) as monthly_revenue
from warehouse.fact_sales f
join warehouse.dim_date d on f.date_key = d.date_key
group by d.year, d.month, d.month_name
order by d.year, d.month;

-- Average order value
select
    sum(total_amount) / nullif(count(distinct order_id), 0) as average_order_value
from warehouse.fact_sales;

-- Revenue by category
select
    p.category,
    sum(f.total_amount) as category_revenue
from warehouse.fact_sales f
join warehouse.dim_product p on f.product_key = p.product_key
group by p.category
order by category_revenue desc;
