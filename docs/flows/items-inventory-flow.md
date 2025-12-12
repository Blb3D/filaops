# Items & Inventory Module - User Flow Documentation

## Overview

The Items & Inventory module handles product/item management, inventory levels, locations, and inventory transactions (receipts, issues, adjustments, transfers). This document maps all user interactions and system behaviors.

---

## 1. Items/Products Management

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ITEMS MANAGEMENT                                     │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │    Items Tab    │
                    │  /admin/items   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌──────────┐   ┌──────────┐   ┌──────────┐
       │  Search  │   │+ New Item│   │  View    │
       │ & Filter │   │          │   │  Table   │
       └────┬─────┘   └────┬─────┘   └────┬─────┘
            │              │              │
            ▼              ▼              │
    ┌──────────────┐ ┌───────────────┐   │
    │ Filter by:   │ │ Item Modal    │   │
    │ • Search term│ │   Opens       │   │
    │ • Category   │ └───────┬───────┘   │
    │ • Item Type  │         │           │
    │ • Active     │         ▼           │
    └──────────────┘ ┌───────────────────┐
                     │  Enter Details    │
                     │  • SKU *          │
                     │  • Name *         │
                     │  • Item Type *    │
                     │  • Category       │
                     │  • Unit (ea/kg/m) │
                     │  • Reorder Point  │
                     │  • Standard Cost  │
                     │  • Preferred Vendor│
                     │  • Active ☑       │
                     └────────┬──────────┘
                              │
                              ▼
                     ┌───────────────────┐
                     │   [Save Item]     │
                     └────────┬──────────┘
                              │
                              ▼
                     ┌───────────────────┐
                     │  Item Created/    │
                     │  Updated          │
                     └───────────────────┘
```

### Item Types

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ITEM TYPES                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  RAW_MATERIAL    - Purchased materials (filament, resin, etc.)             │
│  COMPONENT       - Parts used in assembly                                   │
│  FINISHED_GOOD   - Sellable products                                        │
│  CONSUMABLE      - Items used but not tracked in BOMs                       │
│  MISC            - Other items                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Item Detail View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ITEM DETAIL VIEW                                     │
└─────────────────────────────────────────────────────────────────────────────┘

User clicks item row or "Edit"
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ITEM DETAIL MODAL                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ BASIC INFO                                                          │    │
│  │  SKU: MAT-PLA-BLK            Name: PLA Black Filament              │    │
│  │  Type: Raw Material          Category: Filament                    │    │
│  │  Unit: kg                    Active: ✓                             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ INVENTORY INFO                                                      │    │
│  │  On Hand: 5.25 kg            Available: 3.75 kg                    │    │
│  │  Allocated: 1.50 kg          Reorder Point: 5.00 kg                │    │
│  │  ⚠️ Below reorder point                                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ COSTING                                                             │    │
│  │  Standard Cost: $22.00       Average Cost: $21.50                  │    │
│  │  Last Cost: $23.00           Preferred Vendor: Polymaker           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  Actions:                                                                   │
│  [Edit] [View Transactions] [Adjust Inventory] [View BOM Usage]            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Current Gap: No "Adjust Inventory" quick action on Items page
```

---

## 3. Inventory Locations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INVENTORY LOCATIONS                                  │
└─────────────────────────────────────────────────────────────────────────────┘

Locations are used to track where inventory is stored:

  Default Location: "Main Warehouse" (ID: 1)

  Other possible locations:
  - Production Floor
  - Quality Hold
  - Shipping Staging
  - Receiving Dock

Location Management:
┌─────────────────────────────────────────────────────────────────────────────┐
│  GET /api/v1/admin/inventory/transactions/locations                         │
│                                                                             │
│  Returns list of inventory locations:                                       │
│  [                                                                          │
│    { "id": 1, "name": "Main Warehouse", "is_default": true },              │
│    { "id": 2, "name": "Production Floor", "is_default": false },           │
│    ...                                                                      │
│  ]                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Inventory Transactions Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INVENTORY TRANSACTIONS                                    │
└─────────────────────────────────────────────────────────────────────────────┘

