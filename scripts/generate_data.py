"""
Generate synthetic e-commerce data for local development and demos.

Produces customers.csv, stores.csv, products.csv, orders.csv,
order_items.csv and payments.json in data/raw/. A small percentage of
rows are intentionally broken (nulls, duplicates, invalid values) so the
validation and data quality layers have something real to catch.

Usage:
    python scripts/generate_data.py                  # small sample (default)
    python scripts/generate_data.py --scale full      # full-size dataset
"""

import argparse
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Ishaan", "Priya", "Ananya", "Diya", "Sara",
    "James", "Emma", "Liam", "Olivia", "Noah", "Ava", "Mia", "Lucas",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Reddy", "Iyer", "Khan", "Patel", "Singh",
    "Smith", "Johnson", "Brown", "Garcia", "Miller", "Davis",
]
CITIES = [
    ("Kanpur", "Uttar Pradesh", "India"),
    ("Mumbai", "Maharashtra", "India"),
    ("Bengaluru", "Karnataka", "India"),
    ("Delhi", "Delhi", "India"),
    ("New York", "NY", "USA"),
    ("Austin", "TX", "USA"),
    ("London", "England", "UK"),
]
CATEGORIES = ["Electronics", "Clothing", "Home & Kitchen", "Books", "Sports", "Beauty", "Toys"]
PAYMENT_METHODS = ["credit_card", "debit_card", "upi", "net_banking", "cod"]
PAYMENT_STATUSES = ["success", "failed", "pending", "refunded"]
ORDER_STATUSES = ["placed", "shipped", "delivered", "cancelled", "returned"]

