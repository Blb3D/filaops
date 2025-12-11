"""
BOM Management Endpoints (Admin Only)

Handles Bill of Materials viewing, editing, and approval
"""
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.db.session import get_db
from app.models.bom import BOM, BOMLine
from app.models.product import Product
from app.models.user import User
from app.models.inventory import Inventory
from app.models.manufacturing import Routing
from app.api.v1.deps import get_current_staff_user
from app.logging_config import get_logger
from app.schemas.bom import (
    BOMCreate,
    BOMUpdate,
    BOMListResponse,
    BOMResponse,
    BOMLineCreate,
    BOMLineUpdate,
    BOMLineResponse,
    BOMRecalculateResponse,
    BOMCopyRequest,
)

router = APIRouter(prefix="/bom", tags=["Admin - BOM Management"])

logger = get_logger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_effective_cost(product: Product) -> Decimal:
    """Get the effective cost for a product using fallback priority.

    Priority: standard_cost → average_cost → last_cost → cost (legacy)
    """
    if product.standard_cost and product.standard_cost > 0:
        return Decimal(str(product.standard_cost))
    if product.average_cost and product.average_cost > 0:
        return Decimal(str(product.average_cost))
    if product.last_cost and product.last_cost > 0:
        return Decimal(str(product.last_cost))
    if product.cost and product.cost > 0:
        return Decimal(str(product.cost))
    return Decimal("0")


def get_component_inventory(component_id: int, db: Session) -> dict:
    """Get total inventory for a component across all locations"""
    from sqlalchemy import func

    result = db.query(
        func.sum(Inventory.on_hand_quantity).label('on_hand'),
        func.sum(Inventory.allocated_quantity).label('allocated'),
        func.sum(Inventory.available_quantity).label('available')
    ).filter(Inventory.product_id == component_id).first()

    return {
        "on_hand": float(result.on_hand or 0) if result else 0,
        "allocated": float(result.allocated or 0) if result else 0,
        "available": float(result.available or 0) if result else 0,
    }


def build_bom_response(bom: BOM, db: Session) -> dict:
    """
    Assembles a detailed BOM representation including product metadata and per-line component, cost, inventory, and sub-assembly information.
    
    Parameters:
        bom (BOM): The BOM ORM object to convert into a response dictionary.
    
    Returns:
        dict: A dictionary with BOM fields (id, product_id, code, name, version, active, total_cost, etc.)
        and a `lines` list. Each line entry contains component identifiers and metadata, `quantity`,
        computed `component_cost` and `line_cost` (when available), inventory summaries
        (`inventory_on_hand`, `inventory_available`, `is_available`, `shortage`), and a `has_bom`
        boolean indicating whether the component is a sub-assembly.
    """
    lines = []
    for line in bom.lines:
        component = db.query(Product).filter(Product.id == line.component_id).first()
        component_cost = get_effective_cost(component) if component else Decimal("0")
        line_cost = None
        if component and component_cost > 0 and line.quantity:
            line_cost = float(component_cost) * float(line.quantity)

        # Get inventory status
        inventory = get_component_inventory(line.component_id, db)
        qty_needed = float(line.quantity) if line.quantity else 0
        is_available = inventory["available"] >= qty_needed
        shortage = max(0, qty_needed - inventory["available"])

        # Check if component has its own BOM (is a sub-assembly)
        component_has_bom = db.query(BOM).filter(
            BOM.product_id == line.component_id,
            BOM.active.is_(True)
        ).first() is not None

        lines.append({
            "id": line.id,
            "bom_id": line.bom_id,
            "component_id": line.component_id,
            "quantity": line.quantity,
            "sequence": line.sequence,
            "scrap_factor": line.scrap_factor,
            "notes": line.notes,
            "component_sku": component.sku if component else None,
            "component_name": component.name if component else None,
            "component_unit": component.unit if component else None,
            "component_cost": float(component_cost) if component_cost else None,
            "line_cost": line_cost,
            # Inventory info
            "inventory_on_hand": inventory["on_hand"],
            "inventory_available": inventory["available"],
            "is_available": is_available,
            "shortage": shortage,
            # Sub-assembly indicator
            "has_bom": component_has_bom,
        })

    product = bom.product
    return {
        "id": bom.id,
        "product_id": bom.product_id,
        "product_sku": product.sku if product else None,
        "product_name": product.name if product else None,
        "code": bom.code,
        "name": bom.name,
        "version": bom.version,
        "revision": bom.revision,
        "active": bom.active,
        "total_cost": bom.total_cost,
        "assembly_time_minutes": bom.assembly_time_minutes,
        "effective_date": bom.effective_date,
        "notes": bom.notes,
        "created_at": bom.created_at,
        "lines": lines,
    }


