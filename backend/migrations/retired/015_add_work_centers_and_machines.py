"""add_work_centers_and_machines_tables

Revision ID: 015_add_work_centers_and_machines
Revises: 014_add_fulfillment_status
Create Date: 2025-12-17 21:57:53.409095

Adds work_centers and machines tables for production scheduling and resource management.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql


# revision identifiers, used by Alembic.
revision: str = '015_add_work_centers_and_machines'
down_revision: Union[str, Sequence[str], None] = '014_add_fulfillment_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to work_centers and create machines table if needed."""
    
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # Check if work_centers table exists
    if 'work_centers' in existing_tables:
        # Table exists - add missing columns if needed
        existing_columns = [col['name'] for col in inspector.get_columns('work_centers')]
        
        # Add hourly_rate if missing (maps to machine_rate_per_hour)
        if 'hourly_rate' not in existing_columns:
            op.add_column('work_centers', sa.Column('hourly_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
            
        # Add active if missing (maps to is_active) 
        if 'active' not in existing_columns:
            op.add_column('work_centers', sa.Column('active', sa.Boolean(), nullable=False, server_default='1'))
    else:
        # Table doesn't exist - create it
        op.create_table(
            'work_centers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('hourly_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
            sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.getdate()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.getdate()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code', name='uq_work_centers_code')
        )
        op.create_index('ix_work_centers_id', 'work_centers', ['id'])
        op.create_index('ix_work_centers_code', 'work_centers', ['code'], unique=True)
    
    # Check if machines table exists
    if 'machines' not in existing_tables:
        # Create machines table
        op.create_table(
            'machines',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('work_center_id', sa.Integer(), nullable=False),
            sa.Column('machine_type', sa.String(length=100), nullable=True),
            sa.Column('compatible_materials', sa.String(length=500), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='available'),
            sa.Column('bed_size_x', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('bed_size_y', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('bed_size_z', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('bambu_serial', sa.String(length=100), nullable=True),
            sa.Column('bambu_access_code', sa.String(length=20), nullable=True),
            sa.Column('bambu_ip_address', sa.String(length=45), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.getdate()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.getdate()),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['work_center_id'], ['work_centers.id'], name='fk_machines_work_center'),
            sa.UniqueConstraint('code', name='uq_machines_code')
        )
        op.create_index('ix_machines_id', 'machines', ['id'])
        op.create_index('ix_machines_code', 'machines', ['code'], unique=True)
        op.create_index('ix_machines_status', 'machines', ['status'])
    
    # Add work_center_id to printers table if it exists and doesn't have it
    if 'printers' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('printers')]
        if 'work_center_id' not in existing_columns:
            op.add_column('printers', sa.Column('work_center_id', sa.Integer(), nullable=True))
            op.create_foreign_key(
                'fk_printers_work_center',
                'printers',
                'work_centers',
                ['work_center_id'],
                ['id']
            )


def downgrade() -> None:
    """Drop work_centers and machines tables."""
    
    # Remove foreign key from printers if it exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    if 'printers' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('printers')]
        if 'work_center_id' in existing_columns:
            op.drop_constraint('fk_printers_work_center', 'printers', type_='foreignkey')
            op.drop_column('printers', 'work_center_id')
    
    # Drop machines table
    op.drop_index('ix_machines_status', table_name='machines')
    op.drop_index('ix_machines_code', table_name='machines')
    op.drop_index('ix_machines_id', table_name='machines')
    op.drop_table('machines')
    
    # Drop work_centers table
    op.drop_index('ix_work_centers_code', table_name='work_centers')
    op.drop_index('ix_work_centers_id', table_name='work_centers')
    op.drop_table('work_centers')
