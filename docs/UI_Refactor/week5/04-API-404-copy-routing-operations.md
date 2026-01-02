# API-404: Copy Routing to PO Operations on Release

## Status: ✅ IMPLEMENTED (2025-12-30)

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

**Goal:** Auto-create ProductionOrderOperation records when a PO is released  
**Outcome:** POs automatically get their operation sequence from the product's routing

---

## Why This Matters

**Current behavior:** Production orders are created without operations. Users must manually track progress.

**After API-404:** When a PO status changes to "released", the system automatically creates operation records by copying from the product's routing template. Each operation has proper sequence, work center, and planned times.

**Real-world scenario:**
```
Product: Widget Pro has Routing RTG-WIDGET-PRO:
├── Op 10: PRINT    @ Print Station (240 min)
├── Op 20: CLEAN    @ Finishing (30 min)
├── Op 30: ASSEMBLE @ Assembly (60 min)
├── Op 40: QC       @ QC Station (15 min)
└── Op 50: PACK     @ Shipping (10 min)

When PO-2025-0089 is released:
├── System finds Widget Pro's active routing
├── Copies 5 operations to ProductionOrderOperation table
├── Links each to original RoutingOperation
└── PO now has trackable operation sequence
```

---

## Trigger Points

Operations should be copied when:

1. **PO status changes from draft → released** (primary)
2. **PO created directly in released status** (e.g., from MRP)
3. **Manual trigger** - endpoint to regenerate operations

Operations should NOT be copied when:
- PO already has operations (prevents duplicates)
- Product has no active routing (graceful skip)

---

## Data Mapping

| Routing (Template) | ProductionOrderOperation (Instance) |
|-------------------|-------------------------------------|
| routing_operation.sequence | sequence |
| routing_operation.operation_code | operation_code |
| routing_operation.operation_name | operation_name |
| routing_operation.work_center_id | work_center_id |
| routing_operation.setup_time_minutes | planned_setup_minutes |
| routing_operation.run_time_minutes × po.quantity | planned_run_minutes |
| routing_operation.id | routing_operation_id |
| - | status = 'pending' |
| - | resource_id = NULL |

---

## Endpoints to Create/Modify

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/production-orders/{po_id}/release | Release PO (triggers operation copy) |
| POST | /api/v1/production-orders/{po_id}/operations/generate | Manual operation generation |
| GET | /api/v1/products/{product_id}/routing | Get product's active routing |

---

## Step-by-Step Execution

---

### Step 1 of 7: Write Failing Tests First

**Agent:** Test Agent  
**Time:** 30 minutes  
**Directory:** `backend/tests/api/`

