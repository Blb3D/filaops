"""
Sales Order Management Endpoints

Handles converting quotes to sales orders and order lifecycle management
"""
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.models.user import User
from app.models.quote import Quote
from app.models.sales_order import SalesOrder, SalesOrderLine
from app.models.production_order import ProductionOrder
from app.models.product import Product
from app.models.bom import BOM, BOMLine
from app.models.inventory import Inventory
from app.models.manufacturing import Routing
from app.models.company_settings import CompanySettings
from app.logging_config import get_logger
from app.schemas.sales_order import (
    SalesOrderCreate,
    SalesOrderConvert,
    SalesOrderResponse,
    SalesOrderLineResponse,
    SalesOrderListResponse,
    SalesOrderUpdateStatus,
    SalesOrderUpdatePayment,
    SalesOrderUpdateShipping,
    SalesOrderUpdateAddress,
    SalesOrderCancel,
)
from app.schemas.order_event import (
    OrderEventCreate,
    OrderEventResponse,
    OrderEventListResponse,
)
from app.schemas.shipping_event import (
    ShippingEventCreate,
    ShippingEventResponse,
    ShippingEventListResponse,
)
from app.models.order_event import OrderEvent
from app.models.shipping_event import ShippingEvent
from app.api.v1.endpoints.auth import get_current_user
from app.services.event_service import record_shipping_event
from app.services.inventory_service import process_shipment, reserve_production_materials
from app.core.status_config import (
    SalesOrderStatus,
    PaymentStatus,
    get_allowed_sales_order_transitions,
)
from app.schemas.blocking_issues import SalesOrderBlockingIssues
from app.services.blocking_issues import get_sales_order_blocking_issues
from app.schemas.fulfillment_status import FulfillmentStatus
from app.services.fulfillment_status import get_fulfillment_status

logger = get_logger(__name__)

router = APIRouter(prefix="/sales-orders", tags=["Sales Orders"])


# ============================================================================
# HELPER: Create Production Orders for Sales Order
# ============================================================================

def _create_production_orders_for_so(order: SalesOrder, db: Session, created_by: str) -> List[str]:
    """
    Create production orders for a sales order.

    Returns list of created production order codes.
    """
    from sqlalchemy import desc as sql_desc

    created_orders = []
    year = datetime.utcnow().year

    def get_next_po_code():
        """
        Generate next PO code with row-level locking to prevent race conditions.
        Uses SELECT FOR UPDATE to lock the last row so concurrent requests don't
        generate duplicate codes.
        
        Note: When no rows exist, with_for_update() returns None and we start at 1.
        The unique constraint on ProductionOrder.code and IntegrityError retry logic
        provide additional protection against duplicates.
        """
        # Lock the last production order to prevent concurrent access
        # with_for_update() will lock the row if it exists, or return None if table is empty
        last_po = (
            db.query(ProductionOrder)
            .filter(ProductionOrder.code.like(f"PO-{year}-%"))
            .order_by(sql_desc(ProductionOrder.code))
            .with_for_update(skip_locked=False)  # Wait for lock, don't skip
            .first()
        )
        if last_po:
            last_num = int(last_po.code.split("-")[2])
            next_num = last_num + 1
        else:
            # No existing POs for this year - start at 1
            # Unique constraint on code column will prevent duplicates if concurrent
            next_num = 1
        return f"PO-{year}-{next_num:04d}"

    if order.order_type == "line_item": # pyright: ignore[reportGeneralTypeIssues]
        lines = db.query(SalesOrderLine).filter(
            SalesOrderLine.sales_order_id == order.id
        ).order_by(SalesOrderLine.id).all()

        for idx, line in enumerate(lines, start=1):
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if not product:
                continue

            # Only create WO for products with BOMs (make items)
            if not product.has_bom: # pyright: ignore[reportGeneralTypeIssues]
                continue

            bom = db.query(BOM).filter(
                BOM.product_id == line.product_id,
                BOM.active.is_(True)
            ).first()

            routing = db.query(Routing).filter(
                Routing.product_id == line.product_id,
                Routing.is_active.is_(True)
            ).first()

            # Retry logic to handle race condition if locking fails
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    po_code = get_next_po_code()

                    production_order = ProductionOrder(
                        code=po_code,
                        product_id=line.product_id,
                        bom_id=bom.id if bom else None,
                        routing_id=routing.id if routing else None,
                        sales_order_id=order.id,
                        sales_order_line_id=line.id,
                        quantity_ordered=line.quantity,
                        quantity_completed=0,
                        quantity_scrapped=0,
                        source="sales_order",
                        status="draft",
                        priority=3,
                        notes=f"Auto-generated from {order.order_number} Line {idx}",
                        created_by=created_by,
                    )
                    db.add(production_order)
                    db.flush()  # Flush to detect unique constraint violations
                    created_orders.append(po_code)
                    break  # Success, exit retry loop
                except IntegrityError as e:
                    db.rollback()
                    logger.warning(
                        f"PO code generation attempt {attempt + 1}/{max_retries} failed due to duplicate: {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        # Retry with a new code
                        continue
                    else:
                        # Final attempt failed, raise error
                        logger.error(
                            f"Failed to generate unique PO code after {max_retries} attempts for SO {order.order_number}",
                            exc_info=True
                        )
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to generate unique PO code after {max_retries} attempts: {str(e)}"
                        )

    elif order.order_type == "quote_based" and order.product_id: # pyright: ignore[reportGeneralTypeIssues]
        product = db.query(Product).filter(Product.id == order.product_id).first()
        if product and product.has_bom:
            bom = db.query(BOM).filter(
                BOM.product_id == order.product_id,
                BOM.active.is_(True)
            ).first()

            routing = db.query(Routing).filter(
                Routing.product_id == order.product_id,
                Routing.is_active.is_(True)
            ).first()

            # Retry logic to handle race condition if locking fails
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    po_code = get_next_po_code()

                    production_order = ProductionOrder(
                        code=po_code,
                        product_id=order.product_id,
                        bom_id=bom.id if bom else None,
                        routing_id=routing.id if routing else None,
                        sales_order_id=order.id,
                        quantity_ordered=order.quantity or 1,
                        quantity_completed=0,
                        quantity_scrapped=0,
                        source="sales_order",
                        status="draft",
                        priority=3,
                        notes=f"Auto-generated from {order.order_number}",
                        created_by=created_by,
                    )
                    db.add(production_order)
                    db.flush()  # Flush to detect unique constraint violations
                    created_orders.append(po_code)
                    break  # Success, exit retry loop
                except IntegrityError as e:
                    db.rollback()
                    logger.warning(
                        f"PO code generation attempt {attempt + 1}/{max_retries} failed due to duplicate: {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        # Retry with a new code
                        continue
                    else:
                        # Final attempt failed, raise error
                        logger.error(
                            f"Failed to generate unique PO code after {max_retries} attempts for SO {order.order_number}",
                            exc_info=True
                        )
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to generate unique PO code after {max_retries} attempts: {str(e)}"
                        )

    return created_orders


# ============================================================================
# Status Transitions Metadata
# ============================================================================


@router.get("/status-transitions")
async def get_sales_order_status_transitions(
    current_status: Optional[str] = Query(None, description="Get transitions for a specific status"),
    current_user: User = Depends(get_current_user),
):
    """
    Get valid status transitions for sales orders.

    Returns:
    - All valid statuses and their allowed transitions
    - If current_status is provided, returns only transitions for that status

    Used by frontend to show only valid status options in dropdowns.
    """
    all_statuses = [s.value for s in SalesOrderStatus]

    if current_status:
        if current_status not in all_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{current_status}'. Must be one of: {', '.join(all_statuses)}"
            )
        allowed = get_allowed_sales_order_transitions(current_status)
        return {
            "current_status": current_status,
            "allowed_transitions": allowed,
            "is_terminal": len(allowed) == 0,
        }

    # Return all statuses with their transitions
    transitions = {}
    for order_status in SalesOrderStatus:
        allowed = get_allowed_sales_order_transitions(order_status.value)
        transitions[order_status.value] = {
            "allowed_transitions": allowed,
            "is_terminal": len(allowed) == 0,
        }

    return {
        "statuses": all_statuses,
        "transitions": transitions,
        "terminal_statuses": [s.value for s in SalesOrderStatus if len(get_allowed_sales_order_transitions(s.value)) == 0],
    }


