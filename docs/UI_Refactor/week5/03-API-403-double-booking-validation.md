# API-403: Double-Booking Validation

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

**Goal:** Prevent scheduling two operations on the same resource at overlapping times  
**Outcome:** Scheduler cannot double-book a machine/resource

---

## Why This Matters

**Current behavior:** The scheduler allows booking the same printer for multiple operations at the same time. This creates impossible schedules.

**After API-403:** When scheduling or starting an operation on a resource, the system validates that the resource isn't already committed to another operation during that time window.

**Real-world scenario:**
```
Printer P1S-01 Schedule:
├── 09:00-13:00: PO-0142 Op 10 (PRINT) - Widget Pro
├── 10:00-14:00: PO-0145 Op 10 (PRINT) - Gadget Basic  ❌ CONFLICT!
└── 14:00-16:00: PO-0148 Op 10 (PRINT) - Accessory Pack ✅ OK

Old behavior: Both PO-0142 and PO-0145 can be scheduled
New behavior: PO-0145 scheduling returns error with conflict details
```

---

## Validation Points

The double-booking check should happen at:

1. **Schedule assignment** - When assigning scheduled_start/scheduled_end to an operation
2. **Start operation** - When starting an operation with a resource assignment
3. **Resource change** - When changing the assigned resource

---

## Conflict Detection Logic

Two operations conflict if:
- Same resource_id
- Time ranges overlap: `(start1 < end2) AND (start2 < end1)`
- Neither operation is in a terminal state (complete, skipped, cancelled)

```python
# Overlap check
def times_overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1
```

---

## Endpoints to Create/Modify

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/resources/{resource_id}/schedule | Get scheduled operations for a resource |
| GET | /api/v1/resources/{resource_id}/conflicts | Check for conflicts in a time range |
| POST | /api/v1/production-orders/{po_id}/operations/{op_id}/schedule | Schedule an operation (with conflict check) |

---

## Step-by-Step Execution

---

### Step 1 of 7: Write Failing Tests First

**Agent:** Test Agent  
**Time:** 30 minutes  
**Directory:** `backend/tests/api/`

