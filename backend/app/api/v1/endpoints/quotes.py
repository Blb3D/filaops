"""
Quote Management Endpoints - Community Edition

Manual quote creation and management for small businesses.
Supports creating quotes, updating status, and converting to sales orders.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.db.session import get_db
from app.models.user import User
from app.models.quote import Quote
from app.models.sales_order import SalesOrder
from app.models.company_settings import CompanySettings
from app.logging_config import get_logger
from app.api.v1.endpoints.auth import get_current_user
from pydantic import BaseModel, Field

logger = get_logger(__name__)

router = APIRouter(prefix="/quotes", tags=["Quotes"])


# ============================================================================
# SCHEMAS (Community Edition - Manual Quotes)
# ============================================================================

class ManualQuoteCreate(BaseModel):
    """Schema for creating a manual quote"""
    product_name: str = Field(..., max_length=255, description="Product/item name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    quantity: int = Field(1, ge=1, le=10000, description="Quantity")
    unit_price: Decimal = Field(..., ge=0, description="Price per unit")

    # Customer info
    customer_id: Optional[int] = Field(None, description="Link to customer record (users table)")
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_email: Optional[str] = Field(None, max_length=255)

    # Optional details
    material_type: Optional[str] = Field("PLA", max_length=50)
    color: Optional[str] = Field(None, max_length=50)

    # Tax (if not provided, will use company settings default)
    apply_tax: Optional[bool] = Field(None, description="Whether to apply tax (uses company settings if None)")

    # Notes
    customer_notes: Optional[str] = Field(None, max_length=1000)
    admin_notes: Optional[str] = Field(None, max_length=1000)

    # Validity
    valid_days: int = Field(30, ge=1, le=365, description="Days until quote expires")


class ManualQuoteUpdate(BaseModel):
    """Schema for updating a quote"""
    product_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    quantity: Optional[int] = Field(None, ge=1, le=10000)
    unit_price: Optional[Decimal] = Field(None, ge=0)

    customer_id: Optional[int] = Field(None, description="Link to customer record")
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_email: Optional[str] = Field(None, max_length=255)

    material_type: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=50)

    # Tax
    apply_tax: Optional[bool] = Field(None, description="Whether to apply tax")

    customer_notes: Optional[str] = Field(None, max_length=1000)
    admin_notes: Optional[str] = Field(None, max_length=1000)

    # Shipping address
    shipping_name: Optional[str] = Field(None, max_length=200)
    shipping_address_line1: Optional[str] = Field(None, max_length=255)
    shipping_address_line2: Optional[str] = Field(None, max_length=255)
    shipping_city: Optional[str] = Field(None, max_length=100)
    shipping_state: Optional[str] = Field(None, max_length=50)
    shipping_zip: Optional[str] = Field(None, max_length=20)
    shipping_country: Optional[str] = Field(None, max_length=100)
    shipping_phone: Optional[str] = Field(None, max_length=30)


class QuoteStatusUpdate(BaseModel):
    """Schema for updating quote status"""
    status: str = Field(..., description="New status: pending, approved, rejected, accepted, cancelled")
    rejection_reason: Optional[str] = Field(None, max_length=500)
    admin_notes: Optional[str] = Field(None, max_length=1000)


class QuoteListItem(BaseModel):
    """Quote list item response"""
    id: int
    quote_number: str
    product_name: Optional[str]
    quantity: int
    unit_price: Optional[Decimal]
    subtotal: Optional[Decimal]
    tax_rate: Optional[Decimal]
    tax_amount: Optional[Decimal]
    total_price: Decimal
    status: str
    customer_id: Optional[int]
    customer_name: Optional[str]
    customer_email: Optional[str]
    material_type: Optional[str]
    color: Optional[str]
    has_image: bool = False
    created_at: datetime
    expires_at: datetime
    sales_order_id: Optional[int]

    model_config = {"from_attributes": True}


class QuoteDetail(QuoteListItem):
    """Full quote detail response"""
    description: Optional[str] = None  # May not exist on legacy quotes
    customer_notes: Optional[str]
    admin_notes: Optional[str]
    rejection_reason: Optional[str]

    # Shipping
    shipping_name: Optional[str]
    shipping_address_line1: Optional[str]
    shipping_address_line2: Optional[str]
    shipping_city: Optional[str]
    shipping_state: Optional[str]
    shipping_zip: Optional[str]
    shipping_country: Optional[str]
    shipping_phone: Optional[str]

    updated_at: datetime
    approved_at: Optional[datetime]
    converted_at: Optional[datetime]


class QuoteStatsResponse(BaseModel):
    """Quote statistics for dashboard"""
    total: int
    pending: int
    approved: int
    accepted: int
    rejected: int
    converted: int
    expired: int
    total_value: Decimal
    pending_value: Decimal


# ============================================================================
# HELPER: Generate Quote Number
# ============================================================================

def generate_quote_number(db: Session) -> str:
    """Generate next quote number in format Q-YYYY-NNN"""
    year = datetime.utcnow().year

    # Get the highest quote number for this year
    last_quote = db.query(Quote).filter(
        Quote.quote_number.like(f"Q-{year}-%")
    ).order_by(desc(Quote.quote_number)).first()

    if last_quote:
        # Extract sequence number and increment
        try:
            seq = int(last_quote.quote_number.split("-")[2])
            next_seq = seq + 1
        except (IndexError, ValueError):
            next_seq = 1
    else:
        next_seq = 1

    return f"Q-{year}-{next_seq:03d}"


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[QuoteListItem])
async def list_quotes(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by quote number, product name, or customer"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all quotes with optional filtering"""
    query = db.query(Quote).order_by(desc(Quote.created_at))

    if status:
        query = query.filter(Quote.status == status)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Quote.quote_number.ilike(search_term)) |
            (Quote.product_name.ilike(search_term)) |
            (Quote.customer_name.ilike(search_term)) |
            (Quote.customer_email.ilike(search_term))
        )

    quotes = query.offset(skip).limit(limit).all()
    return quotes


