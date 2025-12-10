"""
Routings API Endpoints

CRUD operations for routings and routing operations.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.db.session import get_db
from app.logging_config import get_logger
from app.models.manufacturing import Routing, RoutingOperation, WorkCenter
from app.models.product import Product
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.manufacturing import (
    RoutingCreate,
    RoutingUpdate,
    RoutingResponse,
    RoutingListResponse,
    RoutingOperationCreate,
    RoutingOperationUpdate,
    RoutingOperationResponse,
    ApplyTemplateRequest,
    ApplyTemplateResponse,
)

router = APIRouter()
logger = get_logger(__name__)


# ============================================================================
# Routing CRUD
# ============================================================================

@router.get("/", response_model=List[RoutingListResponse])
async def list_routings(
    product_id: Optional[int] = None,
    templates_only: bool = False,
    active_only: bool = True,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List all routings.

    - **product_id**: Filter by product
    - **templates_only**: Only return template routings (no product_id)
    - **active_only**: Only return active routings
    - **search**: Search by code or product name
    """
    query = db.query(Routing).options(
        joinedload(Routing.product),
        joinedload(Routing.operations)
    )

    if templates_only:
        query = query.filter(Routing.is_template== True)
    elif product_id:
        query = query.filter(Routing.product_id == product_id)

    if active_only:
        query = query.filter(Routing.is_active== True)

    if search:
        query = query.outerjoin(Product).filter(
            (Routing.code.ilike(f"%{search}%")) |
            (Routing.name.ilike(f"%{search}%")) |
            (Product.sku.ilike(f"%{search}%")) |
            (Product.name.ilike(f"%{search}%"))
        )

    routings = query.order_by(desc(Routing.created_at)).offset(skip).limit(limit).all()

    result = []
    for r in routings:
        result.append(RoutingListResponse(
            id=r.id,
            product_id=r.product_id,
            product_sku=r.product.sku if r.product else None,
            product_name=r.product.name if r.product else None,
            code=r.code,
            name=r.name,
            is_template=r.is_template,
            version=r.version,
            revision=r.revision,
            is_active=r.is_active,
            total_run_time_minutes=r.total_run_time_minutes,
            total_cost=r.total_cost,
            operation_count=len([op for op in r.operations if op.is_active]),
            created_at=r.created_at,
        ))

    return result


