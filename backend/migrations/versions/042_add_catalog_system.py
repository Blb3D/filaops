"""Add catalog system for B2B product visibility

This migration implements the B2B Catalog Access Control System:
- Creates catalogs table (catalog definitions like "Public", "KOA Custom")
- Creates catalog_products table (many-to-many: products in catalogs)
- Creates customer_catalogs table (many-to-many: customers assigned to catalogs)
- Creates default PUBLIC catalog and assigns all active finished goods

Revision ID: 042_add_catalog_system
Revises: 041_price_levels_customers
Create Date: 2026-01-18
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '042_add_catalog_system'
down_revision = '041_price_levels_customers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. Create catalogs table
    # =========================================================================
    op.create_table(
        'catalogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_catalogs_code')
    )
    op.create_index('ix_catalogs_code', 'catalogs', ['code'])
    op.create_index('ix_catalogs_active', 'catalogs', ['active'])
    op.create_index('ix_catalogs_is_public', 'catalogs', ['is_public'])

    # =========================================================================
    # 2. Create catalog_products table (many-to-many with price override)
    # =========================================================================
    op.create_table(
        'catalog_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('catalog_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('price_override', sa.Numeric(12, 4), nullable=True),  # Optional catalog-specific price
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['catalog_id'], ['catalogs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('catalog_id', 'product_id', name='uq_catalog_products')
    )
    op.create_index('ix_catalog_products_catalog_id', 'catalog_products', ['catalog_id'])
    op.create_index('ix_catalog_products_product_id', 'catalog_products', ['product_id'])

    # =========================================================================
    # 3. Create customer_catalogs table (many-to-many)
    # =========================================================================
    op.create_table(
        'customer_catalogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('catalog_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['catalog_id'], ['catalogs.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('customer_id', 'catalog_id', name='uq_customer_catalogs')
    )
    op.create_index('ix_customer_catalogs_customer_id', 'customer_catalogs', ['customer_id'])
    op.create_index('ix_customer_catalogs_catalog_id', 'customer_catalogs', ['catalog_id'])

    # =========================================================================
    # 4. Create default PUBLIC catalog
    # =========================================================================
    op.execute("""
        INSERT INTO catalogs (code, name, description, is_default, is_public, sort_order, active)
        VALUES ('PUBLIC', 'Public Catalog', 'Default public catalog visible to all customers', true, true, 0, true)
    """)

    # =========================================================================
    # 5. Assign all active finished goods to PUBLIC catalog
    # =========================================================================
    op.execute("""
        INSERT INTO catalog_products (catalog_id, product_id, created_at)
        SELECT
            (SELECT id FROM catalogs WHERE code = 'PUBLIC'),
            p.id,
            NOW()
        FROM products p
        WHERE p.active = true
          AND p.item_type = 'finished_good'
    """)


def downgrade() -> None:
    # Drop customer_catalogs
    op.drop_index('ix_customer_catalogs_catalog_id', table_name='customer_catalogs')
    op.drop_index('ix_customer_catalogs_customer_id', table_name='customer_catalogs')
    op.drop_table('customer_catalogs')

    # Drop catalog_products
    op.drop_index('ix_catalog_products_product_id', table_name='catalog_products')
    op.drop_index('ix_catalog_products_catalog_id', table_name='catalog_products')
    op.drop_table('catalog_products')

    # Drop catalogs
    op.drop_index('ix_catalogs_is_public', table_name='catalogs')
    op.drop_index('ix_catalogs_active', table_name='catalogs')
    op.drop_index('ix_catalogs_code', table_name='catalogs')
    op.drop_table('catalogs')
