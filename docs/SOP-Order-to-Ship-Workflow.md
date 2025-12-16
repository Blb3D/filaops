# FilaOps Order-to-Ship Workflow SOP

**Version:** 1.1
**Last Updated:** 2025-12-14
**Status:** In Testing

---

## Overview Flowchart

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FILAOPS ORDER-TO-SHIP WORKFLOW                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  QUOTE   │───>│  ORDER   │───>│PRODUCTION│───>│    QC    │───>│ SHIPPING │
│ CREATION │    │ CONFIRM  │    │          │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     v               v               v               v               v
  ┌──────┐       ┌──────┐       ┌──────┐       ┌──────┐       ┌──────┐
  │Quote │       │Sales │       │ Prod │       │Serial│       │Track │
  │Number│       │Order │       │Order │       │Number│       │Number│
  │Created│      │Created│      │Created│      │Assign│       │Assign│
  └──────┘       └──────┘       └──────┘       └──────┘       └──────┘
                     │               │
                     v               v
                 ┌──────┐       ┌──────┐
                 │Product│      │Consume│
                 │& BOM  │      │Material│
                 │Created│      │Add FG │
                 └──────┘       └──────┘

INVENTORY TRANSACTIONS:
- Production Complete: Consume raw materials, Add finished goods
- Shipping: Consume packaging, Issue finished goods
```

### MRP Cascade (Multi-Level Assemblies)

For products with sub-assemblies (e.g., Robot Arm Kit), the MRP cascade works as follows:

```text
Sales Order Confirmed (Robot Arm Kit)
    ↓
[AUTO] Production Order Created for Top-Level Assembly
    ↓
View "Required Orders" shows full cascade:
    ├── Work Orders Needed (make items with BOMs):
    │   ├── GEAR-SPUR-48 (qty: 2)
    │   ├── BRACKET-MOTOR-V2 (qty: 1)
    │   └── GRIPPER-CLAW-SET (qty: 1)
    │
    └── Purchase Orders Needed (buy items without BOMs):
        └── HW-SCREW-M3X8 (qty: 4)
    ↓
Create Sub-Assembly WOs → Each generates its own material requirements
    ↓
Create POs for raw materials (aggregated across all WOs)
    ↓
Receive POs → Materials available
    ↓
Release & Complete Sub-Assembly WOs
    ↓
Release & Complete Final Assembly WO
    ↓