**File to Create:** `backend/tests/api/test_routing_operations.py`
```python
"""
Tests for routing to PO operations generation.

TDD: Write tests first, then implement to make them pass.
"""
import pytest
from decimal import Decimal

from tests.factories import (
    create_test_product,
    create_test_production_order,
    create_test_work_center,
    create_test_routing,
    create_test_routing_operation,
)


class TestReleaseProductionOrder:
    """Tests for POST /api/v1/production-orders/{po_id}/release"""

    @pytest.mark.api
    def test_release_creates_operations(self, client, db, admin_token):
        """Releasing PO creates operations from routing."""
        # Setup: Product with routing
        product = create_test_product(db, sku="RTG-001", name="Widget")
        
        wc_print = create_test_work_center(db, code="WC-PRINT-RTG1", name="Print Station")
        wc_clean = create_test_work_center(db, code="WC-CLEAN-RTG1", name="Cleaning")
        wc_pack = create_test_work_center(db, code="WC-PACK-RTG1", name="Packing")
        
        routing = create_test_routing(db, product=product, code="RTG-WIDGET")
        create_test_routing_operation(
            db, routing=routing, work_center=wc_print,
            sequence=10, operation_code="PRINT", operation_name="3D Print",
            run_time_minutes=240, setup_time_minutes=5
        )
        create_test_routing_operation(
            db, routing=routing, work_center=wc_clean,
            sequence=20, operation_code="CLEAN", operation_name="Post-Print Clean",
            run_time_minutes=30, setup_time_minutes=0
        )
        create_test_routing_operation(
            db, routing=routing, work_center=wc_pack,
            sequence=30, operation_code="PACK", operation_name="Package",
            run_time_minutes=10, setup_time_minutes=0
        )
        
        # Setup: PO in draft status
        po = create_test_production_order(db, product=product, qty=10, status="draft")
        po.routing_id = routing.id
        db.commit()
        
        # Verify no operations yet
        assert len(po.operations) == 0

        # Execute - release the PO
        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "released"
        assert data["operations_created"] == 3
        
        # Refresh from DB
        db.refresh(po)
        assert po.status == "released"
        assert len(po.operations) == 3
        
        # Verify operation details
        ops = sorted(po.operations, key=lambda x: x.sequence)
        assert ops[0].sequence == 10
        assert ops[0].operation_code == "PRINT"
        assert ops[0].work_center_id == wc_print.id
        assert ops[0].status == "pending"
        
        assert ops[1].sequence == 20
        assert ops[1].operation_code == "CLEAN"
        
        assert ops[2].sequence == 30
        assert ops[2].operation_code == "PACK"

    @pytest.mark.api
    def test_release_calculates_run_time(self, client, db, admin_token):
        """Run time is multiplied by PO quantity."""
        product = create_test_product(db, sku="RTG-002")
        wc = create_test_work_center(db, code="WC-RTG2", name="Work Center")
        
        routing = create_test_routing(db, product=product)
        create_test_routing_operation(
            db, routing=routing, work_center=wc,
            sequence=10, operation_code="WORK",
            run_time_minutes=10,  # 10 min per unit
            setup_time_minutes=15
        )
        
        po = create_test_production_order(db, product=product, qty=20, status="draft")
        po.routing_id = routing.id
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        
        db.refresh(po)
        op = po.operations[0]
        
        # Run time = 10 min/unit × 20 units = 200 min
        assert float(op.planned_run_minutes) == 200.0
        # Setup time stays the same
        assert float(op.planned_setup_minutes) == 15.0

    @pytest.mark.api
    def test_release_no_routing_still_releases(self, client, db, admin_token):
        """PO without routing still releases, just no operations created."""
        product = create_test_product(db, sku="RTG-003")
        # NO routing for this product
        
        po = create_test_production_order(db, product=product, qty=10, status="draft")
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "released"
        assert data["operations_created"] == 0
        assert "no routing" in data.get("message", "").lower() or data["operations_created"] == 0

    @pytest.mark.api
    def test_release_already_released(self, client, db, admin_token):
        """Cannot release already released PO."""
        product = create_test_product(db, sku="RTG-004")
        po = create_test_production_order(db, product=product, qty=10, status="released")
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_release_with_existing_operations_skips(self, client, db, admin_token):
        """If PO already has operations, don't create duplicates."""
        product = create_test_product(db, sku="RTG-005")
        wc = create_test_work_center(db, code="WC-RTG5", name="Work Center")
        
        routing = create_test_routing(db, product=product)
        create_test_routing_operation(
            db, routing=routing, work_center=wc,
            sequence=10, operation_code="WORK", run_time_minutes=60
        )
        
        po = create_test_production_order(db, product=product, qty=10, status="draft")
        po.routing_id = routing.id
        
        # Manually add an operation (simulating prior generation)
        from app.models.production_order import ProductionOrderOperation
        existing_op = ProductionOrderOperation(
            production_order_id=po.id,
            work_center_id=wc.id,
            sequence=10,
            operation_code="WORK",
            status="pending",
            planned_setup_minutes=0,
            planned_run_minutes=60
        )
        db.add(existing_op)
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        
        # Should still release but not add more operations
        db.refresh(po)
        assert po.status == "released"
        assert len(po.operations) == 1  # Still just 1


class TestGenerateOperations:
    """Tests for POST /api/v1/production-orders/{po_id}/operations/generate"""

    @pytest.mark.api
    def test_generate_operations_manual(self, client, db, admin_token):
        """Manually trigger operation generation."""
        product = create_test_product(db, sku="GEN-001")
        wc = create_test_work_center(db, code="WC-GEN1", name="Work Center")
        
        routing = create_test_routing(db, product=product)
        create_test_routing_operation(
            db, routing=routing, work_center=wc,
            sequence=10, operation_code="WORK", run_time_minutes=30
        )
        
        # PO already released but no operations
        po = create_test_production_order(db, product=product, qty=5, status="released")
        po.routing_id = routing.id
        db.commit()
        
        assert len(po.operations) == 0

        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/generate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.json()["operations_created"] == 1
        
        db.refresh(po)
        assert len(po.operations) == 1

    @pytest.mark.api
    def test_generate_operations_force_regenerate(self, client, db, admin_token):
        """Force regenerate replaces existing operations."""
        product = create_test_product(db, sku="GEN-002")
        wc = create_test_work_center(db, code="WC-GEN2", name="Work Center")
        
        routing = create_test_routing(db, product=product)
        create_test_routing_operation(
            db, routing=routing, work_center=wc,
            sequence=10, operation_code="WORK", run_time_minutes=30
        )
        create_test_routing_operation(
            db, routing=routing, work_center=wc,
            sequence=20, operation_code="FINISH", run_time_minutes=15
        )
        
        po = create_test_production_order(db, product=product, qty=5, status="released")
        po.routing_id = routing.id
        
        # Add single old operation
        from app.models.production_order import ProductionOrderOperation
        old_op = ProductionOrderOperation(
            production_order_id=po.id,
            work_center_id=wc.id,
            sequence=99,
            operation_code="OLD",
            status="pending",
            planned_setup_minutes=0,
            planned_run_minutes=999
        )
        db.add(old_op)
        db.commit()
        
        assert len(po.operations) == 1

        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/generate",
            params={"force": True},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.json()["operations_created"] == 2
        
        db.refresh(po)
        assert len(po.operations) == 2
        
        # Verify old operation is gone
        ops = sorted(po.operations, key=lambda x: x.sequence)
        assert ops[0].operation_code == "WORK"
        assert ops[1].operation_code == "FINISH"


class TestGetProductRouting:
    """Tests for GET /api/v1/products/{product_id}/routing"""

    @pytest.mark.api
    def test_get_product_routing(self, client, db, admin_token):
        """Get active routing for a product."""
        product = create_test_product(db, sku="PROD-RTG-001")
        wc = create_test_work_center(db, code="WC-PROD-RTG", name="Work Center")
        
        routing = create_test_routing(
            db, product=product,
            code="RTG-PROD-001", name="Standard Routing"
        )
        create_test_routing_operation(
            db, routing=routing, work_center=wc,
            sequence=10, operation_code="PRINT",
            run_time_minutes=60, setup_time_minutes=5
        )
        create_test_routing_operation(
            db, routing=routing, work_center=wc,
            sequence=20, operation_code="PACK",
            run_time_minutes=10, setup_time_minutes=0
        )
        db.commit()

        response = client.get(
            f"/api/v1/products/{product.id}/routing",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        
        assert data["routing_code"] == "RTG-PROD-001"
        assert data["routing_name"] == "Standard Routing"
        assert len(data["operations"]) == 2
        assert data["operations"][0]["operation_code"] == "PRINT"
        assert data["operations"][1]["operation_code"] == "PACK"

    @pytest.mark.api
    def test_get_product_routing_none(self, client, db, admin_token):
        """Product with no routing returns 404."""
        product = create_test_product(db, sku="PROD-RTG-002")
        db.commit()

        response = client.get(
            f"/api/v1/products/{product.id}/routing",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 404
        assert "routing" in response.json()["detail"].lower()


class TestRoutingOperationLink:
    """Tests for routing_operation_id linkage."""

    @pytest.mark.api
    def test_operations_link_to_routing(self, client, db, admin_token):
        """Generated operations link back to routing operations."""
        product = create_test_product(db, sku="LINK-001")
        wc = create_test_work_center(db, code="WC-LINK1", name="Work Center")
        
        routing = create_test_routing(db, product=product)
        rtg_op = create_test_routing_operation(
            db, routing=routing, work_center=wc,
            sequence=10, operation_code="WORK", run_time_minutes=30
        )
        
        po = create_test_production_order(db, product=product, qty=5, status="draft")
        po.routing_id = routing.id
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        
        db.refresh(po)
        po_op = po.operations[0]
        
        # Should link to routing operation
        assert po_op.routing_operation_id == rtg_op.id
```

