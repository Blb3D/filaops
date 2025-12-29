# FilaOps Gap Analysis: Spec vs Code
## Date: 2025-12-30

---

## Executive Summary

| Category | Status |
|----------|--------|
| **Core Entities** | ⚠️ Mostly aligned, minor gaps |
| **Workflows** | ⚠️ Core exists, but status machines differ |
| **MRP** | ✅ Solid implementation |
| **Blocking Issues** | ✅ Well implemented |
| **Dashboards** | ❌ Not matching spec (generic, not morning/evening) |
| **UOM Conversions** | ⚠️ Complex, has bugs (was a pain point) |
| **Data Integrity** | ⚠️ Some gaps in validation |

---

## PART 1: CORE ENTITIES

### 1.1 Items (Product Model)

| Spec Field | Code Field | Status | Notes |
|------------|------------|--------|-------|
| sku | sku | ✅ | |
| name | name | ✅ | |
| item_type | item_type | ⚠️ | Spec: raw_material, finished_good, packaging. Code: finished_good, component, supply, service |
| standard_cost | standard_cost | ✅ | |
| active | active | ✅ | |
| replenishment_type | stocking_policy | ⚠️ | Spec: reorder_point, order_driven. Code: stocked, on_demand |
| reorder_point | reorder_point | ✅ | |
| reorder_qty | min_order_qty | ⚠️ | Different name, similar purpose |
| base_uom | unit | ✅ | |
| purchase_uom | (missing) | ❌ | **NOT IN CODE** - stored on PO line instead |
| purchase_conversion | (missing) | ❌ | **NOT IN CODE** - conversion inline |

**GAP:** UOM configuration is not on the Product model. Conversions happen inline in MRP/services using `uom_service.py`. This makes it hard to know "how do I buy PLA?" without looking at a PO.

**RECOMMENDATION:** Add `purchase_uom` and `purchase_conversion_factor` to Product model, OR create a `ProductUOM` junction table.

---

### 1.2 Bill of Materials

| Spec Field | Code Field | Status | Notes |
|------------|------------|--------|-------|
| product_id | product_id | ✅ | |
| component_id | component_id | ✅ | |
| quantity_per | quantity | ✅ | |
| scrap_pct | scrap_factor | ✅ | |
| print_time_minutes | (missing) | ❌ | **NOT ON BOM** - on Product.gcode_file_path? |
| gcode_file | (missing) | ⚠️ | On Product, not BOM |

**EXTRA in Code:**
- `consume_stage` (production, shipping) - **GOOD** for packaging
- `is_cost_only` - for overhead items
- `unit` (explicit UOM per line) - **GOOD**

**GAP:** Print time not on BOM. Need it for pricing formula.

---

### 1.3 Customers

| Spec Field | Code Field | Status | Notes |
|------------|------------|--------|-------|
| code | (missing) | ❌ | Code uses User model, no customer code |
| name | (via User) | ⚠️ | first_name + last_name or company_name |
| email | email | ✅ | |
| price_level | (missing) | ❌ | **NOT IN CODE** - no retail vs wholesale |

**GAP:** No dedicated Customer model. Uses User model. Missing price_level for wholesale pricing.

---

### 1.4 Vendors

| Spec Field | Code Field | Status | Notes |
|------------|------------|--------|-------|
| code | code | ✅ | |
| name | name | ✅ | |
| lead_time_days | (missing) | ❌ | **NOT ON VENDOR** - on Product.lead_time_days |

**GAP:** Lead time on Product, not Vendor. Spec says per-vendor.

---

### 1.5 UOM

**Code Status:** Good `UnitOfMeasure` model with `to_base_factor`. Supports conversions.

**GAP:** The inline conversion logic in `mrp.py` (`INLINE_UOM_CONVERSIONS`) duplicates what should be in the database. This is fragile.

---

### 1.6 Inventory Locations

| Spec Code | Code Exists | Status |
|-----------|-------------|--------|
| MAIN | ✅ | Via InventoryLocation model |
| WIP | ⚠️ | Can create, not enforced |
| SHIP | ⚠️ | Can create, not enforced |

**Status:** Location model exists, but workflows don't enforce location transfers.

---

## PART 2: WORKFLOWS

### 2.1 Quote

| Spec Status | Code Status | Match |
|-------------|-------------|-------|
| draft | (exists) | ✅ |
| sent | sent/pending_approval | ⚠️ |
| converted | accepted | ⚠️ |
| expired | expired | ✅ |
| cancelled | rejected/cancelled | ⚠️ |

**GAP:** Status names differ. Code has more granular statuses.

**Convert to SO:** `quote_conversion_service.py` exists - ✅ GOOD

---

### 2.2 Sales Order

| Spec Status | Code Status | Match |
|-------------|-------------|-------|
| draft | draft | ✅ |
| confirmed | confirmed | ✅ |
| in_production | in_production | ✅ |
| ready | ready_to_ship | ✅ |
| shipped | shipped | ✅ |
| cancelled | cancelled | ✅ |

**EXTRA in Code:**
- pending_payment, payment_failed
- partially_shipped
- delivered, completed
- on_hold

**GAP:** Code has more statuses (good for real-world), but state machine not enforced in code.

**Order Missing Material Button:** 
- `blocking_issues.py` calculates shortages ✅
- `resolution_actions` generated ✅
- **BUT:** Frontend button → PO creation flow may be broken (per original complaint)

---

### 2.3 Production Order (WO)

