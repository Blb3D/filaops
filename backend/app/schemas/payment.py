"""
Payment Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ============================================================================
# Request Schemas
# ============================================================================

class PaymentCreate(BaseModel):
    """Record a new payment"""
    sales_order_id: int = Field(..., description="Sales order ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount (positive)")
    payment_method: str = Field(..., description="Payment method: cash, check, credit_card, paypal, stripe, venmo, zelle, wire, other")
    payment_date: Optional[datetime] = Field(None, description="Payment date (defaults to now)")
    transaction_id: Optional[str] = Field(None, max_length=255, description="External transaction ID")
    check_number: Optional[str] = Field(None, max_length=50, description="Check number (for check payments)")
    notes: Optional[str] = Field(None, max_length=1000, description="Payment notes")


class RefundCreate(BaseModel):
    """Record a refund"""
    sales_order_id: int = Field(..., description="Sales order ID")
    amount: Decimal = Field(..., gt=0, description="Refund amount (positive, will be recorded as negative)")
    payment_method: str = Field(..., description="Refund method")
    payment_date: Optional[datetime] = Field(None, description="Refund date (defaults to now)")
    transaction_id: Optional[str] = Field(None, max_length=255, description="Refund transaction ID")
    notes: Optional[str] = Field(None, max_length=1000, description="Refund reason/notes")


class PaymentUpdate(BaseModel):
    """Update payment record (limited fields)"""
    notes: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, description="Payment status: pending, completed, failed, voided")


# ============================================================================
# Response Schemas
# ============================================================================

class PaymentResponse(BaseModel):
    """Payment record response"""
    id: int
    payment_number: str
    sales_order_id: int
    order_number: Optional[str] = None  # Populated from relationship

    amount: Decimal
    payment_method: str
    payment_type: str
    status: str

    transaction_id: Optional[str] = None
    check_number: Optional[str] = None
    notes: Optional[str] = None

    payment_date: datetime
    created_at: datetime
    recorded_by_name: Optional[str] = None  # Populated from relationship

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    """Paginated list of payments"""
    items: List[PaymentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaymentSummary(BaseModel):
    """Payment summary for an order"""
    order_total: Decimal
    total_paid: Decimal
    total_refunded: Decimal
    balance_due: Decimal
    payment_count: int
    last_payment_date: Optional[datetime] = None


class PaymentDashboardStats(BaseModel):
    """Payment dashboard statistics"""
    # Today
    payments_today: int
    amount_today: Decimal

    # This week
    payments_this_week: int
    amount_this_week: Decimal

    # This month
    payments_this_month: int
    amount_this_month: Decimal

    # Outstanding
    orders_with_balance: int
    total_outstanding: Decimal

    # By method (this month)
    by_method: dict  # {"cash": 1500.00, "credit_card": 3200.00, ...}
