"""Add stocking_policy column to products table

Revision ID: 031_add_stocking_policy
Revises: 030_add_event_tables
Create Date: 2025-01-01 00:00:00.000000

This migration adds the stocking_policy column to differentiate between:
- 'stocked': Items that should be kept on hand at reorder_point levels
- 'on_demand': Items only ordered when MRP shows actual demand
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "031_add_stocking_policy"
down_revision = "030_add_event_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add stocking_policy column with default 'on_demand'
    op.add_column("products", sa.Column("stocking_policy", sa.String(20), nullable=False, server_default="on_demand"))

    # Add index for efficient filtering by stocking policy
    op.create_index("ix_products_stocking_policy", "products", ["stocking_policy"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products_stocking_policy", table_name="products")
    op.drop_column("products", "stocking_policy")
