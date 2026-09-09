"""
DataFlowX analytics dashboard.

Reads directly from the warehouse (gold) schema - all the cleaning,
validation and modeling has already happened by the time data gets here.
This file is intentionally light: parse the named queries out of
dashboard_queries.sql, run them, and display the results. No business
logic belongs in a dashboard.

Run with:
    streamlit run dashboard/app.py
"""

import re
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import text

from dataflowx.database.connection import get_engine

QUERIES_FILE = Path(__file__).parent / "queries" / "dashboard_queries.sql"


@st.cache_data(ttl=300)
def load_queries() -> dict[str, str]:
    """Parse '-- name: xyz' delimited queries out of the .sql file."""
    content = QUERIES_FILE.read_text()
    parts = re.split(r"--\s*name:\s*(\w+)", content)
    # parts = ['', 'total_revenue', ' select ...', 'total_orders', ' select ...', ...]
    queries = {}
    for i in range(1, len(parts), 2):
        queries[parts[i]] = parts[i + 1].strip()
    return queries


@st.cache_data(ttl=60)
def run_query(sql: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


def main() -> None:
    st.set_page_config(page_title="DataFlowX Analytics", layout="wide")
    st.title("DataFlowX - E-Commerce Analytics")
    st.caption("Reading from the warehouse (gold) layer, built by dbt.")

    try:
        queries = load_queries()
        kpi_revenue = run_query(queries["total_revenue"]).iloc[0, 0]
        kpi_orders = run_query(queries["total_orders"]).iloc[0, 0]
        kpi_customers = run_query(queries["total_customers"]).iloc[0, 0]
        kpi_aov = run_query(queries["average_order_value"]).iloc[0, 0]
    except Exception as exc:
        st.error(
            "Could not read from the warehouse schema. Make sure PostgreSQL "
            "is reachable and the pipeline has been run at least once "
            f"(`make pipeline`).\n\nDetails: {exc}"
        )
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue", f"${kpi_revenue:,.2f}")
    col2.metric("Total Orders", f"{kpi_orders:,}")
    col3.metric("Total Customers", f"{kpi_customers:,}")
    col4.metric("Average Order Value", f"${kpi_aov:,.2f}")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Revenue by Date")
        df = run_query(queries["revenue_by_date"])
        st.line_chart(df.set_index("full_date")["revenue"])

        st.subheader("Top 10 Products")
        st.dataframe(run_query(queries["top_products"]), use_container_width=True)

        st.subheader("Payment Status Breakdown")
        st.bar_chart(run_query(queries["payment_status_breakdown"]).set_index("payment_status"))

    with right:
        st.subheader("Revenue by Category")
        df = run_query(queries["revenue_by_category"])
        st.bar_chart(df.set_index("category")["revenue"])

        st.subheader("Top 10 Customers")
        st.dataframe(run_query(queries["top_customers"]), use_container_width=True)

        st.subheader("Sales by Store")
        st.dataframe(run_query(queries["sales_by_store"]), use_container_width=True)


if __name__ == "__main__":
    main()