@router.post("/", response_model=RoutingResponse, status_code=status.HTTP_201_CREATED)
async def create_routing(
    data: RoutingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new routing for a product or a template routing."""
    product = None

    # Templates don't need a product
    if data.is_template:
        if not data.code:
            raise HTTPException(status_code=400, detail="Template routing requires a code")
        if not data.name:
            raise HTTPException(status_code=400, detail="Template routing requires a name")
        code = data.code
        name = data.name
    else:
        # Verify product exists for non-templates
        if not data.product_id:
            raise HTTPException(status_code=400, detail="Product ID is required for non-template routings")
        product = db.query(Product).filter(Product.id == data.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Generate code if not provided
        code = data.code or f"RTG-{product.sku}-V{data.version}"
        name = data.name or f"{product.name} Routing"

    # Create routing
    routing = Routing(
        product_id=data.product_id if not data.is_template else None,
        code=code,
        name=name,
        is_template=data.is_template,
        version=data.version,
        revision=data.revision,
        effective_date=data.effective_date,
        notes=data.notes,
        is_active=data.is_active,
    )
    db.add(routing)
    db.flush()  # Get the ID

    # Add operations if provided
    if data.operations:
        for op_data in data.operations:
            # Verify work center exists
            wc = db.query(WorkCenter).filter(WorkCenter.id == op_data.work_center_id).first()
            if not wc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Work center {op_data.work_center_id} not found"
                )

            operation = RoutingOperation(
                routing_id=routing.id,
                work_center_id=op_data.work_center_id,
                sequence=op_data.sequence,
                operation_code=op_data.operation_code,
                operation_name=op_data.operation_name,
                description=op_data.description,
                setup_time_minutes=op_data.setup_time_minutes,
                run_time_minutes=op_data.run_time_minutes,
                wait_time_minutes=op_data.wait_time_minutes,
                move_time_minutes=op_data.move_time_minutes,
                runtime_source=op_data.runtime_source.value,
                slicer_file_path=op_data.slicer_file_path,
                units_per_cycle=op_data.units_per_cycle,
                scrap_rate_percent=op_data.scrap_rate_percent,
                labor_rate_override=op_data.labor_rate_override,
                machine_rate_override=op_data.machine_rate_override,
                can_overlap=op_data.can_overlap,
                is_active=op_data.is_active,
            )
            db.add(operation)

    # Recalculate totals
    db.flush()
    _recalculate_routing_totals(routing, db)

    db.commit()
    db.refresh(routing)

    if data.is_template:
        logger.info(f"Created template routing: {routing.code}")
    else:
        logger.info(f"Created routing: {routing.code} for product {product.sku}")

    return _build_routing_response(routing, db)


# ============================================================================
# Template Seeding (MUST be before /{routing_id} routes!)
# ============================================================================

@router.post("/seed-templates")
async def seed_routing_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Seed the two standard routing templates:
    - Standard Flow: Print → QC → Pack → Ship
    - Assembly Flow: Print → QC → Assemble → Pack → Ship

    Safe to call multiple times - will skip existing templates.
    """
    created = []
    skipped = []

    # Get work centers by code
    work_centers = {}
    for wc in db.query(WorkCenter).filter(WorkCenter.is_active== True).all():
        work_centers[wc.code] = wc

    # Verify required work centers exist
    required = ["FDM-POOL", "QC", "ASSEMBLY", "SHIPPING"]
    missing = [code for code in required if code not in work_centers]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required work centers: {', '.join(missing)}. Please create them first."
        )

    # Template definitions
    templates = [
        {
            "code": "TPL-STANDARD",
            "name": "Standard Flow",
            "notes": "Standard routing: Print → QC → Pack → Ship",
            "operations": [
                {
                    "sequence": 10,
                    "operation_code": "PRINT",
                    "operation_name": "3D Print",
                    "work_center_code": "FDM-POOL",
                    "setup_time_minutes": Decimal("7"),  # Printer warmup/calibration
                    "run_time_minutes": Decimal("60"),  # Default, override per product
                    "runtime_source": "slicer",
                },
                {
                    "sequence": 20,
                    "operation_code": "QC",
                    "operation_name": "Quality Check",
                    "work_center_code": "QC",
                    "setup_time_minutes": Decimal("0"),
                    "run_time_minutes": Decimal("2"),
                },
                {
                    "sequence": 30,
                    "operation_code": "PACK",
                    "operation_name": "Pack",
                    "work_center_code": "SHIPPING",
                    "setup_time_minutes": Decimal("1"),
                    "run_time_minutes": Decimal("2"),
                },
                {
                    "sequence": 40,
                    "operation_code": "SHIP",
                    "operation_name": "Ship",
                    "work_center_code": "SHIPPING",
                    "setup_time_minutes": Decimal("0"),
                    "run_time_minutes": Decimal("3"),
                },
            ]
        },
        {
            "code": "TPL-ASSEMBLY",
            "name": "Assembly Flow",
            "notes": "Assembly routing: Print → QC → Assemble → Pack → Ship",
            "operations": [
                {
                    "sequence": 10,
                    "operation_code": "PRINT",
                    "operation_name": "3D Print",
                    "work_center_code": "FDM-POOL",
                    "setup_time_minutes": Decimal("7"),  # Printer warmup/calibration
                    "run_time_minutes": Decimal("60"),  # Default, override per product
                    "runtime_source": "slicer",
                },
                {
                    "sequence": 20,
                    "operation_code": "QC",
                    "operation_name": "Quality Check",
                    "work_center_code": "QC",
                    "setup_time_minutes": Decimal("0"),
                    "run_time_minutes": Decimal("2"),
                },
                {
                    "sequence": 30,
                    "operation_code": "ASSEMBLE",
                    "operation_name": "Assembly",
                    "work_center_code": "ASSEMBLY",
                    "setup_time_minutes": Decimal("0"),
                    "run_time_minutes": Decimal("5"),  # Default, varies by product
                },
                {
                    "sequence": 40,
                    "operation_code": "PACK",
                    "operation_name": "Pack",
                    "work_center_code": "SHIPPING",
                    "setup_time_minutes": Decimal("1"),
                    "run_time_minutes": Decimal("2"),
                },
                {
                    "sequence": 50,
                    "operation_code": "SHIP",
                    "operation_name": "Ship",
                    "work_center_code": "SHIPPING",
                    "setup_time_minutes": Decimal("0"),
                    "run_time_minutes": Decimal("3"),
                },
            ]
        }
    ]

    for tpl in templates:
        # Check if already exists
        existing = db.query(Routing).filter(
            Routing.code == tpl["code"],
            Routing.is_template== True
        ).first()

        if existing:
            skipped.append(tpl["code"])
            continue

        # Create the template routing
        routing = Routing(
            code=tpl["code"],
            name=tpl["name"],
            notes=tpl["notes"],
            is_template=True,
            version=1,
            revision="1.0",
            is_active=True,
        )
        db.add(routing)
        db.flush()

        # Add operations
        for op_data in tpl["operations"]:
            wc = work_centers[op_data["work_center_code"]]
            operation = RoutingOperation(
                routing_id=routing.id,
                work_center_id=wc.id,
                sequence=op_data["sequence"],
                operation_code=op_data["operation_code"],
                operation_name=op_data["operation_name"],
                setup_time_minutes=op_data["setup_time_minutes"],
                run_time_minutes=op_data["run_time_minutes"],
                wait_time_minutes=Decimal("0"),
                move_time_minutes=Decimal("0"),
                runtime_source=op_data.get("runtime_source", "manual"),
                is_active=True,
            )
            db.add(operation)

        # Recalculate totals
        db.flush()
        _recalculate_routing_totals(routing, db)

        created.append(tpl["code"])

    db.commit()

    logger.info(f"Seeded routing templates - Created: {created}, Skipped: {skipped}")

    return {
        "message": "Routing templates seeded",
        "created": created,
        "skipped": skipped,
    }


