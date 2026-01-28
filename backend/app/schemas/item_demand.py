"""
Schemas for item demand summary endpoint.

Provides structures for:
- Quantity breakdown (on-hand, allocated, available, incoming, projected)
- Allocation details (production orders consuming this item)
- Incoming supply details (purchase orders)
- Shortage information
"""

from datetime import date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class LinkedSalesOrder(BaseModel):
    """Sales order linked to a production order allocation."""

    id: int
    code: str
    customer: Optional[str] = None

    class Config:
        from_attributes = True


class AllocationDetail(BaseModel):
    """Single allocation consuming inventory (typically a production order)."""

    type: str = Field(description="'production_order' or future types")
    reference_code: str
    reference_id: int
    quantity: Decimal
    needed_date: Optional[date] = None
    status: str
    linked_sales_order: Optional[LinkedSalesOrder] = None

    class Config:
        from_attributes = True


class IncomingDetail(BaseModel):
    """Single incoming supply (typically a purchase order line)."""

    type: str = Field(description="'purchase_order' or future types")
    reference_code: str
    reference_id: int
    quantity: Decimal
    expected_date: Optional[date] = None
    status: str
    vendor: Optional[str] = None

    class Config:
        from_attributes = True


class ShortageInfo(BaseModel):
    """Shortage details if available < 0."""

    is_short: bool
    quantity: Decimal = Field(description="Positive number representing shortage amount")
    blocking_orders: List[str] = Field(default_factory=list, description="Order codes blocked by shortage")

    class Config:
        from_attributes = True


class QuantitySummary(BaseModel):
    """Quantity breakdown for an item."""

    on_hand: Decimal
    allocated: Decimal
    available: Decimal = Field(description="on_hand - allocated")
    incoming: Decimal
    projected: Decimal = Field(description="available + incoming")

    class Config:
        from_attributes = True


class ItemDemandSummary(BaseModel):
    """Complete demand summary for an item."""

    item_id: int
    sku: str
    name: str
    stocking_policy: str = Field("on_demand", description="'stocked' or 'on_demand'")
    reorder_point: Optional[Decimal] = Field(None, description="Reorder point for stocked items")

    quantities: QuantitySummary
    allocations: List[AllocationDetail]
    incoming: List[IncomingDetail]
    shortage: ShortageInfo

    class Config:
        from_attributes = True