**Verification:**
- [ ] File created at `backend/tests/api/test_routing_operations.py`
- [ ] Run `pytest backend/tests/api/test_routing_operations.py -v`
- [ ] Tests FAIL (expected - TDD)

**Commit Message:** `test(API-404): add failing tests for routing to PO operations`

---

### Step 2 of 7: Create Operation Generation Service

**Agent:** Backend Agent  
**Time:** 30 minutes  
**Directory:** `backend/app/services/`

**File to Create:** `backend/app/services/operation_generation.py`
```python
"""
Service layer for generating production order operations from routings.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.production_order import ProductionOrder, ProductionOrderOperation
from app.models.manufacturing import Routing, RoutingOperation


class OperationGenerationError(Exception):
    """Custom exception for operation generation errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def get_active_routing(db: Session, product_id: int) -> Optional[Routing]:
    """
    Get the active routing for a product.
    
    Returns the first active routing found, or None if no routing exists.
    """
    return db.query(Routing).filter(
        Routing.product_id == product_id,
        Routing.is_active == True  # noqa: E712
    ).first()


def get_routing_operations(db: Session, routing_id: int) -> List[RoutingOperation]:
    """
    Get operations for a routing, ordered by sequence.
    """
    return db.query(RoutingOperation).filter(
        RoutingOperation.routing_id == routing_id,
        RoutingOperation.is_active == True  # noqa: E712
    ).order_by(RoutingOperation.sequence).all()


def generate_operations_from_routing(
    db: Session,
    po: ProductionOrder,
    routing: Routing,
    quantity: Decimal
) -> List[ProductionOrderOperation]:
    """
    Generate ProductionOrderOperation records from a routing.
    
    Args:
        db: Database session
        po: Production order to generate operations for
        routing: Routing template to copy from
        quantity: Production quantity (for calculating run times)
    
    Returns:
        List of created ProductionOrderOperation records
    """
    routing_ops = get_routing_operations(db, routing.id)
    
    created_ops = []
    for rtg_op in routing_ops:
        # Calculate planned run time based on quantity
        # run_time_minutes from routing is per-unit
        planned_run = rtg_op.run_time_minutes * quantity if rtg_op.run_time_minutes else Decimal("0")
        
        po_op = ProductionOrderOperation(
            production_order_id=po.id,
            routing_operation_id=rtg_op.id,
            work_center_id=rtg_op.work_center_id,
            sequence=rtg_op.sequence,
            operation_code=rtg_op.operation_code,
            operation_name=rtg_op.operation_name,
            status='pending',
            planned_setup_minutes=rtg_op.setup_time_minutes or Decimal("0"),
            planned_run_minutes=planned_run,
        )
        db.add(po_op)
        created_ops.append(po_op)
    
    db.flush()
    return created_ops


def release_production_order(
    db: Session,
    po_id: int
) -> Tuple[ProductionOrder, int, str]:
    """
    Release a production order and generate operations from routing.
    
    Args:
        db: Database session
        po_id: Production order ID
    
    Returns:
        Tuple of (ProductionOrder, operations_created_count, message)
    
    Raises:
        OperationGenerationError: If PO not found or already released
    """
    po = db.get(ProductionOrder, po_id)
    if not po:
        raise OperationGenerationError(f"Production order {po_id} not found", 404)
    
    if po.status not in ('draft',):
        raise OperationGenerationError(
            f"Production order {po.code} is already {po.status}, cannot release",
            400
        )
    
    ops_created = 0
    message = ""
    
    # Only generate operations if PO doesn't already have any
    if len(po.operations) == 0:
        # Get routing - either explicitly set or from product
        routing = None
        if po.routing_id:
            routing = db.get(Routing, po.routing_id)
        
        if not routing:
            routing = get_active_routing(db, po.product_id)
        
        if routing:
            quantity = po.quantity_ordered or Decimal("1")
            created_ops = generate_operations_from_routing(db, po, routing, quantity)
            ops_created = len(created_ops)
            message = f"Created {ops_created} operations from routing {routing.code}"
            
            # Also set routing_id on PO if not already set
            if not po.routing_id:
                po.routing_id = routing.id
        else:
            message = "No routing found for product, released without operations"
    else:
        message = "Operations already exist, skipped generation"
    
    # Update PO status
    po.status = 'released'
    po.released_at = datetime.utcnow()
    po.updated_at = datetime.utcnow()
    
    db.flush()
    return po, ops_created, message


def generate_operations_manual(
    db: Session,
    po_id: int,
    force: bool = False
) -> Tuple[ProductionOrder, int, str]:
    """
    Manually generate operations for a PO.
    
    Args:
        db: Database session
        po_id: Production order ID
        force: If True, delete existing operations first
    
    Returns:
        Tuple of (ProductionOrder, operations_created_count, message)
    
    Raises:
        OperationGenerationError: If PO not found or no routing
    """
    po = db.get(ProductionOrder, po_id)
    if not po:
        raise OperationGenerationError(f"Production order {po_id} not found", 404)
    
    # Get routing
    routing = None
    if po.routing_id:
        routing = db.get(Routing, po.routing_id)
    
    if not routing:
        routing = get_active_routing(db, po.product_id)
    
    if not routing:
        raise OperationGenerationError(
            f"No routing found for product {po.product.sku if po.product else 'unknown'}",
            404
        )
    
    # Handle existing operations
    if len(po.operations) > 0:
        if force:
            # Delete existing operations
            for op in po.operations:
                db.delete(op)
            db.flush()
        else:
            return po, 0, "Operations already exist, use force=true to regenerate"
    
    # Generate operations
    quantity = po.quantity_ordered or Decimal("1")
    created_ops = generate_operations_from_routing(db, po, routing, quantity)
    
    # Set routing_id on PO if not already set
    if not po.routing_id:
        po.routing_id = routing.id
    
    po.updated_at = datetime.utcnow()
    db.flush()
    
    return po, len(created_ops), f"Generated {len(created_ops)} operations from routing {routing.code}"


def get_product_routing_details(
    db: Session,
    product_id: int
) -> dict:
    """
    Get routing details for a product.
    
    Returns:
        Dict with routing info and operations
    
    Raises:
        OperationGenerationError: If product or routing not found
    """
    product = db.get(Product, product_id)
    if not product:
        raise OperationGenerationError(f"Product {product_id} not found", 404)
    
    routing = get_active_routing(db, product_id)
    if not routing:
        raise OperationGenerationError(
            f"No active routing found for product {product.sku}",
            404
        )
    
    operations = get_routing_operations(db, routing.id)
    
    return {
        "product_id": product.id,
        "product_sku": product.sku,
        "product_name": product.name,
        "routing_id": routing.id,
        "routing_code": routing.code,
        "routing_name": routing.name,
        "operations": [
            {
                "id": op.id,
                "sequence": op.sequence,
                "operation_code": op.operation_code,
                "operation_name": op.operation_name,
                "work_center_id": op.work_center_id,
                "work_center_code": op.work_center.code if op.work_center else None,
                "work_center_name": op.work_center.name if op.work_center else None,
                "setup_time_minutes": float(op.setup_time_minutes or 0),
                "run_time_minutes": float(op.run_time_minutes or 0),
            }
            for op in operations
        ]
    }
```

