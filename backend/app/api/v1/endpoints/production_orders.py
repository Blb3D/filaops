"""
Production Orders API Endpoints

Manufacturing Orders (MOs) for tracking production of finished goods.
Supports creation from sales orders, manual entry, and MRP planning.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, case

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models import (
    User,
    ProductionOrder,
    ProductionOrderOperation,
    Product,
    BOM,
    SalesOrder,
    ScrapReason,
)
from app.models.bom import BOMLine
from app.models.inventory import Inventory
from app.models.manufacturing import Routing, RoutingOperation, WorkCenter, Resource
from app.services.inventory_service import process_production_completion
from app.services.uom_service import UOMConversionError
from app.schemas.production_order import (
    ProductionOrderCreate,
    ProductionOrderUpdate,
    ProductionOrderResponse,
    ProductionOrderScrapResponse,
    ProductionOrderListResponse,
    ProductionOrderOperationUpdate,
    ProductionOrderOperationResponse,
    WorkCenterQueue,
    ProductionScheduleSummary,
    ProductionOrderSplitRequest,
    ProductionOrderSplitResponse,
    ScrapReasonCreate,
    ScrapReasonDetail,
    ScrapReasonUpdate,
    ScrapReasonsResponse,
)

logger = logging.getLogger(__name__)

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
    bom = db.query(BOM).filter(BOM.id == order.bom_id).first() if order.bom_id is not None else None
    routing = db.query(Routing).filter(Routing.id == order.routing_id).first() if order.routing_id is not None else None
    sales_order = db.query(SalesOrder).filter(SalesOrder.id == order.sales_order_id).first() if order.sales_order_id is not None else None

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
                    quantity_completed=op.quantity_completed or Decimal(0),
                    quantity_scrapped=op.quantity_scrapped or Decimal(0),
                    planned_setup_minutes=op.planned_setup_minutes or Decimal(0),
                    planned_run_minutes=op.planned_run_minutes or Decimal(0),
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
        quantity_completed=order.quantity_completed or Decimal(0),  # type: ignore[arg-type]
        quantity_scrapped=order.quantity_scrapped or Decimal(0),  # type: ignore[arg-type]
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
            planned_run_minutes=float(rop.run_time_minutes or 0) * float(order.quantity_ordered),
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
) -> List[ProductionOrderListResponse]:
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
) -> ProductionOrderResponse:
    """Create a new production order"""
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Find default BOM if not specified
    bom_id = request.bom_id
    if not bom_id:
        default_bom = db.query(BOM).filter(BOM.product_id == request.product_id, BOM.active == True).first()  # noqa: E712 - SQL Server requires == True
        if default_bom:
            bom_id = default_bom.id

    # Find default routing if not specified
    routing_id = request.routing_id
    if not routing_id:
        default_routing = db.query(Routing).filter(Routing.product_id == request.product_id, Routing.is_active == True).first()  # noqa: E712 - SQL Server requires == True
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


# ============================================================================
# Scrap Reasons Management
# ============================================================================
# NOTE: These routes MUST be defined BEFORE /{order_id} routes to avoid
# FastAPI treating "scrap-reasons" as an order_id path parameter

@router.get("/scrap-reasons", response_model=ScrapReasonsResponse)
async def get_scrap_reasons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapReasonsResponse:
    """Get list of active scrap reasons from database"""
    reasons = db.query(ScrapReason).filter(
        ScrapReason.active == True  # noqa: E712 - SQL Server requires == True
    ).order_by(ScrapReason.sequence, ScrapReason.name).all()

    return ScrapReasonsResponse(
        reasons=[r.code for r in reasons],
        details=[
            ScrapReasonDetail(
                id=r.id,
                code=r.code,
                name=r.name,
                description=r.description,
                sequence=r.sequence,
            )
            for r in reasons
        ],
        descriptions={r.code: r.description or r.name for r in reasons}
    )


@router.get("/scrap-reasons/all")
async def list_all_scrap_reasons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ScrapReasonDetail]:
    """List all scrap reasons including inactive (for admin management)"""
    reasons = db.query(ScrapReason).order_by(ScrapReason.sequence, ScrapReason.name).all()

    return [
        ScrapReasonDetail(
            id=r.id,
            code=r.code,
            name=r.name,
            description=r.description,
            active=r.active,
            sequence=r.sequence,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in reasons
    ]


@router.post("/scrap-reasons", response_model=ScrapReasonDetail)
async def create_scrap_reason(
    request: ScrapReasonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapReasonDetail:
    """Create a new scrap reason"""
    # Check for duplicate code
    existing = db.query(ScrapReason).filter(ScrapReason.code == request.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Scrap reason with code '{request.code}' already exists")

    reason = ScrapReason(
        code=request.code.lower().replace(" ", "_"),
        name=request.name,
        description=request.description,
        sequence=request.sequence,
        active=True,
    )
    db.add(reason)
    db.commit()
    db.refresh(reason)

    return ScrapReasonDetail(
        id=reason.id,
        code=reason.code,
        name=reason.name,
        description=reason.description,
        sequence=reason.sequence,
    )


@router.put("/scrap-reasons/{reason_id}", response_model=ScrapReasonDetail)
async def update_scrap_reason(
    reason_id: int,
    update_data: ScrapReasonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapReasonDetail:
    """Update an existing scrap reason"""
    reason = db.query(ScrapReason).filter(ScrapReason.id == reason_id).first()
    if not reason:
        raise HTTPException(status_code=404, detail="Scrap reason not found")

    # Apply only non-None fields from the update model
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(reason, field, value)

    reason.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reason)

    return ScrapReasonDetail(
        id=reason.id,
        code=reason.code,
        name=reason.name,
        description=reason.description,
        sequence=reason.sequence,
    )


@router.delete("/scrap-reasons/{reason_id}")
async def delete_scrap_reason(
    reason_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete a scrap reason (soft delete by marking inactive)"""
    reason = db.query(ScrapReason).filter(ScrapReason.id == reason_id).first()
    if not reason:
        raise HTTPException(status_code=404, detail="Scrap reason not found")

    # Soft delete - just mark inactive
    reason.active = False
    reason.updated_at = datetime.utcnow()
    db.commit()

    return {"message": f"Scrap reason '{reason.code}' has been deactivated"}


