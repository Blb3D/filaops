"""Add brand-agnostic printer management fields

Revision ID: 008_printer_brand_agnostic
Revises: 007_ensure_production_order_code_unique
Create Date: 2025-12-15

Adds to printers table:
- brand: Printer brand identifier (bambulab, klipper, octoprint, prusa, creality, generic)
- connection_config: JSON for brand-specific connection settings
- capabilities: JSON for printer capabilities/features
- last_seen: Last communication timestamp
- work_center_id: Foreign key to work_centers
- notes: Operator notes
- created_at, updated_at: Timestamps
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '008_printer_brand_agnostic'
down_revision: Union[str, Sequence[str], None] = '007_ensure_code_unique'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    from datetime import datetime

    # Get connection and inspector
    connection = op.get_bind()
    inspector = inspect(connection)

    # Check if printers table exists
    existing_tables = inspector.get_table_names()
    if 'printers' not in existing_tables:
        # Create printers table if it doesn't exist
        op.create_table(
            'printers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('model', sa.String(length=100), nullable=False),
            sa.Column('serial_number', sa.String(length=100), nullable=True),
            sa.Column('brand', sa.String(length=50), nullable=False, server_default='generic'),
            sa.Column('ip_address', sa.String(length=50), nullable=True),
            sa.Column('mqtt_topic', sa.String(length=255), nullable=True),
            sa.Column('connection_config', sa.JSON(), nullable=True),
            sa.Column('capabilities', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=True, server_default='offline'),
            sa.Column('last_seen', sa.DateTime(), nullable=True),
            sa.Column('location', sa.String(length=255), nullable=True),
            sa.Column('work_center_id', sa.Integer(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=True, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('GETUTCDATE()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('GETUTCDATE()')),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['work_center_id'], ['work_centers.id'], name='fk_printers_work_center')
        )
        op.create_index('ix_printers_code', 'printers', ['code'], unique=True)
        op.create_index('ix_printers_brand', 'printers', ['brand'], unique=False)
    else:
        # Table exists, add new columns if they don't exist
        existing_columns = [col['name'] for col in inspector.get_columns('printers')]

        # Add brand column
        if 'brand' not in existing_columns:
            op.add_column('printers', sa.Column('brand', sa.String(length=50), nullable=True))
            # Update existing rows to have 'generic' as default brand
            connection.execute(sa.text("UPDATE printers SET brand = 'generic' WHERE brand IS NULL"))
            # Now make it non-nullable with default (SQL Server requires existing_type)
            op.alter_column('printers', 'brand',
                            existing_type=sa.String(length=50),
                            nullable=False,
                            server_default='generic')
            op.create_index('ix_printers_brand', 'printers', ['brand'], unique=False)

        # Add connection_config JSON column
        if 'connection_config' not in existing_columns:
            op.add_column('printers', sa.Column('connection_config', sa.JSON(), nullable=True))

        # Add capabilities JSON column
        if 'capabilities' not in existing_columns:
            op.add_column('printers', sa.Column('capabilities', sa.JSON(), nullable=True))

        # Add last_seen timestamp
        if 'last_seen' not in existing_columns:
            op.add_column('printers', sa.Column('last_seen', sa.DateTime(), nullable=True))

        # Add work_center_id foreign key
        if 'work_center_id' not in existing_columns:
            op.add_column('printers', sa.Column('work_center_id', sa.Integer(), nullable=True))
            # Check if work_centers table exists before adding FK
            if 'work_centers' in existing_tables:
                op.create_foreign_key(
                    'fk_printers_work_center',
                    'printers',
                    'work_centers',
                    ['work_center_id'],
                    ['id']
                )

        # Add notes column
        if 'notes' not in existing_columns:
            op.add_column('printers', sa.Column('notes', sa.Text(), nullable=True))

        # Add timestamps
        if 'created_at' not in existing_columns:
            op.add_column('printers', sa.Column(
                'created_at',
                sa.DateTime(),
                nullable=True,
                server_default=sa.text('GETUTCDATE()')
            ))
            # Update existing rows
            connection.execute(sa.text("UPDATE printers SET created_at = GETUTCDATE() WHERE created_at IS NULL"))

        if 'updated_at' not in existing_columns:
            op.add_column('printers', sa.Column(
                'updated_at',
                sa.DateTime(),
                nullable=True,
                server_default=sa.text('GETUTCDATE()')
            ))
            # Update existing rows
            connection.execute(sa.text("UPDATE printers SET updated_at = GETUTCDATE() WHERE updated_at IS NULL"))


def downgrade() -> None:
    from sqlalchemy import inspect

    connection = op.get_bind()
    inspector = inspect(connection)
    existing_tables = inspector.get_table_names()

    if 'printers' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('printers')]

        # Drop foreign key first if it exists
        try:
            op.drop_constraint('fk_printers_work_center', 'printers', type_='foreignkey')
        except Exception:
            pass  # Constraint might not exist

        # Drop index
        try:
            op.drop_index('ix_printers_brand', 'printers')
        except Exception:
            pass

        # Drop columns in reverse order
        columns_to_drop = [
            'updated_at', 'created_at', 'notes', 'work_center_id',
            'last_seen', 'capabilities', 'connection_config', 'brand'
        ]

        for col in columns_to_drop:
            if col in existing_columns:
                op.drop_column('printers', col)
