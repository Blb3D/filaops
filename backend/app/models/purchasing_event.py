"""
Purchasing Event Model

Tracks activity history for purchase orders - status changes, receipts, notes, etc.
Provides an audit trail and activity timeline for the PO detail page.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class PurchasingEvent(Base):
    """Purchasing Event - Activity log entry for a purchase order"""

    __tablename__ = "purchasing_events"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    purchase_order_id = Column(
        Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="NO ACTION"), nullable=True, index=True)

    # Event Type
    # status_change, receipt, partial_receipt, note_added, document_attached,
    # tracking_updated, expected_date_changed, cancelled, line_added, line_removed
    event_type = Column(String(50), nullable=False, index=True)

    # Event Details
    title = Column(String(255), nullable=False)  # Short description
    description = Column(Text, nullable=True)  # Detailed description

    # For status changes
    old_value = Column(String(100), nullable=True)  # Previous status
    new_value = Column(String(100), nullable=True)  # New status

    # Event date - when the event actually occurred (user-entered)
    # Distinct from created_at which is system entry timestamp
    event_date = Column(Date, nullable=True, index=True)

    # Metadata (JSON-like key=value for additional context)
    # Examples: quantity_received=100, tracking_number=1Z999AA10123456784
    metadata_key = Column(String(100), nullable=True)
    metadata_value = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    purchase_order = relationship("PurchaseOrder", backref="events")
    user = relationship("User")

    def __repr__(self):
        return f"<PurchasingEvent {self.event_type} for PO-{self.purchase_order_id}>"