@router.get("/payment-statuses")
async def get_payment_statuses(
    current_user: User = Depends(get_current_user),
):
    """
    Get valid payment status values for sales orders.

    Used by frontend to populate payment status dropdowns.
    """
    return {
        "statuses": [s.value for s in PaymentStatus],
        "descriptions": {
            PaymentStatus.PENDING.value: "Payment not yet received",
            PaymentStatus.PARTIAL.value: "Partial payment received",
            PaymentStatus.PAID.value: "Full payment received",
            PaymentStatus.REFUNDED.value: "Payment refunded",
            PaymentStatus.OVERDUE.value: "Payment is overdue",
        },
    }


# ============================================================================
# ENDPOINT: Create Manual Sales Order
# ============================================================================

@router.post("/", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    request: SalesOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a manual sales order (line_item type)

    This endpoint creates a line-item based sales order for standard products.
    Use this for orders from manual entry, Squarespace, WooCommerce, etc.

    For custom quote-based orders, use POST /convert/{quote_id} instead.

    Validations:
    - Customer must exist and be active (if provided)
    - All products must exist and be active
    - Prices are taken from product catalog (frontend price ignored for security)
    - Shipping address auto-copied from customer if not provided

    Returns:
        Sales order with status 'pending'
    """
    # ========================================================================
    # VALIDATION: Customer (if provided)
    # ========================================================================
    customer = None
    if request.customer_id:
        customer = db.query(User).filter(User.id == request.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer ID {request.customer_id} not found"
            )
        if customer.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer '{customer.email}' is not active (status: {customer.status})"
            )

    # ========================================================================
    # VALIDATION: Products - must exist, be active, have price
    # ========================================================================
    line_products = []
    total_price = Decimal("0")
    total_quantity = 0

    for line in request.lines:
        product = db.query(Product).filter(Product.id == line.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product ID {line.product_id} not found"
            )

        # Check product is active
        if not product.active: # pyright: ignore[reportGeneralTypeIssues]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product.sku}' is discontinued and cannot be ordered"
            )

        # SECURITY: Always use product's catalog price, never trust frontend
        unit_price = product.selling_price or Decimal("0")
        if unit_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product.sku}' has no selling price configured"
            )

        line_total = unit_price * line.quantity

        line_products.append({
            "product": product,
            "quantity": line.quantity,
            "unit_price": unit_price,
            "line_total": line_total,
            "notes": line.notes,
        })

        total_price += line_total
        total_quantity += line.quantity

    # ========================================================================
    # GENERATE: Order number with row locking to prevent duplicates
    # ========================================================================
    year = datetime.utcnow().year
    # Use with_for_update() for row-level locking to prevent race conditions
    last_order = (
        db.query(SalesOrder)
        .filter(SalesOrder.order_number.like(f"SO-{year}-%"))
        .order_by(desc(SalesOrder.order_number))
        .with_for_update()
        .first()
    )

    if last_order:
        last_num = int(last_order.order_number.split("-")[2])
        next_num = last_num + 1
    else:
        next_num = 1

    order_number = f"SO-{year}-{next_num:03d}"

    # ========================================================================
    # CALCULATE TAX: Get tax settings from company_settings
    # ========================================================================
    shipping_cost = request.shipping_cost or Decimal("0")
    tax_amount = Decimal("0")
    tax_rate = None
    is_taxable = True  # Default to taxable

    # Fetch company tax settings
    company_settings = db.query(CompanySettings).filter(CompanySettings.id == 1).first()
    if company_settings and company_settings.tax_enabled and company_settings.tax_rate:
        tax_rate = Decimal(str(company_settings.tax_rate))
        # Calculate tax on the product total (not shipping typically)
        tax_amount = (total_price * tax_rate).quantize(Decimal("0.01"))
    else:
        is_taxable = False

    grand_total = total_price + shipping_cost + tax_amount

    # Build product name summary from lines
    if len(line_products) == 1:
        product_name = f"{line_products[0]['product'].name} x{line_products[0]['quantity']}"
    else:
        product_name = f"{len(line_products)} items"

    # Get first product for material_type fallback
    first_product = line_products[0]["product"]

    # Determine user_id: use customer_id if provided, otherwise current admin
    user_id = request.customer_id if request.customer_id else current_user.id

    # ========================================================================
    # AUTO-COPY: Customer shipping address if not provided
    # ========================================================================
    shipping_address_line1 = request.shipping_address_line1
    shipping_address_line2 = request.shipping_address_line2
    shipping_city = request.shipping_city
    shipping_state = request.shipping_state
    shipping_zip = request.shipping_zip
    shipping_country = request.shipping_country or "USA"

    if customer and not shipping_address_line1:
        # Copy customer's shipping address if available
        if customer.shipping_address_line1 is not None and customer.shipping_address_line1 != "":
            shipping_address_line1 = customer.shipping_address_line1
            shipping_address_line2 = customer.shipping_address_line2
            shipping_city = customer.shipping_city
            shipping_state = customer.shipping_state
            shipping_zip = customer.shipping_zip
            shipping_country = customer.shipping_country or "USA"

    # Create sales order
    sales_order = SalesOrder(
        user_id=user_id,
        order_number=order_number,
        order_type="line_item",
        source=request.source or "manual",
        source_order_id=request.source_order_id,
        product_name=product_name,
        quantity=total_quantity,
        material_type=first_product.item_category.name if first_product.item_category else "PLA",  # Use category name as fallback
        finish="standard",
        unit_price=total_price / total_quantity if total_quantity > 0 else Decimal("0"),
        total_price=total_price,
        tax_amount=tax_amount,
        tax_rate=tax_rate,
        is_taxable=is_taxable,
        shipping_cost=shipping_cost,
        grand_total=grand_total,
        status="pending",
        payment_status="pending",
        rush_level="standard",
        shipping_address_line1=shipping_address_line1,
        shipping_address_line2=shipping_address_line2,
        shipping_city=shipping_city,
        shipping_state=shipping_state,
        shipping_zip=shipping_zip,
        shipping_country=shipping_country,
        customer_notes=request.customer_notes,
        internal_notes=request.internal_notes,
    )

    db.add(sales_order)
    db.flush()  # Get sales_order.id

    # Create order lines (using actual database schema)
    for idx, line_data in enumerate(line_products, start=1):
        order_line = SalesOrderLine(
            sales_order_id=sales_order.id,
            product_id=line_data["product"].id,
            quantity=line_data["quantity"],
            unit_price=line_data["unit_price"],
            total=line_data["line_total"],  # Use 'total' not 'total_price'
            discount=Decimal("0"),
            tax_rate=Decimal("0"),
            notes=line_data["notes"],
            created_by=current_user.id,
        )
        db.add(order_line)

    # Record order creation event
    record_order_event(
        db=db,
        order_id=sales_order.id,
        event_type="created",
        title="Order created",
        description=f"Sales order {order_number} created from {request.source or 'manual'} source",
        user_id=current_user.id,
    )

    db.commit()
    db.refresh(sales_order)

    # Trigger MRP check if enabled (behind feature flag, graceful degradation)
    try:
        from app.services.mrp_trigger_service import trigger_mrp_check
        from app.core.settings import get_settings
        settings = get_settings()

        if settings.AUTO_MRP_ON_ORDER_CREATE:
            trigger_mrp_check(db, sales_order.id)
    except Exception as e:
        # Log but don't break order creation - graceful degradation
        logger.warning(
            f"MRP trigger failed for sales order {sales_order.id}: {str(e)}",
            exc_info=True
        )

    return sales_order


# ============================================================================
# ENDPOINT: Convert Quote to Sales Order
# ============================================================================

@router.post("/convert/{quote_id}", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def convert_quote_to_sales_order(
    quote_id: int,
    convert_request: SalesOrderConvert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Convert an accepted quote to a sales order

    This endpoint creates a quote-based sales order from an accepted quote.
    The quote must have already been accepted (which auto-creates product + BOM).

    Requirements:
    - Quote must exist and belong to current user
    - Quote must be in 'accepted' status
    - Quote must have associated product (created during acceptance)
    - Quote must not be expired
    - Quote must not already be converted

    The sales order will be created with:
    - order_type = 'quote_based'
    - source = 'portal'
    - source_order_id = quote number

    Returns:
        Sales order with status 'pending'
    """
    # Get quote
    quote = db.query(Quote).filter(Quote.id == quote_id).first()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )

    # Verify ownership
    if quote.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to convert this quote"
        )

    # Check if quote is accepted
    if quote.status != "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot convert quote with status '{quote.status}'. Must be 'accepted'."
        )

    # Check if quote is expired
    if quote.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote has expired. Please request a new quote."
        )

    # Check if quote is already converted
    if quote.sales_order_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote already converted to sales order"
        )

    # Verify quote has product_id (created during acceptance)
    if not quote.product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote does not have an associated product. This should have been created during acceptance."
        )

    # Generate sales order number with row locking to prevent duplicates
    year = datetime.utcnow().year
    last_order = (
        db.query(SalesOrder)
        .filter(SalesOrder.order_number.like(f"SO-{year}-%"))
        .order_by(desc(SalesOrder.order_number))
        .with_for_update()
        .first()
    )

    if last_order:
        last_num = int(last_order.order_number.split("-")[2])
        next_num = last_num + 1
    else:
        next_num = 1

    order_number = f"SO-{year}-{next_num:03d}"

    # Calculate grand total (no tax/shipping for now, but structure is ready)
    grand_total = quote.total_price

    # Create sales order
    sales_order = SalesOrder(
        user_id=current_user.id,
        quote_id=quote.id,
        order_number=order_number,
        product_name=quote.product_name,
        quantity=quote.quantity,
        material_type=quote.material_type,
        finish=quote.finish,
        unit_price=quote.unit_price,
        total_price=quote.total_price,
        tax_amount=Decimal('0.00'),
        shipping_cost=Decimal('0.00'),
        grand_total=grand_total,
        status="pending",
        payment_status="pending",
        rush_level=quote.rush_level,
        shipping_address_line1=convert_request.shipping_address_line1,
        shipping_address_line2=convert_request.shipping_address_line2,
        shipping_city=convert_request.shipping_city,
        shipping_state=convert_request.shipping_state,
        shipping_zip=convert_request.shipping_zip,
        shipping_country=convert_request.shipping_country or "USA",
        customer_notes=convert_request.customer_notes or quote.customer_notes,
        # Hybrid architecture fields
        order_type="quote_based",
        source="portal",
        source_order_id=quote.quote_number,
    )

    db.add(sales_order)
    db.flush()  # Get sales_order.id

    # Update quote to mark as converted
    quote.sales_order_id = sales_order.id
    quote.converted_at = datetime.utcnow()

    # =========================================================================
    # Create Production Order
    # =========================================================================
    # Find the BOM for this product
    bom = db.query(BOM).filter(
        BOM.product_id == quote.product_id,
        BOM.active.is_(True)
    ).first()

    # Generate production order code
    last_po = (
        db.query(ProductionOrder)
        .filter(ProductionOrder.code.like(f"PO-{year}-%"))
        .order_by(desc(ProductionOrder.code))
        .first()
    )

    if last_po:
        last_po_num = int(last_po.code.split("-")[2])
        next_po_num = last_po_num + 1
    else:
        next_po_num = 1

    po_code = f"PO-{year}-{next_po_num:03d}"

    # Calculate estimated print time from quote
    estimated_time_minutes = int(quote.print_time_hours * 60) if quote.print_time_hours else None

    # Create production order
    production_order = ProductionOrder(
        code=po_code,
        product_id=quote.product_id,
        bom_id=bom.id if bom else None,
        sales_order_id=sales_order.id,  # Link to sales order for transaction tracking
        quantity=quote.quantity,
        status="scheduled",  # Ready for production
        priority="normal" if quote.rush_level == "standard" else "high",
        estimated_time_minutes=estimated_time_minutes,
        notes=f"Auto-created from Sales Order {order_number}. Quote: {quote.quote_number}",
        created_by=current_user.email,
    )

    db.add(production_order)

    # Log the creation
    logger.info(
        "Production order created from quote",
        extra={
            "production_order_code": po_code,
            "sales_order_number": order_number,
            "product_id": quote.product_id,
            "quote_id": quote.id
        }
    )

    # Record order creation event
    record_order_event(
        db=db,
        order_id=sales_order.id,
        event_type="created",
        title="Order created from quote",
        description=f"Sales order {order_number} created from quote {quote.quote_number}",
        user_id=current_user.id,
    )

    db.commit()
    db.refresh(sales_order)

    return sales_order