# ============================================================================
# Order-specific endpoints (/{order_id} routes)
# ============================================================================

@router.get("/{order_id}", response_model=ProductionOrderResponse)
async def get_production_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductionOrderResponse:
    """Get a single production order with full details"""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    return build_production_order_response(order, db)


@router.get("/{order_id}/material-availability")
async def check_material_availability(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Check material availability for a production order.

    Returns list of components with availability status, indicating
    whether each shortage requires a Work Order (make item with BOM)
    or Purchase Order (buy item without BOM).
    """
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    if not order.bom_id:
        return {
            "order_id": order_id,
            "order_code": order.code,
            "can_release": True,
            "components": [],
            "shortages": [],
            "work_orders_needed": [],
            "purchase_orders_needed": []
        }

    bom = db.query(BOM).filter(BOM.id == order.bom_id).first()
    if not bom:
        return {
            "order_id": order_id,
            "order_code": order.code,
            "can_release": True,
            "components": [],
            "shortages": [],
            "work_orders_needed": [],
            "purchase_orders_needed": []
        }

    bom_lines = db.query(BOMLine).filter(BOMLine.bom_id == bom.id).all()

    components = []
    shortages = []
    work_orders_needed = []
    purchase_orders_needed = []

    qty_multiplier = Decimal(str(order.quantity_ordered or 1))

    for line in bom_lines:
        component = db.query(Product).filter(Product.id == line.component_id).first()
        if not component:
            continue

        # Skip cost-only items (overhead, machine time)
        if line.is_cost_only:
            continue

        # Calculate required quantity with scrap factor
        base_qty = Decimal(str(line.quantity or 0))
        scrap_factor = Decimal(str(line.scrap_factor or 0)) / Decimal("100")
        qty_with_scrap = base_qty * (Decimal("1") + scrap_factor)
        required_qty = qty_with_scrap * qty_multiplier

        # Get available inventory across all locations
        inv_result = db.query(
            func.sum(Inventory.available_quantity)
        ).filter(Inventory.product_id == line.component_id).scalar()
        available_qty = Decimal(str(inv_result or 0))

        is_available = available_qty >= required_qty
        shortage_qty = max(Decimal("0"), required_qty - available_qty)

        # Check if this is a make or buy item
        has_bom = component.has_bom or False
        order_type = "production" if has_bom else "purchase"

        comp_data = {
            "component_id": component.id,
            "component_sku": component.sku,
            "component_name": component.name,
            "unit": line.unit or component.unit,
            "required_qty": float(required_qty),
            "available_qty": float(available_qty),
            "shortage_qty": float(shortage_qty),
            "is_available": is_available,
            "has_bom": has_bom,
            "order_type": order_type
        }
        components.append(comp_data)

        if not is_available:
            shortages.append(comp_data)
            if has_bom:
                work_orders_needed.append(comp_data)
            else:
                purchase_orders_needed.append(comp_data)

    return {
        "order_id": order_id,
        "order_code": order.code,
        "product_sku": order.product.sku if order.product else None,
        "quantity_ordered": float(order.quantity_ordered or 0),
        "can_release": len(shortages) == 0,
        "component_count": len(components),
        "shortage_count": len(shortages),
        "components": components,
        "shortages": shortages,
        "work_orders_needed": work_orders_needed,
        "purchase_orders_needed": purchase_orders_needed
    }


@router.get("/{order_id}/required-orders")
async def get_required_orders(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get full cascade of WOs and POs needed to fulfill this production order.

    Recursively explodes BOMs to show:
    - Sub-assemblies that need Work Orders (make items)
    - Raw materials that need Purchase Orders (buy items)

    This provides a complete MRP view of requirements at all BOM levels.
    """
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    work_orders_needed = []
    purchase_orders_needed = []

    def explode_requirements(product_id: int, quantity: Decimal, level: int = 0, visited_boms: set = None):
        """
        Recursively explode BOM to find all requirements
        
        Args:
            product_id: Product to explode BOM for
            quantity: Quantity required
            level: Current BOM depth level
            visited_boms: Set of BOM IDs visited in current recursion path (prevents circular refs)
        """
        # Initialize visited set for top-level calls
        if visited_boms is None:
            visited_boms = set()

        # Find active BOM for this product
        bom = db.query(BOM).filter(
            BOM.product_id == product_id,
            BOM.active == True  # noqa: E712 - SQL Server requires == True
        ).first()

        if not bom:
            return

        # Prevent circular references: check if this BOM is already in the current recursion path
        if bom.id in visited_boms:
            return  # Circular reference detected, stop recursion

        # Add current BOM to the path for downstream recursion
        current_path = visited_boms | {bom.id}

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
                "has_bom": component.has_bom or False
            }

            if component.has_bom:
                work_orders_needed.append(order_info)
                # Recursively explode this sub-assembly's BOM with current path
                explode_requirements(component.id, shortage_qty, level + 1, current_path)
            else:
                purchase_orders_needed.append(order_info)

    # Start explosion from the production order's product
    qty_remaining = Decimal(str(order.quantity_ordered or 0)) - Decimal(str(order.quantity_completed or 0))
    if qty_remaining > 0:
        explode_requirements(order.product_id, qty_remaining)

    return {
        "order_id": order_id,
        "order_code": order.code,
        "product_sku": order.product.sku if order.product else None,
        "quantity_remaining": float(qty_remaining),
        "work_orders_needed": work_orders_needed,
        "purchase_orders_needed": purchase_orders_needed,
        "total_work_orders": len(work_orders_needed),
        "total_purchase_orders": len(purchase_orders_needed)
    }


