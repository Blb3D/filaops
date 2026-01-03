"""
Purchasing Pydantic Schemas

Covers:
- Vendors
- Purchase Orders
- PO Lines
- Receiving
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class POStatus(str, Enum):
    """Purchase order status workflow"""
    DRAFT = "draft"
    ORDERED = "ordered"
    SHIPPED = "shipped"
    RECEIVED = "received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


# ============================================================================
# Vendor Schemas
# ============================================================================

class VendorBase(BaseModel):
    """Base vendor fields"""
    name: str = Field(..., min_length=1, max_length=200, description="Vendor name")
    contact_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=500)

    # Address
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field("USA", max_length=100)

    # Business info
    payment_terms: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    lead_time_days: Optional[int] = Field(None, ge=0)
    rating: Optional[Decimal] = Field(None, ge=1, le=5)

    notes: Optional[str] = None
    is_active: bool = Field(True)


class VendorCreate(VendorBase):
    """Create a new vendor"""
    code: Optional[str] = Field(None, max_length=50, description="Optional code, auto-generated if not provided")


class VendorUpdate(BaseModel):
    """Update an existing vendor"""
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=500)

    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)

    payment_terms: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    lead_time_days: Optional[int] = Field(None, ge=0)
    rating: Optional[Decimal] = Field(None, ge=1, le=5)

    notes: Optional[str] = None
    is_active: Optional[bool] = None


class VendorListResponse(BaseModel):
    """Vendor list summary"""
    id: int
    code: str
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    payment_terms: Optional[str] = None
    is_active: bool
    po_count: int = 0  # Count of POs with this vendor

    class Config:
        from_attributes = True


class VendorResponse(VendorBase):
    """Full vendor details"""
    id: int
    code: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Purchase Order Line Schemas
# ============================================================================

class POLineBase(BaseModel):
    """Base PO line fields"""
    product_id: int = Field(..., description="Product/Item ID")
    quantity_ordered: Decimal = Field(..., gt=0, description="Quantity to order")
    unit_cost: Decimal = Field(..., ge=0, description="Cost per unit")
    purchase_unit: Optional[str] = Field(None, max_length=20, description="Unit of measure for purchase (e.g., G, KG, EA, LB)")
    notes: Optional[str] = None


class POLineCreate(POLineBase):
    """Create a new PO line"""
    pass


class POLineUpdate(BaseModel):
    """Update an existing PO line"""
    quantity_ordered: Optional[Decimal] = Field(None, gt=0)
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None


class POLineResponse(POLineBase):
    """PO line response"""
    id: int
    line_number: int
    quantity_received: Decimal
    line_total: Decimal
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    product_unit: Optional[str] = None  # Product's default unit
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Purchase Order Schemas
# ============================================================================

class PurchaseOrderBase(BaseModel):
    """Base PO fields"""
    vendor_id: int = Field(..., description="Vendor ID")
    order_date: Optional[date] = None
    expected_date: Optional[date] = None
    notes: Optional[str] = None

    # Shipping info
    tracking_number: Optional[str] = Field(None, max_length=200)
    carrier: Optional[str] = Field(None, max_length=100)

    # Financials
    tax_amount: Decimal = Field(Decimal("0"), ge=0)
    shipping_cost: Decimal = Field(Decimal("0"), ge=0)

    # Payment
    payment_method: Optional[str] = Field(None, max_length=100)
    payment_reference: Optional[str] = Field(None, max_length=200)

    # Document
    document_url: Optional[str] = Field(None, max_length=1000)


class PurchaseOrderCreate(PurchaseOrderBase):
    """Create a new PO"""
    lines: List[POLineCreate] = Field(default_factory=list)


class PurchaseOrderUpdate(BaseModel):
    """Update an existing PO"""
    vendor_id: Optional[int] = None
    order_date: Optional[date] = None
    expected_date: Optional[date] = None
    shipped_date: Optional[date] = None
    received_date: Optional[date] = None
    notes: Optional[str] = None

    tracking_number: Optional[str] = Field(None, max_length=200)
    carrier: Optional[str] = Field(None, max_length=100)

    tax_amount: Optional[Decimal] = Field(None, ge=0)
    shipping_cost: Optional[Decimal] = Field(None, ge=0)

    payment_method: Optional[str] = Field(None, max_length=100)
    payment_reference: Optional[str] = Field(None, max_length=200)

    document_url: Optional[str] = Field(None, max_length=1000)


class PurchaseOrderListResponse(BaseModel):
    """PO list summary"""
    id: int
    po_number: str
    vendor_id: int
    vendor_name: str
    status: str
    order_date: Optional[date] = None
    expected_date: Optional[date] = None
    received_date: Optional[date] = None
    total_amount: Decimal
    line_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseOrderResponse(PurchaseOrderBase):
    """Full PO details"""
    id: int
    po_number: str
    status: str
    shipped_date: Optional[date] = None
    received_date: Optional[date] = None
    subtotal: Decimal
    total_amount: Decimal
    vendor_name: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    lines: List[POLineResponse] = []

    class Config:
        from_attributes = True


# ============================================================================
# Status Update
# ============================================================================

class POStatusUpdate(BaseModel):
    """Update PO status"""
    status: POStatus
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None


# ============================================================================
# Receiving
# ============================================================================

class SpoolCreateData(BaseModel):
    """Data for creating a single spool"""
    weight_g: Decimal = Field(..., gt=0, description="Spool weight in GRAMS")
    spool_number: Optional[str] = Field(None, description="Auto-generated if not provided")
    supplier_lot_number: Optional[str] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class ReceiveLineItem(BaseModel):
    """Receive a single line item"""
    line_id: int
    quantity_received: Decimal = Field(..., gt=0)
    lot_number: Optional[str] = None
    vendor_lot_number: Optional[str] = Field(None, description="Vendor's lot number for traceability")
    notes: Optional[str] = None
    create_spools: bool = Field(False, description="Whether to create material spools")
    spools: Optional[List[SpoolCreateData]] = Field(None, description="Individual spool data if creating spools")


class ReceivePORequest(BaseModel):
    """Receive items from a PO"""
    lines: List[ReceiveLineItem]
    location_id: Optional[int] = None  # Inventory location
    notes: Optional[str] = None
    received_date: Optional[date] = Field(
        None,
        description="Actual date items were received (defaults to today if not provided)"
    )


class ReceivePOResponse(BaseModel):
    """Result of receiving"""
    po_number: str
    lines_received: int
    total_quantity: Decimal
    inventory_updated: bool
    transactions_created: List[int] = []  # IDs of inventory transactions
    spools_created: List[str] = []  # List of spool numbers created
    material_lots_created: List[str] = []  # Lot numbers for traceability


# ============================================================================
# Document Schemas
# ============================================================================

class DocumentType(str, Enum):
    """Types of documents that can be attached to a PO"""
    INVOICE = "invoice"
    PACKING_SLIP = "packing_slip"
    RECEIPT = "receipt"
    QUOTE = "quote"
    SHIPPING_LABEL = "shipping_label"
    OTHER = "other"


class PODocumentBase(BaseModel):
    """Base document fields"""
    document_type: DocumentType = Field(..., description="Type of document")
    notes: Optional[str] = None


class PODocumentCreate(PODocumentBase):
    """Create a new document (file comes via multipart form)"""
    pass


class PODocumentUpdate(BaseModel):
    """Update document metadata"""
    document_type: Optional[DocumentType] = None
    notes: Optional[str] = None


class PODocumentResponse(BaseModel):
    """Document response"""
    id: int
    purchase_order_id: int
    document_type: str
    file_name: str
    original_file_name: Optional[str] = None
    file_url: Optional[str] = None
    file_path: Optional[str] = None
    storage_type: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    google_drive_id: Optional[str] = None
    notes: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    download_url: Optional[str] = None  # Computed URL for downloading
    preview_url: Optional[str] = None  # Computed URL for preview (Google Drive)

    class Config:
        from_attributes = True


# ============================================================================
# Vendor Item (SKU Mapping) Schemas
# ============================================================================

class VendorItemBase(BaseModel):
    """Base vendor item fields"""
    vendor_sku: str = Field(..., max_length=100, description="Vendor's SKU/part number")
    vendor_description: Optional[str] = Field(None, max_length=500)
    product_id: Optional[int] = Field(None, description="Mapped FilaOps product ID")
    default_unit_cost: Optional[Decimal] = Field(None, ge=0)
    default_purchase_unit: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class VendorItemCreate(VendorItemBase):
    """Create a new vendor item mapping"""
    pass


class VendorItemUpdate(BaseModel):
    """Update vendor item mapping"""
    vendor_description: Optional[str] = Field(None, max_length=500)
    product_id: Optional[int] = None
    default_unit_cost: Optional[Decimal] = Field(None, ge=0)
    default_purchase_unit: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class VendorItemResponse(VendorItemBase):
    """Vendor item response"""
    id: int
    vendor_id: int
    last_seen_at: Optional[datetime] = None
    times_ordered: int = 0
    created_at: datetime
    updated_at: datetime
    # Joined product info
    product_sku: Optional[str] = None
    product_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# QuickBooks Export Schemas
# ============================================================================

class QBExportType(str, Enum):
    """QuickBooks export types"""
    EXPENSE = "expense"  # Direct expenses (credit card purchases)
    BILL = "bill"  # Accounts payable
    CHECK = "check"  # Check register


class QBExportFormat(str, Enum):
    """QuickBooks export formats"""
    CSV = "csv"  # Universal CSV
    IIF = "iif"  # QuickBooks Desktop Interchange Format


class QBExportRequest(BaseModel):
    """Request for QuickBooks export"""
    start_date: date
    end_date: date
    export_type: QBExportType = QBExportType.EXPENSE
    format: QBExportFormat = QBExportFormat.CSV
    include_tax: bool = True
    include_shipping: bool = True
    include_line_detail: bool = False
    status_filter: Optional[List[str]] = Field(
        default=["received", "closed"],
        description="Only export POs with these statuses"
    )


class QBExportPreviewLine(BaseModel):
    """Preview line for QB export"""
    date: date
    vendor: str
    po_number: str
    account: str
    amount: Decimal
    memo: str
    class_name: Optional[str] = None


class QBExportPreviewResponse(BaseModel):
    """Preview of QB export before download"""
    total_pos: int
    total_amount: Decimal
    date_range: str
    lines: List[QBExportPreviewLine]


# ============================================================================
# Low Stock → PO Workflow Schemas
# ============================================================================

class LowStockItem(BaseModel):
    """A product that's below its reorder point"""
    product_id: int
    sku: str
    name: str
    current_qty: Decimal
    reorder_point: Decimal
    reorder_qty: Decimal
    shortage: Decimal  # How much below reorder point
    unit: str
    purchase_uom: Optional[str] = None
    last_cost: Optional[Decimal] = None
    preferred_vendor_id: Optional[int] = None
    preferred_vendor_name: Optional[str] = None

    class Config:
        from_attributes = True


class LowStockByVendor(BaseModel):
    """Low stock items grouped by vendor"""
    vendor_id: Optional[int] = None
    vendor_name: str
    vendor_code: Optional[str] = None
    items: List[LowStockItem]
    total_estimated_cost: Decimal


class LowStockResponse(BaseModel):
    """Response with low stock items grouped by vendor"""
    total_items: int
    vendors: List[LowStockByVendor]


class CreatePOFromLowStockItem(BaseModel):
    """Single item for PO creation from low stock"""
    product_id: int
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    purchase_unit: Optional[str] = None


class CreatePOFromLowStockRequest(BaseModel):
    """Request to create PO from selected low stock items"""
    vendor_id: int
    items: List[CreatePOFromLowStockItem]
    notes: Optional[str] = None
