"""
Purchase Orders API Endpoints
"""
import os
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from typing import Annotated, Optional
from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.db.session import get_db
from app.logging_config import get_logger
from app.services.uom_service import convert_quantity_safe, get_conversion_factor
from app.services.inventory_helpers import is_material
from app.services.transaction_service import TransactionService, ReceiptItem
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.product import Product
from app.models.inventory import Inventory, InventoryLocation
from app.models.material_spool import MaterialSpool
from app.models.traceability import MaterialLot
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.deps import get_pagination_params
from app.models.user import User
from app.schemas.purchasing import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderListResponse,
    PurchaseOrderResponse,
    POLineCreate,
    POLineUpdate,
    POLineResponse,
    POStatusUpdate,
    ReceivePORequest,
    ReceivePOResponse,
)
from app.schemas.common import PaginationParams, ListResponse, PaginationMeta
from app.schemas.purchasing_event import (
    PurchasingEventCreate,
    PurchasingEventResponse,
    PurchasingEventListResponse,
)
from app.models.purchasing_event import PurchasingEvent
from app.services.event_service import record_purchasing_event

router = APIRouter()
logger = get_logger(__name__)


def _generate_po_number(db: Session) -> str:
    """Generate next PO number (PO-2025-001, PO-2025-002, etc.)"""
    year = datetime.now(timezone.utc).year
    pattern = f"PO-{year}-%"
    last = db.query(PurchaseOrder).filter(
        PurchaseOrder.po_number.like(pattern)
    ).order_by(desc(PurchaseOrder.po_number)).first()

    if last:
        try:
            num = int(last.po_number.split("-")[2])
            return f"PO-{year}-{num + 1:03d}"
        except (IndexError, ValueError):
            pass
    return f"PO-{year}-001"


def _calculate_totals(po: PurchaseOrder) -> None:
    """Recalculate PO totals from lines"""
    subtotal = sum(line.line_total for line in po.lines) if po.lines else Decimal("0")
    po.subtotal = subtotal
    po.total_amount = subtotal + (po.tax_amount or Decimal("0")) + (po.shipping_cost or Decimal("0"))


# ============================================================================
# Purchase Order CRUD
# ============================================================================

@router.get("/", response_model=ListResponse[PurchaseOrderListResponse])
async def list_purchase_orders(
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    status: Optional[str] = Query(None, description="Filter by status (draft, ordered, shipped, received, closed, cancelled)"),
    vendor_id: Optional[int] = Query(None, description="Filter by vendor ID"),
    search: Optional[str] = Query(None, description="Search by PO number"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List purchase orders with pagination

    - **status**: Filter by status (draft, ordered, shipped, received, closed, cancelled)
    - **vendor_id**: Filter by vendor
    - **search**: Search by PO number
    - **offset**: Number of records to skip (default: 0)
    - **limit**: Maximum records to return (default: 50, max: 500)
    """
    query = db.query(PurchaseOrder).options(joinedload(PurchaseOrder.vendor))

    if status:
        query = query.filter(PurchaseOrder.status == status)

    if vendor_id:
        query = query.filter(PurchaseOrder.vendor_id == vendor_id)

    if search:
        query = query.filter(PurchaseOrder.po_number.ilike(f"%{search}%"))

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    pos = query.order_by(desc(PurchaseOrder.created_at)).offset(pagination.offset).limit(pagination.limit).all()

    result = []
    for po in pos:
        result.append(PurchaseOrderListResponse(
            id=po.id,
            po_number=po.po_number,
            vendor_id=po.vendor_id,
            vendor_name=po.vendor.name if po.vendor else "Unknown",
            status=po.status,
            order_date=po.order_date,
            expected_date=po.expected_date,
            received_date=po.received_date,  # User-entered date from receive workflow
            total_amount=po.total_amount,
            line_count=len(po.lines),
            created_at=po.created_at,
        ))

    return ListResponse(
        items=result,
        pagination=PaginationMeta(
            total=total,
            offset=pagination.offset,
            limit=pagination.limit,
            returned=len(result)
        )
    )


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get purchase order details by ID"""
    po = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.vendor),
        joinedload(PurchaseOrder.lines).joinedload(PurchaseOrderLine.product)
    ).filter(PurchaseOrder.id == po_id).first()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    # Build response with line details
    lines = []
    for line in po.lines:
        lines.append(POLineResponse(
            id=line.id,
            line_number=line.line_number,
            product_id=line.product_id,
            product_sku=line.product.sku if line.product else None,
            product_name=line.product.name if line.product else None,
            product_unit=line.product.unit if line.product else None,
            quantity_ordered=line.quantity_ordered,
            quantity_received=line.quantity_received,
            unit_cost=line.unit_cost,
            purchase_unit=line.purchase_unit,
            line_total=line.line_total,
            notes=line.notes,
            created_at=line.created_at,
            updated_at=line.updated_at,
        ))

    return PurchaseOrderResponse(
        id=po.id,
        po_number=po.po_number,
        vendor_id=po.vendor_id,
        vendor_name=po.vendor.name if po.vendor else None,
        status=po.status,
        order_date=po.order_date,
        expected_date=po.expected_date,
        shipped_date=po.shipped_date,
        received_date=po.received_date,
        tracking_number=po.tracking_number,
        carrier=po.carrier,
        subtotal=po.subtotal,
        tax_amount=po.tax_amount,
        shipping_cost=po.shipping_cost,
        total_amount=po.total_amount,
        payment_method=po.payment_method,
        payment_reference=po.payment_reference,
        document_url=po.document_url,
        notes=po.notes,
        created_by=po.created_by,
        created_at=po.created_at,
        updated_at=po.updated_at,
        lines=lines,
    )


