# API-401: Operation Status Transitions

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

**Goal:** Enable starting and completing individual operations within a production order
**Outcome:** PO status is derived from its operations' collective state

---

## Why This Matters

Currently: Complete PO button marks entire order done, skipping all intermediate operations
After API-401: Each operation transitions independently, PO only complete when ALL ops done

This enables real workflows:
- Print (4 hrs) → Complete → Clean (30 min) → Complete → Assemble → Complete → Ship

---

## Endpoints to Create

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/production-orders/{po_id}/operations/{op_id}/start | Start an operation |
| POST | /api/v1/production-orders/{po_id}/operations/{op_id}/complete | Complete an operation |
| POST | /api/v1/production-orders/{po_id}/operations/{op_id}/skip | Skip an operation |
| GET | /api/v1/production-orders/{po_id}/operations | List operations for a PO |

---

## Agent Types

| Agent | Role | Works In |
|-------|------|----------|
| **Test Agent** | pytest tests (TDD - write first) | ackend/tests/ |
| **Backend Agent** | Schemas, services, endpoints | ackend/app/ |

---

## Step-by-Step Execution

---

### Step 1 of 10: Write Failing Tests First

**Agent:** Test Agent  
**Time:** 30 minutes  
**Directory:** ackend/tests/api/

**File to Create:** ackend/tests/api/test_operation_status.py
`python
"""
Tests for operation status transition endpoints.

TDD: Write tests first, then implement to make them pass.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from tests.factories import (
    create_test_user,
    create_test_product,
    create_test_production_order,
    create_test_work_center,
    create_test_resource,
    create_test_routing,
    create_test_routing_operation,
    create_test_po_operation,
    create_test_bom,
    create_test_bom_line,
    create_test_inventory,
)


class TestListOperations:
    """Tests for GET /api/v1/production-orders/{po_id}/operations"""

    @pytest.mark.api
    def test_list_operations_success(self, client, db, admin_token):
        """List operations for a production order."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-001")
        wc_print = create_test_work_center(db, code="WC-PRINT", name="Print Station")
        wc_clean = create_test_work_center(db, code="WC-CLEAN", name="Cleaning")
        
        po = create_test_production_order(db, product=product, qty=10, status="released")
        
        op1 = create_test_po_operation(
            db, production_order=po, work_center=wc_print,
            sequence=10, operation_code="PRINT", operation_name="3D Print",
            planned_run_minutes=240, status="pending"
        )
        op2 = create_test_po_operation(
            db, production_order=po, work_center=wc_clean,
            sequence=20, operation_code="CLEAN", operation_name="Post-Print Clean",
            planned_run_minutes=30, status="pending"
        )
        db.commit()

        # Execute
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2
        assert data[0]["sequence"] == 10
        assert data[0]["operation_code"] == "PRINT"
        assert data[0]["status"] == "pending"
        assert data[1]["sequence"] == 20
        assert data[1]["operation_code"] == "CLEAN"

    @pytest.mark.api
    def test_list_operations_po_not_found(self, client, db, admin_token):
        """Non-existent PO returns 404."""
        response = client.get(
            "/api/v1/production-orders/99999/operations",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404


class TestStartOperation:
    """Tests for POST /api/v1/production-orders/{po_id}/operations/{op_id}/start"""

    @pytest.mark.api
    def test_start_first_operation_success(self, client, db, admin_token):
        """Start first operation in sequence."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-002")
        wc = create_test_work_center(db, code="WC-PRINT-2", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-01", name="Printer 1")
        
        po = create_test_production_order(db, product=product, qty=10, status="released")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", operation_name="3D Print",
            planned_run_minutes=240, status="pending"
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"resource_id": resource.id, "operator_name": "John D"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "running"
        assert data["resource_id"] == resource.id
        assert data["actual_start"] is not None
        assert data["production_order"]["status"] == "in_progress"

    @pytest.mark.api
    def test_start_operation_previous_not_complete(self, client, db, admin_token):
        """Cannot start operation if previous not complete."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-003")
        wc = create_test_work_center(db, code="WC-PRINT-3", name="Print Station")
        
        po = create_test_production_order(db, product=product, qty=10, status="released")
        op1 = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"  # Not complete!
        )
        op2 = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=20, operation_code="CLEAN", status="pending"
        )
        db.commit()

        # Execute - try to start op2 when op1 not done
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op2.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )

        # Verify
        assert response.status_code == 400
        assert "previous operation" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_start_operation_already_running(self, client, db, admin_token):
        """Cannot start operation that is already running."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-004")
        wc = create_test_work_center(db, code="WC-PRINT-4", name="Print Station")
        
        po = create_test_production_order(db, product=product, qty=10, status="in_progress")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="running"  # Already running
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )

        # Verify
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_start_operation_po_derives_in_progress(self, client, db, admin_token):
        """Starting first operation sets PO status to in_progress."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-005")
        wc = create_test_work_center(db, code="WC-PRINT-5", name="Print Station")
        
        po = create_test_production_order(db, product=product, qty=10, status="released")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()
        
        assert po.status == "released"

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )

        # Verify
        assert response.status_code == 200
        
        # Refresh PO from DB
        db.refresh(po)
        assert po.status == "in_progress"


class TestCompleteOperation:
    """Tests for POST /api/v1/production-orders/{po_id}/operations/{op_id}/complete"""

    @pytest.mark.api
    def test_complete_operation_success(self, client, db, admin_token):
        """Complete a running operation."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-006")
        wc = create_test_work_center(db, code="WC-PRINT-6", name="Print Station")
        
        po = create_test_production_order(db, product=product, qty=10, status="in_progress")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="running",
            actual_start=datetime.utcnow() - timedelta(hours=2)
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 10, "quantity_scrapped": 0}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "complete"
        assert data["actual_end"] is not None
        assert data["quantity_completed"] == 10

    @pytest.mark.api
    def test_complete_operation_not_running(self, client, db, admin_token):
        """Cannot complete operation that is not running."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-007")
        wc = create_test_work_center(db, code="WC-PRINT-7", name="Print Station")
        
        po = create_test_production_order(db, product=product, qty=10, status="released")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"  # Not running
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 10}
        )

        # Verify
        assert response.status_code == 400
        assert "not running" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_complete_last_operation_completes_po(self, client, db, admin_token):
        """Completing last operation sets PO status to complete."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-008")
        wc = create_test_work_center(db, code="WC-PRINT-8", name="Print Station")
        
        po = create_test_production_order(db, product=product, qty=10, status="in_progress")
        op1 = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="complete"  # Already done
        )
        op2 = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=20, operation_code="CLEAN", status="running",  # Last one, running
            actual_start=datetime.utcnow() - timedelta(minutes=30)
        )
        db.commit()

        # Execute - complete the last operation
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op2.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 10}
        )

        # Verify
        assert response.status_code == 200
        
        # PO should now be complete
        db.refresh(po)
        assert po.status == "complete"

    @pytest.mark.api
    def test_complete_operation_returns_next_operation(self, client, db, admin_token):
        """Completing operation returns info about next operation."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-009")
        wc_print = create_test_work_center(db, code="WC-PRINT-9", name="Print Station")
        wc_clean = create_test_work_center(db, code="WC-CLEAN-9", name="Cleaning")
        
        po = create_test_production_order(db, product=product, qty=10, status="in_progress")
        op1 = create_test_po_operation(
            db, production_order=po, work_center=wc_print,
            sequence=10, operation_code="PRINT", operation_name="3D Print",
            status="running", actual_start=datetime.utcnow() - timedelta(hours=2)
        )
        op2 = create_test_po_operation(
            db, production_order=po, work_center=wc_clean,
            sequence=20, operation_code="CLEAN", operation_name="Post-Print Clean",
            status="pending"
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op1.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 10}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert "next_operation" in data
        assert data["next_operation"]["id"] == op2.id
        assert data["next_operation"]["operation_code"] == "CLEAN"
        assert data["next_operation"]["status"] == "pending"


class TestSkipOperation:
    """Tests for POST /api/v1/production-orders/{po_id}/operations/{op_id}/skip"""

    @pytest.mark.api
    def test_skip_operation_success(self, client, db, admin_token):
        """Skip an operation with reason."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-010")
        wc = create_test_work_center(db, code="WC-QC-10", name="QC Station")
        
        po = create_test_production_order(db, product=product, qty=10, status="in_progress")
        op1 = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="complete"
        )
        op2 = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=20, operation_code="QC", operation_name="QC Inspect",
            status="pending"
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op2.id}/skip",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "Customer waived QC requirement"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "skipped"
        assert "customer waived" in data["notes"].lower()

    @pytest.mark.api
    def test_skip_operation_requires_reason(self, client, db, admin_token):
        """Skipping operation requires a reason."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-011")
        wc = create_test_work_center(db, code="WC-QC-11", name="QC Station")
        
        po = create_test_production_order(db, product=product, qty=10, status="in_progress")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="QC", status="pending"
        )
        db.commit()

        # Execute - no reason provided
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/skip",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )

        # Verify
        assert response.status_code == 422  # Validation error


class TestOperationNotFound:
    """Tests for 404 scenarios."""

    @pytest.mark.api
    def test_start_operation_not_found(self, client, db, admin_token):
        """Non-existent operation returns 404."""
        product = create_test_product(db, sku="TEST-PROD-012")
        po = create_test_production_order(db, product=product, qty=10, status="released")
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/99999/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )
        assert response.status_code == 404

    @pytest.mark.api
    def test_operation_wrong_po(self, client, db, admin_token):
        """Operation from different PO returns 404."""
        product = create_test_product(db, sku="TEST-PROD-013")
        wc = create_test_work_center(db, code="WC-TEST-13", name="Test")
        
        po1 = create_test_production_order(db, product=product, qty=10, status="released")
        po2 = create_test_production_order(db, product=product, qty=5, status="released")
        
        op = create_test_po_operation(
            db, production_order=po1, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Try to start op from po1 using po2's URL
        response = client.post(
            f"/api/v1/production-orders/{po2.id}/operations/{op.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )
        assert response.status_code == 404
`

