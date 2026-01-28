"""Add order events table for activity timeline

Revision ID: 013_add_order_events
Revises: 012_add_qc_workflow_fields
Create Date: 2025-12-16

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "013_add_order_events"
down_revision = "012_add_qc_workflow"
branch_labels = None
depends_on = None


def upgrade():
    # Create order_events table
    op.create_table(
        "order_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sales_order_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("old_value", sa.String(100), nullable=True),
        sa.Column("new_value", sa.String(100), nullable=True),
        sa.Column("metadata_key", sa.String(100), nullable=True),
        sa.Column("metadata_value", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="NO ACTION"),
    )

    # Create indexes for common queries
    op.create_index("ix_order_events_sales_order_id", "order_events", ["sales_order_id"])
    op.create_index("ix_order_events_event_type", "order_events", ["event_type"])
    op.create_index("ix_order_events_created_at", "order_events", ["created_at"])
    op.create_index("ix_order_events_user_id", "order_events", ["user_id"])


def downgrade():
    op.drop_index("ix_order_events_user_id", table_name="order_events")
    op.drop_index("ix_order_events_created_at", table_name="order_events")
    op.drop_index("ix_order_events_event_type", table_name="order_events")
    op.drop_index("ix_order_events_sales_order_id", table_name="order_events")
    op.drop_table("order_events")