**File to Create:** `backend/tests/api/test_resource_scheduling.py`
```python
"""
Tests for resource scheduling and double-booking validation.

TDD: Write tests first, then implement to make them pass.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from tests.factories import (
    create_test_product,
    create_test_production_order,
    create_test_work_center,
    create_test_resource,
    create_test_po_operation,
)


class TestResourceSchedule:
    """Tests for GET /api/v1/resources/{resource_id}/schedule"""

    @pytest.mark.api
    def test_get_resource_schedule(self, client, db, admin_token):
        """Get scheduled operations for a resource."""
        # Setup
        product = create_test_product(db, sku="SCHED-001")
        wc = create_test_work_center(db, code="WC-SCHED-1", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-SCHED-1", name="Printer 1")
        
        po1 = create_test_production_order(db, product=product, qty=10, status="released")
        po2 = create_test_production_order(db, product=product, qty=5, status="released")
        
        now = datetime.utcnow()
        
        op1 = create_test_po_operation(
            db, production_order=po1, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending",
            resource=resource
        )
        op1.scheduled_start = now + timedelta(hours=1)
        op1.scheduled_end = now + timedelta(hours=5)
        
        op2 = create_test_po_operation(
            db, production_order=po2, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending",
            resource=resource
        )
        op2.scheduled_start = now + timedelta(hours=6)
        op2.scheduled_end = now + timedelta(hours=8)
        
        db.commit()

        # Execute
        response = client.get(
            f"/api/v1/resources/{resource.id}/schedule",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["operations"]) == 2
        assert data["operations"][0]["production_order_code"] == po1.code
        assert data["operations"][1]["production_order_code"] == po2.code

    @pytest.mark.api
    def test_get_resource_schedule_date_filter(self, client, db, admin_token):
        """Filter resource schedule by date range."""
        product = create_test_product(db, sku="SCHED-002")
        wc = create_test_work_center(db, code="WC-SCHED-2", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-SCHED-2", name="Printer 2")
        
        po = create_test_production_order(db, product=product, qty=10, status="released")
        
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)
        
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending",
            resource=resource
        )
        op.scheduled_start = tomorrow
        op.scheduled_end = tomorrow + timedelta(hours=4)
        db.commit()

        # Query for today only - should not include tomorrow's op
        response = client.get(
            f"/api/v1/resources/{resource.id}/schedule",
            params={
                "start_date": now.date().isoformat(),
                "end_date": now.date().isoformat()
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert len(response.json()["operations"]) == 0


class TestDoubleBookingValidation:
    """Tests for double-booking prevention."""

    @pytest.mark.api
    def test_schedule_operation_success(self, client, db, admin_token):
        """Successfully schedule operation when no conflicts."""
        product = create_test_product(db, sku="BOOK-001")
        wc = create_test_work_center(db, code="WC-BOOK-1", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-BOOK-1", name="Printer 1")
        
        po = create_test_production_order(db, product=product, qty=10, status="released")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending",
            planned_run_minutes=240
        )
        db.commit()

        now = datetime.utcnow()
        start_time = now + timedelta(hours=1)
        end_time = now + timedelta(hours=5)

        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "resource_id": resource.id,
                "scheduled_start": start_time.isoformat(),
                "scheduled_end": end_time.isoformat()
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resource_id"] == resource.id
        assert data["scheduled_start"] is not None

    @pytest.mark.api
    def test_schedule_operation_conflict(self, client, db, admin_token):
        """Cannot schedule operation when resource already booked."""
        product = create_test_product(db, sku="BOOK-002")
        wc = create_test_work_center(db, code="WC-BOOK-2", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-BOOK-2", name="Printer 2")
        
        po1 = create_test_production_order(db, product=product, qty=10, status="released")
        po2 = create_test_production_order(db, product=product, qty=5, status="released")
        
        now = datetime.utcnow()
        
        # First operation already scheduled
        op1 = create_test_po_operation(
            db, production_order=po1, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending",
            resource=resource
        )
        op1.scheduled_start = now + timedelta(hours=1)
        op1.scheduled_end = now + timedelta(hours=5)
        
        # Second operation to schedule (overlaps with first)
        op2 = create_test_po_operation(
            db, production_order=po2, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Try to schedule op2 during op1's time
        response = client.post(
            f"/api/v1/production-orders/{po2.id}/operations/{op2.id}/schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "resource_id": resource.id,
                "scheduled_start": (now + timedelta(hours=2)).isoformat(),  # Overlaps!
                "scheduled_end": (now + timedelta(hours=6)).isoformat()
            }
        )

        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "conflict" in data["detail"].lower()
        assert "conflicts" in data
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["production_order_code"] == po1.code

    @pytest.mark.api
    def test_schedule_adjacent_no_conflict(self, client, db, admin_token):
        """Adjacent time slots (end = start) do not conflict."""
        product = create_test_product(db, sku="BOOK-003")
        wc = create_test_work_center(db, code="WC-BOOK-3", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-BOOK-3", name="Printer 3")
        
        po1 = create_test_production_order(db, product=product, qty=10, status="released")
        po2 = create_test_production_order(db, product=product, qty=5, status="released")
        
        now = datetime.utcnow()
        
        # First operation: 1:00 - 5:00
        op1 = create_test_po_operation(
            db, production_order=po1, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending",
            resource=resource
        )
        op1.scheduled_start = now + timedelta(hours=1)
        op1.scheduled_end = now + timedelta(hours=5)
        
        # Second operation to schedule
        op2 = create_test_po_operation(
            db, production_order=po2, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Schedule op2 starting exactly when op1 ends (5:00 - 9:00)
        response = client.post(
            f"/api/v1/production-orders/{po2.id}/operations/{op2.id}/schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "resource_id": resource.id,
                "scheduled_start": (now + timedelta(hours=5)).isoformat(),  # Starts when op1 ends
                "scheduled_end": (now + timedelta(hours=9)).isoformat()
            }
        )

        assert response.status_code == 200  # No conflict

    @pytest.mark.api
    def test_completed_operations_no_conflict(self, client, db, admin_token):
        """Completed operations don't block scheduling."""
        product = create_test_product(db, sku="BOOK-004")
        wc = create_test_work_center(db, code="WC-BOOK-4", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-BOOK-4", name="Printer 4")
        
        po1 = create_test_production_order(db, product=product, qty=10, status="complete")
        po2 = create_test_production_order(db, product=product, qty=5, status="released")
        
        now = datetime.utcnow()
        
        # First operation - COMPLETED
        op1 = create_test_po_operation(
            db, production_order=po1, work_center=wc,
            sequence=10, operation_code="PRINT", status="complete",
            resource=resource
        )
        op1.scheduled_start = now + timedelta(hours=1)
        op1.scheduled_end = now + timedelta(hours=5)
        
        op2 = create_test_po_operation(
            db, production_order=po2, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Schedule op2 during op1's time (should work because op1 is complete)
        response = client.post(
            f"/api/v1/production-orders/{po2.id}/operations/{op2.id}/schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "resource_id": resource.id,
                "scheduled_start": (now + timedelta(hours=2)).isoformat(),
                "scheduled_end": (now + timedelta(hours=6)).isoformat()
            }
        )

        assert response.status_code == 200  # No conflict with completed op


class TestConflictCheck:
    """Tests for GET /api/v1/resources/{resource_id}/conflicts"""

    @pytest.mark.api
    def test_check_conflicts_found(self, client, db, admin_token):
        """Find conflicts for a proposed time range."""
        product = create_test_product(db, sku="CONF-001")
        wc = create_test_work_center(db, code="WC-CONF-1", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-CONF-1", name="Printer 1")
        
        po = create_test_production_order(db, product=product, qty=10, status="in_progress")
        
        now = datetime.utcnow()
        
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="running",
            resource=resource
        )
        op.scheduled_start = now + timedelta(hours=1)
        op.scheduled_end = now + timedelta(hours=5)
        db.commit()

        # Check for conflicts in overlapping range
        response = client.get(
            f"/api/v1/resources/{resource.id}/conflicts",
            params={
                "start": (now + timedelta(hours=2)).isoformat(),
                "end": (now + timedelta(hours=6)).isoformat()
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is True
        assert len(data["conflicts"]) == 1

    @pytest.mark.api
    def test_check_conflicts_none(self, client, db, admin_token):
        """No conflicts for available time range."""
        product = create_test_product(db, sku="CONF-002")
        wc = create_test_work_center(db, code="WC-CONF-2", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-CONF-2", name="Printer 2")
        
        po = create_test_production_order(db, product=product, qty=10, status="in_progress")
        
        now = datetime.utcnow()
        
        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="running",
            resource=resource
        )
        op.scheduled_start = now + timedelta(hours=1)
        op.scheduled_end = now + timedelta(hours=5)
        db.commit()

        # Check for conflicts in non-overlapping range
        response = client.get(
            f"/api/v1/resources/{resource.id}/conflicts",
            params={
                "start": (now + timedelta(hours=6)).isoformat(),
                "end": (now + timedelta(hours=10)).isoformat()
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False
        assert len(data["conflicts"]) == 0


class TestStartOperationDoubleBooking:
    """Tests for double-booking check when starting operation."""

    @pytest.mark.api
    def test_start_operation_resource_busy(self, client, db, admin_token):
        """Cannot start operation if resource is currently running another."""
        product = create_test_product(db, sku="START-001")
        wc = create_test_work_center(db, code="WC-START-1", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-START-1", name="Printer 1")
        
        po1 = create_test_production_order(db, product=product, qty=10, status="in_progress")
        po2 = create_test_production_order(db, product=product, qty=5, status="released")
        
        # First operation already running on resource
        op1 = create_test_po_operation(
            db, production_order=po1, work_center=wc,
            sequence=10, operation_code="PRINT", status="running",
            resource=resource
        )
        op1.actual_start = datetime.utcnow() - timedelta(hours=1)
        
        # Second operation trying to start on same resource
        op2 = create_test_po_operation(
            db, production_order=po2, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Try to start op2 on same resource
        response = client.post(
            f"/api/v1/production-orders/{po2.id}/operations/{op2.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"resource_id": resource.id}
        )

        assert response.status_code == 409  # Conflict
        assert "busy" in response.json()["detail"].lower() or "conflict" in response.json()["detail"].lower()
```

