"""
Payment Model

Tracks payment transactions for sales orders with full audit trail.
Supports partial payments, multiple payment methods, and refunds.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Payment(Base):
    """
    Payment record for sales orders.

    Each payment is a transaction record - supports:
    - Full payments
    - Partial payments (multiple payments per order)
    - Refunds (negative amounts)
    - Multiple payment methods
    """
    __tablename__ = "payments"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    # Note: Using NO ACTION for recorded_by to avoid SQL Server cascade path conflict
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="NO ACTION"), nullable=True, index=True)

    # Payment Reference
    payment_number = Column(String(50), unique=True, nullable=False, index=True)  # PAY-2025-0001

    # Amount
    amount = Column(Numeric(10, 2), nullable=False)  # Positive for payment, negative for refund

    # Payment Method
    payment_method = Column(String(50), nullable=False)  # cash, check, credit_card, paypal, stripe, venmo, zelle, wire, other

    # Transaction Details
    transaction_id = Column(String(255), nullable=True)  # External transaction ID (Stripe, PayPal, etc.)
    check_number = Column(String(50), nullable=True)  # For check payments

    # Payment Type
    payment_type = Column(String(20), nullable=False, default="payment")  # payment, refund, adjustment

    # Status
    status = Column(String(20), nullable=False, default="completed", index=True)  # pending, completed, failed, voided

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    payment_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)  # When payment was made
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # When record was created
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sales_order = relationship("SalesOrder", back_populates="payments")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])

    def __repr__(self):
        return f"<Payment {self.payment_number} - ${self.amount} ({self.payment_method})>"

    @property
    def is_refund(self) -> bool:
        """Check if this is a refund"""
        return self.payment_type == "refund" or self.amount < 0
