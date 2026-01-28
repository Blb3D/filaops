"""020_add_business_hours_to_company_settings

Revision ID: 020
Revises: 019
Create Date: 2025-12-22 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: Union[str, Sequence[str], None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add business hours fields to company_settings table."""
    op.add_column("company_settings", sa.Column("business_hours_start", sa.Integer(), nullable=True))
    op.add_column("company_settings", sa.Column("business_hours_end", sa.Integer(), nullable=True))
    op.add_column("company_settings", sa.Column("business_days_per_week", sa.Integer(), nullable=True))
    op.add_column("company_settings", sa.Column("business_work_days", sa.String(length=20), nullable=True))

    # Set default values for existing rows
    op.execute("""
        UPDATE company_settings 
        SET business_hours_start = 8,
            business_hours_end = 16,
            business_days_per_week = 5,
            business_work_days = '0,1,2,3,4'
        WHERE id = 1
    """)


def downgrade() -> None:
    """Remove business hours fields from company_settings table."""
    op.drop_column("company_settings", "business_work_days")
    op.drop_column("company_settings", "business_days_per_week")
    op.drop_column("company_settings", "business_hours_end")
    op.drop_column("company_settings", "business_hours_start")