**Verification:**
- [ ] File created at `backend/app/services/operation_generation.py`
- [ ] No import errors

**Commit Message:** `feat(API-404): add operation generation service layer`

---

### Step 3 of 7: Create Pydantic Schemas

**Agent:** Backend Agent  
**Time:** 10 minutes  
**Directory:** `backend/app/schemas/`

**File to Create:** `backend/app/schemas/routing_operations.py`
```python
"""
Schemas for routing and operation generation endpoints.
"""
from typing import Optional, List
from pydantic import BaseModel


class RoutingOperationInfo(BaseModel):
    """Info about a routing operation."""
    id: int
    sequence: int
    operation_code: Optional[str] = None
    operation_name: Optional[str] = None
    work_center_id: int
    work_center_code: Optional[str] = None
    work_center_name: Optional[str] = None
    setup_time_minutes: float = 0
    run_time_minutes: float = 0


class ProductRoutingResponse(BaseModel):
    """Response for product routing query."""
    product_id: int
    product_sku: str
    product_name: Optional[str] = None
    routing_id: int
    routing_code: str
    routing_name: Optional[str] = None
    operations: List[RoutingOperationInfo] = []


class ReleaseResponse(BaseModel):
    """Response for PO release."""
    production_order_id: int
    production_order_code: str
    status: str
    operations_created: int
    message: Optional[str] = None


class GenerateOperationsResponse(BaseModel):
    """Response for operation generation."""
    production_order_id: int
    production_order_code: str
    operations_created: int
    message: Optional[str] = None
```

