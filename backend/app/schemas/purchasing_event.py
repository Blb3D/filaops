"""
Purchasing Event Schemas

Pydantic models for the Purchasing Event API endpoints
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PurchasingEventType(str, Enum):
    """Types of purchasing events"""

    STATUS_CHANGE = "status_change"
    CREATED = "created"
    RECEIPT = "receipt"
    PARTIAL_RECEIPT = "partial_receipt"
    NOTE_ADDED = "note_added"
    DOCUMENT_ATTACHED = "document_attached"
    TRACKING_UPDATED = "tracking_updated"
    EXPECTED_DATE_CHANGED = "expected_date_changed"
    CANCELLED = "cancelled"
    LINE_ADDED = "line_added"
    LINE_REMOVED = "line_removed"
    PRICE_UPDATED = "price_updated"
    VENDOR_CONTACTED = "vendor_contacted"


class PurchasingEventCreate(BaseModel):
    """Schema for creating a purchasing event"""

    event_type: PurchasingEventType
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    old_value: Optional[str] = Field(None, max_length=100)
    new_value: Optional[str] = Field(None, max_length=100)
    event_date: Optional[date] = None
    metadata_key: Optional[str] = Field(None, max_length=100)
    metadata_value: Optional[str] = Field(None, max_length=255)


class PurchasingEventResponse(BaseModel):
    """Schema for purchasing event response"""

    id: int
    purchase_order_id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None  # Populated from relationship
    event_type: str
    title: str
    description: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    event_date: Optional[date] = None
    metadata_key: Optional[str] = None
    metadata_value: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PurchasingEventListResponse(BaseModel):
    """Schema for list of purchasing events"""

    items: list[PurchasingEventResponse]
    total: int