def recalculate_bom_cost(bom: BOM, db: Session) -> Decimal:
    """Recalculate total BOM cost from component costs"""
    total = Decimal("0")
    for line in bom.lines:
        component = db.query(Product).filter(Product.id == line.component_id).first()
        if component:
            cost = get_effective_cost(component)
            if cost > 0:
                qty = line.quantity or Decimal("0")
                scrap = line.scrap_factor or Decimal("0")
                # Add scrap factor: qty * (1 + scrap/100)
                effective_qty = qty * (1 + scrap / 100)
                total += cost * effective_qty
    return total


# ============================================================================
# LIST & GET ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[BOMListResponse])
async def list_boms(
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    product_id: Optional[int] = None,
    active_only: bool = True,
    search: Optional[str] = None,
):
    """
    Return a paginated summary list of BOMs including product metadata and cost totals.
    
    Supports optional filtering by product, limiting to active BOMs, and case-insensitive partial search against product SKU, product name, BOM code, or BOM name. Results are ordered by creation date (newest first) and include routing process cost when available.
    
    Parameters:
        skip (int): Number of records to skip (offset).
        limit (int): Maximum number of records to return.
        product_id (Optional[int]): If provided, only BOMs for this product are returned.
        active_only (bool): If True, only BOMs marked active are included.
        search (Optional[str]): Case-insensitive substring to match against product SKU, product name, BOM code, or BOM name.
    
    Returns:
        List[dict]: A list of BOM summary objects with keys:
            - id: BOM database id
            - product_id: Associated product id
            - product_sku: Product SKU or None
            - product_name: Product name or None
            - code: BOM code
            - name: BOM name
            - version: BOM version
            - revision: BOM revision
            - active: BOM active flag
            - material_cost: BOM material total (Decimal)
            - process_cost: Routing/process total cost (Decimal)
            - total_cost: Sum of material_cost and process_cost (Decimal)
            - line_count: Number of BOM lines
            - created_at: BOM creation timestamp
    """
    query = db.query(BOM).options(joinedload(BOM.product), joinedload(BOM.lines))

    if product_id:
        query = query.filter(BOM.product_id == product_id)

    if active_only:
        query = query.filter(BOM.active.is_(True))

    if search:
        query = query.join(Product).filter(
            (Product.sku.ilike(f"%{search}%")) |
            (Product.name.ilike(f"%{search}%")) |
            (BOM.code.ilike(f"%{search}%")) |
            (BOM.name.ilike(f"%{search}%"))
        )

    query = query.order_by(desc(BOM.created_at))
    boms = query.offset(skip).limit(limit).all()

    result = []
    for bom in boms:
        product = bom.product
        material_cost = bom.total_cost or Decimal("0")

        # Get routing process cost for this product
        routing = db.query(Routing).filter(
            Routing.product_id == bom.product_id,
            Routing.is_active.is_(True)
        ).first()
        process_cost = routing.total_cost if routing and routing.total_cost else Decimal("0")

        # Combined total
        combined_total = material_cost + process_cost

        result.append({
            "id": bom.id,
            "product_id": bom.product_id,
            "product_sku": product.sku if product else None,
            "product_name": product.name if product else None,
            "code": bom.code,
            "name": bom.name,
            "version": bom.version,
            "revision": bom.revision,
            "active": bom.active,
            "material_cost": material_cost,
            "process_cost": process_cost,
            "total_cost": combined_total,
            "line_count": len(bom.lines),
            "created_at": bom.created_at,
        })

    return result


