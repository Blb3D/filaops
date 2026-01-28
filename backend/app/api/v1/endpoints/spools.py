"""
Material Spool API Endpoints

Handles CRUD operations for filament spools and spool usage tracking.
"""

# pyright: reportArgumentType=false
# pyright: reportAssignmentType=false
# SQLAlchemy Column types resolve to actual values at runtime
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models import User, MaterialSpool, ProductionOrderSpool, Product
from app.models.production_order import ProductionOrder
from app.models.inventory import InventoryTransaction, Inventory
from app.services.inventory_helpers import is_material
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/spools", tags=["spools"])


@router.get("/")
async def list_spools(
    product_id: Optional[int] = Query(None, description="Filter by product/material"),
    status: Optional[str] = Query(None, description="Filter by status (active, empty, expired, damaged)"),
    location_id: Optional[int] = Query(None, description="Filter by location"),
    low_weight: bool = Query(False, description="Show only low weight spools (< 10%)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all material spools with optional filters.
    """
    query = db.query(MaterialSpool).join(Product)

    if product_id:
        query = query.filter(MaterialSpool.product_id == product_id)
    if status:
        query = query.filter(MaterialSpool.status == status)
    if location_id:
        query = query.filter(MaterialSpool.location_id == location_id)
    if low_weight:
        # Filter for spools with < 10% remaining
        # Calculate percentage: (current / initial) * 100 < 10
        # Simplified: current < initial * 0.1
        query = query.filter(
            MaterialSpool.status == "active",
            MaterialSpool.current_weight_kg < (MaterialSpool.initial_weight_kg * Decimal("0.1")),
        )

    total = query.count()
    spools = query.order_by(desc(MaterialSpool.created_at)).offset(offset).limit(limit).all()

    return {
        "items": [
            {
                "id": spool.id,
                "spool_number": spool.spool_number,
                "product_id": spool.product_id,
                "product_sku": spool.product.sku if spool.product else None,
                "product_name": spool.product.name if spool.product else None,
                "initial_weight_kg": float(spool.initial_weight_kg or 0),
                "current_weight_kg": float(spool.current_weight_kg or 0),
                "weight_remaining_percent": float(spool.weight_remaining_percent)
                if hasattr(spool, "weight_remaining_percent")
                else 0,
                "status": str(spool.status) if spool.status else "active",
                "received_date": spool.received_date.isoformat() if spool.received_date else None,  # type: ignore[union-attr]
                "expiry_date": spool.expiry_date.isoformat() if spool.expiry_date else None,  # type: ignore[union-attr]
                "location_id": spool.location_id,
                "location_name": spool.location.name if spool.location else None,
                "supplier_lot_number": spool.supplier_lot_number,
                "notes": spool.notes,
                "is_low": bool(spool.is_low) if hasattr(spool, "is_low") else False,
                "is_empty": bool(spool.is_empty) if hasattr(spool, "is_empty") else False,
                "created_at": spool.created_at.isoformat() if spool.created_at else None,  # type: ignore[union-attr]
                "updated_at": spool.updated_at.isoformat() if spool.updated_at else None,  # type: ignore[union-attr]
            }
            for spool in spools
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{spool_id}")
async def get_spool(
    spool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get details for a specific spool including usage history.
    """
    spool = db.query(MaterialSpool).filter(MaterialSpool.id == spool_id).first()
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")

    # Get usage history
    usage_history = (
        db.query(ProductionOrderSpool)
        .filter(ProductionOrderSpool.spool_id == spool_id)
        .order_by(desc(ProductionOrderSpool.created_at))
        .all()
    )

    return {
        "id": spool.id,
        "spool_number": spool.spool_number,
        "product_id": spool.product_id,
        "product_sku": spool.product.sku if spool.product else None,
        "product_name": spool.product.name if spool.product else None,
        "initial_weight_kg": float(spool.initial_weight_kg or 0),
        "current_weight_kg": float(spool.current_weight_kg or 0),
        "weight_remaining_percent": float(spool.weight_remaining_percent)
        if hasattr(spool, "weight_remaining_percent")
        else 0,
        "status": str(spool.status) if spool.status else "active",  # type: ignore[arg-type]
        "received_date": spool.received_date.isoformat() if spool.received_date else None,  # type: ignore[union-attr]
        "expiry_date": spool.expiry_date.isoformat() if spool.expiry_date else None,  # type: ignore[union-attr]
        "location_id": spool.location_id,
        "location_name": spool.location.name if spool.location else None,
        "supplier_lot_number": spool.supplier_lot_number,
        "notes": spool.notes,
        "is_low": bool(spool.is_low) if hasattr(spool, "is_low") else False,
        "is_empty": bool(spool.is_empty) if hasattr(spool, "is_empty") else False,
        "created_at": spool.created_at.isoformat() if spool.created_at else None,  # type: ignore[union-attr]
        "updated_at": spool.updated_at.isoformat() if spool.updated_at else None,  # type: ignore[union-attr]
        "usage_history": [
            {
                "production_order_id": usage.production_order_id,
                "production_order_code": usage.production_order.code if usage.production_order else None,
                "weight_consumed_kg": float(usage.weight_consumed_kg or 0),
                "created_at": usage.created_at.isoformat() if usage.created_at else None,  # type: ignore[union-attr]
            }
            for usage in usage_history
        ],
    }


@router.post("/")
async def create_spool(
    spool_number: str = Query(..., description="Unique spool identifier"),
    product_id: int = Query(..., description="Product/material ID"),
    initial_weight_kg: float = Query(..., description="Initial weight (grams)"),
    current_weight_kg: Optional[float] = Query(None, description="Current weight in grams (defaults to initial)"),
    location_id: Optional[int] = Query(None, description="Storage location"),
    supplier_lot_number: Optional[str] = Query(None, description="Supplier lot/batch number"),
    expiry_date: Optional[datetime] = Query(None, description="Material expiry date"),
    notes: Optional[str] = Query(None, description="Additional notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new material spool.
    """
    # Check if spool number already exists
    existing = db.query(MaterialSpool).filter(MaterialSpool.spool_number == spool_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Spool number {spool_number} already exists")

    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Use initial weight as current if not specified
    if current_weight_kg is None:
        current_weight_kg = initial_weight_kg

    spool = MaterialSpool(
        spool_number=spool_number,
        product_id=product_id,
        initial_weight_kg=Decimal(str(initial_weight_kg)),
        current_weight_kg=Decimal(str(current_weight_kg)),
        status="active",
        location_id=location_id,
        supplier_lot_number=supplier_lot_number,
        expiry_date=expiry_date,
        notes=notes,
        created_by=current_user.email if current_user else None,
    )

    db.add(spool)
    db.commit()
    db.refresh(spool)

    logger.info(
        f"Created spool {spool_number} for product {product_id} by {current_user.email if current_user else 'system'}"
    )

    return {
        "id": spool.id,
        "spool_number": spool.spool_number,
        "message": "Spool created successfully",
    }


@router.patch("/{spool_id}")
async def update_spool(
    spool_id: int,
    current_weight_g: Optional[float] = Query(None, description="Update current weight (grams)"),
    status: Optional[str] = Query(None, description="Update status"),
    location_id: Optional[int] = Query(None, description="Update location"),
    notes: Optional[str] = Query(None, description="Update notes"),
    reason: Optional[str] = Query(None, description="Reason for weight adjustment (required if adjusting weight)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update spool information (weight, status, location, notes).

    When updating weight, this creates an inventory adjustment transaction
    and updates the product's inventory level to maintain accuracy.
    """
    spool = db.query(MaterialSpool).filter(MaterialSpool.id == spool_id).first()
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")

    transaction_created = None

    # Handle weight adjustment with inventory transaction
    if current_weight_g is not None:
        if not reason:
            raise HTTPException(
                status_code=400,
                detail="Reason required when adjusting spool weight (e.g., 'Physical inventory count', 'Correction', 'Damaged material')",
            )

        old_weight_g = Decimal(spool.current_weight_kg or 0)  # Actually in grams
        new_weight_g = Decimal(str(current_weight_g))
        adjustment_g = new_weight_g - old_weight_g

        if adjustment_g != 0:
            # Get product for cost calculation and material check
            product = db.query(Product).filter(Product.id == spool.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found for spool")

            # For materials: Store transaction in GRAMS (star schema - transactions are source of truth)
            is_mat = is_material(product)
            transaction_quantity = float(adjustment_g) if is_mat else float(adjustment_g / Decimal("1000"))

            # Cost calculation: Use cost per inventory unit for correct total_cost calculation
            # For materials: $/gram. For others: $/unit
            from app.services.inventory_service import get_effective_cost_per_inventory_unit

            cost_per_unit = None
            total_cost = None
            if product:
                cost_per_unit = get_effective_cost_per_inventory_unit(product)
                if cost_per_unit:
                    total_cost = abs(transaction_quantity) * float(cost_per_unit)

            # Create inventory adjustment transaction
            # For materials: quantity in GRAMS, cost_per_unit in $/gram
            transaction = InventoryTransaction(
                product_id=spool.product_id,
                location_id=spool.location_id,  # Link to spool's location
                transaction_type="adjustment",
                quantity=transaction_quantity,  # GRAMS for materials, product_unit for others
                cost_per_unit=cost_per_unit,  # Cost per inventory unit ($/gram for materials)
                total_cost=total_cost,  # Pre-calculated for UI display
                reference_type="spool_adjustment",
                reference_id=str(spool.id),
                notes=f"Spool {spool.spool_number} weight adjusted: {float(old_weight_g)}g → {float(new_weight_g)}g. Reason: {reason}",
                created_by=current_user.email if current_user else "system",
                created_at=datetime.utcnow(),
            )
            db.add(transaction)
            db.flush()

            transaction_created = transaction.id

            # Update inventory record for this product/location
            # For materials: Store in GRAMS
            logger.info(
                f"Updating inventory for spool {spool.spool_number}: "
                f"product_id={spool.product_id}, location_id={spool.location_id}, "
                f"adjustment={float(adjustment_g):+.1f}g (material: {is_mat})"
            )

            if spool.location_id:
                inventory = (
                    db.query(Inventory)
                    .filter(Inventory.product_id == spool.product_id, Inventory.location_id == spool.location_id)
                    .first()
                )

                if inventory:
                    old_qty = Decimal(inventory.on_hand_quantity or 0)
                    # For materials: Store in grams. For others: Store in product unit
                    new_qty = old_qty + Decimal(str(transaction_quantity))
                    inventory.on_hand_quantity = float(new_qty)  # type: ignore[assignment]
                    inventory.updated_at = datetime.utcnow()  # type: ignore[assignment]
                    db.flush()  # Ensure inventory update is in session

                    unit_label = "g" if is_mat else "KG"
                    logger.info(
                        f"Inventory adjusted for {product.sku} at location {spool.location_id}: "
                        f"{float(old_qty):.1f}{unit_label} → {float(new_qty):.1f}{unit_label} "
                        f"(adjustment: {float(adjustment_g):+.1f}g) "
                        f"due to spool {spool.spool_number} adjustment"
                    )
                else:
                    # Create inventory record if it doesn't exist
                    old_qty = Decimal("0")
                    new_qty = Decimal(str(transaction_quantity))
                    inventory = Inventory(
                        product_id=spool.product_id,
                        location_id=spool.location_id,
                        on_hand_quantity=float(new_qty),
                        allocated_quantity=0,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(inventory)
                    db.flush()  # Ensure inventory creation is in session
                    unit_label = "g" if is_mat else "KG"
                    logger.info(
                        f"Created inventory record for {product.sku} at location {spool.location_id}: "
                        f"{float(new_qty):.1f}{unit_label} (adjustment: {float(adjustment_g):+.1f}g) "
                        f"due to spool {spool.spool_number} adjustment"
                    )
            else:
                logger.warning(
                    f"Spool {spool.spool_number} has no location. Transaction created but inventory not updated. "
                    f"Please assign a location to the spool to enable inventory tracking."
                )

        # Update spool weight
        spool.current_weight_kg = new_weight_g  # type: ignore[assignment]

        # Auto-mark as empty if weight is very low (< 50g)
        if new_weight_g < Decimal("50"):
            spool.status = "empty"  # type: ignore[assignment]
            logger.info(f"Spool {spool.spool_number} automatically marked as empty (weight: {float(new_weight_g)}g)")

    # Handle other updates
    if status:
        spool.status = status  # type: ignore[assignment]

    if location_id is not None:
        spool.location_id = location_id  # type: ignore[assignment]

    if notes is not None:
        spool.notes = notes  # type: ignore[assignment]

    spool.updated_at = datetime.utcnow()  # type: ignore[assignment]

    db.commit()
    db.refresh(spool)

    # Verify inventory was updated (for debugging)
    if transaction_created and spool.location_id:
        verify_inv = (
            db.query(Inventory)
            .filter(Inventory.product_id == spool.product_id, Inventory.location_id == spool.location_id)
            .first()
        )
        if verify_inv:
            logger.info(
                f"Verified inventory update: product_id={spool.product_id}, location_id={spool.location_id}, "
                f"on_hand_quantity={verify_inv.on_hand_quantity}"
            )
        else:
            logger.warning(
                f"Inventory record not found after commit for product_id={spool.product_id}, location_id={spool.location_id}"
            )

    logger.info(f"Updated spool {spool.spool_number} by {current_user.email if current_user else 'system'}")

    return {
        "id": spool.id,
        "spool_number": spool.spool_number,
        "current_weight_kg": float(spool.current_weight_kg or 0),
        "status": str(spool.status) if spool.status else "active",  # type: ignore[arg-type]
        "transaction_id": transaction_created,
        "message": "Spool updated successfully" + (" with inventory adjustment" if transaction_created else ""),
    }


@router.get("/product/{product_id}/available")
async def get_available_spools(
    product_id: int,
    min_weight_kg: Optional[float] = Query(None, description="Minimum weight required"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get available spools for a product, optionally filtered by minimum weight.
    Useful for production spool selection.
    """
    query = db.query(MaterialSpool).filter(MaterialSpool.product_id == product_id, MaterialSpool.status == "active")

    if min_weight_kg:
        query = query.filter(MaterialSpool.current_weight_kg >= Decimal(str(min_weight_kg)))

    spools = query.order_by(desc(MaterialSpool.current_weight_kg)).all()

    return {
        "product_id": product_id,
        "spools": [
            {
                "id": spool.id,
                "spool_number": spool.spool_number,
                "current_weight_kg": float(spool.current_weight_kg or 0),
                "weight_remaining_percent": float(spool.weight_remaining_percent)
                if hasattr(spool, "weight_remaining_percent")
                else 0,
                "location_name": spool.location.name if spool.location else None,
                "supplier_lot_number": spool.supplier_lot_number,
            }
            for spool in spools
        ],
    }


@router.get("/traceability/production-order/{production_order_id}")
async def get_spool_traceability_for_order(
    production_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get spool traceability information for a production order.
    Shows which spools were used and how much material was consumed.
    """
    order = db.query(ProductionOrder).filter(ProductionOrder.id == production_order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")

    # Get spools used for this order
    spool_usage = (
        db.query(ProductionOrderSpool).filter(ProductionOrderSpool.production_order_id == production_order_id).all()
    )

    traceability_data = []
    for usage in spool_usage:
        spool = db.query(MaterialSpool).filter(MaterialSpool.id == usage.spool_id).first()
        if spool:
            traceability_data.append(
                {
                    "spool_id": spool.id,
                    "spool_number": spool.spool_number,
                    "product_id": spool.product_id,
                    "product_sku": spool.product.sku if spool.product else None,
                    "product_name": spool.product.name if spool.product else None,
                    "weight_consumed_kg": float(usage.weight_consumed_kg or 0),
                    "supplier_lot_number": spool.supplier_lot_number,
                    "consumed_at": usage.created_at.isoformat() if usage.created_at else None,  # type: ignore[union-attr]
                }
            )

    return {
        "production_order_id": production_order_id,
        "production_order_code": order.code,
        "spools_used": traceability_data,
        "total_spools": len(traceability_data),
    }


@router.get("/traceability/spool/{spool_id}")
async def get_spool_traceability(
    spool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get full traceability for a spool: which production orders used it, which finished goods were produced.
    """
    spool = db.query(MaterialSpool).filter(MaterialSpool.id == spool_id).first()
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")

    # Get all production orders that used this spool
    usage_records = (
        db.query(ProductionOrderSpool)
        .filter(ProductionOrderSpool.spool_id == spool_id)
        .order_by(desc(ProductionOrderSpool.created_at))
        .all()
    )

    traceability = []
    total_weight_consumed = Decimal("0")

    for usage in usage_records:
        po = db.query(ProductionOrder).filter(ProductionOrder.id == usage.production_order_id).first()
        if po:
            product = db.query(Product).filter(Product.id == po.product_id).first()
            total_weight_consumed += usage.weight_consumed_kg or Decimal("0")

            traceability.append(
                {
                    "production_order_id": po.id,
                    "production_order_code": po.code,
                    "product_id": po.product_id,
                    "product_sku": product.sku if product else None,
                    "product_name": product.name if product else None,
                    "quantity_produced": float(po.quantity_completed or 0),
                    "weight_consumed_kg": float(usage.weight_consumed_kg or 0),
                    "consumed_at": usage.created_at.isoformat() if usage.created_at else None,  # type: ignore[union-attr]
                    "sales_order_id": po.sales_order_id,
                    "sales_order_code": po.sales_order.order_number if po.sales_order else None,
                }
            )

    return {
        "spool_id": spool.id,
        "spool_number": spool.spool_number,
        "product_id": spool.product_id,
        "product_sku": spool.product.sku if spool.product else None,
        "product_name": spool.product.name if spool.product else None,
        "initial_weight_kg": float(spool.initial_weight_kg or 0),
        "current_weight_kg": float(spool.current_weight_kg or 0),
        "total_weight_consumed_kg": float(total_weight_consumed),
        "supplier_lot_number": spool.supplier_lot_number,
        "production_orders": traceability,
        "total_production_orders": len(traceability),
    }


# ============================================================================
# Spool Consumption Recording
# ============================================================================


@router.post("/{spool_id}/consume")
async def consume_spool_for_production(
    spool_id: int,
    production_order_id: int,
    weight_consumed_g: float = Query(gt=0, description="Weight consumed in grams"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Record material consumption from a spool for a production order.

    This creates the traceability link between spools and production orders,
    enabling forward/backward traceability queries.

    Parameters:
    - spool_id: The spool being consumed from
    - production_order_id: The production order using the material
    - weight_consumed_g: Amount consumed in grams

    Returns updated spool info and consumption record.
    """
    # Validate spool exists and is active
    spool = db.query(MaterialSpool).filter(MaterialSpool.id == spool_id).first()
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")

    if spool.status != "active":
        raise HTTPException(status_code=400, detail=f"Cannot consume from spool with status '{spool.status}'")

    # Validate production order exists and is in-progress
    po = db.query(ProductionOrder).filter(ProductionOrder.id == production_order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")

    if po.status not in ("released", "in_progress"):
        raise HTTPException(
            status_code=400, detail=f"Cannot consume material for production order with status '{po.status}'"
        )

    # Check if consumption already recorded - update if so
    existing = (
        db.query(ProductionOrderSpool)
        .filter(
            ProductionOrderSpool.production_order_id == production_order_id,
            ProductionOrderSpool.spool_id == spool_id,
        )
        .first()
    )

    weight_consumed_kg = Decimal(str(weight_consumed_g))  # Field is in grams despite name

    if existing:
        # Update existing record
        existing.weight_consumed_kg = existing.weight_consumed_kg + weight_consumed_kg  # type: ignore[assignment]
        consumption = existing
    else:
        # Create new consumption record
        consumption = ProductionOrderSpool(
            production_order_id=production_order_id,
            spool_id=spool_id,
            weight_consumed_kg=weight_consumed_kg,
            created_by=current_user.email,
        )
        db.add(consumption)

    # Update spool's current weight
    new_weight = (spool.current_weight_kg or Decimal("0")) - weight_consumed_kg
    if new_weight < 0:
        new_weight = Decimal("0")
    spool.current_weight_kg = new_weight  # type: ignore[assignment]

    # Mark as empty if weight is effectively zero
    if new_weight < Decimal("5"):  # Less than 5g = empty
        spool.status = "empty"  # type: ignore[assignment]

    db.commit()
    db.refresh(consumption)
    db.refresh(spool)

    return {
        "message": "Consumption recorded successfully",
        "consumption": {
            "id": consumption.id,
            "production_order_id": consumption.production_order_id,
            "spool_id": consumption.spool_id,
            "weight_consumed_g": float(consumption.weight_consumed_kg or 0),
            "created_at": consumption.created_at.isoformat() if consumption.created_at else None,
        },
        "spool": {
            "id": spool.id,
            "spool_number": spool.spool_number,
            "current_weight_g": float(spool.current_weight_kg or 0),
            "status": spool.status,
        },
    }
