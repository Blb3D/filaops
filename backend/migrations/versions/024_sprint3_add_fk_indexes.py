"""Sprint 3-4: Add missing indexes on foreign key columns

Revision ID: 024_sprint3_add_fk_indexes
Revises: 023_sprint3_cleanup_product
Create Date: 2025-12-23 (Sprint 3-4 - Data Model Cleanup)

Many foreign key columns were missing indexes, causing slow JOIN and
WHERE clause performance. This migration adds indexes to all FK columns.

Also adds proper ForeignKey constraints where they were missing:
- Product.preferred_vendor_id -> vendors.id
- Product.customer_id -> users.id
- Quote.approved_by -> users.id
- Quote.sales_order_id -> sales_orders.id

NOTE: Uses defensive programming - skips if constraint/index already exists.
This is safe to run multiple times without errors.

"""

from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "024_sprint3_add_fk_indexes"
down_revision = "023_sprint3_cleanup_product"
branch_labels = None
depends_on = None


def _fk_exists(table_name, fk_name):
    """Check if a foreign key constraint exists."""
    try:
        bind = op.get_bind()
        inspector = inspect(bind)
        fks = inspector.get_foreign_keys(table_name)
        return any(fk.get("name") == fk_name for fk in fks)
    except Exception:
        return False


def _index_exists(table_name, index_name):
    """Check if an index exists."""
    try:
        bind = op.get_bind()
        inspector = inspect(bind)
        indexes = inspector.get_indexes(table_name)
        return any(idx.get("name") == index_name for idx in indexes)
    except Exception:
        return False


def _table_exists(table_name):
    """Check if a table exists."""
    try:
        bind = op.get_bind()
        inspector = inspect(bind)
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def _create_fk_if_not_exists(fk_name, source_table, target_table, source_cols, target_cols, ondelete=None):
    """Create foreign key only if it doesn't already exist."""
    if not _fk_exists(source_table, fk_name):
        try:
            op.create_foreign_key(fk_name, source_table, target_table, source_cols, target_cols, ondelete=ondelete)
        except Exception as e:
            print(f"  Skipping FK {fk_name}: {e}")


def _create_index_if_not_exists(index_name, table_name, columns):
    """Create index only if it doesn't already exist."""
    if not _table_exists(table_name):
        print(f"  Skipping index {index_name}: table {table_name} does not exist")
        return
    if not _index_exists(table_name, index_name):
        try:
            op.create_index(index_name, table_name, columns)
        except Exception as e:
            print(f"  Skipping index {index_name}: {e}")


def _drop_index_if_exists(index_name, table_name):
    """Drop index only if it exists."""
    if _table_exists(table_name) and _index_exists(table_name, index_name):
        try:
            op.drop_index(index_name, table_name)
        except Exception as e:
            print(f"  Skipping drop index {index_name}: {e}")


def _drop_fk_if_exists(fk_name, table_name):
    """Drop foreign key only if it exists."""
    if _fk_exists(table_name, fk_name):
        try:
            op.drop_constraint(fk_name, table_name, type_="foreignkey")
        except Exception as e:
            print(f"  Skipping drop FK {fk_name}: {e}")


