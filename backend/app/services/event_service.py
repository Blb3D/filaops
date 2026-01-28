"""
Event Service

Centralized helper functions for recording events across the application.
Provides consistent event creation for purchasing, shipping, and order events.
"""

from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.purchasing_event import PurchasingEvent
from app.models.shipping_event import ShippingEvent


def record_purchasing_event(
    db: Session,
    purchase_order_id: int,
    event_type: str,
    title: str,
    description: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    event_date: Optional[date] = None,
    user_id: Optional[int] = None,
    metadata_key: Optional[str] = None,
    metadata_value: Optional[str] = None,
) -> PurchasingEvent:
    """
    Record a purchasing event for a purchase order.

    Args:
        db: Database session
        purchase_order_id: ID of the purchase order
        event_type: Type of event (status_change, receipt, etc.)
        title: Short description of the event
        description: Detailed description (optional)
        old_value: Previous value for status changes
        new_value: New value for status changes
        event_date: When the event actually occurred (defaults to today)
        user_id: ID of user who triggered the event
        metadata_key: Additional context key
        metadata_value: Additional context value

    Returns:
        The created PurchasingEvent instance
    """
    event = PurchasingEvent(
        purchase_order_id=purchase_order_id,
        user_id=user_id,
        event_type=event_type,
        title=title,
        description=description,
        old_value=old_value,
        new_value=new_value,
        event_date=event_date or date.today(),
        metadata_key=metadata_key,
        metadata_value=metadata_value,
    )
    db.add(event)
    # Don't commit - let the calling function handle the transaction
    return event


def record_shipping_event(
    db: Session,
    sales_order_id: int,
    event_type: str,
    title: str,
    description: Optional[str] = None,
    tracking_number: Optional[str] = None,
    carrier: Optional[str] = None,
    location_city: Optional[str] = None,
    location_state: Optional[str] = None,
    location_zip: Optional[str] = None,
    event_date: Optional[date] = None,
    event_timestamp: Optional[datetime] = None,
    user_id: Optional[int] = None,
    metadata_key: Optional[str] = None,
    metadata_value: Optional[str] = None,
    source: str = "manual",
) -> ShippingEvent:
    """
    Record a shipping event for a sales order.

    Args:
        db: Database session
        sales_order_id: ID of the sales order
        event_type: Type of event (label_purchased, in_transit, delivered, etc.)
        title: Short description of the event
        description: Detailed description (carrier message, etc.)
        tracking_number: Package tracking number
        carrier: Carrier name (USPS, UPS, FedEx, etc.)
        location_city: City where event occurred
        location_state: State where event occurred
        location_zip: ZIP code where event occurred
        event_date: Date when event occurred
        event_timestamp: Precise timestamp from carrier
        user_id: ID of user who triggered the event
        metadata_key: Additional context key
        metadata_value: Additional context value
        source: Event source (manual, carrier_api, webhook)

    Returns:
        The created ShippingEvent instance
    """
    event = ShippingEvent(
        sales_order_id=sales_order_id,
        user_id=user_id,
        event_type=event_type,
        title=title,
        description=description,
        tracking_number=tracking_number,
        carrier=carrier,
        location_city=location_city,
        location_state=location_state,
        location_zip=location_zip,
        event_date=event_date or date.today(),
        event_timestamp=event_timestamp,
        metadata_key=metadata_key,
        metadata_value=metadata_value,
        source=source,
    )
    db.add(event)
    # Don't commit - let the calling function handle the transaction
    return event
