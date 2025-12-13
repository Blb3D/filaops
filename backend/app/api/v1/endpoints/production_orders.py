"""
Production Orders API Endpoints

Manufacturing Orders (MOs) for tracking production of finished goods.
Supports creation from sales orders, manual entry, and MRP planning.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, case
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models import (
    User,
    ProductionOrder,
    ProductionOrderOperation,
    Product,
    BOM,
    SalesOrder,
)
from app.models.manufacturing import Routing, RoutingOperation, WorkCenter, Resource
from app.services.inventory_service import process_production_completion
from app.schemas.production_order import (
    ProductionOrderCreate,
    ProductionOrderUpdate,
    ProductionOrderResponse,
    ProductionOrderListResponse,
    ProductionOrderOperationUpdate,
    ProductionOrderOperationResponse,
    WorkCenterQueue,
    ProductionScheduleSummary,
    ProductionOrderSplitRequest,
    ProductionOrderSplitResponse,
)

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

def generate_production_order_code(db: Session) -> str:
    """Generate sequential production order code: PO-YYYY-NNN"""
    year = datetime.utcnow().year
    last = (
        db.query(ProductionOrder)
        .filter(ProductionOrder.code.like(f"PO-{year}-%"))
        .order_by(desc(ProductionOrder.code))
        .first()
    )
    if last:
        try:
            last_num = int(last.code.split("-")[2])
            next_num = last_num + 1
        except (IndexError, ValueError):
            next_num = 1
    else:
        next_num = 1
    return f"PO-{year}-{next_num:04d}"


def build_production_order_response(order: ProductionOrder, db: Session) -> ProductionOrderResponse:
    """Build full response with related data"""
    product = db.query(Product).filter(Product.id == order.product_id).first()
    bom = db.query(BOM).filter(BOM.id == order.bom_id).first() if order.bom_id else None
    routing = db.query(Routing).filter(Routing.id == order.routing_id).first() if order.routing_id else None
    sales_order = db.query(SalesOrder).filter(SalesOrder.id == order.sales_order_id).first() if order.sales_order_id else None

    qty_ordered = float(order.quantity_ordered or 0)
    qty_completed = float(order.quantity_completed or 0)
    qty_remaining = max(0, qty_ordered - qty_completed)
    completion_pct = (qty_completed / qty_ordered * 100) if qty_ordered > 0 else 0

    # Build operations list
    operations_response = []
    if order.operations:
        for op in sorted(order.operations, key=lambda x: x.sequence):
            wc = db.query(WorkCenter).filter(WorkCenter.id == op.work_center_id).first()
            res = db.query(Resource).filter(Resource.id == op.resource_id).first() if op.resource_id else None

            operations_response.append(
                ProductionOrderOperationResponse(
                    id=op.id,
                    production_order_id=op.production_order_id,
                    routing_operation_id=op.routing_operation_id,
                    work_center_id=op.work_center_id,
                    work_center_code=wc.code if wc else None,
                    work_center_name=wc.name if wc else None,
                    resource_id=op.resource_id,
                    resource_code=res.code if res else None,
                    resource_name=res.name if res else None,
                    sequence=op.sequence,
                    operation_code=op.operation_code,
                    operation_name=op.operation_name,
                    status=op.status or "pending",
                    quantity_completed=op.quantity_completed or 0,
                    quantity_scrapped=op.quantity_scrapped or 0,
                    planned_setup_minutes=op.planned_setup_minutes or 0,
                    planned_run_minutes=op.planned_run_minutes or 0,
                    actual_setup_minutes=op.actual_setup_minutes,
                    actual_run_minutes=op.actual_run_minutes,
                    scheduled_start=op.scheduled_start,
                    scheduled_end=op.scheduled_end,
                    actual_start=op.actual_start,
                    actual_end=op.actual_end,
                    bambu_task_id=op.bambu_task_id,
                    bambu_plate_index=op.bambu_plate_index,
                    operator_name=op.operator_name,
                    notes=op.notes,
                    is_complete=op.status == "complete",
                    is_running=op.status == "running",
                    efficiency_percent=None,
                    created_at=op.created_at,
                    updated_at=op.updated_at,
                )
            )

    return ProductionOrderResponse(
        id=order.id,
        code=order.code,
        product_id=order.product_id,
        product_sku=product.sku if product else None,
        product_name=product.name if product else None,
        bom_id=order.bom_id,
        bom_code=bom.code if bom else None,
        routing_id=order.routing_id,
        routing_code=routing.code if routing else None,
        sales_order_id=order.sales_order_id,
        sales_order_code=sales_order.order_number if sales_order else None,
        sales_order_line_id=order.sales_order_line_id,
        quantity_ordered=order.quantity_ordered,
        quantity_completed=order.quantity_completed or 0,
        quantity_scrapped=order.quantity_scrapped or 0,
        quantity_remaining=qty_remaining,
        completion_percent=round(completion_pct, 1),
        source=order.source or "manual",
        status=order.status or "draft",
        priority=order.priority or 3,
        due_date=order.due_date,
        scheduled_start=order.scheduled_start,
        scheduled_end=order.scheduled_end,
        actual_start=order.actual_start,
        actual_end=order.actual_end,
        estimated_time_minutes=order.estimated_time_minutes,
        actual_time_minutes=order.actual_time_minutes,
        estimated_material_cost=order.estimated_material_cost,
        estimated_labor_cost=order.estimated_labor_cost,
        estimated_total_cost=order.estimated_total_cost,
        actual_material_cost=order.actual_material_cost,
        actual_labor_cost=order.actual_labor_cost,
        actual_total_cost=order.actual_total_cost,
        assigned_to=order.assigned_to,
        notes=order.notes,
        operations=operations_response,
        created_at=order.created_at,
        updated_at=order.updated_at,
        created_by=order.created_by,
        released_at=order.released_at,
        completed_at=order.completed_at,
    )


def copy_routing_to_operations(db: Session, order: ProductionOrder, routing_id: int) -> List[ProductionOrderOperation]:
    """Copy routing operations to production order operations"""
    routing_ops = (
        db.query(RoutingOperation)
        .filter(RoutingOperation.routing_id == routing_id)
        .order_by(RoutingOperation.sequence)
        .all()
    )

    operations = []
    for rop in routing_ops:
        op = ProductionOrderOperation(
            production_order_id=order.id,
            routing_operation_id=rop.id,
            work_center_id=rop.work_center_id,
            resource_id=None,  # Resource assigned during scheduling
            sequence=rop.sequence,
            operation_code=rop.operation_code,
            operation_name=rop.operation_name,
            planned_setup_minutes=rop.setup_time_minutes or 0,
            planned_run_minutes=(rop.run_time_minutes or 0) * float(order.quantity_ordered),
            status="pending",
        )
        db.add(op)
        operations.append(op)

    return operations


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("/", response_model=List[ProductionOrderListResponse])
async def list_production_orders(
    status: Optional[str] = Query(None),
    product_id: Optional[int] = Query(None),
    sales_order_id: Optional[int] = Query(None),
    priority: Optional[int] = Query(None, ge=1, le=5),
    due_before: Optional[date] = Query(None),
    due_after: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List production orders with filtering"""
    query = db.query(ProductionOrder)

    if status:
        query = query.filter(ProductionOrder.status == status)
    if product_id:
        query = query.filter(ProductionOrder.product_id == product_id)
    if sales_order_id:
        query = query.filter(ProductionOrder.sales_order_id == sales_order_id)
    if priority:
        query = query.filter(ProductionOrder.priority == priority)
    if due_before:
        query = query.filter(ProductionOrder.due_date <= due_before)
    if due_after:
        query = query.filter(ProductionOrder.due_date >= due_after)
    if search:
        search_term = f"%{search}%"
        query = query.join(Product, ProductionOrder.product_id == Product.id).filter(
            or_(
                ProductionOrder.code.ilike(search_term),
                Product.sku.ilike(search_term),
                Product.name.ilike(search_term),
            )
        )

    # SQL Server doesn't support NULLS LAST, so use CASE expression
    query = query.order_by(
        ProductionOrder.priority.asc(),
        case((ProductionOrder.due_date.is_(None), 1), else_=0),  # NULLs last
        ProductionOrder.due_date.asc(),
        ProductionOrder.created_at.desc(),
    )

    orders = query.offset(skip).limit(limit).all()

    result = []
    for order in orders:
        product = db.query(Product).filter(Product.id == order.product_id).first()
        sales_order = db.query(SalesOrder).filter(SalesOrder.id == order.sales_order_id).first() if order.sales_order_id else None

        op_count = db.query(ProductionOrderOperation).filter(ProductionOrderOperation.production_order_id == order.id).count()
        current_op = (
            db.query(ProductionOrderOperation)
            .filter(
                ProductionOrderOperation.production_order_id == order.id,
                ProductionOrderOperation.status.in_(["running", "queued", "pending"]),
            )
            .order_by(ProductionOrderOperation.sequence)
            .first()
        )

        qty_ordered = float(order.quantity_ordered or 0)
        qty_completed = float(order.quantity_completed or 0)
        qty_remaining = max(0, qty_ordered - qty_completed)
        completion_pct = (qty_completed / qty_ordered * 100) if qty_ordered > 0 else 0

        result.append(
            ProductionOrderListResponse(
                id=order.id,
                code=order.code,
                product_id=order.product_id,
                product_sku=product.sku if product else None,
                product_name=product.name if product else None,
                quantity_ordered=order.quantity_ordered,
                quantity_completed=order.quantity_completed or 0,
                quantity_remaining=qty_remaining,
                completion_percent=round(completion_pct, 1),
                status=order.status or "draft",
                priority=order.priority or 3,
                source=order.source or "manual",
                due_date=order.due_date,
                scheduled_start=order.scheduled_start,
                scheduled_end=order.scheduled_end,
                sales_order_id=order.sales_order_id,
                sales_order_code=sales_order.order_number if sales_order else None,
                assigned_to=order.assigned_to,
                operation_count=op_count,
                current_operation=current_op.operation_name if current_op else None,
                created_at=order.created_at,
            )
        )

    return result


