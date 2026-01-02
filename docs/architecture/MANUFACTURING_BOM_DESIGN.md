# Manufacturing BOM Design Document

**Status:** Draft  
**Author:** Claude + Brandan  
**Created:** 2024-12-30  
**Last Updated:** 2024-12-30

---

## Executive Summary

This document proposes unifying the Bill of Materials (BOM) and Routing into a single **Manufacturing BOM** structure where materials are consumed at specific operations rather than all at once. This enables precise material planning, accurate costing, and better shortage visibility.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Problem Statement](#2-problem-statement)
3. [Proposed Solution](#3-proposed-solution)
4. [Data Model](#4-data-model)
5. [UI Design](#5-ui-design)
6. [API Design](#6-api-design)
7. [Production Flow Changes](#7-production-flow-changes)
8. [MRP Impact](#8-mrp-impact)
9. [Migration Strategy](#9-migration-strategy)
10. [Implementation Plan](#10-implementation-plan)

---

## 1. Current State Analysis

### 1.1 Existing Data Model

```
Product
  ├── BOM (materials only)
  │     └── BOMLine
  │           ├── component_id
  │           ├── quantity
  │           ├── unit
  │           ├── consume_stage ('production' | 'shipping')
  │           └── is_cost_only
  │
  └── Routing (operations only)
        └── RoutingOperation
              ├── work_center_id
              ├── sequence
              ├── setup_time_minutes
              ├── run_time_minutes
              └── (no material link)
```

### 1.2 Current Consumption Logic

| Stage | When Consumed | Items |
|-------|---------------|-------|
| `production` | At print completion | Filament, raw materials |
| `shipping` | At label purchase | Boxes, labels, packaging |

### 1.3 Work Center Types

| Type | Description | Example | Has Resources |
|------|-------------|---------|---------------|
| `machine` | Pool of similar machines | FDM-POOL | Yes (Leonardo, Donatelo...) |
| `station` | Single work station | QC, POST-PRINT | No (or 1 implicit) |
| `production` | Legacy/test data | WC-PRINT | Should delete |

### 1.4 What Works

- ✅ Routing operations copy to PO on release
- ✅ Work centers with rates for costing
- ✅ Resources (machines) can be assigned to operations
- ✅ Time calculation (run_time × quantity)
- ✅ Basic BOM material tracking

### 1.5 What Doesn't Work

- ❌ Materials not tied to operations
- ❌ Can't see "what materials needed for Op 10 vs Op 40"
- ❌ Coarse consumption stages (only 2)
- ❌ MRP can't plan by operation
- ❌ Separate UI for BOM vs Routing
- ❌ `consume_stage` is a workaround

---

## 2. Problem Statement

### 2.1 Real-World Scenario

**Product:** Custom 3D Printed Widget (FG-WIDGET-001)

| Operation | Work Center | Time | Materials Needed |
|-----------|-------------|------|------------------|
| OP-10 Print | FDM-POOL | 325 min | Black PLA 37g |
| OP-20 Post-Process | POST-PRINT | 5 min | - |
| OP-30 QC Inspect | QC | 3 min | - |
| OP-40 Pack & Label | ASSEMBLY | 2 min | Part Label ×1 |
| OP-50 Ship | SHIP | 2 min | Box ×1, Ship Label ×1 |

### 2.2 Current System Limitations

**Problem 1: Can't Start Production Due to Missing Shipping Materials**
```
Planner: "Can I start this job?"
System: "BOM shows you need Box and Shipping Label"
Planner: "But I don't need those until OP-50!"
System: ¯\_(ツ)_/¯
```

**Problem 2: Inaccurate Shortage Analysis**
```
MRP: "Short 100 boxes, can't release any orders"
Reality: Could print all 50 orders, just can't ship yet
```

**Problem 3: Material Traceability Gap**
```
Auditor: "What filament lot was used on this part?"
System: "It was consumed at 'production' stage"
Auditor: "But which operation? Which machine?"
System: ¯\_(ツ)_/¯
```

**Problem 4: Dual Maintenance**
```
Engineer: "I changed the routing to add a QC step"
Also Engineer: "Did I update the BOM? No, those are separate..."
```

---

## 3. Proposed Solution

### 3.1 Core Concept: Operation-Level Materials

Attach materials directly to routing operations. When the operation completes, its materials are consumed.

```
Product: FG-WIDGET-001
└── Manufacturing BOM (unified)
      │
      ├── OP-10: PRINT (FDM-POOL)
      │     ├── Run: 325 min, Setup: 7 min
      │     └── Materials:
      │           └── Black PLA (37g)
      │
      ├── OP-20: POST-PROCESS (POST-PRINT)
      │     ├── Run: 5 min
      │     └── Materials: (none)
      │
      ├── OP-30: QC (QC)
      │     ├── Run: 3 min
      │     └── Materials: (none)
      │
      ├── OP-40: PACK (ASSEMBLY)
      │     ├── Run: 2 min
      │     └── Materials:
      │           └── Part Label (1 EA)
      │
      └── OP-50: SHIP (SHIP)
            ├── Run: 2 min
            └── Materials:
                  ├── 6x6x6 Box (1 EA)
                  └── 4x6 Shipping Label (1 EA)
```

### 3.2 Key Benefits

| Benefit | Description |
|---------|-------------|
| **Precise Planning** | MRP knows exactly when each material is needed |
| **Partial Release** | Can start jobs even if late-stage materials are short |
| **Accurate Costing** | Labor + materials calculated per operation |
| **Better Traceability** | Material lot tied to specific operation execution |
| **Single Source of Truth** | One editor for operations + materials |
| **Cleaner Shortage View** | "Short boxes at OP-50" vs "Short boxes somewhere" |

### 3.3 Design Principles

1. **Backward Compatible** - Existing BOMs/Routings continue to work
2. **Additive Change** - New table, not replacing existing
3. **Optional Materials** - Operations don't require materials
4. **Inherit from Routing** - PO operations still copy from routing template
5. **Consume on Complete** - Materials allocated when operation completes

---

## 4. Data Model

### 4.1 New Table: `routing_operation_materials`

```sql
CREATE TABLE routing_operation_materials (
    id SERIAL PRIMARY KEY,
    routing_operation_id INTEGER NOT NULL REFERENCES routing_operations(id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES products(id),
    
    -- Quantity
    quantity NUMERIC(18,6) NOT NULL,
    quantity_per VARCHAR(20) DEFAULT 'unit',  -- 'unit', 'batch', 'order'
    unit VARCHAR(20) NOT NULL DEFAULT 'EA',   -- EA, g, kg, m, etc.
    
    -- Scrap/waste
    scrap_factor NUMERIC(5,2) DEFAULT 0,
    
    -- Flags
    is_cost_only BOOLEAN DEFAULT FALSE,       -- For overhead items
    is_optional BOOLEAN DEFAULT FALSE,        -- For optional components
    
    -- Notes
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rom_routing_operation ON routing_operation_materials(routing_operation_id);
CREATE INDEX idx_rom_component ON routing_operation_materials(component_id);
```

### 4.2 New Table: `production_order_operation_materials`

```sql
CREATE TABLE production_order_operation_materials (
    id SERIAL PRIMARY KEY,
    production_order_operation_id INTEGER NOT NULL REFERENCES production_order_operations(id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES products(id),
    
    -- Planned (from routing)
    quantity_required NUMERIC(18,6) NOT NULL,
    unit VARCHAR(20) NOT NULL DEFAULT 'EA',
    
    -- Actual (at consumption)
    quantity_consumed NUMERIC(18,6) DEFAULT 0,
    inventory_transaction_id INTEGER REFERENCES inventory_transactions(id),
    lot_number VARCHAR(100),
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, allocated, consumed, returned
    
    -- Metadata
    consumed_at TIMESTAMP,
    consumed_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_poom_operation ON production_order_operation_materials(production_order_operation_id);
CREATE INDEX idx_poom_component ON production_order_operation_materials(component_id);
```

### 4.3 SQLAlchemy Models

```python
# backend/app/models/manufacturing.py (additions)

class RoutingOperationMaterial(Base):
    """Material required for a specific routing operation."""
    __tablename__ = "routing_operation_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    routing_operation_id = Column(Integer, ForeignKey("routing_operations.id", ondelete="CASCADE"), nullable=False)
    component_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Quantity
    quantity = Column(Numeric(18, 6), nullable=False)
    quantity_per = Column(String(20), default="unit")  # unit, batch, order
    unit = Column(String(20), default="EA", nullable=False)
    
    # Scrap/waste
    scrap_factor = Column(Numeric(5, 2), default=0)
    
    # Flags
    is_cost_only = Column(Boolean, default=False)
    is_optional = Column(Boolean, default=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    routing_operation = relationship("RoutingOperation", back_populates="materials")
    component = relationship("Product", foreign_keys=[component_id])


# Update RoutingOperation to include materials relationship
class RoutingOperation(Base):
    # ... existing fields ...
    
    # Add relationship
    materials = relationship("RoutingOperationMaterial", back_populates="routing_operation",
                            cascade="all, delete-orphan")
```

```python
# backend/app/models/production_order.py (additions)

class ProductionOrderOperationMaterial(Base):
    """Material consumption tracking for a production order operation."""
    __tablename__ = "production_order_operation_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    production_order_operation_id = Column(Integer, ForeignKey("production_order_operations.id", ondelete="CASCADE"), nullable=False)
    component_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Planned
    quantity_required = Column(Numeric(18, 6), nullable=False)
    unit = Column(String(20), default="EA", nullable=False)
    
    # Actual consumption
    quantity_consumed = Column(Numeric(18, 6), default=0)
    inventory_transaction_id = Column(Integer, ForeignKey("inventory_transactions.id"), nullable=True)
    lot_number = Column(String(100), nullable=True)
    
    # Status: pending, allocated, consumed, returned
    status = Column(String(20), default="pending")
    
    # Metadata
    consumed_at = Column(DateTime, nullable=True)
    consumed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    operation = relationship("ProductionOrderOperation", back_populates="materials")
    component = relationship("Product", foreign_keys=[component_id])
    transaction = relationship("InventoryTransaction")


# Update ProductionOrderOperation
class ProductionOrderOperation(Base):
    # ... existing fields ...
    
    # Add relationship
    materials = relationship("ProductionOrderOperationMaterial", back_populates="operation",
                            cascade="all, delete-orphan")
```

### 4.4 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TEMPLATE (Routing)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐       ┌─────────────────────┐       ┌──────────────────┐   │
│  │   Product   │──────▶│      Routing        │──────▶│ RoutingOperation │   │
│  │             │       │  (is_active=true)   │       │   (sequence)     │   │
│  └─────────────┘       └─────────────────────┘       └────────┬─────────┘   │
│                                                               │             │
│                                                               │ 1:N         │
│                                                               ▼             │
│                                                    ┌─────────────────────┐  │
│                                                    │RoutingOperationMat. │  │
│                                                    │  (component, qty)   │  │
│                                                    └─────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ On PO Release
                                    │ (copy template)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INSTANCE (Production Order)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐       ┌─────────────────────┐                          │
│  │ ProductionOrder │──────▶│     POOperation     │                          │
│  │  (qty_ordered)  │       │ (qty × routing time)│                          │
│  └─────────────────┘       └──────────┬──────────┘                          │
│                                       │                                      │
│                                       │ 1:N                                  │
│                                       ▼                                      │
│                            ┌─────────────────────┐                          │
│                            │ POOperationMaterial │                          │
│                            │(qty × routing mat.) │                          │
│                            │ + lot tracking      │                          │
│                            └─────────────────────┘                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.5 Quantity Calculation

**Routing (per unit):**
```
Black PLA: 37g per unit
```

**PO (for 10 units):**
```
quantity_required = 37g × 10 = 370g
With 5% scrap: 370g × 1.05 = 388.5g
```

**Quantity Per Options:**
| Value | Description | Calculation |
|-------|-------------|-------------|
| `unit` | Per piece produced | qty × PO quantity |
| `batch` | Per production run | qty × 1 (fixed) |
| `order` | Per order (same as batch for now) | qty × 1 |

---

## 5. UI Design

### 5.1 Manufacturing BOM Editor (Combined)

This replaces the separate BOM and Routing editors with a single unified interface.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Manufacturing BOM: FG-WIDGET-001 - Custom Widget                    [X]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Product: FG-WIDGET-001 - Custom Widget          Version: 1.0  ☑ Active    │
│                                                                             │
│  ┌─ Summary ─────────────────────────────────────────────────────────────┐  │
│  │  Operations: 5    Total Time: 337 min    Material Cost: $4.82         │  │
│  │  Labor Cost: $8.97    Total Cost: $13.79                              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  [+ Add Operation]  [Apply Template ▼]                                      │
│                                                                             │
│  ┌─ Operations ──────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  ▼ OP-10  PRINT                          FDM-POOL        337 min     │  │
│  │    ├─ Setup: 7 min   Run: 325 min/pc   Rate: $1.60/hr                │  │
│  │    │                                                                  │  │
│  │    └─ Materials:                                         [+ Add Mat.] │  │
│  │         ┌──────────────────────────────────────────────────────────┐ │  │
│  │         │ SKU          │ Name        │ Qty    │ Unit │ Cost │  ⚙  │ │  │
│  │         ├──────────────┼─────────────┼────────┼──────┼──────┼─────┤ │  │
│  │         │ MAT-PLA-BLK  │ Black PLA   │ 37     │ g    │ $0.74│ [X] │ │  │
│  │         └──────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  ▶ OP-20  POST-PROCESS                   POST-PRINT      5 min       │  │
│  │    └─ No materials                                                    │  │
│  │                                                                       │  │
│  │  ▶ OP-30  QC INSPECT                     QC              3 min       │  │
│  │    └─ No materials                                                    │  │
│  │                                                                       │  │
│  │  ▼ OP-40  PACK & LABEL                   ASSEMBLY        2 min       │  │
│  │    ├─ Setup: 0 min   Run: 2 min/pc   Rate: $13.00/hr                 │  │
│  │    │                                                                  │  │
│  │    └─ Materials:                                         [+ Add Mat.] │  │
│  │         ┌──────────────────────────────────────────────────────────┐ │  │
│  │         │ SKU          │ Name        │ Qty    │ Unit │ Cost │  ⚙  │ │  │
│  │         ├──────────────┼─────────────┼────────┼──────┼──────┼─────┤ │  │
│  │         │ PKG-LBL-001  │ Part Label  │ 1      │ EA   │ $0.05│ [X] │ │  │
│  │         └──────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  ▼ OP-50  SHIP                           SHIP            2 min       │  │
│  │    ├─ Setup: 0 min   Run: 2 min/pc   Rate: $13.00/hr                 │  │
│  │    │                                                                  │  │
│  │    └─ Materials:                                         [+ Add Mat.] │  │
│  │         ┌──────────────────────────────────────────────────────────┐ │  │
│  │         │ SKU          │ Name           │ Qty │ Unit │ Cost │  ⚙  │ │  │
│  │         ├──────────────┼────────────────┼─────┼──────┼──────┼─────┤ │  │
│  │         │ PKG-BOX-6X6  │ 6x6x6 Box      │ 1   │ EA   │ $1.20│ [X] │ │  │
│  │         │ PKG-LBL-SHIP │ Shipping Label │ 1   │ EA   │ $0.15│ [X] │ │  │
│  │         └──────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│                                              [Cancel]  [Save Manufacturing BOM]│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Add/Edit Operation Modal

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Add Operation                                                       [X]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Sequence:  [ 10 ]        Operation Code: [ PRINT      ]                    │
│                                                                             │
│  Operation Name: [ 3D Print Base Component                    ]             │
│                                                                             │
│  Work Center:    [ FDM-POOL - FDM Printer Pool            ▼ ]               │
│                  Rate: $1.60/hr  │  Capacity: 20 hrs/day                    │
│                  Resources: Leonardo, Donatelo, Michelangelo, Raphael       │
│                                                                             │
│  ┌─ Time ────────────────────────────────────────────────────────────────┐  │
│  │  Setup Time:    [ 7    ] min     (one-time per batch)                 │  │
│  │  Run Time:      [ 325  ] min/pc  (per unit produced)                  │  │
│  │  Wait Time:     [ 0    ] min     (cooling, curing)                    │  │
│  │  Move Time:     [ 0    ] min     (transfer to next op)                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Advanced ────────────────────────────────────────────────────────────┐  │
│  │  Units per Cycle:  [ 1 ]   (parts produced per run cycle)             │  │
│  │  Scrap Rate:       [ 2 ] % (expected yield loss)                      │  │
│  │  Runtime Source:   ( ) Manual  (•) From Slicer  ( ) Calculated        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Notes:                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Print at 0.2mm layer height, 15% infill, tree supports               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│                                              [Cancel]  [Save Operation]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Add Material to Operation Modal

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Add Material to OP-10 PRINT                                         [X]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Search: [ black pla                                    ] [🔍]              │
│                                                                             │
│  ┌─ Search Results ──────────────────────────────────────────────────────┐  │
│  │  ○ MAT-PLA-BLK    Black PLA Filament      $0.02/g    142g in stock   │  │
│  │  ○ MAT-PLA-BLK-CF Black PLA Carbon Fiber  $0.04/g    0g in stock     │  │
│  │  ○ MAT-PETG-BLK   Black PETG Filament     $0.025/g   89g in stock    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Selected: MAT-PLA-BLK - Black PLA Filament                                 │
│                                                                             │
│  Quantity:     [ 37    ]   Unit: [ g  ▼ ]                                   │
│                                                                             │
│  Quantity Per: (•) Per Unit   ( ) Per Batch   ( ) Per Order                 │
│                                                                             │
│  Scrap Factor: [ 5 ] %   (additional qty for waste)                         │
│                                                                             │
│  ☐ Cost Only (don't consume inventory, just add to cost)                    │
│  ☐ Optional  (not required to complete operation)                           │
│                                                                             │
│  Calculated for 10 units:                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Base: 37g × 10 = 370g                                                │  │
│  │  Scrap: 370g × 5% = 18.5g                                             │  │
│  │  Total Required: 388.5g                                               │  │
│  │  Cost: 388.5g × $0.02 = $7.77                                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│                                              [Cancel]  [Add Material]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Production Order Detail - Material View

Show materials needed per operation on the PO detail page:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Production Order: PO-2024-0042                                             │
│  Product: FG-WIDGET-001    Qty: 10                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Operations]  [Materials]  [QC]  [History]                                 │
│                                                                             │
│  ┌─ Materials by Operation ──────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  OP-10 PRINT                                           Status: ●Ready │  │
│  │  ┌────────────┬─────────────┬──────────┬──────────┬─────────────────┐ │  │
│  │  │ Component  │ Required    │ On Hand  │ Allocated│ Status          │ │  │
│  │  ├────────────┼─────────────┼──────────┼──────────┼─────────────────┤ │  │
│  │  │ Black PLA  │ 388.5g      │ 1,420g   │ 388.5g   │ ✓ Allocated     │ │  │
│  │  └────────────┴─────────────┴──────────┴──────────┴─────────────────┘ │  │
│  │                                                                       │  │
│  │  OP-20 POST-PROCESS                                    Status: ●Ready │  │
│  │  └─ No materials required                                             │  │
│  │                                                                       │  │
│  │  OP-30 QC INSPECT                                      Status: ●Ready │  │
│  │  └─ No materials required                                             │  │
│  │                                                                       │  │
│  │  OP-40 PACK & LABEL                                    Status: ●Ready │  │
│  │  ┌────────────┬─────────────┬──────────┬──────────┬─────────────────┐ │  │
│  │  │ Component  │ Required    │ On Hand  │ Allocated│ Status          │ │  │
│  │  ├────────────┼─────────────┼──────────┼──────────┼─────────────────┤ │  │
│  │  │ Part Label │ 10 EA       │ 500 EA   │ 10 EA    │ ✓ Allocated     │ │  │
│  │  └────────────┴─────────────┴──────────┴──────────┴─────────────────┘ │  │
│  │                                                                       │  │
│  │  OP-50 SHIP                                          Status: ⚠ Short  │  │
│  │  ┌────────────┬─────────────┬──────────┬──────────┬─────────────────┐ │  │
│  │  │ Component  │ Required    │ On Hand  │ Allocated│ Status          │ │  │
│  │  ├────────────┼─────────────┼──────────┼──────────┼─────────────────┤ │  │
│  │  │ 6x6x6 Box  │ 10 EA       │ 3 EA     │ 3 EA     │ ⚠ Short 7      │ │  │
│  │  │ Ship Label │ 10 EA       │ 100 EA   │ 10 EA    │ ✓ Allocated     │ │  │
│  │  └────────────┴─────────────┴──────────┴──────────┴─────────────────┘ │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Summary: OP-10 through OP-40 ready to start. OP-50 blocked (short boxes)   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.5 Navigation Updates

Add Manufacturing BOM to relevant places:

```
Admin Sidebar:
├── Items
│     └── [Item Detail] → [Edit Manufacturing BOM] button
├── Manufacturing
│     ├── Work Centers
│     ├── Resources  
│     └── Manufacturing BOMs  ← NEW: List/manage all
├── Production Orders
└── ...
```

---

## 6. API Design

### 6.1 New Endpoints

#### Manufacturing BOM (combined view)

```
GET /api/v1/manufacturing-bom/{product_id}
  → Returns routing + operations + materials in unified structure

PUT /api/v1/manufacturing-bom/{product_id}
  → Update entire manufacturing BOM (operations + materials)

POST /api/v1/manufacturing-bom/{product_id}/from-template
  → Create from routing template
```

#### Routing Operation Materials

```
GET /api/v1/routings/{routing_id}/operations/{op_id}/materials
  → List materials for specific operation

POST /api/v1/routings/{routing_id}/operations/{op_id}/materials
  → Add material to operation

PUT /api/v1/routings/operations/materials/{material_id}
  → Update material quantity/unit

DELETE /api/v1/routings/operations/materials/{material_id}
  → Remove material from operation
```

#### Production Order Operation Materials

```
GET /api/v1/production-orders/{po_id}/operations/{op_id}/materials
  → List materials for PO operation (with availability)

POST /api/v1/production-orders/{po_id}/operations/{op_id}/materials/allocate
  → Allocate inventory to operation materials

POST /api/v1/production-orders/{po_id}/operations/{op_id}/materials/consume
  → Consume materials (called on operation complete)
```

### 6.2 Schema Examples

#### Unified Manufacturing BOM Response

```json
{
  "product_id": 42,
  "product_sku": "FG-WIDGET-001",
  "product_name": "Custom Widget",
  "routing_id": 15,
  "version": "1.0",
  "is_active": true,
  "summary": {
    "operation_count": 5,
    "total_setup_minutes": 7,
    "total_run_minutes_per_unit": 337,
    "total_material_cost_per_unit": 4.82,
    "total_labor_cost_per_unit": 8.97,
    "total_cost_per_unit": 13.79
  },
  "operations": [
    {
      "id": 101,
      "sequence": 10,
      "operation_code": "PRINT",
      "operation_name": "3D Print",
      "work_center_id": 1,
      "work_center_code": "FDM-POOL",
      "work_center_name": "FDM Printer Pool",
      "setup_time_minutes": 7,
      "run_time_minutes": 325,
      "labor_cost": 8.80,
      "materials": [
        {
          "id": 201,
          "component_id": 55,
          "component_sku": "MAT-PLA-BLK",
          "component_name": "Black PLA Filament",
          "quantity": 37,
          "unit": "g",
          "quantity_per": "unit",
          "scrap_factor": 5,
          "unit_cost": 0.02,
          "extended_cost": 0.74,
          "is_cost_only": false,
          "is_optional": false
        }
      ],
      "material_cost": 0.74
    },
    {
      "id": 102,
      "sequence": 20,
      "operation_code": "POST",
      "operation_name": "Post-Process",
      "work_center_id": 2,
      "work_center_code": "POST-PRINT",
      "setup_time_minutes": 0,
      "run_time_minutes": 5,
      "materials": [],
      "material_cost": 0
    }
    // ... more operations
  ]
}
```

---

## 7. Production Flow Changes

### 7.1 Updated Operation Completion Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Complete Operation Flow                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Operator clicks "Complete" on OP-10                              │
│     └─ Enter: qty_good=8, qty_bad=2                                  │
│                                                                      │
│  2. System checks operation materials                                │
│     └─ OP-10 has: Black PLA (388.5g required for 10 units)           │
│                                                                      │
│  3. Calculate actual consumption                                     │
│     └─ Consumed: 388.5g × (8+2)/10 = 388.5g (all material used)      │
│     └─ OR: Could prorate to good qty only: 388.5g × 8/10 = 310.8g    │
│                                                                      │
│  4. Consume inventory                                                │
│     └─ Create inventory_transaction (type='consume')                 │
│     └─ Update po_operation_material.quantity_consumed                │
│     └─ Record lot_number if lot-tracked                              │
│                                                                      │
│  5. Update operation status                                          │
│     └─ status = 'complete'                                           │
│     └─ qty_completed = 8, qty_scrapped = 2                           │
│                                                                      │
│  6. Forward quantity to next operation                               │
│     └─ OP-20 now has quantity_input = 8                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 Material Consumption Options

| Option | Description | When to Use |
|--------|-------------|-------------|
| **Consume All** | Use all planned material regardless of yield | Materials can't be reclaimed (filament, chemicals) |
| **Consume Proportional** | qty_consumed = planned × (good+bad)/planned_qty | Partial material recovery possible |
| **Consume Good Only** | qty_consumed = planned × good/planned_qty | Material fully recoverable from scrap |

**Recommendation:** Default to "Consume All" for 3D printing (filament is used whether part is good or bad). Allow override in work center settings.

### 7.3 Shortage Handling at Operation Start

```python
def start_operation(po_op_id: int) -> dict:
    """Start an operation, checking material availability."""
    
    op = get_operation(po_op_id)
    
    # Check materials for THIS operation
    shortages = []
    for mat in op.materials:
        available = get_available_qty(mat.component_id)
        if available < mat.quantity_required:
            shortages.append({
                'component': mat.component.sku,
                'required': mat.quantity_required,
                'available': available,
                'short': mat.quantity_required - available
            })
    
    if shortages:
        return {
            'can_start': False,
            'reason': 'material_shortage',
            'shortages': shortages
        }
    
    # Allocate materials
    for mat in op.materials:
        allocate_inventory(mat.component_id, mat.quantity_required, po_op_id)
        mat.status = 'allocated'
    
    op.status = 'running'
    return {'can_start': True}
```

---

## 8. MRP Impact

### 8.1 Current MRP Logic (Simplified)

```
For each demand (SO line):
  Get BOM for product
  For each BOM line:
    Calculate gross requirement
    Check inventory
    Generate planned order if short
```

### 8.2 Enhanced MRP with Operation Timing

```
For each demand (SO line):
  Get Manufacturing BOM for product
  
  For each operation (in sequence):
    Calculate operation start date (backward from due date)
    
    For each material in operation:
      requirement_date = operation_start_date
      
      Calculate gross requirement:
        base_qty = material.quantity × demand_qty
        with_scrap = base_qty × (1 + scrap_factor)
      
      Check inventory at requirement_date
      Generate planned order if short
        planned_order.need_date = requirement_date
```

### 8.3 MRP Output Enhancement

```
Current:
┌────────────────┬──────────┬───────────┬───────────┐
│ Component      │ Required │ Available │ Short     │
├────────────────┼──────────┼───────────┼───────────┤
│ Black PLA      │ 388.5g   │ 142g      │ 246.5g    │
│ 6x6x6 Box      │ 10 EA    │ 3 EA      │ 7 EA      │
└────────────────┴──────────┴───────────┴───────────┘

Enhanced:
┌────────────────┬──────────┬───────────┬───────────┬────────────┬──────────┐
│ Component      │ Required │ Available │ Short     │ Need Date  │ For Op   │
├────────────────┼──────────┼───────────┼───────────┼────────────┼──────────┤
│ Black PLA      │ 388.5g   │ 142g      │ 246.5g    │ 2024-01-15 │ OP-10    │
│ 6x6x6 Box      │ 10 EA    │ 3 EA      │ 7 EA      │ 2024-01-17 │ OP-50    │
└────────────────┴──────────┴───────────┴───────────┴────────────┴──────────┘

Insight: Black PLA needed first (OP-10), boxes not until OP-50 (2 days later)
```

---

## 9. Migration Strategy

### 9.1 Phase 1: Add New Tables (Non-Breaking)

1. Create `routing_operation_materials` table
2. Create `production_order_operation_materials` table
3. Add relationships to existing models
4. No changes to existing BOM or Routing functionality

### 9.2 Phase 2: New UI (Parallel)

1. Build Manufacturing BOM editor as new component
2. Keep existing BOM and Routing editors working
3. Add "Edit Manufacturing BOM" button to item detail
4. Allow users to migrate products one at a time

### 9.3 Phase 3: Migration Helper

```python
def migrate_bom_to_manufacturing_bom(product_id: int):
    """
    Migrate traditional BOM to operation-level materials.
    
    Strategy:
    - 'production' stage items → First operation
    - 'shipping' stage items → Last operation (or SHIP op if exists)
    """
    product = get_product(product_id)
    bom = get_active_bom(product_id)
    routing = get_active_routing(product_id)
    
    if not routing:
        raise ValueError("Product needs a routing first")
    
    first_op = routing.operations[0]
    last_op = routing.operations[-1]
    ship_op = find_operation_by_code(routing, 'SHIP') or last_op
    
    for bom_line in bom.lines:
        if bom_line.consume_stage == 'production':
            target_op = first_op
        else:  # shipping
            target_op = ship_op
        
        create_routing_operation_material(
            routing_operation_id=target_op.id,
            component_id=bom_line.component_id,
            quantity=bom_line.quantity,
            unit=bom_line.unit,
            scrap_factor=bom_line.scrap_factor
        )
    
    # Mark BOM as migrated (don't delete yet)
    bom.notes = f"Migrated to Manufacturing BOM on {datetime.now()}"
```

### 9.4 Phase 4: Update Production Flow

1. Modify `complete_operation()` to consume operation materials
2. Update inventory service for operation-level consumption
3. Add material allocation at operation start

### 9.5 Phase 5: Deprecate Old BOM

1. Add deprecation warnings to old BOM editor
2. Update MRP to prefer operation materials
3. Eventually remove `consume_stage` from BOM lines

---

## 10. Implementation Plan

### 10.1 Milestones

| Phase | Milestone | Effort | Dependencies |
|-------|-----------|--------|--------------|
| 1 | Database migrations | 2 hrs | None |
| 2 | SQLAlchemy models | 2 hrs | Phase 1 |
| 3 | API endpoints | 4 hrs | Phase 2 |
| 4 | Manufacturing BOM Editor UI | 8 hrs | Phase 3 |
| 5 | Update operation completion | 4 hrs | Phase 3 |
| 6 | PO materials view | 4 hrs | Phase 5 |
| 7 | MRP enhancement | 4 hrs | Phase 5 |
| 8 | Migration tooling | 2 hrs | Phase 4 |
| 9 | Testing & polish | 4 hrs | All |
| **Total** | | **~34 hrs** | |

### 10.2 Suggested Order

1. **Database + Models** (Foundation)
2. **API Endpoints** (Backend complete)
3. **Manufacturing BOM Editor** (Can test end-to-end)
4. **Operation Completion** (Production flow works)
5. **PO Materials View** (Visibility)
6. **MRP** (Full integration)
7. **Migration** (Clean up old data)

### 10.3 Files to Create/Modify

**New Files:**
- `backend/app/models/routing_operation_material.py` (or add to manufacturing.py)
- `backend/app/schemas/manufacturing_bom.py`
- `backend/app/api/v1/endpoints/manufacturing_bom.py`
- `frontend/src/components/ManufacturingBOMEditor.jsx`
- `frontend/src/pages/admin/AdminManufacturingBOM.jsx`
- `alembic/versions/xxx_add_operation_materials.py`

**Modified Files:**
- `backend/app/models/manufacturing.py` (add relationship)
- `backend/app/models/production_order.py` (add relationship)
- `backend/app/services/operation_status.py` (consume materials)
- `backend/app/services/operation_generation.py` (copy materials)
- `backend/app/services/inventory_service.py` (operation-level consumption)
- `frontend/src/pages/admin/AdminItems.jsx` (add button)
- `frontend/src/components/AdminLayout.jsx` (add nav)

---

## Appendix A: Naming Inconsistency

Found during review:
```python
resource_id = Column(Integer, ForeignKey('machines.id'), nullable=True)
```

The foreign key references `machines.id` but the table is actually `resources`. Need to verify:

```bash
# Check actual table name
SELECT table_name FROM information_schema.tables WHERE table_name IN ('machines', 'resources');
```

If it's `resources`, we need to fix the FK. If it's `machines`, we should rename for consistency.

---

## Appendix B: Design Decisions (Resolved)

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Scrap material handling** | Consume full planned amount | Can't recover filament from scrap. Weighing scrap adds complexity. Inventory adjustments handle variances. |
| **Lot selection** | FIFO default, operator can override | Balance automation with flexibility. Operator may need specific lot for customer requirement. |
| **Phantom assemblies** | Not supported | All sub-assemblies are received to stock. Sub-assemblies consumed at assembly op for FG. No "make and immediately use" phantoms. |
| **Sub-assembly sales** | Not sellable individually | Sub-assemblies flagged as non-sellable. Only consumed internally. |

### Remaining Open Questions

1. **Over-consumption:** Allow consuming more than planned? How to record variance?
2. **Yield percentage:** Apply at operation level or material level?

---

## Approval

- [ ] Technical review
- [ ] UX review  
- [ ] Stakeholder approval
- [ ] Ready for implementation

---

*End of Document*
