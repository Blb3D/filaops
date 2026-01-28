"""Add maintenance logs table

Revision ID: 025_add_maintenance_logs_table
Revises: 024_sprint3_add_fk_indexes
Create Date: 2025-12-24

Adds maintenance logging functionality for printer maintenance tracking.
Freemium feature: Basic maintenance logging and scheduling.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "025_add_maintenance_logs_table"
down_revision: Union[str, None] = "024_sprint3_add_fk_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add maintenance_logs table."""
    op.create_table(
        "maintenance_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("printer_id", sa.Integer(), nullable=False),
        sa.Column("maintenance_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.String(length=100), nullable=True),
        sa.Column("performed_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("next_due_at", sa.DateTime(), nullable=True),
        sa.Column("cost", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["printer_id"], ["printers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for better query performance
    op.create_index(op.f("ix_maintenance_logs_printer_id"), "maintenance_logs", ["printer_id"], unique=False)
    op.create_index(
        op.f("ix_maintenance_logs_maintenance_type"), "maintenance_logs", ["maintenance_type"], unique=False
    )
    op.create_index(op.f("ix_maintenance_logs_performed_at"), "maintenance_logs", ["performed_at"], unique=False)
    op.create_index(op.f("ix_maintenance_logs_next_due_at"), "maintenance_logs", ["next_due_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema - remove maintenance_logs table."""
    op.drop_index(op.f("ix_maintenance_logs_next_due_at"), table_name="maintenance_logs")
    op.drop_index(op.f("ix_maintenance_logs_performed_at"), table_name="maintenance_logs")
    op.drop_index(op.f("ix_maintenance_logs_maintenance_type"), table_name="maintenance_logs")
    op.drop_index(op.f("ix_maintenance_logs_printer_id"), table_name="maintenance_logs")
    op.drop_table("maintenance_logs")
