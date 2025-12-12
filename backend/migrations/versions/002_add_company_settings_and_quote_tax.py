"""Add company settings and quote tax fields

Revision ID: 002_company_settings
Revises: baseline_001
Create Date: 2025-12-11

Adds:
- company_settings table
- Quote fields: subtotal, tax_rate, tax_amount, image_data, image_filename, image_mime_type, customer_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_company_settings'
down_revision: Union[str, Sequence[str], None] = 'baseline_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    from alembic import context

    # Get connection and inspector
    connection = op.get_bind()
    inspector = inspect(connection)

    # Check if company_settings table exists
    existing_tables = inspector.get_table_names()
    if 'company_settings' not in existing_tables:
        op.create_table(
            'company_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_name', sa.String(length=255), nullable=True),
            sa.Column('company_address_line1', sa.String(length=255), nullable=True),
            sa.Column('company_address_line2', sa.String(length=255), nullable=True),
            sa.Column('company_city', sa.String(length=100), nullable=True),
            sa.Column('company_state', sa.String(length=50), nullable=True),
            sa.Column('company_zip', sa.String(length=20), nullable=True),
            sa.Column('company_country', sa.String(length=100), nullable=True),
            sa.Column('company_phone', sa.String(length=30), nullable=True),
            sa.Column('company_email', sa.String(length=255), nullable=True),
            sa.Column('company_website', sa.String(length=255), nullable=True),
            sa.Column('logo_data', sa.LargeBinary(), nullable=True),
            sa.Column('logo_filename', sa.String(length=255), nullable=True),
            sa.Column('logo_mime_type', sa.String(length=100), nullable=True),
            sa.Column('tax_enabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('tax_rate', sa.Numeric(precision=5, scale=4), nullable=True),
            sa.Column('tax_name', sa.String(length=50), nullable=True),
            sa.Column('tax_registration_number', sa.String(length=100), nullable=True),
            sa.Column('default_quote_validity_days', sa.Integer(), nullable=False, server_default='30'),
            sa.Column('quote_terms', sa.String(length=2000), nullable=True),
            sa.Column('quote_footer', sa.String(length=1000), nullable=True),
            sa.Column('invoice_prefix', sa.String(length=20), nullable=True),
            sa.Column('invoice_terms', sa.String(length=2000), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id')
        )

    # Get existing columns in quotes table
    quotes_columns = [c['name'] for c in inspector.get_columns('quotes')]

    # Add new columns to quotes table (only if they don't exist)
    if 'subtotal' not in quotes_columns:
        op.add_column('quotes', sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=True))
    if 'tax_rate' not in quotes_columns:
        op.add_column('quotes', sa.Column('tax_rate', sa.Numeric(precision=5, scale=4), nullable=True))
    if 'tax_amount' not in quotes_columns:
        op.add_column('quotes', sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=True))
    if 'image_data' not in quotes_columns:
        op.add_column('quotes', sa.Column('image_data', sa.LargeBinary(), nullable=True))
    if 'image_filename' not in quotes_columns:
        op.add_column('quotes', sa.Column('image_filename', sa.String(length=255), nullable=True))
    if 'image_mime_type' not in quotes_columns:
        op.add_column('quotes', sa.Column('image_mime_type', sa.String(length=100), nullable=True))
    if 'customer_id' not in quotes_columns:
        op.add_column('quotes', sa.Column('customer_id', sa.Integer(), nullable=True))

        # Create index and foreign key for customer_id (only if we just added the column)
        # Check if index exists first
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('quotes')]
        if 'ix_quotes_customer_id' not in existing_indexes:
            op.create_index('ix_quotes_customer_id', 'quotes', ['customer_id'])

        # Check if foreign key exists first
        existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('quotes')]
        if 'fk_quotes_customer_id' not in existing_fks:
            try:
                op.create_foreign_key(
                    'fk_quotes_customer_id',
                    'quotes', 'users',
                    ['customer_id'], ['id']
                )
            except Exception:
                # FK creation may fail if users table doesn't have proper PK - skip in this case
                pass

    # Make material_type nullable (for admin quotes that don't specify material)
    # SQL Server requires explicit ALTER COLUMN
    connection.execute(sa.text("ALTER TABLE quotes ALTER COLUMN material_type VARCHAR(50) NULL"))


def downgrade() -> None:
    # Drop foreign key and index
    op.drop_constraint('fk_quotes_customer_id', 'quotes', type_='foreignkey')
    op.drop_index('ix_quotes_customer_id', table_name='quotes')

    # Drop quote columns
    op.drop_column('quotes', 'customer_id')
    op.drop_column('quotes', 'image_mime_type')
    op.drop_column('quotes', 'image_filename')
    op.drop_column('quotes', 'image_data')
    op.drop_column('quotes', 'tax_amount')
    op.drop_column('quotes', 'tax_rate')
    op.drop_column('quotes', 'subtotal')

    # Drop company_settings table
    op.drop_table('company_settings')
