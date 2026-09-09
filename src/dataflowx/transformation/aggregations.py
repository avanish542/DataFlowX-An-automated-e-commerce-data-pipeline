"""
Pandas-based aggregations.

The warehouse (dbt marts) is the source of truth for reporting, but
having the same business logic available as plain pandas functions makes
it possible to unit test revenue/AOV logic without a running database.
These mirror the SQL in sql/analytics/ - if the two ever disagree, that's
a bug worth catching.
"""

import pandas as pd


def total_revenue(order_items: pd.DataFrame) -> float:
    """Sum of (quantity * unit_price - discount) across all line items."""
    line_totals = order_items["quantity"] * order_items["unit_price"] - order_items.get(
        "discount", 0
    )
    return float(line_totals.sum())


def revenue_by_date(order_items: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """Daily revenue, joining order_items to orders for the order date."""
    merged = order_items.merge(orders[["order_id", "order_date"]], on="order_id")
    merged["line_total"] = merged["quantity"] * merged["unit_price"] - merged.get("discount", 0)
    return (
        merged.groupby("order_date")["line_total"]
        .sum()
        .reset_index()
        .rename(columns={"line_total": "revenue"})
        .sort_values("order_date")
    )


def top_n_products(order_items: pd.DataFrame, products: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N products by total revenue."""
    merged = order_items.merge(products[["product_id", "product_name"]], on="product_id")
    merged["line_total"] = merged["quantity"] * merged["unit_price"] - merged.get("discount", 0)
    return (
        merged.groupby("product_name")["line_total"]
        .sum()
        .reset_index()
        .rename(columns={"line_total": "revenue"})
        .sort_values("revenue", ascending=False)
        .head(n)
    )


def average_order_value(order_items: pd.DataFrame) -> float:
    """Total revenue divided by the number of distinct orders."""
    line_totals = order_items["quantity"] * order_items["unit_price"] - order_items.get(
        "discount", 0
    )
    order_count = order_items["order_id"].nunique()
    if order_count == 0:
        return 0.0
    return float(line_totals.sum() / order_count)