**Verification:**
- [ ] File created at `backend/tests/api/test_resource_scheduling.py`
- [ ] Run `pytest backend/tests/api/test_resource_scheduling.py -v`
- [ ] Tests FAIL (expected - TDD)

**Commit Message:** `test(API-403): add failing tests for double-booking validation`

---

### Step 2 of 7: Create Resource Scheduling Service

**Agent:** Backend Agent  
**Time:** 30 minutes  
**Directory:** `backend/app/services/`

**File to Create:** `backend/app/services/resource_scheduling.py`
```python
"""
Service layer for resource scheduling and conflict detection.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.production_order import ProductionOrder, ProductionOrderOperation
from app.models.manufacturing import Resource


class SchedulingError(Exception):
    """Custom exception for scheduling errors."""
    def __init__(self, message: str, status_code: int = 400, conflicts: list = None):
        self.message = message
        self.status_code = status_code
        self.conflicts = conflicts or []
        super().__init__(self.message)


# Terminal statuses - operations in these states don't block resources
TERMINAL_STATUSES = ['complete', 'skipped', 'cancelled']


def get_resource_schedule(
    db: Session,
    resource_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    exclude_terminal: bool = True
) -> List[ProductionOrderOperation]:
    """
    Get scheduled operations for a resource.
    
    Args:
        db: Database session
        resource_id: Resource ID
        start_date: Filter operations starting on or after this date
        end_date: Filter operations ending on or before this date
        exclude_terminal: If True, exclude completed/skipped/cancelled operations
    
    Returns:
        List of operations ordered by scheduled_start
    """
    query = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.resource_id == resource_id,
        ProductionOrderOperation.scheduled_start.isnot(None)
    )
    
    if exclude_terminal:
        query = query.filter(
            ProductionOrderOperation.status.notin_(TERMINAL_STATUSES)
        )
    
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        query = query.filter(ProductionOrderOperation.scheduled_end >= start_dt)
    
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.filter(ProductionOrderOperation.scheduled_start <= end_dt)
    
    return query.order_by(ProductionOrderOperation.scheduled_start).all()


def find_conflicts(
    db: Session,
    resource_id: int,
    start: datetime,
    end: datetime,
    exclude_operation_id: Optional[int] = None
) -> List[ProductionOrderOperation]:
    """
    Find operations that conflict with a proposed time range.
    
    Two operations conflict if their time ranges overlap:
    (start1 < end2) AND (start2 < end1)
    
    Args:
        db: Database session
        resource_id: Resource ID to check
        start: Proposed start time
        end: Proposed end time
        exclude_operation_id: Operation ID to exclude (for rescheduling same op)
    
    Returns:
        List of conflicting operations
    """
    query = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.resource_id == resource_id,
        ProductionOrderOperation.status.notin_(TERMINAL_STATUSES),
        ProductionOrderOperation.scheduled_start.isnot(None),
        ProductionOrderOperation.scheduled_end.isnot(None),
        # Overlap condition: start1 < end2 AND start2 < end1
        ProductionOrderOperation.scheduled_start < end,
        ProductionOrderOperation.scheduled_end > start
    )
    
    if exclude_operation_id:
        query = query.filter(ProductionOrderOperation.id != exclude_operation_id)
    
    return query.all()


def find_running_operations(
    db: Session,
    resource_id: int
) -> List[ProductionOrderOperation]:
    """
    Find operations currently running on a resource.
    
    An operation is considered "running" if:
    - status = 'running'
    - resource_id matches
    """
    return db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.resource_id == resource_id,
        ProductionOrderOperation.status == 'running'
    ).all()


def schedule_operation(
    db: Session,
    po_id: int,
    op_id: int,
    resource_id: int,
    scheduled_start: datetime,
    scheduled_end: datetime
) -> ProductionOrderOperation:
    """
    Schedule an operation on a resource.
    
    Validates:
    - No conflicts with other scheduled operations
    - Resource exists and is available
    
    Args:
        db: Database session
        po_id: Production order ID
        op_id: Operation ID
        resource_id: Resource to schedule on
        scheduled_start: Start time
        scheduled_end: End time
    
    Returns:
        Updated operation
    
    Raises:
        SchedulingError: If conflicts exist or validation fails
    """
    # Get and validate operation
    op = db.get(ProductionOrderOperation, op_id)
    if not op:
        raise SchedulingError(f"Operation {op_id} not found", 404)
    
    if op.production_order_id != po_id:
        raise SchedulingError(f"Operation {op_id} does not belong to production order {po_id}", 404)
    
    # Validate resource
    resource = db.get(Resource, resource_id)
    if not resource:
        raise SchedulingError(f"Resource {resource_id} not found", 404)
    
    # Check for conflicts
    conflicts = find_conflicts(
        db, resource_id, scheduled_start, scheduled_end,
        exclude_operation_id=op_id
    )
    
    if conflicts:
        conflict_details = []
        for c in conflicts:
            po = db.get(ProductionOrder, c.production_order_id)
            conflict_details.append({
                "operation_id": c.id,
                "production_order_id": c.production_order_id,
                "production_order_code": po.code if po else "Unknown",
                "operation_code": c.operation_code,
                "scheduled_start": c.scheduled_start.isoformat() if c.scheduled_start else None,
                "scheduled_end": c.scheduled_end.isoformat() if c.scheduled_end else None,
            })
        
        raise SchedulingError(
            f"Resource {resource.code} has {len(conflicts)} conflicting operation(s)",
            409,
            conflict_details
        )
    
    # Update operation
    op.resource_id = resource_id
    op.scheduled_start = scheduled_start
    op.scheduled_end = scheduled_end
    op.updated_at = datetime.utcnow()
    
    db.flush()
    return op


def check_resource_available_now(
    db: Session,
    resource_id: int
) -> Tuple[bool, Optional[ProductionOrderOperation]]:
    """
    Check if a resource is available right now (no running operations).
    
    Returns:
        Tuple of (is_available, running_operation_if_any)
    """
    running = find_running_operations(db, resource_id)
    
    if running:
        return False, running[0]
    
    return True, None
```

