"""Unit tests for the transformation layer (cleaners, transformers, aggregations)."""

import pandas as pd

from dataflowx.transformation.aggregations import (
    average_order_value,
    revenue_by_date,
    top_n_products,
    total_revenue,
)
from dataflowx.transformation.cleaners import (
    drop_exact_duplicates,
    normalize_emails,
    standardize_text_case,
    trim_whitespace,
)
from dataflowx.transformation.transformers import add_line_total, coerce_dates, coerce_numeric


def test_trim_whitespace_strips_values():
    df = pd.DataFrame({"city": ["  Kanpur ", "Mumbai  "]})

    result = trim_whitespace(df, ["city"])

    assert list(result["city"]) == ["Kanpur", "Mumbai"]


def test_standardize_text_case_title_case():
    df = pd.DataFrame({"status": ["SHIPPED", "delivered"]})

    result = standardize_text_case(df, ["status"], case="title")

    assert list(result["status"]) == ["Shipped", "Delivered"]


def test_drop_exact_duplicates_removes_repeated_rows():
    df = pd.DataFrame({"id": [1, 1, 2], "value": ["a", "a", "b"]})

    result = drop_exact_duplicates(df)

    assert len(result) == 2


def test_normalize_emails_lowercases_and_strips():
    df = pd.DataFrame({"email": [" User@Example.com ", "OTHER@X.COM"]})

    result = normalize_emails(df)

    assert list(result["email"]) == ["user@example.com", "other@x.com"]


def test_coerce_numeric_converts_strings_and_flags_bad_values():
    df = pd.DataFrame({"price": ["10.5", "not-a-number", "20"]})

    result = coerce_numeric(df, ["price"])

    assert result["price"].iloc[0] == 10.5
    assert pd.isna(result["price"].iloc[1])
    assert result["price"].iloc[2] == 20.0


def test_coerce_dates_converts_strings():
    df = pd.DataFrame({"order_date": ["2024-01-01", "invalid-date"]})

    result = coerce_dates(df, ["order_date"])

    assert result["order_date"].iloc[0] is not None
    assert pd.isna(result["order_date"].iloc[1])


def test_add_line_total_computes_quantity_times_price_minus_discount():
    df = pd.DataFrame({"quantity": [2, 3], "unit_price": [10.0, 5.0], "discount": [1.0, 0.0]})

    result = add_line_total(df)

    assert list(result["line_total"]) == [19.0, 15.0]


def test_total_revenue_sums_line_totals():
    order_items = pd.DataFrame(
        {
            "order_id": [1, 1, 2],
            "quantity": [1, 2, 1],
            "unit_price": [10.0, 5.0, 20.0],
            "discount": [0.0, 0.0, 5.0],
        }
    )

    assert total_revenue(order_items) == 35.0  # 10 + 10 + 15


def test_average_order_value_divides_by_distinct_orders():
    order_items = pd.DataFrame(
        {
            "order_id": [1, 1, 2],
            "quantity": [1, 1, 1],
            "unit_price": [10.0, 10.0, 10.0],
            "discount": [0.0, 0.0, 0.0],
        }
    )

    # total revenue = 30, distinct orders = 2 -> AOV = 15
    assert average_order_value(order_items) == 15.0


def test_revenue_by_date_groups_by_order_date():
    order_items = pd.DataFrame(
        {"order_id": [1, 2], "quantity": [1, 1], "unit_price": [10.0, 20.0], "discount": [0.0, 0.0]}
    )
    orders = pd.DataFrame({"order_id": [1, 2], "order_date": ["2024-01-01", "2024-01-01"]})

    result = revenue_by_date(order_items, orders)

    assert len(result) == 1
    assert result.iloc[0]["revenue"] == 30.0


def test_top_n_products_orders_by_revenue_desc():
    order_items = pd.DataFrame(
        {
            "order_id": [1, 2],
            "product_id": [1, 2],
            "quantity": [1, 1],
            "unit_price": [100.0, 5.0],
            "discount": [0.0, 0.0],
        }
    )
    products = pd.DataFrame({"product_id": [1, 2], "product_name": ["Laptop", "Pen"]})

    result = top_n_products(order_items, products, n=2)

    assert result.iloc[0]["product_name"] == "Laptop"
