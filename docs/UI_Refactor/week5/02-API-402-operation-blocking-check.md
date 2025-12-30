# API-402: Operation-Level Blocking Check

## Status: NOT STARTED

---

## Agent Instructions

- Execute steps IN ORDER - do not skip ahead
- Create ONLY the files listed - no extras
- Use EXACT code provided - do not "improve" it
- Run verification after EACH step before proceeding
- If a test fails, STOP and report - do not attempt fixes
- Commit with the EXACT message provided

⚠️ DO NOT:
- Modify any files outside the explicit list
- Add new dependencies without approval
- Refactor existing code "while you're in there"
- Skip the test step
- Change model field names or relationships
- "Optimize" or "clean up" code not in scope

---

## Overview

**Goal:** Check material availability per-operation, not per-PO  
**Outcome:** Missing shipping boxes don't block starting the print operation

---

## Why This Matters

**Current behavior:** When checking if a PO can start, we check ALL BOM materials. If the shipping boxes aren't in stock, the entire PO is blocked - even though we won't need boxes until the final PACK operation.

**After API-402:** Each operation only checks materials for ITS consume stage. The PRINT operation only checks filament. The PACK operation only checks boxes. Operations are independent.

**Real-world scenario:**
```
PO: Make Widget Pro (50 units)
├── Op 10: PRINT    → Needs: PLA filament (consume_stage='production')
├── Op 20: CLEAN    → Needs: nothing
├── Op 30: ASSEMBLE → Needs: hardware kit (consume_stage='assembly')  
├── Op 40: QC       → Needs: nothing
└── Op 50: PACK     → Needs: boxes (consume_stage='shipping')

Inventory:
- PLA filament: ✅ In stock
- Hardware kit: ✅ In stock  
- Boxes: ❌ OUT OF STOCK (PO arriving in 3 days)

Old behavior: ❌ Can't start PO - boxes missing
New behavior: ✅ Can start PRINT - boxes not needed until Op 50
```

---

## Consume Stage Mapping

The `BOMLine.consume_stage` field maps to operation codes:

| consume_stage | Operation Codes | Materials |
|---------------|-----------------|-----------|
| `production` | PRINT, EXTRUDE | Filament, raw materials |
| `assembly` | ASSEMBLE, BUILD | Hardware, subassemblies |
| `shipping` | PACK, SHIP | Boxes, labels, packaging |
| `any` | All operations | Consumed at first operation |

**Note:** We're extending consume_stage vocabulary, not changing the column type.

---

## Endpoints to Create/Modify

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/production-orders/{po_id}/operations/{op_id}/blocking-issues | Get blocking issues for specific operation |
| GET | /api/v1/production-orders/{po_id}/operations/{op_id}/can-start | Quick check if operation can start |

---

## Data Flow

```
1. User clicks "Start Operation" on PRINT op
2. Frontend calls GET /operations/{op_id}/can-start
3. Backend:
   a. Get operation's operation_code (e.g., "PRINT")
   b. Map operation_code → consume_stage (e.g., "production")
   c. Get BOM lines WHERE consume_stage IN ('production', 'any')
   d. Check inventory availability for ONLY those materials
   e. Return {can_start: true/false, blocking_issues: [...]}
4. If can_start=true, frontend enables Start button
5. If can_start=false, frontend shows blocking issues
```

---

## Step-by-Step Execution

---

### Step 1 of 8: Write Failing Tests First

**Agent:** Test Agent  
**Time:** 30 minutes  
**Directory:** backend/tests/api/

