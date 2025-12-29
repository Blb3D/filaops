# API-301: Single Order Fulfillment Status

**Ticket:** API-301  
**Status:** Not Started  
**Depends On:** None  
**Estimate:** 2-3 hours

---

## Endpoint

```
GET /api/v1/sales-orders/{order_id}/fulfillment-status
```

**Authentication:** Required (Bearer token)

---

## Response Schema

```python
# app/schemas/fulfillment_status.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from enum import Enum


class FulfillmentState(str, Enum):
    READY_TO_SHIP = "ready_to_ship"
    PARTIALLY_READY = "partially_ready"
    BLOCKED = "blocked"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class LineStatus(BaseModel):
    """Status of a single order line."""
    line_id: int
    line_number: int
    product_id: int
    product_sku: str
    product_name: str
    quantity_ordered: float
    quantity_allocated: float
    quantity_shipped: float
    quantity_remaining: float  # ordered - shipped
    is_ready: bool  # allocated >= remaining
    shortage: float  # max(0, remaining - allocated)
    blocking_reason: Optional[str] = None  # e.g., "Insufficient inventory"


class FulfillmentStatusSummary(BaseModel):
    """High-level fulfillment status."""
    state: FulfillmentState
    lines_total: int
    lines_ready: int
    lines_blocked: int
    fulfillment_percent: float  # 0-100
    can_ship_partial: bool  # At least one line ready
    can_ship_complete: bool  # All lines ready
    estimated_complete_date: Optional[date] = None  # Based on incoming POs


class FulfillmentStatus(BaseModel):
    """Complete fulfillment status for a sales order."""
    order_id: int
    order_number: str
    customer_name: str
    order_date: date
    requested_date: Optional[date] = None
    summary: FulfillmentStatusSummary
    lines: List[LineStatus]
```

---

## Example Response

```json
{
  "order_id": 123,
  "order_number": "SO-2025-0042",
  "customer_name": "Acme Corp",
  "order_date": "2025-01-15",
  "requested_date": "2025-01-20",
  "summary": {
    "state": "partially_ready",
    "lines_total": 5,
    "lines_ready": 3,
    "lines_blocked": 2,
    "fulfillment_percent": 60.0,
    "can_ship_partial": true,
    "can_ship_complete": false,
    "estimated_complete_date": "2025-01-22"
  },
  "lines": [
    {
      "line_id": 456,
      "line_number": 1,
      "product_id": 10,
      "product_sku": "FIL-PLA-BLK-1KG",
      "product_name": "PLA Black 1kg",
      "quantity_ordered": 10.0,
      "quantity_allocated": 10.0,
      "quantity_shipped": 0.0,
      "quantity_remaining": 10.0,
      "is_ready": true,
      "shortage": 0.0,
      "blocking_reason": null
    },
    {
      "line_id": 457,
      "line_number": 2,
      "product_id": 11,
      "product_sku": "FIL-PLA-WHT-1KG",
      "product_name": "PLA White 1kg",
      "quantity_ordered": 5.0,
      "quantity_allocated": 2.0,
      "quantity_shipped": 0.0,
      "quantity_remaining": 5.0,
      "is_ready": false,
      "shortage": 3.0,
      "blocking_reason": "Insufficient inventory (need 3.0 more)"
    }
  ]
}
```

---

## Service Logic

