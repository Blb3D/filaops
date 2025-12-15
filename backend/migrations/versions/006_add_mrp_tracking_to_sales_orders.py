"""Add MRP tracking fields to sales_orders

Revision ID: 006_mrp_tracking
Revises: 005_units_of_measure
Create Date: 2025-12-15

Adds MRP tracking fields to sales_orders table:
- mrp_status: Track if MRP has been processed for this order
- mrp_run_id: Link to the MRP run that processed this order

These fields support the enhanced MRP flow that includes Sales Orders
as independent demand sources.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006_mrp_tracking'
down_revision: Union[str, Sequence[str], None] = '005_units_of_measure'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    # Get connection and inspector
    connection = op.get_bind()
    inspector = inspect(connection)

    # Get existing columns in sales_orders table
    sales_orders_columns = [c['name'] for c in inspector.get_columns('sales_orders')]

    # Add mrp_status column if it doesn't exist
    if 'mrp_status' not in sales_orders_columns:
        op.add_column(
            'sales_orders',
            sa.Column('mrp_status', sa.String(length=50), nullable=True)
        )

        # Create index (if it doesn't already exist)
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('sales_orders')]
        if 'ix_sales_orders_mrp_status' not in existing_indexes:
            op.create_index('ix_sales_orders_mrp_status', 'sales_orders', ['mrp_status'])

    # Add mrp_run_id column if it doesn't exist
    if 'mrp_run_id' not in sales_orders_columns:
        op.add_column(
            'sales_orders',
            sa.Column('mrp_run_id', sa.Integer(), nullable=True)
        )

        # Create index (if it doesn't already exist)
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('sales_orders')]
        if 'ix_sales_orders_mrp_run_id' not in existing_indexes:
            op.create_index('ix_sales_orders_mrp_run_id', 'sales_orders', ['mrp_run_id'])

        # Create foreign key (if it doesn't already exist)
        existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('sales_orders')]
        if 'fk_sales_orders_mrp_run_id' not in existing_fks:
            # Check if mrp_runs table exists
            existing_tables = inspector.get_table_names()
            if 'mrp_runs' in existing_tables:
                try:
                    op.create_foreign_key(
                        'fk_sales_orders_mrp_run_id',
                        'sales_orders', 'mrp_runs',
                        ['mrp_run_id'], ['id'],
                        ondelete='SET NULL'
                    )
                except Exception:
                    # FK creation may fail if mrp_runs table doesn't have proper PK - skip
                    pass


def downgrade() -> None:
    from sqlalchemy import inspect

    connection = op.get_bind()
    inspector = inspect(connection)

    # Drop foreign key if it exists
    existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('sales_orders')]
    if 'fk_sales_orders_mrp_run_id' in existing_fks:
        op.drop_constraint('fk_sales_orders_mrp_run_id', 'sales_orders', type_='foreignkey')

    # Drop indexes
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('sales_orders')]
    if 'ix_sales_orders_mrp_run_id' in existing_indexes:
        op.drop_index('ix_sales_orders_mrp_run_id', table_name='sales_orders')
    if 'ix_sales_orders_mrp_status' in existing_indexes:
        op.drop_index('ix_sales_orders_mrp_status', table_name='sales_orders')

    # Drop columns
    sales_orders_columns = [c['name'] for c in inspector.get_columns('sales_orders')]
    if 'mrp_run_id' in sales_orders_columns:
        op.drop_column('sales_orders', 'mrp_run_id')
    if 'mrp_status' in sales_orders_columns:
        op.drop_column('sales_orders', 'mrp_status')

