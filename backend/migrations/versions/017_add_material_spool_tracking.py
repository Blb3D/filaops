"""Add material spool tracking tables

Revision ID: 017
Revises: b1815de543ea
Create Date: 2025-12-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: Union[str, None] = "b1815de543ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create material_spools table
    op.create_table(
        "material_spools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("spool_number", sa.String(length=100), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("initial_weight_kg", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("current_weight_kg", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("received_date", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("expiry_date", sa.DateTime(), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("supplier_lot_number", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["inventory_locations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("spool_number"),
    )
    op.create_index(op.f("ix_material_spools_spool_number"), "material_spools", ["spool_number"], unique=True)
    op.create_index(op.f("ix_material_spools_product_id"), "material_spools", ["product_id"], unique=False)
    op.create_index(op.f("ix_material_spools_status"), "material_spools", ["status"], unique=False)

    # Create production_order_spools junction table
    op.create_table(
        "production_order_spools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("production_order_id", sa.Integer(), nullable=False),
        sa.Column("spool_id", sa.Integer(), nullable=False),
        sa.Column("weight_consumed_kg", sa.Numeric(precision=10, scale=3), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["production_order_id"],
            ["production_orders.id"],
        ),
        sa.ForeignKeyConstraint(
            ["spool_id"],
            ["material_spools.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_production_order_spools_production_order_id"),
        "production_order_spools",
        ["production_order_id"],
        unique=False,
    )
    op.create_index(op.f("ix_production_order_spools_spool_id"), "production_order_spools", ["spool_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_production_order_spools_spool_id"), table_name="production_order_spools")
    op.drop_index(op.f("ix_production_order_spools_production_order_id"), table_name="production_order_spools")
    op.drop_table("production_order_spools")
    op.drop_index(op.f("ix_material_spools_status"), table_name="material_spools")
    op.drop_index(op.f("ix_material_spools_product_id"), table_name="material_spools")
    op.drop_index(op.f("ix_material_spools_spool_number"), table_name="material_spools")
    op.drop_table("material_spools")