@router.put("/{order_id}", response_model=ProductionOrderResponse)
async def update_production_order(
    order_id: int,
    request: ProductionOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductionOrderResponse:
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
) -> Dict[str, str]:
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
) -> ProductionOrderResponse:
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
) -> ProductionOrderResponse:
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
) -> ProductionOrderResponse:
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
    try:
        process_production_completion(
            db=db,
            production_order=order,
            quantity_completed=qty_completed,
            created_by=current_user.email if current_user else None,
        )
    except UOMConversionError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    # Update linked sales order status to ready_to_ship if all production is complete
    if order.sales_order_id:
        sales_order = db.query(SalesOrder).filter(SalesOrder.id == order.sales_order_id).first()
        if sales_order and sales_order.status == "in_production":
            # Count completed and total production orders for this sales order
            complete_count = db.query(ProductionOrder).filter(
                ProductionOrder.sales_order_id == order.sales_order_id,
                ProductionOrder.status == "complete",
            ).count()

            total_count = db.query(ProductionOrder).filter(
                ProductionOrder.sales_order_id == order.sales_order_id,
            ).count()

            # Only mark ready_to_ship if ALL production orders completed successfully
            if complete_count == total_count and total_count > 0:
                sales_order.status = "ready_to_ship"
                sales_order.updated_at = datetime.utcnow()
                logger.info(
                    f"Sales order {sales_order.order_number} auto-transitioned to ready_to_ship "
                    f"({complete_count}/{total_count} production orders complete)"
                )

    db.commit()
    db.refresh(order)

    return build_production_order_response(order, db)


