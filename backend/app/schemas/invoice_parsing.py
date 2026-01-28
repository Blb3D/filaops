"""
Invoice Parsing Schemas

Pydantic models for invoice parsing and PO creation workflow.
"""

from datetime import date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class MatchConfidence(str, Enum):
    """Confidence level for product matching"""

    EXACT = "exact"  # Vendor SKU found in vendor_items
    FUZZY = "fuzzy"  # Similar SKU or description match
    NONE = "none"  # No match found


class ParsedInvoiceLine(BaseModel):
    """A single line item from a parsed invoice"""

    line_number: int = Field(..., description="Line number on invoice")
    vendor_sku: str = Field(..., description="Vendor's SKU/part number")
    description: str = Field("", description="Item description from invoice")
    quantity: Decimal = Field(..., ge=0)
    unit: str = Field("EA", description="Unit of measure (EA, KG, LB, etc.)")
    unit_cost: Decimal = Field(..., ge=0)
    line_total: Decimal = Field(..., ge=0)

    # Matching info (populated after parsing)
    matched_product_id: Optional[int] = None
    matched_product_sku: Optional[str] = None
    matched_product_name: Optional[str] = None
    match_confidence: MatchConfidence = MatchConfidence.NONE
    match_source: Optional[str] = None  # How the match was found

    # For review UI
    is_confirmed: bool = False  # User has confirmed this mapping
    user_product_id: Optional[int] = None  # User override


class ParsedInvoice(BaseModel):
    """Complete parsed invoice data"""

    # Vendor info
    vendor_name: str = Field(..., description="Detected vendor name")
    vendor_id: Optional[int] = Field(None, description="Matched vendor ID")
    vendor_confidence: MatchConfidence = MatchConfidence.NONE

    # Invoice metadata
    invoice_number: str = Field("", description="Invoice/reference number")
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None

    # Totals (detected from invoice)
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    shipping: Optional[Decimal] = None
    total: Optional[Decimal] = None

    # Line items
    lines: List[ParsedInvoiceLine] = []

    # Summary stats
    line_count: int = 0
    matched_count: int = 0
    unmapped_count: int = 0

    # Warnings/notes from parsing
    warnings: List[str] = []
    raw_text: Optional[str] = None  # For debugging

    # AI model info
    ai_model: Optional[str] = None  # Model used for parsing (e.g., "claude-opus-4-5-20251101")
    ai_provider: Optional[str] = None  # "anthropic", "ollama", or "basic"


class InvoiceParseRequest(BaseModel):
    """Request to parse an invoice file"""

    vendor_id: Optional[int] = Field(None, description="Pre-select vendor if known")
    file_type: Optional[str] = Field(None, description="Override file type detection")


class InvoiceParseResponse(BaseModel):
    """Response from invoice parsing"""

    success: bool
    parsed_invoice: Optional[ParsedInvoice] = None
    error: Optional[str] = None
    processing_time_ms: int = 0


class ConfirmedInvoiceLine(BaseModel):
    """A line item confirmed by user for PO creation"""

    vendor_sku: str
    product_id: int  # Must be mapped
    quantity: Decimal
    unit_cost: Decimal
    purchase_unit: str = "EA"
    notes: Optional[str] = None

    # Save mapping for future invoices
    save_mapping: bool = True


class CreatePOFromInvoiceRequest(BaseModel):
    """Request to create PO from parsed invoice"""

    vendor_id: int
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None

    lines: List[ConfirmedInvoiceLine]

    # Optional overrides
    tax: Optional[Decimal] = None
    shipping: Optional[Decimal] = None
    notes: Optional[str] = None

    # Attach original document
    attach_document: bool = True
    document_type: str = "invoice"  # invoice, packing_slip, quote, etc.