**Verification:**
- [ ] File created at `backend/app/services/resource_scheduling.py`
- [ ] No import errors

**Commit Message:** `feat(API-403): add resource scheduling service layer`

---

### Step 3 of 7: Create Pydantic Schemas

**Agent:** Backend Agent  
**Time:** 10 minutes  
**Directory:** `backend/app/schemas/`

**File to Create:** `backend/app/schemas/resource_scheduling.py`
```python
"""
Schemas for resource scheduling endpoints.
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class ScheduleOperationRequest(BaseModel):
    """Request to schedule an operation."""
    resource_id: int = Field(..., description="Resource/machine to schedule on")
    scheduled_start: datetime = Field(..., description="Scheduled start time")
    scheduled_end: datetime = Field(..., description="Scheduled end time")


class ConflictInfo(BaseModel):
    """Info about a scheduling conflict."""
    operation_id: int
    production_order_id: int
    production_order_code: str
    operation_code: Optional[str] = None
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None


class ScheduledOperationInfo(BaseModel):
    """Info about a scheduled operation."""
    operation_id: int
    production_order_id: int
    production_order_code: str
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    operation_code: Optional[str] = None
    operation_name: Optional[str] = None
    status: str
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    quantity: Optional[float] = None


class ResourceScheduleResponse(BaseModel):
    """Response for resource schedule query."""
    resource_id: int
    resource_code: str
    resource_name: Optional[str] = None
    operations: List[ScheduledOperationInfo] = []


class ConflictCheckResponse(BaseModel):
    """Response for conflict check."""
    resource_id: int
    start: datetime
    end: datetime
    has_conflicts: bool
    conflicts: List[ConflictInfo] = []


class ScheduleOperationResponse(BaseModel):
    """Response after scheduling an operation."""
    operation_id: int
    resource_id: int
    resource_code: Optional[str] = None
    scheduled_start: datetime
    scheduled_end: datetime
    production_order_id: int
    production_order_code: str
```

