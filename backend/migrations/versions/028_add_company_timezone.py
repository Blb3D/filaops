"""Add timezone column to company_settings

Revision ID: 028_add_company_timezone
Revises: 027_backfill_po_received_date
Create Date: 2025-12-24

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "028_add_company_timezone"
down_revision = "027_backfill_po_received_date"
branch_labels = None
depends_on = None


def upgrade():
    """Add timezone column to company_settings table."""
    op.add_column(
        "company_settings", sa.Column("timezone", sa.String(50), nullable=True, server_default="America/New_York")
    )


def downgrade():
    """Remove timezone column from company_settings table."""
    op.drop_column("company_settings", "timezone")
