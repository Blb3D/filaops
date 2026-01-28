"""
Shipping Event Model

Tracks shipping lifecycle events for sales orders - label purchase, pickup,
in transit, delivered, etc. Provides a shipment tracking timeline.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class ShippingEvent(Base):
    """Shipping Event - Shipment tracking log entry for a sales order"""

    __tablename__ = "shipping_events"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="NO ACTION"), nullable=True, index=True)

    # Event Type
    # label_purchased, picked_up, in_transit, out_for_delivery, delivered,
    # delivery_attempted, returned, exception, address_corrected
    event_type = Column(String(50), nullable=False, index=True)

    # Event Details
    title = Column(String(255), nullable=False)  # Short description
    description = Column(Text, nullable=True)  # Detailed description (carrier message)

    # Tracking info
    tracking_number = Column(String(100), nullable=True, index=True)
    carrier = Column(String(50), nullable=True)  # USPS, UPS, FedEx, etc.

    # Location info (for transit events)
    location_city = Column(String(100), nullable=True)
    location_state = Column(String(50), nullable=True)
    location_zip = Column(String(20), nullable=True)

    # Event date - when the event actually occurred
    # Distinct from created_at which is system entry timestamp
    event_date = Column(Date, nullable=True, index=True)
    event_timestamp = Column(DateTime, nullable=True)  # Precise time from carrier

    # Metadata (JSON-like key=value for additional context)
    # Examples: signature=John Doe, weight=2.5lbs
    metadata_key = Column(String(100), nullable=True)
    metadata_value = Column(String(255), nullable=True)

    # Source of event
    # manual, carrier_api, webhook
    source = Column(String(50), default="manual", nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    sales_order = relationship("SalesOrder", backref="shipping_events")
    user = relationship("User")

    def __repr__(self):
        return f"<ShippingEvent {self.event_type} for SO-{self.sales_order_id}>"
