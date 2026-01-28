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
from sqlalchemy import desc, or_

from app.db.session import get_db
from app.models.user import User
from app.models.inventory import Inventory, InventoryTransaction, InventoryLocation
from app.models.product import Product
from app.api.v1.deps import get_current_staff_user
from app.services.inventory_helpers import is_material
from app.services.uom_service import convert_quantity_safe
from app.services.transaction_service import TransactionService
from app.logging_config import get_logger

router = APIRouter(prefix="/inventory/transactions", tags=["Admin - Inventory"])
logger = get_logger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def normalize_unit(unit: Optional[str]) -> Optional[str]:
    """
    Normalize unit string to standard format.

    Handles common variations:
    - "gram", "grams", "g" -> "G"
    - "kilogram", "kilograms", "kg" -> "KG"
    - "milligram", "milligrams", "mg" -> "MG"
    - Other units are uppercased and stripped

    Args:
        unit: Unit string to normalize (can be None)

    Returns:
        Normalized unit string (uppercase) or None if input is None/empty
    """
    if not unit:
        return None

    unit = unit.strip().lower()

    # Handle common mass unit variations
    if unit in ("gram", "grams", "g"):
        return "G"
    elif unit in ("kilogram", "kilograms", "kg"):
        return "KG"
    elif unit in ("milligram", "milligrams", "mg"):
        return "MG"

    # For other units, just uppercase
    return unit.upper()