Sales Order ready to ship
```

#### Key Concept: Make vs Buy

- **Make Items** (has BOM): Show "Create WO" button → generates Work Order
- **Buy Items** (no BOM): Show "Create PO" button → generates Purchase Order

---

## Phase 1: Quote Creation

### Prerequisites

- [ ] Materials configured in system (Items > Raw Materials)
- [ ] Colors configured in system (Items > Colors)
- [ ] Shipping boxes configured (Items > Packaging)
- [ ] Customer account exists (or will be created)

### Step 1.1: Navigate to Quotes

1. Log in as Admin at `/login`
2. Navigate to **Quotes** from sidebar menu
3. Click **"New Quote"** button

### Step 1.2: Enter Quote Details

| Field | Description | Example |
|-------|-------------|---------|
| Customer | Select existing or create new | "John Smith" |
| Product Name | Description of the print | "Custom Phone Stand" |
| Quantity | Number of units | 1 |
| Material Type | Select from configured materials | "PLA Basic" |
| Color | Select from configured colors | "Black" |
| Dimensions (X/Y/Z) | Part size in mm | 100 x 50 x 75 |
| Material Weight | Grams of filament | 45 |
| Print Time | Estimated hours | 2.5 |
| Unit Price | Price per unit | $25.00 |

### Step 1.3: Upload File (Optional)

- Upload 3MF or STL file
- System stores file reference for production

### Step 1.4: Save Quote

- Click **"Create Quote"**
- System generates quote number: `Q-YYYY-XXXX`
- Quote status: `pending`

### Expected Results

- [ ] Quote appears in Quotes list
- [ ] Quote number generated
- [ ] Status shows "Pending"

---

## Phase 2: Quote Acceptance & Order Creation

### Step 2.1: Accept Quote

1. From Quotes list, find the quote
2. Click **"Accept"** or open quote details
3. Click **"Convert to Order"**

### Step 2.2: System Auto-Creates

When quote is accepted, system automatically:

1. Creates **Product** record (SKU: `PRD-CUS-YYYY-XXX`)
2. Creates **BOM** with lines:
   - Material line (filament) - `consume_stage: production`
   - Packaging line (box) - `consume_stage: shipping`
   - Machine time (if configured) - `is_cost_only: true`
3. Creates **Sales Order** (SO: `SO-YYYY-XXXX`)

### Step 2.3: Verify Order Created

1. Navigate to **Order Management**
2. Find new order by order number
3. Verify status: `confirmed`

### Expected Results

- [ ] Sales Order created with correct details
- [ ] Product record exists
- [ ] BOM exists with material + packaging lines
- [ ] Quote status updated to "accepted"

---

## Phase 3: Production Order Generation

### Automatic WO Creation (v1.1+)

When a Sales Order status changes from `pending` to `confirmed`, the system **automatically** creates Production Orders for each line item.

### Step 3.1: Confirm Sales Order

1. From **Order Management**, find the sales order (status: `pending`)
2. Click **"Confirm"** or advance status to `confirmed`
3. System automatically:
   - Creates Production Order for each SO line
   - Updates SO status to `in_production`

### Step 3.2: Verify Production Order

1. Navigate to **Manufacturing > Production Orders**
2. Find the new production order (WO-YYYY-XXXX)
3. Verify details match sales order

### Step 3.3: View Required Orders (Multi-Level BOMs)

For products with sub-assemblies:

1. Open the Production Order details
2. View **"Required Orders"** section to see full MRP cascade
3. System shows:
   - **Work Orders Needed**: Sub-assemblies that must be manufactured first
   - **Purchase Orders Needed**: Raw materials to procure

### Production Order Fields

| Field | Auto-Populated From |
|-------|---------------------|
| Product | Sales Order product |
| Quantity | Sales Order quantity |
| Due Date | Based on lead time |
| Status | `planned` |
| Sales Order Link | Automatic |

### Expected Results

- [ ] Production Order auto-created on SO confirmation
- [ ] Work Order Number assigned (WO-YYYY-XXXX)
- [ ] Status: `planned`
- [ ] Linked to Sales Order
- [ ] SO status updated to `in_production`

---

## Phase 4: Production Execution

### Step 4.1: Start Production

1. From **Production Orders**, find the order
2. Click **"Start"** button
3. Status changes to `in_progress`
4. `actual_start` timestamp recorded

### Step 4.2: Complete Production

1. After printing is complete, click **"Complete"**
2. Enter quantity completed (defaults to ordered qty)
3. Enter quantity scrapped (if any)

### Step 4.3: Inventory Transactions (Automatic)

When production completes, system automatically:

**Consumes Raw Materials:**

- Reads BOM lines where `consume_stage = 'production'`
- Creates `consumption` transactions for each material
- Deducts from `inventory.on_hand_quantity`

**Receives Finished Goods:**

- Creates `receipt` transaction for finished product
- Adds to `inventory.on_hand_quantity`

### Step 4.4: Serial Number Generation (If Enabled)

- If product has `track_serials = true`
- System generates serial numbers: `BLB-YYYYMMDD-XXXX`
- Serial linked to production order

### Expected Results

- [ ] Production Order status: `complete`
- [ ] Inventory transactions created for material consumption
- [ ] Inventory transaction created for FG receipt
- [ ] Raw material inventory reduced
- [ ] Finished goods inventory increased
- [ ] Serial numbers generated (if applicable)

---

## Phase 5: Quality Control (Optional)

### Step 5.1: QC Check

1. Navigate to **Manufacturing > QC**
2. Find items pending QC
3. Perform inspection
4. Mark as **Pass** or **Fail**

### Step 5.2: QC Status Update

- Pass: Order moves to `qc_passed`
- Fail: Order marked `qc_failed`, requires rework

### Expected Results

- [ ] QC status recorded
- [ ] Serial number updated with QC result

---

## Phase 6: Shipping

### Step 6.1: Navigate to Shipping Dashboard

1. Go to **Shipping** from sidebar
2. View orders ready to ship (status: `ready_to_ship`, `qc_passed`)

### Step 6.2: Verify Shipping Address

1. Click on order to view details
2. Verify shipping address is complete
3. If missing, click **"Edit Address"** to add

### Step 6.3: Mark as Shipped

1. Click **"Mark Shipped"** button
2. Enter shipping details:
   - Carrier (USPS, UPS, FedEx)
   - Service (Priority, Ground, etc.)
   - Tracking Number (auto-generated if blank)

### Step 6.4: Inventory Transactions (Automatic)

When order ships, system automatically:

**Consumes Packaging Materials:**

- Reads BOM lines where `consume_stage = 'shipping'`
- Creates `consumption` transactions for packaging
- Deducts boxes from inventory

**Issues Finished Goods:**

- Creates `shipment` transaction
- Deducts finished goods from inventory

### Expected Results

- [ ] Order status: `shipped`
- [ ] Tracking number assigned
- [ ] `shipped_at` timestamp recorded
- [ ] Packaging inventory reduced
- [ ] Finished goods inventory reduced
- [ ] Order removed from Shipping dashboard

---

## Verification: Inventory Transactions

### How to Verify Inventory Changes

1. Navigate to **Inventory > Transactions**
2. Filter by reference_type: `production_order` or `sales_order`
3. Filter by reference_id: the specific order ID

### Expected Transaction Types

| When | Transaction Type | Reference Type | Qty Effect |
|------|------------------|----------------|------------|
| Production Complete | `consumption` | production_order | Decrease raw materials |
| Production Complete | `receipt` | production_order | Increase finished goods |
| Ship Order | `consumption` | sales_order | Decrease packaging |
| Ship Order | `shipment` | sales_order | Decrease finished goods |

---

## Troubleshooting

### Quote Won't Convert to Order

- **Check:** Material/Color combination exists
- **Check:** Suitable shipping box exists for dimensions
- **Check:** Quote has all required fields (dimensions, material_grams)

### Production Won't Complete

- **Check:** Order status is `in_progress`
- **Check:** BOM exists for product

### Shipping Button Does Nothing

- **Check:** Order has shipping address
- **Check:** Order status allows shipping
- **Check:** Browser console for errors

### Inventory Not Updating

- **Check:** `inventory_transactions` table for new records
- **Check:** BOM has correct `consume_stage` values
- **Check:** Backend logs for errors

---

## Testing Checklist

### Phase 1: Quote Creation

- [ ] Step 1.1: Navigate to Quotes - **Status:** ___
- [ ] Step 1.2: Enter Quote Details - **Status:** ___
- [ ] Step 1.3: Upload File - **Status:** ___
- [ ] Step 1.4: Save Quote - **Status:** ___

### Phase 2: Order Creation

- [ ] Step 2.1: Accept Quote - **Status:** ___
- [ ] Step 2.2: Verify Auto-Created Items - **Status:** ___
- [ ] Step 2.3: Verify Order - **Status:** ___

### Phase 3: Production Order

- [ ] Step 3.1: Generate Production Order - **Status:** ___
- [ ] Step 3.2: Verify Production Order - **Status:** ___

### Phase 4: Production Execution

- [ ] Step 4.1: Start Production - **Status:** ___
- [ ] Step 4.2: Complete Production - **Status:** ___
- [ ] Step 4.3: Verify Inventory Transactions - **Status:** ___

### Phase 5: QC

- [ ] Step 5.1: QC Check - **Status:** ___

### Phase 6: Shipping

- [ ] Step 6.1: Navigate to Shipping - **Status:** ___
- [ ] Step 6.2: Verify Address - **Status:** ___
- [ ] Step 6.3: Mark Shipped - **Status:** ___
- [ ] Step 6.4: Verify Inventory Transactions - **Status:** ___

---

## Notes & Issues Log

| Date | Phase | Issue | Resolution |
|------|-------|-------|------------|
| | | | |