# ============================================================================
# ENDPOINT: Get User's Sales Orders
# ============================================================================

# Valid fulfillment states for filtering
VALID_FULFILLMENT_STATES = {"ready_to_ship", "partially_ready", "blocked", "shipped", "cancelled"}

# Priority order for fulfillment_priority sorting (lower = more actionable)
FULFILLMENT_PRIORITY = {
    "ready_to_ship": 1,
    "partially_ready": 2,
    "blocked": 3,
    "shipped": 4,
    "cancelled": 5,
}


@router.get("/", response_model=List[SalesOrderListResponse])
async def get_user_sales_orders(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    status: Optional[List[str]] = Query(None),
    include_fulfillment: bool = Query(False, description="Include fulfillment status summary"),
    fulfillment_state: Optional[str] = Query(
        None,
        description="Filter by fulfillment state(s), comma-separated (ready_to_ship,partially_ready,blocked,shipped,cancelled)"
    ),
    sort_by: str = Query(
        "order_date",
        description="Sort field: order_date, fulfillment_priority, fulfillment_percent, customer_name"
    ),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get list of sales orders

    Query parameters:
    - skip: Pagination offset (default: 0)
    - limit: Max results (default: 50, max: 100)
    - status_filter: Filter by single status (deprecated, use status instead)
    - status: Filter by status(es) - can be repeated for multiple values
    - include_fulfillment: Include fulfillment status summary for each order (default: false)
    - fulfillment_state: Filter by fulfillment state(s), comma-separated
    - sort_by: Sort field (order_date, fulfillment_priority, fulfillment_percent, customer_name)
    - sort_order: Sort order (asc or desc)

    Returns:
        List of sales orders ordered by creation date (newest first)
        - Admin users see ALL orders
        - Regular users see only their own orders
    """
    if limit > 100:
        limit = 100

    # Validate sort_order
    if sort_order not in ("asc", "desc"):
        raise HTTPException(
            status_code=400,
            detail="sort_order must be 'asc' or 'desc'"
        )

    # Validate sort_by
    valid_sort_fields = {"order_date", "fulfillment_priority", "fulfillment_percent", "customer_name"}
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=400,
            detail=f"sort_by must be one of: {', '.join(valid_sort_fields)}"
        )

    # Parse and validate fulfillment_state filter
    requested_states = None
    if fulfillment_state:
        requested_states = set(s.strip().lower() for s in fulfillment_state.split(","))
        invalid_states = requested_states - VALID_FULFILLMENT_STATES
        if invalid_states:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid fulfillment_state value(s): {', '.join(invalid_states)}. Valid: {', '.join(VALID_FULFILLMENT_STATES)}"
            )

    # OPTIMIZED: Use joinedload to eager load user relationship for better performance
    query = db.query(SalesOrder).options(
        joinedload(SalesOrder.user),
        joinedload(SalesOrder.product)
    )

    # Admin users can see all orders, regular users only see their own
    if current_user.account_type != "admin":
        query = query.filter(SalesOrder.user_id == current_user.id)

    # Support multiple status values (new) or single status_filter (legacy)
    if status:
        query = query.filter(SalesOrder.status.in_(status))
    elif status_filter:
        query = query.filter(SalesOrder.status == status_filter)

    # Determine if we need fulfillment data for filtering or sorting
    needs_fulfillment = (
        include_fulfillment or
        fulfillment_state is not None or
        sort_by in ("fulfillment_priority", "fulfillment_percent")
    )

    if needs_fulfillment:
        # Fetch all orders (we'll paginate after filtering/sorting)
        all_orders = query.all()

        # Compute fulfillment for each order
        orders_with_fulfillment = []
        for order in all_orders:
            order_dict = SalesOrderListResponse.model_validate(order).model_dump()
            fulfillment_data = get_fulfillment_status(db, order.id)
            if fulfillment_data:
                order_dict["fulfillment"] = fulfillment_data.summary
            orders_with_fulfillment.append(order_dict)

        # Filter by fulfillment_state if requested
        if requested_states:
            orders_with_fulfillment = [
                o for o in orders_with_fulfillment
                if o.get("fulfillment") and o["fulfillment"].state.value in requested_states
            ]

        # Sort
        reverse = sort_order == "desc"
        if sort_by == "order_date":
            orders_with_fulfillment.sort(key=lambda o: o.get("created_at") or "", reverse=reverse)
        elif sort_by == "fulfillment_priority":
            orders_with_fulfillment.sort(
                key=lambda o: FULFILLMENT_PRIORITY.get(
                    o["fulfillment"].state.value if o.get("fulfillment") else "cancelled", 5
                ),
                reverse=reverse
            )
        elif sort_by == "fulfillment_percent":
            orders_with_fulfillment.sort(
                key=lambda o: o["fulfillment"].fulfillment_percent if o.get("fulfillment") else 0,
                reverse=reverse
            )
        elif sort_by == "customer_name":
            orders_with_fulfillment.sort(
                key=lambda o: (o.get("customer_name") or "").lower(),
                reverse=reverse
            )

        # Paginate
        paginated = orders_with_fulfillment[skip:skip + limit]

        # Convert back to response models
        return [SalesOrderListResponse(**o) for o in paginated]

    # No fulfillment needed - use database sorting and pagination
    if sort_by == "order_date":
        order_column = SalesOrder.created_at
    elif sort_by == "customer_name":
        order_column = SalesOrder.customer_name
    else:
        order_column = SalesOrder.created_at

    if sort_order == "desc":
        query = query.order_by(desc(order_column))
    else:
        query = query.order_by(order_column)

    orders = query.offset(skip).limit(limit).all()

    return orders


# ============================================================================
# ENDPOINT: Get Sales Order Details
# ============================================================================

@router.get("/{order_id}", response_model=SalesOrderResponse)
async def get_sales_order_details(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific sales order

    Returns:
        Complete sales order data including shipping and payment info
    """
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )

    # Verify user owns this order OR is an admin
    # Use same check as list endpoint
    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if order.user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this order"
        )

    # Use helper function to build response with proper line handling
    return build_sales_order_response(order, db)


