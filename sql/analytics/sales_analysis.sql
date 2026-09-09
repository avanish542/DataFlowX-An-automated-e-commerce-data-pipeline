-- Sales, payment and store analysis queries.

-- Payment success/failure rate
select
    payment_status,
    count(*) as line_items,
    round(100.0 * count(*) / sum(count(*)) over (), 2) as pct_of_total
from warehouse.fact_sales
group by payment_status
order by line_items desc;

-- Sales by store
select
    s.store_id,
    s.store_name,
    s.city,
    sum(f.total_amount) as store_revenue,
    count(distinct f.order_id) as orders_fulfilled
from warehouse.fact_sales f
join warehouse.dim_store s on f.store_key = s.store_key
group by s.store_id, s.store_name, s.city
order by store_revenue desc;

-- Weekday vs weekend sales
select
    d.is_weekend,
    sum(f.total_amount) as revenue,
    count(distinct f.order_id) as order_count
from warehouse.fact_sales f
join warehouse.dim_date d on f.date_key = d.date_key
group by d.is_weekend;