```python
# app/services/fulfillment_status.py

from sqlalchemy.orm import Session
from app.models import SalesOrder, SalesOrderLine, InventoryAllocation, Product
from app.schemas.fulfillment_status import (
    FulfillmentStatus, FulfillmentStatusSummary, LineStatus, FulfillmentState
)
from typing import Optional
from datetime import date


def get_fulfillment_status(db: Session, order_id: int) -> Optional[FulfillmentStatus]:
    """
    Calculate complete fulfillment status for a sales order.
    
    Logic:
    1. Load order with lines
    2. For each line, calculate allocated vs remaining
    3. Determine line-level readiness
    4. Aggregate to order-level status
    5. Check for incoming supply to estimate completion
    """
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        return None
    
    # Handle already-terminal states
    if order.status == "shipped":
        return _build_shipped_status(order)
    if order.status == "cancelled":
        return _build_cancelled_status(order)
    
    lines_status = []
    lines_ready = 0
    lines_blocked = 0
    
    for line in order.lines:
        # Get allocated quantity for this line
        allocated = _get_allocated_quantity(db, line)
        remaining = line.quantity - line.shipped_quantity
        shortage = max(0, remaining - allocated)
        is_ready = allocated >= remaining
        
        if is_ready:
            lines_ready += 1
        else:
            lines_blocked += 1
        
        lines_status.append(LineStatus(
            line_id=line.id,
            line_number=line.line_number,
            product_id=line.product_id,
            product_sku=line.product.sku,
            product_name=line.product.name,
            quantity_ordered=line.quantity,
            quantity_allocated=allocated,
            quantity_shipped=line.shipped_quantity,
            quantity_remaining=remaining,
            is_ready=is_ready,
            shortage=shortage,
            blocking_reason=f"Insufficient inventory (need {shortage} more)" if shortage > 0 else None
        ))
    
    lines_total = len(lines_status)
    
    # Determine state
    if lines_ready == lines_total:
        state = FulfillmentState.READY_TO_SHIP
    elif lines_ready > 0:
        state = FulfillmentState.PARTIALLY_READY
    else:
        state = FulfillmentState.BLOCKED
    
    # Calculate fulfillment percent
    fulfillment_percent = (lines_ready / lines_total * 100) if lines_total > 0 else 0
    
    # Estimate completion date based on incoming POs
    estimated_date = _estimate_completion_date(db, order, lines_status)
    
    return FulfillmentStatus(
        order_id=order.id,
        order_number=order.order_number,
        customer_name=order.customer.name if order.customer else "Unknown",
        order_date=order.order_date,
        requested_date=order.requested_date,
        summary=FulfillmentStatusSummary(
            state=state,
            lines_total=lines_total,
            lines_ready=lines_ready,
            lines_blocked=lines_blocked,
            fulfillment_percent=round(fulfillment_percent, 1),
            can_ship_partial=lines_ready > 0,
            can_ship_complete=lines_ready == lines_total,
            estimated_complete_date=estimated_date
        ),
        lines=lines_status
    )


def _get_allocated_quantity(db: Session, line) -> float:
    """Get total allocated quantity for a sales order line."""
    # Check InventoryAllocation table for this line
    # Sum all allocations where sales_order_line_id = line.id
    # This should already exist from Week 2 work
    result = db.query(func.sum(InventoryAllocation.quantity)).filter(
        InventoryAllocation.sales_order_line_id == line.id
    ).scalar()
    return result or 0.0


def _estimate_completion_date(db, order, lines_status) -> Optional[date]:
    """
    Estimate when all lines could be fulfilled based on incoming POs.
    Returns None if no incoming supply found for blocked items.
    """
    # For each blocked line, find POs for that product
    # Return the latest expected_date from those POs
    # This is a simplified version - could be more sophisticated
    pass  # Implement based on existing PO query patterns


def _build_shipped_status(order) -> FulfillmentStatus:
    """Build status for already-shipped order."""
    # All lines are "ready" (already shipped)
    pass


def _build_cancelled_status(order) -> FulfillmentStatus:
    """Build status for cancelled order."""
    pass
```

---

## Endpoint Implementation

```python
# Add to app/api/v1/endpoints/sales_orders.py

from app.schemas.fulfillment_status import FulfillmentStatus
from app.services.fulfillment_status import get_fulfillment_status


@router.get("/{order_id}/fulfillment-status", response_model=FulfillmentStatus)
async def get_order_fulfillment_status(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get fulfillment status for a sales order.
    
    Returns line-by-line status and overall fulfillment progress.
    """
    result = get_fulfillment_status(db, order_id)
    if not result:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return result
```

---

## Tests