def convert_quantity_to_kg_for_cost(
    db: Session, quantity: Decimal, product_unit: Optional[str], product_id: int, product_sku: Optional[str] = None
) -> float:
    """
    Convert quantity to kilograms for cost calculation.

    Cost per unit is stored per-KG for materials, so we need to convert
    the quantity to KG before multiplying by cost_per_unit.

    Args:
        db: Database session
        quantity: Quantity in product's unit
        product_unit: Product's unit of measure (will be normalized)
        product_id: Product ID for error messages
        product_sku: Product SKU for error messages (optional)

    Returns:
        Quantity in kilograms as float

    Raises:
        ValueError: If unit conversion fails and unit is unknown
    """
    normalized_unit = normalize_unit(product_unit)

    if not normalized_unit:
        # No unit specified - assume it's already in the correct unit for cost
        # Log a warning but proceed
        logger.warning(
            f"Product {product_id} ({product_sku or 'unknown'}) has no unit specified. "
            f"Assuming quantity {quantity} is already in cost unit (KG) for cost calculation.",
            extra={"product_id": product_id, "product_sku": product_sku, "quantity": str(quantity)},
        )
        try:
            return float(quantity)
        except (ValueError, TypeError) as e:
            logger.error(
                f"Failed to cast quantity {quantity} to float for product {product_id}: {e}",
                extra={"product_id": product_id, "quantity": str(quantity)},
            )
            raise ValueError(f"Cannot convert quantity {quantity} to float: {e}")

    # If already in KG, no conversion needed
    if normalized_unit == "KG":
        try:
            return float(quantity)
        except (ValueError, TypeError) as e:
            logger.error(
                f"Failed to cast quantity {quantity} to float for product {product_id}: {e}",
                extra={"product_id": product_id, "quantity": str(quantity)},
            )
            raise ValueError(f"Cannot convert quantity {quantity} to float: {e}")

    # Convert from product unit to KG
    converted_qty, success = convert_quantity_safe(db, quantity, normalized_unit, "KG")

    if not success:
        # Try local fallback conversion for common mass units not in the service
        # This handles cases where MG (milligrams) might not be in the database
        local_mass_conversions = {
            "MG": Decimal("0.000001"),  # 1 milligram = 0.000001 kg
            "G": Decimal("0.001"),  # 1 gram = 0.001 kg (should be in service, but fallback)
        }

        if normalized_unit in local_mass_conversions:
            # Use local conversion factor
            conversion_factor = local_mass_conversions[normalized_unit]
            converted_qty = quantity * conversion_factor
            success = True
            logger.debug(
                f"Used local conversion for {normalized_unit} -> KG for product {product_id}",
                extra={"product_id": product_id, "unit": normalized_unit, "quantity": str(quantity)},
            )

    if not success:
        # Conversion failed - this is a serious error for cost calculation
        error_msg = (
            f"Cannot convert quantity {quantity} {normalized_unit} to KG for product {product_id} "
            f"({product_sku or 'unknown'}). Unit '{normalized_unit}' is unknown or incompatible. "
            f"This will cause incorrect total_cost calculation."
        )
        logger.error(
            error_msg,
            extra={
                "product_id": product_id,
                "product_sku": product_sku,
                "quantity": str(quantity),
                "unit": normalized_unit,
            },
        )
        raise ValueError(error_msg)

    try:
        return float(converted_qty)
    except (ValueError, TypeError) as e:
        logger.error(
            f"Failed to cast converted quantity {converted_qty} to float for product {product_id}: {e}",
            extra={"product_id": product_id, "converted_quantity": str(converted_qty)},
        )
        raise ValueError(f"Cannot convert quantity {converted_qty} to float: {e}")


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
    product_unit: Optional[str] = None  # Unit of measure for the product
    material_type_id: Optional[int] = None  # Material type ID if this is a material
    location_id: Optional[int]
    location_name: Optional[str]
    transaction_type: str
    quantity: Decimal
    unit: Optional[str] = None  # STORED unit from transaction (G, EA, etc.) - UI displays directly
    cost_per_unit: Optional[Decimal]
    total_cost: Optional[Decimal]  # STORED total - UI displays directly, NO client-side math
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
    """
    List inventory transactions with filters.

    SINGLE SOURCE OF TRUTH: Returns stored total_cost and unit directly.
    See docs/AI_DIRECTIVE_UOM_COSTS.md - UI displays these values with NO client-side math.
    """
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
        location = (
            db.query(InventoryLocation).filter(InventoryLocation.id == txn.location_id).first()
            if txn.location_id
            else None
        )
        to_location = (
            db.query(InventoryLocation).filter(InventoryLocation.id == txn.to_location_id).first()
            if hasattr(txn, "to_location_id") and txn.to_location_id
            else None
        )

        # SINGLE SOURCE OF TRUTH: Use stored values from transaction
        # Fallback calculation only for legacy transactions created before migration 039
        stored_total_cost = getattr(txn, "total_cost", None)
        stored_unit = getattr(txn, "unit", None)

        if stored_total_cost is not None:
            # New transaction with stored total_cost - use directly
            total_cost = stored_total_cost
        elif txn.cost_per_unit is not None and txn.quantity is not None:
            # Legacy transaction - calculate for display (but log warning)
            logger.debug(
                f"Transaction {txn.id} missing stored total_cost - calculating for display. "
                f"Run migration 039 to backfill."
            )
            try:
                if product and is_material(product):
                    quantity_kg = convert_quantity_to_kg_for_cost(
                        db, txn.quantity, product.unit, product.id, product.sku
                    )
                    total_cost = Decimal(str(float(txn.cost_per_unit) * quantity_kg))
                else:
                    total_cost = Decimal(str(float(txn.cost_per_unit) * float(txn.quantity)))
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to calculate total_cost for transaction {txn.id}: {e}")
                total_cost = None
        else:
            total_cost = None

        # Use stored unit, fallback to inferred for legacy transactions
        if stored_unit:
            display_unit = stored_unit
        elif product:
            display_unit = "G" if is_material(product) else product.unit
        else:
            display_unit = None

        result.append(
            TransactionResponse(
                id=txn.id,
                product_id=txn.product_id,
                product_sku=product.sku if product else "",
                product_name=product.name if product else "",
                product_unit=product.unit if product else None,
                material_type_id=product.material_type_id if product else None,
                location_id=txn.location_id,
                location_name=location.name if location else None,
                transaction_type=txn.transaction_type,
                quantity=txn.quantity,
                unit=display_unit,  # STORED unit - UI displays directly
                cost_per_unit=txn.cost_per_unit,
                total_cost=total_cost,  # STORED total - UI displays directly
                reference_type=txn.reference_type,
                reference_id=txn.reference_id,
                lot_number=txn.lot_number,
                serial_number=txn.serial_number,
                notes=txn.notes,
                created_at=txn.created_at,
                created_by=txn.created_by,
                to_location_id=getattr(txn, "to_location_id", None),
                to_location_name=to_location.name if to_location else None,
            )
        )

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
            location = InventoryLocation(name="Main Warehouse", code="MAIN", type="warehouse", active=True)
            db.add(location)
            db.flush()

    # Validate transaction type
    valid_types = ["receipt", "issue", "transfer", "adjustment", "consumption", "scrap"]
    if request.transaction_type not in valid_types:
        raise HTTPException(
            status_code=400, detail=f"Invalid transaction_type. Must be one of: {', '.join(valid_types)}"
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
    inventory = (
        db.query(Inventory)
        .filter(Inventory.product_id == request.product_id, Inventory.location_id == location.id)
        .first()
    )

    if not inventory:
        inventory = Inventory(
            product_id=request.product_id, location_id=location.id, on_hand_quantity=0, allocated_quantity=0
        )
        db.add(inventory)
        db.flush()

    # Handle transfers specially (create two transactions)
    if request.transaction_type == "transfer":
        # Validate sufficient inventory
        if float(inventory.on_hand_quantity) < float(request.quantity):
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient inventory for transfer. On hand: {inventory.on_hand_quantity}, requested: {request.quantity}",
            )

        # Calculate total_cost if cost_per_unit provided
        total_cost = None
        if request.cost_per_unit is not None and request.quantity:
            total_cost = float(request.quantity) * float(request.cost_per_unit)

        # Create issue transaction at source
        from_transaction = InventoryTransaction(
            product_id=request.product_id,
            location_id=location.id,
            transaction_type="issue",
            reference_type=request.reference_type or "transfer",
            reference_id=request.reference_id,
            quantity=request.quantity,
            cost_per_unit=request.cost_per_unit,
            total_cost=total_cost,
            lot_number=request.lot_number,
            serial_number=request.serial_number,
            notes=f"Transfer to {to_location.name if to_location else 'location'}: {request.notes or ''}",
            created_by=current_admin.email,
        )
        db.add(from_transaction)

        # Decrease from source location
        inventory.on_hand_quantity = float(inventory.on_hand_quantity) - float(request.quantity)

        # Get or create destination inventory
        to_inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == request.product_id, Inventory.location_id == request.to_location_id)
            .first()
        )

        if not to_inventory:
            to_inventory = Inventory(
                product_id=request.product_id,
                location_id=request.to_location_id,
                on_hand_quantity=0,
                allocated_quantity=0,
            )
            db.add(to_inventory)

        # Create receipt transaction at destination (reuse total_cost calculated above)
        to_transaction = InventoryTransaction(
            product_id=request.product_id,
            location_id=request.to_location_id,
            transaction_type="receipt",
            reference_type=request.reference_type or "transfer",
            reference_id=request.reference_id,
            quantity=request.quantity,
            cost_per_unit=request.cost_per_unit,
            total_cost=total_cost,
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
        # Calculate total_cost if cost_per_unit provided
        total_cost = None
        if request.cost_per_unit is not None and request.quantity:
            total_cost = float(request.quantity) * float(request.cost_per_unit)

        # Create single transaction for other types
        transaction = InventoryTransaction(
            product_id=request.product_id,
            location_id=location.id,
            transaction_type=request.transaction_type,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            quantity=request.quantity,
            cost_per_unit=request.cost_per_unit,
            total_cost=total_cost,
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
                    detail=f"Insufficient inventory. On hand: {inventory.on_hand_quantity}, requested: {request.quantity}",
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
    if transaction.cost_per_unit is not None and transaction.quantity is not None:
        try:
            # For materials: cost_per_unit is per-KG, so convert quantity to KG
            # For non-materials: quantity and cost are typically in same unit
            if is_material(product):
                # Materials: convert quantity from product.unit to KG for cost calculation
                quantity_kg = convert_quantity_to_kg_for_cost(
                    db, transaction.quantity, product.unit, product.id, product.sku
                )
                total_cost = float(transaction.cost_per_unit) * quantity_kg
            else:
                # For non-materials: typically quantity and cost are in same unit
                # If unit is specified, we could validate, but for now assume direct multiplication
                try:
                    total_cost = float(transaction.cost_per_unit) * float(transaction.quantity)
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Failed to calculate total_cost for non-material product {product.id} "
                        f"({product.sku}): {e}",
                        extra={
                            "product_id": product.id,
                            "product_sku": product.sku,
                            "cost_per_unit": str(transaction.cost_per_unit),
                            "quantity": str(transaction.quantity),
                        },
                    )
                    total_cost = None
        except ValueError as e:
            # Unit conversion failed - log error and set total_cost to None
            logger.error(
                f"Failed to calculate total_cost for transaction {transaction.id}: {e}",
                extra={
                    "transaction_id": transaction.id,
                    "product_id": transaction.product_id,
                    "cost_per_unit": str(transaction.cost_per_unit),
                    "quantity": str(transaction.quantity),
                },
            )
            total_cost = None

    return TransactionResponse(
        id=transaction.id,
        product_id=transaction.product_id,
        product_sku=product.sku,
        product_name=product.name,
        product_unit=product.unit,  # Include product unit
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
    locations = db.query(InventoryLocation).filter(InventoryLocation.active.is_(True)).all()
    return [
        {
            "id": loc.id,
            "name": loc.name,
            "code": loc.code,
            "type": loc.type,
        }
        for loc in locations
    ]


# ============================================================================
# BATCH INVENTORY UPDATE (CYCLE COUNTING)
# ============================================================================


class BatchItemUpdate(BaseModel):
    """Single item in a batch update"""

    product_id: int
    counted_quantity: Decimal
    reason: str  # Required for accounting audit trail


class BatchUpdateRequest(BaseModel):
    """Batch inventory update request for cycle counting"""

    items: List[BatchItemUpdate]
    location_id: Optional[int] = None
    count_reference: Optional[str] = None  # e.g., "Cycle Count 2025-01-20"


class BatchUpdateResult(BaseModel):
    """Result of a single item update in batch"""

    product_id: int
    product_sku: str
    product_name: str
    previous_quantity: Decimal
    counted_quantity: Decimal
    variance: Decimal
    transaction_id: Optional[int] = None
    journal_entry_id: Optional[int] = None  # GL journal entry for accounting
    success: bool
    error: Optional[str] = None


class BatchUpdateResponse(BaseModel):
    """Batch update response"""

    total_items: int
    successful: int
    failed: int
    results: List[BatchUpdateResult]
    count_reference: Optional[str]


@router.post("/batch", response_model=BatchUpdateResponse, status_code=200)
async def batch_update_inventory(
    request: BatchUpdateRequest,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Batch update inventory quantities for cycle counting.

    This endpoint accepts a list of items with their counted quantities
    and creates adjustment transactions for each item where the count
    differs from the current on-hand quantity.

    For cycle counting workflow:
    1. User performs physical count
    2. User enters counted quantities in batch
    3. System creates adjustment transactions for variances
    4. Inventory is updated to match counted quantities
    """
    results = []
    successful = 0
    failed = 0

    # Get or create default location
    if request.location_id:
        location = db.query(InventoryLocation).filter(InventoryLocation.id == request.location_id).first()
        if not location:
            raise HTTPException(status_code=404, detail=f"Location {request.location_id} not found")
    else:
        location = db.query(InventoryLocation).filter(InventoryLocation.type == "warehouse").first()
        if not location:
            # Create default warehouse
            location = InventoryLocation(name="Main Warehouse", code="MAIN", type="warehouse", active=True)
            db.add(location)
            db.flush()

    count_ref = request.count_reference or f"Cycle Count {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    # Use TransactionService for atomic inventory + GL transactions
    txn_service = TransactionService(db)

    for item in request.items:
        try:
            # Get product
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                results.append(
                    BatchUpdateResult(
                        product_id=item.product_id,
                        product_sku="UNKNOWN",
                        product_name="Unknown Product",
                        previous_quantity=Decimal(0),
                        counted_quantity=item.counted_quantity,
                        variance=Decimal(0),
                        success=False,
                        error=f"Product {item.product_id} not found",
                    )
                )
                failed += 1
                continue

            # Get or create inventory record
            inventory = (
                db.query(Inventory)
                .filter(Inventory.product_id == item.product_id, Inventory.location_id == location.id)
                .first()
            )

            if not inventory:
                inventory = Inventory(
                    product_id=item.product_id, location_id=location.id, on_hand_quantity=0, allocated_quantity=0
                )
                db.add(inventory)
                db.flush()

            previous_qty = Decimal(str(inventory.on_hand_quantity))
            variance = item.counted_quantity - previous_qty

            # Skip if no variance (count matches)
            if variance == 0:
                results.append(
                    BatchUpdateResult(
                        product_id=item.product_id,
                        product_sku=product.sku,
                        product_name=product.name,
                        previous_quantity=previous_qty,
                        counted_quantity=item.counted_quantity,
                        variance=Decimal(0),
                        success=True,
                        error=None,
                    )
                )
                successful += 1
                continue

            # Build reason for audit trail: count reference + user reason
            full_reason = f"{count_ref}: {item.reason}"

            # Use TransactionService for atomic inventory + GL accounting
            # This creates:
            # 1. InventoryTransaction record
            # 2. GLJournalEntry with balanced debit/credit lines
            # 3. Updates inventory quantity
            inv_txn, journal_entry = txn_service.cycle_count_adjustment(
                product_id=item.product_id,
                expected_qty=previous_qty,
                actual_qty=item.counted_quantity,
                reason=full_reason,
                location_id=location.id,
                user_id=current_admin.id,
            )

            # Update last_counted timestamp
            inventory.last_counted = datetime.utcnow()

            db.flush()

            results.append(
                BatchUpdateResult(
                    product_id=item.product_id,
                    product_sku=product.sku,
                    product_name=product.name,
                    previous_quantity=previous_qty,
                    counted_quantity=item.counted_quantity,
                    variance=variance,
                    transaction_id=inv_txn.id,
                    journal_entry_id=journal_entry.id,
                    success=True,
                    error=None,
                )
            )
            successful += 1

        except ValueError as e:
            # TransactionService raises ValueError for missing accounts, etc.
            logger.error(f"Accounting error for batch item {item.product_id}: {e}")
            results.append(
                BatchUpdateResult(
                    product_id=item.product_id,
                    product_sku=product.sku if product else "ERROR",
                    product_name=product.name if product else "Error",
                    previous_quantity=previous_qty if "previous_qty" in locals() else Decimal(0),
                    counted_quantity=item.counted_quantity,
                    variance=Decimal(0),
                    success=False,
                    error=f"Accounting error: {str(e)}",
                )
            )
            failed += 1
        except Exception as e:
            logger.error(f"Error processing batch item {item.product_id}: {e}")
            results.append(
                BatchUpdateResult(
                    product_id=item.product_id,
                    product_sku="ERROR",
                    product_name="Error",
                    previous_quantity=Decimal(0),
                    counted_quantity=item.counted_quantity,
                    variance=Decimal(0),
                    success=False,
                    error=str(e),
                )
            )
            failed += 1

    # Commit all changes (inventory + GL entries atomically)
    db.commit()

    return BatchUpdateResponse(
        total_items=len(request.items), successful=successful, failed=failed, results=results, count_reference=count_ref
    )


@router.get("/inventory-summary")
async def get_inventory_summary(
    location_id: Optional[int] = Query(None, description="Filter by location"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by SKU or name"),
    show_zero: bool = Query(False, description="Include items with zero quantity"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Get inventory summary for cycle counting.

    Returns current inventory levels with product info for easy counting.
    """
    query = db.query(Inventory).join(Product)

    if location_id:
        query = query.filter(Inventory.location_id == location_id)

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(Product.sku.ilike(search_term), Product.name.ilike(search_term)))

    if not show_zero:
        query = query.filter(Inventory.on_hand_quantity > 0)

    total = query.count()
    items = query.order_by(Product.sku).offset(offset).limit(limit).all()

    result = []
    for inv in items:
        product = inv.product
        location = inv.location
        result.append(
            {
                "inventory_id": inv.id,
                "product_id": product.id,
                "product_sku": product.sku,
                "product_name": product.name,
                "category_name": product.item_category.name if product.item_category else None,
                "unit": "G" if is_material(product) else (product.unit or "EA"),
                "location_id": location.id if location else None,
                "location_name": location.name if location else None,
                "on_hand_quantity": float(inv.on_hand_quantity),
                "allocated_quantity": float(inv.allocated_quantity),
                "available_quantity": float(inv.available_quantity)
                if inv.available_quantity
                else float(inv.on_hand_quantity) - float(inv.allocated_quantity),
                "last_counted": inv.last_counted.isoformat() if inv.last_counted else None,
            }
        )

    return {"items": result, "total": total, "limit": limit, "offset": offset}
