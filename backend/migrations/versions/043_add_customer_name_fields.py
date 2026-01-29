"""Create customers table with name fields

Revision ID: 043_add_customer_name_fields
Revises: 040_update_material_item_types
Create Date: 2026-01-10

Creates the customers table for CRM functionality.
Customers can be B2B organizations or B2C individuals.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '043_add_customer_name_fields'
down_revision = '040_update_material_item_types'
branch_labels = None
depends_on = None


def upgrade():
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

        # Notes
        sa.Column('notes', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_customers_id', 'customers', ['id'])
    op.create_index('ix_customers_customer_number', 'customers', ['customer_number'], unique=True)
    op.create_index('ix_customers_company_name', 'customers', ['company_name'])
    op.create_index('ix_customers_email', 'customers', ['email'])
    op.create_index('ix_customers_status', 'customers', ['status'])


def downgrade():
    op.drop_index('ix_customers_status', table_name='customers')
    op.drop_index('ix_customers_email', table_name='customers')
    op.drop_index('ix_customers_company_name', table_name='customers')
    op.drop_index('ix_customers_customer_number', table_name='customers')
    op.drop_index('ix_customers_id', table_name='customers')
    op.drop_table('customers')
