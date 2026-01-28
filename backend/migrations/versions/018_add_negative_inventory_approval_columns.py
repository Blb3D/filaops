"""Add negative inventory approval columns to inventory_transactions

Revision ID: 018
Revises: 017
Create Date: 2025-12-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add negative inventory approval columns to inventory_transactions table."""
    # Add columns for negative inventory approval workflow
    op.add_column(
        "inventory_transactions", sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column("inventory_transactions", sa.Column("approval_reason", sa.Text(), nullable=True))
    op.add_column("inventory_transactions", sa.Column("approved_by", sa.String(length=100), nullable=True))
    op.add_column("inventory_transactions", sa.Column("approved_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove negative inventory approval columns."""
    op.drop_column("inventory_transactions", "approved_at")
    op.drop_column("inventory_transactions", "approved_by")
    op.drop_column("inventory_transactions", "approval_reason")
    op.drop_column("inventory_transactions", "requires_approval")