@router.get("/{bom_id}", response_model=BOMResponse)
async def get_bom(
    bom_id: int,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Get a single BOM with all lines and component details.

    Admin only.
    """
    bom = (
        db.query(BOM)
        .options(joinedload(BOM.product), joinedload(BOM.lines))
        .filter(BOM.id == bom_id)
        .first()
    )

    if not bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOM not found"
        )

    return build_bom_response(bom, db)


# ============================================================================
# CREATE & UPDATE ENDPOINTS
# ============================================================================

@router.post("/", response_model=BOMResponse, status_code=status.HTTP_201_CREATED)
async def create_bom(
    bom_data: BOMCreate,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Create a new BOM for a product.

    Admin only. Can include initial lines.
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == bom_data.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Generate BOM code if not provided
    bom_code = bom_data.code
    if not bom_code:
        # Generate code based on product SKU and version
        version = bom_data.version or 1
        bom_code = f"BOM-{product.sku}-V{version}"

    # Generate name if not provided
    bom_name = bom_data.name
    if not bom_name:
        bom_name = f"{product.name} BOM"

    # Create BOM
    bom = BOM(
        product_id=bom_data.product_id,
        code=bom_code,
        name=bom_name,
        version=bom_data.version or 1,
        revision=bom_data.revision or "1.0",
        assembly_time_minutes=bom_data.assembly_time_minutes,
        effective_date=bom_data.effective_date,
        notes=bom_data.notes,
        active=True,
    )
    db.add(bom)
    db.flush()  # Get the BOM ID

    # Add lines if provided
    if bom_data.lines:
        for seq, line_data in enumerate(bom_data.lines, start=1):
            # Verify component exists
            component = db.query(Product).filter(Product.id == line_data.component_id).first()
            if not component:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Component {line_data.component_id} not found"
                )

            line = BOMLine(
                bom_id=bom.id,
                component_id=line_data.component_id,
                quantity=line_data.quantity,
                sequence=line_data.sequence or seq,
                scrap_factor=line_data.scrap_factor,
                notes=line_data.notes,
            )
            db.add(line)

    # Calculate total cost
    db.flush()
    bom.total_cost = recalculate_bom_cost(bom, db)

    # Update product flag
    product.has_bom = True

    db.commit()
    db.refresh(bom)

    logger.info(
        "BOM created",
        extra={
            "bom_id": bom.id,
            "product_id": product.id,
            "product_sku": product.sku,
            "admin_id": current_admin.id,
            "admin_email": current_admin.email
        }
    )

    return build_bom_response(bom, db)


@router.patch("/{bom_id}", response_model=BOMResponse)
async def update_bom(
    bom_id: int,
    bom_data: BOMUpdate,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Update BOM header fields (not lines).

    Admin only. Use line-specific endpoints to modify lines.
    """
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOM not found"
        )

    # Update provided fields
    update_data = bom_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bom, field, value)

    db.commit()
    db.refresh(bom)

    logger.info(
        "BOM updated",
        extra={
            "bom_id": bom_id,
            "admin_id": current_admin.id,
            "admin_email": current_admin.email
        }
    )

    return build_bom_response(bom, db)


@router.delete("/{bom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bom(
    bom_id: int,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Delete a BOM (soft delete by setting active=False).

    Admin only.
    """
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOM not found"
        )

    # Soft delete
    bom.active = False
    db.commit()

    logger.info(
        "BOM deactivated",
        extra={
            "bom_id": bom_id,
            "admin_id": current_admin.id,
            "admin_email": current_admin.email
        }
    )


# ============================================================================
# BOM LINE ENDPOINTS
# ============================================================================

@router.post("/{bom_id}/lines", response_model=BOMLineResponse, status_code=status.HTTP_201_CREATED)
async def add_bom_line(
    bom_id: int,
    line_data: BOMLineCreate,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Add a new line to a BOM.

    Admin only.
    """
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOM not found"
        )

    # Verify component exists
    component = db.query(Product).filter(Product.id == line_data.component_id).first()
    if not component:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Component not found"
        )

    # Get next sequence if not provided
    if line_data.sequence is None:
        max_seq = db.query(BOMLine).filter(BOMLine.bom_id == bom_id).count()
        sequence = max_seq + 1
    else:
        sequence = line_data.sequence

    # Create line
    line = BOMLine(
        bom_id=bom_id,
        component_id=line_data.component_id,
        quantity=line_data.quantity,
        sequence=sequence,
        scrap_factor=line_data.scrap_factor,
        notes=line_data.notes,
    )
    db.add(line)

    # Recalculate BOM cost
    db.flush()
    bom.total_cost = recalculate_bom_cost(bom, db)

    db.commit()
    db.refresh(line)

    # Calculate line cost
    comp_cost = get_effective_cost(component)
    line_cost = None
    if comp_cost > 0 and line.quantity:
        line_cost = float(comp_cost) * float(line.quantity)

    logger.info(
        "BOM line added",
        extra={
            "bom_id": bom_id,
            "line_id": line.id,
            "component_id": line.component_id,
            "admin_id": current_admin.id,
            "admin_email": current_admin.email
        }
    )

    return {
        "id": line.id,
        "bom_id": line.bom_id,
        "component_id": line.component_id,
        "quantity": line.quantity,
        "sequence": line.sequence,
        "scrap_factor": line.scrap_factor,
        "notes": line.notes,
        "component_sku": component.sku,
        "component_name": component.name,
        "component_unit": component.unit,
        "component_cost": float(comp_cost) if comp_cost else None,
        "line_cost": line_cost,
    }


