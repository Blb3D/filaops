"""Add scrap_reason column to production_order_operations

Revision ID: 034_add_operation_scrap_reason
Create Date: 2026-01-01

Tracks WHY pieces were scrapped (adhesion, layer_shift, stringing, etc)
when completing operations with quantity_scrapped > 0.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "034_add_operation_scrap_reason"
down_revision = "033_add_operation_materials"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("production_order_operations", sa.Column("scrap_reason", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("production_order_operations", "scrap_reason")
