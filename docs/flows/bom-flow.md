# Bill of Materials (BOM) Flow Documentation

This document describes the BOM module workflows in FilaOps.

---

## 1. BOM Overview

```
+-----------------------------------------------------------------------------+
|                         BILL OF MATERIALS (BOM)                             |
|                                                                             |
|  A BOM defines the components (materials, parts) needed to produce          |
|  a finished product. FilaOps supports:                                      |
|                                                                             |
|  - Single-level BOMs (flat list of components)                              |
|  - Multi-level BOMs (sub-assemblies with their own BOMs)                    |
|  - Version control (multiple versions per product)                          |
|  - Cost rollup (automatic cost calculation)                                 |
|  - Scrap factor tracking                                                    |
+-----------------------------------------------------------------------------+

Key Concepts:
+---------------------+  +---------------------+  +---------------------+
|   PARENT PRODUCT    |  |        BOM          |  |     BOM LINES       |
+---------------------+  +---------------------+  +---------------------+
| • Finished good     |  | • Version number    |  | • Component ID      |
| • has_bom = true    |  | • Revision          |  | • Quantity needed   |
| • Can be sold       |  | • Total cost        |  | • Scrap factor %    |
| • Appears in orders |  | • Active/Inactive   |  | • Sequence order    |
+---------------------+  +---------------------+  +---------------------+
```

---

## 2. BOM Creation Flow

```
+-----------------------------------------------------------------------------+
|                         BOM CREATION FLOW                                    |
+-----------------------------------------------------------------------------+

User navigates to Admin > BOMs
         |
         v
+-----------------------------+
|    Click "New BOM"          |
|    (or from Items page)     |
+-----------------------------+
         |
         v
+-----------------------------+
|    Select Parent Product    |
|    (finished good to make)  |
+-----------------------------+
         |
         v
+-----------------------------+
|    BOM Header Created       |
|    +----------------------+ |
|    | Code: BOM-{SKU}-V1   | |
|    | Name: {Product} BOM  | |
|    | Version: 1           | |
|    | Active: true         | |
|    +----------------------+ |
+-----------------------------+
         |
         v
+-----------------------------+
|    Add BOM Lines            |
|    (components/materials)   |
+-----------------------------+
         |
         v
+---------------------------------------------------------+
|                    ADD LINE MODAL                        |
|                                                          |
|  Component: [Search raw materials / supplies...]         |
|  Quantity:  [_______]                                    |
|  Unit:      [kg / pcs / etc]  (from component)           |
|  Scrap %:   [_______]  (optional waste factor)           |
|  Notes:     [_______________________________________]    |
|                                                          |
|             [Cancel]  [Add Line]                         |
+---------------------------------------------------------+
         |
         v
+-----------------------------+
|   Line Added to BOM         |
|   • Total cost recalculated |
|   • Shows component details |
|   • Inventory status shown  |
+-----------------------------+
         |
         v (repeat for more lines)
         |
+-----------------------------+
|   BOM Complete              |
|   • All materials listed    |
|   • Total material cost set |
|   • Ready for production    |
+-----------------------------+
```

---

## 3. BOM List View

```
+-----------------------------------------------------------------------------+
|                         ADMIN BOM PAGE                                       |
+-----------------------------------------------------------------------------+

+-----------------------------------------------------------------------------+
| BOMs                                           [+ New BOM]  [Search...]     |
+-----------------------------------------------------------------------------+
| [Show Inactive]                                                             |
+-----------------------------------------------------------------------------+
|                                                                             |
| Product      | BOM Code        | Version | Material | Process | Total      |
|              |                 |         | Cost     | Cost    | Cost       |
| -------------+-----------------+---------+----------+---------+----------- |
| Widget A     | BOM-WIDGET-A-V1 |    1    |  $5.00   |  $2.00  |  $7.00    |
| MAT-WIDGET-A |                 |         |          |         |            |
| -------------+-----------------+---------+----------+---------+----------- |
| Bracket B    | BOM-BRACKET-V2  |    2    |  $3.50   |  $1.50  |  $5.00    |
| MAT-BRACKET  |                 |         |          |         |            |
| -------------+-----------------+---------+----------+---------+----------- |
|                                                                             |
+-----------------------------------------------------------------------------+

Cost Breakdown:
+------------------------------------+
| Material Cost = Sum of BOM lines   |
|   (component cost * quantity)      |
|                                    |
| Process Cost = From Routing        |
|   (labor + machine time)           |
|                                    |
| Total Cost = Material + Process    |
+------------------------------------+

Click row to expand BOM details...
```

