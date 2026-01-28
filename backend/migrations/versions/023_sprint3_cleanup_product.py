"""Sprint 3-4: Remove legacy fields from products table

Revision ID: 023_sprint3_cleanup_product
Revises: 022_sprint3_cleanup_work_center
Create Date: 2025-12-23 (Sprint 3-4 - Data Model Cleanup)

Product model had legacy fields that are now replaced:
- 'category' (string) -> 'category_id' (FK to item_categories)
- 'cost' (numeric) -> 'standard_cost' (numeric)
- 'weight' (numeric) -> 'weight_oz' (numeric)

All legacy fields have 0 records using them, so this is safe to drop.

NOTE: Uses defensive programming - skips if columns don't exist.

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "023_sprint3_cleanup_product"
down_revision = "022_sprint3_cleanup_work_center"
branch_labels = None
depends_on = None


def _column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    try:
        bind = op.get_bind()
        inspector = inspect(bind)
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def _drop_column_if_exists(table_name, column_name):
    """Drop a column only if it exists."""
    if _column_exists(table_name, column_name):
        try:
            op.drop_column(table_name, column_name)
            print(f"  Dropped column '{column_name}' from {table_name}")
        except Exception as e:
            print(f"  Could not drop '{column_name}' from {table_name}: {e}")
    else:
        print(f"  Column '{column_name}' does not exist in {table_name}, skipping...")


def _add_column_if_not_exists(table_name, column):
    """Add a column only if it doesn't exist."""
    if not _column_exists(table_name, column.name):
        try:
            op.add_column(table_name, column)
            print(f"  Added column '{column.name}' to {table_name}")
        except Exception as e:
            print(f"  Could not add '{column.name}' to {table_name}: {e}")
    else:
        print(f"  Column '{column.name}' already exists in {table_name}, skipping...")


def upgrade():
    # Drop legacy columns that have no data
    _drop_column_if_exists("products", "category")
    _drop_column_if_exists("products", "cost")
    _drop_column_if_exists("products", "weight")


def downgrade():
    # Re-add legacy columns
    _add_column_if_not_exists("products", sa.Column("weight", sa.Numeric(precision=18, scale=4), nullable=True))
    _add_column_if_not_exists("products", sa.Column("cost", sa.Numeric(precision=18, scale=4), nullable=True))
    _add_column_if_not_exists("products", sa.Column("category", sa.String(length=100), nullable=True))
