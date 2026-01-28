"""Add product_id to sales_orders

Revision ID: 003_sales_order_product
Revises: 002_company_settings
Create Date: 2025-12-11

Adds product_id foreign key to sales_orders table to link quote-based orders
to their associated product for BOM explosion and material requirements.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_sales_order_product"
down_revision: Union[str, Sequence[str], None] = "002_company_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    # Get connection and inspector
    connection = op.get_bind()
    inspector = inspect(connection)

    # Get existing columns in sales_orders table
    sales_orders_columns = [c["name"] for c in inspector.get_columns("sales_orders")]

    # Add product_id column if it doesn't exist
    if "product_id" not in sales_orders_columns:
        op.add_column("sales_orders", sa.Column("product_id", sa.Integer(), nullable=True))

        # Create index (if it doesn't already exist)
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("sales_orders")]
        if "ix_sales_orders_product_id" not in existing_indexes:
            op.create_index("ix_sales_orders_product_id", "sales_orders", ["product_id"])

        # Create foreign key (if it doesn't already exist)
        existing_fks = [fk["name"] for fk in inspector.get_foreign_keys("sales_orders")]
        if "fk_sales_orders_product_id" not in existing_fks:
            try:
                op.create_foreign_key(
                    "fk_sales_orders_product_id",
                    "sales_orders",
                    "products",
                    ["product_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            except Exception:
                # FK creation may fail if products table doesn't have proper PK - skip
                pass


def downgrade() -> None:
    # Drop foreign key
    op.drop_constraint("fk_sales_orders_product_id", "sales_orders", type_="foreignkey")

    # Drop index
    op.drop_index("ix_sales_orders_product_id", table_name="sales_orders")

    # Drop column
    op.drop_column("sales_orders", "product_id")
