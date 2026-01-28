"""Backfill received_date for POs with status=received but no date

Revision ID: 027_backfill_po_received_date
Revises: 026_maintenance_tracking
Create Date: 2025-12-24

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "027_backfill_po_received_date"
down_revision = "026_maintenance_tracking"
branch_labels = None
depends_on = None


def upgrade():
    """Backfill received_date for POs that have status='received' but null received_date.
    Uses order_date as the fallback value."""

    # Update received POs that don't have a received_date
    # Use order_date as the received date (best approximation)
    op.execute("""
        UPDATE purchase_orders
        SET received_date = order_date
        WHERE status = 'received'
        AND received_date IS NULL
        AND order_date IS NOT NULL
    """)

    # For any remaining (where order_date is also null), use created_at date
    op.execute("""
        UPDATE purchase_orders
        SET received_date = DATE(created_at)
        WHERE status = 'received'
        AND received_date IS NULL
    """)


def downgrade():
    """No downgrade needed - this is a data backfill"""
    pass