---

## 4. BOM Detail View

```
+-----------------------------------------------------------------------------+
|                         BOM DETAIL VIEW                                      |
+-----------------------------------------------------------------------------+

+-----------------------------------------------------------------------------+
| [< Back]                                              [Edit] [Copy] [Delete] |
|                                                                              |
| BOM-WIDGET-A-V1                                                              |
| Widget A Bill of Materials                                                   |
+------------------------------------------------------------------------------+
| Product: Widget A (MAT-WIDGET-A)                                             |
| Version: 1  |  Revision: 1.0  |  Status: Active                              |
| Total Material Cost: $5.00                                                   |
+------------------------------------------------------------------------------+

COMPONENTS
+-----------------------------------------------------------------------------+
| Seq | Component          | SKU           | Qty    | Unit | Scrap | Cost     |
| ----+--------------------+---------------+--------+------+-------+--------- |
|  1  | PLA Black Filament | MAT-PLA-BLK   | 0.250  | kg   |  5%   | $3.15    |
|     | [sub-assembly icon if has BOM]      |        |      |       |          |
| ----+--------------------+---------------+--------+------+-------+--------- |
|  2  | Hardware Kit       | MAT-HW-KIT    | 1.000  | pcs  |  0%   | $1.85    |
|     |                    |               |        |      |       |          |
+-----------------------------------------------------------------------------+
| TOTAL                                                           | $5.00    |
+-----------------------------------------------------------------------------+

Line Actions:                     Inventory Status:
+-----------------------------+   +-----------------------------+
| [Edit] - Change qty/scrap   |   | Green = Sufficient stock    |
| [Delete] - Remove line      |   | Yellow = Below reorder pt   |
| [View] - If sub-assembly    |   | Red = Insufficient/shortage |
+-----------------------------+   +-----------------------------+
```

---

## 5. Multi-Level BOM (Sub-Assemblies)

```
+-----------------------------------------------------------------------------+
|                    MULTI-LEVEL BOM STRUCTURE                                 |
+-----------------------------------------------------------------------------+

Finished Product: "Complete Widget Assembly"
         |
         +-- Level 0 (Parent BOM)
         |
         v
+---------------------+
| BOM: Widget Assembly|
+---------------------+
         |
         +----+----+----+
         |    |    |    |
         v    v    v    v
     +------+ +------+ +------+ +------+
     |PLA   | |Screws| |Label | |Sub-  |
     |0.5kg | |4 pcs | |1 pcs | |Assy A|
     +------+ +------+ +------+ +------+
                                   |
                                   +-- Level 1 (Sub-Assembly BOM)
                                   |
                                   v
                           +---------------------+
                           | BOM: Sub-Assembly A |
                           +---------------------+
                                   |
                                   +----+----+
                                   |    |    |
                                   v    v    v
                               +------+ +------+ +------+
                               |Metal | |Spring| |Washer|
                               |0.1kg | |2 pcs | |4 pcs |
                               +------+ +------+ +------+

BOM Explosion (Flatten):
+-----------------------------------------------------------------+
| When exploding a multi-level BOM, quantities cascade:           |
|                                                                 |
| If Parent needs 2x Sub-Assembly A, and Sub-Assy needs 4 washers |
| Then Total washers = 2 * 4 = 8 washers                          |
+-----------------------------------------------------------------+
```

---

## 6. Cost Calculation Flow

