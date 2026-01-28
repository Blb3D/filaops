"""Add production order split fields

Revision ID: 004_production_order_split
Revises: 003_add_sales_order_product_id
Create Date: 2025-12-11

Adds parent_order_id and split_sequence columns to production_orders table
for supporting split orders across multiple machines.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004_production_order_split"
down_revision: Union[str, Sequence[str], None] = "003_sales_order_product"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    connection = op.get_bind()
    inspector = inspect(connection)

    # Get existing columns in production_orders table
    existing_columns = [c["name"] for c in inspector.get_columns("production_orders")]

    # Add parent_order_id column if it doesn't exist
    if "parent_order_id" not in existing_columns:
        op.add_column("production_orders", sa.Column("parent_order_id", sa.Integer(), nullable=True))
        op.create_index("ix_production_orders_parent_order_id", "production_orders", ["parent_order_id"])
        op.create_foreign_key(
            "fk_production_orders_parent_order_id",
            "production_orders",
            "production_orders",
            ["parent_order_id"],
            ["id"],
        )

    # Add split_sequence column if it doesn't exist
    if "split_sequence" not in existing_columns:
        op.add_column("production_orders", sa.Column("split_sequence", sa.Integer(), nullable=True))


def downgrade() -> None:
    # Drop foreign key first
    op.drop_constraint("fk_production_orders_parent_order_id", "production_orders", type_="foreignkey")
    op.drop_index("ix_production_orders_parent_order_id", table_name="production_orders")

    # Drop columns
    op.drop_column("production_orders", "split_sequence")
    op.drop_column("production_orders", "parent_order_id")
