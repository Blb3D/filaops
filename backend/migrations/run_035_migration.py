"""
Run this script to apply the purchase_uom migration.

Usage:
    cd C:\repos\filaops\backend
    python migrations/run_035_migration.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.core.config import settings


def run_migration():
    print("=" * 60)
    print("FilaOps Migration: Add purchase_uom to products")
    print("=" * 60)

    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        # Step 1: Add column
        print("\n[1/8] Adding purchase_uom column...")
        conn.execute(
            text("""
            ALTER TABLE products ADD COLUMN IF NOT EXISTS purchase_uom VARCHAR(20)
        """)
        )
        conn.commit()
        print("      Done.")

        # Step 2: Update filaments by category
        print("\n[2/8] Updating filament products by category...")
        result = conn.execute(
            text("""
            UPDATE products 
            SET purchase_uom = 'KG',
                unit = 'G',
                is_raw_material = true
            WHERE category_id IN (
                WITH RECURSIVE category_tree AS (
                    SELECT id FROM item_categories WHERE code = 'FILAMENT'
                    UNION ALL
                    SELECT ic.id FROM item_categories ic
                    INNER JOIN category_tree ct ON ic.parent_id = ct.id
                )
                SELECT id FROM category_tree
            )
            RETURNING sku
        """)
        )
        conn.commit()
        count = len(result.fetchall())
        print(f"      Updated {count} products by category.")

        # Step 3: Update by SKU pattern
        print("\n[3/8] Updating filament products by SKU pattern (MAT-*, FIL-*)...")
        result = conn.execute(
            text("""
            UPDATE products 
            SET purchase_uom = 'KG',
                unit = 'G',
                is_raw_material = true
            WHERE (sku LIKE 'MAT-%' OR sku LIKE 'FIL-%')
            AND purchase_uom IS NULL
            RETURNING sku
        """)
        )
        conn.commit()
        count = len(result.fetchall())
        print(f"      Updated {count} additional products by SKU.")

        # Step 4: Update hardware
        print("\n[4/8] Updating hardware products (HW-*)...")
        result = conn.execute(
            text("""
            UPDATE products 
            SET purchase_uom = 'EA',
                unit = 'EA'
            WHERE sku LIKE 'HW-%'
            AND purchase_uom IS NULL
            RETURNING sku
        """)
        )
        conn.commit()
        count = len(result.fetchall())
        print(f"      Updated {count} hardware products.")

        # Step 5: Default everything else
        print("\n[5/8] Setting default purchase_uom for remaining products...")
        result = conn.execute(
            text("""
            UPDATE products 
            SET purchase_uom = COALESCE(unit, 'EA')
            WHERE purchase_uom IS NULL
            RETURNING sku
        """)
        )
        conn.commit()
        count = len(result.fetchall())
        print(f"      Updated {count} remaining products.")

        # Step 6: Fix BOM line units
        print("\n[6/8] Fixing BOM line units for filaments...")
        result = conn.execute(
            text("""
            UPDATE bom_lines bl
            SET unit = p.unit
            FROM products p
            WHERE bl.component_id = p.id
            AND p.purchase_uom = 'KG'
            AND p.unit = 'G'
            AND bl.unit = 'EA'
            RETURNING bl.id
        """)
        )
        conn.commit()
        count = len(result.fetchall())
        print(f"      Fixed {count} BOM line units.")

        # Step 7: Convert BOM quantities from KG to G
        print("\n[7/8] Converting BOM quantities from KG to G...")
        result = conn.execute(
            text("""
            UPDATE bom_lines bl
            SET quantity = bl.quantity * 1000
            FROM products p
            WHERE bl.component_id = p.id
            AND p.purchase_uom = 'KG'
            AND p.unit = 'G'
            AND bl.unit = 'G'
            AND bl.quantity < 10
            RETURNING bl.id, bl.quantity
        """)
        )
        conn.commit()
        rows = result.fetchall()
        print(f"      Converted {len(rows)} BOM line quantities.")

        # Step 8: Update alembic version
        print("\n[8/8] Updating alembic version...")
        conn.execute(
            text("""
            UPDATE alembic_version SET version_num = '035_add_purchase_uom_to_products'
        """)
        )
        conn.commit()
        print("      Done.")

        # Verification
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        # Check filament products
        print("\nFilament products (sample):")
        result = conn.execute(
            text("""
            SELECT sku, unit, purchase_uom, standard_cost,
                   ROUND(standard_cost / 1000, 4) as cost_per_gram
            FROM products 
            WHERE sku LIKE 'MAT-%' OR sku LIKE 'FIL-%'
            LIMIT 5
        """)
        )
        for row in result:
            print(
                f"  {row.sku}: unit={row.unit}, purchase_uom={row.purchase_uom}, "
                f"${row.standard_cost}/KG = ${row.cost_per_gram}/G"
            )

        # Check BOM lines
        print("\nBOM lines with filaments:")
        result = conn.execute(
            text("""
            SELECT p.sku as product, bl.quantity, bl.unit, c.sku as component,
                   ROUND(bl.quantity * (c.standard_cost / 1000), 2) as line_cost
            FROM bom_lines bl
            JOIN boms b ON b.id = bl.bom_id
            JOIN products p ON p.id = b.product_id
            JOIN products c ON c.id = bl.component_id
            WHERE c.sku LIKE 'MAT-%' OR c.sku LIKE 'FIL-%'
        """)
        )
        for row in result:
            print(f"  {row.product}: {row.quantity} {row.unit} of {row.component} = ${row.line_cost}")

        print("\n" + "=" * 60)
        print("Migration complete!")
        print("=" * 60)


if __name__ == "__main__":
    run_migration()
