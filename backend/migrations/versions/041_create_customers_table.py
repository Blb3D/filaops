"""Create customers table for CRM

Revision ID: 041_create_customers_table
Revises: 040_update_material_item_types
Create Date: 2026-01-28

Customers can be B2B organizations or B2C individuals.
This was previously a PRO feature but is now part of Core for
basic CRM functionality.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '041_create_customers_table'
down_revision = '040_update_material_item_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create customers table with indexes and updated_at trigger."""
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_number', sa.String(50), nullable=True),
        sa.Column('company_name', sa.String(200), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),

        # Billing Address
        sa.Column('billing_address_line1', sa.String(255), nullable=True),
        sa.Column('billing_address_line2', sa.String(255), nullable=True),
        sa.Column('billing_city', sa.String(100), nullable=True),
        sa.Column('billing_state', sa.String(50), nullable=True),
        sa.Column('billing_zip', sa.String(20), nullable=True),
        sa.Column('billing_country', sa.String(100), nullable=True, server_default='USA'),

        # Shipping Address
        sa.Column('shipping_address_line1', sa.String(255), nullable=True),
        sa.Column('shipping_address_line2', sa.String(255), nullable=True),
        sa.Column('shipping_city', sa.String(100), nullable=True),
        sa.Column('shipping_state', sa.String(50), nullable=True),
        sa.Column('shipping_zip', sa.String(20), nullable=True),
        sa.Column('shipping_country', sa.String(100), nullable=True, server_default='USA'),

        # Metadata
        sa.Column('notes', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_number', name='uq_customers_customer_number'),
    )

    # Create indexes (id and customer_number already indexed by PK and unique constraint)
    op.create_index('ix_customers_company_name', 'customers', ['company_name'])
    op.create_index('ix_customers_email', 'customers', ['email'])
    op.create_index('ix_customers_status', 'customers', ['status'])

    # Add trigger to update updated_at on row update (PostgreSQL)
    op.execute('''
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    ''')
    op.execute('''
    CREATE TRIGGER update_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();
    ''')


def downgrade() -> None:
    """Revert customers table creation, removing trigger, function, indexes, and table."""
    # Remove trigger and function
    op.execute('DROP TRIGGER IF EXISTS update_customers_updated_at ON customers;')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column();')
    op.drop_index('ix_customers_status', table_name='customers')
    op.drop_index('ix_customers_email', table_name='customers')
    op.drop_index('ix_customers_company_name', table_name='customers')
    op.drop_table('customers')
