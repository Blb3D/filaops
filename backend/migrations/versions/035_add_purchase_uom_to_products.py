"""Add purchase_uom to products table for proper cost conversion

This migration adds the purchase_uom field to distinguish between:
- purchase_uom: How we BUY items (KG, BOX, ROLL, EA)
- unit: How we STORE/track items (G, EA)

Costs (standard_cost, average_cost, last_cost) are stored per PURCHASE unit.
The system converts to cost per STORAGE unit when calculating COGS.

Example:
- Filament: purchase_uom='KG', unit='G', standard_cost=20.00 ($/KG)
- System calculates: $20/KG ÷ 1000 = $0.02/G for transactions
- This fixes the 1000x cost bug where costs were misapplied

Revision ID: 035
Revises: 034
Create Date: 2025-01-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '035'
down_revision: Union[str, None] = '034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add purchase_uom column and backfill existing products."""
    
    # 1. Add purchase_uom column
    op.add_column('products', 
        sa.Column('purchase_uom', sa.String(length=20), nullable=True,
                  comment='Unit of measure for purchasing (KG, BOX, EA). Costs are per this unit.'))
    
    # 2. Backfill existing products based on category and SKU patterns
    # Use raw SQL for data migration
    connection = op.get_bind()
    
    # Get the Filament category ID and its children
    filament_categories = connection.execute(sa.text("""
        WITH RECURSIVE category_tree AS (
            SELECT id FROM item_categories WHERE code = 'FILAMENT'
            UNION ALL
            SELECT ic.id FROM item_categories ic
            INNER JOIN category_tree ct ON ic.parent_id = ct.id
        )
        SELECT id FROM category_tree
    """)).fetchall()
    filament_category_ids = [row[0] for row in filament_categories]
    
    if filament_category_ids:
        # Filaments: purchase in KG, store in G
        connection.execute(sa.text("""
            UPDATE products 
            SET purchase_uom = 'KG',
                unit = 'G',
                is_raw_material = true
            WHERE category_id IN :category_ids
        """), {'category_ids': tuple(filament_category_ids)})
    
    # Also catch MAT-* and FIL-* SKUs that might not have category set
    connection.execute(sa.text("""
        UPDATE products 
        SET purchase_uom = 'KG',
            unit = 'G',
            is_raw_material = true
        WHERE (sku LIKE 'MAT-%' OR sku LIKE 'FIL-%')
        AND purchase_uom IS NULL
    """))
    
    # Hardware (HW-*): purchase and store in EA
    connection.execute(sa.text("""
        UPDATE products 
        SET purchase_uom = 'EA',
            unit = 'EA'
        WHERE sku LIKE 'HW-%'
        AND purchase_uom IS NULL
    """))
    
    # Default: set purchase_uom = unit for everything else
    connection.execute(sa.text("""
        UPDATE products 
        SET purchase_uom = COALESCE(unit, 'EA')
        WHERE purchase_uom IS NULL
    """))
    
    # 3. Fix BOM lines that have wrong units
    # BOM lines for filaments should use G (storage unit), not EA
    connection.execute(sa.text("""
        UPDATE bom_lines bl
        SET unit = p.unit
        FROM products p
        WHERE bl.component_id = p.id
        AND p.purchase_uom != p.unit
        AND bl.unit = 'EA'
    """))
    
    # 4. Also need to fix quantity for any BOM lines that were entered as KG values
    # but marked as EA (e.g., 0.15 EA should be 150 G)
    # Only do this for filaments where quantity looks like KG (< 10)
    connection.execute(sa.text("""
        UPDATE bom_lines bl
        SET quantity = bl.quantity * 1000
        FROM products p
        WHERE bl.component_id = p.id
        AND p.purchase_uom = 'KG'
        AND p.unit = 'G'
        AND bl.unit = 'G'
        AND bl.quantity < 10
    """))


def downgrade() -> None:
    """Remove purchase_uom column."""
    op.drop_column('products', 'purchase_uom')
