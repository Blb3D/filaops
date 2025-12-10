"""
Admin Inventory Transaction Endpoints

Provides admin interface for creating and managing inventory transactions:
- Receipts (PO receiving, manual receipts)
- Issues (production consumption, manual issues)
- Transfers (location-to-location)
- Adjustments (cycle counts, corrections)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.models.user import User
from app.models.inventory import Inventory, InventoryTransaction, InventoryLocation
from app.models.product import Product
from app.api.v1.deps import get_current_staff_user

router = APIRouter(prefix="/inventory/transactions", tags=["Admin - Inventory"])


# ============================================================================
# SCHEMAS
# ============================================================================

class TransactionCreate(BaseModel):
    """Create inventory transaction request"""
    product_id: int
    location_id: Optional[int] = None
    transaction_type: str  # receipt, issue, transfer, adjustment
    quantity: Decimal
    cost_per_unit: Optional[Decimal] = None
    reference_type: Optional[str] = None  # purchase_order, production_order, adjustment, etc.
    reference_id: Optional[int] = None
    lot_number: Optional[str] = None
    serial_number: Optional[str] = None
    notes: Optional[str] = None
    # For transfers
    to_location_id: Optional[int] = None


class TransactionResponse(BaseModel):
    """Inventory transaction response"""
    id: int
    product_id: int
    product_sku: str
    product_name: str
    location_id: Optional[int]
    location_name: Optional[str]
    transaction_type: str
    quantity: Decimal
    cost_per_unit: Optional[Decimal]
    total_cost: Optional[Decimal]
    reference_type: Optional[str]
    reference_id: Optional[int]
    lot_number: Optional[str]
    serial_number: Optional[str]
    notes: Optional[str]
    created_at: datetime
    created_by: Optional[str]
    # For transfers
    to_location_id: Optional[int]
    to_location_name: Optional[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("", response_model=List[TransactionResponse])
async def list_transactions(
    product_id: Optional[int] = Query(None, description="Filter by product"),
    transaction_type: Optional[str] = Query(None, description="Filter by type"),
    location_id: Optional[int] = Query(None, description="Filter by location"),
    reference_type: Optional[str] = Query(None, description="Filter by reference type"),
    reference_id: Optional[int] = Query(None, description="Filter by reference ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """List inventory transactions with filters"""
    query = db.query(InventoryTransaction).join(Product)
    
    if product_id:
        query = query.filter(InventoryTransaction.product_id == product_id)
    if transaction_type:
        query = query.filter(InventoryTransaction.transaction_type == transaction_type)
    if location_id:
        query = query.filter(InventoryTransaction.location_id == location_id)
    if reference_type:
        query = query.filter(InventoryTransaction.reference_type == reference_type)
    if reference_id:
        query = query.filter(InventoryTransaction.reference_id == reference_id)
    
    transactions = query.order_by(desc(InventoryTransaction.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for txn in transactions:
        product = db.query(Product).filter(Product.id == txn.product_id).first()
        location = db.query(InventoryLocation).filter(InventoryLocation.id == txn.location_id).first() if txn.location_id else None
        to_location = db.query(InventoryLocation).filter(InventoryLocation.id == txn.to_location_id).first() if hasattr(txn, 'to_location_id') and txn.to_location_id else None
        
        total_cost = None
        if txn.cost_per_unit and txn.quantity:
            total_cost = float(txn.cost_per_unit) * float(txn.quantity)
        
        result.append(TransactionResponse(
            id=txn.id,
            product_id=txn.product_id,
            product_sku=product.sku if product else "",
            product_name=product.name if product else "",
            location_id=txn.location_id,
            location_name=location.name if location else None,
            transaction_type=txn.transaction_type,
            quantity=txn.quantity,
            cost_per_unit=txn.cost_per_unit,
            total_cost=Decimal(str(total_cost)) if total_cost else None,
            reference_type=txn.reference_type,
            reference_id=txn.reference_id,
            lot_number=txn.lot_number,
            serial_number=txn.serial_number,
            notes=txn.notes,
            created_at=txn.created_at,
            created_by=txn.created_by,
            to_location_id=getattr(txn, 'to_location_id', None),
            to_location_name=to_location.name if to_location else None,
        ))
    
    return result


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    request: TransactionCreate,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """Create an inventory transaction"""
    # Validate product
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {request.product_id} not found")
    
    # Validate location
    location = None
    if request.location_id:
        location = db.query(InventoryLocation).filter(InventoryLocation.id == request.location_id).first()
        if not location:
            raise HTTPException(status_code=404, detail=f"Location {request.location_id} not found")
    else:
        # Get default location
        location = db.query(InventoryLocation).filter(InventoryLocation.type == "warehouse").first()
        if not location:
            # Create default warehouse
            location = InventoryLocation(
                name="Main Warehouse",
                code="MAIN",
                type="warehouse",
                active=True
            )
            db.add(location)
            db.flush()
    
    # Validate transaction type
    valid_types = ["receipt", "issue", "transfer", "adjustment", "consumption", "scrap"]
    if request.transaction_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transaction_type. Must be one of: {', '.join(valid_types)}"
        )
    
    # For transfers, validate to_location
    to_location = None
    if request.transaction_type == "transfer":
        if not request.to_location_id:
            raise HTTPException(status_code=400, detail="to_location_id required for transfer transactions")
        to_location = db.query(InventoryLocation).filter(InventoryLocation.id == request.to_location_id).first()
        if not to_location:
            raise HTTPException(status_code=404, detail=f"To location {request.to_location_id} not found")
        if request.to_location_id == location.id:
            raise HTTPException(status_code=400, detail="Cannot transfer to the same location")
    
    # Get or create inventory record
    inventory = db.query(Inventory).filter(
        Inventory.product_id == request.product_id,
        Inventory.location_id == location.id
    ).first()
    
    if not inventory:
        inventory = Inventory(
            product_id=request.product_id,
            location_id=location.id,
            on_hand_quantity=0,
            allocated_quantity=0
        )
        db.add(inventory)
        db.flush()
    
    # Handle transfers specially (create two transactions)
    if request.transaction_type == "transfer":
        # Validate sufficient inventory
        if float(inventory.on_hand_quantity) < float(request.quantity):
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient inventory for transfer. On hand: {inventory.on_hand_quantity}, requested: {request.quantity}"
            )
        
        # Create issue transaction at source
        from_transaction = InventoryTransaction(
            product_id=request.product_id,
            location_id=location.id,
            transaction_type="issue",
            reference_type=request.reference_type or "transfer",
            reference_id=request.reference_id,
            quantity=request.quantity,
            cost_per_unit=request.cost_per_unit,
            lot_number=request.lot_number,
            serial_number=request.serial_number,
            notes=f"Transfer to {to_location.name if to_location else 'location'}: {request.notes or ''}",
            created_by=current_admin.email,
        )
        db.add(from_transaction)
        
        # Decrease from source location
        inventory.on_hand_quantity = float(inventory.on_hand_quantity) - float(request.quantity)
        
        # Get or create destination inventory
        to_inventory = db.query(Inventory).filter(
            Inventory.product_id == request.product_id,
            Inventory.location_id == request.to_location_id
        ).first()
        
        if not to_inventory:
            to_inventory = Inventory(
                product_id=request.product_id,
                location_id=request.to_location_id,
                on_hand_quantity=0,
                allocated_quantity=0
            )
            db.add(to_inventory)
        
        # Create receipt transaction at destination
        to_transaction = InventoryTransaction(
            product_id=request.product_id,
            location_id=request.to_location_id,
            transaction_type="receipt",
            reference_type=request.reference_type or "transfer",
            reference_id=request.reference_id,
            quantity=request.quantity,
            cost_per_unit=request.cost_per_unit,
            lot_number=request.lot_number,
            serial_number=request.serial_number,
            notes=f"Transfer from {location.name}: {request.notes or ''}",
            created_by=current_admin.email,
        )
        db.add(to_transaction)
        
        # Increase at destination location
        to_inventory.on_hand_quantity = float(to_inventory.on_hand_quantity) + float(request.quantity)
        
        # Return the from_transaction as the primary one
        transaction = from_transaction
    else:
        # Create single transaction for other types
        transaction = InventoryTransaction(
            product_id=request.product_id,
            location_id=location.id,
            transaction_type=request.transaction_type,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            quantity=request.quantity,
            cost_per_unit=request.cost_per_unit,
            lot_number=request.lot_number,
            serial_number=request.serial_number,
            notes=request.notes,
            created_by=current_admin.email,
        )
        db.add(transaction)
        
        # Update inventory based on transaction type
        if request.transaction_type == "receipt":
            inventory.on_hand_quantity = float(inventory.on_hand_quantity) + float(request.quantity)
        elif request.transaction_type in ["issue", "consumption", "scrap"]:
            if float(inventory.on_hand_quantity) < float(request.quantity):
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient inventory. On hand: {inventory.on_hand_quantity}, requested: {request.quantity}"
                )
            inventory.on_hand_quantity = float(inventory.on_hand_quantity) - float(request.quantity)
        elif request.transaction_type == "adjustment":
            inventory.on_hand_quantity = float(request.quantity)
    
    db.commit()
    db.refresh(transaction)
    
    db.commit()
    db.refresh(transaction)
    
    # Build response
    to_location = None
    if request.transaction_type == "transfer" and request.to_location_id:
        to_location = db.query(InventoryLocation).filter(InventoryLocation.id == request.to_location_id).first()
    
    total_cost = None
    if transaction.cost_per_unit and transaction.quantity:
        total_cost = float(transaction.cost_per_unit) * float(transaction.quantity)
    
    return TransactionResponse(
        id=transaction.id,
        product_id=transaction.product_id,
        product_sku=product.sku,
        product_name=product.name,
        location_id=transaction.location_id,
        location_name=location.name,
        transaction_type=request.transaction_type,  # Use original type for display
        quantity=transaction.quantity,
        cost_per_unit=transaction.cost_per_unit,
        total_cost=Decimal(str(total_cost)) if total_cost else None,
        reference_type=transaction.reference_type,
        reference_id=transaction.reference_id,
        lot_number=transaction.lot_number,
        serial_number=transaction.serial_number,
        notes=transaction.notes,
        created_at=transaction.created_at,
        created_by=transaction.created_by,
        to_location_id=request.to_location_id if request.transaction_type == "transfer" else None,
        to_location_name=to_location.name if to_location else None,
    )


@router.get("/locations")
async def list_locations(
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """List all inventory locations"""
    locations = db.query(InventoryLocation).filter(InventoryLocation.active== True).all()
    return [
        {
            "id": loc.id,
            "name": loc.name,
            "code": loc.code,
            "type": loc.type,
        }
        for loc in locations
    ]