**File to Create:** `backend/tests/api/test_operation_blocking.py`
```python
"""
Tests for operation-level blocking check endpoints.

TDD: Write tests first, then implement to make them pass.
"""
import pytest
from decimal import Decimal

from tests.factories import (
    create_test_user,
    create_test_product,
    create_test_production_order,
    create_test_work_center,
    create_test_po_operation,
    create_test_bom,
    create_test_bom_line,
    create_test_inventory,
    create_test_inventory_location,
)


class TestOperationCanStart:
    """Tests for GET /api/v1/production-orders/{po_id}/operations/{op_id}/can-start"""

    @pytest.mark.api
    def test_can_start_materials_available(self, client, db, admin_token):
        """Operation can start when its materials are available."""
        # Setup: Product with BOM
        product = create_test_product(db, sku="WIDGET-001", name="Widget")
        filament = create_test_product(db, sku="PLA-BLACK", name="Black PLA", product_type="material")
        
        bom = create_test_bom(db, product=product)
        create_test_bom_line(
            db, bom=bom, component=filament,
            quantity=Decimal("0.5"), unit="KG",
            consume_stage="production"
        )
        
        # Setup: Inventory with enough filament
        location = create_test_inventory_location(db, code="WH-01", name="Warehouse")
        create_test_inventory(
            db, product=filament, location=location,
            on_hand=Decimal("10.0"), allocated=Decimal("0")
        )
        
        # Setup: Production order with PRINT operation
        wc = create_test_work_center(db, code="WC-PRINT-BLK1", name="Print Station")
        po = create_test_production_order(db, product=product, qty=10, status="released")
        po.bom_id = bom.id
        
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Execute
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert data["can_start"] is True
        assert data["blocking_issues"] == []

    @pytest.mark.api
    def test_cannot_start_materials_short(self, client, db, admin_token):
        """Operation cannot start when its materials are short."""
        # Setup: Product with BOM
        product = create_test_product(db, sku="WIDGET-002", name="Widget")
        filament = create_test_product(db, sku="PLA-WHITE", name="White PLA", product_type="material")
        
        bom = create_test_bom(db, product=product)
        create_test_bom_line(
            db, bom=bom, component=filament,
            quantity=Decimal("0.5"), unit="KG",
            consume_stage="production"
        )
        
        # Setup: Inventory with NOT ENOUGH filament (need 5kg for 10 units, only have 2kg)
        location = create_test_inventory_location(db, code="WH-02", name="Warehouse")
        create_test_inventory(
            db, product=filament, location=location,
            on_hand=Decimal("2.0"), allocated=Decimal("0")
        )
        
        # Setup: Production order with PRINT operation
        wc = create_test_work_center(db, code="WC-PRINT-BLK2", name="Print Station")
        po = create_test_production_order(db, product=product, qty=10, status="released")
        po.bom_id = bom.id
        
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Execute
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert data["can_start"] is False
        assert len(data["blocking_issues"]) == 1
        assert data["blocking_issues"][0]["product_sku"] == "PLA-WHITE"
        assert float(data["blocking_issues"][0]["quantity_short"]) == 3.0  # Need 5, have 2

    @pytest.mark.api
    def test_print_not_blocked_by_shipping_materials(self, client, db, admin_token):
        """PRINT operation not blocked by missing shipping materials."""
        # Setup: Product with BOM - both production and shipping materials
        product = create_test_product(db, sku="WIDGET-003", name="Widget")
        filament = create_test_product(db, sku="PLA-RED", name="Red PLA", product_type="material")
        boxes = create_test_product(db, sku="BOX-SMALL", name="Small Box", product_type="material")
        
        bom = create_test_bom(db, product=product)
        create_test_bom_line(
            db, bom=bom, component=filament,
            quantity=Decimal("0.5"), unit="KG",
            consume_stage="production"  # Consumed at PRINT
        )
        create_test_bom_line(
            db, bom=bom, component=boxes,
            quantity=Decimal("1"), unit="EA",
            consume_stage="shipping"  # Consumed at PACK
        )
        
        # Setup: Filament in stock, boxes OUT OF STOCK
        location = create_test_inventory_location(db, code="WH-03", name="Warehouse")
        create_test_inventory(
            db, product=filament, location=location,
            on_hand=Decimal("10.0"), allocated=Decimal("0")
        )
        # NO inventory for boxes!
        
        # Setup: Production order with PRINT operation
        wc = create_test_work_center(db, code="WC-PRINT-BLK3", name="Print Station")
        po = create_test_production_order(db, product=product, qty=10, status="released")
        po.bom_id = bom.id
        
        op_print = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Execute - check PRINT operation
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op_print.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify - PRINT can start even though boxes are missing
        assert response.status_code == 200
        data = response.json()
        
        assert data["can_start"] is True  # KEY ASSERTION
        assert data["blocking_issues"] == []

    @pytest.mark.api
    def test_pack_blocked_by_missing_boxes(self, client, db, admin_token):
        """PACK operation IS blocked by missing shipping materials."""
        # Setup: Same as above
        product = create_test_product(db, sku="WIDGET-004", name="Widget")
        filament = create_test_product(db, sku="PLA-BLUE", name="Blue PLA", product_type="material")
        boxes = create_test_product(db, sku="BOX-MED", name="Medium Box", product_type="material")
        
        bom = create_test_bom(db, product=product)
        create_test_bom_line(
            db, bom=bom, component=filament,
            quantity=Decimal("0.5"), unit="KG",
            consume_stage="production"
        )
        create_test_bom_line(
            db, bom=bom, component=boxes,
            quantity=Decimal("1"), unit="EA",
            consume_stage="shipping"
        )
        
        # Setup: Filament in stock, boxes OUT OF STOCK
        location = create_test_inventory_location(db, code="WH-04", name="Warehouse")
        create_test_inventory(
            db, product=filament, location=location,
            on_hand=Decimal("10.0"), allocated=Decimal("0")
        )
        
        # Setup: Production order with PACK operation (after PRINT is done)
        wc_print = create_test_work_center(db, code="WC-PRINT-BLK4", name="Print Station")
        wc_pack = create_test_work_center(db, code="WC-PACK-BLK4", name="Pack Station")
        
        po = create_test_production_order(db, product=product, qty=10, status="in_progress")
        po.bom_id = bom.id
        
        op_print = create_test_po_operation(
            db, production_order=po, work_center=wc_print,
            sequence=10, operation_code="PRINT", status="complete"
        )
        op_pack = create_test_po_operation(
            db, production_order=po, work_center=wc_pack,
            sequence=20, operation_code="PACK", status="pending"
        )
        db.commit()

        # Execute - check PACK operation
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op_pack.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify - PACK is blocked by missing boxes
        assert response.status_code == 200
        data = response.json()
        
        assert data["can_start"] is False  # KEY ASSERTION
        assert len(data["blocking_issues"]) == 1
        assert data["blocking_issues"][0]["product_sku"] == "BOX-MED"

    @pytest.mark.api
    def test_no_bom_can_start(self, client, db, admin_token):
        """Operation with no BOM can always start (no materials to check)."""
        product = create_test_product(db, sku="SERVICE-001", name="Service Item")
        wc = create_test_work_center(db, code="WC-SVC-BLK", name="Service")
        
        po = create_test_production_order(db, product=product, qty=1, status="released")
        # NO BOM assigned
        
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="WORK", status="pending"
        )
        db.commit()

        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.json()["can_start"] is True


class TestOperationBlockingIssues:
    """Tests for GET /api/v1/production-orders/{po_id}/operations/{op_id}/blocking-issues"""

    @pytest.mark.api
    def test_blocking_issues_detail(self, client, db, admin_token):
        """Get detailed blocking issues for an operation."""
        # Setup
        product = create_test_product(db, sku="WIDGET-005", name="Widget")
        mat1 = create_test_product(db, sku="MAT-A", name="Material A", product_type="material")
        mat2 = create_test_product(db, sku="MAT-B", name="Material B", product_type="material")
        
        bom = create_test_bom(db, product=product)
        create_test_bom_line(db, bom=bom, component=mat1, quantity=Decimal("5"), consume_stage="production")
        create_test_bom_line(db, bom=bom, component=mat2, quantity=Decimal("3"), consume_stage="production")
        
        # Only mat1 in stock, mat2 missing
        location = create_test_inventory_location(db, code="WH-05", name="Warehouse")
        create_test_inventory(db, product=mat1, location=location, on_hand=Decimal("100"), allocated=Decimal("0"))
        # mat2 not in inventory
        
        wc = create_test_work_center(db, code="WC-BLK-05", name="Work Center")
        po = create_test_production_order(db, product=product, qty=10, status="released")
        po.bom_id = bom.id
        
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/blocking-issues",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        
        assert data["operation_id"] == op.id
        assert data["operation_code"] == "PRINT"
        assert data["can_start"] is False
        
        # Should only show mat2 as blocking (mat1 is fine)
        assert len(data["material_issues"]) == 1
        assert data["material_issues"][0]["product_sku"] == "MAT-B"
        assert float(data["material_issues"][0]["quantity_required"]) == 30.0  # 3 per unit * 10 units
        assert float(data["material_issues"][0]["quantity_available"]) == 0
        assert float(data["material_issues"][0]["quantity_short"]) == 30.0

    @pytest.mark.api
    def test_blocking_issues_considers_allocated(self, client, db, admin_token):
        """Blocking check considers allocated inventory."""
        product = create_test_product(db, sku="WIDGET-006", name="Widget")
        filament = create_test_product(db, sku="PLA-GREEN", name="Green PLA", product_type="material")
        
        bom = create_test_bom(db, product=product)
        create_test_bom_line(db, bom=bom, component=filament, quantity=Decimal("1"), consume_stage="production")
        
        # 10 on hand but 8 allocated = only 2 available
        location = create_test_inventory_location(db, code="WH-06", name="Warehouse")
        create_test_inventory(
            db, product=filament, location=location,
            on_hand=Decimal("10"), allocated=Decimal("8")
        )
        
        wc = create_test_work_center(db, code="WC-BLK-06", name="Work Center")
        po = create_test_production_order(db, product=product, qty=5, status="released")  # Need 5
        po.bom_id = bom.id
        
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/blocking-issues",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        
        # Need 5, only 2 available (10 - 8 allocated) = 3 short
        assert data["can_start"] is False
        assert len(data["material_issues"]) == 1
        assert float(data["material_issues"][0]["quantity_available"]) == 2.0
        assert float(data["material_issues"][0]["quantity_short"]) == 3.0

    @pytest.mark.api
    def test_cost_only_lines_ignored(self, client, db, admin_token):
        """BOM lines marked is_cost_only=True are not checked for availability."""
        product = create_test_product(db, sku="WIDGET-007", name="Widget")
        filament = create_test_product(db, sku="PLA-YELLOW", name="Yellow PLA", product_type="material")
        overhead = create_test_product(db, sku="OVERHEAD", name="Machine Overhead", product_type="service")
        
        bom = create_test_bom(db, product=product)
        create_test_bom_line(
            db, bom=bom, component=filament,
            quantity=Decimal("1"), consume_stage="production",
            is_cost_only=False
        )
        create_test_bom_line(
            db, bom=bom, component=overhead,
            quantity=Decimal("1"), consume_stage="production",
            is_cost_only=True  # Should be ignored
        )
        
        location = create_test_inventory_location(db, code="WH-07", name="Warehouse")
        create_test_inventory(db, product=filament, location=location, on_hand=Decimal("100"), allocated=Decimal("0"))
        # No inventory for overhead (and shouldn't matter)
        
        wc = create_test_work_center(db, code="WC-BLK-07", name="Work Center")
        po = create_test_production_order(db, product=product, qty=10, status="released")
        po.bom_id = bom.id
        
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Should be able to start - overhead line is cost-only
        assert response.status_code == 200
        assert response.json()["can_start"] is True


class TestOperationNotFound:
    """Tests for 404 scenarios."""

    @pytest.mark.api
    def test_can_start_po_not_found(self, client, db, admin_token):
        response = client.get(
            "/api/v1/production-orders/99999/operations/1/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404

    @pytest.mark.api
    def test_can_start_op_not_found(self, client, db, admin_token):
        product = create_test_product(db, sku="TEST-404")
        po = create_test_production_order(db, product=product, qty=1, status="released")
        db.commit()

        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/99999/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
```

