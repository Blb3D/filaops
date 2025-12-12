```diff
--- a/c:\Users\brand\OneDrive\Documents\filaops\ARCHITECTURE.md
+++ b/c:\Users\brand\OneDrive\Documents\filaops\ARCHITECTURE.md
@@ -201,6 +201,19 @@
 │       └── ... (scheduling, timestamps)
 │
 │-- Print Jobs (linked to Bambu Suite)
+│
+│-- Inventory Transactions (Source of Truth)
+inventory_transactions
+├── id (PK)
+├── product_id (FK → products)
+├── transaction_type -- 'RECEIPT', 'ISSUE', 'ADJUST'
+├── quantity
+├── source_document_type -- 'PO', 'WO', 'SO'
+├── source_document_id
+├── created_by
+└── material_lot_id (FK)
+
+-- Print Jobs (linked to Bambu Suite)
 print_jobs
 ├── id (PK)
 ├── production_order_id (FK → production_orders)

# How FilaOps Works

A practical guide to understanding FilaOps for 3D print farm operators.

---

## The Big Picture

FilaOps manages the complete lifecycle of your print farm operations:

```
Customer Order → Production Planning → Printing → Quality Check → Shipping
       ↓                 ↓                ↓            ↓            ↓
  Sales Order    →  Production Order  →  Inventory Consumption  →  Fulfillment
```

Everything connects through **Products**, **BOMs**, and **Inventory**.

---

## Core Concepts

### 1. Products

Everything in FilaOps is a **Product** - whether you're selling it, buying it, or using it to make something else.

| Type | Examples | Track Inventory? |
|------|----------|------------------|
| **Finished Goods** | Phone stands, custom parts | Yes |
| **Raw Materials** | PLA Black, PETG Blue | Yes (by weight) |
| **Components** | Heat inserts, magnets | Yes |
| **Supplies** | Boxes, labels, tape | Yes |

**Key insight:** Your filament is a product. Your finished prints are products. The box you ship in is a product.

### 2. Bills of Materials (BOMs)

A BOM answers: **"What do I need to make this product?"**

Example BOM for a "Phone Stand (Black)":

| Component | Quantity | Unit |
|-----------|----------|------|
| PLA Black | 45 | grams |
| Heat Insert M3 | 4 | each |
| Small Box | 1 | each |

When you produce this item, FilaOps:
- Deducts 45g from your PLA Black inventory
- Deducts 4 heat inserts
- Deducts 1 box

### 3. Work Centers & Routings

**Work Centers** are where work happens:
- `FDM-POOL` - Your printer fleet (capacity: X hours/day)
- `QC` - Quality inspection station
- `PACKING` - Packing and shipping station

**Routings** define HOW to make something:

| Step | Work Center | Time |
|------|-------------|------|
| 1. Print | FDM-POOL | 2.5 hours |
| 2. Inspect | QC | 5 minutes |
| 3. Pack | PACKING | 3 minutes |

This enables:
- **Capacity planning** - "Can we deliver 50 units by Friday?"
- **Costing** - "This product costs $X in machine time + $Y in labor"
- **Scheduling** - "Printer pool is at 80% capacity this week"

### 4. Inventory Flow

```
Purchase Order (receive filament)
        ↓
    Inventory (PLA Black: 10kg on hand)
        ↓
Production Order (consume 450g for 10 phone stands)
        ↓
    Inventory (PLA Black: 9.55kg remaining)
              (Phone Stand: 10 units on hand)
        ↓
Sales Order (ship 5 phone stands)
        ↓
    Inventory (Phone Stand: 5 units remaining)
```

Every movement is tracked with an **Inventory Transaction**.

---

## The Workflow: Order to Shipment

### Step 1: Receive a Sales Order

A customer orders 10 "Phone Stands (Black)".

FilaOps creates:
- **Sales Order** `SO-2025-042`
  - Customer: Acme Corp
  - Product: Phone Stand (Black) × 10
  - Status: `confirmed`

### Step 2: Create Production Order

From the sales order, you generate a production order:

- **Production Order** `PO-2025-087`
  - Product: Phone Stand (Black)
  - Quantity: 10
  - BOM: BOM-PHONE-STAND-BLK
  - Routing: Standard Print Route
  - Status: `scheduled`

### Step 3: Start Production

When you click "Start Production":

1. **Material Reservation** - FilaOps reserves:
   - 450g PLA Black (45g × 10)
   - 40 heat inserts (4 × 10)
   - 10 small boxes

2. **Status Update** - Production order moves to `in_progress`

3. **Work Assignment** - First operation (Print) becomes active

**Tip:** For large orders, use **Split Order** to divide production across multiple machines. A 50-unit order can become two 25-unit child orders (PO-001-A, PO-001-B) that track independently.

### Step 4: Complete Printing

When printing finishes:

1. **Record Results**:
   - Quantity Good: 9
   - Quantity Bad: 1 (scrapped)

2. **Inventory Updates**:
   - Consume 405g PLA Black (good parts)
   - Scrap 45g PLA Black (bad part)
   - 9 finished goods added to inventory

3. **Move to Next Operation** - QC inspection

### Step 5: Quality Control

Inspector checks parts and marks QC passed/failed.

- Passed: Parts move to packing
- Failed: Parts scrapped, may trigger reprint

### Step 6: Ship Order

From the Shipping page:

1. **View ready orders** - Orders with status "completed" appear in the shipping queue
2. **Verify address** - Click "Edit Address" on Order Detail if needed
3. **Create label** - Use carrier links (USPS, FedEx, UPS) to create shipping label
4. **Enter tracking** - Add tracking number in the Ship modal
5. **Mark shipped** - Order status updates and tracking is saved

**Pro feature:** EasyPost integration for automated label creation and rate shopping.

---

## Setting Up Your First Workflow

### Minimal Setup (Get Running in 15 Minutes)

**1. Add a filament product:**

```
SKU: PLA-BLACK
Name: PLA Black 1kg
Category: Filament
Unit: grams
Cost: $0.025/gram
```

**2. Add a finished good:**

```
SKU: PHONE-STAND-BLK
Name: Phone Stand (Black)
Category: Finished Goods
Unit: each
Selling Price: $15.00
```

**3. Create a BOM:**

```
Product: Phone Stand (Black)
Lines:
  - PLA Black: 45 grams
