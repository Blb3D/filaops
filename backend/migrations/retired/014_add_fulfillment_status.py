"""
Add fulfillment status and improve order workflow

Revision ID: 014_add_fulfillment_status
Revises: 
Create Date: 2025-12-16

This migration:
1. Adds fulfillment_status to sales_orders
2. Updates default sales order status from 'pending' to 'draft'
3. Adds QC workflow fields to production_orders
4. Creates indexes for new status fields
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql


# revision identifiers, used by Alembic.
revision = '014_add_fulfillment_status'
down_revision = '013_add_order_events'  # Depends on order events migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Upgrade database schema for improved order status workflow
    """
    # ========================================================================
    # SALES ORDERS - Add fulfillment_status
    # ========================================================================
    
    # Add fulfillment_status column
    op.add_column(
        'sales_orders',
        sa.Column('fulfillment_status', sa.String(50), nullable=False, server_default='pending')
    )
    
    # Create index for fulfillment_status (improves shipping queue queries)
    op.create_index(
        'ix_sales_orders_fulfillment_status',
        'sales_orders',
        ['fulfillment_status']
    )
    
    # ========================================================================
    # SALES ORDERS - Migrate existing status values
    # ========================================================================
    
    # Update existing orders with new status logic
    # Old 'pending' â†’ 'draft' (not yet paid)
    # Old 'confirmed' â†’ 'confirmed' (paid, ready for production)
    # Old 'in_production' â†’ 'in_production' (manufacturing)
    # Old 'quality_check' â†’ 'ready_to_ship' (QC is now at WO level)
    
    connection = op.get_bind()
    
    # Migrate old 'pending' status to 'draft' OR 'pending_payment'
    # Check payment_status to determine which
    connection.execute(sa.text("""
        UPDATE sales_orders 
        SET status = CASE 
            WHEN payment_status = 'paid' THEN 'confirmed'
            WHEN status = 'pending' THEN 'pending_payment'
            ELSE status
        END
        WHERE status = 'pending'
    """))
    
    # Migrate 'quality_check' to 'ready_to_ship'
    connection.execute(sa.text("""
        UPDATE sales_orders 
        SET status = 'ready_to_ship',
            fulfillment_status = 'ready'
        WHERE status = 'quality_check'
    """))
    
    # Set fulfillment_status based on current status
    connection.execute(sa.text("""
        UPDATE sales_orders 
        SET fulfillment_status = CASE 
            WHEN status IN ('shipped', 'delivered', 'completed') THEN 'shipped'
            WHEN status = 'ready_to_ship' THEN 'ready'
            ELSE 'pending'
        END
    """))
    
    # ========================================================================
    # PRODUCTION ORDERS - Add QC fields (if not already present)
    # ========================================================================
    
    # Check if qc_status exists, add if missing
    # (Some installs may already have this from previous migrations)
    try:
        op.add_column(
            'production_orders',
            sa.Column('qc_status', sa.String(50), nullable=False, server_default='not_required')
        )
    except Exception:
        # Column already exists, skip
        pass
    
    try:
        op.add_column(
            'production_orders',
            sa.Column('qc_notes', sa.Text(), nullable=True)
        )
    except Exception:
        pass
    
    try:
        op.add_column(
            'production_orders',
            sa.Column('qc_inspected_by', sa.String(100), nullable=True)
        )
    except Exception:
        pass
    
    try:
        op.add_column(
            'production_orders',
            sa.Column('qc_inspected_at', sa.DateTime(), nullable=True)
        )
    except Exception:
        pass
    
    # ========================================================================
    # PRODUCTION ORDERS - Migrate existing status values
    # ========================================================================
    
    # Migrate old 'complete' to 'closed' (if QC passed or not required)
    connection.execute(sa.text("""
        UPDATE production_orders 
        SET status = 'closed'
        WHERE status = 'complete'
    """))
    
    # ========================================================================
    # CREATE AUDIT TRAIL (Optional - for tracking status changes)
    # ========================================================================
    
    # Uncomment if you want to track all status changes
    # op.create_table(
    #     'order_status_history',
    #     sa.Column('id', sa.Integer(), nullable=False),
    #     sa.Column('order_type', sa.String(20), nullable=False),  # 'sales' or 'production'
    #     sa.Column('order_id', sa.Integer(), nullable=False),
    #     sa.Column('old_status', sa.String(50), nullable=True),
    #     sa.Column('new_status', sa.String(50), nullable=False),
    #     sa.Column('changed_by', sa.String(100), nullable=True),
    #     sa.Column('changed_at', sa.DateTime(), nullable=False),
    #     sa.Column('reason', sa.Text(), nullable=True),
    #     sa.PrimaryKeyConstraint('id')
    # )
    # op.create_index('ix_status_history_order', 'order_status_history', ['order_type', 'order_id'])


def downgrade():
    """
    Rollback changes if needed
    """
    # Drop fulfillment_status
    op.drop_index('ix_sales_orders_fulfillment_status', table_name='sales_orders')
    op.drop_column('sales_orders', 'fulfillment_status')
    
    # Revert status migrations (best effort)
    connection = op.get_bind()
    
    connection.execute(sa.text("""
        UPDATE sales_orders 
        SET status = 'pending'
        WHERE status IN ('draft', 'pending_payment', 'payment_failed')
    """))
    
    connection.execute(sa.text("""
        UPDATE sales_orders 
        SET status = 'quality_check'
        WHERE status = 'ready_to_ship'
    """))
    
    connection.execute(sa.text("""
        UPDATE production_orders 
        SET status = 'complete'
        WHERE status = 'closed'
    """))
    
    # Note: QC columns are left in place to avoid data loss
    # They were optional additions and safe to keep