**Verification:**
- [ ] File created at `backend/app/schemas/routing_operations.py`
- [ ] No Pydantic validation errors

**Commit Message:** `feat(API-404): add routing operations Pydantic schemas`

---

### Step 4 of 7: Add Release Endpoint to Production Orders Router

**Agent:** Backend Agent  
**Time:** 15 minutes  
**File to Modify:** `backend/app/api/v1/endpoints/production_orders.py`

**Add these imports and endpoints:**
```python
# Add to imports
from app.schemas.routing_operations import (
    ReleaseResponse,
    GenerateOperationsResponse,
)
from app.services.operation_generation import (
    OperationGenerationError,
    release_production_order,
    generate_operations_manual,
)


# Add these endpoints

@router.post(
    "/{po_id}/release",
    response_model=ReleaseResponse,
    summary="Release a production order"
)
def release_po(
    po_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Release a production order.
    
    When released:
    - Status changes from draft to released
    - Operations are generated from the product's routing
    - PO is ready for scheduling and production
    """
    try:
        po, ops_created, message = release_production_order(db, po_id)
        db.commit()
    except OperationGenerationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    
    return ReleaseResponse(
        production_order_id=po.id,
        production_order_code=po.code,
        status=po.status,
        operations_created=ops_created,
        message=message
    )


@router.post(
    "/{po_id}/operations/generate",
    response_model=GenerateOperationsResponse,
    summary="Generate operations from routing"
)
def generate_operations(
    po_id: int,
    force: bool = Query(False, description="Delete existing operations first"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Manually generate operations for a production order.
    
    Use force=true to replace existing operations.
    """
    try:
        po, ops_created, message = generate_operations_manual(db, po_id, force)
        db.commit()
    except OperationGenerationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    
    return GenerateOperationsResponse(
        production_order_id=po.id,
        production_order_code=po.code,
        operations_created=ops_created,
        message=message
    )
```

