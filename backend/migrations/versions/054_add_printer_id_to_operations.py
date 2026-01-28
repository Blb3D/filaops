"""Add printer_id column to production_order_operations

Revision ID: 054
Revises: 053
Create Date: 2026-01-20

Adds printer_id column to production_order_operations table to properly
track which printer is assigned to an operation. This fixes the 500 error
when scheduling operations on printers (previously the code tried to use
negative resource_id values which violated the foreign key constraint).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "054_add_printer_id"
down_revision = "053_scrap_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add printer_id column to production_order_operations
    op.add_column("production_order_operations", sa.Column("printer_id", sa.Integer(), nullable=True))

    # Add foreign key constraint to printers table
    op.create_foreign_key(
        "fk_production_order_operations_printer_id",
        "production_order_operations",
        "printers",
        ["printer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index for faster lookups
    op.create_index("ix_production_order_operations_printer_id", "production_order_operations", ["printer_id"])


def downgrade() -> None:
    # Remove index
    op.drop_index("ix_production_order_operations_printer_id", "production_order_operations")

    # Remove foreign key
    op.drop_constraint("fk_production_order_operations_printer_id", "production_order_operations", type_="foreignkey")

    # Remove column
    op.drop_column("production_order_operations", "printer_id")
