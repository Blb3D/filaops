"""Quick cleanup script for E2E tests."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()

tables = [
    "inventory_transactions",
    "inventory",
    "inventory_locations",
    "purchase_order_lines",
    "purchase_orders",
    "production_order_operations",
    "production_orders",
    "sales_order_lines",
    "sales_orders",
    "bom_lines",
    "boms",
    "routing_operations",
    "routings",
    "quotes",
    "products",
    "vendors",
    "refresh_tokens",
]

print("Cleaning database for E2E tests...")
for table in tables:
    try:
        db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        print(f"  Truncated: {table}")
    except Exception as e:
        print(f"  Skip {table}: {e}")

# Delete test users only
db.execute(text("DELETE FROM users WHERE email LIKE '%@filaops.test'"))
print("  Deleted test users")

db.commit()
print("Done!")
db.close()