Navigation: Admin > Inventory Transactions
Path: /admin/inventory/transactions

                    ┌─────────────────────────┐
                    │  Inventory Transactions │
                    │         Page            │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
       ┌──────────┐       ┌──────────┐       ┌──────────┐
       │  Filter  │       │+ New     │       │  View    │
       │Transactions│     │Transaction│      │  List    │
       └────┬─────┘       └────┬─────┘       └────┬─────┘
            │                  │                  │
            ▼                  ▼                  │
    ┌──────────────┐   ┌───────────────┐         │
    │ Filter by:   │   │Transaction    │         │
    │ • Product    │   │  Form Opens   │         │
    │ • Type       │   └───────┬───────┘         │
    │ • Location   │           │                 │
    └──────────────┘           ▼                 │
                     ┌─────────────────────────┐ │
                     │  Select Transaction     │ │
                     │  Type:                  │ │
                     │  • receipt              │ │
                     │  • issue                │ │
                     │  • transfer             │ │
                     │  • adjustment           │ │
                     │  • consumption          │ │
                     │  • scrap                │ │
                     └────────────┬────────────┘ │
                                  │              │
                                  ▼              │
                     ┌─────────────────────────┐ │
                     │  Enter Details:         │ │
                     │  • Product *            │ │
                     │  • Location             │ │
                     │  • Quantity *           │ │
                     │  • Cost per Unit        │ │
                     │  • Lot Number           │ │
                     │  • Serial Number        │ │
                     │  • Reference (PO/SO)    │ │
                     │  • Notes                │ │
                     │  • To Location (xfer)   │ │
                     └────────────┬────────────┘ │
                                  │              │
                                  ▼              │
                     ┌─────────────────────────┐ │
                     │  [Create Transaction]   │ │
                     └────────────┬────────────┘ │
                                  │              │
                                  ▼              │
                     ┌─────────────────────────┐ │
                     │  Transaction Created    │◄┘
                     │  Inventory Updated      │
                     └─────────────────────────┘
```

---

## 5. Transaction Types Explained

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRANSACTION TYPE BEHAVIORS                                │
└─────────────────────────────────────────────────────────────────────────────┘

  Type         │ Effect on Inventory          │ Common Use Cases
  ─────────────┼──────────────────────────────┼──────────────────────────────
  RECEIPT      │ ADDS to on_hand_quantity     │ • PO receiving
               │                              │ • Customer returns
               │                              │ • Found inventory
  ─────────────┼──────────────────────────────┼──────────────────────────────
  ISSUE        │ SUBTRACTS from on_hand       │ • Ship to customer
               │                              │ • Internal use
               │                              │ • Lost/stolen
  ─────────────┼──────────────────────────────┼──────────────────────────────
  TRANSFER     │ MOVES between locations      │ • Move to production floor
               │ (subtract from source,       │ • Move to shipping staging
               │  add to destination)         │ • Consolidate locations
  ─────────────┼──────────────────────────────┼──────────────────────────────
  ADJUSTMENT   │ SETS to absolute quantity    │ • Cycle count corrections
               │ (replaces current value)     │ • Physical inventory count
               │                              │ • Correct system errors
  ─────────────┼──────────────────────────────┼──────────────────────────────
  CONSUMPTION  │ SUBTRACTS from on_hand       │ • Production order usage
               │ (used by production)         │ • BOM component consumption
  ─────────────┼──────────────────────────────┼──────────────────────────────
  SCRAP        │ SUBTRACTS from on_hand       │ • Defective material
               │ (marks as waste)             │ • Expired material
               │                              │ • Quality rejects

Backend Logic (inventory_transactions.py):
┌─────────────────────────────────────────────────────────────────────────────┐
│  if request.transaction_type in ["receipt"]:                                │
│      inventory.on_hand_quantity += float(request.quantity)                  │
│                                                                             │
│  elif request.transaction_type in ["issue", "consumption", "scrap"]:        │
│      inventory.on_hand_quantity -= float(request.quantity)                  │
│                                                                             │
│  elif request.transaction_type == "adjustment":                             │
│      inventory.on_hand_quantity = float(request.quantity)  # SET, not delta │
│                                                                             │
│  elif request.transaction_type == "transfer":                               │
│      # Subtract from source location                                        │
│      source_inventory.on_hand_quantity -= float(request.quantity)           │
│      # Add to destination location                                          │
│      dest_inventory.on_hand_quantity += float(request.quantity)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Adjustment Flow (Cycle Count)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CYCLE COUNT / ADJUSTMENT FLOW                             │
└─────────────────────────────────────────────────────────────────────────────┘

Scenario: Physical count shows 4.5kg but system shows 5.0kg

Step 1: Go to Inventory Transactions
         │
         ▼
Step 2: Click "+ New Transaction"
         │
         ▼
Step 3: Fill form:
┌─────────────────────────────────────────────────────────────────────────────┐
│  Transaction Type: [Adjustment ▼]                                           │
│  Product:          [MAT-PLA-BLK - PLA Black Filament ▼]                    │
│  Location:         [Main Warehouse ▼]                                       │
│  Quantity:         [4.5] ← Enter the ACTUAL count, not the difference      │
│  Cost per Unit:    [22.00] (optional)                                       │
│  Reference Type:   [Adjustment ▼]                                           │
│  Notes:            [Cycle count 2025-01-15]                                 │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
Step 4: Click "Create Transaction"
         │
         ▼
Result: System inventory is now 4.5kg
        Transaction record shows: "adjustment" with qty 4.5
        Previous value was 5.0kg

IMPORTANT: Adjustment type SETS the quantity, not adds/subtracts!
```