# ============================================================================
# ENDPOINT: Get Required Orders (MRP Cascade)
# ============================================================================

@router.get("/{order_id}/required-orders")
async def get_required_orders_for_sales_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get full MRP cascade of WOs and POs needed to fulfill this sales order.

    Recursively explodes BOMs for all line items to show:
    - Work Orders needed for sub-assemblies (make items with BOMs)
    - Purchase Orders needed for raw materials (buy items without BOMs)

    This provides a complete view of manufacturing requirements before
    creating production orders.

    Returns:
        - work_orders_needed: List of sub-assemblies requiring production
        - purchase_orders_needed: List of materials requiring purchase
        - summary by product with quantities
    """
    # Admin-only endpoint
    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view MRP requirements"
        )

    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )

    work_orders_needed = []
    purchase_orders_needed = []
    top_level_products = []

    def explode_requirements(product_id: int, quantity: Decimal, level: int = 0, parent_sku: Optional[str] = None, visited_bom_ids: Optional[set] = None) -> None:
        """
        Recursively explode BOM to find all requirements
        
        Args:
            product_id: Product to explode BOM for
            quantity: Quantity required
            level: Current BOM depth level
            parent_sku: SKU of parent product
            visited_bom_ids: Set of BOM IDs visited in current recursion path (prevents circular refs)
        """
        # Initialize visited set for top-level calls
        if visited_bom_ids is None:
            visited_bom_ids = set()

        # Find active BOM for this product
        bom = db.query(BOM).filter(
            BOM.product_id == product_id,
            BOM.active.is_(True)
        ).first()

        if not bom:
            return

        # Prevent circular references: check if this BOM is already in the current recursion path
        if bom.id in visited_bom_ids:
            return  # Circular reference detected, stop recursion

        # Add current BOM to the path for downstream recursion
        current_path = visited_bom_ids | {bom.id}

        bom_lines = db.query(BOMLine).filter(BOMLine.bom_id == bom.id).all()

        for line in bom_lines:
            if line.is_cost_only:
                continue

            component = db.query(Product).filter(Product.id == line.component_id).first()
            if not component:
                continue

            # Calculate required quantity with scrap
            base_qty = Decimal(str(line.quantity or 0))
            scrap_factor = Decimal(str(line.scrap_factor or 0)) / Decimal("100")
            required_qty = base_qty * (Decimal("1") + scrap_factor) * quantity

            # Get available inventory
            inv_result = db.query(
                func.sum(Inventory.available_quantity)
            ).filter(Inventory.product_id == line.component_id).scalar()
            available_qty = Decimal(str(inv_result or 0))

            shortage_qty = max(Decimal("0"), required_qty - available_qty)

            if shortage_qty <= 0:
                continue  # No shortage, no order needed

            order_info = {
                "product_id": component.id,
                "product_sku": component.sku,
                "product_name": component.name,
                "unit": line.unit or component.unit,
                "required_qty": float(required_qty),
                "available_qty": float(available_qty),
                "order_qty": float(shortage_qty),
                "bom_level": level,
                "has_bom": component.has_bom or False,
                "parent_sku": parent_sku
            }

            if component.has_bom:
                work_orders_needed.append(order_info)
                # Recursively explode this sub-assembly's BOM with current path
                explode_requirements(component.id, shortage_qty, level + 1, component.sku, current_path)
            else:
                purchase_orders_needed.append(order_info)

    # Process based on order type
    if order.order_type == "line_item":
        # OPTIMIZED: Get all lines with eager-loaded products in one query
        lines = db.query(SalesOrderLine).options(
            joinedload(SalesOrderLine.product)
        ).filter(
            SalesOrderLine.sales_order_id == order_id
        ).all()

        for line in lines:
            # OPTIMIZED: Use eager-loaded product (no additional query)
            product = line.product
            if not product:
                continue

            qty = Decimal(str(line.quantity or 1))

            # Check if this product needs a top-level WO
            if product.has_bom:
                # Get available inventory for the finished good
                inv_result = db.query(
                    func.sum(Inventory.available_quantity)
                ).filter(Inventory.product_id == product.id).scalar()
                available_qty = Decimal(str(inv_result or 0))
                shortage_qty = max(Decimal("0"), qty - available_qty)

                if shortage_qty > 0:
                    top_level_products.append({
                        "product_id": product.id,
                        "product_sku": product.sku,
                        "product_name": product.name,
                        "order_qty": float(shortage_qty),
                        "has_bom": True
                    })

            # Each line item starts a fresh BOM explosion (no visited set carried over)
            explode_requirements(product.id, qty, level=0, parent_sku=product.sku)

    elif order.order_type == "quote_based" and order.product_id:
        # Single product from quote
        product = db.query(Product).filter(Product.id == order.product_id).first()
        if product:
            qty = Decimal(str(order.quantity or 1))

            if product.has_bom:
                inv_result = db.query(
                    func.sum(Inventory.available_quantity)
                ).filter(Inventory.product_id == product.id).scalar()
                available_qty = Decimal(str(inv_result or 0))
                shortage_qty = max(Decimal("0"), qty - available_qty)

                if shortage_qty > 0:
                    top_level_products.append({
                        "product_id": product.id,
                        "product_sku": product.sku,
                        "product_name": product.name,
                        "order_qty": float(shortage_qty),
                        "has_bom": True
                    })

            explode_requirements(product.id, qty, level=0, parent_sku=product.sku)

    # Aggregate duplicate materials (same product from different sub-assemblies)
    aggregated_pos = {}
    for po in purchase_orders_needed:
        key = po["product_id"]
        if key in aggregated_pos:
            aggregated_pos[key]["order_qty"] += po["order_qty"]
            aggregated_pos[key]["required_qty"] += po["required_qty"]
        else:
            aggregated_pos[key] = po.copy()
            aggregated_pos[key]["sources"] = []
        aggregated_pos[key]["sources"].append(po.get("parent_sku", "direct"))

    return {
        "order_id": order_id,
        "order_number": order.order_number,
        "order_type": order.order_type,
        "top_level_work_orders": top_level_products,
        "sub_assembly_work_orders": work_orders_needed,
        "purchase_orders_needed": list(aggregated_pos.values()),
        "summary": {
            "top_level_wos": len(top_level_products),
            "sub_assembly_wos": len(work_orders_needed),
            "purchase_orders": len(aggregated_pos),
            "total_orders_needed": len(top_level_products) + len(work_orders_needed) + len(aggregated_pos)
        }
    }


# ============================================================================
# ENDPOINT: Get Blocking Issues Analysis (API-201)
# ============================================================================


@router.get("/{order_id}/blocking-issues", response_model=SalesOrderBlockingIssues)
async def get_blocking_issues(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get blocking issues analysis for a sales order.

    Analyzes what's preventing fulfillment and returns:
    - Status summary (can_fulfill, blocking_count, estimated_ready_date)
    - Per-line breakdown of blocking issues
    - Prioritized resolution actions

    Issue types:
    - production_incomplete: Work order exists but not finished
    - production_missing: No work order created for make item
    - material_shortage: Insufficient material for production
    - purchase_pending: PO exists but not yet received

    Resolution actions are prioritized:
    1. Expedite pending purchase orders
    2. Create purchase orders for shortages without POs
    3. Complete incomplete production orders
    4. Create missing production orders
    """
    result = get_sales_order_blocking_issues(db, order_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales order {order_id} not found"
        )

    return result