**Verification:**
- [ ] File created at `backend/tests/api/test_operation_blocking.py`
- [ ] Run `pytest backend/tests/api/test_operation_blocking.py -v`
- [ ] Tests FAIL (expected - TDD, endpoints don't exist yet)

**Commit Message:** `test(API-402): add failing tests for operation-level blocking check`

---

### Step 2 of 8: Add Factory Functions

**Agent:** Test Agent  
**Time:** 10 minutes  
**File to Modify:** `backend/tests/factories.py`

**Add these functions (if not already present):**
```python
def create_test_bom(
    db,
    product,
    code: str = None,
    name: str = "Test BOM",
    version: int = 1,
    active: bool = True
):
    """Create a test BOM."""
    from app.models.bom import BOM
    
    if code is None:
        code = f"BOM-{product.sku}"
    
    bom = BOM(
        product_id=product.id,
        code=code,
        name=name,
        version=version,
        active=active
    )
    db.add(bom)
    db.flush()
    return bom


def create_test_bom_line(
    db,
    bom,
    component,
    quantity: Decimal = Decimal("1"),
    unit: str = "EA",
    sequence: int = None,
    consume_stage: str = "production",
    is_cost_only: bool = False,
    scrap_factor: Decimal = Decimal("0")
):
    """Create a test BOM line."""
    from app.models.bom import BOMLine
    
    if sequence is None:
        # Auto-increment sequence
        existing = db.query(BOMLine).filter(BOMLine.bom_id == bom.id).count()
        sequence = (existing + 1) * 10
    
    line = BOMLine(
        bom_id=bom.id,
        component_id=component.id,
        sequence=sequence,
        quantity=quantity,
        unit=unit,
        consume_stage=consume_stage,
        is_cost_only=is_cost_only,
        scrap_factor=scrap_factor
    )
    db.add(line)
    db.flush()
    return line


def create_test_inventory_location(
    db,
    code: str = None,
    name: str = "Test Location",
    location_type: str = "warehouse",
    active: bool = True
):
    """Create a test inventory location."""
    from app.models.inventory import InventoryLocation
    
    if code is None:
        code = f"LOC-{datetime.now().strftime('%H%M%S%f')}"
    
    # Check if exists
    existing = db.query(InventoryLocation).filter(InventoryLocation.code == code).first()
    if existing:
        return existing
    
    location = InventoryLocation(
        code=code,
        name=name,
        type=location_type,
        active=active
    )
    db.add(location)
    db.flush()
    return location


def create_test_inventory(
    db,
    product,
    location,
    on_hand: Decimal = Decimal("0"),
    allocated: Decimal = Decimal("0")
):
    """Create a test inventory record."""
    from app.models.inventory import Inventory
    
    # Check if exists for this product/location
    existing = db.query(Inventory).filter(
        Inventory.product_id == product.id,
        Inventory.location_id == location.id
    ).first()
    
    if existing:
        existing.on_hand_quantity = on_hand
        existing.allocated_quantity = allocated
        db.flush()
        return existing
    
    inv = Inventory(
        product_id=product.id,
        location_id=location.id,
        on_hand_quantity=on_hand,
        allocated_quantity=allocated
    )
    db.add(inv)
    db.flush()
    return inv
```

**Verification:**
- [ ] Functions added to `backend/tests/factories.py`
- [ ] No import errors when running tests

**Commit Message:** `test(API-402): add BOM and inventory factory functions`

---

### Step 3 of 8: Create Operation Code to Consume Stage Mapping

**Agent:** Backend Agent  
**Time:** 10 minutes  
**Directory:** `backend/app/services/`

**File to Create:** `backend/app/services/operation_material_mapping.py`
```python
"""
Maps operation codes to BOM consume stages.

This determines which materials are needed at each operation.
"""
from typing import List, Set

# Operation code to consume stage mapping
# Multiple operation codes can map to the same consume stage
OPERATION_CONSUME_STAGES = {
    # Production operations - consume raw materials, filament
    "PRINT": ["production", "any"],
    "EXTRUDE": ["production", "any"],
    "MOLD": ["production", "any"],
    "CUT": ["production", "any"],
    "MACHINE": ["production", "any"],
    
    # Assembly operations - consume hardware, subassemblies
    "ASSEMBLE": ["assembly", "production", "any"],
    "BUILD": ["assembly", "production", "any"],
    "WELD": ["assembly", "production", "any"],
    
    # Finishing operations - typically no material consumption
    "CLEAN": ["any"],
    "SAND": ["any"],
    "PAINT": ["finishing", "any"],
    "COAT": ["finishing", "any"],
    
    # Quality operations - typically no material consumption
    "QC": ["any"],
    "INSPECT": ["any"],
    "TEST": ["any"],
    
    # Shipping operations - consume packaging materials
    "PACK": ["shipping", "any"],
    "SHIP": ["shipping", "any"],
    "LABEL": ["shipping", "any"],
}

# Default stages if operation code not found
DEFAULT_CONSUME_STAGES = ["production", "any"]


def get_consume_stages_for_operation(operation_code: str) -> List[str]:
    """
    Get the consume stages that apply to an operation code.
    
    Args:
        operation_code: The operation code (e.g., "PRINT", "PACK")
    
    Returns:
        List of consume stages to check for this operation
    """
    if not operation_code:
        return DEFAULT_CONSUME_STAGES
    
    code_upper = operation_code.upper()
    return OPERATION_CONSUME_STAGES.get(code_upper, DEFAULT_CONSUME_STAGES)


def get_all_consume_stages() -> Set[str]:
    """Get all known consume stages."""
    stages = set()
    for stage_list in OPERATION_CONSUME_STAGES.values():
        stages.update(stage_list)
    return stages
```

**Verification:**
- [ ] File created at `backend/app/services/operation_material_mapping.py`
- [ ] No import errors

**Commit Message:** `feat(API-402): add operation code to consume stage mapping`

---

### Step 4 of 8: Create Operation Blocking Service

**Agent:** Backend Agent  
**Time:** 30 minutes  
**Directory:** `backend/app/services/`

**File to Create:** `backend/app/services/operation_blocking.py`
```python
"""
Service layer for operation-level blocking checks.

Checks material availability for a specific operation, not the entire PO.
"""
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.bom import BOM, BOMLine
from app.models.production_order import ProductionOrder, ProductionOrderOperation
from app.models.inventory import Inventory
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.services.operation_material_mapping import get_consume_stages_for_operation


class OperationBlockingError(Exception):
    """Custom exception for operation blocking errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def get_operation_with_validation(
    db: Session,
    po_id: int,
    op_id: int
) -> Tuple[ProductionOrder, ProductionOrderOperation]:
    """
    Get operation and validate it belongs to the specified PO.
    
    Returns:
        Tuple of (ProductionOrder, ProductionOrderOperation)
    
    Raises:
        OperationBlockingError: If PO or operation not found
    """
    po = db.get(ProductionOrder, po_id)
    if not po:
        raise OperationBlockingError(f"Production order {po_id} not found", 404)
    
    op = db.get(ProductionOrderOperation, op_id)
    if not op:
        raise OperationBlockingError(f"Operation {op_id} not found", 404)
    
    if op.production_order_id != po_id:
        raise OperationBlockingError(
            f"Operation {op_id} does not belong to production order {po_id}", 404
        )
    
    return po, op


def get_material_available(db: Session, product_id: int) -> Decimal:
    """
    Get available inventory for a material.
    
    Available = on_hand - allocated (across all locations)
    """
    result = db.query(
        func.coalesce(func.sum(Inventory.on_hand_quantity - Inventory.allocated_quantity), Decimal("0"))
    ).filter(
        Inventory.product_id == product_id
    ).scalar()
    
    return Decimal(str(result or 0))


def get_bom_lines_for_operation(
    db: Session,
    bom_id: int,
    operation_code: str
) -> List[BOMLine]:
    """
    Get BOM lines that should be checked for a specific operation.
    
    Filters by:
    - consume_stage matches operation's stages
    - is_cost_only = False (cost-only lines don't consume inventory)
    
    Args:
        db: Database session
        bom_id: BOM ID
        operation_code: Operation code (e.g., "PRINT", "PACK")
    
    Returns:
        List of BOMLine objects to check
    """
    consume_stages = get_consume_stages_for_operation(operation_code)
    
    lines = db.query(BOMLine).filter(
        BOMLine.bom_id == bom_id,
        BOMLine.consume_stage.in_(consume_stages),
        BOMLine.is_cost_only == False  # noqa: E712
    ).all()
    
    return lines


def get_pending_purchase_orders(
    db: Session,
    product_id: int
) -> List[Tuple[PurchaseOrder, Decimal]]:
    """Get pending purchase orders for a product with remaining quantities."""
    active_statuses = ['draft', 'ordered', 'shipped']

    results = db.query(PurchaseOrder, PurchaseOrderLine).join(
        PurchaseOrderLine,
        PurchaseOrder.id == PurchaseOrderLine.purchase_order_id
    ).filter(
        PurchaseOrderLine.product_id == product_id,
        PurchaseOrder.status.in_(active_statuses)
    ).all()

    pos = []
    for po, pol in results:
        remaining = (pol.quantity_ordered or Decimal("0")) - (pol.quantity_received or Decimal("0"))
        if remaining > 0:
            pos.append((po, remaining))

    return pos


def check_operation_blocking(
    db: Session,
    po_id: int,
    op_id: int
) -> dict:
    """
    Check if an operation is blocked by material shortages.
    
    Only checks materials for THIS operation's consume stage,
    not all materials for the entire PO.
    
    Args:
        db: Database session
        po_id: Production order ID
        op_id: Operation ID
    
    Returns:
        dict with:
        - operation_id: int
        - operation_code: str
        - can_start: bool
        - blocking_issues: list of material shortage issues
        - material_issues: list of all material checks (for detailed view)
    
    Raises:
        OperationBlockingError: If PO or operation not found
    """
    po, op = get_operation_with_validation(db, po_id, op_id)
    
    result = {
        "operation_id": op.id,
        "operation_code": op.operation_code,
        "operation_name": op.operation_name,
        "can_start": True,
        "blocking_issues": [],
        "material_issues": [],
    }
    
    # If no BOM, nothing to check
    if not po.bom_id:
        return result
    
    # Get BOM lines for this operation
    bom_lines = get_bom_lines_for_operation(db, po.bom_id, op.operation_code)
    
    if not bom_lines:
        return result
    
    # Calculate quantity to produce (remaining)
    qty_to_produce = (po.quantity_ordered or Decimal("0")) - (po.quantity_completed or Decimal("0"))
    
    if qty_to_produce <= 0:
        return result
    
    # Check each material
    for line in bom_lines:
        component = db.get(Product, line.component_id)
        if not component:
            continue
        
        # Calculate required quantity (including scrap factor)
        scrap_multiplier = 1 + (line.scrap_factor or Decimal("0")) / 100
        qty_required = line.quantity * qty_to_produce * scrap_multiplier
        
        # Get available inventory
        qty_available = get_material_available(db, component.id)
        qty_short = max(Decimal("0"), qty_required - qty_available)
        
        # Check for incoming supply
        incoming_supply = None
        pending_pos = get_pending_purchase_orders(db, component.id)
        if pending_pos:
            po_incoming, po_qty = pending_pos[0]
            incoming_supply = {
                "purchase_order_id": po_incoming.id,
                "purchase_order_code": po_incoming.po_number,
                "quantity": float(po_qty),
                "expected_date": po_incoming.expected_date.isoformat() if po_incoming.expected_date else None
            }
        
        material_issue = {
            "product_id": component.id,
            "product_sku": component.sku,
            "product_name": component.name,
            "quantity_required": float(qty_required),
            "quantity_available": float(max(Decimal("0"), qty_available)),
            "quantity_short": float(qty_short),
            "unit": line.unit,
            "consume_stage": line.consume_stage,
            "incoming_supply": incoming_supply,
        }
        
        result["material_issues"].append(material_issue)
        
        # If short, add to blocking issues
        if qty_short > 0:
            result["can_start"] = False
            result["blocking_issues"].append(material_issue)
    
    return result


def can_operation_start(
    db: Session,
    po_id: int,
    op_id: int
) -> dict:
    """
    Quick check if an operation can start.
    
    Returns simplified response with just can_start and blocking issues.
    """
    full_result = check_operation_blocking(db, po_id, op_id)
    
    return {
        "can_start": full_result["can_start"],
        "blocking_issues": full_result["blocking_issues"]
    }
```

**Verification:**
- [ ] File created at `backend/app/services/operation_blocking.py`
- [ ] No import errors

**Commit Message:** `feat(API-402): add operation blocking service layer`

---

### Step 5 of 8: Create Pydantic Schemas

**Agent:** Backend Agent  
**Time:** 10 minutes  
**Directory:** `backend/app/schemas/`

**File to Create:** `backend/app/schemas/operation_blocking.py`
```python
"""
Schemas for operation-level blocking check responses.
"""
from datetime import date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class IncomingSupplyInfo(BaseModel):
    """Info about incoming supply from a purchase order."""
    purchase_order_id: int
    purchase_order_code: str
    quantity: float
    expected_date: Optional[str] = None


class MaterialIssueInfo(BaseModel):
    """Material availability info for an operation."""
    product_id: int
    product_sku: str
    product_name: Optional[str] = None
    quantity_required: float
    quantity_available: float
    quantity_short: float
    unit: str = "EA"
    consume_stage: str = "production"
    incoming_supply: Optional[IncomingSupplyInfo] = None


class CanStartResponse(BaseModel):
    """Response for quick can-start check."""
    can_start: bool
    blocking_issues: List[MaterialIssueInfo] = []


class OperationBlockingResponse(BaseModel):
    """Full blocking issues response for an operation."""
    operation_id: int
    operation_code: Optional[str] = None
    operation_name: Optional[str] = None
    can_start: bool
    blocking_issues: List[MaterialIssueInfo] = []
    material_issues: List[MaterialIssueInfo] = []
```

**Verification:**
- [ ] File created at `backend/app/schemas/operation_blocking.py`
- [ ] No Pydantic validation errors

**Commit Message:** `feat(API-402): add operation blocking Pydantic schemas`

---

### Step 6 of 8: Add API Endpoints

**Agent:** Backend Agent  
**Time:** 15 minutes  
**File to Modify:** `backend/app/api/v1/endpoints/operation_status.py`

**Add these endpoints to the existing operation_status.py router:**
```python
# Add these imports at the top
from app.schemas.operation_blocking import (
    CanStartResponse,
    OperationBlockingResponse,
)
from app.services.operation_blocking import (
    OperationBlockingError,
    can_operation_start,
    check_operation_blocking,
)


# Add these endpoints after the existing ones

@router.get(
    "/{po_id}/operations/{op_id}/can-start",
    response_model=CanStartResponse,
    summary="Check if operation can start"
)
def check_can_start(
    po_id: int,
    op_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Quick check if an operation can start based on material availability.
    
    Only checks materials for THIS operation's consume stage.
    For example, PRINT only checks production materials, not shipping materials.
    """
    try:
        result = can_operation_start(db, po_id, op_id)
        return result
    except OperationBlockingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/{po_id}/operations/{op_id}/blocking-issues",
    response_model=OperationBlockingResponse,
    summary="Get detailed blocking issues for operation"
)
def get_blocking_issues(
    po_id: int,
    op_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get detailed blocking issues for an operation.
    
    Returns all material checks, not just blocking ones.
    Useful for showing full material requirements and availability.
    """
    try:
        result = check_operation_blocking(db, po_id, op_id)
        return result
    except OperationBlockingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
```

**Verification:**
- [ ] Endpoints added to `backend/app/api/v1/endpoints/operation_status.py`
- [ ] App starts without errors

**Commit Message:** `feat(API-402): add operation blocking API endpoints`

---

### Step 7 of 8: Run Tests and Fix Issues

**Agent:** Backend Agent  
**Time:** 30 minutes

**Run the tests:**
```bash
cd backend
pytest tests/api/test_operation_blocking.py -v --tb=short
```

**Common issues to fix:**
1. Import paths may need adjustment
2. Factory function parameter names
3. Product.product_type field name (check actual model)

**Fix each failing test one at a time. Do NOT change test logic, only fix implementation bugs.**

**Verification:**
- [ ] All 10 tests pass
- [ ] No regressions: `pytest tests/api/ -v --tb=short -q`

**Commit Message:** `fix(API-402): resolve test failures`

---

### Step 8 of 8: Integration with Start Operation

**Agent:** Backend Agent  
**Time:** 15 minutes  
**File to Modify:** `backend/app/services/operation_status.py`

**Add material availability check to start_operation function:**

Find the `start_operation` function and add blocking check after the previous operation check:

```python
# Add import at top of file
from app.services.operation_blocking import check_operation_blocking

# In start_operation function, after the previous operation check, add:

    # Check material availability for this operation
    blocking_result = check_operation_blocking(db, po_id, op_id)
    if not blocking_result["can_start"]:
        short_materials = [m["product_sku"] for m in blocking_result["blocking_issues"]]
        raise OperationError(
            f"Operation blocked by material shortages: {', '.join(short_materials)}",
            400
        )
```

**Verification:**
- [ ] Blocking check added to start_operation
- [ ] Run full test suite: `pytest tests/api/test_operation_status.py tests/api/test_operation_blocking.py -v`

**Commit Message:** `feat(API-402): integrate blocking check into start operation`

---

## Final Checklist

- [ ] All 8 steps executed in order
- [ ] 10+ new tests passing
- [ ] No regressions in existing tests
- [ ] API endpoints accessible
- [ ] Start operation now checks material availability

---

## API Usage Examples

```bash
# Quick check if operation can start
curl -X GET "http://localhost:8000/api/v1/production-orders/15/operations/42/can-start" \
  -H "Authorization: Bearer <token>"

# Response when materials available:
{
  "can_start": true,
  "blocking_issues": []
}

# Response when materials short:
{
  "can_start": false,
  "blocking_issues": [
    {
      "product_id": 123,
      "product_sku": "BOX-SMALL",
      "product_name": "Small Shipping Box",
      "quantity_required": 50.0,
      "quantity_available": 10.0,
      "quantity_short": 40.0,
      "unit": "EA",
      "consume_stage": "shipping",
      "incoming_supply": {
        "purchase_order_id": 456,
        "purchase_order_code": "PO-2025-0089",
        "quantity": 100.0,
        "expected_date": "2025-01-05"
      }
    }
  ]
}

# Get detailed blocking issues
curl -X GET "http://localhost:8000/api/v1/production-orders/15/operations/42/blocking-issues" \
  -H "Authorization: Bearer <token>"
```

---

## Handoff to Next Ticket

**API-403: Double-Booking Validation**
- Prevent scheduling two operations on same resource at same time
- Check scheduled_start/scheduled_end for conflicts
- Return conflict details if resource already booked