@router.get("/stats", response_model=QuoteStatsResponse)
async def get_quote_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get quote statistics for dashboard"""
    now = datetime.utcnow()

    total = db.query(Quote).count()
    pending = db.query(Quote).filter(Quote.status == "pending").count()
    approved = db.query(Quote).filter(Quote.status == "approved").count()
    accepted = db.query(Quote).filter(Quote.status == "accepted").count()
    rejected = db.query(Quote).filter(Quote.status == "rejected").count()
    converted = db.query(Quote).filter(Quote.status == "converted").count()
    expired = db.query(Quote).filter(
        Quote.status.in_(["pending", "approved"]),
        Quote.expires_at < now
    ).count()

    total_value = db.query(func.sum(Quote.total_price)).scalar() or Decimal("0")
    pending_value = db.query(func.sum(Quote.total_price)).filter(
        Quote.status == "pending"
    ).scalar() or Decimal("0")

    return QuoteStatsResponse(
        total=total,
        pending=pending,
        approved=approved,
        accepted=accepted,
        rejected=rejected,
        converted=converted,
        expired=expired,
        total_value=total_value,
        pending_value=pending_value,
    )


@router.get("/{quote_id}", response_model=QuoteDetail)
async def get_quote(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get quote details"""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote {quote_id} not found"
        )
    return quote


