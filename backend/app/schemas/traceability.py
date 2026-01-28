"""
Pydantic schemas for Traceability - Serial Numbers, Material Lots, and Customer Profiles
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


# =============================================================================
# Customer Traceability Profile Schemas
# =============================================================================


class CustomerTraceabilityProfileBase(BaseModel):
    """Base schema for customer traceability profiles."""

    traceability_level: str = Field(default="none", description="none, lot, serial, or full")
    requires_coc: bool = Field(default=False, description="Requires Certificate of Conformance")
    requires_coa: bool = Field(default=False, description="Requires Certificate of Analysis")
    requires_first_article: bool = Field(default=False, description="Requires First Article Inspection")
    record_retention_days: int = Field(default=2555, description="Document retention period in days")
    custom_serial_prefix: Optional[str] = Field(default=None, max_length=20)
    compliance_standards: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class CustomerTraceabilityProfileCreate(CustomerTraceabilityProfileBase):
    """Schema for creating a customer traceability profile."""

    user_id: int


class CustomerTraceabilityProfileUpdate(BaseModel):
    """Schema for updating a customer traceability profile."""

    traceability_level: Optional[str] = None
    requires_coc: Optional[bool] = None
    requires_coa: Optional[bool] = None
    requires_first_article: Optional[bool] = None
    record_retention_days: Optional[int] = None
    custom_serial_prefix: Optional[str] = None
    compliance_standards: Optional[str] = None
    notes: Optional[str] = None


class CustomerTraceabilityProfileResponse(CustomerTraceabilityProfileBase):
    """Response schema for customer traceability profile."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Material Lot Schemas
# =============================================================================


class MaterialLotBase(BaseModel):
    """Base schema for material lots."""

    lot_number: str = Field(..., max_length=100)
    product_id: int
    vendor_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    vendor_lot_number: Optional[str] = Field(default=None, max_length=100)
    quantity_received: Decimal = Field(..., ge=0)
    status: str = Field(default="active", description="active, depleted, quarantine, expired, recalled")
    certificate_of_analysis: Optional[str] = None
    coa_file_path: Optional[str] = None
    inspection_status: str = Field(default="pending", description="pending, passed, failed, waived")
    manufactured_date: Optional[date] = None
    expiration_date: Optional[date] = None
    received_date: Optional[date] = None
    unit_cost: Optional[Decimal] = None
    location: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None


class MaterialLotCreate(MaterialLotBase):
    """Schema for creating a material lot."""

    pass


class MaterialLotUpdate(BaseModel):
    """Schema for updating a material lot."""

    vendor_lot_number: Optional[str] = None
    status: Optional[str] = None
    certificate_of_analysis: Optional[str] = None
    coa_file_path: Optional[str] = None
    inspection_status: Optional[str] = None
    expiration_date: Optional[date] = None
    unit_cost: Optional[Decimal] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    quantity_scrapped: Optional[Decimal] = None
    quantity_adjusted: Optional[Decimal] = None


class MaterialLotResponse(MaterialLotBase):
    """Response schema for material lot."""

    id: int
    quantity_consumed: Decimal
    quantity_scrapped: Decimal
    quantity_adjusted: Decimal
    quantity_remaining: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MaterialLotListResponse(BaseModel):
    """List response for material lots."""

    items: List[MaterialLotResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Serial Number Schemas
# =============================================================================


class SerialNumberBase(BaseModel):
    """Base schema for serial numbers."""

    serial_number: str = Field(..., max_length=50)
    product_id: int
    production_order_id: int
    status: str = Field(default="manufactured", description="manufactured, in_stock, sold, shipped, returned, scrapped")
    qc_passed: bool = Field(default=True)
    qc_date: Optional[datetime] = None
    qc_notes: Optional[str] = None


class SerialNumberCreate(BaseModel):
    """Schema for creating serial numbers (typically auto-generated)."""

    product_id: int
    production_order_id: int
    quantity: int = Field(default=1, ge=1, description="Number of serials to generate")
    qc_passed: bool = Field(default=True)
    qc_notes: Optional[str] = None


class SerialNumberUpdate(BaseModel):
    """Schema for updating a serial number."""

    status: Optional[str] = None
    qc_passed: Optional[bool] = None
    qc_date: Optional[datetime] = None
    qc_notes: Optional[str] = None
    sales_order_id: Optional[int] = None
    sales_order_line_id: Optional[int] = None
    tracking_number: Optional[str] = None
    return_reason: Optional[str] = None


class SerialNumberResponse(BaseModel):
    """Response schema for serial number."""

    id: int
    serial_number: str
    product_id: int
    production_order_id: int
    status: str
    qc_passed: bool
    qc_date: Optional[datetime] = None
    qc_notes: Optional[str] = None
    sales_order_id: Optional[int] = None
    sales_order_line_id: Optional[int] = None
    sold_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    tracking_number: Optional[str] = None
    returned_at: Optional[datetime] = None
    return_reason: Optional[str] = None
    manufactured_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SerialNumberListResponse(BaseModel):
    """List response for serial numbers."""

    items: List[SerialNumberResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Production Lot Consumption Schemas
# =============================================================================


class ProductionLotConsumptionBase(BaseModel):
    """Base schema for production lot consumption."""

    production_order_id: int
    material_lot_id: int
    serial_number_id: Optional[int] = None
    bom_line_id: Optional[int] = None
    quantity_consumed: Decimal = Field(..., ge=0)


class ProductionLotConsumptionCreate(ProductionLotConsumptionBase):
    """Schema for recording material consumption."""

    pass


class ProductionLotConsumptionResponse(ProductionLotConsumptionBase):
    """Response schema for production lot consumption."""

    id: int
    consumed_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Recall Query Schemas
# =============================================================================


class RecallForwardQueryRequest(BaseModel):
    """Request for forward recall query: What did we make with lot X?"""

    lot_number: str


class RecallBackwardQueryRequest(BaseModel):
    """Request for backward recall query: What went into serial Y?"""

    serial_number: str


class RecallAffectedProduct(BaseModel):
    """Products affected by a material lot recall."""

    serial_number: str
    product_name: str
    production_order_code: str
    manufactured_at: datetime
    status: str
    customer_email: Optional[str] = None
    sales_order_number: Optional[str] = None
    shipped_at: Optional[datetime] = None


class RecallForwardQueryResponse(BaseModel):
    """Response for forward recall query."""

    lot_number: str
    material_name: str
    quantity_received: Decimal
    quantity_consumed: Decimal
    affected_products: List[RecallAffectedProduct]
    total_affected: int


class MaterialLotUsed(BaseModel):
    """Material lot used in a product."""

    lot_number: str
    material_name: str
    vendor_name: Optional[str] = None
    vendor_lot_number: Optional[str] = None
    quantity_consumed: Decimal


class RecallBackwardQueryResponse(BaseModel):
    """Response for backward recall query."""

    serial_number: str
    product_name: str
    manufactured_at: datetime
    material_lots_used: List[MaterialLotUsed]