# ============================================================================
# ENDPOINT: Get Fulfillment Status (API-301)
# ============================================================================

@router.get("/{order_id}/fulfillment-status", response_model=FulfillmentStatus)
async def get_order_fulfillment_status(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get fulfillment status for a sales order.

    Returns line-by-line status and overall fulfillment progress.

    Response includes:
    - Order summary with fulfillment state (ready_to_ship, partially_ready, blocked, shipped, cancelled)
    - Per-line breakdown with quantities ordered, allocated, shipped, and shortage amounts
    - Estimated completion date based on incoming purchase orders
    """
    result = get_fulfillment_status(db, order_id)
    if not result:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return result


# ============================================================================
# ENDPOINT: Update Order Status (Admin)
# ============================================================================

@router.patch("/{order_id}/status", response_model=SalesOrderResponse)
async def update_order_status(
    order_id: int,
    update: SalesOrderUpdateStatus,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update sales order status (admin only)

    Allowed status transitions:
    - pending → confirmed
    - confirmed → in_production
    - in_production → quality_check
    - quality_check → shipped
    - shipped → delivered
    - delivered → completed
    - Any → on_hold, cancelled

    Returns:
        Updated sales order
    """
    # Admin-only endpoint
    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update order status"
        )

    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )

    # Update status
    old_status = order.status
    order.status = update.status

    # Set timestamps based on status
    if update.status == "confirmed" and old_status == "pending":
        order.confirmed_at = datetime.utcnow()

        # Auto-create production orders for confirmed orders
        # Check if production orders already exist
        existing_pos = db.query(ProductionOrder).filter(
            ProductionOrder.sales_order_id == order_id
        ).all()

        if not existing_pos:
            # Generate production orders for this SO
            created_orders = _create_production_orders_for_so(order, db, current_user.email)
            if created_orders:
                # Update status to in_production since WOs are created
                order.status = "in_production"
                
                # Trigger MRP check if enabled (behind feature flag, graceful degradation)
                try:
                    from app.services.mrp_trigger_service import trigger_mrp_check
                    from app.core.settings import get_settings
                    settings = get_settings()
                    
                    if settings.AUTO_MRP_ON_CONFIRMATION:
                        trigger_mrp_check(db, order.id)
                except Exception as e:
                    # Log but don't break order confirmation - graceful degradation
                    logger.warning(
                        f"MRP trigger failed after order confirmation {order.id}: {str(e)}",
                        exc_info=True
                    )

    if update.status == "shipped":
        order.shipped_at = datetime.utcnow()

    if update.status == "delivered":
        order.delivered_at = datetime.utcnow()

    if update.status == "completed":
        order.actual_completion_date = datetime.utcnow()

    # Update notes
    if update.internal_notes:
        order.internal_notes = update.internal_notes

    if update.production_notes:
        order.production_notes = update.production_notes

    # Record status change event
    if old_status != order.status:
        record_order_event(
            db=db,
            order_id=order_id,
            event_type="status_change",
            title=f"Status changed to {order.status.replace('_', ' ').title()}",
            old_value=old_status,
            new_value=order.status,
            user_id=current_user.id,
        )

    db.commit()
    db.refresh(order)

    return order


# ============================================================================
# ENDPOINT: Update Payment Information
# ============================================================================

@router.patch("/{order_id}/payment", response_model=SalesOrderResponse)
async def update_payment_info(
    order_id: int,
    update: SalesOrderUpdatePayment,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update payment information for an order (admin only)

    Returns:
        Updated sales order
    """
    # Admin-only endpoint
    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update payment information"
        )

    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )

    # Track old status for event recording
    old_payment_status = order.payment_status

    # Update payment info
    order.payment_status = update.payment_status

    if update.payment_method:
        order.payment_method = update.payment_method

    if update.payment_transaction_id:
        order.payment_transaction_id = update.payment_transaction_id

    if update.payment_status == "paid":
        order.paid_at = datetime.utcnow()

    # Record payment event
    if old_payment_status != update.payment_status:
        event_type = "payment_received" if update.payment_status == "paid" else "payment_refunded" if update.payment_status == "refunded" else "status_change"
        title = "Payment received" if update.payment_status == "paid" else "Payment refunded" if update.payment_status == "refunded" else f"Payment status changed to {update.payment_status}"

        record_order_event(
            db=db,
            order_id=order_id,
            event_type=event_type,
            title=title,
            old_value=old_payment_status,
            new_value=update.payment_status,
            user_id=current_user.id,
            metadata_key="payment_method" if update.payment_method else None,
            metadata_value=update.payment_method,
        )

    db.commit()
    db.refresh(order)

    return order


# ============================================================================
# ENDPOINT: Update Shipping Information
# ============================================================================

@router.patch("/{order_id}/shipping", response_model=SalesOrderResponse)
async def update_shipping_info(
    order_id: int,
    update: SalesOrderUpdateShipping,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update shipping information for an order (admin only)

    Returns:
        Updated sales order
    """
    # Admin-only endpoint
    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update shipping information"
        )

    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )

    # Track if we're marking as shipped (transition from not-shipped to shipped)
    is_shipping = order.shipped_at is None and update.shipped_at is not None

    # Update shipping info
    if update.tracking_number:
        order.tracking_number = update.tracking_number

    if update.carrier:
        order.carrier = update.carrier

    if update.shipped_at:
        order.shipped_at = update.shipped_at
        order.status = "shipped"

    # Record shipping event
    if is_shipping:
        record_order_event(
            db=db,
            order_id=order_id,
            event_type="shipped",
            title="Order shipped",
            description=f"Shipped via {update.carrier or 'carrier'}" + (f", tracking: {update.tracking_number}" if update.tracking_number else ""),
            user_id=current_user.id,
            metadata_key="tracking_number" if update.tracking_number else None,
            metadata_value=update.tracking_number,
        )

    db.commit()
    db.refresh(order)

    return order