@router.patch("/{bom_id}/lines/{line_id}", response_model=BOMLineResponse)
async def update_bom_line(
    bom_id: int,
    line_id: int,
    line_data: BOMLineUpdate,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Update a BOM line.

    Admin only.
    """
    line = db.query(BOMLine).filter(
        BOMLine.id == line_id,
        BOMLine.bom_id == bom_id
    ).first()

    if not line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOM line not found"
        )

    # If changing component, verify it exists
    if line_data.component_id is not None:
        component = db.query(Product).filter(Product.id == line_data.component_id).first()
        if not component:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Component not found"
            )

    # Update provided fields
    update_data = line_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(line, field, value)

    # Recalculate BOM cost
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    bom.total_cost = recalculate_bom_cost(bom, db)

    db.commit()
    db.refresh(line)

    # Get component for response
    component = db.query(Product).filter(Product.id == line.component_id).first()
    comp_cost = get_effective_cost(component) if component else Decimal("0")
    line_cost = None
    if component and comp_cost > 0 and line.quantity:
        line_cost = float(comp_cost) * float(line.quantity)

    logger.info(
        "BOM line updated",
        extra={
            "bom_id": bom_id,
            "line_id": line_id,
            "admin_id": current_admin.id,
            "admin_email": current_admin.email
        }
    )

    return {
        "id": line.id,
        "bom_id": line.bom_id,
        "component_id": line.component_id,
        "quantity": line.quantity,
        "sequence": line.sequence,
        "scrap_factor": line.scrap_factor,
        "notes": line.notes,
        "component_sku": component.sku if component else None,
        "component_name": component.name if component else None,
        "component_unit": component.unit if component else None,
        "component_cost": float(comp_cost) if comp_cost else None,
        "line_cost": line_cost,
    }


@router.delete("/{bom_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bom_line(
    bom_id: int,
    line_id: int,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Delete a BOM line.

    Admin only.
    """
    line = db.query(BOMLine).filter(
        BOMLine.id == line_id,
        BOMLine.bom_id == bom_id
    ).first()

    if not line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOM line not found"
        )

    db.delete(line)

    # Recalculate BOM cost
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    db.flush()
    bom.total_cost = recalculate_bom_cost(bom, db)

    db.commit()

    logger.info(
        "BOM line deleted",
        extra={
            "bom_id": bom_id,
            "line_id": line_id,
            "admin_id": current_admin.id,
            "admin_email": current_admin.email
        }
    )


# ============================================================================
# BULK & UTILITY ENDPOINTS
# ============================================================================

@router.post("/{bom_id}/recalculate", response_model=BOMRecalculateResponse)
async def recalculate_bom(
    bom_id: int,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Recalculate BOM total cost from current component costs.

    Admin only. Useful after component prices change.
    """
    bom = (
        db.query(BOM)
        .options(joinedload(BOM.lines))
        .filter(BOM.id == bom_id)
        .first()
    )

    if not bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOM not found"
        )

    previous_cost = bom.total_cost

    # Calculate line costs for response
    line_costs = []
    for line in bom.lines:
        component = db.query(Product).filter(Product.id == line.component_id).first()
        if component and component.cost:
            qty = line.quantity or Decimal("0")
            scrap = line.scrap_factor or Decimal("0")
            effective_qty = qty * (1 + scrap / 100)
            line_cost = float(component.cost * effective_qty)
        else:
            line_cost = 0

        line_costs.append({
            "line_id": line.id,
            "component_sku": component.sku if component else None,
            "quantity": float(line.quantity) if line.quantity else 0,
            "unit_cost": float(component.cost) if component and component.cost else 0,
            "line_cost": line_cost,
        })

    # Update total
    new_cost = recalculate_bom_cost(bom, db)
    bom.total_cost = new_cost
    db.commit()

    logger.info(
        "BOM recalculated",
        extra={
            "bom_id": bom_id,
            "previous_cost": str(previous_cost),
            "new_cost": str(new_cost),
            "admin_id": current_admin.id,
            "admin_email": current_admin.email
        }
    )

    return {
        "bom_id": bom_id,
        "previous_cost": previous_cost,
        "new_cost": new_cost,
        "line_costs": line_costs,
    }


@router.post("/{bom_id}/copy", response_model=BOMResponse, status_code=status.HTTP_201_CREATED)
async def copy_bom(
    bom_id: int,
    copy_data: BOMCopyRequest,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Copy a BOM to another product.

    Admin only. Useful for creating similar products.
    """
    # Get source BOM
    source_bom = (
        db.query(BOM)
        .options(joinedload(BOM.lines))
        .filter(BOM.id == bom_id)
        .first()
    )

    if not source_bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source BOM not found"
        )

    # Verify target product exists
    target_product = db.query(Product).filter(Product.id == copy_data.target_product_id).first()
    if not target_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target product not found"
        )

    # Create new BOM
    new_bom = BOM(
        product_id=copy_data.target_product_id,
        code=f"{target_product.sku}-BOM",
        name=f"BOM for {target_product.name}",
        version=copy_data.new_version or 1,
        revision=source_bom.revision,
        assembly_time_minutes=source_bom.assembly_time_minutes,
        effective_date=source_bom.effective_date,
        notes=f"Copied from BOM {bom_id}",
        active=True,
    )
    db.add(new_bom)
    db.flush()

    # Copy lines if requested
    if copy_data.include_lines:
        for line in source_bom.lines:
            new_line = BOMLine(
                bom_id=new_bom.id,
                component_id=line.component_id,
                quantity=line.quantity,
                sequence=line.sequence,
                scrap_factor=line.scrap_factor,
                notes=line.notes,
            )
            db.add(new_line)

    # Calculate cost
    db.flush()
    new_bom.total_cost = recalculate_bom_cost(new_bom, db)

    # Update target product flag
    target_product.has_bom = True

    db.commit()
    db.refresh(new_bom)

    logger.info(
        "BOM copied",
        extra={
            "source_bom_id": bom_id,
            "target_product_id": target_product.id,
            "target_product_sku": target_product.sku,
            "new_bom_id": new_bom.id,
            "admin_id": current_admin.id,
            "admin_email": current_admin.email
        }
    )

    return build_bom_response(new_bom, db)


