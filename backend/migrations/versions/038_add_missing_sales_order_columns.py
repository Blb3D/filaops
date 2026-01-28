"""add_missing_sales_order_columns

Revision ID: 038_add_missing_so_cols
Revises: 037_add_anthropic_model
Create Date: 2026-01-07

This migration adds columns that were in the model but missing from the
initial migration:
- color
- customer_id (FK to users)
- customer_name
- customer_email
- customer_phone
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "038_add_missing_so_cols"
down_revision: Union[str, Sequence[str], None] = "037_add_anthropic_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to sales_orders table."""
    # Add color column
    op.add_column("sales_orders", sa.Column("color", sa.String(50), nullable=True))

    # Add customer columns
    op.add_column("sales_orders", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.add_column("sales_orders", sa.Column("customer_name", sa.String(200), nullable=True))
    op.add_column("sales_orders", sa.Column("customer_email", sa.String(255), nullable=True))
    op.add_column("sales_orders", sa.Column("customer_phone", sa.String(30), nullable=True))

    # Add foreign key constraint for customer_id
    op.create_foreign_key(
        "fk_sales_orders_customer_id_users", "sales_orders", "users", ["customer_id"], ["id"], ondelete="SET NULL"
    )

    # Add index for customer_id for better query performance
    op.create_index("ix_sales_orders_customer_id", "sales_orders", ["customer_id"])


def downgrade() -> None:
    """Remove the added columns from sales_orders table."""
    # Remove index
    op.drop_index("ix_sales_orders_customer_id", table_name="sales_orders")

    # Remove foreign key
    op.drop_constraint("fk_sales_orders_customer_id_users", "sales_orders", type_="foreignkey")

    # Remove columns
    op.drop_column("sales_orders", "customer_phone")
    op.drop_column("sales_orders", "customer_email")
    op.drop_column("sales_orders", "customer_name")
    op.drop_column("sales_orders", "customer_id")
    op.drop_column("sales_orders", "color")