# ============================================================================
# ENDPOINT: Update Shipping Address
# ============================================================================

@router.patch("/{order_id}/address", response_model=SalesOrderResponse)
async def update_shipping_address(
    order_id: int,
    update: SalesOrderUpdateAddress,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update shipping address for an order (admin only)
    """
    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update shipping address"
        )

    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found")

    # Track if any changes were made
    address_changed = False

    if update.shipping_address_line1 is not None:
        order.shipping_address_line1 = update.shipping_address_line1
        address_changed = True
    if update.shipping_address_line2 is not None:
        order.shipping_address_line2 = update.shipping_address_line2
        address_changed = True
    if update.shipping_city is not None:
        order.shipping_city = update.shipping_city
        address_changed = True
    if update.shipping_state is not None:
        order.shipping_state = update.shipping_state
        address_changed = True
    if update.shipping_zip is not None:
        order.shipping_zip = update.shipping_zip
        address_changed = True
    if update.shipping_country is not None:
        order.shipping_country = update.shipping_country
        address_changed = True

    order.updated_at = datetime.utcnow()

    # Record address change event
    if address_changed:
        record_order_event(
            db=db,
            order_id=order_id,
            event_type="address_updated",
            title="Shipping address updated",
            user_id=current_user.id,
        )

    db.commit()
    db.refresh(order)
    return order


# ============================================================================
# ENDPOINT: Cancel Sales Order
# ============================================================================

@router.post("/{order_id}/cancel", response_model=SalesOrderResponse)
async def cancel_sales_order(
    order_id: int,
    cancel_request: SalesOrderCancel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel a sales order

    Requirements:
    - Order must be cancellable (pending, confirmed, or on_hold)
    - User must own the order OR be an admin

    Returns:
        Cancelled sales order
    """
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )

    # Verify ownership or admin
    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if order.user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this order"
        )

    # Check if order can be cancelled
    if not order.is_cancellable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status '{order.status}'"
        )

    # Check for linked production orders that aren't cancelled
    linked_wos = db.query(ProductionOrder).filter(
        ProductionOrder.sales_order_id == order_id,
        ProductionOrder.status != "cancelled"
    ).all()

    if linked_wos:
        wo_codes = [wo.code for wo in linked_wos]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel: {len(linked_wos)} work order(s) still active ({', '.join(wo_codes[:3])}{'...' if len(wo_codes) > 3 else ''}). Cancel work orders first."
        )

    # Cancel order
    old_status = order.status
    order.status = "cancelled"
    order.cancelled_at = datetime.utcnow()
    order.cancellation_reason = cancel_request.cancellation_reason

    # Record cancellation event
    record_order_event(
        db=db,
        order_id=order_id,
        event_type="cancelled",
        title="Order cancelled",
        description=cancel_request.cancellation_reason,
        old_value=old_status,
        new_value="cancelled",
        user_id=current_user.id,
    )

    db.commit()
    db.refresh(order)

    return order


# ============================================================================
# ENDPOINT: Delete Sales Order (Admin Only)
# ============================================================================

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sales_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a sales order (admin only)

    Requirements:
    - Only admins can delete orders
    - Order must be cancelled or pending (not in production/shipped)
    - Associated production orders will be checked

    Returns:
        204 No Content on success
    """
    # Admin-only endpoint
    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete sales orders"
        )

    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )

    # Check if order can be deleted (only cancelled or pending orders)
    deletable_statuses = ["cancelled", "pending"]
    if order.status not in deletable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete order with status '{order.status}'. Only cancelled or pending orders can be deleted."
        )

    # Check for associated production orders
    existing_pos = db.query(ProductionOrder).filter(
        ProductionOrder.sales_order_id == order_id
    ).all()

    if existing_pos:
        # Only block deletion if POs are not cancelled/draft
        active_pos = [po for po in existing_pos if po.status not in ["cancelled", "draft"]]
        if active_pos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete order with active production orders. Cancel or delete the production orders first: {', '.join([po.code for po in active_pos])}"
            )

    # Delete the order (cascade will handle lines and payments)
    db.delete(order)
    db.commit()

    return None


# ============================================================================
# ENDPOINT: Create Shipping Label / Ship Order
# ============================================================================

class ShipOrderRequest(BaseModel):
    """Request to ship an order"""
    carrier: str = "USPS"
    service: Optional[str] = "Priority"
    tracking_number: Optional[str] = None  # If already have tracking


@router.post("/{order_id}/ship")
async def ship_order(
    order_id: int,
    request: ShipOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create shipping label and mark order as shipped.

    For now, this generates a mock tracking number.
    In production, integrate with carrier APIs (EasyPost, ShipStation, etc.)

    Returns:
        tracking_number, label_url, carrier info
    """
    # Admin-only endpoint
    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can ship orders"
        )

    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found")

    # Validate shipping address exists
    if not order.shipping_address_line1 and not order.shipping_city:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has no shipping address. Please add one first."
        )

    # Generate mock tracking number if not provided
    # Format: {CARRIER}-{YEAR}{MONTH}{DAY}-{ORDER_ID}{RANDOM}
    import random
    import string
    if request.tracking_number:
        tracking_number = request.tracking_number
    else:
        date_part = datetime.utcnow().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        carrier_prefix = request.carrier[:3].upper() if request.carrier else "SHP"
        tracking_number = f"{carrier_prefix}{date_part}{order_id:04d}{random_part}"

    # Update order
    order.tracking_number = tracking_number
    order.carrier = request.carrier
    order.shipped_at = datetime.utcnow()
    order.status = "shipped"
    order.updated_at = datetime.utcnow()

    # Process inventory transactions:
    # 1. Consume packaging materials (shipping stage BOM items)
    # 2. Issue finished goods from inventory
    process_shipment(
        db=db,
        sales_order=order,
        created_by=current_user.email if current_user else None,
    )

    # Record order event (for general activity timeline)
    record_order_event(
        db=db,
        order_id=order_id,
        event_type="shipped",
        title="Order shipped",
        description=f"Shipped via {request.carrier}" + (f" ({request.service})" if request.service else ""),
        user_id=current_user.id,
        metadata_key="tracking_number",
        metadata_value=tracking_number,
    )

    # Record shipping event (for dedicated shipping timeline)
    record_shipping_event(
        db=db,
        sales_order_id=order_id,
        event_type="label_purchased",
        title="Shipping Label Created",
        description=f"Carrier: {request.carrier}" + (f", Service: {request.service}" if request.service else ""),
        tracking_number=tracking_number,
        carrier=request.carrier,
        user_id=current_user.id,
        source="manual",
    )

    db.commit()
    db.refresh(order)

    # Trigger MRP recalculation if enabled (behind feature flag, graceful degradation)
    try:
        from app.services.mrp_trigger_service import trigger_mrp_recalculation
        from app.core.settings import get_settings
        settings = get_settings()
        
        if settings.AUTO_MRP_ON_SHIPMENT:
            trigger_mrp_recalculation(db, order.id, reason="shipment")
    except Exception as e:
        # Log but don't break shipping - graceful degradation
        logger.warning(
            f"MRP recalculation trigger failed after shipping order {order.id}: {str(e)}",
            exc_info=True
        )

    return {
        "message": "Order shipped successfully",
        "tracking_number": tracking_number,
        "carrier": request.carrier,
        "service": request.service,
        "shipped_at": order.shipped_at.isoformat(),
        "label_url": None,  # Would be actual label URL with carrier integration
    }