@router.post("/apply-template", response_model=ApplyTemplateResponse)
async def apply_template_to_product(
    data: ApplyTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Apply a routing template to a product, creating a product-specific routing.

    - Copies operations from the template
    - Allows overriding times for specific operations (e.g., print time from slicer)
    - Creates or updates the routing for the product
    """
    # Validate template exists
    template = db.query(Routing).options(
        joinedload(Routing.operations).joinedload(RoutingOperation.work_center)
    ).filter(
        Routing.id == data.template_id,
        Routing.is_template== True,
        Routing.is_active== True
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Validate product exists
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check for existing routing for this product
    existing = db.query(Routing).filter(
        Routing.product_id == data.product_id,
        Routing.is_active== True
    ).first()

    # Build override lookup
    override_map = {o.operation_code: o for o in data.overrides}

    if existing:
        # Update existing routing - deactivate old operations and create new ones
        for op in existing.operations:
            op.is_active = False
        db.flush()

        routing = existing
        routing.name = f"{template.name} - {product.sku}"
        routing.notes = f"Applied from template {template.code}"
        routing.updated_at = datetime.utcnow()
        message = f"Updated routing for {product.sku}"
    else:
        # Create new routing for this product
        routing = Routing(
            product_id=product.id,
            code=f"RTG-{product.sku}",
            name=f"{template.name} - {product.sku}",
            is_template=False,
            version=1,
            revision="1.0",
            is_active=True,
            notes=f"Applied from template {template.code}",
        )
        db.add(routing)
        db.flush()
        message = f"Created routing for {product.sku}"

    # Copy operations from template with overrides
    new_operations = []
    for tpl_op in template.operations:
        if not tpl_op.is_active:
            continue

        # Check for override
        override = override_map.get(tpl_op.operation_code)

        run_time = tpl_op.run_time_minutes
        setup_time = tpl_op.setup_time_minutes

        if override:
            if override.run_time_minutes is not None:
                run_time = override.run_time_minutes
            if override.setup_time_minutes is not None:
                setup_time = override.setup_time_minutes

        operation = RoutingOperation(
            routing_id=routing.id,
            work_center_id=tpl_op.work_center_id,
            sequence=tpl_op.sequence,
            operation_code=tpl_op.operation_code,
            operation_name=tpl_op.operation_name,
            description=tpl_op.description,
            setup_time_minutes=setup_time,
            run_time_minutes=run_time,
            wait_time_minutes=tpl_op.wait_time_minutes,
            move_time_minutes=tpl_op.move_time_minutes,
            runtime_source="slicer" if override and override.run_time_minutes else tpl_op.runtime_source,
            units_per_cycle=tpl_op.units_per_cycle,
            scrap_rate_percent=tpl_op.scrap_rate_percent,
            is_active=True,
        )
        db.add(operation)
        new_operations.append(operation)

    db.flush()

    # Recalculate totals
    _recalculate_routing_totals(routing, db)

    db.commit()
    db.refresh(routing)

    logger.info(f"Applied template {template.code} to product {product.sku}")

    # Build response with operations
    ops_response = []
    for op in new_operations:
        db.refresh(op)
        wc = op.work_center
        total_time = Decimal(str(
            float(op.setup_time_minutes or 0) +
            float(op.run_time_minutes or 0) +
            float(op.wait_time_minutes or 0) +
            float(op.move_time_minutes or 0)
        ))
        # Calculate cost (includes setup + run time)
        total_costed_minutes = float(op.setup_time_minutes or 0) + float(op.run_time_minutes or 0)
        costed_hours = total_costed_minutes / 60
        rate = op.labor_rate_override or op.machine_rate_override
        if not rate and wc:
            rate = Decimal(str(wc.total_rate_per_hour))
        calculated_cost = Decimal(str(costed_hours * float(rate or 0)))

        ops_response.append(RoutingOperationResponse(
            id=op.id,
            routing_id=op.routing_id,
            work_center_id=op.work_center_id,
            work_center_code=wc.code if wc else None,
            work_center_name=wc.name if wc else None,
            sequence=op.sequence,
            operation_code=op.operation_code,
            operation_name=op.operation_name,
            description=op.description,
            setup_time_minutes=op.setup_time_minutes,
            run_time_minutes=op.run_time_minutes,
            wait_time_minutes=op.wait_time_minutes,
            move_time_minutes=op.move_time_minutes,
            runtime_source=op.runtime_source,
            slicer_file_path=op.slicer_file_path,
            units_per_cycle=op.units_per_cycle,
            scrap_rate_percent=op.scrap_rate_percent,
            labor_rate_override=op.labor_rate_override,
            machine_rate_override=op.machine_rate_override,
            predecessor_operation_id=op.predecessor_operation_id,
            can_overlap=op.can_overlap,
            is_active=op.is_active,
            total_time_minutes=total_time,
            calculated_cost=calculated_cost,
            created_at=op.created_at,
            updated_at=op.updated_at,
        ))

    return ApplyTemplateResponse(
        routing_id=routing.id,
        routing_code=routing.code,
        product_sku=product.sku,
        product_name=product.name,
        operations=ops_response,
        total_run_time_minutes=routing.total_run_time_minutes or Decimal("0"),
        total_cost=routing.total_cost or Decimal("0"),
        message=message,
    )


# ============================================================================
# Single Routing CRUD
# ============================================================================

@router.get("/{routing_id}", response_model=RoutingResponse)
async def get_routing(
    routing_id: int,
    db: Session = Depends(get_db),
):
    """Get a routing by ID with all operations."""
    routing = db.query(Routing).options(
        joinedload(Routing.product),
        joinedload(Routing.operations).joinedload(RoutingOperation.work_center)
    ).filter(Routing.id == routing_id).first()

    if not routing:
        raise HTTPException(status_code=404, detail="Routing not found")

    return _build_routing_response(routing, db)


@router.get("/product/{product_id}", response_model=RoutingResponse)
async def get_product_routing(
    product_id: int,
    db: Session = Depends(get_db),
):
    """Get the active routing for a product."""
    routing = db.query(Routing).options(
        joinedload(Routing.product),
        joinedload(Routing.operations).joinedload(RoutingOperation.work_center)
    ).filter(
        Routing.product_id == product_id,
        Routing.is_active== True
    ).order_by(desc(Routing.version)).first()

    if not routing:
        raise HTTPException(status_code=404, detail="No active routing found for product")

    return _build_routing_response(routing, db)


@router.put("/{routing_id}", response_model=RoutingResponse)
async def update_routing(
    routing_id: int,
    data: RoutingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a routing."""
    routing = db.query(Routing).filter(Routing.id == routing_id).first()
    if not routing:
        raise HTTPException(status_code=404, detail="Routing not found")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(routing, field, value)

    routing.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(routing)

    logger.info(f"Updated routing: {routing.code}")

    return _build_routing_response(routing, db)


@router.delete("/{routing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing(
    routing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a routing (soft delete - marks as inactive)."""
    routing = db.query(Routing).filter(Routing.id == routing_id).first()
    if not routing:
        raise HTTPException(status_code=404, detail="Routing not found")

    routing.is_active = False
    routing.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Deactivated routing: {routing.code}")


# ============================================================================
# Routing Operations CRUD
# ============================================================================

@router.get("/{routing_id}/operations", response_model=List[RoutingOperationResponse])
async def list_routing_operations(
    routing_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List all operations for a routing."""
    routing = db.query(Routing).filter(Routing.id == routing_id).first()
    if not routing:
        raise HTTPException(status_code=404, detail="Routing not found")

    query = db.query(RoutingOperation).options(
        joinedload(RoutingOperation.work_center)
    ).filter(RoutingOperation.routing_id == routing_id)

    if active_only:
        query = query.filter(RoutingOperation.is_active== True)

    operations = query.order_by(RoutingOperation.sequence).all()

    return [_build_operation_response(op) for op in operations]


@router.post("/{routing_id}/operations", response_model=RoutingOperationResponse, status_code=status.HTTP_201_CREATED)
async def add_routing_operation(
    routing_id: int,
    data: RoutingOperationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new operation to a routing."""
    routing = db.query(Routing).filter(Routing.id == routing_id).first()
    if not routing:
        raise HTTPException(status_code=404, detail="Routing not found")

    # Verify work center exists
    wc = db.query(WorkCenter).filter(WorkCenter.id == data.work_center_id).first()
    if not wc:
        raise HTTPException(status_code=400, detail="Work center not found")

    operation = RoutingOperation(
        routing_id=routing_id,
        work_center_id=data.work_center_id,
        sequence=data.sequence,
        operation_code=data.operation_code,
        operation_name=data.operation_name,
        description=data.description,
        setup_time_minutes=data.setup_time_minutes,
        run_time_minutes=data.run_time_minutes,
        wait_time_minutes=data.wait_time_minutes,
        move_time_minutes=data.move_time_minutes,
        runtime_source=data.runtime_source.value,
        slicer_file_path=data.slicer_file_path,
        units_per_cycle=data.units_per_cycle,
        scrap_rate_percent=data.scrap_rate_percent,
        labor_rate_override=data.labor_rate_override,
        machine_rate_override=data.machine_rate_override,
        predecessor_operation_id=data.predecessor_operation_id,
        can_overlap=data.can_overlap,
        is_active=data.is_active,
    )
    db.add(operation)
    db.flush()

    # Recalculate routing totals
    _recalculate_routing_totals(routing, db)

    db.commit()
    db.refresh(operation)

    logger.info(f"Added operation {operation.sequence} to routing {routing.code}")

    return _build_operation_response(operation)


@router.put("/operations/{operation_id}", response_model=RoutingOperationResponse)
async def update_routing_operation(
    operation_id: int,
    data: RoutingOperationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a routing operation."""
    operation = db.query(RoutingOperation).options(
        joinedload(RoutingOperation.routing),
        joinedload(RoutingOperation.work_center)
    ).filter(RoutingOperation.id == operation_id).first()

    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    # Verify work center if changing
    if data.work_center_id:
        wc = db.query(WorkCenter).filter(WorkCenter.id == data.work_center_id).first()
        if not wc:
            raise HTTPException(status_code=400, detail="Work center not found")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "runtime_source" and value:
            value = value.value
        setattr(operation, field, value)

    operation.updated_at = datetime.utcnow()

    # Recalculate routing totals
    _recalculate_routing_totals(operation.routing, db)

    db.commit()
    db.refresh(operation)

    logger.info(f"Updated operation {operation.id}")

    return _build_operation_response(operation)


@router.delete("/operations/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_operation(
    operation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a routing operation (soft delete)."""
    operation = db.query(RoutingOperation).options(
        joinedload(RoutingOperation.routing)
    ).filter(RoutingOperation.id == operation_id).first()

    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    operation.is_active = False
    operation.updated_at = datetime.utcnow()

    # Recalculate routing totals
    _recalculate_routing_totals(operation.routing, db)

    db.commit()

    logger.info(f"Deactivated operation {operation_id}")


# ============================================================================
# Helper Functions
# ============================================================================

def _recalculate_routing_totals(routing: Routing, db: Session):
    """Recalculate routing totals from operations."""
    operations = db.query(RoutingOperation).options(
        joinedload(RoutingOperation.work_center)
    ).filter(
        RoutingOperation.routing_id == routing.id,
        RoutingOperation.is_active== True
    ).all()

    total_setup = Decimal("0")
    total_run = Decimal("0")
    total_cost = Decimal("0")

    for op in operations:
        total_setup += op.setup_time_minutes or Decimal("0")
        total_run += (op.run_time_minutes or Decimal("0")) + \
                     (op.wait_time_minutes or Decimal("0")) + \
                     (op.move_time_minutes or Decimal("0"))

        # Calculate operation cost (includes setup + run time)
        total_costed_minutes = float(op.setup_time_minutes or 0) + float(op.run_time_minutes or 0)
        costed_hours = total_costed_minutes / 60
        rate = op.labor_rate_override or op.machine_rate_override
        if not rate and op.work_center:
            rate = (
                (op.work_center.machine_rate_per_hour or Decimal("0")) +
                (op.work_center.labor_rate_per_hour or Decimal("0")) +
                (op.work_center.overhead_rate_per_hour or Decimal("0"))
            )
        total_cost += Decimal(str(costed_hours)) * (rate or Decimal("0"))

    routing.total_setup_time_minutes = total_setup
    routing.total_run_time_minutes = total_run
    routing.total_cost = total_cost
    routing.updated_at = datetime.utcnow()


def _build_routing_response(routing: Routing, db: Session) -> RoutingResponse:
    """Build a routing response with operations."""
    operations = []
    for op in sorted(routing.operations, key=lambda x: x.sequence):
        if op.is_active:
            operations.append(_build_operation_response(op))

    return RoutingResponse(
        id=routing.id,
        product_id=routing.product_id,
        product_sku=routing.product.sku if routing.product else None,
        product_name=routing.product.name if routing.product else None,
        code=routing.code,
        name=routing.name,
        is_template=routing.is_template,
        version=routing.version,
        revision=routing.revision,
        effective_date=routing.effective_date,
        notes=routing.notes,
        is_active=routing.is_active,
        total_setup_time_minutes=routing.total_setup_time_minutes,
        total_run_time_minutes=routing.total_run_time_minutes,
        total_cost=routing.total_cost,
        operations=operations,
        created_at=routing.created_at,
        updated_at=routing.updated_at,
    )


def _build_operation_response(op: RoutingOperation) -> RoutingOperationResponse:
    """Build a routing operation response."""
    total_time = (
        (op.setup_time_minutes or Decimal("0")) +
        (op.run_time_minutes or Decimal("0")) +
        (op.wait_time_minutes or Decimal("0")) +
        (op.move_time_minutes or Decimal("0"))
    )

    # Calculate cost (includes setup + run time)
    total_costed_minutes = float(op.setup_time_minutes or 0) + float(op.run_time_minutes or 0)
    costed_hours = total_costed_minutes / 60
    rate = op.labor_rate_override or op.machine_rate_override
    if not rate and op.work_center:
        rate = (
            (op.work_center.machine_rate_per_hour or Decimal("0")) +
            (op.work_center.labor_rate_per_hour or Decimal("0")) +
            (op.work_center.overhead_rate_per_hour or Decimal("0"))
        )
    calculated_cost = Decimal(str(costed_hours)) * (rate or Decimal("0"))

    return RoutingOperationResponse(
        id=op.id,
        routing_id=op.routing_id,
        work_center_id=op.work_center_id,
        work_center_code=op.work_center.code if op.work_center else None,
        work_center_name=op.work_center.name if op.work_center else None,
        sequence=op.sequence,
        operation_code=op.operation_code,
        operation_name=op.operation_name,
        description=op.description,
        setup_time_minutes=op.setup_time_minutes,
        run_time_minutes=op.run_time_minutes,
        wait_time_minutes=op.wait_time_minutes,
        move_time_minutes=op.move_time_minutes,
        runtime_source=op.runtime_source,
        slicer_file_path=op.slicer_file_path,
        units_per_cycle=op.units_per_cycle,
        scrap_rate_percent=op.scrap_rate_percent,
        labor_rate_override=op.labor_rate_override,
        machine_rate_override=op.machine_rate_override,
        predecessor_operation_id=op.predecessor_operation_id,
        can_overlap=op.can_overlap,
        is_active=op.is_active,
        total_time_minutes=total_time,
        calculated_cost=calculated_cost,
        created_at=op.created_at,
        updated_at=op.updated_at,
    )
