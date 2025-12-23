"""add performance indexes for common queries

Revision ID: 021_add_performance_indexes
Revises: 020_add_business_hours_to_company_settings
Create Date: 2025-12-23 (Sprint 1 - Agent 1)

Performance Optimization: Add database indexes for common query patterns
to reduce query times on large datasets.

Target Performance:
- Dashboard: <500ms
- List endpoints: <1s with 1000 records

Indexes Added:
1. sales_orders (status, created_at) - For filtering by status and sorting
2. sales_orders (payment_status, paid_at) - For payment reports and revenue calculations
3. inventory (product_id, location_id) - For inventory lookups by product+location
4. production_orders (status, created_at) - For production queue and filtering
5. sales_order_lines (sales_order_id, product_id) - For BOM explosion and requirement lookups
6. bom_lines (bom_id, component_id) - For BOM component lookups
7. products (active, item_type, procurement_type) - For product filtering
8. inventory_transactions (product_id, created_at) - For inventory history and reporting

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021_add_performance_indexes'
down_revision = '020_add_business_hours_to_company_settings'
branch_labels = None
depends_on = None


def upgrade():
    # Sales Orders - Composite index for common filtering and sorting
    op.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_sales_orders_status_created_at' AND object_id = OBJECT_ID('sales_orders'))
        BEGIN
            CREATE NONCLUSTERED INDEX ix_sales_orders_status_created_at
            ON sales_orders (status, created_at DESC)
            INCLUDE (order_number, grand_total, payment_status);
        END
    """)

    # Sales Orders - Payment reporting index
    op.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_sales_orders_payment_status_paid_at' AND object_id = OBJECT_ID('sales_orders'))
        BEGIN
            CREATE NONCLUSTERED INDEX ix_sales_orders_payment_status_paid_at
            ON sales_orders (payment_status, paid_at DESC)
            WHERE payment_status = 'paid';
        END
    """)

    # Inventory - Product + Location lookup (most common inventory query)
    op.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_inventory_product_location' AND object_id = OBJECT_ID('inventory'))
        BEGIN
            CREATE NONCLUSTERED INDEX ix_inventory_product_location
            ON inventory (product_id, location_id)
            INCLUDE (on_hand_quantity, allocated_quantity, available_quantity);
        END
    """)

    # Production Orders - Status and creation date for queue management
    op.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_production_orders_status_created_at' AND object_id = OBJECT_ID('production_orders'))
        BEGIN
            CREATE NONCLUSTERED INDEX ix_production_orders_status_created_at
            ON production_orders (status, created_at DESC)
            INCLUDE (code, product_id, quantity_ordered, priority);
        END
    """)

    # Sales Order Lines - For BOM explosion and MRP calculations
    op.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_sales_order_lines_order_product' AND object_id = OBJECT_ID('sales_order_lines'))
        BEGIN
            CREATE NONCLUSTERED INDEX ix_sales_order_lines_order_product
            ON sales_order_lines (sales_order_id, product_id)
            INCLUDE (quantity, unit_price, total);
        END
    """)

    # BOM Lines - Component lookups for BOM explosion
    op.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_bom_lines_bom_component' AND object_id = OBJECT_ID('bom_lines'))
        BEGIN
            CREATE NONCLUSTERED INDEX ix_bom_lines_bom_component
            ON bom_lines (bom_id, component_id)
            INCLUDE (quantity, unit, scrap_factor, is_cost_only);
        END
    """)

    # Products - Active items filtering
    op.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_products_active_type_procurement' AND object_id = OBJECT_ID('products'))
        BEGIN
            CREATE NONCLUSTERED INDEX ix_products_active_type_procurement
            ON products (active, item_type, procurement_type)
            INCLUDE (sku, name, has_bom, reorder_point);
        END
    """)

    # Inventory Transactions - Product history and reporting
    op.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_inventory_transactions_product_created' AND object_id = OBJECT_ID('inventory_transactions'))
        BEGIN
            CREATE NONCLUSTERED INDEX ix_inventory_transactions_product_created
            ON inventory_transactions (product_id, created_at DESC)
            INCLUDE (transaction_type, quantity, reference_type, reference_id);
        END
    """)


def downgrade():
    # Drop indexes in reverse order
    op.execute("DROP INDEX IF EXISTS ix_inventory_transactions_product_created ON inventory_transactions")
    op.execute("DROP INDEX IF EXISTS ix_products_active_type_procurement ON products")
    op.execute("DROP INDEX IF EXISTS ix_bom_lines_bom_component ON bom_lines")
    op.execute("DROP INDEX IF EXISTS ix_sales_order_lines_order_product ON sales_order_lines")
    op.execute("DROP INDEX IF EXISTS ix_production_orders_status_created_at ON production_orders")
    op.execute("DROP INDEX IF EXISTS ix_inventory_product_location ON inventory")
    op.execute("DROP INDEX IF EXISTS ix_sales_orders_payment_status_paid_at ON sales_orders")
    op.execute("DROP INDEX IF EXISTS ix_sales_orders_status_created_at ON sales_orders")