| Spec Status | Code Status | Match |
|-------------|-------------|-------|
| draft | draft | ✅ |
| released | released | ✅ |
| in_progress | in_progress | ✅ |
| complete | completed/closed | ⚠️ |
| cancelled | cancelled | ✅ |

**EXTRA in Code:**
- scheduled
- qc_hold, scrapped
- on_hold

**GOOD:** QC tracking, scrap reasons, split orders - more than spec requires.

---

### 2.4 Purchase Order

| Spec Status | Code Status | Match |
|-------------|-------------|-------|
| draft | draft | ✅ |
| sent | ordered | ⚠️ |
| partial | (partially_received?) | ⚠️ |
| received | received/closed | ⚠️ |
| cancelled | cancelled | ✅ |

**Code has:** shipped (from vendor) - GOOD

---

### 2.5 Inventory Transactions

| Spec Type | Code Type | Status |
|-----------|-----------|--------|
| receive | receive, po_receipt | ✅ |
| issue | consumption | ⚠️ |
| complete | production_complete | ✅ |
| ship | shipment | ✅ |
| adjust | adjustment | ✅ |
| scrap | scrap | ✅ |

**EXTRA in Code:**
- reservation, reservation_release (for allocations)
- transfer

**Status:** Comprehensive, probably more than needed.

---

## PART 3: MRP

**Overall:** ✅ **SOLID IMPLEMENTATION**

| Spec Requirement | Code Status | Notes |
|------------------|-------------|-------|
| BOM Explosion | ✅ | `explode_bom()` - recursive, handles cycles |
| Net Requirements | ✅ | `calculate_net_requirements()` |
| Shortage Detection | ✅ | Returns `net_shortage` |
| Reorder Alerts | ⚠️ | Logic exists but alerting not wired up |
| Planned Orders | ✅ | `PlannedOrder` model, can firm/release |

**UOM Conversion in MRP:** ⚠️ Uses inline `convert_uom()` with hardcoded `INLINE_UOM_CONVERSIONS`. This was causing bugs.

---

## PART 4: DASHBOARDS

### Morning Dashboard (Spec)

| Widget | Code Status | Notes |
|--------|-------------|-------|
| Ship Today | ❌ | No dedicated widget |
| Print Today | ❌ | No dedicated widget |
| Need to Order | ❌ | No dedicated widget |
| Printers | ⚠️ | Printer page exists, not dashboard |
| Quotes Pending | ❌ | No widget |

### Evening Dashboard (Spec)

| Widget | Code Status | Notes |
|--------|-------------|-------|
| Need to Order | ❌ | |
| Arriving Soon (POs) | ❌ | |
| Overnight Suggestions | ❌ | |
| Stock Levels | ❌ | |

**GAP:** `AdminDashboard.jsx` exists but is generic. NOT the action-focused dashboards in spec.

---

## PART 5: DATA INTEGRITY

### Spec Assertions vs Code

| Assertion | Enforced | How |
|-----------|----------|-----|
| SO line has valid product | ⚠️ | FK constraint only |
| WO has valid BOM | ❌ | Not enforced |
| Inventory >= 0 | ❌ | **CAN GO NEGATIVE** |
| qty_completed <= qty_ordered | ❌ | Not enforced |
| qty_shipped <= qty_ordered | ❌ | Not enforced |
| qty_received <= qty_ordered | ❌ | Not enforced |

**GAP:** No business rule enforcement. Database constraints only.

---

## PART 6: KNOWN BROKEN FLOWS

### 6.1 "Order Missing Material" Button

**Reported Issue:** Button on SO opens Purchasing page but doesn't carry shortage data.

**Root Cause (Likely):**
- `blocking_issues.py` returns shortages correctly
- Frontend gets data
- Navigation to Purchasing doesn't pass item_id, quantity as URL params or state
- Purchasing page doesn't read those params

**Fix Needed:**
1. Pass shortage data in navigation (URL params or React state)
2. Purchasing page reads and pre-fills PO form

### 6.2 UOM Conversion Bugs

**Reported Issue:** MRP calculations were massively wrong.

**Root Cause:**
- `INLINE_UOM_CONVERSIONS` in `uom_service.py` had wrong factors
- OR: Conversions not applied consistently (some places use DB, some use inline)

**Fix Needed:**
1. Single source of truth for UOM conversions (database)
2. Remove inline conversion dicts
3. Add unit tests for every conversion path

---

## PRIORITY FIX LIST

### P0 - Critical (Blocking Basic Use)

1. **UOM Conversion Consistency** - single source of truth
2. **Order Missing Material Flow** - button → PO creation working

### P1 - Important (Core Workflow Gaps)

3. **Morning Dashboard** - ship today, print today, shortages
4. **State Machine Enforcement** - can't ship cancelled order, etc.
5. **Negative Inventory Prevention** - check before deducting

### P2 - Polish (Nice to Have)

6. **Price Level on Customer** - retail vs wholesale
7. **Lead Time on Vendor** - not just Product
8. **Print Time on BOM** - for pricing formula
9. **Evening Dashboard** - planning widgets

---

## NEXT STEPS

1. **Write integration test for "Quote → SO → WO → Ship" flow**
   - This is the critical path test from spec
   - It will fail where things are broken

2. **Fix UOM conversions**
   - Audit every place `convert_uom` or `convert_quantity_safe` is called
   - Ensure they all use same lookup

3. **Fix Order Missing Material button**
   - Trace frontend click → navigation → PO form
   - Add URL params or global state for shortage data

4. **Build Morning Dashboard**
   - New component or refactor AdminDashboard
   - Queries: SOs due today, WOs due today, inventory below reorder

---

**END OF GAP ANALYSIS**
