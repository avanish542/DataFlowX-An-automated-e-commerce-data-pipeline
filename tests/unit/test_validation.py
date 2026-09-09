"""Unit tests for schema validation and business rule checks."""

import pandas as pd

from dataflowx.validation.schema_validator import CUSTOMERS_SCHEMA, ORDER_ITEMS_SCHEMA, validate_schema
from dataflowx.validation.validation_rules import (
    check_accepted_values,
    check_discount_not_exceed_line_value,
    check_no_duplicate_ids,
    check_non_negative,
    check_positive_quantity,
    check_valid_date,
)


def test_validate_schema_splits_valid_and_invalid_rows():
    df = pd.DataFrame(
        {
            "customer_id": [1, 2, 3],
            "first_name": ["Aarav", "Priya", None],
            "last_name": ["Sharma", "Iyer", "Khan"],
            "email": ["a@x.com", "b@x.com", "c@x.com"],
            "signup_date": ["2024-01-01", "2024-02-01", "2024-03-01"],
        }
    )

    result = validate_schema(df, CUSTOMERS_SCHEMA)

    assert len(result.valid_rows) == 2
    assert len(result.invalid_rows) == 1
    assert not result.is_valid


def test_validate_schema_missing_required_column_fails_fast():
    df = pd.DataFrame({"customer_id": [1, 2]})  # missing first_name, last_name, email, signup_date

    result = validate_schema(df, CUSTOMERS_SCHEMA)

    assert not result.is_valid
    assert len(result.valid_rows) == 0
    assert "Missing required columns" in result.errors[0]


def test_check_positive_quantity_splits_correctly():
    df = pd.DataFrame({"quantity": [1, -2, 3, 0]})

    valid, invalid, reason = check_positive_quantity(df)

    assert len(valid) == 2
    assert len(invalid) == 2
    assert "quantity" in reason


def test_check_non_negative_splits_correctly():
    df = pd.DataFrame({"amount": [10.0, -5.0, 0.0]})

    valid, invalid, _ = check_non_negative(df, "amount")

    assert len(valid) == 2
    assert len(invalid) == 1


def test_check_accepted_values_splits_correctly():
    df = pd.DataFrame({"payment_status": ["success", "failed", "bogus"]})

    valid, invalid, _ = check_accepted_values(df, "payment_status", {"success", "failed"})

    assert len(valid) == 2
    assert len(invalid) == 1
    assert invalid.iloc[0]["payment_status"] == "bogus"


def test_check_valid_date_flags_unparseable_dates():
    df = pd.DataFrame({"order_date": ["2024-01-01", "not-a-date", "2024-03-15"]})

    valid, invalid, _ = check_valid_date(df, "order_date")

    assert len(valid) == 2
    assert len(invalid) == 1


def test_check_no_duplicate_ids_keeps_first_occurrence():
    df = pd.DataFrame({"order_id": [1, 2, 2, 3]})

    valid, duplicates, _ = check_no_duplicate_ids(df, "order_id")

    assert len(valid) == 3
    assert len(duplicates) == 1
    assert list(valid["order_id"]) == [1, 2, 3]


def test_order_items_schema_requires_quantity_and_price():
    df = pd.DataFrame(
        {
            "order_item_id": [1],
            "order_id": [1],
            "product_id": [1],
            "quantity": [None],
            "unit_price": [10.0],
        }
    )

    result = validate_schema(df, ORDER_ITEMS_SCHEMA)

    assert len(result.invalid_rows) == 1


def test_check_discount_not_exceed_line_value():
    df = pd.DataFrame(
        {"quantity": [2, 1], "unit_price": [10.0, 5.0], "discount": [5.0, 6.0]}
    )

    valid, invalid, reason = check_discount_not_exceed_line_value(df)

    assert len(valid) == 1
    assert len(invalid) == 1
    assert "discount" in reason
