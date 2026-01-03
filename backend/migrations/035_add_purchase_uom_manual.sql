-- ============================================================================
-- FilaOps V1 Fix: Add purchase_uom to products for proper cost conversion
-- ============================================================================
-- 
-- PROBLEM: 1000x cost calculation error
-- - Products store cost as $/KG (e.g., $20/KG for filament)
-- - Inventory stores quantity in G (e.g., 1000 G)
-- - Without knowing cost is "per KG", system calculated: 1000 G × $20 = $20,000 (WRONG!)
-- - Should be: 1000 G × ($20/KG ÷ 1000) = $20 (CORRECT!)
--
-- SOLUTION: Add purchase_uom field to explicitly store what unit costs are in
-- - purchase_uom = 'KG' means standard_cost is $/KG
-- - unit = 'G' means inventory is tracked in grams
-- - System converts: $/KG → $/G when creating transactions
--
-- Run this script against your filaops database
-- ============================================================================

BEGIN;

-- Step 1: Add purchase_uom column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'purchase_uom'
    ) THEN
        ALTER TABLE products ADD COLUMN purchase_uom VARCHAR(20);
        RAISE NOTICE 'Added purchase_uom column to products table';
    ELSE
        RAISE NOTICE 'purchase_uom column already exists';
    END IF;
END $$;

-- Step 2: Get filament category IDs (parent and children)
CREATE TEMP TABLE filament_categories AS
WITH RECURSIVE category_tree AS (
    SELECT id FROM item_categories WHERE code = 'FILAMENT'
    UNION ALL
    SELECT ic.id FROM item_categories ic
    INNER JOIN category_tree ct ON ic.parent_id = ct.id
)
SELECT id FROM category_tree;

-- Step 3: Update filaments by category - purchase in KG, store in G
UPDATE products 
SET purchase_uom = 'KG',
    unit = 'G',
    is_raw_material = true
WHERE category_id IN (SELECT id FROM filament_categories);

-- Show what was updated
DO $$
DECLARE
    cnt INTEGER;
BEGIN
    SELECT COUNT(*) INTO cnt FROM products 
    WHERE category_id IN (SELECT id FROM filament_categories);
    RAISE NOTICE 'Updated % products by filament category', cnt;
END $$;

-- Step 4: Update filaments by SKU pattern (MAT-* and FIL-*)
UPDATE products 
SET purchase_uom = 'KG',
    unit = 'G',
    is_raw_material = true
WHERE (sku LIKE 'MAT-%' OR sku LIKE 'FIL-%')
AND purchase_uom IS NULL;

-- Show what was updated
DO $$
DECLARE
    cnt INTEGER;
BEGIN
    SELECT COUNT(*) INTO cnt FROM products 
    WHERE (sku LIKE 'MAT-%' OR sku LIKE 'FIL-%');
    RAISE NOTICE 'Total MAT-*/FIL-* products: %', cnt;
END $$;

-- Step 5: Update hardware by SKU pattern (HW-*)
UPDATE products 
SET purchase_uom = 'EA',
    unit = 'EA'
WHERE sku LIKE 'HW-%'
AND purchase_uom IS NULL;

-- Step 6: Default everything else - purchase_uom = unit
UPDATE products 
SET purchase_uom = COALESCE(unit, 'EA')
WHERE purchase_uom IS NULL;

-- Step 7: Fix BOM lines that have wrong units for filaments
-- BOM lines should use the component's storage unit (G), not EA
UPDATE bom_lines bl
SET unit = p.unit
FROM products p
WHERE bl.component_id = p.id
AND p.purchase_uom = 'KG'
AND p.unit = 'G'
AND bl.unit = 'EA';

-- Show what was updated
DO $$
DECLARE
    cnt INTEGER;
BEGIN
    GET DIAGNOSTICS cnt = ROW_COUNT;
    RAISE NOTICE 'Fixed % BOM lines with wrong unit', cnt;
END $$;

-- Step 8: Fix BOM line quantities that look like KG values but should be G
-- Only for filaments where quantity < 10 (likely entered as KG, should be G)
UPDATE bom_lines bl
SET quantity = bl.quantity * 1000
FROM products p
WHERE bl.component_id = p.id
AND p.purchase_uom = 'KG'
AND p.unit = 'G'
AND bl.unit = 'G'
AND bl.quantity < 10;

-- Show what was updated
DO $$
DECLARE
    cnt INTEGER;
BEGIN
    GET DIAGNOSTICS cnt = ROW_COUNT;
    RAISE NOTICE 'Converted % BOM line quantities from KG to G', cnt;
END $$;

-- Cleanup temp table
DROP TABLE filament_categories;

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES - Run these after the migration
-- ============================================================================

-- Check filament products have correct UOMs
SELECT 
    sku, 
    name, 
    purchase_uom, 
    unit, 
    standard_cost,
    CASE 
        WHEN purchase_uom = 'KG' AND unit = 'G' THEN '✓ Correct'
        ELSE '⚠️ Check this'
    END as status
FROM products 
WHERE sku LIKE 'MAT-%' OR sku LIKE 'FIL-%'
ORDER BY sku
LIMIT 20;

-- Check BOM lines for filaments have correct quantities
SELECT 
    p.sku as product,
    bl.quantity,
    bl.unit as bom_unit,
    c.sku as component,
    c.purchase_uom,
    c.unit as storage_unit,
    c.standard_cost,
    ROUND(bl.quantity * (c.standard_cost / 1000), 2) as calculated_cost,
    CASE 
        WHEN bl.unit = c.unit THEN '✓ Units match'
        ELSE '⚠️ Unit mismatch'
    END as unit_status,
    CASE 
        WHEN bl.quantity >= 10 THEN '✓ Looks like grams'
        ELSE '⚠️ Might be KG (< 10)'
    END as qty_status
FROM bom_lines bl
JOIN boms b ON b.id = bl.bom_id
JOIN products p ON p.id = b.product_id
JOIN products c ON c.id = bl.component_id
WHERE c.purchase_uom = 'KG'
ORDER BY p.sku, bl.sequence;