@router.post("/{order_id}/cancel", response_model=ProductionOrderResponse)
async def cancel_production_order(
    order_id: int,
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductionOrderResponse:
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
) -> ProductionOrderResponse:
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
) -> ProductionOrderSplitResponse:
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
) -> ProductionOrderOperationResponse:
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
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
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
) -> ProductionScheduleSummary:
    """Get production schedule summary stats"""
    today = date.today()

    status_counts = db.query(ProductionOrder.status, func.count(ProductionOrder.id)).filter(
        ProductionOrder.status.not_in(["cancelled"])
    ).group_by(ProductionOrder.status).all()
    orders_by_status = {status: count for status, count in status_counts}

    due_today = db.query(func.count(ProductionOrder.id)).filter(
        ProductionOrder.due_date == today,
        ProductionOrder.status.not_in(["complete", "cancelled"]),
    ).scalar() or 0

    overdue = db.query(func.count(ProductionOrder.id)).filter(
        ProductionOrder.due_date < today,
        ProductionOrder.status.not_in(["complete", "cancelled"]),
    ).scalar() or 0

    in_progress = orders_by_status.get("in_progress", 0)

    total_qty = db.query(func.sum(ProductionOrder.quantity_ordered - ProductionOrder.quantity_completed)).filter(
        ProductionOrder.status.not_in(["complete", "cancelled"])
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
) -> List[WorkCenterQueue]:
    """Get operations queued at each work center"""
    work_centers = db.query(WorkCenter).filter(WorkCenter.active == True).all()  # noqa: E712 - SQL Server requires == True

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


