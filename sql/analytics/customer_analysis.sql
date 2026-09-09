-- Customer analysis queries against warehouse.fact_sales / dim_customer.

-- Top 10 most valuable customers by lifetime spend
select
    c.customer_id,
    c.first_name,
    c.last_name,
    sum(f.total_amount) as lifetime_spend,
    count(distinct f.order_id) as total_orders
from warehouse.fact_sales f
join warehouse.dim_customer c on f.customer_key = c.customer_key
group by c.customer_id, c.first_name, c.last_name
order by lifetime_spend desc
limit 10;

-- New customers acquired per month (based on signup_date)
select
    date_trunc('month', signup_date)::date as signup_month,
    count(*) as new_customers
from warehouse.dim_customer
where signup_date is not null
group by signup_month
order by signup_month;

-- Repeat customer rate: share of customers with more than one order
with orders_per_customer as (
    select customer_key, count(distinct order_id) as order_count
    from warehouse.fact_sales
    group by customer_key
)
select
    count(*) filter (where order_count > 1)::numeric
        / nullif(count(*), 0) as repeat_customer_rate
from orders_per_customer;