**Verification:**
- [ ] File created at `backend/app/schemas/resource_scheduling.py`
- [ ] No Pydantic validation errors

**Commit Message:** `feat(API-403): add resource scheduling Pydantic schemas`

---

### Step 4 of 7: Create API Router

**Agent:** Backend Agent  
**Time:** 20 minutes  
**Directory:** `backend/app/api/v1/endpoints/`

**File to Create:** `backend/app/api/v1/endpoints/resource_scheduling.py`
```python
"""
API endpoints for resource scheduling and conflict detection.
"""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.models.production_order import ProductionOrder
from app.models.manufacturing import Resource
from app.schemas.resource_scheduling import (
    ScheduleOperationRequest,
    ResourceScheduleResponse,
    ConflictCheckResponse,
    ScheduleOperationResponse,
    ScheduledOperationInfo,
    ConflictInfo,
)
from app.services.resource_scheduling import (
    SchedulingError,
    get_resource_schedule,
    find_conflicts,
    schedule_operation,
)


router = APIRouter()


@router.get(
    "/{resource_id}/schedule",
    response_model=ResourceScheduleResponse,
    summary="Get resource schedule"
)
def get_schedule(
    resource_id: int,
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get scheduled operations for a resource.
    
    Returns operations ordered by scheduled start time.
    """
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
    
    operations = get_resource_schedule(db, resource_id, start_date, end_date)
    
    op_list = []
    for op in operations:
        po = db.get(ProductionOrder, op.production_order_id)
        product = po.product if po else None
        
        op_list.append(ScheduledOperationInfo(
            operation_id=op.id,
            production_order_id=op.production_order_id,
            production_order_code=po.code if po else "Unknown",
            product_sku=product.sku if product else None,
            product_name=product.name if product else None,
            operation_code=op.operation_code,
            operation_name=op.operation_name,
            status=op.status,
            scheduled_start=op.scheduled_start,
            scheduled_end=op.scheduled_end,
            quantity=float(po.quantity_ordered) if po and po.quantity_ordered else None,
        ))
    
    return ResourceScheduleResponse(
        resource_id=resource.id,
        resource_code=resource.code,
        resource_name=resource.name,
        operations=op_list
    )


@router.get(
    "/{resource_id}/conflicts",
    response_model=ConflictCheckResponse,
    summary="Check for scheduling conflicts"
)
def check_conflicts(
    resource_id: int,
    start: datetime = Query(..., description="Proposed start time"),
    end: datetime = Query(..., description="Proposed end time"),
    exclude_operation_id: Optional[int] = Query(None, description="Operation to exclude"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Check if a time range conflicts with existing scheduled operations.
    
    Useful for UI to show available slots before scheduling.
    """
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
    
    conflicts = find_conflicts(db, resource_id, start, end, exclude_operation_id)
    
    conflict_list = []
    for c in conflicts:
        po = db.get(ProductionOrder, c.production_order_id)
        conflict_list.append(ConflictInfo(
            operation_id=c.id,
            production_order_id=c.production_order_id,
            production_order_code=po.code if po else "Unknown",
            operation_code=c.operation_code,
            scheduled_start=c.scheduled_start.isoformat() if c.scheduled_start else None,
            scheduled_end=c.scheduled_end.isoformat() if c.scheduled_end else None,
        ))
    
    return ConflictCheckResponse(
        resource_id=resource_id,
        start=start,
        end=end,
        has_conflicts=len(conflicts) > 0,
        conflicts=conflict_list
    )
```

