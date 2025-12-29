# API-303: Enhanced SO List with Sorting/Filtering

**Ticket:** API-303  
**Status:** Not Started  
**Depends On:** API-302  
**Estimate:** 1-2 hours

---

## Purpose

Allow sorting and filtering the SO list by fulfillment state so operators see actionable orders first.

---

## New Query Parameters

```
GET /api/v1/sales-orders/
  ?include_fulfillment=true
  &fulfillment_state=ready_to_ship,partially_ready  # Filter by state(s)
  &sort_by=fulfillment_priority                      # Sort by actionability
  &sort_order=asc                                    # asc or desc
```

### Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `fulfillment_state` | string (comma-sep) | all | Filter: `ready_to_ship`, `partially_ready`, `blocked`, `shipped`, `cancelled` |
| `sort_by` | string | `order_date` | Sort field: `order_date`, `fulfillment_priority`, `fulfillment_percent`, `customer_name` |
| `sort_order` | string | `desc` | `asc` or `desc` |

### Fulfillment Priority Order

When `sort_by=fulfillment_priority`:

1. `ready_to_ship` (priority 1) - Can ship now
2. `partially_ready` (priority 2) - Can partially ship
3. `blocked` (priority 3) - Need action
4. `shipped` (priority 4) - Done
5. `cancelled` (priority 5) - Done

With `sort_order=asc`, ready_to_ship comes first (most actionable).

---

## Implementation

```python
# app/api/v1/endpoints/sales_orders.py

from typing import List, Optional
from enum import Enum


class SortByField(str, Enum):
    ORDER_DATE = "order_date"
    FULFILLMENT_PRIORITY = "fulfillment_priority"
    FULFILLMENT_PERCENT = "fulfillment_percent"
    CUSTOMER_NAME = "customer_name"


FULFILLMENT_PRIORITY_MAP = {
    "ready_to_ship": 1,
    "partially_ready": 2,
    "blocked": 3,
    "shipped": 4,
    "cancelled": 5,
}


@router.get("/", response_model=SalesOrderListResponse)
async def list_sales_orders(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    include_fulfillment: bool = False,
    fulfillment_state: Optional[str] = None,  # NEW: comma-separated states
    sort_by: SortByField = SortByField.ORDER_DATE,  # NEW
    sort_order: str = "desc",  # NEW
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List sales orders with filtering and sorting options.
    
    Fulfillment-based sorting requires include_fulfillment=true.
    """
    # Validate sort_order
    if sort_order not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="sort_order must be 'asc' or 'desc'")
    
    # Parse fulfillment_state filter
    state_filter = None
    if fulfillment_state:
        state_filter = [s.strip() for s in fulfillment_state.split(",")]
        valid_states = {"ready_to_ship", "partially_ready", "blocked", "shipped", "cancelled"}
        invalid = set(state_filter) - valid_states
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid states: {invalid}")
    
    # Base query
    query = db.query(SalesOrder)
    
    if status:
        query = query.filter(SalesOrder.status == status)
    
    # Get all orders first (for fulfillment calculation)
    # This is not ideal for huge datasets but works for typical order counts
    orders = query.all()
    
    # Calculate fulfillment for filtering/sorting
    if include_fulfillment or state_filter or sort_by in (SortByField.FULFILLMENT_PRIORITY, SortByField.FULFILLMENT_PERCENT):
        order_ids = [o.id for o in orders]
        fulfillment_map = get_bulk_fulfillment_summaries(db, order_ids)
    else:
        fulfillment_map = {}
    
    # Filter by fulfillment state
    if state_filter:
        orders = [o for o in orders if fulfillment_map.get(o.id, {}).get("state") in state_filter]
    
    # Sort
    if sort_by == SortByField.ORDER_DATE:
        orders.sort(key=lambda o: o.order_date, reverse=(sort_order == "desc"))
    elif sort_by == SortByField.CUSTOMER_NAME:
        orders.sort(key=lambda o: o.customer.name if o.customer else "", reverse=(sort_order == "desc"))
    elif sort_by == SortByField.FULFILLMENT_PRIORITY:
        orders.sort(
            key=lambda o: FULFILLMENT_PRIORITY_MAP.get(
                fulfillment_map.get(o.id, {}).get("state", "blocked"), 99
            ),
            reverse=(sort_order == "desc")
        )
    elif sort_by == SortByField.FULFILLMENT_PERCENT:
        orders.sort(
            key=lambda o: fulfillment_map.get(o.id, {}).get("fulfillment_percent", 0),
            reverse=(sort_order == "desc")
        )
    
    # Paginate
    total = len(orders)
    orders = orders[skip:skip + limit]
    
    # Build response
    items = []
    for order in orders:
        item = SalesOrderListItem.from_orm(order)
        if include_fulfillment and order.id in fulfillment_map:
            item.fulfillment = fulfillment_map[order.id]
        items.append(item)
    
    return SalesOrderListResponse(items=items, total=total, page=skip//limit + 1, size=limit)
```