```

**4. Add inventory:**

```
PLA Black: 1000 grams (Main Warehouse)
```

**5. Create a sales order:**

```
Customer: Test Customer
Product: Phone Stand (Black) × 2
```

**6. Generate production order from sales order**

**7. Complete production and ship**

---

## Understanding the Admin Dashboard

### Dashboard Metrics

| Metric | What It Shows |
|--------|---------------|
| **Pending Orders** | Sales orders waiting for production |
| **In Production** | Active production orders |
| **Ready to Ship** | Completed, awaiting shipment |
| **Low Stock Alerts** | Products below reorder point |

### Key Pages

| Page | Purpose |
|------|---------|
| **Products** | Add/edit your product catalog |
| **BOMs** | Define what goes into each product |
| **Orders** | View and manage sales orders |
| **Production** | Production queue and status |
| **Inventory** | Stock levels and adjustments |
| **Manufacturing** | Work centers and routings |
| **Purchasing** | Vendor management and POs |

---

## Traceability (For B2B/Compliance)

FilaOps supports tiered traceability:

| Level | What's Tracked | Use Case |
|-------|----------------|----------|
| **None** | Nothing | B2C retail |
| **Lot** | Material batches | Basic B2B |
| **Serial** | Individual units | Quality-critical |
| **Full** | Lot + Serial + CoC | FDA/ISO compliance |

### Example: Lot Traceability

When you receive filament:
- Create lot `PLA-BLK-2025-0042`
- Record vendor lot number, received date

When you produce:
- FilaOps records which lots were consumed
- If there's a recall, you can query: "What products used lot 0042?"

### Example: Serial Traceability

Each finished unit gets a serial number:
- `BLB-20251207-0001`
- `BLB-20251207-0002`

You can trace backward: "What materials went into serial 0001?"

---

## Cost Tracking

FilaOps calculates product costs from:

### Material Cost (from BOM)

```
Phone Stand BOM:
  PLA Black: 45g × $0.025 = $1.125
  Heat Insert: 4 × $0.05 = $0.20
  Box: 1 × $0.30 = $0.30

Material Total: $1.625
```

### Manufacturing Cost (from Routing)

```
Routing:
  Print: 2.5 hrs × $4.00/hr = $10.00
  QC: 0.08 hrs × $25.00/hr = $2.00
  Pack: 0.05 hrs × $18.00/hr = $0.90

Manufacturing Total: $12.90
```

### Total Product Cost

```
Material: $1.625
Manufacturing: $12.90
Total: $14.525
Selling Price: $15.00
Margin: $0.475 (3.2%)
```

---

## Common Questions

### "How do I track filament by the spool?"

Create each spool as a **lot**:
- Lot: `PLA-BLK-2025-0042`
- Quantity: 1000g
- Vendor lot: (from spool label)

When you load a spool, consume from that lot.

### "Can I handle multi-material prints?"

Yes! Your BOM includes multiple filament lines:

```
Benchy (Multi-Color) BOM:
  PLA White: 30g (hull)
  PLA Red: 5g (flag)
  PLA Black: 2g (details)
```

### "How do I handle reprints/failures?"

When completing a production operation:
1. Enter **Qty Good** and **Qty Bad**
2. Bad quantity is scrapped (inventory adjusted)
3. If you need more, create a new production order for the shortage

### "Can multiple people use it?"

Yes - it's a web app. Multiple users can access the admin dashboard simultaneously.

### "Does it connect to my printers?"

The **open source version** doesn't include printer integration.

**FilaOps Pro/Enterprise** includes:
- Bambu printer fleet management
- Automatic job dispatch
- Live print monitoring
- ML-based time estimation

---

## What's NOT in Open Source

The open source FilaOps includes everything for managing your print farm **except**:

| Feature | Open Source | Pro |
|---------|:-----------:|:---:|
| Products, BOMs, Inventory | Yes | Yes |
| Orders & Production | Yes | Yes |
| Traceability | Yes | Yes |
| MRP Planning | Yes | Yes |
| Admin Dashboard | Yes | Yes |
| Customer Quote Portal | No | Yes |
| Printer Integration | No | Yes |
| Shipping Labels | No | Yes |
| Payment Processing | No | Yes |

See the [README](README.md) for the full feature comparison.

---

## Next Steps

1. **Set up your database** - See [GETTING_STARTED.md](GETTING_STARTED.md)
2. **Add your products and BOMs** - Start with your top 5 products
3. **Process a test order** - Full cycle from order to ship
4. **Join the community** - [GitHub Discussions](https://github.com/Blb3D/filaops/discussions)

---

## Getting Help

- **Setup issues:** [GETTING_STARTED.md](GETTING_STARTED.md)
- **API questions:** [API Documentation](http://localhost:8000/docs)
- **Bug reports:** [GitHub Issues](https://github.com/Blb3D/filaops/issues)
- **Feature requests:** [GitHub Discussions](https://github.com/Blb3D/filaops/discussions)
