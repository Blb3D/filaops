"""
033: Add operation-level material tables for Manufacturing BOM

This migration creates:
1. routing_operation_materials - Template materials per operation
2. production_order_operation_materials - Actual consumption tracking per PO operation

This enables:
- Materials tied to specific operations (not just BOM-level)
- Precise MRP planning (know WHEN each material is needed)
- Operation-level consumption with lot tracking
- Partial release (can start printing even if short on shipping boxes)

Date: 2024-12-30
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "033_add_operation_materials"
down_revision = "032_cleanup_machines_table"
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # Table 1: routing_operation_materials (Template)
    # =========================================================================
    op.create_table(
        "routing_operation_materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "routing_operation_id",
            sa.Integer(),
            sa.ForeignKey("routing_operations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False, index=True),
        # Quantity
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_per", sa.String(20), server_default="unit", nullable=False),  # unit, batch, order
        sa.Column("unit", sa.String(20), server_default="EA", nullable=False),
        # Scrap/waste allowance
        sa.Column("scrap_factor", sa.Numeric(5, 2), server_default="0", nullable=True),
        # Flags
        sa.Column("is_cost_only", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_optional", sa.Boolean(), server_default="false", nullable=False),
        # Notes
        sa.Column("notes", sa.Text(), nullable=True),
        # Metadata
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    print("Created routing_operation_materials table")

    # =========================================================================
    # Table 2: production_order_operation_materials (Instance)
    # =========================================================================
    op.create_table(
        "production_order_operation_materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "production_order_operation_id",
            sa.Integer(),
            sa.ForeignKey("production_order_operations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False, index=True),
        sa.Column(
            "routing_operation_material_id",
            sa.Integer(),
            sa.ForeignKey("routing_operation_materials.id", ondelete="SET NULL"),
            nullable=True,
        ),  # Link back to template
        # Planned quantities (calculated from routing × PO qty)
        sa.Column("quantity_required", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit", sa.String(20), server_default="EA", nullable=False),
        # Actual consumption
        sa.Column("quantity_allocated", sa.Numeric(18, 6), server_default="0", nullable=False),
        sa.Column("quantity_consumed", sa.Numeric(18, 6), server_default="0", nullable=False),
        # Lot tracking
        sa.Column("lot_number", sa.String(100), nullable=True),
        sa.Column("inventory_transaction_id", sa.Integer(), sa.ForeignKey("inventory_transactions.id"), nullable=True),
        # Status: pending, allocated, consumed, returned
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        # Metadata
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("consumed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    print("Created production_order_operation_materials table")


def downgrade():
    op.drop_table("production_order_operation_materials")
    print("Dropped production_order_operation_materials table")

    op.drop_table("routing_operation_materials")
    print("Dropped routing_operation_materials table")