---

## Tests

```python
# tests/api/test_fulfillment_status.py (add to existing)

class TestEnhancedSOList:
    """Tests for filtering and sorting by fulfillment."""
    
    def test_filter_by_ready_to_ship(self, client, db, auth_headers):
        """Should filter to only ready_to_ship orders."""
        customer = create_customer(db)
        product = create_product(db)
        
        # Create ready order
        ready_order = create_sales_order(db, customer_id=customer.id)
        line = create_sales_order_line(db, order_id=ready_order.id, product_id=product.id, quantity=10)
        inv = create_inventory(db, product_id=product.id, quantity=10)
        create_inventory_allocation(db, inventory_id=inv.id, sales_order_line_id=line.id, quantity=10)
        
        # Create blocked order
        blocked_order = create_sales_order(db, customer_id=customer.id)
        create_sales_order_line(db, order_id=blocked_order.id, product_id=product.id, quantity=100)
        
        response = client.get(
            "/api/v1/sales-orders/?include_fulfillment=true&fulfillment_state=ready_to_ship",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == ready_order.id
    
    def test_sort_by_fulfillment_priority(self, client, db, auth_headers):
        """Should sort ready_to_ship first."""
        customer = create_customer(db)
        product = create_product(db)
        
        # Create blocked order first (older)
        blocked_order = create_sales_order(db, customer_id=customer.id)
        create_sales_order_line(db, order_id=blocked_order.id, product_id=product.id, quantity=100)
        
        # Create ready order second (newer)
        ready_order = create_sales_order(db, customer_id=customer.id)
        line = create_sales_order_line(db, order_id=ready_order.id, product_id=product.id, quantity=5)
        inv = create_inventory(db, product_id=product.id, quantity=5)
        create_inventory_allocation(db, inventory_id=inv.id, sales_order_line_id=line.id, quantity=5)
        
        response = client.get(
            "/api/v1/sales-orders/?include_fulfillment=true&sort_by=fulfillment_priority&sort_order=asc",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Ready should come first despite being created second
        assert data["items"][0]["fulfillment"]["state"] == "ready_to_ship"
    
    def test_sort_by_fulfillment_percent(self, client, db, auth_headers):
        """Should sort by percent complete."""
        # Setup orders with different completion percentages
        # ...
        pass
    
    def test_invalid_state_returns_400(self, client, auth_headers):
        """Invalid fulfillment_state should return 400."""
        response = client.get(
            "/api/v1/sales-orders/?fulfillment_state=invalid_state",
            headers=auth_headers
        )
        assert response.status_code == 400
    
    def test_invalid_sort_order_returns_400(self, client, auth_headers):
        """Invalid sort_order should return 400."""
        response = client.get(
            "/api/v1/sales-orders/?sort_order=invalid",
            headers=auth_headers
        )
        assert response.status_code == 400
```

---

## Frontend Usage

```typescript
// Get actionable orders first
const response = await fetch(
  '/api/v1/sales-orders/?include_fulfillment=true&sort_by=fulfillment_priority&sort_order=asc'
);

// Filter to just ready orders
const response = await fetch(
  '/api/v1/sales-orders/?include_fulfillment=true&fulfillment_state=ready_to_ship'
);

// Show blocked orders that need attention
const response = await fetch(
  '/api/v1/sales-orders/?include_fulfillment=true&fulfillment_state=blocked,partially_ready'
);
```

---

## Definition of Done

- [ ] `fulfillment_state` filter parameter added
- [ ] `sort_by` parameter with fulfillment options added
- [ ] Validation for invalid parameters (400 response)
- [ ] 4+ tests passing
- [ ] No regressions
