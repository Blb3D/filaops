"""
Purchase Orders API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.db.session import get_db
from app.logging_config import get_logger
from app.services.google_drive import get_drive_service
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.product import Product
from app.models.inventory import Inventory, InventoryTransaction
from app.api.v1.endpoints.auth import get_current_user
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

router = APIRouter()
logger = get_logger(__name__)


def _generate_po_number(db: Session) -> str:
    """Generate next PO number (PO-2025-001, PO-2025-002, etc.)"""
    year = datetime.utcnow().year
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

@router.get("/", response_model=List[PurchaseOrderListResponse])
async def list_purchase_orders(
    status: Optional[str] = None,
    vendor_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List purchase orders

    - **status**: Filter by status (draft, ordered, shipped, received, closed, cancelled)
    - **vendor_id**: Filter by vendor
    - **search**: Search by PO number
    """
    query = db.query(PurchaseOrder).options(joinedload(PurchaseOrder.vendor))

    if status:
        query = query.filter(PurchaseOrder.status == status)

    if vendor_id:
        query = query.filter(PurchaseOrder.vendor_id == vendor_id)

    if search:
        query = query.filter(PurchaseOrder.po_number.ilike(f"%{search}%"))

    pos = query.order_by(desc(PurchaseOrder.created_at)).offset(skip).limit(limit).all()

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
            total_amount=po.total_amount,
            line_count=len(po.lines),
            created_at=po.created_at,
        ))

    return result


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: int,
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
            quantity_ordered=line.quantity_ordered,
            quantity_received=line.quantity_received,
            unit_cost=line.unit_cost,
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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
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
            unit_cost=line_data.unit_cost,
            line_total=line_data.quantity_ordered * line_data.unit_cost,
            notes=line_data.notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(line)
        po.lines.append(line)

    # Calculate totals
    _calculate_totals(po)

    db.commit()
    db.refresh(po)

    logger.info(f"Created PO {po.po_number} for vendor {vendor.name}")

    # Return full response
    return await get_purchase_order(po.id, db)


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

    po.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(po)

    logger.info(f"Updated PO {po.po_number}")
    return await get_purchase_order(po.id, db)


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
        unit_cost=request.unit_cost,
        line_total=request.quantity_ordered * request.unit_cost,
        notes=request.notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(line)

    # Recalculate totals
    po.lines.append(line)
    _calculate_totals(po)
    po.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(po)

    return await get_purchase_order(po.id, db)


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
    line.updated_at = datetime.utcnow()

    # Recalculate PO totals
    _calculate_totals(po)
    po.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(po)

    logger.info(f"Updated line {line_id} on PO {po.po_number}")
    return await get_purchase_order(po.id, db)


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
    po.updated_at = datetime.utcnow()

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
    po.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(po)

    logger.info(f"PO {po.po_number} status: {old_status} -> {new_status}")
    return await get_purchase_order(po.id, db)


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

    # Default location (get first warehouse or create default)
    location_id = request.location_id
    if not location_id:
        from app.models.inventory import InventoryLocation
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
    total_received = Decimal("0")
    lines_received = 0

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
        line.updated_at = datetime.utcnow()
        total_received += item.quantity_received
        lines_received += 1

        # Update inventory
        inventory = db.query(Inventory).filter(
            Inventory.product_id == line.product_id,
            Inventory.location_id == location_id
        ).first()

        if inventory:
            inventory.on_hand_quantity = inventory.on_hand_quantity + item.quantity_received
            inventory.updated_at = datetime.utcnow()
        else:
            inventory = Inventory(
                product_id=line.product_id,
                location_id=location_id,
                on_hand_quantity=item.quantity_received,
                allocated_quantity=Decimal("0"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(inventory)

        # Create inventory transaction
        txn = InventoryTransaction(
            product_id=line.product_id,
            location_id=location_id,
            transaction_type="receipt",
            reference_type="purchase_order",
            reference_id=po.id,
            quantity=item.quantity_received,
            lot_number=item.lot_number,
            cost_per_unit=line.unit_cost,
            notes=item.notes or f"Received from PO {po.po_number}",
            created_at=datetime.utcnow(),
            created_by=current_user.email,
        )
        db.add(txn)
        db.flush()
        transaction_ids.append(txn.id)

        # Update product average cost
        product = db.query(Product).filter(Product.id == line.product_id).first()
        if product:
            # Simple weighted average update
            if product.average_cost is None or product.average_cost == 0:
                product.average_cost = line.unit_cost
            else:
                # Rough weighted average (simplified)
                product.average_cost = (product.average_cost + line.unit_cost) / 2
            product.last_cost = line.unit_cost
            product.updated_at = datetime.utcnow()

    # Check if fully received
    all_received = all(
        line.quantity_received >= line.quantity_ordered
        for line in po.lines
    )

    if all_received:
        po.status = "received"
        po.received_date = date.today()

    po.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Received {total_received} items on PO {po.po_number}")

    return ReceivePOResponse(
        po_number=po.po_number,
        lines_received=lines_received,
        total_quantity=total_received,
        inventory_updated=True,
        transactions_created=transaction_ids,
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
    safe_filename = f"{po.po_number}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"

    # Try Google Drive first
    drive_service = get_drive_service()
    if drive_service.enabled:
        success, result = drive_service.upload_bytes(
            file_bytes=file_content,
            filename=safe_filename,
            mime_type=content_type,
            subfolder="Purchase Orders"
        )

        if success:
            # Save URL to PO
            po.document_url = result
            po.updated_at = datetime.utcnow()
            db.commit()

            return {
                "success": True,
                "storage": "google_drive",
                "url": result,
                "filename": safe_filename,
            }
        else:
            logger.warning(f"Google Drive upload failed: {result}, falling back to local")

    # Fallback: Save locally
    upload_dir = os.path.join("uploads", "purchase_orders")
    os.makedirs(upload_dir, exist_ok=True)

    local_path = os.path.join(upload_dir, safe_filename)
    with open(local_path, "wb") as f:
        f.write(file_content)

    # For local files, we'll store a relative path
    # The frontend can construct the full URL or a download endpoint can serve it
    po.document_url = f"/uploads/purchase_orders/{safe_filename}"
    po.updated_at = datetime.utcnow()
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