**Verification:**
- [ ] File created at `backend/app/api/v1/endpoints/resource_scheduling.py`
- [ ] No import errors

**Commit Message:** `feat(API-403): add resource scheduling API endpoints`

---

### Step 5 of 7: Add Schedule Endpoint to Operation Status Router

**Agent:** Backend Agent  
**Time:** 10 minutes  
**File to Modify:** `backend/app/api/v1/endpoints/operation_status.py`

**Add these imports and endpoint:**
```python
# Add to imports
from app.schemas.resource_scheduling import (
    ScheduleOperationRequest,
    ScheduleOperationResponse,
)
from app.services.resource_scheduling import (
    SchedulingError,
    schedule_operation,
)


# Add this endpoint
@router.post(
    "/{po_id}/operations/{op_id}/schedule",
    response_model=ScheduleOperationResponse,
    summary="Schedule an operation on a resource"
)
def schedule_operation_endpoint(
    po_id: int,
    op_id: int,
    request: ScheduleOperationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Schedule an operation on a specific resource.
    
    Validates that no other operations are scheduled on the same
    resource during the requested time window.
    """
    try:
        op = schedule_operation(
            db=db,
            po_id=po_id,
            op_id=op_id,
            resource_id=request.resource_id,
            scheduled_start=request.scheduled_start,
            scheduled_end=request.scheduled_end
        )
        db.commit()
    except SchedulingError as e:
        if e.conflicts:
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
                headers={"X-Conflicts": "true"}
            ) from None
        raise HTTPException(status_code=e.status_code, detail=e.message)
    
    po = db.get(ProductionOrder, po_id)
    resource = db.get(Resource, request.resource_id) if request.resource_id else None
    
    return ScheduleOperationResponse(
        operation_id=op.id,
        resource_id=op.resource_id,
        resource_code=resource.code if resource else None,
        scheduled_start=op.scheduled_start,
        scheduled_end=op.scheduled_end,
        production_order_id=po.id,
        production_order_code=po.code
    )
```

