"""UOM Cost Normalization - Single Source of Truth for Transactions

CRITICAL MIGRATION - Fixes recurring UOM/cost bugs (occurred 10x, 2x data loss)

This migration establishes transactions as the SINGLE SOURCE OF TRUTH by:
1. Adding `purchase_factor` to products - explicit conversion factor
2. Adding `total_cost` to transactions - pre-calculated, no UI math
3. Adding `unit` to transactions - stored unit, not inferred
4. Backfilling all existing data

After this migration:
- UI displays ONLY what API returns
- Zero client-side cost calculations
- All cost math happens at transaction creation time

Revision ID: 039_uom_cost_normalization
Revises: 038_add_missing_so_cols
Create Date: 2025-01-08

"""
from typing import Sequence, Union
from decimal import Decimal

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '039_uom_cost_normalization'
down_revision: Union[str, None] = '038_add_missing_so_cols'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add purchase_factor, total_cost, and transaction unit columns.
    Backfill all existing data.
    """
    connection = op.get_bind()
    
    # =========================================================================
    # STEP 1: Add purchase_factor to products
    # =========================================================================
    # This is the explicit conversion: 1 purchase_uom = X unit
    # Example: 1 KG = 1000 G, 1 BOX = 100 EA
    op.add_column('products',
        sa.Column('purchase_factor', sa.Numeric(18, 6), nullable=True,
                  comment='Conversion factor: 1 purchase_uom = X unit. E.g., 1000 for KG->G'))
    
    # =========================================================================
    # STEP 2: Add total_cost and unit to inventory_transactions
    # =========================================================================
    op.add_column('inventory_transactions',
        sa.Column('total_cost', sa.Numeric(18, 4), nullable=True,
                  comment='Pre-calculated total: quantity * cost_per_unit. UI displays this directly.'))
    
    op.add_column('inventory_transactions',
        sa.Column('unit', sa.String(20), nullable=True,
                  comment='Unit of measure for quantity (G, EA, BOX). Stored, not inferred.'))
    
    # =========================================================================
    # STEP 3: Backfill purchase_factor for existing products
    # =========================================================================
    
    # Materials (KG -> G): factor = 1000
    connection.execute(sa.text("""
        UPDATE products
        SET purchase_factor = 1000
        WHERE purchase_uom = 'KG' AND unit = 'G'
    """))
    
    # Materials (LB -> G): factor = 453.592
    connection.execute(sa.text("""
        UPDATE products
        SET purchase_factor = 453.592
        WHERE purchase_uom = 'LB' AND unit = 'G'
    """))
    
    # Materials (OZ -> G): factor = 28.3495
    connection.execute(sa.text("""
        UPDATE products
        SET purchase_factor = 28.3495
        WHERE purchase_uom = 'OZ' AND unit = 'G'
    """))
    
    # Same unit (EA -> EA, G -> G, etc.): factor = 1
    connection.execute(sa.text("""
        UPDATE products
        SET purchase_factor = 1
        WHERE purchase_uom = unit
        AND purchase_factor IS NULL
    """))
    
    # Default everything else to 1 (same unit assumption)
    connection.execute(sa.text("""
        UPDATE products
        SET purchase_factor = 1
        WHERE purchase_factor IS NULL
    """))
    
    # =========================================================================
    # STEP 4: Backfill total_cost for existing transactions
    # =========================================================================
    connection.execute(sa.text("""
        UPDATE inventory_transactions
        SET total_cost = quantity * COALESCE(cost_per_unit, 0)
        WHERE total_cost IS NULL
    """))
    
    # =========================================================================
    # STEP 5: Backfill unit for existing transactions from product
    # =========================================================================
    # For materials, transactions are stored in G (consumption unit)
    # For non-materials, transactions are stored in product.unit
    
    # Materials with material_type_id: unit = 'G'
    connection.execute(sa.text("""
        UPDATE inventory_transactions it
        SET unit = 'G'
        FROM products p
        WHERE it.product_id = p.id
        AND p.material_type_id IS NOT NULL
        AND it.unit IS NULL
    """))
    
    # Materials by SKU pattern: unit = 'G'
    connection.execute(sa.text("""
        UPDATE inventory_transactions it
        SET unit = 'G'
        FROM products p
        WHERE it.product_id = p.id
        AND (p.sku LIKE 'MAT-%' OR p.sku LIKE 'FIL-%')
        AND it.unit IS NULL
    """))
    
    # Everything else: use product.unit
    connection.execute(sa.text("""
        UPDATE inventory_transactions it
        SET unit = COALESCE(p.unit, 'EA')
        FROM products p
        WHERE it.product_id = p.id
        AND it.unit IS NULL
    """))
    
    # Final fallback for any orphaned transactions
    connection.execute(sa.text("""
        UPDATE inventory_transactions
        SET unit = 'EA'
        WHERE unit IS NULL
    """))
    
    # =========================================================================
    # STEP 6: Add index for common queries
    # =========================================================================
    op.create_index(
        'ix_inventory_transactions_unit',
        'inventory_transactions',
        ['unit']
    )
    
    print("=" * 70)
    print("MIGRATION 039 COMPLETE: UOM Cost Normalization")
    print("=" * 70)
    print("✓ Added products.purchase_factor")
    print("✓ Added inventory_transactions.total_cost")
    print("✓ Added inventory_transactions.unit")
    print("✓ Backfilled all existing data")
    print("")
    print("IMPORTANT: Update your frontend to display transaction.total_cost")
    print("           directly instead of calculating quantity * cost_per_unit")
    print("=" * 70)


def downgrade() -> None:
    """Remove added columns."""
    op.drop_index('ix_inventory_transactions_unit', 'inventory_transactions')
    op.drop_column('inventory_transactions', 'unit')
    op.drop_column('inventory_transactions', 'total_cost')
    op.drop_column('products', 'purchase_factor')
