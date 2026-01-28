"""Add downtime and parts tracking to maintenance logs

Revision ID: 026_maintenance_tracking
Revises: 025_add_maintenance_logs_table
Create Date: 2024-12-24

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "026_maintenance_tracking"
down_revision = "025_add_maintenance_logs_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add downtime_minutes column for OEE tracking
    op.add_column("maintenance_logs", sa.Column("downtime_minutes", sa.Integer(), nullable=True))

    # Add parts_used column for tracking parts consumed during maintenance
    op.add_column("maintenance_logs", sa.Column("parts_used", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("maintenance_logs", "parts_used")
    op.drop_column("maintenance_logs", "downtime_minutes")