```python
# tests/api/test_fulfillment_status.py

import pytest
from tests.factories import (
    create_customer, create_product, create_sales_order,
    create_sales_order_line, create_inventory, create_inventory_allocation
)


class TestFulfillmentStatusEndpoint:
    """Tests for GET /sales-orders/{id}/fulfillment-status"""
    
    def test_ready_to_ship_all_lines_allocated(self, client, db, auth_headers):
        """Order with all lines fully allocated should be ready_to_ship."""
        customer = create_customer(db)
        product = create_product(db, sku="FIL-TEST-001")
        order = create_sales_order(db, customer_id=customer.id)
        line = create_sales_order_line(db, order_id=order.id, product_id=product.id, quantity=10)
        
        # Create inventory and allocate fully
        inv = create_inventory(db, product_id=product.id, quantity=20)
        create_inventory_allocation(db, 
            inventory_id=inv.id, 
            sales_order_line_id=line.id,
            quantity=10
        )
        
        response = client.get(f"/api/v1/sales-orders/{order.id}/fulfillment-status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["state"] == "ready_to_ship"
        assert data["summary"]["lines_total"] == 1
        assert data["summary"]["lines_ready"] == 1
        assert data["summary"]["fulfillment_percent"] == 100.0
        assert data["summary"]["can_ship_complete"] is True
    
    def test_partially_ready_some_lines_allocated(self, client, db, auth_headers):
        """Order with some lines allocated should be partially_ready."""
        customer = create_customer(db)
        product1 = create_product(db, sku="FIL-TEST-001")
        product2 = create_product(db, sku="FIL-TEST-002")
        order = create_sales_order(db, customer_id=customer.id)
        line1 = create_sales_order_line(db, order_id=order.id, product_id=product1.id, quantity=10)
        line2 = create_sales_order_line(db, order_id=order.id, product_id=product2.id, quantity=10)
        
        # Only allocate line1
        inv1 = create_inventory(db, product_id=product1.id, quantity=20)
        create_inventory_allocation(db, inventory_id=inv1.id, sales_order_line_id=line1.id, quantity=10)
        # line2 has no allocation
        
        response = client.get(f"/api/v1/sales-orders/{order.id}/fulfillment-status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["state"] == "partially_ready"
        assert data["summary"]["lines_ready"] == 1
        assert data["summary"]["lines_blocked"] == 1
        assert data["summary"]["fulfillment_percent"] == 50.0
        assert data["summary"]["can_ship_partial"] is True
        assert data["summary"]["can_ship_complete"] is False
    
    def test_blocked_no_lines_allocated(self, client, db, auth_headers):
        """Order with no allocations should be blocked."""
        customer = create_customer(db)
        product = create_product(db, sku="FIL-TEST-001")
        order = create_sales_order(db, customer_id=customer.id)
        create_sales_order_line(db, order_id=order.id, product_id=product.id, quantity=10)
        # No inventory, no allocation
        
        response = client.get(f"/api/v1/sales-orders/{order.id}/fulfillment-status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["state"] == "blocked"
        assert data["summary"]["lines_ready"] == 0
        assert data["summary"]["can_ship_partial"] is False
    
    def test_line_details_include_shortage(self, client, db, auth_headers):
        """Line status should include shortage amount."""
        customer = create_customer(db)
        product = create_product(db, sku="FIL-TEST-001")
        order = create_sales_order(db, customer_id=customer.id)
        line = create_sales_order_line(db, order_id=order.id, product_id=product.id, quantity=10)
        
        # Partial allocation
        inv = create_inventory(db, product_id=product.id, quantity=7)
        create_inventory_allocation(db, inventory_id=inv.id, sales_order_line_id=line.id, quantity=7)
        
        response = client.get(f"/api/v1/sales-orders/{order.id}/fulfillment-status", headers=auth_headers)
        
        data = response.json()
        line_status = data["lines"][0]
        assert line_status["quantity_ordered"] == 10.0
        assert line_status["quantity_allocated"] == 7.0
        assert line_status["shortage"] == 3.0
        assert line_status["is_ready"] is False
        assert "need 3" in line_status["blocking_reason"].lower()
    
    def test_404_for_nonexistent_order(self, client, auth_headers):
        """Should return 404 for nonexistent order."""
        response = client.get("/api/v1/sales-orders/99999/fulfillment-status", headers=auth_headers)
        assert response.status_code == 404
    
    def test_requires_authentication(self, client):
        """Should require auth token."""
        response = client.get("/api/v1/sales-orders/1/fulfillment-status")
        assert response.status_code == 401
    
    def test_shipped_order_shows_shipped_state(self, client, db, auth_headers):
        """Shipped orders should show shipped state."""
        customer = create_customer(db)
        product = create_product(db, sku="FIL-TEST-001")
        order = create_sales_order(db, customer_id=customer.id, status="shipped")
        create_sales_order_line(db, order_id=order.id, product_id=product.id, quantity=10, shipped_quantity=10)
        
        response = client.get(f"/api/v1/sales-orders/{order.id}/fulfillment-status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["state"] == "shipped"
    
    def test_cancelled_order_shows_cancelled_state(self, client, db, auth_headers):
        """Cancelled orders should show cancelled state."""
        customer = create_customer(db)
        order = create_sales_order(db, customer_id=customer.id, status="cancelled")
        
        response = client.get(f"/api/v1/sales-orders/{order.id}/fulfillment-status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["state"] == "cancelled"
```

---

## Verification

After implementation, verify:

```bash
# Run tests
cd backend
pytest tests/api/test_fulfillment_status.py -v

# Manual test
curl -X GET "http://localhost:8000/api/v1/sales-orders/1/fulfillment-status" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Definition of Done

- [ ] Schema created in `app/schemas/fulfillment_status.py`
- [ ] Service created in `app/services/fulfillment_status.py`
- [ ] Endpoint added to `app/api/v1/endpoints/sales_orders.py`
- [ ] 8 tests passing in `tests/api/test_fulfillment_status.py`
- [ ] No regressions in existing tests
- [ ] This doc updated with completion status