**Also update the HTTPException for SchedulingError to include conflicts:**

In the endpoint, replace the HTTPException raise with:
```python
    except SchedulingError as e:
        error_response = {"detail": e.message}
        if e.conflicts:
            error_response["conflicts"] = e.conflicts
        raise HTTPException(
            status_code=e.status_code,
            detail=error_response["detail"]
        )
```

Wait, FastAPI doesn't allow custom fields easily. Let's use a different approach - return the conflicts in the detail:

```python
    except SchedulingError as e:
        if e.conflicts:
            # Return conflict details in response body
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.message,
                    "conflicts": e.conflicts
                }
            )
        raise HTTPException(status_code=e.status_code, detail=e.message)
```

**Verification:**
- [ ] Endpoint added to operation_status.py
- [ ] Import JSONResponse from fastapi.responses

**Commit Message:** `feat(API-403): add schedule operation endpoint`

---

### Step 6 of 7: Register Resource Router

**Agent:** Backend Agent  
**Time:** 5 minutes  
**File to Modify:** `backend/app/api/v1/api.py` (or `__init__.py`)

**Add router registration:**
```python
from app.api.v1.endpoints import resource_scheduling

api_router.include_router(
    resource_scheduling.router,
    prefix="/resources",
    tags=["resource-scheduling"]
)
```

**Verification:**
- [ ] Router registered
- [ ] App starts without errors

**Commit Message:** `chore(API-403): register resource scheduling router`

---

### Step 7 of 7: Update Start Operation with Double-Booking Check

**Agent:** Backend Agent  
**Time:** 10 minutes  
**File to Modify:** `backend/app/services/operation_status.py`

**Add double-booking check to start_operation function:**

Add import at top:
```python
from app.services.resource_scheduling import check_resource_available_now
```

In `start_operation` function, after validating resource_id, add:
```python
    # Validate resource if provided
    if resource_id:
        resource = db.get(Resource, resource_id)
        if not resource:
            raise OperationError(f"Resource {resource_id} not found", 404)
        
        # Check resource is not currently running another operation
        is_available, running_op = check_resource_available_now(db, resource_id)
        if not is_available:
            running_po = db.get(ProductionOrder, running_op.production_order_id)
            raise OperationError(
                f"Resource {resource.code} is busy with operation {running_op.operation_code} "
                f"on {running_po.code if running_po else 'unknown PO'}",
                409
            )
        
        op.resource_id = resource_id
```

**Verification:**
- [ ] Double-booking check added to start_operation
- [ ] All tests pass: `pytest tests/api/test_resource_scheduling.py tests/api/test_operation_status.py -v`

**Commit Message:** `feat(API-403): add double-booking check to start operation`

---

## Final Checklist

- [ ] All 7 steps executed in order
- [ ] 10+ new tests passing
- [ ] No regressions in existing tests
- [ ] API endpoints accessible
- [ ] Start operation validates resource availability

---

## API Usage Examples

```bash
# Get resource schedule
curl -X GET "http://localhost:8000/api/v1/resources/5/schedule?start_date=2025-01-01" \
  -H "Authorization: Bearer <token>"

# Check for conflicts
curl -X GET "http://localhost:8000/api/v1/resources/5/conflicts?start=2025-01-02T09:00:00&end=2025-01-02T13:00:00" \
  -H "Authorization: Bearer <token>"

# Schedule an operation
curl -X POST "http://localhost:8000/api/v1/production-orders/15/operations/42/schedule" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_id": 5,
    "scheduled_start": "2025-01-02T09:00:00",
    "scheduled_end": "2025-01-02T13:00:00"
  }'

# Response when conflict:
{
  "detail": "Resource PRINTER-01 has 1 conflicting operation(s)",
  "conflicts": [
    {
      "operation_id": 41,
      "production_order_id": 14,
      "production_order_code": "PO-2025-0014",
      "operation_code": "PRINT",
      "scheduled_start": "2025-01-02T08:00:00",
      "scheduled_end": "2025-01-02T12:00:00"
    }
  ]
}
```

---

## Handoff to Next Ticket

**API-404: Copy Routing to PO Operations on Release**
- When PO status changes to "released", auto-create operation records
- Copy from product's routing template
- Set up operation sequence, work centers, planned times
