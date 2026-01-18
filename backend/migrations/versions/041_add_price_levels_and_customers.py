"""Add price_levels and customers tables

This migration implements the B2B pricing and customer organization system:
- Creates price_levels table with discount tiers (A, B, C, D)
- Creates customers table (organization-level CRM records, separate from portal users)
- Adds customer_id FK to users table (portal users link to customer organizations)
- Migrates existing customer data from users to customers table

Revision ID: 041_price_levels_customers
Revises: 040_update_material_item_types
Create Date: 2026-01-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '041_price_levels_customers'
down_revision = '040_update_material_item_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. Create price_levels table
    # =========================================================================
    op.create_table(
        'price_levels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(10), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('discount_percent', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_price_levels_code')
    )
    op.create_index('ix_price_levels_code', 'price_levels', ['code'])
    op.create_index('ix_price_levels_active', 'price_levels', ['active'])

    # Seed default price levels (A=25%, B=20%, C=10%, D=0%)
    op.execute("""
        INSERT INTO price_levels (code, name, discount_percent, description, sort_order, active)
        VALUES
            ('A', 'Tier A - Premium', 25.00, 'Best pricing for high-volume partners', 1, true),
            ('B', 'Tier B - Preferred', 20.00, 'Preferred partner pricing', 2, true),
            ('C', 'Tier C - Standard', 10.00, 'Standard wholesale pricing', 3, true),
            ('D', 'Tier D - Retail', 0.00, 'Retail pricing (no discount)', 4, true)
    """)

    # =========================================================================
    # 2. Create customers table (organization-level, separate from users)
    # =========================================================================
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_number', sa.String(50), nullable=True),
        sa.Column('company_name', sa.String(200), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),  # Primary contact email
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),

        # Price Level FK
        sa.Column('price_level_id', sa.Integer(), sa.ForeignKey('price_levels.id'), nullable=True),

        # Billing Address
        sa.Column('billing_address_line1', sa.String(255), nullable=True),
        sa.Column('billing_address_line2', sa.String(255), nullable=True),
        sa.Column('billing_city', sa.String(100), nullable=True),
        sa.Column('billing_state', sa.String(50), nullable=True),
        sa.Column('billing_zip', sa.String(20), nullable=True),
        sa.Column('billing_country', sa.String(100), nullable=True, server_default='USA'),

        # Shipping Address (default for orders)
        sa.Column('shipping_address_line1', sa.String(255), nullable=True),
        sa.Column('shipping_address_line2', sa.String(255), nullable=True),
        sa.Column('shipping_city', sa.String(100), nullable=True),
        sa.Column('shipping_state', sa.String(50), nullable=True),
        sa.Column('shipping_zip', sa.String(20), nullable=True),
        sa.Column('shipping_country', sa.String(100), nullable=True, server_default='USA'),

        # Metadata
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_customers_customer_number', 'customers', ['customer_number'], unique=True)
    op.create_index('ix_customers_status', 'customers', ['status'])
    op.create_index('ix_customers_email', 'customers', ['email'])
    op.create_index('ix_customers_company_name', 'customers', ['company_name'])

    # =========================================================================
    # 3. Add customer_id FK to users table
    # =========================================================================
    op.add_column('users', sa.Column('customer_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_users_customer_id',
        'users', 'customers',
        ['customer_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_users_customer_id', 'users', ['customer_id'])

    # =========================================================================
    # 4. Migrate existing customer users to customers table
    # =========================================================================
    # For each user with account_type='customer', create a Customer record
    # and link the user to it
    op.execute("""
        WITH customer_users AS (
            SELECT id, customer_number, company_name, first_name, last_name, 
                   email, phone, status,
                   billing_address_line1, billing_address_line2, billing_city,
                   billing_state, billing_zip, billing_country,
                   shipping_address_line1, shipping_address_line2, shipping_city,
                   shipping_state, shipping_zip, shipping_country,
                   created_at, updated_at
            FROM users
            WHERE account_type = 'customer'
        ),
        inserted_customers AS (
            INSERT INTO customers (
                customer_number, company_name, first_name, last_name,
                email, phone, status,
                billing_address_line1, billing_address_line2, billing_city,
                billing_state, billing_zip, billing_country,
                shipping_address_line1, shipping_address_line2, shipping_city,
                shipping_state, shipping_zip, shipping_country,
                created_at, updated_at
            )
            SELECT
                customer_number, company_name, first_name, last_name,
                email, phone, status,
                billing_address_line1, billing_address_line2, billing_city,
                billing_state, billing_zip, billing_country,
                shipping_address_line1, shipping_address_line2, shipping_city,
                shipping_state, shipping_zip, shipping_country,
                created_at, updated_at
            FROM customer_users
            RETURNING id, email
        )
        UPDATE users u
        SET customer_id = ic.id
        FROM inserted_customers ic
        WHERE u.email = ic.email AND u.account_type = 'customer'
    """)


def downgrade() -> None:
    # Remove customer_id from users
    op.drop_index('ix_users_customer_id', table_name='users')
    op.drop_constraint('fk_users_customer_id', 'users', type_='foreignkey')
    op.drop_column('users', 'customer_id')

    # Drop customers table
    op.drop_index('ix_customers_company_name', table_name='customers')
    op.drop_index('ix_customers_email', table_name='customers')
    op.drop_index('ix_customers_status', table_name='customers')
    op.drop_index('ix_customers_customer_number', table_name='customers')
    op.drop_table('customers')

    # Drop price_levels table
    op.drop_index('ix_price_levels_active', table_name='price_levels')
    op.drop_index('ix_price_levels_code', table_name='price_levels')
    op.drop_table('price_levels')