```
+-----------------------------------------------------------------------------+
|                         COST CALCULATION                                     |
+-----------------------------------------------------------------------------+

Cost Priority (which cost to use for component):
+-----------------------------------------------+
| 1. standard_cost  (if set and > 0)            |
| 2. average_cost   (if set and > 0)            |
| 3. last_cost      (from most recent PO)       |
| 4. cost           (legacy field)              |
+-----------------------------------------------+

Line Cost Calculation:
+-----------------------------------------------+
| Line Cost = Component Cost * Quantity * (1 + Scrap%)
|                                               |
| Example:                                      |
|   Component: PLA @ $12/kg                     |
|   Quantity: 0.25 kg                           |
|   Scrap: 5%                                   |
|                                               |
|   Effective Qty = 0.25 * 1.05 = 0.2625 kg     |
|   Line Cost = $12 * 0.2625 = $3.15            |
+-----------------------------------------------+

BOM Total Cost:
+-----------------------------------------------+
| Total Material Cost = Sum(all line costs)     |
|                                               |
| For sub-assemblies:                           |
|   Use rolled-up cost from sub-BOM             |
|   (recursive calculation)                     |
+-----------------------------------------------+

Recalculate Endpoint:
+-----------------------------------------------+
| POST /api/v1/admin/bom/{id}/recalculate       |
|                                               |
| Triggered when:                               |
|   • Component prices change                   |
|   • Manual refresh requested                  |
|   • BOM line added/updated/deleted            |
+-----------------------------------------------+
```

---

## 7. BOM Copy Flow

```
+-----------------------------------------------------------------------------+
|                         BOM COPY FLOW                                        |
+-----------------------------------------------------------------------------+

Use Case: Create similar product with same/modified BOM

User clicks "Copy BOM"
         |
         v
+---------------------------------------------------------+
|                    COPY BOM MODAL                        |
|                                                          |
|  Source BOM: BOM-WIDGET-A-V1                             |
|                                                          |
|  Target Product: [Select product...]                     |
|  New Version:    [1]                                     |
|                                                          |
|  [x] Include all lines                                   |
|                                                          |
|             [Cancel]  [Copy BOM]                         |
+---------------------------------------------------------+
         |
         v
+-----------------------------+
|   POST /bom/{id}/copy       |
|   {                         |
|     target_product_id: 123, |
|     new_version: 1,         |
|     include_lines: true     |
|   }                         |
+-----------------------------+
         |
         v
+-----------------------------+
|   New BOM Created           |
|   • Same lines as source    |
|   • Linked to new product   |
|   • Ready for editing       |
+-----------------------------+
```

---

## 8. BOM Version Management

```
+-----------------------------------------------------------------------------+
|                         VERSION MANAGEMENT                                   |
+-----------------------------------------------------------------------------+

One Product Can Have Multiple BOM Versions:
+------------------+------------------+------------------+
| BOM-WIDGET-A-V1  | BOM-WIDGET-A-V2  | BOM-WIDGET-A-V3  |
| Version: 1       | Version: 2       | Version: 3       |
| Active: false    | Active: false    | Active: true     |
| (superseded)     | (superseded)     | (current)        |
+------------------+------------------+------------------+

Version Use Cases:
+-----------------------------------------------+
| • Product redesign (new materials)            |
| • Cost optimization (cheaper alternatives)    |
| • Process improvement                         |
| • Regulatory changes                          |
+-----------------------------------------------+

Active BOM Selection:
+-----------------------------------------------+
| GET /bom/product/{product_id}                 |
|                                               |
| Returns: Most recent ACTIVE BOM               |
| Sort: ORDER BY version DESC                   |
| Filter: WHERE active = true                   |
+-----------------------------------------------+

Deactivating Old Versions:
+-----------------------------------------------+
| When new version created:                     |
|   1. Create new BOM with version + 1          |
|   2. Set new BOM active = true                |
|   3. (Optional) Set old BOM active = false    |
|                                               |
| Note: Old versions kept for history           |
+-----------------------------------------------+
```

---

## 9. Inventory Availability Check

```
+-----------------------------------------------------------------------------+
|                    INVENTORY AVAILABILITY                                    |
+-----------------------------------------------------------------------------+

For each BOM line, system checks:
+-----------------------------------------------+
| GET component inventory from all locations    |
|                                               |
| on_hand_qty   = Total physical stock          |
| allocated_qty = Reserved for orders           |
| available_qty = on_hand - allocated           |
+-----------------------------------------------+

Availability Status per Line:
+-----------------------------------------------+
| qty_needed = line.quantity * parent_qty       |
|                                               |
| if available >= qty_needed:                   |
|     Status: AVAILABLE (green)                 |
|     shortage = 0                              |
|                                               |
| else:                                         |
|     Status: SHORTAGE (red)                    |
|     shortage = qty_needed - available         |
+-----------------------------------------------+

BOM Detail Shows:
+-----------------------------------------------------------------------------+
| Component      | Qty Needed | Available | Status    | Shortage             |
| ---------------+------------+-----------+-----------+--------------------- |
| PLA Black      | 0.25 kg    | 5.00 kg   | Available | -                    |
| Hardware Kit   | 1.00 pcs   | 0.00 pcs  | Shortage  | 1.00 pcs             |
+-----------------------------------------------------------------------------+

Quick Actions:
+-----------------------------+
| Shortage detected?          |
|   [Create PO] button        |
|   Links to Purchasing       |
+-----------------------------+
```