@router.post("/", response_model=QuoteDetail, status_code=status.HTTP_201_CREATED)
async def create_quote(
    request: ManualQuoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new manual quote"""
    quote_number = generate_quote_number(db)
    expires_at = datetime.utcnow() + timedelta(days=request.valid_days)

    # Calculate subtotal
    subtotal = request.unit_price * request.quantity

    # Get company settings for tax
    company_settings = db.query(CompanySettings).filter(CompanySettings.id == 1).first()

    # Determine if tax should be applied
    apply_tax = request.apply_tax
    if apply_tax is None and company_settings:
        apply_tax = company_settings.tax_enabled

    # Calculate tax
    tax_rate = None
    tax_amount = None
    total_price = subtotal

    if apply_tax and company_settings and company_settings.tax_rate:
        tax_rate = company_settings.tax_rate
        tax_amount = subtotal * tax_rate
        total_price = subtotal + tax_amount

    # Validate customer_id if provided
    if request.customer_id:
        customer = db.query(User).filter(
            User.id == request.customer_id,
            User.account_type == "customer"
        ).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer_id - customer not found"
            )

    quote = Quote(
        quote_number=quote_number,
        user_id=current_user.id,
        product_name=request.product_name,
        quantity=request.quantity,
        unit_price=request.unit_price,
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total_price=total_price,
        material_type=request.material_type or "PLA",
        color=request.color,
        customer_id=request.customer_id,
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        customer_notes=request.customer_notes,
        admin_notes=request.admin_notes,
        status="pending",
        file_format="manual",  # Indicates manually created
        file_size_bytes=0,
        expires_at=expires_at,
    )

    db.add(quote)
    db.commit()
    db.refresh(quote)

    logger.info(f"Quote {quote_number} created by user {current_user.email}")
    return quote


@router.patch("/{quote_id}", response_model=QuoteDetail)
async def update_quote(
    quote_id: int,
    request: ManualQuoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update quote details"""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote {quote_id} not found"
        )

    # Don't allow editing converted quotes
    if quote.status == "converted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit a converted quote"
        )

    # Validate customer_id if provided
    if request.customer_id is not None:
        if request.customer_id:  # Not zero/null
            customer = db.query(User).filter(
                User.id == request.customer_id,
                User.account_type == "customer"
            ).first()
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid customer_id - customer not found"
                )

    # Update fields (exclude apply_tax as it's not a model field)
    update_data = request.model_dump(exclude_unset=True)
    apply_tax = update_data.pop("apply_tax", None)

    for field, value in update_data.items():
        setattr(quote, field, value)

    # Recalculate pricing if price, quantity, or tax setting changed
    if request.unit_price is not None or request.quantity is not None or apply_tax is not None:
        unit_price = request.unit_price if request.unit_price is not None else quote.unit_price
        quantity = request.quantity if request.quantity is not None else quote.quantity
        subtotal = unit_price * quantity
        quote.subtotal = subtotal

        # Handle tax calculation
        if apply_tax is not None:
            if apply_tax:
                # Get company settings for tax rate
                company_settings = db.query(CompanySettings).filter(CompanySettings.id == 1).first()
                if company_settings and company_settings.tax_rate:
                    quote.tax_rate = company_settings.tax_rate
                    quote.tax_amount = subtotal * company_settings.tax_rate
                    quote.total_price = subtotal + quote.tax_amount
                else:
                    quote.tax_rate = None
                    quote.tax_amount = None
                    quote.total_price = subtotal
            else:
                # Remove tax
                quote.tax_rate = None
                quote.tax_amount = None
                quote.total_price = subtotal
        else:
            # Keep existing tax settings, just recalculate with new subtotal
            if quote.tax_rate:
                quote.tax_amount = subtotal * quote.tax_rate
                quote.total_price = subtotal + quote.tax_amount
            else:
                quote.total_price = subtotal

    quote.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(quote)

    logger.info(f"Quote {quote.quote_number} updated by user {current_user.email}")
    return quote


