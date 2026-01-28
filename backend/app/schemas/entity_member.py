"""
Entity Member Schemas

Pydantic models for LLC member/partner CRUD operations.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Literal

from pydantic import BaseModel, Field


class EntityMemberCreate(BaseModel):
    """Create a new entity member."""

    name: str = Field(..., min_length=1, max_length=255)
    member_type: Literal["individual", "entity", "trust"] = "individual"
    tax_id_last4: Optional[str] = Field(None, max_length=4, pattern=r"^\d{4}$")

    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip: Optional[str] = Field(None, max_length=20)

    # Ownership
    ownership_percentage: Decimal = Field(..., ge=0, le=100)
    capital_account: Decimal = Field(default=Decimal("0"))

    # Status
    is_managing_member: bool = False
    effective_date: date


class EntityMemberUpdate(BaseModel):
    """Update an existing entity member."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    member_type: Optional[Literal["individual", "entity", "trust"]] = None
    tax_id_last4: Optional[str] = Field(None, max_length=4, pattern=r"^\d{4}$")

    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip: Optional[str] = Field(None, max_length=20)

    # Ownership
    ownership_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    capital_account: Optional[Decimal] = None

    # Status
    is_managing_member: Optional[bool] = None
    status: Optional[Literal["active", "inactive", "withdrawn"]] = None
    effective_date: Optional[date] = None
    end_date: Optional[date] = None


class EntityMemberResponse(BaseModel):
    """Entity member response."""

    id: int
    name: str
    member_type: str
    tax_id_last4: Optional[str] = None

    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None

    # Ownership
    ownership_percentage: Decimal
    capital_account: Decimal

    # Status
    is_managing_member: bool
    status: str
    effective_date: date
    end_date: Optional[date] = None

    # Audit
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EntityMemberListResponse(BaseModel):
    """List of entity members with summary."""

    members: List[EntityMemberResponse]
    total_ownership: Decimal
    member_count: int
    active_count: int


class CapitalTransactionCreate(BaseModel):
    """Record a capital contribution or distribution."""

    amount: Decimal = Field(..., description="Positive for contribution, negative for distribution")
    description: Optional[str] = Field(None, max_length=500)
    transaction_date: date