---

## 10. Data Model

```
+-----------------------------------------------------------------------------+
|                         BOM DATA MODEL                                       |
+-----------------------------------------------------------------------------+

+------------------+          +------------------+          +------------------+
|     products     |          |       boms       |          |    bom_lines     |
+------------------+          +------------------+          +------------------+
| id (PK)          |<---------| product_id (FK)  |          | id (PK)          |
| sku              |          | id (PK)          |<---------| bom_id (FK)      |
| name             |          | code             |          | component_id(FK) |--+
| has_bom          |          | name             |          | quantity         |  |
| ...              |          | version          |          | sequence         |  |
+------------------+          | revision         |          | scrap_factor     |  |
                              | active           |          | notes            |  |
                              | total_cost       |          +------------------+  |
                              | assembly_time    |                               |
                              | effective_date   |          +------------------+  |
                              | notes            |          |     products     |  |
                              +------------------+          | (as component)   |<-+
                                                            +------------------+
                                                            | id (PK)          |
                                                            | sku              |
                                                            | name             |
                                                            | cost             |
                                                            | ...              |
                                                            +------------------+
```

---

## 11. API Endpoints Reference

```
+-----------------------------------------------------------------------------+
|                         BOM API ENDPOINTS                                    |
+-----------------------------------------------------------------------------+

LIST & GET:
  GET  /api/v1/admin/bom/                    List all BOMs (paginated)
  GET  /api/v1/admin/bom/{bom_id}            Get single BOM with lines
  GET  /api/v1/admin/bom/product/{prod_id}   Get active BOM for product

CREATE & UPDATE:
  POST   /api/v1/admin/bom/                  Create new BOM
  PATCH  /api/v1/admin/bom/{bom_id}          Update BOM header
  DELETE /api/v1/admin/bom/{bom_id}          Deactivate BOM (soft delete)

LINE MANAGEMENT:
  POST   /api/v1/admin/bom/{bom_id}/lines              Add line
  PATCH  /api/v1/admin/bom/{bom_id}/lines/{line_id}   Update line
  DELETE /api/v1/admin/bom/{bom_id}/lines/{line_id}   Delete line

UTILITIES:
  POST /api/v1/admin/bom/{bom_id}/recalculate   Recalculate costs
  POST /api/v1/admin/bom/{bom_id}/copy          Copy BOM to new product

EXPLOSION (Multi-Level):
  GET /api/v1/admin/bom/{bom_id}/explode        Flatten multi-level BOM
  GET /api/v1/admin/bom/{bom_id}/rolled-up-cost Calculate full cost

+-----------------------------------------------------------------------------+
```

---

## 12. Testing Checklist

### BOM Creation
- [ ] Can create BOM for a product
- [ ] Auto-generates BOM code if not provided
- [ ] Can add multiple lines
- [ ] Total cost calculates correctly
- [ ] Product has_bom flag updates

### BOM Lines
- [ ] Can add component with quantity
- [ ] Scrap factor affects cost calculation
- [ ] Can edit line quantity/scrap
- [ ] Can delete line
- [ ] Cost recalculates on changes

### Multi-Level BOMs
- [ ] Sub-assemblies show BOM indicator
- [ ] Can drill down into sub-assembly BOM
- [ ] Explosion shows all levels
- [ ] Rolled-up cost includes sub-assemblies

### Version Management
- [ ] Can create new version
- [ ] Only one active BOM per product
- [ ] Old versions retained for history
- [ ] Copy creates new version

### Inventory Integration
- [ ] Shows available quantity per component
- [ ] Shortage status displays correctly
- [ ] Can trigger PO from shortage

### Cost Calculation
- [ ] Uses correct cost priority
- [ ] Scrap factor included
- [ ] Recalculate updates all costs
- [ ] Sub-assembly costs roll up
