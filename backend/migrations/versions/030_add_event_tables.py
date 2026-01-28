"""Add PurchasingEvent and ShippingEvent tables

Revision ID: 030_add_event_tables
Revises: 029_add_transaction_date
Create Date: 2025-12-24

These tables provide event tracking/audit trails for purchase orders
and shipping activities, complementing the existing OrderEvent table
for sales orders.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "030_add_event_tables"
down_revision = "029_add_transaction_date"
branch_labels = None
depends_on = None


def upgrade():
    """Create purchasing_events and shipping_events tables."""

    # Create purchasing_events table
    op.create_table(
        "purchasing_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_order_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("old_value", sa.String(100), nullable=True),
        sa.Column("new_value", sa.String(100), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("metadata_key", sa.String(100), nullable=True),
        sa.Column("metadata_value", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="NO ACTION"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchasing_events_id", "purchasing_events", ["id"])
    op.create_index("ix_purchasing_events_purchase_order_id", "purchasing_events", ["purchase_order_id"])
    op.create_index("ix_purchasing_events_user_id", "purchasing_events", ["user_id"])
    op.create_index("ix_purchasing_events_event_type", "purchasing_events", ["event_type"])
    op.create_index("ix_purchasing_events_event_date", "purchasing_events", ["event_date"])
    op.create_index("ix_purchasing_events_created_at", "purchasing_events", ["created_at"])

    # Create shipping_events table
    op.create_table(
        "shipping_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sales_order_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tracking_number", sa.String(100), nullable=True),
        sa.Column("carrier", sa.String(50), nullable=True),
        sa.Column("location_city", sa.String(100), nullable=True),
        sa.Column("location_state", sa.String(50), nullable=True),
        sa.Column("location_zip", sa.String(20), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("event_timestamp", sa.DateTime(), nullable=True),
        sa.Column("metadata_key", sa.String(100), nullable=True),
        sa.Column("metadata_value", sa.String(255), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="NO ACTION"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shipping_events_id", "shipping_events", ["id"])
    op.create_index("ix_shipping_events_sales_order_id", "shipping_events", ["sales_order_id"])
    op.create_index("ix_shipping_events_user_id", "shipping_events", ["user_id"])
    op.create_index("ix_shipping_events_event_type", "shipping_events", ["event_type"])
    op.create_index("ix_shipping_events_tracking_number", "shipping_events", ["tracking_number"])
    op.create_index("ix_shipping_events_event_date", "shipping_events", ["event_date"])
    op.create_index("ix_shipping_events_created_at", "shipping_events", ["created_at"])


def downgrade():
    """Drop purchasing_events and shipping_events tables."""
    op.drop_table("shipping_events")
    op.drop_table("purchasing_events")