@router.post("/", response_model=PurchaseOrderResponse, status_code=201)
async def create_purchase_order(
    request: PurchaseOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new purchase order"""
    # Verify vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == request.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Generate PO number
    po_number = _generate_po_number(db)

    po = PurchaseOrder(
        po_number=po_number,
        vendor_id=request.vendor_id,
        status="draft",
        order_date=request.order_date,
        expected_date=request.expected_date,
        tracking_number=request.tracking_number,
        carrier=request.carrier,
        tax_amount=request.tax_amount,
        shipping_cost=request.shipping_cost,
        payment_method=request.payment_method,
        payment_reference=request.payment_reference,
        document_url=request.document_url,
        notes=request.notes,
        created_by=current_user.email,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(po)
    db.flush()  # Get PO ID

    # Add lines
    for i, line_data in enumerate(request.lines, start=1):
        # Verify product exists
        product = db.query(Product).filter(Product.id == line_data.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product ID {line_data.product_id} not found")

        line = PurchaseOrderLine(
            purchase_order_id=po.id,
            line_number=i,
            product_id=line_data.product_id,
            quantity_ordered=line_data.quantity_ordered,
            quantity_received=Decimal("0"),
            purchase_unit=line_data.purchase_unit or getattr(product, 'purchase_uom', None) or product.unit,
            unit_cost=line_data.unit_cost,
            line_total=line_data.quantity_ordered * line_data.unit_cost,
            notes=line_data.notes,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(line)
        po.lines.append(line)

    # Calculate totals
    _calculate_totals(po)

    # Record creation event
    record_purchasing_event(
        db=db,
        purchase_order_id=po.id,
        event_type="created",
        title="Purchase Order Created",
        description=f"Created for vendor {vendor.name}",
        new_value="draft",
        user_id=current_user.id,
    )

    db.commit()
    db.refresh(po)

    logger.info(f"Created PO {po.po_number} for vendor {vendor.name}")

    # Return full response
    return await get_purchase_order(po.id, current_user, db)


@router.put("/{po_id}", response_model=PurchaseOrderResponse)
async def update_purchase_order(
    po_id: int,
    request: PurchaseOrderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a purchase order"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    # Only allow updates on draft/ordered POs
    if po.status in ["received", "closed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update PO in '{po.status}' status"
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(po, field, value)

    # Recalculate totals if financial fields changed
    if any(f in update_data for f in ["tax_amount", "shipping_cost"]):
        _calculate_totals(po)

    po.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(po)

    logger.info(f"Updated PO {po.po_number}")
    return await get_purchase_order(po.id, current_user, db)


@router.post("/{po_id}/lines", response_model=PurchaseOrderResponse)
async def add_po_line(
    po_id: int,
    request: POLineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a line to a purchase order"""
    po = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.lines)
    ).filter(PurchaseOrder.id == po_id).first()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.status not in ["draft", "ordered"]:
        raise HTTPException(status_code=400, detail=f"Cannot add lines to PO in '{po.status}' status")

    # Verify product exists
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get next line number
    next_line = max([line.line_number for line in po.lines], default=0) + 1

    line = PurchaseOrderLine(
        purchase_order_id=po.id,
        line_number=next_line,
        product_id=request.product_id,
        quantity_ordered=request.quantity_ordered,
        quantity_received=Decimal("0"),
        purchase_unit=request.purchase_unit or getattr(product, 'purchase_uom', None) or product.unit,
        unit_cost=request.unit_cost,
        line_total=request.quantity_ordered * request.unit_cost,
        notes=request.notes,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(line)

    # Recalculate totals
    po.lines.append(line)
    _calculate_totals(po)
    po.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(po)

    return await get_purchase_order(po.id, current_user, db)


@router.put("/{po_id}/lines/{line_id}", response_model=PurchaseOrderResponse)
async def update_po_line(
    po_id: int,
    line_id: int,
    request: POLineUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a line on a purchase order

    Can update quantity_ordered, unit_cost, or notes for draft/ordered POs.
    Cannot reduce quantity_ordered below quantity_received.
    """
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.status not in ["draft", "ordered"]:
        raise HTTPException(status_code=400, detail=f"Cannot modify PO in '{po.status}' status")

    line = db.query(PurchaseOrderLine).filter(
        PurchaseOrderLine.id == line_id,
        PurchaseOrderLine.purchase_order_id == po_id
    ).first()

    if not line:
        raise HTTPException(status_code=404, detail="Line not found")

    # Validate quantity if being updated
    if request.quantity_ordered is not None:
        if request.quantity_ordered < line.quantity_received:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reduce quantity below received amount ({line.quantity_received})"
            )
        line.quantity_ordered = request.quantity_ordered

    # Update unit cost if provided
    if request.unit_cost is not None:
        line.unit_cost = request.unit_cost

    # Update notes if provided
    if request.notes is not None:
        line.notes = request.notes

    # Recalculate line total
    line.line_total = line.quantity_ordered * line.unit_cost
    line.updated_at = datetime.now(timezone.utc)

    # Recalculate PO totals
    _calculate_totals(po)
    po.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(po)

    logger.info(f"Updated line {line_id} on PO {po.po_number}")
    return await get_purchase_order(po.id, current_user, db)


@router.delete("/{po_id}/lines/{line_id}")
async def delete_po_line(
    po_id: int,
    line_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a line from a purchase order"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.status not in ["draft", "ordered"]:
        raise HTTPException(status_code=400, detail=f"Cannot modify PO in '{po.status}' status")

    line = db.query(PurchaseOrderLine).filter(
        PurchaseOrderLine.id == line_id,
        PurchaseOrderLine.purchase_order_id == po_id
    ).first()

    if not line:
        raise HTTPException(status_code=404, detail="Line not found")

    if line.quantity_received > 0:
        raise HTTPException(status_code=400, detail="Cannot delete line with received quantity")

    db.delete(line)

    # Recalculate totals
    _calculate_totals(po)
    po.updated_at = datetime.now(timezone.utc)

    db.commit()
    return {"message": "Line deleted"}


# ============================================================================
# Status Management
# ============================================================================

@router.post("/{po_id}/status", response_model=PurchaseOrderResponse)
async def update_po_status(
    po_id: int,
    request: POStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update PO status

    Valid transitions:
    - draft -> ordered (places the order)
    - ordered -> shipped (vendor shipped)
    - shipped -> received (fully received)
    - any -> cancelled
    - received -> closed (finalize)
    """
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    old_status = po.status
    new_status = request.status.value

    # Validate transitions
    valid_transitions = {
        "draft": ["ordered", "cancelled"],
        "ordered": ["shipped", "received", "cancelled"],
        "shipped": ["received", "cancelled"],
        "received": ["closed", "cancelled"],  # Allow cancel for errant imports
        "closed": [],
        "cancelled": [],
    }

    if new_status not in valid_transitions.get(old_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{old_status}' to '{new_status}'"
        )

    # Handle specific transitions
    if new_status == "ordered":
        if not po.lines:
            raise HTTPException(status_code=400, detail="Cannot order a PO with no lines")
        po.order_date = po.order_date or date.today()

    elif new_status == "shipped":
        po.shipped_date = date.today()
        if request.tracking_number:
            po.tracking_number = request.tracking_number
        if request.carrier:
            po.carrier = request.carrier

    elif new_status == "received":
        po.received_date = date.today()

    po.status = new_status
    po.updated_at = datetime.now(timezone.utc)

    # Record status change event
    status_titles = {
        "ordered": "Order Placed",
        "shipped": "Marked as Shipped",
        "received": "Marked as Received",
        "closed": "Order Closed",
        "cancelled": "Order Cancelled",
    }
    description = None
    if new_status == "shipped" and request.tracking_number:
        description = f"Tracking: {request.tracking_number}"
        if request.carrier:
            description += f" ({request.carrier})"

    record_purchasing_event(
        db=db,
        purchase_order_id=po.id,
        event_type="status_change",
        title=status_titles.get(new_status, f"Status changed to {new_status}"),
        description=description,
        old_value=old_status,
        new_value=new_status,
        user_id=current_user.id,
    )

    db.commit()
    db.refresh(po)

    logger.info(f"PO {po.po_number} status: {old_status} -> {new_status}")
    return await get_purchase_order(po.id, current_user, db)


# ============================================================================
# Receiving
# ============================================================================

@router.post("/{po_id}/receive", response_model=ReceivePOResponse)
async def receive_purchase_order(
    po_id: int,
    request: ReceivePORequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Receive items from a purchase order

    - Updates quantity_received on PO lines
    - Creates inventory transactions
    - Updates on-hand inventory
    - Auto-transitions to 'received' if fully received
    """
    po = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.lines)
    ).filter(PurchaseOrder.id == po_id).first()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.status not in ["ordered", "shipped"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot receive items on PO in '{po.status}' status"
        )

    # User-entered received date (defaults to today if not provided)
    # This is the date items were ACTUALLY received, not when entered in system
    actual_received_date = request.received_date or date.today()

    # Default location (get first warehouse or create default)
    location_id = request.location_id
    if not location_id:
        default_loc = db.query(InventoryLocation).filter(
            InventoryLocation.type == "warehouse"
        ).first()
        if default_loc:
            location_id = default_loc.id
        else:
            # Create default warehouse
            default_loc = InventoryLocation(
                name="Main Warehouse",
                code="MAIN",
                type="warehouse",
                active=True
            )
            db.add(default_loc)
            db.flush()
            location_id = default_loc.id

    # Build line lookup
    line_map = {line.id: line for line in po.lines}

    transaction_ids = []
    spools_created = []  # Initialize spools list
    material_lots_created = []  # Lot numbers for traceability
    total_received = Decimal("0")
    lines_received = 0

    # Collect items for TransactionService (processed after loop)
    receipt_items_for_service = []

    for item in request.lines:
        if item.line_id not in line_map:
            raise HTTPException(status_code=404, detail=f"Line {item.line_id} not found on this PO")

        line = line_map[item.line_id]
        remaining = line.quantity_ordered - line.quantity_received

        if item.quantity_received > remaining:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot receive {item.quantity_received} for line {item.line_id}. Only {remaining} remaining."
            )

        # Update line
        line.quantity_received = line.quantity_received + item.quantity_received
        line.updated_at = datetime.now(timezone.utc)
        total_received += item.quantity_received
        lines_received += 1

        # Convert quantity from purchase_unit to product's default unit
        product = db.query(Product).filter(Product.id == line.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {line.product_id} not found")
        
        purchase_unit = (line.purchase_unit or product.unit or 'EA').upper().strip()
        product_unit = (product.unit or 'EA').upper().strip()
        
        # Check if this is a material (for cost handling)
        is_mat = is_material(product)
        
        # Convert quantity if units differ
        quantity_received_decimal = Decimal(str(item.quantity_received))
        quantity_for_inventory = quantity_received_decimal
        cost_per_unit_for_inventory = line.unit_cost
        
        if purchase_unit != product_unit:
            # Convert quantity: purchase_unit -> product_unit
            # Use safe conversion which falls back to inline conversions if DB lookup fails
            logger.info(
                f"Converting quantity for PO {po.po_number} line {line.line_number}: "
                f"{quantity_received_decimal} {purchase_unit} -> {product_unit}"
            )
            
            converted_qty, conversion_success = convert_quantity_safe(
                db, quantity_received_decimal, purchase_unit, product_unit
            )
            
            if not conversion_success:
                # Conversion failed - this is a critical error
                logger.error(
                    f"UOM conversion FAILED for PO {po.po_number} line {line.line_number}. "
                    f"Purchase unit: '{purchase_unit}', Product unit: '{product_unit}', "
                    f"Quantity received: {quantity_received_decimal}. "
                    f"Cannot convert incompatible units - this will cause incorrect inventory!"
                )
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Cannot convert {quantity_received_decimal} {purchase_unit} to {product_unit} "
                        f"for product {product.sku}. "
                        f"Units are incompatible. Supported conversions: G↔KG, LB↔KG, OZ↔KG, etc."
                    )
                )
            
            quantity_for_inventory = converted_qty
            logger.info(
                f"Conversion successful: {quantity_received_decimal} {purchase_unit} = {quantity_for_inventory} {product_unit}"
            )
            
            # Convert cost_per_unit: cost per purchase_unit -> cost per product_unit
            # For materials: Convert to $/G since quantity is stored in grams
            # This ensures COGS calculations work correctly: cost_per_unit ($/G) * quantity (G)
            if is_mat:
                # Materials: Convert cost from $/purchase_unit to $/G
                if purchase_unit == "KG":
                    # Purchased in KG, storing in G: divide cost by 1000
                    cost_per_unit_for_inventory = line.unit_cost / Decimal("1000")
                    logger.info(
                        f"Material cost conversion: ${line.unit_cost}/KG → "
                        f"${cost_per_unit_for_inventory}/G"
                    )
                else:
                    # Purchased in other units (G, LB, OZ, etc.) - use conversion factor
                    try:
                        quantity_conversion_factor = get_conversion_factor(db, purchase_unit, "G")
                        cost_conversion_factor = Decimal("1") / quantity_conversion_factor
                        cost_per_unit_for_inventory = line.unit_cost * cost_conversion_factor
                        logger.info(
                            f"Material cost conversion: ${line.unit_cost}/{purchase_unit} → "
                            f"${cost_per_unit_for_inventory}/G (factor: {cost_conversion_factor})"
                        )
                    except Exception as e:
                        logger.error(f"Cost conversion failed for material: {e}")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cannot convert cost from {purchase_unit} to G"
                        )
            else:
                # Non-materials: Convert cost per purchase_unit -> cost per product_unit
                # Cost conversion factor is the inverse of quantity conversion factor
                # Example: $20/LB -> $44.09/KG when converting 1LB -> 0.453592KG
                try:
                    quantity_conversion_factor = get_conversion_factor(db, purchase_unit, product_unit)
                    logger.info(
                        f"Cost conversion: quantity_factor={quantity_conversion_factor} "
                        f"(from {purchase_unit} to {product_unit})"
                    )
                    cost_conversion_factor = Decimal("1") / quantity_conversion_factor
                    cost_per_unit_for_inventory = line.unit_cost * cost_conversion_factor
                    logger.info(
                        f"Cost conversion: cost_factor={cost_conversion_factor}, "
                        f"unit_cost={line.unit_cost}, result={cost_per_unit_for_inventory}"
                    )
                except Exception as e:
                    # If cost conversion fails, use derived factor from quantity conversion
                    qty_received = Decimal(str(item.quantity_received))
                    if qty_received > 0 and quantity_for_inventory > 0:
                        quantity_conversion_factor_derived = quantity_for_inventory / qty_received
                        cost_conversion_factor = Decimal("1") / quantity_conversion_factor_derived
                        cost_per_unit_for_inventory = line.unit_cost * cost_conversion_factor
                        logger.info(
                            f"Cost conversion (fallback): qty_factor={quantity_conversion_factor_derived}, "
                            f"cost_factor={cost_conversion_factor}, unit_cost={line.unit_cost}, "
                            f"result={cost_per_unit_for_inventory}"
                        )
                    else:
                        cost_per_unit_for_inventory = line.unit_cost
                        logger.warning(
                            f"Cost conversion: Cannot derive factor (qty_received={qty_received}, "
                            f"quantity_for_inventory={quantity_for_inventory}), using original cost"
                        )
                    logger.warning(
                        f"Cost conversion factor lookup failed, using derived factor: {e}"
                    )
            
            logger.info(
                f"UOM conversion for PO {po.po_number} line {line.line_number}: "
                f"{item.quantity_received} {purchase_unit} @ ${line.unit_cost}/{purchase_unit} -> "
                f"{quantity_for_inventory} {product_unit} @ ${cost_per_unit_for_inventory}/"
                f"{'G' if is_mat else product_unit} (material: {is_mat})"
            )

        # ============================================================================
        # STAR SCHEMA: Convert to transaction unit (GRAMS for materials, native for others)
        # ============================================================================
        # For materials: Convert to GRAMS before transaction (single source of truth)
        # For others: Use product_unit as-is
        transaction_quantity = quantity_for_inventory
        if is_material(product):
            # Material: Convert to grams for transaction storage
            # quantity_for_inventory is in product_unit (typically KG), but could be G if purchased in G
            # Check if we need to convert to grams
            if product_unit == "KG":
                transaction_quantity = quantity_for_inventory * Decimal("1000")
            elif product_unit == "G":
                # Already in grams - use as-is
                transaction_quantity = quantity_for_inventory
            elif product_unit == "LB":
                transaction_quantity = quantity_for_inventory * Decimal("453.592")
            elif product_unit == "OZ":
                transaction_quantity = quantity_for_inventory * Decimal("28.3495")
            else:
                # Unknown unit - assume grams for materials
                logger.warning(
                    f"Material {product.sku} has unknown unit '{product_unit}', assuming grams"
                )
                transaction_quantity = quantity_for_inventory
            
            logger.info(
                f"Material conversion for transaction: {quantity_for_inventory} {product_unit} -> "
                f"{transaction_quantity} G (product: {product.sku}, purchased in: {purchase_unit})"
            )
            
            # ============================================================================
            # FIX: Ensure cost is ALWAYS in $/G for materials (matches transaction unit)
            # ============================================================================
            # This handles the case where purchase_unit == product_unit (e.g., both KG)
            # In that case, the earlier cost conversion block was skipped, but we still
            # need to convert cost from $/product_unit to $/G since quantity is now in grams.
            #
            # Example: Purchase 1 KG @ $20/KG, product_unit=KG
            #   - Earlier block skipped (units match)
            #   - Quantity converted: 1 KG -> 1000 G
            #   - Cost MUST be: $20/KG -> $0.02/G
            #   - Verify: 1000 G × $0.02/G = $20 ✓
            #
            # IMPORTANT: Only run this when purchase_unit == product_unit
            # When purchase_unit != product_unit, cost was already converted above (lines 703-727)
            if purchase_unit == product_unit:
                if product_unit == "KG":
                    # Cost was in $/KG, convert to $/G
                    cost_per_unit_for_inventory = line.unit_cost / Decimal("1000")
                    logger.info(
                        f"Material cost normalization (KG->G): ${line.unit_cost}/KG -> "
                        f"${cost_per_unit_for_inventory}/G"
                    )
                elif product_unit == "LB":
                    # Cost was in $/LB, convert to $/G (1 LB = 453.592 G)
                    cost_per_unit_for_inventory = line.unit_cost / Decimal("453.592")
                    logger.info(
                        f"Material cost normalization (LB->G): ${line.unit_cost}/LB -> "
                        f"${cost_per_unit_for_inventory}/G"
                    )
                elif product_unit == "OZ":
                    # Cost was in $/OZ, convert to $/G (1 OZ = 28.3495 G)
                    cost_per_unit_for_inventory = line.unit_cost / Decimal("28.3495")
                    logger.info(
                        f"Material cost normalization (OZ->G): ${line.unit_cost}/OZ -> "
                        f"${cost_per_unit_for_inventory}/G"
                    )
                elif product_unit == "G":
                    # Already in $/G, no conversion needed
                    logger.info(
                        f"Material cost already in $/G: ${cost_per_unit_for_inventory}/G"
                    )
                else:
                    # Unknown unit - log warning but keep original cost
                    logger.warning(
                        f"Material {product.sku} has unknown unit '{product_unit}', "
                        f"cost not normalized. This may cause incorrect COGS calculations!"
                    )
        # For non-materials, transaction_quantity = quantity_for_inventory (already in product_unit)

        # Collect for TransactionService batch processing
        transaction_unit = 'G' if is_mat else product_unit
        receipt_items_for_service.append(ReceiptItem(
            product_id=line.product_id,
            quantity=transaction_quantity,
            unit_cost=cost_per_unit_for_inventory,
            unit=transaction_unit,
            lot_number=item.lot_number,
        ))

        # Update product average cost using proper weighted average
        # Formula: (old_qty × old_cost + new_qty × new_cost) / (old_qty + new_qty)
        if product:
            # Get current on-hand quantity BEFORE this receipt
            from sqlalchemy import func as sql_func
            total_on_hand = db.query(sql_func.coalesce(
                sql_func.sum(Inventory.on_hand_quantity), 0
            )).filter(Inventory.product_id == product.id).scalar()

            old_qty = Decimal(str(total_on_hand)) - transaction_quantity  # Subtract what we just added
            old_cost = Decimal(str(product.average_cost or 0))
            new_qty = transaction_quantity
            new_cost = cost_per_unit_for_inventory

            total_qty = old_qty + new_qty
            if total_qty > 0:
                weighted_avg = (old_qty * old_cost + new_qty * new_cost) / total_qty
                product.average_cost = float(weighted_avg.quantize(Decimal("0.0001")))
                logger.debug(
                    f"Weighted avg for {product.sku}: "
                    f"({old_qty}×${old_cost} + {new_qty}×${new_cost}) / {total_qty} = ${product.average_cost}"
                )
            elif new_qty > 0:
                # First receipt - use new cost
                product.average_cost = float(new_cost)

            product.last_cost = float(cost_per_unit_for_inventory)
            product.last_cost_date = datetime.now(timezone.utc)
            product.updated_at = datetime.now(timezone.utc)

        # ============================================================================
        # MaterialLot Creation (for traceability)
        # ============================================================================
        # Create MaterialLot for supply/component/material items to enable traceability
        if product.item_type in ('supply', 'component', 'material') or product.material_type_id:
            from sqlalchemy import extract
            year = datetime.now(timezone.utc).year

            # Count existing lots for this product this year to generate sequence
            existing_count = db.query(MaterialLot).filter(
                MaterialLot.product_id == product.id,
                extract('year', MaterialLot.received_date) == year
            ).count()

            lot_number = f"{product.sku}-{year}-{existing_count + 1:04d}"

            # Get location code for storage
            location = db.query(InventoryLocation).filter(
                InventoryLocation.id == location_id
            ).first() if location_id else None

            material_lot = MaterialLot(
                lot_number=lot_number,
                product_id=product.id,
                vendor_id=po.vendor_id,
                purchase_order_id=po.id,
                vendor_lot_number=item.vendor_lot_number or item.lot_number,
                quantity_received=transaction_quantity,
                quantity_consumed=Decimal("0"),
                quantity_scrapped=Decimal("0"),
                quantity_adjusted=Decimal("0"),
                status="active",
                inspection_status="pending",
                received_date=actual_received_date,
                unit_cost=cost_per_unit_for_inventory,
                location=location.code if location else "MAIN",
            )
            db.add(material_lot)
            db.flush()
            material_lots_created.append(lot_number)

            logger.info(
                f"Created MaterialLot {lot_number} for {product.sku}: "
                f"{transaction_quantity} units @ ${cost_per_unit_for_inventory}/unit "
                f"(vendor lot: {material_lot.vendor_lot_number or 'N/A'})"
            )

        # ============================================================================
        # Spool Creation (if requested for material products)
        # ============================================================================
        if item.create_spools and item.spools:
            # Validate product is a material/supply type with material_type_id
            if product.item_type not in ('supply', 'material') or not product.material_type_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Spool creation only available for material products with material_type. {product.sku} is type '{product.item_type}'"
                )
            
            # Convert received quantity to grams for validation
            # quantity_for_inventory is already in product's unit from conversion above
            received_qty_g = quantity_for_inventory
            product_unit_upper = (product.unit or 'EA').upper().strip()
            
            # Convert to grams if not already in grams
            if product_unit_upper == 'KG':
                received_qty_g = quantity_for_inventory * Decimal("1000")
            elif product_unit_upper == 'G':
                # Already in grams
                pass
            elif product_unit_upper == 'LB':
                received_qty_g = quantity_for_inventory * Decimal("453.59237")
            elif product_unit_upper == 'OZ':
                received_qty_g = quantity_for_inventory * Decimal("28.34952")
            else:
                logger.warning(f"Material product {product.sku} has unexpected unit: {product.unit}, assuming grams")
            
            # Validate sum of spool weights equals received quantity (in grams)
            spool_weight_sum_g = sum(Decimal(str(s.weight_g)) for s in item.spools)
            tolerance = Decimal("0.1")  # 0.1g tolerance
            
            if abs(spool_weight_sum_g - received_qty_g) > tolerance:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Spool weights sum ({spool_weight_sum_g}g) must equal received quantity ({received_qty_g}g) "
                        f"for product {product.sku}. Difference: {abs(spool_weight_sum_g - received_qty_g):.2f}g"
                    )
                )
            
            # Create spools
            for idx, spool_data in enumerate(item.spools, start=1):
                # Generate spool number if not provided
                spool_number = spool_data.spool_number or f"{po.po_number}-L{line.line_number}-{idx:03d}"
                
                # Check uniqueness
                existing = db.query(MaterialSpool).filter(
                    MaterialSpool.spool_number == spool_number
                ).first()
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Spool number '{spool_number}' already exists"
                    )
                
                # Create spool (store in grams despite column name)
                spool = MaterialSpool(
                    spool_number=spool_number,
                    product_id=line.product_id,
                    initial_weight_kg=spool_data.weight_g,  # Actually grams despite column name
                    current_weight_kg=spool_data.weight_g,   # Actually grams despite column name
                    status="active",
                    location_id=location_id,
                    supplier_lot_number=spool_data.supplier_lot_number or item.lot_number,
                    expiry_date=spool_data.expiry_date,
                    notes=spool_data.notes,
                    received_date=datetime.combine(actual_received_date, datetime.min.time()),  # Use user-entered date
                    created_by=current_user.email,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(spool)
                db.flush()  # Get spool ID
                
                # Track created spools for response
                spools_created.append(spool_number)
                
                logger.info(
                    f"Created spool {spool_number} for {product.sku}: {spool_data.weight_g}g "
                    f"(lot: {spool.supplier_lot_number or 'N/A'})"
                )

    # =========================================================================
    # PO RECEIPT via TransactionService (atomic + GL entries)
    # Accounting: DR 1200 Raw Materials, CR 2000 Accounts Payable
    # =========================================================================
    if receipt_items_for_service:
        txn_service = TransactionService(db)
        inv_txns, journal_entry = txn_service.receive_purchase_order(
            purchase_order_id=po.id,
            items=receipt_items_for_service,
            user_id=current_user.id if current_user else None,
        )
        transaction_ids = [txn.id for txn in inv_txns]

    # Check if fully received
    all_received = all(
        line.quantity_received >= line.quantity_ordered
        for line in po.lines
    )

    if all_received:
        po.status = "received"
        po.received_date = actual_received_date  # Use user-entered date

    po.updated_at = datetime.now(timezone.utc)

    # Record receipt event
    event_type = "receipt" if all_received else "partial_receipt"
    event_title = "Items Received" if all_received else "Partial Receipt"
    event_description = f"Received {total_received} units across {lines_received} line(s)"
    if spools_created:
        event_description += f". Created {len(spools_created)} spool(s)."
    if material_lots_created:
        event_description += f" Created {len(material_lots_created)} material lot(s) for traceability."

    record_purchasing_event(
        db=db,
        purchase_order_id=po.id,
        event_type=event_type,
        title=event_title,
        description=event_description,
        event_date=actual_received_date,
        user_id=current_user.id,
        metadata_key="quantity_received",
        metadata_value=str(total_received),
    )

    # If fully received, also record status change event
    if all_received:
        record_purchasing_event(
            db=db,
            purchase_order_id=po.id,
            event_type="status_change",
            title="Fully Received",
            description="All items received - PO status updated",
            old_value="ordered",
            new_value="received",
            event_date=actual_received_date,
            user_id=current_user.id,
        )

    db.commit()

    logger.info(f"Received {total_received} items on PO {po.po_number}")

    return ReceivePOResponse(
        po_number=po.po_number,
        lines_received=lines_received,
        total_quantity=total_received,
        inventory_updated=True,
        transactions_created=transaction_ids,
        spools_created=spools_created,
        material_lots_created=material_lots_created,
    )


# ============================================================================
# File Upload (Google Drive)
# ============================================================================

@router.post("/{po_id}/upload")
async def upload_po_document(
    po_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a document for a purchase order (invoice, receipt, etc.)

    Uploads to Google Drive if configured, otherwise saves locally.
    Returns the document URL which is saved to the PO.
    """
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    # Validate file type
    allowed_types = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
        "text/csv",
    ]
    content_type = file.content_type or "application/octet-stream"

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed. Allowed: PDF, JPEG, PNG, XLSX, CSV"
        )

    # Read file content
    file_content = await file.read()

    # Generate filename with PO number
    ext = os.path.splitext(file.filename or "document")[1] or ".pdf"
    safe_filename = f"{po.po_number}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}{ext}"

    # Save locally
    upload_dir = os.path.join("uploads", "purchase_orders")
    os.makedirs(upload_dir, exist_ok=True)

    local_path = os.path.join(upload_dir, safe_filename)
    with open(local_path, "wb") as f:
        f.write(file_content)

    # For local files, we'll store a relative path
    # The frontend can construct the full URL or a download endpoint can serve it
    po.document_url = f"/uploads/purchase_orders/{safe_filename}"
    po.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"Saved PO document locally: {local_path}")

    return {
        "success": True,
        "storage": "local",
        "url": po.document_url,
        "filename": safe_filename,
    }


