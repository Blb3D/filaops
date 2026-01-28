"""Add purchase_unit to purchase_order_lines

Revision ID: 019
Revises: 018
Create Date: 2025-12-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add purchase_unit column to purchase_order_lines table."""
    op.add_column("purchase_order_lines", sa.Column("purchase_unit", sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Remove purchase_unit column."""
    op.drop_column("purchase_order_lines", "purchase_unit")
