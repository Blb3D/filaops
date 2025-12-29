# API-302: Bulk Fulfillment Status

**Ticket:** API-302  
**Status:** Not Started  
**Depends On:** API-301  
**Estimate:** 1-2 hours

---

## Purpose

Extend the existing SO list endpoint to include fulfillment status summaries. This avoids N+1 queries when rendering the list.

---

## Option A: Query Parameter (Recommended)

Modify existing list endpoint to optionally include fulfillment:

```
GET /api/v1/sales-orders/?include_fulfillment=true
```

### Response Shape

```json
{
  "items": [
    {
      "id": 123,
      "order_number": "SO-2025-0042",
      "customer_name": "Acme Corp",
      "order_date": "2025-01-15",
      "status": "pending",
      "total": 1500.00,
      "fulfillment": {
        "state": "partially_ready",
        "lines_total": 5,
        "lines_ready": 3,
        "fulfillment_percent": 60.0,
        "can_ship_partial": true,
        "can_ship_complete": false
      }
    },
    {
      "id": 124,
      "order_number": "SO-2025-0043",
      "customer_name": "Beta Inc",
      "order_date": "2025-01-16",
      "status": "pending",
      "total": 800.00,
      "fulfillment": {
        "state": "ready_to_ship",
        "lines_total": 2,
        "lines_ready": 2,
        "fulfillment_percent": 100.0,
        "can_ship_partial": true,
        "can_ship_complete": true
      }
    }
  ],
  "total": 50,
  "page": 1,
  "size": 20
}
```

---

## Option B: Separate Bulk Endpoint

```
POST /api/v1/sales-orders/bulk-fulfillment-status
Body: { "order_ids": [123, 124, 125] }
```

**Not recommended** - adds complexity and requires two API calls.

---

## Implementation (Option A)

### 1. Update SO List Schema

```python
# app/schemas/sales_order.py (modify existing)

from typing import Optional
from app.schemas.fulfillment_status import FulfillmentStatusSummary


class SalesOrderListItem(BaseModel):
    """Sales order in list view."""
    id: int
    order_number: str
    customer_name: str
    order_date: date
    status: str
    total: float
    fulfillment: Optional[FulfillmentStatusSummary] = None  # NEW FIELD
    
    class Config:
        from_attributes = True
```

### 2. Update List Endpoint

```python
# app/api/v1/endpoints/sales_orders.py (modify existing)

@router.get("/", response_model=SalesOrderListResponse)
async def list_sales_orders(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    include_fulfillment: bool = False,  # NEW PARAM
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List sales orders with optional fulfillment status.
    
    Set include_fulfillment=true to get fulfillment summary for each order.
    """
    query = db.query(SalesOrder)
    
    if status:
        query = query.filter(SalesOrder.status == status)
    
    total = query.count()
    orders = query.offset(skip).limit(limit).all()
    
    items = []
    for order in orders:
        item = SalesOrderListItem.from_orm(order)
        
        if include_fulfillment:
            # Use the service from API-301
            status_result = get_fulfillment_status(db, order.id)
            if status_result:
                item.fulfillment = status_result.summary
        
        items.append(item)
    
    return SalesOrderListResponse(items=items, total=total, page=skip//limit + 1, size=limit)
```

### 3. Performance Optimization

The naive approach above does N queries for N orders. Optimize:

```python
# app/services/fulfillment_status.py (add bulk function)

def get_bulk_fulfillment_summaries(db: Session, order_ids: List[int]) -> Dict[int, FulfillmentStatusSummary]:
    """
    Get fulfillment summaries for multiple orders efficiently.
    
    Uses a single query with aggregation instead of N separate queries.
    """
    # Single query: join orders → lines → allocations, group by order
    results = db.query(
        SalesOrder.id,
        func.count(SalesOrderLine.id).label('lines_total'),
        # ... aggregation logic
    ).join(
        SalesOrderLine
    ).outerjoin(
        InventoryAllocation
    ).filter(
        SalesOrder.id.in_(order_ids)
    ).group_by(
        SalesOrder.id
    ).all()
    
    # Build dict of order_id -> summary
    summaries = {}
    for row in results:
        summaries[row.id] = FulfillmentStatusSummary(
            state=_determine_state(row),
            lines_total=row.lines_total,
            # ...
        )
    
    return summaries
```

---

## Tests

```python
# tests/api/test_fulfillment_status.py (add to existing)

class TestBulkFulfillmentStatus:
    """Tests for list endpoint with include_fulfillment=true"""
    
    def test_list_without_fulfillment_flag(self, client, db, auth_headers):
        """Default list should NOT include fulfillment."""
        # Create order
        customer = create_customer(db)
        order = create_sales_order(db, customer_id=customer.id)
        
        response = client.get("/api/v1/sales-orders/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        # fulfillment should be None or not present
        assert data["items"][0].get("fulfillment") is None
    
    def test_list_with_fulfillment_flag(self, client, db, auth_headers):
        """List with flag should include fulfillment summaries."""
        customer = create_customer(db)
        product = create_product(db, sku="FIL-TEST-001")
        order = create_sales_order(db, customer_id=customer.id)
        create_sales_order_line(db, order_id=order.id, product_id=product.id, quantity=10)
        
        response = client.get("/api/v1/sales-orders/?include_fulfillment=true", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["fulfillment"] is not None
        assert "state" in data["items"][0]["fulfillment"]
        assert "lines_total" in data["items"][0]["fulfillment"]
    
    def test_bulk_performance(self, client, db, auth_headers):
        """Listing 20 orders with fulfillment should be fast."""
        customer = create_customer(db)
        for i in range(20):
            create_sales_order(db, customer_id=customer.id)
        
        import time
        start = time.time()
        response = client.get("/api/v1/sales-orders/?include_fulfillment=true&limit=20", headers=auth_headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert len(response.json()["items"]) == 20
        assert elapsed < 2.0  # Should complete in under 2 seconds
```

---

## Definition of Done

- [ ] Query parameter `include_fulfillment` added to list endpoint
- [ ] Response includes fulfillment summary when flag is true
- [ ] Bulk query optimized (not N+1)
- [ ] 3+ tests passing
- [ ] No regressions
