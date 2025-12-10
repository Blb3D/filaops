"""
Inventory API Endpoints

These endpoints handle material availability checks
and inventory transactions for the integration.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.logging_config import get_logger
from app.models.inventory import Inventory, InventoryTransaction, InventoryLocation
from app.models.product import Product

router = APIRouter()
logger = get_logger(__name__)

class InventoryCheckRequest(BaseModel):
    """Request to check inventory availability"""
    material_type: str
    required_quantity: float  # in kg

class InventoryLocationRequest(BaseModel):
    """Inventory location details"""
    location: str
    quantity: float

class InventoryCheckResponse(BaseModel):
    """Inventory availability response"""
    available: bool
    on_hand_quantity: float
    allocated_quantity: float
    available_quantity: float
    locations: List[InventoryLocationRequest]


@router.post("/check", response_model=InventoryCheckResponse)
async def check_inventory_availability(
    request: InventoryCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Check if material is available for printing

    Called by Bambu Print Suite before starting a print job
    to ensure sufficient material is in stock.
    """
    try:
        logger.info(f"Checking availability for {request.material_type}: {request.required_quantity} kg")

        # Find the product (material) by SKU or name
        product = db.query(Product).filter(
            (Product.sku == request.material_type) |
            (Product.name.like(f"%{request.material_type}%"))
        ).filter(Product.is_raw_material.is_(True)).first()

        if not product:
            # Material not found - return zero availability
            logger.warning(f"Material {request.material_type} not found in database")
            return InventoryCheckResponse(
                available=False,
                on_hand_quantity=0.0,
                allocated_quantity=0.0,
                available_quantity=0.0,
                locations=[]
            )

        # Query inventory for this product across all locations
        inventory_items = db.query(Inventory).filter(Inventory.product_id == product.id).all()

        # Calculate totals
        total_on_hand = sum(float(item.on_hand_quantity) for item in inventory_items)
        total_allocated = sum(float(item.allocated_quantity) for item in inventory_items)
        total_available = sum(float(item.available_quantity) for item in inventory_items)

        # Check if sufficient quantity is available
        is_available = total_available >= request.required_quantity

        # Build location list (simplified - using location_id as location name for now)
        locations = [
            InventoryLocationRequest(
                location=f"LOC-{item.location_id}",
                quantity=float(item.available_quantity)
            )
            for item in inventory_items if float(item.available_quantity) > 0
        ]

        return InventoryCheckResponse(
            available=is_available,
            on_hand_quantity=total_on_hand,
            allocated_quantity=total_allocated,
            available_quantity=total_available,
            locations=locations
        )

    except Exception as e:
        logger.error(f"Failed to check inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class InventoryTransactionRequest(BaseModel):
    """Request to create inventory transaction"""
    transaction_type: str  # consumption, receipt, adjustment
    reference_type: str  # print_job, sales_order, etc.
    reference_id: str
    product_sku: str
    quantity: float  # in kg
    location: str
    notes: Optional[str] = None

@router.post("/transactions")
async def create_inventory_transaction(
    transaction_req: InventoryTransactionRequest,
    db: Session = Depends(get_db)
):
    """
    Create an inventory transaction

    Called by Bambu Print Suite when material is consumed during printing,
    or when print jobs are completed to update inventory levels.
    """
    try:
        logger.info(
            f"Creating {transaction_req.transaction_type} transaction for "
            f"{transaction_req.product_sku}: {transaction_req.quantity} kg"
        )

        # Find the product
        product = db.query(Product).filter(Product.sku == transaction_req.product_sku).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {transaction_req.product_sku} not found")

        # Create the inventory transaction
        transaction = InventoryTransaction(
            product_id=product.id,
            transaction_type=transaction_req.transaction_type,
            reference_type=transaction_req.reference_type,
            reference_id=int(transaction_req.reference_id) if transaction_req.reference_id.isdigit() else None,
            quantity=transaction_req.quantity,
            to_location=transaction_req.location if transaction_req.transaction_type == 'receipt' else None,
            from_location=transaction_req.location if transaction_req.transaction_type == 'consumption' else None,
            notes=transaction_req.notes,
            transaction_date=datetime.utcnow()
        )

        db.add(transaction)

        # Update inventory quantities based on transaction type
        # Find or get default location
        location = None
        if transaction_req.location:
            # Try to find location by code or name
            location = db.query(InventoryLocation).filter(
                (InventoryLocation.code == transaction_req.location) |
                (InventoryLocation.name == transaction_req.location)
            ).first()
        
        # Fallback to default location (MAIN or first available)
        if not location:
            location = db.query(InventoryLocation).filter(
                InventoryLocation.code == 'MAIN'
            ).first()
            if not location:
                location = db.query(InventoryLocation).filter(
                    InventoryLocation.active.is_(True)
                ).first()
        
        # If still no location, create a default one
        if not location:
            location = InventoryLocation(
                code="MAIN",
                name="Main Warehouse",
                type="warehouse",
                active=True
            )
            db.add(location)
            db.flush()
        
        # Find or create inventory for this product at this location
        inventory = db.query(Inventory).filter(
            Inventory.product_id == product.id,
            Inventory.location_id == location.id
        ).first()

        # Create inventory record if it doesn't exist
        if not inventory:
            inventory = Inventory(
                product_id=product.id,
                location_id=location.id,
                on_hand_quantity=0.0,
                allocated_quantity=0.0,
            )
            db.add(inventory)
            db.flush()

        if inventory:
            if transaction_req.transaction_type == 'consumption':
                # Decrease on-hand and available quantities
                inventory.on_hand_quantity = float(inventory.on_hand_quantity) - transaction_req.quantity
                inventory.available_quantity = float(inventory.available_quantity) - transaction_req.quantity

            elif transaction_req.transaction_type == 'receipt':
                # Increase on-hand and available quantities
                inventory.on_hand_quantity = float(inventory.on_hand_quantity) + transaction_req.quantity
                inventory.available_quantity = float(inventory.available_quantity) + transaction_req.quantity

            elif transaction_req.transaction_type == 'adjustment':
                # Set to exact quantity (transaction.quantity is the new total)
                inventory.on_hand_quantity = transaction_req.quantity
                inventory.available_quantity = transaction_req.quantity - float(inventory.allocated_quantity)

        db.commit()
        db.refresh(transaction)

        return {
            "transaction_id": transaction.id,
            "status": "success",
            "created_at": transaction.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create inventory transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/materials")
async def list_materials(db: Session = Depends(get_db)):
    """
    List all available materials

    Returns materials that can be used for 3D printing,
    used by Bambu Print Suite for material selection.
    """
    try:
        # Query products table for raw materials
        materials = db.query(Product).filter(
            Product.is_raw_material.is_(True),
            Product.active.is_(True)
        ).all()

        # Get inventory quantities for each material
        result_materials = []
        for material in materials:
            # Get total on-hand quantity across all locations
            inventory_items = db.query(Inventory).filter(
                Inventory.product_id == material.id
            ).all()

            total_on_hand = sum(float(item.on_hand_quantity) for item in inventory_items)

            # Parse material type from SKU or name (simplified)
            material_type = "PLA"  # Default
            if "PLA" in material.name.upper():
                material_type = "PLA"
            elif "PETG" in material.name.upper():
                material_type = "PETG"
            elif "ABS" in material.name.upper():
                material_type = "ABS"
            elif "TPU" in material.name.upper():
                material_type = "TPU"

            result_materials.append({
                "sku": material.sku,
                "name": material.name,
                "type": material_type,
                "on_hand": total_on_hand,
                "cost_per_kg": float(material.cost) if material.cost else 0.0
            })

        return {"materials": result_materials}

    except Exception as e:
        logger.error(f"Failed to list materials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