# ============================================================================
# Delete
# ============================================================================

@router.delete("/{po_id}")
async def delete_purchase_order(
    po_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a purchase order

    Can only delete draft POs. Others must be cancelled.
    """
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete PO in '{po.status}' status. Cancel it instead."
        )

    db.delete(po)
    db.commit()

    logger.info(f"Deleted PO {po.po_number}")
    return {"message": f"Purchase order {po.po_number} deleted"}


# ============================================================================
# Event Timeline
# ============================================================================

@router.get("/{po_id}/events", response_model=PurchasingEventListResponse)
async def list_po_events(
    po_id: int,
    limit: int = Query(default=50, ge=1, le=200, description="Max events to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List activity events for a purchase order

    Returns a timeline of all events (status changes, receipts, notes, etc.)
    ordered by most recent first.
    """
    # Verify PO exists
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    # Query events with pagination
    query = db.query(PurchasingEvent).filter(
        PurchasingEvent.purchase_order_id == po_id
    ).order_by(desc(PurchasingEvent.created_at))

    total = query.count()
    events = query.offset(offset).limit(limit).all()

    # Build response with user names
    items = []
    for event in events:
        user_name = None
        if event.user_id and event.user:
            user_name = event.user.full_name

        items.append(PurchasingEventResponse(
            id=event.id,
            purchase_order_id=event.purchase_order_id,
            user_id=event.user_id,
            user_name=user_name,
            event_type=event.event_type,
            title=event.title,
            description=event.description,
            old_value=event.old_value,
            new_value=event.new_value,
            event_date=event.event_date,
            metadata_key=event.metadata_key,
            metadata_value=event.metadata_value,
            created_at=event.created_at,
        ))

    return PurchasingEventListResponse(items=items, total=total)


@router.post("/{po_id}/events", response_model=PurchasingEventResponse, status_code=201)
async def add_po_event(
    po_id: int,
    request: PurchasingEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a manual event to a purchase order (typically a note)

    This endpoint is for adding notes or manual tracking entries.
    Status changes and receipts are automatically recorded by their
    respective endpoints.
    """
    # Verify PO exists
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    event = record_purchasing_event(
        db=db,
        purchase_order_id=po_id,
        event_type=request.event_type.value,
        title=request.title,
        description=request.description,
        old_value=request.old_value,
        new_value=request.new_value,
        event_date=request.event_date,
        user_id=current_user.id,
        metadata_key=request.metadata_key,
        metadata_value=request.metadata_value,
    )
    db.commit()
    db.refresh(event)

    user_name = current_user.full_name

    logger.info(f"Added event '{request.event_type.value}' to PO {po.po_number}")

    return PurchasingEventResponse(
        id=event.id,
        purchase_order_id=event.purchase_order_id,
        user_id=event.user_id,
        user_name=user_name,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        old_value=event.old_value,
        new_value=event.new_value,
        event_date=event.event_date,
        metadata_key=event.metadata_key,
        metadata_value=event.metadata_value,
        created_at=event.created_at,
    )