@router.post("/", response_model=ProductionOrderResponse)
async def create_production_order(
    request: ProductionOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new production order"""
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Find default BOM if not specified
    bom_id = request.bom_id
    if not bom_id:
        default_bom = db.query(BOM).filter(BOM.product_id == request.product_id, BOM.active== True).first()
        if default_bom:
            bom_id = default_bom.id

    # Find default routing if not specified
    routing_id = request.routing_id
    if not routing_id:
        default_routing = db.query(Routing).filter(Routing.product_id == request.product_id, Routing.is_active== True).first()
        if default_routing:
            routing_id = default_routing.id

    code = generate_production_order_code(db)

    order = ProductionOrder(
        code=code,
        product_id=request.product_id,
        bom_id=bom_id,
        routing_id=routing_id,
        sales_order_id=request.sales_order_id,
        sales_order_line_id=request.sales_order_line_id,
        quantity_ordered=request.quantity_ordered,
        quantity_completed=0,
        quantity_scrapped=0,
        source=request.source.value if request.source else "manual",
        status="draft",
        priority=request.priority or 3,
        due_date=request.due_date,
        assigned_to=request.assigned_to,
        notes=request.notes,
        created_by=current_user.email,
    )
    db.add(order)
    db.flush()

    if routing_id:
        copy_routing_to_operations(db, order, routing_id)

    db.commit()
    db.refresh(order)

    return build_production_order_response(order, db)


@router.get("/{order_id}", response_model=ProductionOrderResponse)
async def get_production_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single production order with full details"""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    return build_production_order_response(order, db)


@router.put("/{order_id}", response_model=ProductionOrderResponse)
async def update_production_order(
    order_id: int,
    request: ProductionOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a production order"""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    if order.status in ("complete", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot update {order.status} production order")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(order, field):
            setattr(order, field, value)

    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    return build_production_order_response(order, db)


@router.delete("/{order_id}")
async def delete_production_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a draft production order"""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    if order.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft orders can be deleted")

    db.query(ProductionOrderOperation).filter(ProductionOrderOperation.production_order_id == order_id).delete()
    db.delete(order)
    db.commit()

    return {"message": "Production order deleted"}


# ============================================================================
# Status Transitions
# ============================================================================

@router.post("/{order_id}/release", response_model=ProductionOrderResponse)
async def release_production_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Release a draft order for production"""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    if order.status != "draft":
        raise HTTPException(status_code=400, detail=f"Cannot release order in {order.status} status")

    order.status = "released"
    order.released_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    first_op = db.query(ProductionOrderOperation).filter(ProductionOrderOperation.production_order_id == order_id).order_by(ProductionOrderOperation.sequence).first()
    if first_op:
        first_op.status = "queued"

    db.commit()
    db.refresh(order)

    return build_production_order_response(order, db)


@router.post("/{order_id}/start", response_model=ProductionOrderResponse)
async def start_production_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start production on an order"""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    if order.status not in ("released", "on_hold"):
        raise HTTPException(status_code=400, detail=f"Cannot start order in {order.status} status")

    order.status = "in_progress"
    if not order.actual_start:
        order.actual_start = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return build_production_order_response(order, db)


@router.post("/{order_id}/complete", response_model=ProductionOrderResponse)
async def complete_production_order(
    order_id: int,
    quantity_completed: Optional[Decimal] = Query(None),
    quantity_scrapped: Optional[Decimal] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete a production order"""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    if order.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Cannot complete order in {order.status} status")

    # Default quantity_completed to quantity_ordered if not provided
    if quantity_completed is not None:
        order.quantity_completed = quantity_completed
    else:
        order.quantity_completed = order.quantity_ordered
    if quantity_scrapped is not None:
        order.quantity_scrapped = quantity_scrapped

    order.status = "complete"
    order.actual_end = datetime.utcnow()
    order.completed_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    if order.actual_start:
        delta = order.actual_end - order.actual_start
        order.actual_time_minutes = int(delta.total_seconds() / 60)

    db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.production_order_id == order_id,
        ProductionOrderOperation.status != "complete",
    ).update({"status": "complete"})

    # Auto-generate serial numbers if product requires serial tracking
    product = db.query(Product).filter(Product.id == order.product_id).first()
    if product and product.track_serials:
        from app.models.traceability import SerialNumber

        qty_to_serial = int(order.quantity_completed or order.quantity_ordered)
        today = datetime.utcnow()
        date_str = today.strftime("%Y%m%d")
        prefix = f"BLB-{date_str}-"

        # Find highest existing sequence for today
        last_serial = db.query(SerialNumber).filter(
            SerialNumber.serial_number.like(f"{prefix}%")
        ).order_by(desc(SerialNumber.serial_number)).first()

        seq = 0
        if last_serial:
            try:
                seq = int(last_serial.serial_number.replace(prefix, ""))
            except ValueError:
                pass

        for _ in range(qty_to_serial):
            seq += 1
            serial = SerialNumber(
                serial_number=f"{prefix}{seq:04d}",
                product_id=order.product_id,
                production_order_id=order.id,
                status='manufactured',
                qc_passed=True,
                manufactured_at=today,
            )
            db.add(serial)

    # Process inventory transactions:
    # 1. Consume raw materials based on BOM (production stage items)
    # 2. Add finished goods to inventory
    qty_completed = order.quantity_completed or order.quantity_ordered
    process_production_completion(
        db=db,
        production_order=order,
        quantity_completed=qty_completed,
        created_by=current_user.email if current_user else None,
    )

    # Update linked sales order status to ready_to_ship if all production is complete
    if order.sales_order_id:
        sales_order = db.query(SalesOrder).filter(SalesOrder.id == order.sales_order_id).first()
        if sales_order and sales_order.status == "in_production":
            # Check if ALL production orders for this sales order are complete
            incomplete_production = db.query(ProductionOrder).filter(
                ProductionOrder.sales_order_id == order.sales_order_id,
                ProductionOrder.status.notin_(["complete", "cancelled"]),
            ).count()

            if incomplete_production == 0:
                sales_order.status = "ready_to_ship"
                sales_order.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return build_production_order_response(order, db)


@router.post("/{order_id}/cancel", response_model=ProductionOrderResponse)
async def cancel_production_order(
    order_id: int,
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a production order"""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    if order.status == "complete":
        raise HTTPException(status_code=400, detail="Cannot cancel completed order")

    order.status = "cancelled"
    if notes:
        order.notes = (order.notes or "") + f"\n[Cancelled: {notes}]"
    order.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return build_production_order_response(order, db)


@router.post("/{order_id}/hold", response_model=ProductionOrderResponse)
async def hold_production_order(
    order_id: int,
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Put a production order on hold"""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    if order.status in ("complete", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot hold {order.status} order")

    order.status = "on_hold"
    if notes:
        order.notes = (order.notes or "") + f"\n[On Hold: {notes}]"
    order.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return build_production_order_response(order, db)


# ============================================================================
# Split Order
# ============================================================================

@router.post("/{order_id}/split", response_model=ProductionOrderSplitResponse)
async def split_production_order(
    order_id: int,
    request: ProductionOrderSplitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Split a production order into multiple child orders.

    Use case: Large runs that need to be split across multiple machines.
    Each child order gets a portion of the quantity and its own operations.

    Requirements:
    - Order must be in 'released' status (not yet started)
    - Split quantities must sum to original quantity
    - Creates child orders with codes like PO-2025-0001-A, PO-2025-0001-B
    """
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    # Validate order can be split
    if order.status != "released":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot split order in '{order.status}' status. Order must be 'released'."
        )

    if order.parent_order_id:
        raise HTTPException(status_code=400, detail="Cannot split an order that is already a child of another order")

    if order.child_orders and len(order.child_orders) > 0:
        raise HTTPException(status_code=400, detail="This order has already been split")

    # Validate split quantities sum to original
    total_split_qty = sum(s.quantity for s in request.splits)
    original_qty = int(order.quantity_ordered)

    if total_split_qty != original_qty:
        raise HTTPException(
            status_code=400,
            detail=f"Split quantities ({total_split_qty}) must equal original quantity ({original_qty})"
        )

    # Create child orders
    child_orders = []
    suffix_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for idx, split in enumerate(request.splits):
        suffix = suffix_chars[idx] if idx < 26 else str(idx + 1)
        child_code = f"{order.code}-{suffix}"

        # Create child order
        child = ProductionOrder(
            code=child_code,
            product_id=order.product_id,
            bom_id=order.bom_id,
            routing_id=order.routing_id,
            sales_order_id=order.sales_order_id,
            sales_order_line_id=order.sales_order_line_id,
            parent_order_id=order.id,
            split_sequence=idx + 1,
            quantity_ordered=Decimal(str(split.quantity)),
            quantity_completed=0,
            quantity_scrapped=0,
            source=order.source,
            status="released",  # Child orders are already released
            priority=order.priority,
            due_date=order.due_date,
            assigned_to=order.assigned_to,
            notes=f"Split from {order.code} (part {idx + 1} of {len(request.splits)})",
            created_by=current_user.email,
            released_at=datetime.utcnow(),
        )
        db.add(child)
        db.flush()  # Get the child ID

        # Copy operations from parent, scaling run times proportionally
        if order.routing_id:
            routing_ops = (
                db.query(RoutingOperation)
                .filter(RoutingOperation.routing_id == order.routing_id)
                .order_by(RoutingOperation.sequence)
                .all()
            )

            for rop in routing_ops:
                # Scale run time based on quantity ratio
                base_run_time = float(rop.run_time_minutes or 0)
                scaled_run_time = base_run_time * split.quantity

                op = ProductionOrderOperation(
                    production_order_id=child.id,
                    routing_operation_id=rop.id,
                    work_center_id=rop.work_center_id,
                    resource_id=None,  # Resource assigned during scheduling
                    sequence=rop.sequence,
                    operation_code=rop.operation_code,
                    operation_name=rop.operation_name,
                    planned_setup_minutes=rop.setup_time_minutes or 0,
                    planned_run_minutes=Decimal(str(scaled_run_time)),
                    status="queued" if rop.sequence == 1 else "pending",
                )
                db.add(op)

        child_orders.append(child)

    # Update parent order status to indicate it was split
    order.status = "split"
    order.notes = (order.notes or "") + f"\n[Split into {len(request.splits)} orders on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}]"
    order.updated_at = datetime.utcnow()

    db.commit()

    # Build response
    child_responses = []
    for child in child_orders:
        db.refresh(child)
        product = db.query(Product).filter(Product.id == child.product_id).first()
        sales_order = db.query(SalesOrder).filter(SalesOrder.id == child.sales_order_id).first() if child.sales_order_id else None

        op_count = db.query(ProductionOrderOperation).filter(
            ProductionOrderOperation.production_order_id == child.id
        ).count()

        child_responses.append(
            ProductionOrderListResponse(
                id=child.id,
                code=child.code,
                product_id=child.product_id,
                product_sku=product.sku if product else None,
                product_name=product.name if product else None,
                quantity_ordered=child.quantity_ordered,
                quantity_completed=child.quantity_completed or 0,
                quantity_remaining=float(child.quantity_ordered),
                completion_percent=0,
                status=child.status,
                priority=child.priority or 3,
                source=child.source or "manual",
                due_date=child.due_date,
                scheduled_start=child.scheduled_start,
                scheduled_end=child.scheduled_end,
                sales_order_id=child.sales_order_id,
                sales_order_code=sales_order.order_number if sales_order else None,
                assigned_to=child.assigned_to,
                operation_count=op_count,
                current_operation=None,
                created_at=child.created_at,
            )
        )

    return ProductionOrderSplitResponse(
        parent_order_id=order.id,
        parent_order_code=order.code,
        parent_status="split",
        child_orders=child_responses,
        message=f"Successfully split {order.code} into {len(child_orders)} orders"
    )


# ============================================================================
# Operation Management
# ============================================================================

@router.put("/{order_id}/operations/{operation_id}", response_model=ProductionOrderOperationResponse)
async def update_operation(
    order_id: int,
    operation_id: int,
    request: ProductionOrderOperationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an operation"""
    op = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.id == operation_id,
        ProductionOrderOperation.production_order_id == order_id,
    ).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(op, field):
            if field == "status" and value:
                value = value.value if hasattr(value, "value") else value
            setattr(op, field, value)

    op.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(op)

    wc = db.query(WorkCenter).filter(WorkCenter.id == op.work_center_id).first()
    res = db.query(Resource).filter(Resource.id == op.resource_id).first() if op.resource_id else None

    return ProductionOrderOperationResponse(
        id=op.id,
        production_order_id=op.production_order_id,
        routing_operation_id=op.routing_operation_id,
        work_center_id=op.work_center_id,
        work_center_code=wc.code if wc else None,
        work_center_name=wc.name if wc else None,
        resource_id=op.resource_id,
        resource_code=res.code if res else None,
        resource_name=res.name if res else None,
        sequence=op.sequence,
        operation_code=op.operation_code,
        operation_name=op.operation_name,
        status=op.status or "pending",
        quantity_completed=op.quantity_completed or 0,
        quantity_scrapped=op.quantity_scrapped or 0,
        planned_setup_minutes=op.planned_setup_minutes or 0,
        planned_run_minutes=op.planned_run_minutes or 0,
        actual_setup_minutes=op.actual_setup_minutes,
        actual_run_minutes=op.actual_run_minutes,
        scheduled_start=op.scheduled_start,
        scheduled_end=op.scheduled_end,
        actual_start=op.actual_start,
        actual_end=op.actual_end,
        bambu_task_id=op.bambu_task_id,
        bambu_plate_index=op.bambu_plate_index,
        operator_name=op.operator_name,
        notes=op.notes,
        is_complete=op.status == "complete",
        is_running=op.status == "running",
        efficiency_percent=None,
        created_at=op.created_at,
        updated_at=op.updated_at,
    )


@router.post("/{order_id}/operations/{operation_id}/start")
async def start_operation(
    order_id: int,
    operation_id: int,
    resource_id: Optional[int] = Query(None),
    operator_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start an operation"""
    op = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.id == operation_id,
        ProductionOrderOperation.production_order_id == order_id,
    ).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")

    if op.status not in ("pending", "queued"):
        raise HTTPException(status_code=400, detail=f"Cannot start operation in {op.status} status")

    op.status = "running"
    op.actual_start = datetime.utcnow()
    if resource_id:
        op.resource_id = resource_id
    if operator_name:
        op.operator_name = operator_name
    op.updated_at = datetime.utcnow()

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if order and order.status == "released":
        order.status = "in_progress"
        if not order.actual_start:
            order.actual_start = datetime.utcnow()

    db.commit()

    return {"message": "Operation started", "operation_id": operation_id}


@router.post("/{order_id}/operations/{operation_id}/complete")
async def complete_operation(
    order_id: int,
    operation_id: int,
    quantity_completed: Decimal = Query(...),
    quantity_scrapped: Optional[Decimal] = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete an operation and queue the next one"""
    op = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.id == operation_id,
        ProductionOrderOperation.production_order_id == order_id,
    ).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")

    op.status = "complete"
    op.actual_end = datetime.utcnow()
    op.quantity_completed = quantity_completed
    op.quantity_scrapped = quantity_scrapped or 0

    if op.actual_start:
        delta = op.actual_end - op.actual_start
        op.actual_run_minutes = Decimal(str(delta.total_seconds() / 60))

    op.updated_at = datetime.utcnow()

    next_op = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.production_order_id == order_id,
        ProductionOrderOperation.sequence > op.sequence,
        ProductionOrderOperation.status == "pending",
    ).order_by(ProductionOrderOperation.sequence).first()

    if next_op:
        next_op.status = "queued"

    if not next_op:
        order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
        if order:
            order.quantity_completed = (order.quantity_completed or 0) + quantity_completed
            order.quantity_scrapped = (order.quantity_scrapped or 0) + (quantity_scrapped or 0)

    db.commit()

    return {
        "message": "Operation completed",
        "operation_id": operation_id,
        "next_operation_queued": next_op.id if next_op else None,
    }


# ============================================================================
# Schedule & Queue Views
# ============================================================================

@router.get("/schedule/summary", response_model=ProductionScheduleSummary)
async def get_schedule_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get production schedule summary stats"""
    today = date.today()

    status_counts = db.query(ProductionOrder.status, func.count(ProductionOrder.id)).filter(
        ProductionOrder.status.notin_(["cancelled"])
    ).group_by(ProductionOrder.status).all()
    orders_by_status = {status: count for status, count in status_counts}

    due_today = db.query(func.count(ProductionOrder.id)).filter(
        ProductionOrder.due_date == today,
        ProductionOrder.status.notin_(["complete", "cancelled"]),
    ).scalar() or 0

    overdue = db.query(func.count(ProductionOrder.id)).filter(
        ProductionOrder.due_date < today,
        ProductionOrder.status.notin_(["complete", "cancelled"]),
    ).scalar() or 0

    in_progress = orders_by_status.get("in_progress", 0)

    total_qty = db.query(func.sum(ProductionOrder.quantity_ordered - ProductionOrder.quantity_completed)).filter(
        ProductionOrder.status.notin_(["complete", "cancelled"])
    ).scalar() or 0

    total_orders = sum(orders_by_status.values())

    return ProductionScheduleSummary(
        total_orders=total_orders,
        orders_by_status=orders_by_status,
        orders_due_today=due_today,
        orders_overdue=overdue,
        orders_in_progress=in_progress,
        total_quantity_to_produce=float(total_qty),
    )


@router.get("/queue/by-work-center", response_model=List[WorkCenterQueue])
async def get_queue_by_work_center(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get operations queued at each work center"""
    work_centers = db.query(WorkCenter).filter(WorkCenter.active== True).all()

    result = []
    for wc in work_centers:
        queued_ops = db.query(ProductionOrderOperation).join(ProductionOrder).filter(
            ProductionOrderOperation.work_center_id == wc.id,
            ProductionOrderOperation.status == "queued",
            ProductionOrder.status.in_(["released", "in_progress"]),
        ).order_by(ProductionOrder.priority, ProductionOrder.due_date).all()

        running_ops = db.query(ProductionOrderOperation).filter(
            ProductionOrderOperation.work_center_id == wc.id,
            ProductionOrderOperation.status == "running",
        ).all()

        def build_op_response(op, is_running=False):
            res = db.query(Resource).filter(Resource.id == op.resource_id).first() if op.resource_id else None
            return ProductionOrderOperationResponse(
                id=op.id,
                production_order_id=op.production_order_id,
                routing_operation_id=op.routing_operation_id,
                work_center_id=op.work_center_id,
                work_center_code=wc.code,
                work_center_name=wc.name,
                resource_id=op.resource_id,
                resource_code=res.code if res else None,
                resource_name=res.name if res else None,
                sequence=op.sequence,
                operation_code=op.operation_code,
                operation_name=op.operation_name,
                status=op.status or "pending",
                quantity_completed=op.quantity_completed or 0,
                quantity_scrapped=op.quantity_scrapped or 0,
                planned_setup_minutes=op.planned_setup_minutes or 0,
                planned_run_minutes=op.planned_run_minutes or 0,
                actual_setup_minutes=op.actual_setup_minutes,
                actual_run_minutes=op.actual_run_minutes,
                scheduled_start=op.scheduled_start,
                scheduled_end=op.scheduled_end,
                actual_start=op.actual_start,
                actual_end=op.actual_end,
                bambu_task_id=op.bambu_task_id,
                bambu_plate_index=op.bambu_plate_index,
                operator_name=op.operator_name,
                notes=op.notes,
                is_complete=False,
                is_running=is_running,
                efficiency_percent=None,
                created_at=op.created_at,
                updated_at=op.updated_at,
            )

        total_minutes = sum(float(op.planned_run_minutes or 0) for op in queued_ops)

        result.append(WorkCenterQueue(
            work_center_id=wc.id,
            work_center_code=wc.code,
            work_center_name=wc.name,
            queued_operations=[build_op_response(op) for op in queued_ops],
            running_operations=[build_op_response(op, True) for op in running_ops],
            total_queued_minutes=total_minutes,
        ))

    return result
