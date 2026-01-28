"""
Shipping Event Schemas

Pydantic models for the Shipping Event API endpoints
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ShippingEventType(str, Enum):
    """Types of shipping events"""

    LABEL_PURCHASED = "label_purchased"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    DELIVERY_ATTEMPTED = "delivery_attempted"
    RETURNED = "returned"
    EXCEPTION = "exception"
    ADDRESS_CORRECTED = "address_corrected"
    PACKAGE_CREATED = "package_created"
    CUSTOMS_CLEARED = "customs_cleared"


class ShippingEventSource(str, Enum):
    """Source of shipping event"""

    MANUAL = "manual"
    CARRIER_API = "carrier_api"
    WEBHOOK = "webhook"


class ShippingEventCreate(BaseModel):
    """Schema for creating a shipping event"""

    event_type: ShippingEventType
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tracking_number: Optional[str] = Field(None, max_length=100)
    carrier: Optional[str] = Field(None, max_length=50)
    location_city: Optional[str] = Field(None, max_length=100)
    location_state: Optional[str] = Field(None, max_length=50)
    location_zip: Optional[str] = Field(None, max_length=20)
    event_date: Optional[date] = None
    event_timestamp: Optional[datetime] = None
    metadata_key: Optional[str] = Field(None, max_length=100)
    metadata_value: Optional[str] = Field(None, max_length=255)
    source: ShippingEventSource = ShippingEventSource.MANUAL


class ShippingEventResponse(BaseModel):
    """Schema for shipping event response"""

    id: int
    sales_order_id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None  # Populated from relationship
    event_type: str
    title: str
    description: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_zip: Optional[str] = None
    event_date: Optional[date] = None
    event_timestamp: Optional[datetime] = None
    metadata_key: Optional[str] = None
    metadata_value: Optional[str] = None
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class ShippingEventListResponse(BaseModel):
    """Schema for list of shipping events"""

    items: list[ShippingEventResponse]
    total: int