@router.post("/{order_id}/scrap", response_model=ProductionOrderScrapResponse)
async def scrap_production_order(
    order_id: int,
    scrap_reason: str = Query(..., description="Reason for scrapping"),
    quantity_scrapped: Optional[Decimal] = Query(None, description="Quantity to scrap (defaults to full order qty)"),
    notes: Optional[str] = Query(None, description="Additional notes about the failure"),
    create_remake: bool = Query(True, description="Automatically create a remake order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductionOrderScrapResponse:
    """
    Scrap a production order due to print failure.

    This will:
    1. Mark the WO as scrapped with the reason
    2. Create a scrap inventory transaction (material consumed but no output)
    3. Optionally create a remake WO linked to the original

    The scrapped WO's material costs will roll up to the SO's total COGS.

    If quantity_scrapped is less than quantity_ordered, the order stays in progress
    and you can continue producing the remaining quantity.
    """
    from app.services.inventory_service import (
        get_or_create_default_location,
        create_inventory_transaction,
        get_effective_cost,
    )

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    # Validate scrap reason against database
    valid_reason = db.query(ScrapReason).filter(
        ScrapReason.code == scrap_reason,
        ScrapReason.active == True  # noqa: E712 - SQL Server requires == True
    ).first()
    if not valid_reason:
        # Get list of valid codes for error message
        valid_codes = db.query(ScrapReason.code).filter(
            ScrapReason.active == True  # noqa: E712 - SQL Server requires == True
        ).all()
        valid_list = ", ".join([c[0] for c in valid_codes])
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scrap reason '{scrap_reason}'. Must be one of: {valid_list}"
        )

    # Can only scrap orders that are in progress or released
    if order.status not in ("released", "in_progress"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot scrap order in '{order.status}' status. Order must be 'released' or 'in_progress'."
        )

    # Default to full order quantity if not specified
    qty_to_scrap = quantity_scrapped if quantity_scrapped is not None else order.quantity_ordered

    # Validate scrap quantity
    remaining_qty = Decimal(str(order.quantity_ordered)) - Decimal(str(order.quantity_completed or 0)) - Decimal(str(order.quantity_scrapped or 0))
    if qty_to_scrap > remaining_qty:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot scrap {qty_to_scrap} units. Only {remaining_qty} units remaining (ordered: {order.quantity_ordered}, completed: {order.quantity_completed or 0}, already scrapped: {order.quantity_scrapped or 0})"
        )

    if qty_to_scrap <= 0:
        raise HTTPException(status_code=400, detail="Quantity to scrap must be greater than 0")

    # Update scrapped quantity
    order.quantity_scrapped = Decimal(str(order.quantity_scrapped or 0)) + qty_to_scrap

    # Determine if order is fully scrapped or partially scrapped
    total_accounted = Decimal(str(order.quantity_completed or 0)) + order.quantity_scrapped
    is_full_scrap = total_accounted >= order.quantity_ordered

    if is_full_scrap:
        # Full scrap - mark order as scrapped
        order.status = "scrapped"
        order.scrapped_at = datetime.utcnow()
    # else: order stays in_progress so remaining can be completed

    order.scrap_reason = scrap_reason

    scrap_note = f"Scrapped {qty_to_scrap} units: {scrap_reason}"
    if notes:
        scrap_note += f" - {notes}"
    order.notes = (order.notes or "") + f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {scrap_note}"
    order.updated_at = datetime.utcnow()

    # Create scrap inventory transactions for consumed materials
    # (Material was consumed but no finished goods produced)
    if order.bom_id:
        from app.services.inventory_service import convert_and_generate_notes

        location = get_or_create_default_location(db)
        bom = db.query(BOM).filter(BOM.id == order.bom_id).first()

        if bom:
            bom_lines = db.query(BOMLine).filter(
                BOMLine.bom_id == bom.id,
                BOMLine.consume_stage == "production"
            ).all()

            for line in bom_lines:
                if line.is_cost_only:
                    continue

                component = db.query(Product).filter(Product.id == line.component_id).first()
                if not component:
                    continue

                # Calculate consumed quantity based on scrapped qty
                base_qty = Decimal(str(line.quantity or 0))
                scrap_factor = Decimal(str(line.scrap_factor or 0)) / Decimal("100")
                qty_with_scrap = base_qty * (Decimal("1") + scrap_factor)
                bom_qty = qty_with_scrap * qty_to_scrap

                # UOM Conversion: Convert BOM line unit to component's inventory unit
                # e.g., BOM says 63.8 G per unit, but component is stored in KG
                line_unit = (line.unit or component.unit or "EA").upper()
                component_unit = (component.unit or "EA").upper()

                total_qty, notes = convert_and_generate_notes(
                    db=db,
                    bom_qty=bom_qty,
                    line_unit=line_unit,
                    component_unit=component_unit,
                    component_name=component.name,
                    component_sku=component.sku,
                    reference_prefix="Scrap from failed WO#",
                    reference_code=f"{order.code} ({scrap_reason})",
                )

                # Create scrap transaction - material consumed with no output
                create_inventory_transaction(
                    db=db,
                    product_id=line.component_id,
                    location_id=location.id,
                    transaction_type="scrap",
                    quantity=total_qty,
                    reference_type="production_order",
                    reference_id=order.id,
                    notes=notes,
                    cost_per_unit=get_effective_cost(component),
                    created_by=current_user.email if current_user else None,
                )

    remake_order = None
    # Only create remake if scrapping the full order and create_remake is True
    if create_remake and is_full_scrap:
        # Create a remake work order linked to the original
        remake_code = generate_production_order_code(db)

        remake_order = ProductionOrder(
            code=remake_code,
            product_id=order.product_id,
            bom_id=order.bom_id,
            routing_id=order.routing_id,
            sales_order_id=order.sales_order_id,
            sales_order_line_id=order.sales_order_line_id,
            remake_of_id=order.id,  # Link to original failed order
            quantity_ordered=order.quantity_ordered,
            quantity_completed=Decimal("0"),
            quantity_scrapped=Decimal("0"),
            source="remake",
            status="draft",
            priority=max(1, (order.priority or 3) - 1),  # Bump priority
            due_date=order.due_date,
            assigned_to=order.assigned_to,
            notes=f"Remake of scrapped order {order.code} (reason: {scrap_reason})",
            created_by=current_user.email if current_user else None,
        )
        db.add(remake_order)
        db.flush()

        # Copy routing operations to remake order
        if order.routing_id:
            copy_routing_to_operations(db, remake_order, order.routing_id)

    db.commit()
    db.refresh(order)

    # Build base response
    base_response = build_production_order_response(order, db)
    response_dict = base_response.model_dump()

    # Add remake info if created
    if remake_order:
        db.refresh(remake_order)
        response_dict["remake_order_id"] = remake_order.id
        response_dict["remake_order_code"] = remake_order.code
    else:
        response_dict["remake_order_id"] = None
        response_dict["remake_order_code"] = None

    return ProductionOrderScrapResponse(**response_dict)