def upgrade():
    # ===========================================
    # Add missing FK constraints first
    # ===========================================

    # Product.preferred_vendor_id -> vendors.id
    _create_fk_if_not_exists(
        "fk_products_preferred_vendor", "products", "vendors", ["preferred_vendor_id"], ["id"], ondelete="SET NULL"
    )

    # Product.customer_id -> users.id (for customer-specific products)
    _create_fk_if_not_exists("fk_products_customer", "products", "users", ["customer_id"], ["id"], ondelete="SET NULL")

    # Quote.approved_by -> users.id
    _create_fk_if_not_exists("fk_quotes_approved_by", "quotes", "users", ["approved_by"], ["id"], ondelete="SET NULL")

    # Quote.sales_order_id -> sales_orders.id
    _create_fk_if_not_exists(
        "fk_quotes_sales_order", "quotes", "sales_orders", ["sales_order_id"], ["id"], ondelete="SET NULL"
    )

    # ===========================================
    # Add missing indexes on FK columns
    # ===========================================

    # Products table
    _create_index_if_not_exists("ix_products_preferred_vendor_id", "products", ["preferred_vendor_id"])
    _create_index_if_not_exists("ix_products_customer_id", "products", ["customer_id"])

    # Production Orders table
    _create_index_if_not_exists("ix_production_orders_product_id", "production_orders", ["product_id"])
    _create_index_if_not_exists("ix_production_orders_bom_id", "production_orders", ["bom_id"])
    _create_index_if_not_exists("ix_production_orders_routing_id", "production_orders", ["routing_id"])
    _create_index_if_not_exists("ix_production_orders_sales_order_id", "production_orders", ["sales_order_id"])
    _create_index_if_not_exists(
        "ix_production_orders_sales_order_line_id", "production_orders", ["sales_order_line_id"]
    )
    _create_index_if_not_exists("ix_production_orders_remake_of_id", "production_orders", ["remake_of_id"])

    # Production Order Operations table
    _create_index_if_not_exists(
        "ix_production_order_operations_routing_operation_id", "production_order_operations", ["routing_operation_id"]
    )
    _create_index_if_not_exists(
        "ix_production_order_operations_work_center_id", "production_order_operations", ["work_center_id"]
    )
    _create_index_if_not_exists(
        "ix_production_order_operations_resource_id", "production_order_operations", ["resource_id"]
    )

    # Production Order Materials table
    _create_index_if_not_exists(
        "ix_production_order_materials_bom_line_id", "production_order_materials", ["bom_line_id"]
    )
    _create_index_if_not_exists(
        "ix_production_order_materials_original_product_id", "production_order_materials", ["original_product_id"]
    )
    _create_index_if_not_exists(
        "ix_production_order_materials_substitute_product_id", "production_order_materials", ["substitute_product_id"]
    )

    # Inventory table
    _create_index_if_not_exists("ix_inventory_location_id", "inventory", ["location_id"])

    # Inventory Transactions table
    _create_index_if_not_exists("ix_inventory_transactions_location_id", "inventory_transactions", ["location_id"])

    # Purchase Order Lines table
    _create_index_if_not_exists("ix_purchase_order_lines_product_id", "purchase_order_lines", ["product_id"])

    # BOM Lines table
    _create_index_if_not_exists("ix_bom_lines_component_id", "bom_lines", ["component_id"])

    # Resources table (manufacturing)
    _create_index_if_not_exists("ix_resources_work_center_id", "resources", ["work_center_id"])

    # Routings table
    _create_index_if_not_exists("ix_routings_product_id", "routings", ["product_id"])

    # Routing Operations table
    _create_index_if_not_exists("ix_routing_operations_work_center_id", "routing_operations", ["work_center_id"])
    _create_index_if_not_exists(
        "ix_routing_operations_predecessor_id", "routing_operations", ["predecessor_operation_id"]
    )

    # Machines table
    _create_index_if_not_exists("ix_machines_work_center_id", "machines", ["work_center_id"])

    # Print Jobs table
    _create_index_if_not_exists("ix_print_jobs_printer_id", "print_jobs", ["printer_id"])

    # Material Spools table
    _create_index_if_not_exists("ix_material_spools_location_id", "material_spools", ["location_id"])

    # Quotes table
    _create_index_if_not_exists("ix_quotes_approved_by", "quotes", ["approved_by"])
    _create_index_if_not_exists("ix_quotes_sales_order_id", "quotes", ["sales_order_id"])

    # Planned Orders table (MRP)
    _create_index_if_not_exists("ix_planned_orders_product_id", "planned_orders", ["product_id"])
    _create_index_if_not_exists("ix_planned_orders_converted_to_po_id", "planned_orders", ["converted_to_po_id"])
    _create_index_if_not_exists("ix_planned_orders_converted_to_mo_id", "planned_orders", ["converted_to_mo_id"])


def downgrade():
    # Drop indexes (reverse order) - use defensive approach
    _drop_index_if_exists("ix_planned_orders_converted_to_mo_id", "planned_orders")
    _drop_index_if_exists("ix_planned_orders_converted_to_po_id", "planned_orders")
    _drop_index_if_exists("ix_planned_orders_product_id", "planned_orders")

    _drop_index_if_exists("ix_quotes_sales_order_id", "quotes")
    _drop_index_if_exists("ix_quotes_approved_by", "quotes")

    _drop_index_if_exists("ix_material_spools_location_id", "material_spools")
    _drop_index_if_exists("ix_print_jobs_printer_id", "print_jobs")
    _drop_index_if_exists("ix_machines_work_center_id", "machines")

    _drop_index_if_exists("ix_routing_operations_predecessor_id", "routing_operations")
    _drop_index_if_exists("ix_routing_operations_work_center_id", "routing_operations")
    _drop_index_if_exists("ix_routings_product_id", "routings")
    _drop_index_if_exists("ix_resources_work_center_id", "resources")

    _drop_index_if_exists("ix_bom_lines_component_id", "bom_lines")
    _drop_index_if_exists("ix_purchase_order_lines_product_id", "purchase_order_lines")
    _drop_index_if_exists("ix_inventory_transactions_location_id", "inventory_transactions")
    _drop_index_if_exists("ix_inventory_location_id", "inventory")

    _drop_index_if_exists("ix_production_order_materials_substitute_product_id", "production_order_materials")
    _drop_index_if_exists("ix_production_order_materials_original_product_id", "production_order_materials")
    _drop_index_if_exists("ix_production_order_materials_bom_line_id", "production_order_materials")

    _drop_index_if_exists("ix_production_order_operations_resource_id", "production_order_operations")
    _drop_index_if_exists("ix_production_order_operations_work_center_id", "production_order_operations")
    _drop_index_if_exists("ix_production_order_operations_routing_operation_id", "production_order_operations")

    _drop_index_if_exists("ix_production_orders_remake_of_id", "production_orders")
    _drop_index_if_exists("ix_production_orders_sales_order_line_id", "production_orders")
    _drop_index_if_exists("ix_production_orders_sales_order_id", "production_orders")
    _drop_index_if_exists("ix_production_orders_routing_id", "production_orders")
    _drop_index_if_exists("ix_production_orders_bom_id", "production_orders")
    _drop_index_if_exists("ix_production_orders_product_id", "production_orders")

    _drop_index_if_exists("ix_products_customer_id", "products")
    _drop_index_if_exists("ix_products_preferred_vendor_id", "products")

    # Drop FK constraints
    _drop_fk_if_exists("fk_quotes_sales_order", "quotes")
    _drop_fk_if_exists("fk_quotes_approved_by", "quotes")
    _drop_fk_if_exists("fk_products_customer", "products")
    _drop_fk_if_exists("fk_products_preferred_vendor", "products")