---

## 7. Data Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA MODEL                                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│     PRODUCTS     │     │    INVENTORY     │     │   INVENTORY      │
│     (Items)      │────►│    (Levels)      │◄────│   TRANSACTIONS   │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ id               │     │ id               │     │ id               │
│ sku              │     │ product_id       │     │ product_id       │
│ name             │     │ location_id      │     │ location_id      │
│ item_type        │     │ on_hand_quantity │     │ transaction_type │
│ category_id      │     │ allocated_qty    │     │ quantity         │
│ unit             │     │ available_qty    │     │ cost_per_unit    │
│ reorder_point    │     │ last_count_date  │     │ reference_type   │
│ standard_cost    │     │ created_at       │     │ reference_id     │
│ average_cost     │     │ updated_at       │     │ lot_number       │
│ last_cost        │     └──────────────────┘     │ serial_number    │
│ preferred_vendor │                              │ notes            │
│ active           │     ┌──────────────────┐     │ created_at       │
└──────────────────┘     │ INVENTORY        │     │ created_by       │
                         │ LOCATIONS        │     └──────────────────┘
                         ├──────────────────┤
                         │ id               │
                         │ name             │
                         │ is_default       │
                         │ active           │
                         └──────────────────┘

Inventory Calculation:
┌─────────────────────────────────────────────────────────────────────────────┐
│  available_quantity = on_hand_quantity - allocated_quantity                 │
│                                                                             │
│  allocated_quantity is increased when:                                      │
│  - Sales order is created (reserves stock)                                  │
│  - Production order allocates components                                    │
│                                                                             │
│  allocated_quantity is decreased when:                                      │
│  - Order is shipped (issue transaction)                                     │
│  - Order is cancelled                                                       │
│  - Production is completed                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. API Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API ENDPOINTS                                        │
└─────────────────────────────────────────────────────────────────────────────┘

ITEMS:
  GET    /api/v1/items                    List items (with filters)
  GET    /api/v1/items/{id}               Get single item
  POST   /api/v1/items                    Create item
  PUT    /api/v1/items/{id}               Update item
  DELETE /api/v1/items/{id}               Delete/deactivate item
  GET    /api/v1/items/low-stock          Get items below reorder point

INVENTORY TRANSACTIONS:
  GET    /api/v1/admin/inventory/transactions           List transactions
  POST   /api/v1/admin/inventory/transactions           Create transaction
  GET    /api/v1/admin/inventory/transactions/locations List locations

