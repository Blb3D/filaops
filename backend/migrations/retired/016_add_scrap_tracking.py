"""add_scrap_tracking_columns_to_production_orders

Revision ID: 016_add_scrap_tracking
Revises: 015_add_work_centers_and_machines
Create Date: 2025-12-17 22:09:11.226349

Adds scrap tracking columns to production_orders:
- scrap_reason: Why the order was scrapped
- scrapped_at: When it was scrapped
- remake_of_id: Links a remake order to the original failed order
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '016_add_scrap_tracking'
down_revision: Union[str, Sequence[str], None] = '015_add_work_centers_and_machines'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scrap tracking columns to production_orders."""
    
    # Check if columns already exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_columns = [col['name'] for col in inspector.get_columns('production_orders')]
    
    if 'scrap_reason' not in existing_columns:
        op.add_column('production_orders', sa.Column('scrap_reason', sa.String(length=100), nullable=True))
    
    if 'scrapped_at' not in existing_columns:
        op.add_column('production_orders', sa.Column('scrapped_at', sa.DateTime(), nullable=True))
    
    if 'remake_of_id' not in existing_columns:
        op.add_column('production_orders', sa.Column('remake_of_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_production_orders_remake_of',
            'production_orders',
            'production_orders',
            ['remake_of_id'],
            ['id']
        )


def downgrade() -> None:
    """Remove scrap tracking columns from production_orders."""
    
    # Check if columns exist before dropping
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_columns = [col['name'] for col in inspector.get_columns('production_orders')]
    
    if 'remake_of_id' in existing_columns:
        op.drop_constraint('fk_production_orders_remake_of', 'production_orders', type_='foreignkey')
        op.drop_column('production_orders', 'remake_of_id')
    
    if 'scrapped_at' in existing_columns:
        op.drop_column('production_orders', 'scrapped_at')
    
    if 'scrap_reason' in existing_columns:
        op.drop_column('production_orders', 'scrap_reason')
