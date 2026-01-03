-- ============================================================================
-- FilaOps Migration: Add purchase_uom to products
-- Run this in psql or pgAdmin connected to the filaops database
-- ============================================================================

-- STEP 1: Add the purchase_uom column
ALTER TABLE products ADD COLUMN IF NOT EXISTS purchase_uom VARCHAR(20);

-- STEP 2: Get filament category IDs (parent and children)
-- First, let's see what we have
SELECT id, code, name, parent_id FROM item_categories WHERE code = 'FILAMENT' OR parent_id IN (SELECT id FROM item_categories WHERE code = 'FILAMENT');

-- STEP 3: Update filaments by category (Filament parent and all children)
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
);

-- STEP 4: Also update MAT-* and FIL-* SKUs that might not have category set
UPDATE products 
SET purchase_uom = 'KG',
    unit = 'G',
    is_raw_material = true
WHERE (sku LIKE 'MAT-%' OR sku LIKE 'FIL-%')
AND purchase_uom IS NULL;

-- STEP 5: Hardware (HW-*): purchase and store in EA
UPDATE products 
SET purchase_uom = 'EA',
    unit = 'EA'
WHERE sku LIKE 'HW-%'
AND purchase_uom IS NULL;

-- STEP 6: Default: set purchase_uom = unit for everything else
UPDATE products 
SET purchase_uom = COALESCE(unit, 'EA')
WHERE purchase_uom IS NULL;

-- STEP 7: Fix BOM lines that have wrong units for filaments
-- BOM lines for filaments should use G (storage unit), not EA
UPDATE bom_lines bl
SET unit = p.unit
FROM products p
WHERE bl.component_id = p.id
AND p.purchase_uom = 'KG'
AND p.unit = 'G'
AND bl.unit = 'EA';

-- STEP 8: Convert BOM line quantities that look like KG values to G
-- (quantities < 10 for filaments are likely KG values that need *1000)
UPDATE bom_lines bl
SET quantity = bl.quantity * 1000
FROM products p
WHERE bl.component_id = p.id
AND p.purchase_uom = 'KG'
AND p.unit = 'G'
AND bl.unit = 'G'
AND bl.quantity < 10;

-- STEP 9: Update alembic version
UPDATE alembic_version SET version_num = '035_add_purchase_uom_to_products';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check filament products now have correct UOMs
SELECT sku, name, unit, purchase_uom, is_raw_material, standard_cost,
       CASE 
           WHEN purchase_uom = 'KG' AND unit = 'G' THEN '✓ Filament OK'
           WHEN purchase_uom = 'EA' AND unit = 'EA' THEN '✓ Hardware OK'
           ELSE '? Check this'
       END as status
FROM products 
WHERE sku LIKE 'MAT-%' OR sku LIKE 'FIL-%' OR sku LIKE 'HW-%'
ORDER BY sku
LIMIT 20;

-- Check BOM lines now have correct units
SELECT 
    p.sku as product_sku,
    bl.quantity,
    bl.unit as bom_unit,
    c.sku as component_sku,
    c.unit as component_storage_unit,
    c.purchase_uom as component_purchase_unit,
    CASE 
        WHEN bl.unit = c.unit THEN '✓ Match'
        ELSE '⚠️ MISMATCH'
    END as status
FROM bom_lines bl
JOIN boms b ON b.id = bl.bom_id
JOIN products p ON p.id = b.product_id
JOIN products c ON c.id = bl.component_id
WHERE c.sku LIKE 'MAT-%' OR c.sku LIKE 'FIL-%';

-- Verify cost interpretation will be correct
-- Costs should be ~$15-50 per KG for filaments
SELECT sku, name, purchase_uom, unit, standard_cost,
       CASE 
           WHEN purchase_uom = 'KG' AND standard_cost BETWEEN 10 AND 100 
           THEN '✓ Cost looks like $/KG'
           WHEN purchase_uom = 'KG' AND standard_cost < 1 
           THEN '⚠️ Cost looks like $/G - may need to multiply by 1000'
           WHEN purchase_uom = 'EA' 
           THEN '✓ EA items OK'
           ELSE '? Check cost'
       END as cost_check
FROM products 
WHERE sku LIKE 'MAT-%' OR sku LIKE 'FIL-%'
ORDER BY sku
LIMIT 20;