# ============================================================================
# ENDPOINT: Generate Production Orders from Sales Order
# ============================================================================

@router.post("/{order_id}/generate-production-orders")
async def generate_production_orders(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate production orders from a sales order (admin only).

    For line_item orders: Creates one production order per line item.
    For quote_based orders: Creates a single production order.

    Requirements:
    - Sales order must exist
    - Sales order must not be cancelled
    - Line items must have valid products
    - No duplicate production orders (checks existing)

    Returns:
        List of created production order codes
    """
    # Admin-only endpoint
    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can generate production orders"
        )

    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )

    if order.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate production orders for cancelled sales order"
        )

    # Check if production orders already exist for the specific line item products
    # (not just any PO linked to the sales order - those could be sub-assemblies)
    if order.order_type == "line_item":
        line_product_ids = [line.product_id for line in order.lines if line.product_id]
        existing_pos = db.query(ProductionOrder).filter(
            ProductionOrder.sales_order_id == order_id,
            ProductionOrder.product_id.in_(line_product_ids)
        ).all()
    else:
        existing_pos = db.query(ProductionOrder).filter(
            ProductionOrder.sales_order_id == order_id
        ).all()

    if existing_pos:
        return {
            "message": "Production orders already exist",
            "existing_orders": [po.code for po in existing_pos],
            "created_orders": []
        }

    created_orders = []
    year = datetime.utcnow().year

    # Helper to generate next PO code
    def get_next_po_code():
        last_po = (
            db.query(ProductionOrder)
            .filter(ProductionOrder.code.like(f"PO-{year}-%"))
            .order_by(desc(ProductionOrder.code))
            .first()
        )
        if last_po:
            last_num = int(last_po.code.split("-")[2])
            next_num = last_num + 1
        else:
            next_num = 1
        return f"PO-{year}-{next_num:04d}"

    if order.order_type == "line_item":
        # Get all lines for this order
        lines = db.query(SalesOrderLine).filter(
            SalesOrderLine.sales_order_id == order_id
        ).order_by(SalesOrderLine.id).all()

        if not lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sales order has no line items"
            )

        for idx, line in enumerate(lines, start=1):
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product ID {line.product_id} not found for line {idx}"
                )

            # Find BOM for product (first active one)
            bom = db.query(BOM).filter(
                BOM.product_id == line.product_id,
                BOM.active.is_(True)
            ).first()

            routing = db.query(Routing).filter(
                Routing.product_id == line.product_id,
                Routing.is_active.is_(True)
            ).first()

            po_code = get_next_po_code()

            production_order = ProductionOrder(
                code=po_code,
                product_id=line.product_id,
                bom_id=bom.id if bom else None,
                routing_id=routing.id if routing else None,
                sales_order_id=order.id,
                sales_order_line_id=line.id,
                quantity_ordered=line.quantity,
                quantity_completed=0,
                quantity_scrapped=0,
                source="sales_order",
                status="draft",
                priority=3,  # Normal priority
                notes=f"Generated from {order.order_number} Line {idx}",
                created_by=current_user.email,
            )

            db.add(production_order)
            db.flush()  # Get the ID for the next PO code lookup

            # Allocate materials for this production order
            reserve_production_materials(
                db=db,
                production_order=production_order,
                created_by=current_user.email,
            )

            created_orders.append(po_code)

    else:
        # quote_based order - should already have production order from convert
        # But we can create one if it doesn't exist

        # For quote-based, we need to find the product_id from the quote
        if order.quote_id:
            quote = db.query(Quote).filter(Quote.id == order.quote_id).first()
            if quote and quote.product_id:
                product_id = quote.product_id

                bom = db.query(BOM).filter(
                    BOM.product_id == product_id,
                    BOM.active.is_(True)
                ).first()

                routing = db.query(Routing).filter(
                    Routing.product_id == product_id,
                    Routing.is_active.is_(True)
                ).first()

                po_code = get_next_po_code()

                production_order = ProductionOrder(
                    code=po_code,
                    product_id=product_id,
                    bom_id=bom.id if bom else None,
                    routing_id=routing.id if routing else None,
                    sales_order_id=order.id,
                    quantity_ordered=order.quantity,
                    quantity_completed=0,
                    quantity_scrapped=0,
                    source="sales_order",
                    status="draft",
                    priority=3,
                    notes=f"Generated from {order.order_number}",
                    created_by=current_user.email,
                )

                db.add(production_order)
                db.flush()  # Get the ID for allocation

                # Allocate materials for this production order
                reserve_production_materials(
                    db=db,
                    production_order=production_order,
                    created_by=current_user.email,
                )

                created_orders.append(po_code)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quote-based order has no product. Please accept the quote first."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quote-based order has no associated quote"
            )

    # Record event for production order creation
    if created_orders:
        record_order_event(
            db=db,
            order_id=order_id,
            event_type="production_started",
            title=f"Created {len(created_orders)} work order(s)",
            description=f"Work orders: {', '.join(created_orders)}",
            user_id=current_user.id,
        )

    db.commit()

    # Update order status to confirmed if pending
    if order.status == "pending":
        order.status = "confirmed"
        order.confirmed_at = datetime.utcnow()
        db.commit()

    return {
        "message": f"Created {len(created_orders)} production order(s)",
        "created_orders": created_orders,
        "existing_orders": []
    }


# ============================================================================
# Helper: Build response with lines
# ============================================================================

def build_sales_order_response(order: SalesOrder, db: Session) -> SalesOrderResponse:
    """Build sales order response with line items"""
    lines = []
    if order.order_type == "line_item":
        order_lines = db.query(SalesOrderLine).filter(
            SalesOrderLine.sales_order_id == order.id
        ).order_by(SalesOrderLine.id).all()  # Order by ID since line_number doesn't exist

        for line in order_lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            # Use actual database columns: total (not total_price)
            line_total = line.total if line.total else (line.unit_price * line.quantity)
            lines.append(SalesOrderLineResponse(
                id=line.id,
                product_id=line.product_id,
                product_sku=product.sku if product else "",
                product_name=product.name if product else "",
                quantity=line.quantity if line.quantity else Decimal("0"),
                unit_price=line.unit_price,
                total=line_total,
                notes=line.notes,
            ))

    # Build response from order dict, manually constructing to avoid SQLAlchemy relationship validation
    # The issue is that model_validate(order) tries to validate order.lines which are SQLAlchemy
    # objects without the computed properties (line_number, total_price)
    order_data = {
        "id": order.id,
        "user_id": order.user_id,
        "quote_id": order.quote_id,
        "product_id": getattr(order, "product_id", None),  # For BOM explosion
        "order_number": order.order_number,
        "order_type": order.order_type,
        "source": order.source,
        "source_order_id": order.source_order_id,
        "product_name": order.product_name,
        "quantity": int(order.quantity) if order.quantity else 0,
        "material_type": order.material_type,
        "finish": order.finish,
        "unit_price": order.unit_price,
        "total_price": order.total_price,
        "tax_amount": order.tax_amount if order.tax_amount is not None else Decimal("0"),
        "shipping_cost": order.shipping_cost if order.shipping_cost is not None else Decimal("0"),
        "grand_total": order.grand_total,
        "status": order.status,
        "fulfillment_status": getattr(order, "fulfillment_status", "pending"),
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "payment_transaction_id": order.payment_transaction_id,
        "paid_at": getattr(order, "paid_at", None),
        "estimated_completion_date": getattr(order, "estimated_completion_date", None),
        "actual_completion_date": getattr(order, "actual_completion_date", None),
        # Customer information
        "customer_id": getattr(order, "customer_id", None),
        "customer_name": getattr(order, "customer_name", None),
        "customer_email": getattr(order, "customer_email", None),
        "customer_phone": getattr(order, "customer_phone", None),
        # Shipping address
        "shipping_address_line1": order.shipping_address_line1,
        "shipping_address_line2": order.shipping_address_line2,
        "shipping_city": order.shipping_city,
        "shipping_state": order.shipping_state,
        "shipping_zip": order.shipping_zip,
        "shipping_country": order.shipping_country,
        "tracking_number": order.tracking_number,
        "carrier": order.carrier,
        "shipped_at": order.shipped_at,
        "delivered_at": order.delivered_at,
        "rush_level": order.rush_level,
        "customer_notes": order.customer_notes,
        "internal_notes": order.internal_notes,
        "production_notes": order.production_notes,
        "cancelled_at": getattr(order, "cancelled_at", None),
        "cancellation_reason": order.cancellation_reason,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "confirmed_at": getattr(order, "confirmed_at", None),
        "lines": lines,  # Use the properly formatted lines we built above
    }
    
    response = SalesOrderResponse.model_validate(order_data)
    return response


# ============================================================================
# ENDPOINT: Order Events (Activity Timeline)
# ============================================================================

@router.get("/{order_id}/events", response_model=OrderEventListResponse)
async def get_order_events(
    order_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get activity timeline for a sales order.

    Returns all events (status changes, notes, payments, etc.) in reverse
    chronological order (most recent first).
    """
    # Verify order exists and user has access
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )

    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if order.user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this order's events"
        )

    # Query events
    query = db.query(OrderEvent).filter(OrderEvent.sales_order_id == order_id)
    total = query.count()

    events = (
        query
        .order_by(desc(OrderEvent.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Build response with user names
    items = []
    for event in events:
        user_name = None
        if event.user_id:
            user = db.query(User).filter(User.id == event.user_id).first()
            if user:
                user_name = user.full_name or user.email

        items.append(OrderEventResponse(
            id=event.id,
            sales_order_id=event.sales_order_id,
            user_id=event.user_id,
            user_name=user_name,
            event_type=event.event_type,
            title=event.title,
            description=event.description,
            old_value=event.old_value,
            new_value=event.new_value,
            metadata_key=event.metadata_key,
            metadata_value=event.metadata_value,
            created_at=event.created_at,
        ))

    return OrderEventListResponse(items=items, total=total)


@router.post("/{order_id}/events", response_model=OrderEventResponse, status_code=status.HTTP_201_CREATED)
async def add_order_event(
    order_id: int,
    event_data: OrderEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add an event to a sales order's activity timeline.

    Typically used for adding notes. Status changes and payments are
    automatically recorded by their respective endpoints.
    """
    # Verify order exists and user has access
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )

    is_admin = getattr(current_user, "account_type", None) == "admin" or getattr(current_user, "is_admin", False)
    if order.user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add events to this order"
        )

    # Create event
    event = OrderEvent(
        sales_order_id=order_id,
        user_id=current_user.id,
        event_type=event_data.event_type,
        title=event_data.title,
        description=event_data.description,
        old_value=event_data.old_value,
        new_value=event_data.new_value,
        metadata_key=event_data.metadata_key,
        metadata_value=event_data.metadata_value,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    user_name = current_user.full_name or current_user.email

    return OrderEventResponse(
        id=event.id,
        sales_order_id=event.sales_order_id,
        user_id=event.user_id,
        user_name=user_name,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        old_value=event.old_value,
        new_value=event.new_value,
        metadata_key=event.metadata_key,
        metadata_value=event.metadata_value,
        created_at=event.created_at,
    )


# Helper function to record order events (for use by other endpoints)
def record_order_event(
    db: Session,
    order_id: int,
    event_type: str,
    title: str,
    description: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    user_id: Optional[int] = None,
    metadata_key: Optional[str] = None,
    metadata_value: Optional[str] = None,
) -> None:
    """
    Helper function to record an order event.

    Called internally by status change, payment, and shipping endpoints.
    """
    event = OrderEvent(
        sales_order_id=order_id,
        user_id=user_id,
        event_type=event_type,
        title=title,
        description=description,
        old_value=old_value,
        new_value=new_value,
        metadata_key=metadata_key,
        metadata_value=metadata_value,
    )
    db.add(event)
    # Don't commit - let the calling function handle the transaction


# ============================================================================
# Shipping Events Timeline
# ============================================================================

@router.get("/{order_id}/shipping-events", response_model=ShippingEventListResponse)
async def list_shipping_events(
    order_id: int,
    limit: int = Query(default=50, ge=1, le=200, description="Max events to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    List shipping events for a sales order

    Returns a timeline of all shipping events (label purchase, in transit,
    delivered, etc.) ordered by most recent first.
    """
    # Verify order exists
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")

    # Query events with pagination
    query = db.query(ShippingEvent).filter(
        ShippingEvent.sales_order_id == order_id
    ).order_by(desc(ShippingEvent.created_at))

    total = query.count()
    events = query.offset(offset).limit(limit).all()

    # Build response with user names
    items = []
    for event in events:
        user_name = None
        if event.user_id and event.user:
            user_name = event.user.name or event.user.email

        items.append(ShippingEventResponse(
            id=event.id,
            sales_order_id=event.sales_order_id,
            user_id=event.user_id,
            user_name=user_name,
            event_type=event.event_type,
            title=event.title,
            description=event.description,
            tracking_number=event.tracking_number,
            carrier=event.carrier,
            location_city=event.location_city,
            location_state=event.location_state,
            location_zip=event.location_zip,
            event_date=event.event_date,
            event_timestamp=event.event_timestamp,
            metadata_key=event.metadata_key,
            metadata_value=event.metadata_value,
            source=event.source,
            created_at=event.created_at,
        ))

    return ShippingEventListResponse(items=items, total=total)


@router.post("/{order_id}/shipping-events", response_model=ShippingEventResponse, status_code=201)
async def add_shipping_event(
    order_id: int,
    request: ShippingEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a shipping event to a sales order

    Used for manual tracking updates or carrier webhook integrations.
    """
    # Verify order exists
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")

    event = record_shipping_event(
        db=db,
        sales_order_id=order_id,
        event_type=request.event_type.value,
        title=request.title,
        description=request.description,
        tracking_number=request.tracking_number,
        carrier=request.carrier,
        location_city=request.location_city,
        location_state=request.location_state,
        location_zip=request.location_zip,
        event_date=request.event_date,
        event_timestamp=request.event_timestamp,
        user_id=current_user.id,
        metadata_key=request.metadata_key,
        metadata_value=request.metadata_value,
        source=request.source.value,
    )
    db.commit()
    db.refresh(event)

    user_name = current_user.name or current_user.email

    logger.info(f"Added shipping event '{request.event_type.value}' to order {order.order_number}")

    return ShippingEventResponse(
        id=event.id,
        sales_order_id=event.sales_order_id,
        user_id=event.user_id,
        user_name=user_name,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        tracking_number=event.tracking_number,
        carrier=event.carrier,
        location_city=event.location_city,
        location_state=event.location_state,
        location_zip=event.location_zip,
        event_date=event.event_date,
        event_timestamp=event.event_timestamp,
        metadata_key=event.metadata_key,
        metadata_value=event.metadata_value,
        source=event.source,
        created_at=event.created_at,
    )