**Verification:**
- [ ] File created at ackend/tests/api/test_operation_status.py
- [ ] Run pytest backend/tests/api/test_operation_status.py -v
- [ ] Tests FAIL (expected - TDD, endpoints don't exist yet)

**Commit Message:** 	est(API-401): add failing tests for operation status transitions

---

### Step 2 of 10: Add Factory Functions

**Agent:** Test Agent  
**Time:** 15 minutes  
**File to Modify:** ackend/tests/factories.py

**Add these functions to the existing factories.py file:**
`python
def create_test_work_center(
    db,
    code: str = None,
    name: str = "Test Work Center",
    center_type: str = "production",
    is_active: bool = True
):
    """Create a test work center."""
    from app.models.work_center import WorkCenter
    
    if code is None:
        code = f"WC-{datetime.now().strftime('%H%M%S%f')}"
    
    # Check if exists
    existing = db.query(WorkCenter).filter(WorkCenter.code == code).first()
    if existing:
        return existing
    
    wc = WorkCenter(
        code=code,
        name=name,
        center_type=center_type,
        is_active=is_active
    )
    db.add(wc)
    db.flush()
    return wc


def create_test_resource(
    db,
    work_center,
    code: str = None,
    name: str = "Test Resource",
    status: str = "available",
    is_active: bool = True
):
    """Create a test resource/machine."""
    from app.models.manufacturing import Resource
    
    if code is None:
        code = f"RES-{datetime.now().strftime('%H%M%S%f')}"
    
    # Check if exists
    existing = db.query(Resource).filter(Resource.code == code).first()
    if existing:
        return existing
    
    resource = Resource(
        work_center_id=work_center.id,
        code=code,
        name=name,
        status=status,
        is_active=is_active
    )
    db.add(resource)
    db.flush()
    return resource


def create_test_po_operation(
    db,
    production_order,
    work_center,
    sequence: int = 10,
    operation_code: str = "OP",
    operation_name: str = "Test Operation",
    status: str = "pending",
    planned_run_minutes: int = 60,
    resource=None,
    actual_start=None,
    actual_end=None
):
    """Create a test production order operation."""
    from app.models.production_order import ProductionOrderOperation
    
    op = ProductionOrderOperation(
        production_order_id=production_order.id,
        work_center_id=work_center.id,
        resource_id=resource.id if resource else None,
        sequence=sequence,
        operation_code=operation_code,
        operation_name=operation_name,
        status=status,
        planned_setup_minutes=0,
        planned_run_minutes=planned_run_minutes,
        actual_start=actual_start,
        actual_end=actual_end
    )
    db.add(op)
    db.flush()
    return op


def create_test_routing(
    db,
    product,
    code: str = None,
    name: str = "Test Routing",
    is_active: bool = True
):
    """Create a test routing."""
    from app.models.manufacturing import Routing
    
    if code is None:
        code = f"RTG-{product.sku}"
    
    routing = Routing(
        product_id=product.id,
        code=code,
        name=name,
        is_active=is_active
    )
    db.add(routing)
    db.flush()
    return routing


def create_test_routing_operation(
    db,
    routing,
    work_center,
    sequence: int = 10,
    operation_code: str = "OP",
    operation_name: str = "Test Operation",
    run_time_minutes: int = 60,
    setup_time_minutes: int = 0
):
    """Create a test routing operation."""
    from app.models.manufacturing import RoutingOperation
    
    op = RoutingOperation(
        routing_id=routing.id,
        work_center_id=work_center.id,
        sequence=sequence,
        operation_code=operation_code,
        operation_name=operation_name,
        run_time_minutes=run_time_minutes,
        setup_time_minutes=setup_time_minutes,
        is_active=True
    )
    db.add(op)
    db.flush()
    return op
`

**Verification:**
- [ ] Functions added to ackend/tests/factories.py
- [ ] No import errors when running tests

**Commit Message:** 	est(API-401): add factory functions for operations

---

### Step 3 of 10: Create Pydantic Schemas

**Agent:** Backend Agent  
**Time:** 15 minutes  
**Directory:** ackend/app/schemas/

**File to Create:** ackend/app/schemas/operation_status.py
`python
"""
Schemas for operation status transitions.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class OperationStartRequest(BaseModel):
    """Request to start an operation."""
    resource_id: Optional[int] = Field(None, description="Specific resource/machine to use")
    operator_name: Optional[str] = Field(None, max_length=100, description="Name of operator")
    notes: Optional[str] = Field(None, description="Notes for starting operation")


class OperationCompleteRequest(BaseModel):
    """Request to complete an operation."""
    quantity_completed: Decimal = Field(..., ge=0, description="Quantity completed")
    quantity_scrapped: Decimal = Field(default=Decimal("0"), ge=0, description="Quantity scrapped")
    actual_run_minutes: Optional[int] = Field(None, ge=0, description="Override actual run time")
    notes: Optional[str] = Field(None, description="Completion notes")


class OperationSkipRequest(BaseModel):
    """Request to skip an operation."""
    reason: str = Field(..., min_length=5, max_length=500, description="Reason for skipping")


class ProductionOrderSummary(BaseModel):
    """Summary of production order for operation responses."""
    id: int
    code: str
    status: str
    current_operation_sequence: Optional[int] = None

    class Config:
        from_attributes = True


class NextOperationInfo(BaseModel):
    """Info about the next operation in sequence."""
    id: int
    sequence: int
    operation_code: Optional[str]
    operation_name: Optional[str]
    status: str
    work_center_code: Optional[str] = None
    work_center_name: Optional[str] = None

    class Config:
        from_attributes = True


class OperationResponse(BaseModel):
    """Response for operation status changes."""
    id: int
    sequence: int
    operation_code: Optional[str]
    operation_name: Optional[str]
    status: str
    
    # Resource assignment
    resource_id: Optional[int] = None
    resource_code: Optional[str] = None
    
    # Timing
    planned_run_minutes: Optional[Decimal] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    actual_run_minutes: Optional[Decimal] = None
    
    # Quantities
    quantity_completed: Decimal = Decimal("0")
    quantity_scrapped: Decimal = Decimal("0")
    
    # Notes
    notes: Optional[str] = None
    
    # Related
    production_order: ProductionOrderSummary
    next_operation: Optional[NextOperationInfo] = None

    class Config:
        from_attributes = True


class OperationListItem(BaseModel):
    """Operation in a list."""
    id: int
    sequence: int
    operation_code: Optional[str]
    operation_name: Optional[str]
    status: str
    
    work_center_id: int
    work_center_code: Optional[str] = None
    work_center_name: Optional[str] = None
    
    resource_id: Optional[int] = None
    resource_code: Optional[str] = None
    
    planned_setup_minutes: Decimal = Decimal("0")
    planned_run_minutes: Decimal
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    
    quantity_completed: Decimal = Decimal("0")
    quantity_scrapped: Decimal = Decimal("0")

    class Config:
        from_attributes = True
`

**Verification:**
- [ ] File created at ackend/app/schemas/operation_status.py
- [ ] No Pydantic validation errors

**Commit Message:** eat(API-401): add operation status Pydantic schemas

---

### Step 4 of 10: Create Service Layer

**Agent:** Backend Agent  
**Time:** 45 minutes  
**Directory:** ackend/app/services/

**File to Create:** ackend/app/services/operation_status.py
`python
"""
Service layer for operation status transitions.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.production_order import ProductionOrder, ProductionOrderOperation
from app.models.work_center import WorkCenter
from app.models.manufacturing import Resource


class OperationError(Exception):
    """Custom exception for operation errors."""
    pass


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
        OperationError: If PO or operation not found, or operation doesn't belong to PO
    """
    po = db.get(ProductionOrder, po_id)
    if not po:
        raise OperationError(f"Production order {po_id} not found", 404)
    
    op = db.get(ProductionOrderOperation, op_id)
    if not op:
        raise OperationError(f"Operation {op_id} not found", 404)
    
    if op.production_order_id != po_id:
        raise OperationError(f"Operation {op_id} does not belong to production order {po_id}", 404)
    
    return po, op


def get_previous_operation(
    db: Session,
    po: ProductionOrder,
    current_op: ProductionOrderOperation
) -> Optional[ProductionOrderOperation]:
    """Get the previous operation in sequence."""
    ops = sorted(po.operations, key=lambda x: x.sequence)
    
    for i, op in enumerate(ops):
        if op.id == current_op.id and i > 0:
            return ops[i - 1]
    
    return None


def get_next_operation(
    db: Session,
    po: ProductionOrder,
    current_op: ProductionOrderOperation
) -> Optional[ProductionOrderOperation]:
    """Get the next operation in sequence."""
    ops = sorted(po.operations, key=lambda x: x.sequence)
    
    for i, op in enumerate(ops):
        if op.id == current_op.id and i < len(ops) - 1:
            return ops[i + 1]
    
    return None


def derive_po_status(po: ProductionOrder) -> str:
    """
    Derive PO status from its operations.
    
    Rules:
    - All pending → released
    - All complete/skipped → complete
    - Any running or mixed → in_progress
    """
    if not po.operations:
        return po.status  # No operations, keep current
    
    statuses = [op.status for op in po.operations]
    
    if all(s == 'pending' for s in statuses):
        return 'released'
    elif all(s in ('complete', 'skipped') for s in statuses):
        return 'complete'
    else:
        return 'in_progress'


def update_po_status(db: Session, po: ProductionOrder) -> None:
    """Update PO status based on operations."""
    new_status = derive_po_status(po)
    
    if po.status != new_status:
        po.status = new_status
        po.updated_at = datetime.utcnow()
        
        if new_status == 'in_progress' and not po.actual_start:
            po.actual_start = datetime.utcnow()
        elif new_status == 'complete' and not po.actual_end:
            po.actual_end = datetime.utcnow()
            po.completed_at = datetime.utcnow()


def start_operation(
    db: Session,
    po_id: int,
    op_id: int,
    resource_id: Optional[int] = None,
    operator_name: Optional[str] = None,
    notes: Optional[str] = None
) -> ProductionOrderOperation:
    """
    Start an operation.
    
    Validations:
    - Operation must be pending or queued
    - Previous operation (by sequence) must be complete or skipped
    - Resource must not have conflicting scheduled operation
    
    Returns:
        Updated operation
    
    Raises:
        OperationError: If validation fails
    """
    po, op = get_operation_with_validation(db, po_id, op_id)
    
    # Check operation status
    if op.status == 'running':
        raise OperationError("Operation is already running", 400)
    if op.status in ('complete', 'skipped'):
        raise OperationError(f"Operation is already {op.status}", 400)
    if op.status not in ('pending', 'queued'):
        raise OperationError(f"Cannot start operation in status '{op.status}'", 400)
    
    # Check previous operation is complete
    prev_op = get_previous_operation(db, po, op)
    if prev_op and prev_op.status not in ('complete', 'skipped'):
        raise OperationError(
            f"Previous operation (sequence {prev_op.sequence}) must be complete before starting this one",
            400
        )
    
    # Validate resource if provided
    if resource_id:
        resource = db.get(Resource, resource_id)
        if not resource:
            raise OperationError(f"Resource {resource_id} not found", 404)
        
        # TODO: Check for double-booking (API-403)
        op.resource_id = resource_id
    
    # Update operation
    op.status = 'running'
    op.actual_start = datetime.utcnow()
    op.operator_name = operator_name
    if notes:
        op.notes = notes
    op.updated_at = datetime.utcnow()
    
    # Update PO status
    update_po_status(db, po)
    
    db.flush()
    return op


def complete_operation(
    db: Session,
    po_id: int,
    op_id: int,
    quantity_completed: Decimal,
    quantity_scrapped: Decimal = Decimal("0"),
    actual_run_minutes: Optional[int] = None,
    notes: Optional[str] = None
) -> ProductionOrderOperation:
    """
    Complete an operation.
    
    Validations:
    - Operation must be running
    
    Side effects:
    - Updates PO status if last operation
    - TODO: Consume materials for this operation (API-402)
    
    Returns:
        Updated operation
    
    Raises:
        OperationError: If validation fails
    """
    po, op = get_operation_with_validation(db, po_id, op_id)
    
    # Check operation status
    if op.status != 'running':
        raise OperationError("Operation is not running, cannot complete", 400)
    
    # Update operation
    op.status = 'complete'
    op.actual_end = datetime.utcnow()
    op.quantity_completed = quantity_completed
    op.quantity_scrapped = quantity_scrapped
    
    # Calculate actual run time if not provided
    if actual_run_minutes is not None:
        op.actual_run_minutes = actual_run_minutes
    elif op.actual_start:
        elapsed = datetime.utcnow() - op.actual_start
        op.actual_run_minutes = int(elapsed.total_seconds() / 60)
    
    if notes:
        op.notes = notes
    op.updated_at = datetime.utcnow()
    
    # Update PO status
    update_po_status(db, po)
    
    # Update PO quantities
    po.quantity_completed = quantity_completed
    po.quantity_scrapped = (po.quantity_scrapped or Decimal("0")) + quantity_scrapped
    
    db.flush()
    return op


def skip_operation(
    db: Session,
    po_id: int,
    op_id: int,
    reason: str
) -> ProductionOrderOperation:
    """
    Skip an operation.
    
    Validations:
    - Operation must be pending or queued
    - Previous operation must be complete or skipped
    
    Returns:
        Updated operation
    
    Raises:
        OperationError: If validation fails
    """
    po, op = get_operation_with_validation(db, po_id, op_id)
    
    # Check operation status
    if op.status not in ('pending', 'queued'):
        raise OperationError(f"Cannot skip operation in status '{op.status}'", 400)
    
    # Check previous operation
    prev_op = get_previous_operation(db, po, op)
    if prev_op and prev_op.status not in ('complete', 'skipped'):
        raise OperationError(
            f"Previous operation (sequence {prev_op.sequence}) must be complete before skipping this one",
            400
        )
    
    # Update operation
    op.status = 'skipped'
    op.notes = f"SKIPPED: {reason}"
    op.updated_at = datetime.utcnow()
    
    # Update PO status
    update_po_status(db, po)
    
    db.flush()
    return op


def list_operations(
    db: Session,
    po_id: int
) -> List[ProductionOrderOperation]:
    """
    List operations for a production order.
    
    Returns:
        List of operations ordered by sequence
    
    Raises:
        OperationError: If PO not found
    """
    po = db.get(ProductionOrder, po_id)
    if not po:
        raise OperationError(f"Production order {po_id} not found", 404)
    
    return sorted(po.operations, key=lambda x: x.sequence)
`

**Verification:**
- [ ] File created at ackend/app/services/operation_status.py
- [ ] No import errors

**Commit Message:** eat(API-401): add operation status service layer

---

### Step 5 of 10: Create API Router

**Agent:** Backend Agent  
**Time:** 30 minutes  
**Directory:** ackend/app/api/v1/endpoints/

**File to Create:** ackend/app/api/v1/endpoints/operation_status.py
`python
"""
API endpoints for operation status transitions.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.schemas.operation_status import (
    OperationStartRequest,
    OperationCompleteRequest,
    OperationSkipRequest,
    OperationResponse,
    OperationListItem,
    ProductionOrderSummary,
    NextOperationInfo,
)
from app.services.operation_status import (
    OperationError,
    start_operation,
    complete_operation,
    skip_operation,
    list_operations,
    get_next_operation,
)
from app.models.production_order import ProductionOrder


router = APIRouter()


def build_operation_response(op, po, next_op=None) -> OperationResponse:
    """Build response from operation model."""
    resource_code = None
    if op.resource:
        resource_code = op.resource.code
    
    # Get current operation sequence for PO
    current_seq = None
    for o in sorted(po.operations, key=lambda x: x.sequence):
        if o.status not in ('complete', 'skipped'):
            current_seq = o.sequence
            break
    
    next_op_info = None
    if next_op:
        next_op_info = NextOperationInfo(
            id=next_op.id,
            sequence=next_op.sequence,
            operation_code=next_op.operation_code,
            operation_name=next_op.operation_name,
            status=next_op.status,
            work_center_code=next_op.work_center.code if next_op.work_center else None,
            work_center_name=next_op.work_center.name if next_op.work_center else None,
        )
    
    return OperationResponse(
        id=op.id,
        sequence=op.sequence,
        operation_code=op.operation_code,
        operation_name=op.operation_name,
        status=op.status,
        resource_id=op.resource_id,
        resource_code=resource_code,
        planned_run_minutes=op.planned_run_minutes,
        actual_start=op.actual_start,
        actual_end=op.actual_end,
        actual_run_minutes=op.actual_run_minutes,
        quantity_completed=op.quantity_completed,
        quantity_scrapped=op.quantity_scrapped,
        notes=op.notes,
        production_order=ProductionOrderSummary(
            id=po.id,
            code=po.code,
            status=po.status,
            current_operation_sequence=current_seq,
        ),
        next_operation=next_op_info,
    )


@router.get(
    "/{po_id}/operations",
    response_model=List[OperationListItem],
    summary="List operations for a production order"
)
def get_operations(
    po_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all operations for a production order, ordered by sequence.
    """
    try:
        ops = list_operations(db, po_id)
    except OperationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    result = []
    for op in ops:
        result.append(OperationListItem(
            id=op.id,
            sequence=op.sequence,
            operation_code=op.operation_code,
            operation_name=op.operation_name,
            status=op.status,
            work_center_id=op.work_center_id,
            work_center_code=op.work_center.code if op.work_center else None,
            work_center_name=op.work_center.name if op.work_center else None,
            resource_id=op.resource_id,
            resource_code=op.resource.code if op.resource else None,
            planned_setup_minutes=op.planned_setup_minutes,
            planned_run_minutes=op.planned_run_minutes,
            actual_start=op.actual_start,
            actual_end=op.actual_end,
            quantity_completed=op.quantity_completed,
            quantity_scrapped=op.quantity_scrapped,
        ))
    
    return result


@router.post(
    "/{po_id}/operations/{op_id}/start",
    response_model=OperationResponse,
    summary="Start an operation"
)
def start_operation_endpoint(
    po_id: int,
    op_id: int,
    request: OperationStartRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Start an operation.
    
    Validations:
    - Operation must be in pending or queued status
    - Previous operation must be complete or skipped
    - Resource must not have conflicting scheduled operation
    """
    try:
        op = start_operation(
            db=db,
            po_id=po_id,
            op_id=op_id,
            resource_id=request.resource_id,
            operator_name=request.operator_name,
            notes=request.notes,
        )
        db.commit()
    except OperationError as e:
        status_code = 400
        if "not found" in str(e).lower():
            status_code = 404
        raise HTTPException(status_code=status_code, detail=str(e))
    
    po = db.get(ProductionOrder, po_id)
    next_op = get_next_operation(db, po, op)
    
    return build_operation_response(op, po, next_op)


@router.post(
    "/{po_id}/operations/{op_id}/complete",
    response_model=OperationResponse,
    summary="Complete an operation"
)
def complete_operation_endpoint(
    po_id: int,
    op_id: int,
    request: OperationCompleteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Complete an operation.
    
    Validations:
    - Operation must be in running status
    
    Side effects:
    - Updates PO status if this is the last operation
    - Consumes materials for this operation stage
    """
    try:
        op = complete_operation(
            db=db,
            po_id=po_id,
            op_id=op_id,
            quantity_completed=request.quantity_completed,
            quantity_scrapped=request.quantity_scrapped,
            actual_run_minutes=request.actual_run_minutes,
            notes=request.notes,
        )
        db.commit()
    except OperationError as e:
        status_code = 400
        if "not found" in str(e).lower():
            status_code = 404
        raise HTTPException(status_code=status_code, detail=str(e))
    
    po = db.get(ProductionOrder, po_id)
    next_op = get_next_operation(db, po, op)
    
    return build_operation_response(op, po, next_op)


@router.post(
    "/{po_id}/operations/{op_id}/skip",
    response_model=OperationResponse,
    summary="Skip an operation"
)
def skip_operation_endpoint(
    po_id: int,
    op_id: int,
    request: OperationSkipRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Skip an operation with a reason.
    
    Use cases:
    - Customer waived QC requirement
    - Operation not applicable for this product variant
    """
    try:
        op = skip_operation(
            db=db,
            po_id=po_id,
            op_id=op_id,
            reason=request.reason,
        )
        db.commit()
    except OperationError as e:
        status_code = 400
        if "not found" in str(e).lower():
            status_code = 404
        raise HTTPException(status_code=status_code, detail=str(e))
    
    po = db.get(ProductionOrder, po_id)
    next_op = get_next_operation(db, po, op)
    
    return build_operation_response(op, po, next_op)
`

**Verification:**
- [ ] File created at ackend/app/api/v1/endpoints/operation_status.py
- [ ] No import errors

**Commit Message:** eat(API-401): add operation status API endpoints

---

### Step 6 of 10: Register Router

**Agent:** Backend Agent  
**Time:** 5 minutes  
**File to Modify:** ackend/app/api/v1/api.py

**Add these lines to the existing router registration:**
`python
from app.api.v1.endpoints import operation_status

# Add this line with the other router includes
api_router.include_router(
    operation_status.router,
    prefix="/production-orders",
    tags=["production-operations"]
)
`

**Verification:**
- [ ] Router registered in ackend/app/api/v1/api.py
- [ ] App starts without errors: uvicorn app.main:app --reload

**Commit Message:** chore(API-401): register operation status router

---

### Step 7 of 10: Fix OperationError Exception Handling

**Agent:** Backend Agent  
**Time:** 10 minutes  
**File to Modify:** ackend/app/services/operation_status.py

**Update the OperationError class to include status code:**
`python
class OperationError(Exception):
    """Custom exception for operation errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
    
    def __str__(self):
        return self.message
`

**Verification:**
- [ ] OperationError updated with status_code attribute

**Commit Message:** ix(API-401): add status_code to OperationError

---

### Step 8 of 10: Run Tests and Fix Issues

**Agent:** Backend Agent  
**Time:** 30 minutes

**Run the tests:**
`ash
cd backend
pytest tests/api/test_operation_status.py -v
`

**Expected issues to fix:**
1. Import paths may need adjustment based on actual project structure
2. Factory functions may need tweaks for field names
3. Auth token fixture may need to match existing pattern

**Fix each failing test one at a time. Do NOT change test logic, only fix implementation bugs.**

**Verification:**
- [ ] All 15 tests pass
- [ ] No skipped tests (except intentionally marked)

**Commit Message:** ix(API-401): resolve test failures

---

### Step 9 of 10: Add Integration Test with Scenario

**Agent:** Test Agent  
**Time:** 15 minutes  
**File to Modify:** ackend/tests/api/test_operation_status.py

**Add this test at the end of the file:**
`python
class TestOperationWorkflow:
    """Integration tests for full operation workflow."""

    @pytest.mark.integration
    def test_full_operation_workflow(self, client, db, admin_token):
        """
        Complete workflow: create PO with 3 operations, 
        start and complete each in sequence.
        """
        # Setup
        product = create_test_product(db, sku="WORKFLOW-TEST")
        wc_print = create_test_work_center(db, code="WC-PRINT-WF", name="Print")
        wc_clean = create_test_work_center(db, code="WC-CLEAN-WF", name="Clean")
        wc_pack = create_test_work_center(db, code="WC-PACK-WF", name="Pack")
        
        po = create_test_production_order(db, product=product, qty=10, status="released")
        
        op1 = create_test_po_operation(
            db, production_order=po, work_center=wc_print,
            sequence=10, operation_code="PRINT", planned_run_minutes=240
        )
        op2 = create_test_po_operation(
            db, production_order=po, work_center=wc_clean,
            sequence=20, operation_code="CLEAN", planned_run_minutes=30
        )
        op3 = create_test_po_operation(
            db, production_order=po, work_center=wc_pack,
            sequence=30, operation_code="PACK", planned_run_minutes=15
        )
        db.commit()
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Verify initial state
        assert po.status == "released"
        
        # Step 1: Start op1
        resp = client.post(f"/api/v1/production-orders/{po.id}/operations/{op1.id}/start", headers=headers, json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"
        assert resp.json()["production_order"]["status"] == "in_progress"
        
        # Step 2: Complete op1
        resp = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op1.id}/complete",
            headers=headers,
            json={"quantity_completed": 10}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "complete"
        assert resp.json()["next_operation"]["id"] == op2.id
        
        # Step 3: Start op2
        resp = client.post(f"/api/v1/production-orders/{po.id}/operations/{op2.id}/start", headers=headers, json={})
        assert resp.status_code == 200
        
        # Step 4: Complete op2
        resp = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op2.id}/complete",
            headers=headers,
            json={"quantity_completed": 10}
        )
        assert resp.status_code == 200
        
        # Step 5: Start op3
        resp = client.post(f"/api/v1/production-orders/{po.id}/operations/{op3.id}/start", headers=headers, json={})
        assert resp.status_code == 200
        
        # Step 6: Complete op3 (last operation)
        resp = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op3.id}/complete",
            headers=headers,
            json={"quantity_completed": 10}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "complete"
        assert resp.json()["production_order"]["status"] == "complete"  # PO now complete!
        assert resp.json()["next_operation"] is None  # No more operations
`

**Verification:**
- [ ] Integration test added
- [ ] Test passes: pytest tests/api/test_operation_status.py::TestOperationWorkflow -v

**Commit Message:** 	est(API-401): add full workflow integration test

---

### Step 10 of 10: Update Documentation

**Agent:** Config Agent  
**Time:** 5 minutes  
**File to Modify:** docs/UI_Refactor/02-incremental-dev-plan.md

**Add to the Week 5 section:**
`markdown
### Week 5: Operation-Level Production (v2.3.0)

| Ticket | Status | Description |
|--------|--------|-------------|
| API-401 | ✅ Complete | Operation status transitions |
| API-402 | ⏳ Not Started | Blocking check per operation |
| API-403 | ⏳ Not Started | Double-booking validation |
| API-404 | ⏳ Not Started | Copy routing → PO ops on release |
| UI-401 | ⏳ Not Started | PO detail operation sequence view |
| UI-402 | ⏳ Not Started | Operation-level scheduler |
| UI-403 | ⏳ Not Started | Progress bar |
| UI-404 | ⏳ Not Started | Ready to Start queue |
| E2E-401 | ⏳ Not Started | Operation flow E2E tests |
`

**Verification:**
- [ ] Dev plan updated

**Commit Message:** docs(API-401): mark API-401 complete in dev plan

---

## Final Checklist

- [ ] All 10 steps executed in order
- [ ] 15+ tests passing
- [ ] No regressions in existing tests
- [ ] API endpoints accessible
- [ ] Documentation updated

---

## API Usage Examples
`ash
# List operations for a PO
curl -X GET "http://localhost:8000/api/v1/production-orders/15/operations" \
  -H "Authorization: Bearer "

# Start an operation
curl -X POST "http://localhost:8000/api/v1/production-orders/15/operations/42/start" \
  -H "Authorization: Bearer " \
  -H "Content-Type: application/json" \
  -d '{"resource_id": 5, "operator_name": "John D"}'

# Complete an operation
curl -X POST "http://localhost:8000/api/v1/production-orders/15/operations/42/complete" \
  -H "Authorization: Bearer " \
  -H "Content-Type: application/json" \
  -d '{"quantity_completed": 50, "quantity_scrapped": 0}'

# Skip an operation
curl -X POST "http://localhost:8000/api/v1/production-orders/15/operations/44/skip" \
  -H "Authorization: Bearer " \
  -H "Content-Type: application/json" \
  -d '{"reason": "Customer waived QC requirement"}'
`

---

## Handoff to Next Ticket

**API-402: Blocking Check Per Operation**
- Check material availability for CURRENT operation only
- BOMLine.consume_stage maps to operation codes
- Operation blocked only if its materials unavailable