**Verification:**
- [ ] Endpoints added to production_orders.py
- [ ] Import Query from fastapi if not already

**Commit Message:** `feat(API-404): add release and generate operations endpoints`

---

### Step 5 of 7: Add Product Routing Endpoint

**Agent:** Backend Agent  
**Time:** 10 minutes  
**File to Modify:** `backend/app/api/v1/endpoints/products.py` (or create if needed)

If products.py exists, add:
```python
# Add to imports
from app.schemas.routing_operations import ProductRoutingResponse
from app.services.operation_generation import (
    OperationGenerationError,
    get_product_routing_details,
)


# Add endpoint
@router.get(
    "/{product_id}/routing",
    response_model=ProductRoutingResponse,
    summary="Get product routing"
)
def get_product_routing(
    product_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get the active routing for a product.
    
    Returns the routing template with all operations.
    """
    try:
        result = get_product_routing_details(db, product_id)
    except OperationGenerationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    
    return result
```

If products.py doesn't exist, check what file handles product endpoints and add there.

**Verification:**
- [ ] Endpoint added
- [ ] App starts without errors

**Commit Message:** `feat(API-404): add product routing endpoint`

---

### Step 6 of 7: Run Tests and Fix Issues

**Agent:** Backend Agent  
**Time:** 30 minutes

**Run the tests:**
```bash
cd backend
pytest tests/api/test_routing_operations.py -v --tb=short
```

**Common issues to fix:**
1. Import paths
2. Factory function parameters
3. Model field name differences

**Verification:**
- [ ] All 10 tests pass
- [ ] No regressions: `pytest tests/api/ -v --tb=short -q`

**Commit Message:** `fix(API-404): resolve test failures`

---

### Step 7 of 7: Integration Test

**Agent:** Test Agent  
**Time:** 15 minutes  
**File to Modify:** `backend/tests/api/test_routing_operations.py`

