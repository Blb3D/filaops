"""add performance indexes for common queries

Revision ID: 021_add_performance_indexes
Revises: 020
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
revision = "021_add_performance_indexes"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade():
    # Sales Orders - Composite index for common filtering and sorting
    op.create_index(
        "ix_sales_orders_status_created_at", "sales_orders", ["status", sa.text("created_at DESC")], if_not_exists=True
    )

    # Sales Orders - Payment reporting index (partial index for paid orders)
    op.create_index(
        "ix_sales_orders_payment_status_paid_at",
        "sales_orders",
        ["payment_status", sa.text("paid_at DESC")],
        if_not_exists=True,
        postgresql_where=sa.text("payment_status = 'paid'"),
    )

    # Inventory - Product + Location lookup (most common inventory query)
    op.create_index("ix_inventory_product_location", "inventory", ["product_id", "location_id"], if_not_exists=True)

    # Production Orders - Status and creation date for queue management
    op.create_index(
        "ix_production_orders_status_created_at",
        "production_orders",
        ["status", sa.text("created_at DESC")],
        if_not_exists=True,
    )

    # Sales Order Lines - For BOM explosion and MRP calculations
    op.create_index(
        "ix_sales_order_lines_order_product", "sales_order_lines", ["sales_order_id", "product_id"], if_not_exists=True
    )

    # BOM Lines - Component lookups for BOM explosion
    op.create_index("ix_bom_lines_bom_component", "bom_lines", ["bom_id", "component_id"], if_not_exists=True)

    # Products - Active items filtering
    op.create_index(
        "ix_products_active_type_procurement",
        "products",
        ["active", "item_type", "procurement_type"],
        if_not_exists=True,
    )

    # Inventory Transactions - Product history and reporting
    op.create_index(
        "ix_inventory_transactions_product_created",
        "inventory_transactions",
        ["product_id", sa.text("created_at DESC")],
        if_not_exists=True,
    )


def downgrade():
    # Drop indexes in reverse order
    op.drop_index("ix_inventory_transactions_product_created", table_name="inventory_transactions", if_exists=True)
    op.drop_index("ix_products_active_type_procurement", table_name="products", if_exists=True)
    op.drop_index("ix_bom_lines_bom_component", table_name="bom_lines", if_exists=True)
    op.drop_index("ix_sales_order_lines_order_product", table_name="sales_order_lines", if_exists=True)
    op.drop_index("ix_production_orders_status_created_at", table_name="production_orders", if_exists=True)
    op.drop_index("ix_inventory_product_location", table_name="inventory", if_exists=True)
    op.drop_index("ix_sales_orders_payment_status_paid_at", table_name="sales_orders", if_exists=True)
    op.drop_index("ix_sales_orders_status_created_at", table_name="sales_orders", if_exists=True)
