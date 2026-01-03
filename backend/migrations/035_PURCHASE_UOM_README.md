# FilaOps: Purchase UOM Fix (1000x Cost Bug)

## Problem Solved
BOM material costs were 1000x too high because:
- Costs stored as $/KG (e.g., $25/KG for filament)
- Inventory stored in grams (G)
- System had no way to know cost was per KG, so it used $25/G
- Result: 250g × $25 = $6,250 instead of $6.25

## Solution
Added `purchase_uom` field to products to distinguish:
- `unit`: Storage/inventory unit (G for filament)
- `purchase_uom`: Unit costs are quoted in (KG for filament)

System now converts: $25/KG ÷ 1000 = $0.025/G

## Files Changed

### New Files
1. `migrations/versions/035_add_purchase_uom_to_products.py` - Alembic migration
2. `migrations/035_purchase_uom_manual.sql` - Standalone SQL (alternative)
3. `migrations/run_035_migration.py` - Python script to run migration
4. `app/services/product_uom_service.py` - UOM validation/auto-config helpers

### Modified Files
1. `app/models/product.py` - Added `purchase_uom` column
2. `app/services/inventory_service.py` - Updated `get_effective_cost_per_inventory_unit()` to use `purchase_uom`
3. `app/schemas/item.py` - Added `purchase_uom` to API schemas

## How to Apply

### Option 1: Run Python script (recommended)
```bash
cd C:\repos\filaops\backend
python migrations/run_035_migration.py
```

### Option 2: Run alembic
```bash
cd C:\repos\filaops\backend
python -m alembic upgrade head
```

### Option 3: Run SQL directly
Open `migrations/035_purchase_uom_manual.sql` in pgAdmin and execute.

## What the Migration Does

1. **Adds `purchase_uom` column** to products table

2. **Updates filament products** (by category and SKU pattern):
   - `purchase_uom` = 'KG'
   - `unit` = 'G'
   - `is_raw_material` = true

3. **Updates hardware products** (HW-* SKUs):
   - `purchase_uom` = 'EA'
   - `unit` = 'EA'

4. **Fixes BOM lines**:
   - Changes unit from 'EA' to 'G' for filament components
   - Converts quantities from KG to G (multiplies by 1000)

## How Cost Conversion Works Now

```python
# In inventory_service.py
def get_effective_cost_per_inventory_unit(product):
    base_cost = get_effective_cost(product)  # e.g., $25 ($/KG)
    
    storage_unit = product.unit              # e.g., 'G'
    purchase_unit = product.purchase_uom     # e.g., 'KG'
    
    if purchase_unit == storage_unit:
        return base_cost  # No conversion needed
    
    # Convert: $25/KG → $0.025/G
    return convert_cost_for_unit(base_cost, purchase_unit, storage_unit)
```

## Verification Queries

After running migration, verify with:

```sql
-- Check filament products
SELECT sku, unit, purchase_uom, standard_cost,
       ROUND(standard_cost / 1000, 4) as cost_per_gram
FROM products 
WHERE sku LIKE 'MAT-%' 
LIMIT 5;

-- Check BOM line costs are now correct
SELECT p.sku, bl.quantity, bl.unit, c.sku as component,
       ROUND(bl.quantity * (c.standard_cost / 1000), 2) as line_cost
FROM bom_lines bl
JOIN boms b ON b.id = bl.bom_id
JOIN products p ON p.id = b.product_id
JOIN products c ON c.id = bl.component_id
WHERE c.sku LIKE 'MAT-%';
```

## UI Considerations

When creating/editing products:
- For filaments: Set `purchase_uom` = 'KG', `unit` = 'G'
- Enter cost as $/KG (what you pay per spool)
- System automatically converts for inventory transactions

The `product_uom_service.py` has helpers:
- `get_recommended_uoms()` - Auto-suggest based on SKU/category
- `validate_product_uoms()` - Check configuration is correct
- `auto_configure_product_uoms()` - Fix products automatically