@router.get("/product/{product_id}", response_model=BOMResponse)
async def get_bom_by_product(
    product_id: int,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve the most recent active BOM for the given product.
    
    Returns:
        A detailed BOM response containing product info and BOM lines.
    
    Raises:
        HTTPException: 404 if no active BOM exists for the product.
    """
    bom = (
        db.query(BOM)
        .options(joinedload(BOM.product), joinedload(BOM.lines))
        .filter(BOM.product_id == product_id, BOM.active.is_(True))
        .order_by(desc(BOM.version))
        .first()
    )

    if not bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active BOM found for this product"
        )

    return build_bom_response(bom, db)


# ============================================================================
# SUB-ASSEMBLY / MULTI-LEVEL BOM ENDPOINTS
# ============================================================================

def explode_bom_recursive(
    bom_id: int,
    db: Session,
    parent_qty: Decimal = Decimal("1"),
    level: int = 0,
    visited: set = None,
    max_depth: int = 10
) -> list:
    """
    Explodes a BOM into its leaf components and returns per-component entries with quantities, costs, inventory, and sub-assembly metadata.
    
    Parameters:
        bom_id (int): ID of the BOM to explode.
        parent_qty (Decimal): Multiplier inherited from the parent level (default 1).
        level (int): Current recursion depth (root is 0).
        visited (set): Set of BOM IDs already visited to detect circular references.
        max_depth (int): Maximum allowed recursion depth; exceeding it yields an error entry.
    
    Returns:
        list: A list where each item is either:
          - a component dict containing keys such as `component_id`, `component_sku`, `component_name`,
            `component_unit`, `component_cost`, `base_quantity`, `effective_quantity`, `scrap_factor`,
            `level`, `parent_bom_id`, `is_sub_assembly`, `sub_bom_id`, `inventory_available`, and `line_cost`;
          - or an error dict with keys like `error` (e.g., `"circular_reference"` or `"max_depth_exceeded"`),
            `bom_id` or `level`, and `message` describing the problem.
    """
    if visited is None:
        visited = set()

    # Circular reference check
    if bom_id in visited:
        return [{
            "error": "circular_reference",
            "bom_id": bom_id,
            "level": level,
            "message": f"Circular reference detected at BOM {bom_id}"
        }]

    # Depth limit check
    if level > max_depth:
        return [{
            "error": "max_depth_exceeded",
            "level": level,
            "message": f"Maximum depth of {max_depth} exceeded"
        }]

    visited.add(bom_id)

    bom = db.query(BOM).options(joinedload(BOM.lines)).filter(BOM.id == bom_id).first()
    if not bom:
        return []

    exploded = []

    for line in bom.lines:
        component = db.query(Product).filter(Product.id == line.component_id).first()
        if not component:
            continue

        # Calculate effective quantity (including scrap factor)
        qty = line.quantity or Decimal("0")
        scrap = line.scrap_factor or Decimal("0")
        effective_qty = qty * (1 + scrap / 100) * parent_qty

        # Check if this component has its own BOM (sub-assembly)
        sub_bom = (
            db.query(BOM)
            .filter(BOM.product_id == component.id, BOM.active.is_(True))
            .order_by(desc(BOM.version))
            .first()
        )

        # Get inventory
        inventory = get_component_inventory(component.id, db)

        component_data = {
            "component_id": component.id,
            "component_sku": component.sku,
            "component_name": component.name,
            "component_unit": component.unit,
            "component_cost": float(component.cost) if component.cost else 0,
            "base_quantity": float(qty),
            "effective_quantity": float(effective_qty),
            "scrap_factor": float(scrap) if scrap else 0,
            "level": level,
            "parent_bom_id": bom_id,
            "is_sub_assembly": sub_bom is not None,
            "sub_bom_id": sub_bom.id if sub_bom else None,
            "inventory_available": inventory["available"],
            "line_cost": float(component.cost * effective_qty) if component.cost else 0,
        }

        exploded.append(component_data)

        # Recursively explode sub-assemblies
        if sub_bom:
            sub_exploded = explode_bom_recursive(
                sub_bom.id,
                db,
                parent_qty=effective_qty,
                level=level + 1,
                visited=visited.copy(),  # Copy to allow parallel branches
                max_depth=max_depth
            )
            exploded.extend(sub_exploded)

    return exploded


def calculate_rolled_up_cost(bom_id: int, db: Session, visited: set = None) -> Decimal:
    """
    Compute the total rolled-up cost for a BOM by summing costs of its lines and any sub-assembly BOMs.
    
    Parameters:
        bom_id (int): ID of the BOM to roll up.
        db (Session): Database session.
        visited (set, optional): Set of BOM IDs already visited to prevent infinite recursion; callers normally omit this.
    
    Returns:
        Decimal: Total cost of the BOM including costs of sub-assemblies. Returns Decimal('0') if the BOM is not found or a circular reference is encountered for a visited BOM.
    """
    if visited is None:
        visited = set()

    if bom_id in visited:
        return Decimal("0")  # Circular reference, don't double-count

    visited.add(bom_id)

    bom = db.query(BOM).options(joinedload(BOM.lines)).filter(BOM.id == bom_id).first()
    if not bom:
        return Decimal("0")

    total = Decimal("0")

    for line in bom.lines:
        component = db.query(Product).filter(Product.id == line.component_id).first()
        if not component:
            continue

        qty = line.quantity or Decimal("0")
        scrap = line.scrap_factor or Decimal("0")
        effective_qty = qty * (1 + scrap / 100)

        # Check for sub-BOM
        sub_bom = (
            db.query(BOM)
            .filter(BOM.product_id == component.id, BOM.active.is_(True))
            .order_by(desc(BOM.version))
            .first()
        )

        if sub_bom:
            # Use rolled-up cost from sub-assembly
            sub_cost = calculate_rolled_up_cost(sub_bom.id, db, visited.copy())
            total += sub_cost * effective_qty
        elif component.cost:
            # Use component's direct cost
            total += component.cost * effective_qty

    return total


@router.get("/{bom_id}/explode")
async def explode_bom(
    bom_id: int,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
    max_depth: int = Query(10, ge=1, le=20),
    flatten: bool = Query(False, description="If true, aggregate quantities for duplicate components"),
):
    """
    Explode a BOM to show all components at all levels.

    This recursively expands sub-assemblies to show the full material requirements.

    - **max_depth**: Maximum levels to expand (default 10, max 20)
    - **flatten**: If true, consolidates duplicate components into single rows with summed quantities
    """
    bom = db.query(BOM).options(joinedload(BOM.product)).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")

    exploded = explode_bom_recursive(bom_id, db, max_depth=max_depth)

    # Check for errors
    errors = [e for e in exploded if isinstance(e, dict) and e.get("error")]
    if errors:
        return {
            "bom_id": bom_id,
            "product_sku": bom.product.sku if bom.product else None,
            "product_name": bom.product.name if bom.product else None,
            "errors": errors,
            "components": [c for c in exploded if not c.get("error")],
        }

    # Optionally flatten/aggregate
    if flatten:
        aggregated = {}
        for comp in exploded:
            key = comp["component_id"]
            if key in aggregated:
                aggregated[key]["effective_quantity"] += comp["effective_quantity"]
                aggregated[key]["line_cost"] += comp["line_cost"]
            else:
                aggregated[key] = comp.copy()
                aggregated[key]["level"] = "aggregated"
        exploded = list(aggregated.values())

    # Calculate totals
    total_cost = sum(c.get("line_cost", 0) for c in exploded if not c.get("is_sub_assembly"))
    rolled_up_cost = float(calculate_rolled_up_cost(bom_id, db))

    # Unique components (by component_id)
    unique_ids = set(c.get("component_id") for c in exploded)

    # Transform component data for frontend compatibility
    lines = []
    for comp in exploded:
        lines.append({
            "level": comp.get("level", 0),
            "component_id": comp.get("component_id"),
            "component_sku": comp.get("component_sku"),
            "component_name": comp.get("component_name"),
            "component_unit": comp.get("component_unit"),
            "quantity_per_unit": comp.get("base_quantity", 0),
            "extended_quantity": comp.get("effective_quantity", 0),
            "unit_cost": comp.get("component_cost", 0),
            "line_cost": comp.get("line_cost", 0),
            "is_sub_assembly": comp.get("is_sub_assembly", False),
            "sub_bom_id": comp.get("sub_bom_id"),
            "inventory_available": comp.get("inventory_available", 0),
            "parent_bom_id": comp.get("parent_bom_id"),
        })

    return {
        "bom_id": bom_id,
        "product_sku": bom.product.sku if bom.product else None,
        "product_name": bom.product.name if bom.product else None,
        "max_depth": max(c.get("level", 0) for c in exploded) if exploded else 0,
        "total_components": len(exploded),
        "unique_components": len(unique_ids),
        "leaf_component_count": len([c for c in exploded if not c.get("is_sub_assembly")]),
        "total_cost": rolled_up_cost,
        "total_leaf_cost": total_cost,
        "lines": lines,
        # Keep legacy fields for backwards compat
        "components": exploded,
    }


@router.get("/{bom_id}/cost-rollup")
async def get_cost_rollup(
    bom_id: int,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Builds a detailed cost breakdown for a BOM with nested sub-assembly costs rolled up.
    
    Calculates each BOM line's effective quantity (quantity adjusted for scrap), determines unit cost from a nested sub-BOM when present or from the component's direct cost, and aggregates line costs into a rolled-up total.
    
    Parameters:
        bom_id (int): ID of the BOM to analyze.
    
    Returns:
        dict: Summary and breakdown containing:
            - bom_id (int): The analyzed BOM id.
            - product_sku (str|None): SKU of the BOM's product.
            - product_name (str|None): Name of the BOM's product.
            - stored_cost (float): BOM.total_cost stored in the database (0 if missing).
            - rolled_up_cost (float): Sum of computed line costs including sub-assemblies.
            - cost_difference (float): rolled_up_cost minus stored_cost.
            - has_sub_assemblies (bool): Whether any lines reference sub-assemblies.
            - sub_assembly_count (int): Number of lines that are sub-assemblies.
            - direct_cost (float): Sum of line costs that use direct component cost.
            - sub_assembly_cost (float): Sum of line costs that come from sub-assemblies.
            - breakdown (list[dict]): Per-line items with:
                - component_id (int)
                - component_sku (str)
                - component_name (str)
                - quantity (float)
                - effective_quantity (float)
                - unit_cost (float): Unit cost used (sub-BOM rolled-up cost or component cost or 0).
                - line_cost (float)
                - cost_source (str): One of "sub_assembly", "direct", or "missing".
                - is_sub_assembly (bool)
                - sub_bom_id (int|None)
    """
    bom = db.query(BOM).options(joinedload(BOM.product), joinedload(BOM.lines)).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")

    breakdown = []
    total = Decimal("0")

    for line in bom.lines:
        component = db.query(Product).filter(Product.id == line.component_id).first()
        if not component:
            continue

        qty = line.quantity or Decimal("0")
        scrap = line.scrap_factor or Decimal("0")
        effective_qty = qty * (1 + scrap / 100)

        # Check for sub-BOM
        sub_bom = (
            db.query(BOM)
            .filter(BOM.product_id == component.id, BOM.active.is_(True))
            .order_by(desc(BOM.version))
            .first()
        )

        if sub_bom:
            sub_cost = calculate_rolled_up_cost(sub_bom.id, db)
            line_cost = sub_cost * effective_qty
            cost_source = "sub_assembly"
        elif component.cost:
            line_cost = component.cost * effective_qty
            cost_source = "direct"
        else:
            line_cost = Decimal("0")
            cost_source = "missing"

        total += line_cost

        breakdown.append({
            "component_id": component.id,
            "component_sku": component.sku,
            "component_name": component.name,
            "quantity": float(qty),
            "effective_quantity": float(effective_qty),
            "unit_cost": float(sub_cost if sub_bom else (component.cost or 0)),
            "line_cost": float(line_cost),
            "cost_source": cost_source,
            "is_sub_assembly": sub_bom is not None,
            "sub_bom_id": sub_bom.id if sub_bom else None,
        })

    # Calculate sub-assembly totals
    sub_assembly_items = [b for b in breakdown if b["is_sub_assembly"]]
    direct_items = [b for b in breakdown if not b["is_sub_assembly"]]

    return {
        "bom_id": bom_id,
        "product_sku": bom.product.sku if bom.product else None,
        "product_name": bom.product.name if bom.product else None,
        "stored_cost": float(bom.total_cost) if bom.total_cost else 0,
        "rolled_up_cost": float(total),
        "cost_difference": float(total - (bom.total_cost or 0)),
        # Additional summary fields for UI
        "has_sub_assemblies": len(sub_assembly_items) > 0,
        "sub_assembly_count": len(sub_assembly_items),
        "direct_cost": sum(b["line_cost"] for b in direct_items),
        "sub_assembly_cost": sum(b["line_cost"] for b in sub_assembly_items),
        "breakdown": breakdown,
    }


@router.get("/where-used/{product_id}")
async def where_used(
    product_id: int,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
    include_inactive: bool = False,
):
    """
    Finds all BOMs that reference the given product as a component and summarizes usage.
    
    Parameters:
        include_inactive (bool): If True, include BOMs that are not active.
    
    Returns:
        dict: {
            "component_id": int,
            "component_sku": str or None,
            "component_name": str or None,
            "used_in_count": int,              # number of distinct BOMs using the component
            "used_in": [                       # list of usage summaries, one per BOM
                {
                    "bom_id": int,
                    "bom_code": str or None,
                    "product_id": int or None,
                    "product_sku": str or None,
                    "product_name": str or None,
                    "active": bool,
                    "quantity_used": float,    # aggregated quantity of the component in that BOM
                    "line_id": int             # id of the first matching BOM line encountered
                },
                ...
            ]
        }
    
    Raises:
        HTTPException: 404 if the component product is not found.
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Find all BOM lines using this component
    query = (
        db.query(BOMLine)
        .join(BOM)
        .options(joinedload(BOMLine.bom).joinedload(BOM.product))
        .filter(BOMLine.component_id == product_id)
    )

    if not include_inactive:
        query = query.filter(BOM.active.is_(True))

    lines = query.all()

    # Group by BOM
    bom_usage = {}
    for line in lines:
        bom = line.bom
        if bom.id not in bom_usage:
            bom_usage[bom.id] = {
                "bom_id": bom.id,
                "bom_code": bom.code,
                "product_id": bom.product_id,
                "product_sku": bom.product.sku if bom.product else None,
                "product_name": bom.product.name if bom.product else None,
                "active": bom.active,
                "quantity_used": float(line.quantity) if line.quantity else 0,
                "line_id": line.id,
            }
        else:
            # Same component appears multiple times in same BOM
            bom_usage[bom.id]["quantity_used"] += float(line.quantity) if line.quantity else 0

    return {
        "component_id": product_id,
        "component_sku": product.sku,
        "component_name": product.name,
        "used_in_count": len(bom_usage),
        "used_in": list(bom_usage.values()),
    }


@router.post("/{bom_id}/validate")
async def validate_bom(
    bom_id: int,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Validate a BOM for structural and data issues such as missing components, missing costs, invalid quantities, and circular references.
    
    Returns:
        A dictionary with validation results:
        - `bom_id` (int): The validated BOM id.
        - `product_sku` (str|None): SKU of the BOM's product when available.
        - `is_valid` (bool): `true` if no errors were found, `false` otherwise.
        - `error_count` (int): Number of issues with severity "error".
        - `warning_count` (int): Number of issues with severity "warning".
        - `issues` (list): Array of issue objects; each contains:
            - `severity` (str): "error" or "warning".
            - `code` (str): Short machine-readable issue code (e.g., "missing_component", "missing_cost", "invalid_quantity", "circular_reference").
            - `message` (str): Human-readable description of the issue.
            - Optional context fields such as `line_id`, `component_id`, or `bom_id` when applicable.
    """
    bom = db.query(BOM).options(joinedload(BOM.product), joinedload(BOM.lines)).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")

    issues = []

    # Check for empty BOM
    if not bom.lines:
        issues.append({
            "severity": "warning",
            "code": "empty_bom",
            "message": "BOM has no components"
        })

    # Check each line
    for line in bom.lines:
        component = db.query(Product).filter(Product.id == line.component_id).first()

        if not component:
            issues.append({
                "severity": "error",
                "code": "missing_component",
                "message": f"Component ID {line.component_id} not found",
                "line_id": line.id
            })
            continue

        # Missing cost
        if not component.cost:
            # Check if it's a sub-assembly
            sub_bom = db.query(BOM).filter(
                BOM.product_id == component.id,
                BOM.active.is_(True)
            ).first()

            if not sub_bom:
                issues.append({
                    "severity": "warning",
                    "code": "missing_cost",
                    "message": f"Component {component.sku} has no cost defined",
                    "component_id": component.id,
                    "line_id": line.id
                })

        # Zero quantity
        if not line.quantity or line.quantity <= 0:
            issues.append({
                "severity": "error",
                "code": "invalid_quantity",
                "message": f"Line for {component.sku} has invalid quantity",
                "line_id": line.id
            })

    # Check for circular references
    exploded = explode_bom_recursive(bom_id, db, max_depth=15)
    circular_errors = [e for e in exploded if isinstance(e, dict) and e.get("error") == "circular_reference"]

    for err in circular_errors:
        issues.append({
            "severity": "error",
            "code": "circular_reference",
            "message": err.get("message", "Circular reference detected"),
            "bom_id": err.get("bom_id")
        })

    return {
        "bom_id": bom_id,
        "product_sku": bom.product.sku if bom.product else None,
        "is_valid": not any(i["severity"] == "error" for i in issues),
        "error_count": len([i for i in issues if i["severity"] == "error"]),
        "warning_count": len([i for i in issues if i["severity"] == "warning"]),
        "issues": issues,
    }