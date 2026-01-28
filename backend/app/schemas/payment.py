"""
Payment Pydantic Schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal


# ============================================================================
# Request Schemas
# ============================================================================


class PaymentCreate(BaseModel):
    """Record a new payment"""

    sales_order_id: int = Field(..., description="Sales order ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount (positive)")
    payment_method: str = Field(
        ..., description="Payment method: cash, check, credit_card, paypal, stripe, venmo, zelle, wire, other"
    )
    payment_date: Optional[datetime] = Field(None, description="Payment date (defaults to now)")
    transaction_id: Optional[str] = Field(None, max_length=255, description="External transaction ID")
    check_number: Optional[str] = Field(None, max_length=50, description="Check number (for check payments)")
    notes: Optional[str] = Field(None, max_length=1000, description="Payment notes")

    @field_validator("payment_date")
    @classmethod
    def validate_payment_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate payment date is reasonable (between 2000-2099) and not in future"""
        if v is not None:
            if v.year < 2000 or v.year > 2099:
                raise ValueError("Payment date must be between year 2000 and 2099")

            # Payments shouldn't be dated more than 1 day in the future
            # (allow 1 day grace period for timezone differences)
            # Use timezone-aware datetime to avoid comparison issues
            now_utc = datetime.now(timezone.utc)
            future_limit = now_utc + timedelta(days=1)

            # Make v timezone-aware if it isn't already
            v_aware = v if v.tzinfo else v.replace(tzinfo=timezone.utc)

            if v_aware > future_limit:
                raise ValueError(
                    f"Payment date cannot be more than 1 day in the future. "
                    f"Provided: {v.date()}, Maximum allowed: {future_limit.date()}"
                )
        return v


class RefundCreate(BaseModel):
    """Record a refund"""

    sales_order_id: int = Field(..., description="Sales order ID")
    amount: Decimal = Field(..., gt=0, description="Refund amount (positive, will be recorded as negative)")
    payment_method: str = Field(..., description="Refund method")
    payment_date: Optional[datetime] = Field(None, description="Refund date (defaults to now)")
    transaction_id: Optional[str] = Field(None, max_length=255, description="Refund transaction ID")
    notes: Optional[str] = Field(None, max_length=1000, description="Refund reason/notes")

    @field_validator("payment_date")
    @classmethod
    def validate_payment_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate refund date is reasonable (between 2000-2099)"""
        if v is not None:
            if v.year < 2000 or v.year > 2099:
                raise ValueError("Refund date must be between year 2000 and 2099")
        return v


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
