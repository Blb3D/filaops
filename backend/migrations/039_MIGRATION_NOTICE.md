# MIGRATION REQUIRED: 039_uom_cost_normalization

## ⚠️ BREAKING CHANGE - Action Required

**Version:** 2.1.0+  
**Date:** 2025-01-08  
**Priority:** CRITICAL  

---

## What Changed

This migration fixes recurring UOM/cost calculation bugs by establishing transactions as the **single source of truth**.

### Database Changes

| Table | Column | Type | Description |
|-------|--------|------|-------------|
| `products` | `purchase_factor` | Numeric(18,6) | Conversion: 1 purchase_uom = X unit |
| `inventory_transactions` | `total_cost` | Numeric(18,4) | Pre-calculated total |
| `inventory_transactions` | `unit` | String(20) | Stored unit (G, EA, BOX) |

### Why This Matters

**Before:** UI calculated `total_cost = quantity * cost_per_unit`  
**Problem:** UI didn't know the unit mismatch (cost was $/KG, quantity was in G)  
**Result:** Displayed $0.04 instead of $36.00

**After:** Backend calculates and stores `total_cost` at transaction creation  
**UI:** Displays exactly what API returns - no math

---

## How to Migrate

### Step 1: Backup Your Database
```bash
pg_dump -U postgres -d filaops_prod > backup_before_039.sql
```

### Step 2: Run Migration
```bash
cd backend
alembic upgrade head
```

### Step 3: Verify Data
```sql
-- Check that total_cost is populated
SELECT COUNT(*) as total,
       COUNT(total_cost) as with_total_cost,
       COUNT(unit) as with_unit
FROM inventory_transactions;

-- Spot check a material receipt
SELECT sku, quantity, unit, cost_per_unit, total_cost
FROM inventory_transactions it
JOIN products p ON it.product_id = p.id
WHERE p.material_type_id IS NOT NULL
LIMIT 5;
```

### Step 4: Update Frontend (if custom)
If you've customized the frontend, update these files:
- Remove any `quantity * cost_per_unit` calculations
- Display `transaction.total_cost` directly
- Display `transaction.unit` for the unit label

---

## Rollback (if needed)

```bash
alembic downgrade 038_add_missing_sales_order_columns
```

⚠️ Rolling back will remove the new columns. You'll need to re-run the migration to restore them.

---

## Questions?

This migration addresses a bug that occurred 10 times and caused data loss twice. If you encounter issues, please report them immediately.

Contact: [Your support channel]