# Fraction of rows to deliberately corrupt in each table, so the pipeline's
# validation and data-quality layers have real problems to catch.
BAD_RECORD_RATE = 0.02


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def generate_customers(n: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        city, state, country = random.choice(CITIES)
        row = {
            "customer_id": i,
            "first_name": random.choice(FIRST_NAMES),
            "last_name": random.choice(LAST_NAMES),
            "email": f"customer{i}@example.com",
            "phone": f"+91-9{random.randint(100000000, 999999999)}",
            "city": city,
            "state": state,
            "country": country,
            "signup_date": _random_date(date(2023, 1, 1), date(2026, 9, 1)).isoformat(),
        }
        rows.append(row)

    # Inject bad records: missing email, duplicate customer_id, bad date
    for row in random.sample(rows, k=int(n * BAD_RECORD_RATE)):
        flaw = random.choice(["missing_email", "bad_date", "duplicate"])
        if flaw == "missing_email":
            row["email"] = None
        elif flaw == "bad_date":
            row["signup_date"] = "not-a-date"
        elif flaw == "duplicate" and len(rows) > 1:
            rows.append(dict(row))  # duplicate customer_id

    return pd.DataFrame(rows)


def generate_stores(n: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        city, state, country = random.choice(CITIES)
        rows.append(
            {
                "store_id": i,
                "store_name": f"{random.choice(LAST_NAMES)} {random.choice(['Mart', 'Store', 'Retail', 'Bazaar'])}",
                "city": city,
                "state": state,
                "country": country,
            }
        )
    return pd.DataFrame(rows)


def generate_products(n: int, store_count: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        row = {
            "product_id": i,
            "product_name": f"{random.choice(CATEGORIES)} Item {i}",
            "category": random.choice(CATEGORIES),
            "price": round(random.uniform(5, 500), 2),
            "store_id": random.randint(1, store_count),
        }
        rows.append(row)

    for row in random.sample(rows, k=int(n * BAD_RECORD_RATE)):
        row["price"] = -abs(row["price"])  # invalid negative price

    return pd.DataFrame(rows)


def generate_orders(n: int, customer_ids: list[int], store_count: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        rows.append(
            {
                "order_id": i,
                "customer_id": random.choice(customer_ids),
                "store_id": random.randint(1, store_count),
                "order_date": _random_date(date(2024, 1, 1), date(2026, 9, 1)).isoformat(),
                "order_status": random.choice(ORDER_STATUSES),
            }
        )

    for row in random.sample(rows, k=int(n * BAD_RECORD_RATE)):
        row["order_date"] = "31-31-2026"  # malformed date

    return pd.DataFrame(rows)


def generate_order_items(n: int, order_count: int, product_ids: list[int]) -> pd.DataFrame:
    """Generate line items while preserving product/order referential integrity.

    Every order receives one valid line item first. A small number of extra
    rows are deliberately corrupted after generation so validation has real
    work to do, but clean rows always have a non-negative line total.
    """
    if not product_ids:
        raise ValueError("product_ids must contain at least one valid product ID")

    def make_item(order_id: int, item_id: int) -> dict:
        quantity = random.randint(1, 5)
        unit_price = round(random.uniform(5, 500), 2)
        max_discount = round(quantity * unit_price, 2)
        discount = round(random.uniform(0, min(20, max_discount)), 2)
        return {
            "order_item_id": item_id,
            "order_id": order_id,
            "product_id": random.choice(product_ids),
            "quantity": quantity,
            "unit_price": unit_price,
            "discount": discount,
        }

    rows = []
    item_id = 1

    # Guarantee coverage: every order starts with one clean line item.
    for order_id in range(1, order_count + 1):
        rows.append(make_item(order_id, item_id))
        item_id += 1

    extra_rows = []
    while item_id <= n:
        extra_rows.append(make_item(random.randint(1, order_count), item_id))
        item_id += 1

    # Corrupt only extra rows, so a bad row cannot remove an order's only
    # valid line item and make the warehouse completeness test fail.
    if extra_rows:
        bad_count = min(len(extra_rows), int(n * BAD_RECORD_RATE))
        for row in random.sample(extra_rows, k=bad_count):
            flaw = random.choice(["negative_quantity", "negative_price"])
            if flaw == "negative_quantity":
                row["quantity"] = -row["quantity"]
            else:
                row["unit_price"] = -abs(row["unit_price"])

    return pd.DataFrame(rows + extra_rows)


def generate_payments(n: int, order_count: int) -> list[dict]:
    records = []
    for i in range(1, n + 1):
        records.append(
            {
                "payment_id": i,
                "order_id": random.randint(1, order_count),
                "payment_method": random.choice(PAYMENT_METHODS),
                "amount": round(random.uniform(5, 2500), 2),
                "payment_status": random.choice(PAYMENT_STATUSES),
                "payment_date": _random_date(date(2024, 1, 1), date(2026, 9, 1)).isoformat(),
            }
        )

    bad_indices = random.sample(range(n), k=int(n * BAD_RECORD_RATE))
    for idx in bad_indices:
        flaw = random.choice(["bad_status", "negative_amount"])
        if flaw == "bad_status":
            records[idx]["payment_status"] = "unknown_status"
        else:
            records[idx]["amount"] = -abs(records[idx]["amount"])

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic e-commerce data")
    parser.add_argument(
        "--scale",
        choices=["sample", "full"],
        default="sample",
        help="'sample' (default, small - good for git/demo) or 'full' (large dataset)",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.scale == "sample":
        counts = dict(customers=500, stores=20, products=200, orders=1500, order_items=3500, payments=1500)
    else:
        counts = dict(
            customers=10_000, stores=200, products=1_000, orders=50_000,
            order_items=100_000, payments=50_000,
        )

    print(f"Generating '{args.scale}' dataset: {counts}")

    customers = generate_customers(counts["customers"])
    stores = generate_stores(counts["stores"])
    products = generate_products(counts["products"], counts["stores"])

    # Do not let intentionally rejected customer/product rows become
    # accidental referential-integrity failures in otherwise valid orders.
    valid_customer_ids = (
        customers.loc[
            customers["email"].notna()
            & pd.to_datetime(customers["signup_date"], errors="coerce").notna(),
            "customer_id",
        ]
        .drop_duplicates()
        .astype(int)
        .tolist()
    )
    valid_product_ids = (
        products.loc[products["price"] >= 0, "product_id"]
        .drop_duplicates()
        .astype(int)
        .tolist()
    )

    orders = generate_orders(counts["orders"], valid_customer_ids, counts["stores"])
    order_items = generate_order_items(
        counts["order_items"], counts["orders"], valid_product_ids
    )
    payments = generate_payments(counts["payments"], counts["orders"])

    customers.to_csv(OUTPUT_DIR / "customers.csv", index=False)
    stores.to_csv(OUTPUT_DIR / "stores.csv", index=False)
    products.to_csv(OUTPUT_DIR / "products.csv", index=False)
    orders.to_csv(OUTPUT_DIR / "orders.csv", index=False)
    order_items.to_csv(OUTPUT_DIR / "order_items.csv", index=False)

    with (OUTPUT_DIR / "payments.json").open("w", encoding="utf-8") as f:
        json.dump(payments, f, indent=2)

    print(f"Wrote files to {OUTPUT_DIR}")
    for name, count in counts.items():
        print(f"  {name}: ~{count} rows (some intentionally invalid)")


if __name__ == "__main__":
    main()
