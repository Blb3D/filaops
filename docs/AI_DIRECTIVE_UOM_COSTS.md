# UOM & Cost Handling - CRITICAL AI DIRECTIVE

> **WARNING**: This document exists because UOM/cost bugs have occurred 10+ times.  
> Production data was lost twice. READ THIS BEFORE TOUCHING COST OR UOM CODE.

---

## The Law

### 1. Transactions are the SINGLE SOURCE OF TRUTH

```
Transactions store:
├── quantity        → The amount (in consumption unit)
├── unit            → The unit (G, EA, BOX) - STORED, not inferred
├── cost_per_unit   → Cost per unit ($/G for materials, $/EA for discrete)
└── total_cost      → PRE-CALCULATED: quantity × cost_per_unit
```

**UI displays ONLY what API returns. ZERO client-side cost math.**

### 2. Product Table Rules

| Field | Purpose | Example |
|-------|---------|---------|
| `unit` | Consumption/storage unit | G, EA, BOX |
| `purchase_uom` | What we buy in | KG, BOX |
| `purchase_factor` | Conversion factor | 1000 (1 KG = 1000 G) |

**Rule:** If `purchase_uom ≠ unit`, then `purchase_factor` is REQUIRED.

### 3. PO Receipt Flow (NEVER SKIP STEPS)

```
PO Line Input:
├── quantity_ordered: 3
├── purchase_unit: KG
└── unit_cost: $20.00/KG

     │
     ▼  Apply purchase_factor (1000)

Transaction Output:
├── quantity: 3000 (G)
├── unit: 'G'
├── cost_per_unit: $0.02/G ($20 ÷ 1000)
└── total_cost: $60.00 (3000 × $0.02)
```

### 4. The Frontend Rule

```
❌ WRONG (causes bugs):
   const total = transaction.quantity * transaction.cost_per_unit;
   const unit = inferUnitFromProduct(product);

✅ CORRECT:
   const total = transaction.total_cost;
   const unit = transaction.unit;
```

**If you're doing cost math in frontend → STOP → You're doing it wrong.**

---

## Conversion Reference

### Materials (Filament)

| Purchase UOM | Storage Unit | Factor | Cost Conversion |
|--------------|--------------|--------|-----------------|
| KG | G | 1000 | $20/KG → $0.02/G |
| LB | G | 453.592 | $20/LB → $0.044/G |
| OZ | G | 28.3495 | $5/OZ → $0.176/G |
| G | G | 1 | $0.02/G → $0.02/G |

### Discrete Items

| Purchase UOM | Storage Unit | Factor | Example |
|--------------|--------------|--------|---------|
| BOX (100ct) | EA | 100 | $15/BOX → $0.15/EA |
| PACK (12ct) | EA | 12 | $24/PACK → $2.00/EA |
| EA | EA | 1 | $5/EA → $5/EA |

---

## Code Locations

### Backend (single source of truth)
- **Receipt processing:** `backend/app/api/v1/endpoints/purchase_orders.py`
  - Function: `receive_purchase_order()`
  - This is where cost conversion happens
  
- **Consumption:** `backend/app/services/inventory_service.py`
  - Uses `transaction.cost_per_unit` directly
  
- **UOM conversions:** `backend/app/services/uom_service.py`
  - `convert_quantity_safe()` - quantity conversion
  - `get_conversion_factor()` - factor lookup

### Frontend (display only)
- **Transaction list:** Display `transaction.total_cost` and `transaction.unit`
- **NO calculations allowed**

---

## Debugging Checklist

When costs look wrong:

1. **Check the transaction record:**
   ```sql
   SELECT quantity, unit, cost_per_unit, total_cost
   FROM inventory_transactions WHERE id = ?;
   ```

2. **Verify the math:**
   - `total_cost` should equal `quantity × cost_per_unit`
   - `unit` should match quantity's unit (G for materials)

3. **Check the product:**
   ```sql
   SELECT unit, purchase_uom, purchase_factor
   FROM products WHERE id = ?;
   ```

4. **If transaction data is wrong:** Fix in `receive_purchase_order()`
5. **If display is wrong:** Fix in frontend (should just display API data)

---

## History

| Date | Bug | Impact | Root Cause |
|------|-----|--------|------------|
| Multiple | Costs 1000x too high | Display error | UI calculated qty × cost without unit conversion |
| Multiple | Costs 1000x too low | Data corruption | Cost stored as $/KG but qty in G |
| 2x | Data loss | Production wiped | Bad migration attempts |

**This directive prevents recurrence.**

---

## AI Agent Instructions

When working on FilaOps cost/UOM code:

1. **Read this document first**
2. **Never add cost calculations to frontend**
3. **All cost math goes through `receive_purchase_order()` or similar backend functions**
4. **If unsure, ask the human before changing cost-related code**
5. **Test with known values:**
   - Input: 3 KG @ $20/KG
   - Expected transaction: 3000 G @ $0.02/G = $60.00 total

**Violations of these rules require explicit human approval.**
