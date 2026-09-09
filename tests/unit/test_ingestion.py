"""Unit tests for the CSV and JSON ingestion loaders."""

import json

import pandas as pd
import pytest

from dataflowx.ingestion.csv_loader import CsvFileNotFoundError, CsvLoadError, load_csv
from dataflowx.ingestion.json_loader import JsonFileNotFoundError, JsonLoadError, load_json


def test_load_csv_returns_dataframe(tmp_path):
    file_path = tmp_path / "customers.csv"
    file_path.write_text("customer_id,first_name\n1,Ananya\n2,Rahul\n")

    df = load_csv(file_path)

    assert len(df) == 2
    assert list(df.columns) == ["customer_id", "first_name"]


def test_load_csv_missing_file_raises(tmp_path):
    with pytest.raises(CsvFileNotFoundError):
        load_csv(tmp_path / "does_not_exist.csv")


def test_load_csv_missing_required_column_raises(tmp_path):
    file_path = tmp_path / "orders.csv"
    file_path.write_text("order_id\n1\n2\n")

    with pytest.raises(CsvLoadError):
        load_csv(file_path, required_columns=["order_id", "customer_id"])


def test_load_csv_empty_file_raises(tmp_path):
    file_path = tmp_path / "empty.csv"
    file_path.write_text("")

    with pytest.raises(CsvLoadError):
        load_csv(file_path)


def test_load_json_list_of_records(tmp_path):
    file_path = tmp_path / "payments.json"
    file_path.write_text(json.dumps([{"payment_id": 1, "amount": 10.0}]))

    df = load_json(file_path)

    assert len(df) == 1
    assert df.iloc[0]["payment_id"] == 1


def test_load_json_with_data_key(tmp_path):
    file_path = tmp_path / "payments.json"
    file_path.write_text(json.dumps({"data": [{"payment_id": 1}, {"payment_id": 2}]}))

    df = load_json(file_path)

    assert len(df) == 2


def test_load_json_missing_file_raises(tmp_path):
    with pytest.raises(JsonFileNotFoundError):
        load_json(tmp_path / "missing.json")


def test_load_json_invalid_shape_raises(tmp_path):
    file_path = tmp_path / "bad.json"
    file_path.write_text(json.dumps({"not_data": []}))

    with pytest.raises(JsonLoadError):
        load_json(file_path)


def test_load_json_empty_list_raises(tmp_path):
    file_path = tmp_path / "empty.json"
    file_path.write_text(json.dumps([]))

    with pytest.raises(JsonLoadError):
        load_json(file_path)
