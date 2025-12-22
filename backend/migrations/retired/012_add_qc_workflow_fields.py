"""Add QC workflow fields to production orders

Revision ID: 012_add_qc_workflow
Revises: 011_add_scrap_reasons
Create Date: 2025-12-16

Adds Quality Control (QC) tracking fields to production orders:
- qc_status: Track QC state (not_required, pending, passed, failed)
- qc_notes: Inspector notes
- qc_inspected_by: Who performed QC
- qc_inspected_at: When QC was performed
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '012_add_qc_workflow'
down_revision = '011_add_scrap_reasons'
branch_labels = None
depends_on = None


def upgrade():
    """Add QC workflow fields to production_orders table"""

    # Add qc_status column with default 'not_required'
    op.add_column(
        'production_orders',
        sa.Column('qc_status', sa.String(50), nullable=False, server_default='not_required')
    )

    # Add qc_notes column
    op.add_column(
        'production_orders',
        sa.Column('qc_notes', sa.Text(), nullable=True)
    )

    # Add qc_inspected_by column
    op.add_column(
        'production_orders',
        sa.Column('qc_inspected_by', sa.String(100), nullable=True)
    )

    # Add qc_inspected_at column
    op.add_column(
        'production_orders',
        sa.Column('qc_inspected_at', sa.DateTime(), nullable=True)
    )

    # Create index on qc_status for filtering
    op.create_index(
        'ix_production_orders_qc_status',
        'production_orders',
        ['qc_status']
    )


def downgrade():
    """Remove QC workflow fields from production_orders table"""

    # Drop index
    op.drop_index('ix_production_orders_qc_status', table_name='production_orders')

    # Drop columns
    op.drop_column('production_orders', 'qc_inspected_at')
    op.drop_column('production_orders', 'qc_inspected_by')
    op.drop_column('production_orders', 'qc_notes')
    op.drop_column('production_orders', 'qc_status')
