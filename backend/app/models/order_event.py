"""
Order Event Model

Tracks activity history for sales orders - status changes, notes, payments, etc.
Provides an audit trail and activity timeline for the OrderDetail page.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class OrderEvent(Base):
    """Order Event - Activity log entry for a sales order"""
    __tablename__ = "order_events"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    sales_order_id = Column(
        Integer,
        ForeignKey("sales_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Note: ondelete=NO ACTION because SQL Server doesn't allow
    # multiple cascade paths (sales_order->user and order_event->user)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="NO ACTION"),
        nullable=True,
        index=True
    )

    # Event Type
    # status_change, note_added, payment_received, payment_refunded,
    # production_started, production_completed, shipped, delivered,
    # address_updated, cancelled, on_hold, resumed
    event_type = Column(String(50), nullable=False, index=True)

    # Event Details
    title = Column(String(255), nullable=False)  # Short description
    description = Column(Text, nullable=True)  # Detailed description

    # For status changes
    old_value = Column(String(100), nullable=True)  # Previous status
    new_value = Column(String(100), nullable=True)  # New status

    # Metadata (JSON-like key=value for additional context)
    # Examples: payment_amount=150.00, tracking_number=1Z999AA10123456784
    metadata_key = Column(String(100), nullable=True)
    metadata_value = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    sales_order = relationship("SalesOrder", backref="events")
    user = relationship("User")

    def __repr__(self):
        return f"<OrderEvent {self.event_type} for SO-{self.sales_order_id}>"