@router.patch("/{quote_id}/status", response_model=QuoteDetail)
async def update_quote_status(
    quote_id: int,
    request: QuoteStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update quote status (approve, reject, cancel, accept)"""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote {quote_id} not found"
        )

    allowed_statuses = ["pending", "approved", "rejected", "accepted", "cancelled"]
    if request.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed: {', '.join(allowed_statuses)}"
        )

    # Validate status transitions
    if quote.status == "converted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change status of a converted quote"
        )

    old_status = quote.status
    quote.status = request.status

    if request.status == "approved":
        quote.approved_at = datetime.utcnow()
        quote.approved_by = current_user.id
        quote.approval_method = "manual"

    if request.status == "rejected":
        quote.rejection_reason = request.rejection_reason

    if request.admin_notes:
        quote.admin_notes = request.admin_notes

    quote.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(quote)

    logger.info(f"Quote {quote.quote_number} status changed from {old_status} to {request.status} by {current_user.email}")
    return quote


@router.post("/{quote_id}/convert", status_code=status.HTTP_201_CREATED)
async def convert_quote_to_order(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Convert an accepted/approved quote to a sales order"""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote {quote_id} not found"
        )

    # Check quote can be converted
    if quote.status not in ["approved", "accepted"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quote must be approved or accepted to convert. Current status: {quote.status}"
        )

    if quote.sales_order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quote already converted to order {quote.sales_order_id}"
        )

    # Check if expired
    if quote.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote has expired"
        )

    # Generate order number
    year = datetime.utcnow().year
    last_order = db.query(SalesOrder).filter(
        SalesOrder.order_number.like(f"SO-{year}-%")
    ).order_by(desc(SalesOrder.order_number)).first()

    if last_order:
        try:
            seq = int(last_order.order_number.split("-")[2])
            next_seq = seq + 1
        except (IndexError, ValueError):
            next_seq = 1
    else:
        next_seq = 1

    order_number = f"SO-{year}-{next_seq:04d}"

    # Build shipping address string
    shipping_parts = []
    if quote.shipping_name:
        shipping_parts.append(quote.shipping_name)
    if quote.shipping_address_line1:
        shipping_parts.append(quote.shipping_address_line1)
    if quote.shipping_address_line2:
        shipping_parts.append(quote.shipping_address_line2)
    if quote.shipping_city or quote.shipping_state or quote.shipping_zip:
        city_state_zip = f"{quote.shipping_city or ''}, {quote.shipping_state or ''} {quote.shipping_zip or ''}".strip(", ")
        shipping_parts.append(city_state_zip)
    if quote.shipping_country and quote.shipping_country != "USA":
        shipping_parts.append(quote.shipping_country)

    shipping_address = "\n".join(shipping_parts) if shipping_parts else None

    # Create sales order
    sales_order = SalesOrder(
        order_number=order_number,
        quote_id=quote.id,
        order_type="quote",
        product_name=quote.product_name,
        quantity=quote.quantity,
        unit_price=quote.unit_price,
        subtotal=quote.total_price,
        grand_total=quote.total_price,
        status="pending",
        payment_status="pending",
        customer_email=quote.customer_email,
        customer_notes=quote.customer_notes,
        shipping_address=shipping_address,
    )

    db.add(sales_order)
    db.flush()  # Get the ID

    # Update quote
    quote.status = "converted"
    quote.sales_order_id = sales_order.id
    quote.converted_at = datetime.utcnow()
    quote.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(sales_order)

    logger.info(f"Quote {quote.quote_number} converted to order {order_number} by {current_user.email}")

    return {
        "message": f"Quote converted to order {order_number}",
        "order_id": sales_order.id,
        "order_number": order_number,
    }


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a quote (only if not converted)"""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote {quote_id} not found"
        )

    if quote.status == "converted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a converted quote"
        )

    db.delete(quote)
    db.commit()

    logger.info(f"Quote {quote.quote_number} deleted by {current_user.email}")


# ============================================================================
# QUOTE IMAGE ENDPOINTS
# ============================================================================

@router.post("/{quote_id}/image")
async def upload_quote_image(
    quote_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload an image for a quote (product photo/render)"""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote {quote_id} not found"
        )

    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: PNG, JPEG, GIF, WebP"
        )

    # Limit file size (5MB for product images)
    max_size = 5 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size: 5MB"
        )

    quote.image_data = content
    quote.image_filename = file.filename
    quote.image_mime_type = file.content_type
    quote.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"Image uploaded for quote {quote.quote_number} by {current_user.email}")
    return {"message": "Image uploaded successfully", "filename": file.filename}


