# FilaOps ERP - Functional Specification
## Purpose-Built for 3D Print Farm Operations

**Version:** 0.2 (Based on operator interview)
**Last Updated:** 2025-12-29
**Status:** 🔄 Core workflows mapped

---

## Document Purpose

This is THE source of truth for what FilaOps does. Every feature, button, and calculation should trace back to this document.

**Rules:**
1. If it's not documented here, it doesn't exist
2. Code implements this spec, not the other way around
3. Tests validate this spec

---

## Design Philosophy

**The operator works 20 hrs/day, 7 days/week. This system exists to reduce that.**

```
AUTOMATE: Web orders, MRP calculations, low stock alerts
SIMPLIFY: Morning dashboard, one-click actions, fast decisions
REMEMBER: So the operator doesn't have to hold it all in their head
```

**What FilaOps IS:**
- Operations management (quotes, orders, production, inventory, shipping)
- Decision support (what to make, what to buy, what's blocking)

**What FilaOps IS NOT:**
- Accounting system (QuickBooks does that)
- Full MES/shop floor control (overkill for small print farm)
- Printer firmware (Bambu handles that)

---

## Operator Profile

```
Solo print farm owner
├── Multiple sales channels (web, wholesale, POS, custom quotes)
├── 6+ printers running daily
├── MTO (make-to-order) + MTS (make-to-stock) hybrid
├── One-person: sales, production, QC, shipping, IT
└── Needs: Less mental load, fewer surprises, faster decisions
```

---

# PART 1: CORE ENTITIES (Master Data)

## 1.1 Items (Products & Materials)

### Item Types (Simple)
| Type | Description | Example | Has BOM | Purchased | Produced | Sold |
|------|-------------|---------|---------|-----------|----------|------|
| raw_material | Stuff you buy to make things | Filament, screws, LEDs | No | ✅ | - | - |
| finished_good | Stuff you sell | Widget Pro, Custom Lamp | Yes | - | ✅ | ✅ |
| packaging | Boxes, labels, bags | Box-Small, Poly Mailer | No | ✅ | - | - |

### Standard Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| sku | string | yes | Your unique code (PLA-BLK-1KG, WIDGET-PRO) |
| name | string | yes | Display name |
| item_type | enum | yes | raw_material, finished_good, packaging |
| standard_cost | decimal | yes | Your cost basis for pricing |
| active | bool | yes | Still in use? |

### Replenishment Fields
| Field | Type | Description |
|-------|------|-------------|
| replenishment_type | enum | reorder_point, order_driven |
| reorder_point | decimal | Alert when on_hand drops below this |
| reorder_qty | decimal | Suggested order quantity |

**Staples (reorder_point):** PLA-WHITE, PLA-BLACK, common hardware
**Specialty (order_driven):** TPU, silk filaments, one-off components

### UOM Configuration (The Special Sauce)
| Field | Type | Description |
|-------|------|-------------|
| base_uom | string | Internal tracking unit (grams for filament, ea for hardware) |
| purchase_uom | string | How vendors sell it (spool, box, bag) |
| purchase_conversion | decimal | 1 purchase_uom = X base_uom |

**Example:**
```
Item: PLA-BLACK
├── base_uom: grams (what slicer reports, what BOM uses)
├── purchase_uom: spool
├── purchase_conversion: 1000 (1 spool = 1000g)
├── standard_cost: $0.02/gram
├── replenishment_type: reorder_point
├── reorder_point: 2000 (grams = 2 spools)
└── reorder_qty: 5000 (grams = 5 spools)

When you buy: "5 spools" → system adds 5000g to inventory
When BOM says: "47g" → system knows what that means
When low: Alert at 2000g, suggest order 5000g
```

### Filament-Specific Fields (Optional)
| Field | Type | Description |
|-------|------|-------------|
| material_type | enum | PLA, PETG, ABS, TPU, ASA, etc. |
| color | string | Black, White, Silk Gold |
| manufacturer | string | Bambu, PolyMaker, Sunlu |

*Nice for filtering/reporting, not required for core function.*

---

## 1.2 Bill of Materials (BOM)

A recipe. "To make 1 Widget, you need these things."

### BOM Structure
```
BOM: LAMP-DESK-01
├── Parent: LAMP-DESK-01 (what we're making)
├── Makes: 1 ea
│
└── Components:
    ├── Line 1: PLA-BLACK, 235g, $0.02/g = $4.70
    ├── Line 2: LED-PUCK, 1 ea, $4.50 = $4.50
    ├── Line 3: POWER-CORD, 1 ea, $2.00 = $2.00
    ├── Line 4: HARDWARE-KIT, 1 ea, $0.50 = $0.50
    ├── Line 5: BOX-LAMP, 1 ea, $1.20 = $1.20
    │
    ├── Material Cost: $12.90
    ├── Runtime: 6 hours × $1.50/hr = $9.00
    │
    ├── TOTAL COST: $21.90
    ├── Retail (×3.5): $76.65 → $75.99
    └── B2B 10+ (×2.5): $54.75 → $52.99
```

### BOM Fields
| Field | Type | Description |
|-------|------|-------------|
| product_id | FK→Item | The finished good |
| component_id | FK→Item | What goes into it |
| quantity_per | decimal | How many/much per unit (in component's base_uom) |
| scrap_pct | decimal | Expected waste (default 0%) |

### Print-Specific Fields
| Field | Type | Description |
|-------|------|-------------|
| print_time_minutes | int | From slicer |
| gcode_file | string | Path to sliced file (optional) |

### Pricing Formula (Brandan's Method)
```python
def calculate_price(bom, markup_multiplier=3.5):
    """
    markup_multiplier: 3.5 for retail, 2.5 for B2B 10+
    """
    material_cost = sum(line.qty * line.component.standard_cost for line in bom.lines)
    runtime_cost = bom.print_time_minutes / 60 * 1.50  # $1.50/hr
    total_cost = material_cost + runtime_cost
    price = total_cost * markup_multiplier
    return round_to_99(price)  # $76.65 → $75.99
```

---

## 1.3 Customers

Keep it simple.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| code | string | yes | Short identifier |
| name | string | yes | Display name |
| email | string | yes | For quotes/invoices |
| phone | string | no | |
| address | text | no | Shipping address |
| price_level | enum | yes | retail (×3.5), wholesale (×2.5) |
| notes | text | no | "Prefers USPS", "Net 30 approved" |

**Sources:**
- Manual entry (custom quotes, phone orders)
- Auto-created from web orders (Shopify, Etsy, etc.)

---

## 1.4 Vendors (Suppliers)

Who you buy from.

| Field | Type | Notes |
|-------|------|-------|
| code | string | BAMBU, AMAZON, ULINE, MCMASTER |
| name | string | Full name |
| lead_time_days | int | Default for planning (Bambu=5, Amazon=2) |
| notes | text | Account numbers, contacts |

---

## 1.5 Units of Measure (UOM)

Keep the list small.

| Code | Name | Class | Used For |
|------|------|-------|----------|
| ea | Each | quantity | Hardware, components, finished goods |
| g | Grams | weight | Filament (base unit) |
| kg | Kilograms | weight | Bulk filament |
| spool | Spool | quantity | Filament purchasing |
| m | Meters | length | Some specialty materials |

### Conversions (System-Defined)
| From | To | Factor |
|------|-----|--------|
| kg | g | 1000 |
| spool | g | (per item, typically 1000) |

---

## 1.6 Inventory Locations

Simple for a home/small print farm.

| Code | Name | Purpose |
|------|------|---------|
| MAIN | Main Storage | Raw materials, finished stock |
| WIP | Work in Progress | Staging area (optional tracking) |
| SHIP | Ready to Ship | Packed and labeled (optional) |

*Many small operations just use MAIN for everything. That's fine.*

---

## 1.7 Printers (Future Enhancement)

Not required for core function, but useful for:
- Knowing which printer ran which job
- Status dashboard
- Capacity planning

| Field | Type | Notes |
|-------|------|-------|
| code | string | P1S-01, A1-MINI-02 |
| model | enum | P1S, P1P, X1C, A1, A1-Mini |
| status | enum | idle, printing, error, offline |
| current_job | FK→WO | What's running |

*Bambu Handy already does this. FilaOps integration = nice to have, not essential.*

---

# PART 2: CORE WORKFLOWS

## 2.1 The Big Picture

```
HOW WORK FLOWS THROUGH THE SYSTEM
─────────────────────────────────

DEMAND COMES IN                    SUPPLY GOES OUT
(why are we making stuff?)         (how do we fulfill it?)

┌─────────────┐                    
│ Custom      │──→ Quote ──→┐      
│ Request     │             │      
└─────────────┘             │      
                            ▼      
┌─────────────┐      ┌────────────┐      ┌────────────┐      ┌─────────┐
│ Web Order   │──→──→│   SALES    │──→──→│ PRODUCTION │──→──→│  SHIP   │
│ (auto)      │      │   ORDER    │      │   ORDER    │      │         │
└─────────────┘      └────────────┘      └────────────┘      └─────────┘
                            │                   │
┌─────────────┐             │                   │
│ Phone/POS   │──→──→───────┘                   │
│ (manual)    │                                 │
└─────────────┘                                 │
                                                ▼
┌─────────────┐                          ┌────────────┐
│ Low Stock   │──→──→──→──→──→──→──→──→──│ PRODUCTION │ (restock run)
│ Alert       │                          │   ORDER    │
└─────────────┘                          └────────────┘
                                                │
                                                ▼
                                         ┌────────────┐
                                         │    MRP     │
                                         │ "What do   │
                                         │  I need?"  │
                                         └────────────┘
                                                │
                                    ┌───────────┴───────────┐
                                    ▼                       ▼
                             ┌────────────┐          ┌────────────┐
                             │  PURCHASE  │          │  HAVE IT   │
                             │   ORDER    │          │  (proceed) │
                             └────────────┘          └────────────┘
                                    │
                                    ▼
                             ┌────────────┐
                             │  RECEIVE   │──→ Inventory
                             └────────────┘
```

---

## 2.2 Quote (Custom Work)

**When:** Customer asks "can you make this?"

**States:**
| Status | Meaning | Actions Available |
|--------|---------|-------------------|
| draft | You're working on it | Edit, Send, Delete |
| sent | Customer has it | Convert to SO, Expire, Cancel |
| converted | Became an order | (done) |
| expired | Too old | (done) |
| cancelled | They said no | (done) |

**Quote Document:**
```
Quote Q-2025-0042
├── Customer: Jane's Craft Shop
├── Created: 2025-01-10
├── Valid Until: 2025-01-24
├── Status: sent
│
├── Lines:
│   ├── CUSTOM-BRACKET-001 × 50 @ $4.99 = $249.50
│   └── (includes: 23g PLA, 45min print, ×3.5 markup)
│
├── Notes: "Customer provided STL, wants matte black"
└── Total: $249.50
```

**Key Action: Convert to Sales Order**
```
WHEN: Customer says "yes, let's do it"

1. Create Sales Order from quote
   - Copy customer
   - Copy lines
   - Link SO back to quote
2. Update quote.status = 'converted'
3. Navigate to new SO
```

---

## 2.3 Sales Order (Commitment to Deliver)

**When:** Customer wants something and you've agreed to make/ship it

**Sources:**
- Converted quote (custom)
- Web order import (Shopify, Etsy, etc.)
- Manual entry (phone, wholesale, POS)

**States:**
| Status | Meaning | Actions Available |
|--------|---------|-------------------|
| draft | Entering order | Edit, Confirm, Cancel |
| confirmed | Ready to produce | Create WO, Cancel (if no WO) |
| in_production | Being made | View progress |
| ready | Complete, ready to ship | Ship |
| shipped | Out the door | (done - goes to QB as invoice) |
| cancelled | Cancelled | (done) |

**Sales Order Document:**
```
Sales Order SO-2025-0089
├── Customer: Acme Corp
├── Order Date: 2025-01-15
├── Ship By: 2025-01-22
├── Source: Q-2025-0042 (or "Shopify #1234", or "Manual")
├── Status: in_production
│
├── Lines:
│   ├── Line 1: WIDGET-PRO × 10 @ $12.99 = $129.90
│   │   ├── Qty Ready: 6
│   │   └── Production: WO-0112 (60% complete)
│   │
│   └── Line 2: GADGET-MINI × 5 @ $6.99 = $34.95
│       ├── Qty Ready: 5 ✓
│       └── Production: WO-0113 (complete)
│
├── Subtotal: $164.85
├── Shipping: $8.50
└── Total: $173.35

BLOCKING ISSUES:
├── WO-0112 needs 47g PLA-RED (out of stock)
└── [Order Missing Material] button
```

**Key Actions:**

**Confirm Order:**
```
WHEN: Order is complete and you're committing to it

1. Validate has lines
2. Set status = 'confirmed'
3. Trigger MRP check (do we have material?)
```

**Create Production Order:**
```
WHEN: Confirmed order has items that need to be made

For each line:
1. Check if product has BOM (if not, skip or error)
2. Create Production Order:
   - Product = line.product
   - Quantity = line.qty
   - Due date = SO.ship_by
   - Link back to SO line
3. Set SO status = 'in_production'
```

**Order Missing Material:**
```
WHEN: Blocking issues show material shortages

1. Gather all material shortages across linked WOs
2. Open Purchase Order dialog pre-filled:
   - Suggested vendor (from item.preferred_vendor)
   - Items and quantities needed
3. On submit: Create PO, link to demand
4. Blocking issues now show "Incoming: PO-xxxx, ETA: date"
```

**Ship Order:**
```
WHEN: All lines ready (or partial ship)

1. Create Shipment record
2. Deduct inventory
3. Set SO status = 'shipped'
4. (Future: create QB invoice, notify customer)
```

---

## 2.4 Production Order (Work Order)

**When:** You need to make something

**Sources:**
- Created from Sales Order (MTO)
- Created manually for restocking (MTS)
- Suggested by MRP/low stock alert

**States:**
| Status | Meaning | Actions Available |
|--------|---------|-------------------|
| draft | Planning | Edit, Release, Cancel |
| released | Ready to print | Start, Cancel |
| in_progress | On the printer | Record completion, Scrap |
| complete | Done printing | (done) |
| cancelled | Cancelled | (done) |

**Production Order Document:**
```
Production Order WO-2025-0112
├── Product: WIDGET-PRO
├── Quantity: 10
├── Due Date: 2025-01-22
├── Status: in_progress
│
├── Demand Source:
│   ├── Sales Order: SO-2025-0089, Line 1
│   └── Customer: Acme Corp
│
├── Progress:
│   ├── Completed: 6
│   ├── Scrapped: 1
│   └── Remaining: 3
│
├── Material Requirements:
│   ├── PLA-BLACK: 470g needed (47g × 10)
│   │   ├── Available: 2,500g
│   │   └── Status: ✓ OK
│   ├── SPRING-CLIP: 20 ea needed (2 × 10)
│   │   ├── Available: 45 ea
│   │   └── Status: ✓ OK
│
└── Print Time: 4.5 hrs total (27 min × 10)
```

**Key Actions:**

**Release:**
```
WHEN: WO is planned and materials are checked

1. Set status = 'released'
2. Materials are now "allocated" (reserved for this job)
```

**Record Completion:**
```
WHEN: Prints come off the printer

INPUT: quantity_good, quantity_scrapped

1. Update WO.qty_completed += quantity_good
2. Update WO.qty_scrapped += quantity_scrapped
3. Add finished goods to inventory
4. If qty_completed >= qty_ordered: status = 'complete'
5. Update linked SO line qty_ready
```

**Scrap:**
```
WHEN: Print fails, bad quality, etc.

INPUT: quantity, reason

1. Update WO.qty_scrapped += quantity
2. (Material was consumed but no output)
3. Log reason for review
```

---

## 2.5 Purchase Order

**When:** You need to buy materials

**Sources:**
- Manual ("I need to order filament")
- From "Order Missing Material" button on SO
- From MRP suggestion
- From low stock alert

**States:**
| Status | Meaning | Actions Available |
|--------|---------|-------------------|
| draft | Entering order | Edit, Send, Cancel |
| sent | Ordered from vendor | Receive, Cancel |
| partial | Some received | Receive more, Close |
| received | All received | (done) |
| cancelled | Cancelled | (done) |

**Purchase Order Document:**
```
Purchase Order PO-2025-0034
├── Vendor: Bambu Lab
├── Order Date: 2025-01-15
├── Expected: 2025-01-20
├── Status: sent
│
├── Lines:
│   ├── PLA-BLACK × 5 spools @ $19.99 = $99.95
│   │   └── Qty Received: 0
│   └── PLA-WHITE × 3 spools @ $19.99 = $59.97
│       └── Qty Received: 0
│
└── Total: $159.92

LINKED DEMAND:
├── WO-0112 (needs PLA-BLACK for SO-0089)
└── Low stock replenishment
```

**Key Action: Receive**
```
WHEN: Package arrives

For each line:
1. Enter qty received
2. Convert to base UOM: 5 spools × 1000g = 5000g
3. Add to inventory (location: MAIN)
4. Update PO line qty_received

If all lines fully received:
5. Set PO status = 'received'
6. (Future: create QB bill)
```

---

## 2.6 Inventory Transactions

Every time inventory changes, record it.

### Transaction Types
| Type | Direction | Trigger | Example |
|------|-----------|---------|---------|
| receive | + | PO received | +5000g PLA-BLACK |
| issue | - | WO material used | -470g PLA-BLACK |
| complete | + | WO finished | +10 ea WIDGET-PRO |
| ship | - | Order shipped | -10 ea WIDGET-PRO |
| adjust | +/- | Physical count | +50g (found extra) |
| scrap | - | Waste/damage | -47g (failed print) |

### Running Balance Example
```
Item: PLA-BLACK
Location: MAIN

Date     | Type     | Reference  | Qty     | Balance
---------|----------|------------|---------|--------
01/01    | -        | Opening    | -       | 3,000g
01/10    | issue    | WO-0098    | -235g   | 2,765g
01/12    | issue    | WO-0101    | -470g   | 2,295g
01/15    | receive  | PO-0034    | +5,000g | 7,295g
01/16    | issue    | WO-0112    | -282g   | 7,013g
```

---

## 2.7 Shipment

**When:** Order is ready to go out the door

**Shipment Document:**
```
Shipment SH-2025-0067
├── Sales Order: SO-2025-0089
├── Customer: Acme Corp
├── Ship Date: 2025-01-22
├── Carrier: USPS
├── Tracking: 9400111899223456789012
│
├── Items Shipped:
│   ├── WIDGET-PRO × 10
│   └── GADGET-MINI × 5
│
└── Status: shipped
```

**On Ship:**
1. Deduct inventory for each line
2. Update SO status
3. Record tracking number
4. (Future: notify customer, sync to Pirateship)

---

## 2.8 Returns (Edge Case)

Happens rarely, but need to handle.

**Process:**
1. Create Return record linked to original SO/Shipment
2. Receive items back
3. Inspect: restock or scrap?
4. Adjust inventory accordingly
5. (Refund handled in QuickBooks)

---

# PART 3: MRP (The Brain)

MRP answers: **"What do I need, and when?"**

## 3.1 How It Works

```
DEMAND                              SUPPLY
(what I need to make/ship)          (what I have or is coming)
───────────────────────────         ───────────────────────────
Sales Order lines (confirmed)       On-hand inventory
+ Restock needs (below reorder)     + Open PO lines (not received)
+ Safety stock                      + Open WO completions
= GROSS REQUIREMENT                 = AVAILABLE SUPPLY

GROSS - AVAILABLE = NET REQUIREMENT

If NET > 0 → You need to buy or make something
```

## 3.2 Simple MRP Check (Per Item)

```python
def check_item_availability(item_id):
    """
    The core calculation used everywhere
    """
    # What do I have?
    on_hand = get_inventory_qty(item_id)
    
    # What's coming in?
    incoming_po = sum(po_line.qty_open for po_line in open_po_lines(item_id))
    incoming_wo = sum(wo.qty_remaining for wo in open_wos_producing(item_id))
    
    # What's promised out?
    allocated_to_wos = sum(
        wo.qty_ordered * bom_line.qty_per
        for wo in open_wos
        for bom_line in wo.product.bom
        if bom_line.component_id == item_id
    )
    
    # What's the situation?
    available = on_hand - allocated_to_wos
    net_position = available + incoming_po + incoming_wo
    
    return {
        'on_hand': on_hand,
        'allocated': allocated_to_wos,
        'available': available,
        'incoming': incoming_po + incoming_wo,
        'net_position': net_position,
        'is_short': available < 0
    }
```

## 3.3 MRP Suggestions

**When you confirm a Sales Order:**
```
For each line:
  1. Can we ship from stock? 
     - If yes: reserve inventory, done
     - If no: need to produce
  
  2. To produce, check materials:
     - For each BOM component:
       - Is there enough available?
       - If no: suggest PO
       
  3. Show user:
     - "Ready to go" (have everything)
     - "Need to order: X, Y, Z" (shortages)
     - "Waiting for: PO-123" (already ordered)
```

## 3.4 Reorder Point Alerts

**Nightly (or on-demand):**
```
For each item where replenishment_type = 'reorder_point':
  if on_hand < reorder_point:
    create_alert(
      item=item,
      on_hand=on_hand,
      reorder_point=reorder_point,
      suggested_qty=reorder_qty,
      severity='critical' if on_hand < (reorder_point / 2) else 'warning'
    )
```

---

# PART 4: DASHBOARDS

## 4.1 Morning Dashboard

**Purpose:** What do I need to DO today?

```
┌─────────────────────────────────────────────────────────┐
│ 📦 SHIP TODAY                                  3 orders │
├─────────────────────────────────────────────────────────┤
│ SO-0089 │ Acme Corp   │ 2 items │ ✅ READY     │ [Ship] │
│ SO-0091 │ Jane Doe    │ 1 item  │ ✅ READY     │ [Ship] │
│ SO-0092 │ Bob's Shop  │ 3 items │ ⚠️ 2 of 3   │ [View] │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 🖨️ PRINT TODAY                                  5 jobs │
├─────────────────────────────────────────────────────────┤
│ WO-0112 │ Widget Pro ×10 │ Due Today │ ✅ Mat Ready    │
│ WO-0113 │ Gadget ×5      │ Due Today │ ✅ Mat Ready    │
│ WO-0114 │ Custom ×1      │ Due Today │ ⚠️ Need PLA-RED │
│ WO-0115 │ Lamp ×2        │ Due Tmrw  │ ✅ Mat Ready    │
│ WO-0116 │ Stand ×20      │ Due Tmrw  │ ✅ Mat Ready    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 🛒 NEED TO ORDER                               2 items │
├─────────────────────────────────────────────────────────┤
│ PLA-RED      │ Have: 200g │ Need: 450g │ Short: 250g  │
│ SPRING-CLIP  │ Have: 12   │ Need: 40   │ Short: 28    │
│                                                         │
│ [Create PO for All Shortages]                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 🖨️ PRINTERS                                            │
├─────────────────────────────────────────────────────────┤
│ P1S-01: 🟢 Idle        │ P1S-02: 🔵 Printing 67%       │
│ A1-01:  🟢 Idle        │ A1-02:  🟢 Idle               │
│ A1-03:  🔴 Error       │ A1-04:  🟢 Idle               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 💬 QUOTES PENDING RESPONSE                    2 quotes │
├─────────────────────────────────────────────────────────┤
│ Q-0156 │ Jane's Crafts │ Custom bracket │ Sent 3d ago │
│ Q-0158 │ Wholesale Co  │ 50× widgets    │ Sent 1d ago │
└─────────────────────────────────────────────────────────┘
```

## 4.2 Evening Dashboard

**Purpose:** What do I need to PLAN?

```
┌─────────────────────────────────────────────────────────┐
│ 🛒 NEED TO ORDER                               4 items │
├─────────────────────────────────────────────────────────┤
│ PLA-WHITE  │ 800g   │ Min: 2kg  │ 🔴 CRITICAL         │
│ PLA-BLACK  │ 1.5kg  │ Min: 2kg  │ 🟡 LOW              │
│ LED-PUCK   │ 4 ea   │ Min: 10   │ 🟡 LOW              │
│ BOX-SMALL  │ 18 ea  │ Min: 25   │ 🟡 LOW              │
│                                                         │
│ [Create PO - Bambu Lab]  [Create PO - Amazon]          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 📬 ARRIVING SOON                               2 POs   │
├─────────────────────────────────────────────────────────┤
│ PO-0034 │ Bambu Lab │ 5× PLA spools   │ ETA: Tomorrow │
│ PO-0036 │ Amazon    │ LED pucks, wire │ ETA: Friday   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 🌙 OVERNIGHT SUGGESTIONS                      3 jobs   │
├─────────────────────────────────────────────────────────┤
│ These items are below reorder point and material ready │
├─────────────────────────────────────────────────────────┤
│ ☐ WIDGET-PRO ×10    │ 8hr print │ PLA-BLK ✅          │
│ ☐ PHONE-STAND ×15   │ 6hr print │ PLA-BLK ✅          │
│ ☐ GADGET-MINI ×20   │ 4hr print │ PLA-WHT ⚠️ low     │
│                                                         │
│ [Create WO for Selected]                               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 📉 STOCK LEVELS                                        │
├─────────────────────────────────────────────────────────┤
│ Finished Goods Below Reorder:                          │
│ • WIDGET-PRO: 3 ea (min: 10)                          │
│ • PHONE-STAND: 5 ea (min: 15)                         │
│ • GADGET-MINI: 8 ea (min: 20)                         │
└─────────────────────────────────────────────────────────┘
```

---

# PART 5: INTEGRATIONS (Future)

## 5.1 Priority Order

| Integration | Value | Effort | When |
|-------------|-------|--------|------|
| Web order import (Shopify/Etsy) | HIGH | Medium | After core stable |
| QuickBooks export | HIGH | Medium | After core stable |
| Pirateship sync | MEDIUM | Low | Nice to have |
| Bambu printer status | LOW | High | Much later |

## 5.2 QuickBooks Integration

**What to sync:**
- Shipped orders → QB Invoices
- Received POs → QB Bills
- Customers → QB Customers
- Vendors → QB Vendors

**What NOT to sync:**
- Inventory (let QB do its own thing or sync periodically)
- Anything in draft status

## 5.3 Web Order Import

**Shopify/Etsy/TikTok flow:**
```
1. Order placed on platform (payment collected there)
2. FilaOps polls or receives webhook
3. Create Customer (if new)
4. Create Sales Order (status: confirmed)
5. Trigger normal fulfillment flow
6. On ship: send tracking back to platform
```

---

# PART 6: DATA INTEGRITY RULES

## 6.1 What Must Always Be True

These are assertions. If any is false, something is broken.

```python
# Every SO line has a valid product
assert all(line.product_id is not None for so in sales_orders for line in so.lines)

# Every WO has a valid BOM
assert all(wo.product.bom is not None for wo in production_orders)

# Inventory can never be negative
assert all(inv.qty >= 0 for inv in inventory_records)

# Completed WO qty_completed <= qty_ordered (can't make more than asked)
assert all(wo.qty_completed <= wo.qty_ordered for wo in production_orders)

# Shipped qty can't exceed ordered qty
assert all(line.qty_shipped <= line.qty_ordered for so in sales_orders for line in so.lines)

# PO received can't exceed ordered
assert all(line.qty_received <= line.qty_ordered for po in purchase_orders for line in po.lines)
```

## 6.2 State Machine Rules

```
Quote: draft → sent → [converted | expired | cancelled]
             ↓
       (no going back from converted/expired/cancelled)

Sales Order: draft → confirmed → in_production → ready → shipped
                  ↓
             cancelled (only from draft/confirmed)

Production Order: draft → released → in_progress → complete
                       ↓
                  cancelled (only from draft/released)

Purchase Order: draft → sent → [partial →] received
                     ↓
                cancelled (only before receiving)
```

## 6.3 Referential Integrity

```
Delete Rules:
- Can't delete Customer with open SOs
- Can't delete Item with inventory > 0
- Can't delete Item used in open orders
- Can't delete Vendor with open POs

Cascade Rules:
- Archive Item → archives BOMs using it (soft delete)
- Cancel SO → releases any material allocations
```

---

# PART 7: TESTING REQUIREMENTS

## 7.1 Critical Path Tests

Before ANY release, these must pass:

```python
def test_quote_to_shipment_flow():
    """The happy path works end-to-end"""
    # Create quote
    quote = create_quote(customer, lines=[{product: widget, qty: 10}])
    # Convert to SO
    so = convert_quote(quote.id)
    assert so.status == 'confirmed'
    # Create production
    wo = create_production_order(so.lines[0])
    # Complete production
    complete_wo(wo.id, qty=10)
    # Ship
    shipment = ship_order(so.id)
    # Verify inventory changed
    assert get_inventory(widget.id) >= 0  # didn't go negative

def test_material_shortage_detected():
    """System warns when we can't make something"""
    product = create_product_with_bom(needs=[{item: pla, qty: 100}])
    set_inventory(pla, qty=50)  # not enough
    so = create_so(product, qty=1)
    blocking = get_blocking_issues(so.id)
    assert blocking['can_fulfill'] == False
    assert 'pla' in str(blocking['issues']).lower()

def test_po_receipt_adds_inventory_correctly():
    """UOM conversion works on receipt"""
    item = create_item(base_uom='g', purchase_uom='spool', conversion=1000)
    set_inventory(item, qty=0)
    po = create_po(item, qty=5)  # 5 spools
    receive_po(po.id, qty=5)
    assert get_inventory(item.id) == 5000  # grams

def test_reorder_alerts_fire():
    """Low stock creates alerts"""
    item = create_item(reorder_point=100, reorder_qty=500)
    set_inventory(item, qty=50)  # below reorder point
    alerts = run_reorder_check()
    assert any(a.item_id == item.id for a in alerts)
```

## 7.2 Integration Tests by Workflow

| Workflow | Key Tests |
|----------|-----------|
| Quote | Create, send, convert, expire |
| Sales Order | Create, confirm, produce, ship, cancel |
| Production | Create, release, record completion, scrap |
| Purchasing | Create, send, receive (partial, full) |
| Inventory | Transactions, running balance, negative prevention |
| MRP | Shortage detection, suggestions, reorder alerts |

---

# APPENDIX: OPEN QUESTIONS

Decisions to make as we build:

1. **Partial shipments?** Can we ship 8 of 10 and ship 2 later?
2. **Lot/serial tracking?** Needed for traceability?
3. **Multi-location?** Or just MAIN for now?
4. **Approval workflows?** Or trust the operator?
5. **Audit log?** How detailed?
6. **Seasonal forecasting?** Or just reorder points?

---

# APPENDIX: GLOSSARY

| Term | Meaning |
|------|---------|
| BOM | Bill of Materials - recipe for making a product |
| MTO | Make-to-Order - produce after customer orders |
| MTS | Make-to-Stock - produce to replenish inventory |
| MRP | Material Requirements Planning - "what do I need" |
| SO | Sales Order |
| PO | Purchase Order |
| WO | Work Order / Production Order |
| UOM | Unit of Measure |
| FG | Finished Goods |
| RM | Raw Materials |

---

**END OF SPECIFICATION v0.2**