ITEM CATEGORIES:
  GET    /api/v1/items/categories         List categories
  POST   /api/v1/items/categories         Create category

Transaction Create Request:
┌─────────────────────────────────────────────────────────────────────────────┐
│  POST /api/v1/admin/inventory/transactions                                  │
│  {                                                                          │
│    "product_id": 1,                    // Required                          │
│    "location_id": 1,                   // Optional (default: Main)          │
│    "transaction_type": "adjustment",   // Required                          │
│    "quantity": 4.5,                    // Required                          │
│    "cost_per_unit": 22.00,            // Optional                          │
│    "reference_type": "adjustment",     // Optional                          │
│    "reference_id": null,               // Optional                          │
│    "lot_number": "LOT-001",           // Optional                          │
│    "serial_number": null,              // Optional                          │
│    "notes": "Cycle count",            // Optional                          │
│    "to_location_id": null              // Required for transfer type        │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Current Gaps / Planned Improvements

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT GAPS                                              │
└─────────────────────────────────────────────────────────────────────────────┘

1. NO QUICK ADJUST ON ITEMS PAGE
   Current: Must navigate to separate Inventory Transactions page
   Desired: "Adjust" button on each item row → opens adjustment modal

2. NO INLINE INVENTORY EDIT
   Current: View-only inventory quantities on Items table
   Desired: Click to edit, or +/- buttons for quick adjustments

3. NO TRANSACTION HISTORY ON ITEM DETAIL
   Current: Must go to transactions page and filter
   Desired: "Recent Transactions" section on item detail modal

4. NO LOCATION MANAGEMENT UI
   Current: Locations managed via database only
   Desired: Admin page to add/edit/delete locations

5. NO BATCH ADJUSTMENT (CYCLE COUNT)
   Current: Adjust one item at a time
   Desired: Upload CSV or spreadsheet of counts, compare & adjust

6. LIMITED LOW STOCK ACTIONS
   Current: Shows items below reorder, "Create PO" button
   Desired: Pre-populate PO with suggested qty & vendor
```

---

## 10. Testing Checklist

### Items Management
- [ ] Can create new item with all fields
- [ ] Can edit existing item
- [ ] Can deactivate item
- [ ] Search filters work (SKU, name)
- [ ] Category filter works
- [ ] Item type filter works
- [ ] Active/inactive filter works
- [ ] Inventory levels display correctly

### Inventory Transactions
- [ ] **Product dropdown populates** ← PRIMARY FIX
- [ ] Location dropdown populates
- [ ] Can create RECEIPT transaction (qty increases)
- [ ] Can create ISSUE transaction (qty decreases)
- [ ] Can create ADJUSTMENT transaction (qty sets to value)
- [ ] Can create TRANSFER transaction (moves between locations)
- [ ] Transaction list displays correctly
- [ ] Filters work (product, type, location)
- [ ] Transaction history shows on refresh

### Low Stock
- [ ] Summary cards show correct counts
- [ ] Items below reorder point appear
- [ ] MRP shortages appear (if applicable)
- [ ] "Create PO" button works

---

## 11. Quick Reference: How to Adjust Inventory

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    QUICK REFERENCE                                           │
└─────────────────────────────────────────────────────────────────────────────┘

TO ADD INVENTORY (e.g., received shipment):
1. Go to Admin > Inventory Transactions
2. Click "+ New Transaction"
3. Type: Receipt
4. Select product, enter qty to ADD
5. Click Create

TO REMOVE INVENTORY (e.g., shipped order):
1. Go to Admin > Inventory Transactions
2. Click "+ New Transaction"
3. Type: Issue
4. Select product, enter qty to REMOVE
5. Click Create

TO CORRECT INVENTORY (e.g., cycle count):
1. Go to Admin > Inventory Transactions
2. Click "+ New Transaction"
3. Type: Adjustment
4. Select product, enter ACTUAL PHYSICAL COUNT
5. Click Create

TO MOVE INVENTORY (e.g., to production):
1. Go to Admin > Inventory Transactions
2. Click "+ New Transaction"
3. Type: Transfer
4. Select product, enter qty, select source & destination locations
5. Click Create
```
