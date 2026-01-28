"""add_production_order_materials_table

Revision ID: 65be66a7c00f
Revises: 020
Create Date: 2025-12-22 23:41:37.359436

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "65be66a7c00f"
down_revision: Union[str, Sequence[str], None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add production_order_materials table for material substitutions."""
    # Create production_order_materials table
    op.create_table(
        "production_order_materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("production_order_id", sa.Integer(), nullable=False),
        sa.Column("bom_line_id", sa.Integer(), nullable=True),
        sa.Column("original_product_id", sa.Integer(), nullable=False),
        sa.Column("original_quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("substitute_product_id", sa.Integer(), nullable=False),
        sa.Column("planned_quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("actual_quantity_used", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["production_order_id"], ["production_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bom_line_id"], ["bom_lines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["original_product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["substitute_product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index("idx_po_materials_production_order", "production_order_materials", ["production_order_id"])
    op.create_index("idx_po_materials_original_product", "production_order_materials", ["original_product_id"])
    op.create_index("idx_po_materials_substitute_product", "production_order_materials", ["substitute_product_id"])


def downgrade() -> None:
    """Remove production_order_materials table."""
    op.drop_index("idx_po_materials_substitute_product", table_name="production_order_materials")
    op.drop_index("idx_po_materials_original_product", table_name="production_order_materials")
    op.drop_index("idx_po_materials_production_order", table_name="production_order_materials")
    op.drop_table("production_order_materials")