**Add integration test at the end:**
```python
class TestFullWorkflow:
    """Integration test for complete routing workflow."""

    @pytest.mark.integration
    def test_full_routing_workflow(self, client, db, admin_token):
        """
        Complete workflow:
        1. Create product with routing
        2. Create draft PO
        3. Release PO (operations auto-created)
        4. Verify operations have correct data
        """
        # Setup: Product with 3-operation routing
        product = create_test_product(db, sku="FULL-WF-001", name="Full Workflow Widget")
        
        wc_print = create_test_work_center(db, code="WC-FWF-PRINT", name="Print")
        wc_qc = create_test_work_center(db, code="WC-FWF-QC", name="QC")
        wc_ship = create_test_work_center(db, code="WC-FWF-SHIP", name="Ship")
        
        routing = create_test_routing(db, product=product, code="RTG-FWF")
        rtg_print = create_test_routing_operation(
            db, routing=routing, work_center=wc_print,
            sequence=10, operation_code="PRINT", operation_name="3D Print",
            run_time_minutes=24, setup_time_minutes=5  # 24 min/unit
        )
        rtg_qc = create_test_routing_operation(
            db, routing=routing, work_center=wc_qc,
            sequence=20, operation_code="QC", operation_name="Quality Check",
            run_time_minutes=2, setup_time_minutes=0  # 2 min/unit
        )
        rtg_ship = create_test_routing_operation(
            db, routing=routing, work_center=wc_ship,
            sequence=30, operation_code="SHIP", operation_name="Package & Ship",
            run_time_minutes=1, setup_time_minutes=0  # 1 min/unit
        )
        db.commit()
        
        # Step 1: Check routing via API
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get(
            f"/api/v1/products/{product.id}/routing",
            headers=headers
        )
        assert response.status_code == 200
        routing_data = response.json()
        assert len(routing_data["operations"]) == 3
        
        # Step 2: Create draft PO via API (or use factory)
        po = create_test_production_order(
            db, product=product, qty=10, status="draft"
        )
        po.routing_id = routing.id
        db.commit()
        
        # Step 3: Release PO
        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers=headers
        )
        assert response.status_code == 200
        release_data = response.json()
        
        assert release_data["status"] == "released"
        assert release_data["operations_created"] == 3
        
        # Step 4: Verify operations
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations",
            headers=headers
        )
        assert response.status_code == 200
        ops = response.json()
        
        assert len(ops) == 3
        
        # Verify PRINT operation
        print_op = next(o for o in ops if o["operation_code"] == "PRINT")
        assert print_op["sequence"] == 10
        assert print_op["work_center_id"] == wc_print.id
        assert float(print_op["planned_setup_minutes"]) == 5.0
        assert float(print_op["planned_run_minutes"]) == 240.0  # 24 min × 10 qty
        
        # Verify QC operation
        qc_op = next(o for o in ops if o["operation_code"] == "QC")
        assert float(qc_op["planned_run_minutes"]) == 20.0  # 2 min × 10 qty
        
        # Verify SHIP operation
        ship_op = next(o for o in ops if o["operation_code"] == "SHIP")
        assert float(ship_op["planned_run_minutes"]) == 10.0  # 1 min × 10 qty
```

**Verification:**
- [ ] Integration test passes
- [ ] Full test suite passes

**Commit Message:** `test(API-404): add full workflow integration test`

---

## Final Checklist

- [ ] All 7 steps executed in order
- [ ] 10+ new tests passing
- [ ] No regressions in existing tests
- [ ] API endpoints accessible
- [ ] Release PO auto-creates operations

---

## API Usage Examples

```bash
# Get product routing
curl -X GET "http://localhost:8000/api/v1/products/15/routing" \
  -H "Authorization: Bearer <token>"

# Release a production order
curl -X POST "http://localhost:8000/api/v1/production-orders/42/release" \
  -H "Authorization: Bearer <token>"

# Response:
{
  "production_order_id": 42,
  "production_order_code": "PO-2025-0042",
  "status": "released",
  "operations_created": 5,
  "message": "Created 5 operations from routing RTG-WIDGET-PRO"
}

# Manually regenerate operations
curl -X POST "http://localhost:8000/api/v1/production-orders/42/operations/generate?force=true" \
  -H "Authorization: Bearer <token>"
```

---

## Week 5 Backend Complete

With API-404 done, all backend specs for Week 5 are complete:

| Ticket | Description | Status |
|--------|-------------|--------|
| API-401 | Operation status transitions | ✅ |
| API-402 | Operation-level blocking check | 📝 Spec ready |
| API-403 | Double-booking validation | 📝 Spec ready |
| API-404 | Copy routing to PO operations | 📝 Spec ready |

**Next:** UI specs (UI-401 through UI-404) for the frontend components.