@router.get("/{quote_id}/image")
async def get_quote_image(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the image for a quote"""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote {quote_id} not found"
        )

    if not quote.image_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No image uploaded for this quote"
        )

    return Response(
        content=quote.image_data,
        media_type=quote.image_mime_type or "image/png",
        headers={
            "Content-Disposition": f'inline; filename="{quote.image_filename or "quote_image.png"}"'
        }
    )


@router.delete("/{quote_id}/image")
async def delete_quote_image(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete the image for a quote"""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote {quote_id} not found"
        )

    quote.image_data = None
    quote.image_filename = None
    quote.image_mime_type = None
    quote.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"Image deleted for quote {quote.quote_number} by {current_user.email}")
    return {"message": "Image deleted"}


# ============================================================================
# PDF GENERATION
# ============================================================================

@router.get("/{quote_id}/pdf")
async def generate_quote_pdf(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a PDF for a quote using ReportLab with company logo, image, and tax"""
    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote {quote_id} not found"
        )

    # Get company settings
    company_settings = db.query(CompanySettings).filter(CompanySettings.id == 1).first()

    # Create PDF buffer
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#2563eb'))
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=12, textColor=colors.gray)
    normal_style = styles['Normal']
    small_style = ParagraphStyle('Small', parent=normal_style, fontSize=9)

    # Build content
    content = []

    # Header with logo
    if company_settings and company_settings.logo_data:
        try:
            logo_buffer = io.BytesIO(company_settings.logo_data)
            logo_img = Image(logo_buffer, width=1.5*inch, height=1.5*inch)
            logo_img.hAlign = 'LEFT'

            # Company info for header
            company_info = []
            if company_settings.company_name:
                company_info.append(f"<b>{company_settings.company_name}</b>")
            if company_settings.company_address_line1:
                company_info.append(company_settings.company_address_line1)
            if company_settings.company_city or company_settings.company_state:
                city_state = f"{company_settings.company_city or ''}, {company_settings.company_state or ''} {company_settings.company_zip or ''}".strip(", ")
                company_info.append(city_state)
            if company_settings.company_phone:
                company_info.append(company_settings.company_phone)
            if company_settings.company_email:
                company_info.append(company_settings.company_email)

            # Create header table with logo and company info
            header_data = [[logo_img, Paragraph("<br/>".join(company_info), normal_style)]]
            header_table = Table(header_data, colWidths=[2*inch, 4.5*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            content.append(header_table)
            content.append(Spacer(1, 0.3*inch))
        except Exception:
            # If logo fails, just continue without it
            pass
    elif company_settings and company_settings.company_name:
        # No logo but have company name
        content.append(Paragraph(f"<b>{company_settings.company_name}</b>", title_style))
        content.append(Spacer(1, 0.2*inch))

    # Quote title, customer info, and optional image in a compact layout
    # Build left column content (quote info + customer)
    left_content = []
    left_content.append(Paragraph("QUOTE", title_style))
    left_content.append(Paragraph(f"<b>{quote.quote_number}</b>", normal_style))
    left_content.append(Paragraph(f"Date: {quote.created_at.strftime('%B %d, %Y')}", normal_style))
    left_content.append(Spacer(1, 0.15*inch))
    left_content.append(Paragraph("CUSTOMER", heading_style))
    left_content.append(Paragraph(f"<b>{quote.customer_name or 'N/A'}</b>", normal_style))
    if quote.customer_email:
        left_content.append(Paragraph(quote.customer_email, normal_style))

    # If we have an image, create a two-column layout
    if quote.image_data:
        try:
            img_buffer = io.BytesIO(quote.image_data)
            # Scale image to fit nicely - max 2 inches
            quote_img = Image(img_buffer, width=2*inch, height=2*inch)
            quote_img.hAlign = 'RIGHT'

            # Create a table with quote info on left, image on right
            from reportlab.platypus import KeepTogether
            info_table = Table(
                [[left_content, quote_img]],
                colWidths=[4.5*inch, 2.2*inch]
            )
            info_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ]))
            content.append(info_table)
        except Exception:
            # If image fails, just use the left content
            for item in left_content:
                content.append(item)
    else:
        # No image - just add left content
        for item in left_content:
            content.append(item)

    content.append(Spacer(1, 0.2*inch))

    # Quote Details Table
    content.append(Paragraph("QUOTE DETAILS", heading_style))
    content.append(Spacer(1, 0.1*inch))

    material_desc = quote.material_type or 'N/A'
    if quote.color:
        material_desc += f" - {quote.color}"

    # Calculate subtotal
    subtotal = float(quote.subtotal) if quote.subtotal else float(quote.unit_price or 0) * quote.quantity

    # Build table with proper tax breakdown
    table_data = [
        ['Description', 'Material', 'Qty', 'Unit Price', 'Amount'],
        [
            quote.product_name or 'Custom Item',
            material_desc,
            str(quote.quantity),
            f"${float(quote.unit_price or 0):,.2f}",
            f"${subtotal:,.2f}"
        ],
    ]

    # Add subtotal row
    table_data.append(['', '', '', 'Subtotal:', f"${subtotal:,.2f}"])

    # Add tax row if applicable
    if quote.tax_rate and quote.tax_amount:
        tax_percent = float(quote.tax_rate) * 100
        tax_name = "Sales Tax"
        if company_settings and company_settings.tax_name:
            tax_name = company_settings.tax_name
        table_data.append(['', '', '', f'{tax_name} ({tax_percent:.2f}%):', f"${float(quote.tax_amount):,.2f}"])

    # Add total row
    table_data.append(['', '', '', 'TOTAL:', f"${float(quote.total_price or 0):,.2f}"])

    table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 0.5*inch, 1.2*inch, 0.8*inch])
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # Data rows
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        # Total row (last row) - bold
        ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (3, -1), (-1, -1), 1, colors.black),
        # Grid
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#e5e7eb')),
        ('LINEBELOW', (0, 1), (-1, 1), 0.5, colors.HexColor('#e5e7eb')),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
    ]))
    content.append(table)
    content.append(Spacer(1, 0.3*inch))

    # Notes
    if quote.customer_notes:
        content.append(Paragraph("NOTES", heading_style))
        content.append(Paragraph(quote.customer_notes, normal_style))
        content.append(Spacer(1, 0.2*inch))

    # Validity
    content.append(Spacer(1, 0.2*inch))
    validity_style = ParagraphStyle('Validity', parent=normal_style, backColor=colors.HexColor('#fef3c7'), borderPadding=10)
    content.append(Paragraph(
        f"<b>Quote Valid Until:</b> {quote.expires_at.strftime('%B %d, %Y')}",
        validity_style
    ))
    content.append(Spacer(1, 0.3*inch))

    # Terms (from company settings)
    if company_settings and company_settings.quote_terms:
        content.append(Paragraph("TERMS & CONDITIONS", heading_style))
        content.append(Paragraph(company_settings.quote_terms, small_style))
        content.append(Spacer(1, 0.2*inch))

    # Footer
    if company_settings and company_settings.quote_footer:
        content.append(Paragraph(company_settings.quote_footer, normal_style))
    else:
        content.append(Paragraph("Thank you for your business!", normal_style))
        content.append(Paragraph("To accept this quote, please contact us with your quote number.", normal_style))

    # Build PDF
    doc.build(content)
    pdf_buffer.seek(0)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{quote.quote_number}.pdf"'
        }
    )