@router.get("/{order_id}/cost-breakdown")
async def get_order_cost_breakdown(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get detailed cost breakdown for a production order including all remake costs.

    For orders that have been remade, this shows:
    - Original order material costs (scrapped)
    - Each remake attempt's costs
    - Total true cost of producing the item
    """
    from app.models.inventory import InventoryTransaction

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    def get_order_costs(wo: ProductionOrder):
        """Get material costs from inventory transactions for a WO"""
        # Get consumption and scrap transactions for this order
        transactions = db.query(InventoryTransaction).filter(
            InventoryTransaction.reference_type == "production_order",
            InventoryTransaction.reference_id == wo.id,
            InventoryTransaction.transaction_type.in_(["consumption", "scrap"])
        ).all()

        material_cost = Decimal("0")
        for txn in transactions:
            qty = abs(Decimal(str(txn.quantity or 0)))
            cost = Decimal(str(txn.cost_per_unit or 0))
            material_cost += qty * cost

        return {
            "order_id": wo.id,
            "order_code": wo.code,
            "status": wo.status,
            "is_scrapped": wo.status == "scrapped",
            "scrap_reason": wo.scrap_reason,
            "scrapped_at": wo.scrapped_at.isoformat() if wo.scrapped_at else None,
            "quantity_ordered": float(wo.quantity_ordered or 0),
            "quantity_completed": float(wo.quantity_completed or 0),
            "quantity_scrapped": float(wo.quantity_scrapped or 0),
            "material_cost": float(material_cost),
            "is_remake": wo.remake_of_id is not None,
            "remake_of_id": wo.remake_of_id,
        }

    # Get the root order (original, not a remake)
    root_order = order
    while root_order.remake_of_id:
        parent = db.query(ProductionOrder).filter(ProductionOrder.id == root_order.remake_of_id).first()
        if parent:
            root_order = parent
        else:
            break

    # Get all orders in the chain (original + all remakes)
    order_chain = [root_order]

    # Find all remakes recursively
    def find_remakes(parent_id: int):
        remakes = db.query(ProductionOrder).filter(ProductionOrder.remake_of_id == parent_id).all()
        for remake in remakes:
            order_chain.append(remake)
            find_remakes(remake.id)

    find_remakes(root_order.id)

    # Calculate costs for each order
    breakdown = []
    total_material_cost = Decimal("0")
    total_scrapped_cost = Decimal("0")
    completed_cost = Decimal("0")

    for wo in order_chain:
        costs = get_order_costs(wo)
        breakdown.append(costs)
        total_material_cost += Decimal(str(costs["material_cost"]))

        if wo.status == "scrapped":
            total_scrapped_cost += Decimal(str(costs["material_cost"]))
        elif wo.status == "complete":
            completed_cost += Decimal(str(costs["material_cost"]))

    # Count attempts
    scrapped_count = sum(1 for wo in order_chain if wo.status == "scrapped")
    completed_count = sum(1 for wo in order_chain if wo.status == "complete")

    return {
        "root_order_id": root_order.id,
        "root_order_code": root_order.code,
        "product_id": root_order.product_id,
        "product_sku": root_order.product.sku if root_order.product else None,
        "product_name": root_order.product.name if root_order.product else None,
        "sales_order_id": root_order.sales_order_id,
        "total_attempts": len(order_chain),
        "scrapped_attempts": scrapped_count,
        "successful_attempts": completed_count,
        "pending_attempts": len(order_chain) - scrapped_count - completed_count,
        "first_pass_yield": completed_count == 1 and scrapped_count == 0,
        "costs": {
            "total_material_cost": float(total_material_cost),
            "scrapped_material_cost": float(total_scrapped_cost),
            "successful_material_cost": float(completed_cost),
            "scrap_percentage": float(total_scrapped_cost / total_material_cost * 100) if total_material_cost > 0 else 0,
        },
        "order_breakdown": breakdown,
    }
