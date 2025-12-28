"""
Inventory Transaction Service

Handles automatic inventory transactions for:
- Production completion (consume materials, add finished goods)
- Shipping (consume packaging materials, issue finished goods)
"""
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.inventory import Inventory, InventoryTransaction, InventoryLocation
from app.models.product import Product
from app.models.bom import BOM, BOMLine
from app.models.production_order import ProductionOrder
from app.models.sales_order import SalesOrder
from app.models.traceability import MaterialLot, ProductionLotConsumption
from app.logging_config import get_logger
from app.services.uom_service import (
    convert_quantity_safe,
    format_conversion_note,
    UOMConversionError,
    convert_cost_for_unit,
    get_cost_reference_unit,
)

logger = get_logger(__name__)


def get_effective_cost(product: "Product") -> "Optional[Decimal]":
    """
    Get the effective cost for a product based on its declared cost_method.

    Cost methods:
    - 'standard': Use standard_cost (for manufactured items with set costs)
    - 'average': Use weighted average cost (default, for purchased items)
    - 'fifo': Use last_cost as approximation (full FIFO requires cost layers)
    - 'last': Use most recent purchase price

    Returns None if no cost is available.
    """
    method = (product.cost_method or "average").lower()

    if method == "standard":
        if product.standard_cost is not None:
            return Decimal(str(product.standard_cost))
        # Fallback: warn and use average/last
        logger.warning(
            f"Product {product.sku} uses standard costing but has no standard_cost set. "
            f"Falling back to average/last cost."
        )
        if product.average_cost is not None:
            return Decimal(str(product.average_cost))
        if product.last_cost is not None:
            return Decimal(str(product.last_cost))
        return None

    elif method == "average":
        if product.average_cost is not None:
            return Decimal(str(product.average_cost))
        # Fallback to last_cost for products without average yet
        if product.last_cost is not None:
            return Decimal(str(product.last_cost))
        return None

    elif method == "fifo":
        # Full FIFO requires cost layer tracking (not yet implemented)
        # For now, use last_cost as approximation
        if product.last_cost is not None:
            return Decimal(str(product.last_cost))
        if product.average_cost is not None:
            return Decimal(str(product.average_cost))
        return None

    elif method == "last":
        if product.last_cost is not None:
            return Decimal(str(product.last_cost))
        return None

    # Unknown method - default to average behavior
    logger.warning(f"Unknown cost_method '{method}' for {product.sku}, using average")
    if product.average_cost is not None:
        return Decimal(str(product.average_cost))
    if product.last_cost is not None:
        return Decimal(str(product.last_cost))
    return None




# ============================================================================
# CRITICAL: Cost Per Unit Conversion - DO NOT MODIFY WITHOUT DISCUSSION
# ============================================================================
# This function converts cost from PURCHASING unit ($/KG) to INVENTORY unit ($/G).
#
# WHY THIS EXISTS:
# - Products store cost per purchasing unit (e.g., $14.99/KG for filament)
# - Inventory transactions store quantity in base unit (e.g., grams)
# - We must convert cost to match: $14.99/KG -> $0.01499/G
#
# WITHOUT THIS: 3856 G * $14.99 = $57,801 (caused $1.1M fake COGS!)
# WITH THIS:    3856 G * $0.01499 = $57.80 (correct)
#
# DO NOT CHANGE without verifying accounting dashboard COGS calculations.
# ============================================================================
def get_effective_cost_per_inventory_unit(product: "Product") -> "Optional[Decimal]":
    """
    Get the effective cost for a product, converted to cost per inventory unit.

    Product costs (standard_cost, average_cost, last_cost) are stored per the
    cost reference unit (e.g., $/KG for materials). When inventory tracks in
    a different unit (e.g., grams), we must convert to $/inventory_unit.

    Example:
        - Product has unit='G' and standard_cost=14.99 ($/KG)
        - Returns: 0.01499 ($/G)
        - So: 1000 G * $0.01499/G = $14.99 (correct!)

    Args:
        product: Product to get cost for

    Returns:
        Cost per inventory unit (e.g., $/G), or None if no cost available
    """
    base_cost = get_effective_cost(product)
    if base_cost is None:
        return None

    inventory_unit = (product.unit or 'EA').upper().strip()
    cost_reference_unit = get_cost_reference_unit(inventory_unit)

    # Convert cost from reference unit to inventory unit
    return convert_cost_for_unit(base_cost, cost_reference_unit, inventory_unit)


def convert_and_generate_notes(
    db: Session,
    bom_qty: Decimal,
    line_unit: str,
    component_unit: str,
    component_name: str,
    component_sku: str,
    reference_prefix: str,
    reference_code: str,
) -> Tuple[Decimal, str]:
    """Convert BOM quantity to component unit and generate transaction notes.
    
    Args:
        db: Database session
        bom_qty: Quantity in BOM line units
        line_unit: BOM line unit code
        component_unit: Component's inventory unit code
        component_name: Component product name
        component_sku: Component SKU (for logging)
        reference_prefix: Prefix for notes (e.g., "Consumed for PO#", "Shipping materials for SO#")
        reference_code: Reference code/number for notes
    
    Returns:
        Tuple of (total_qty, notes) where total_qty is the converted quantity
        and notes is the formatted transaction description
    
    Raises:
        UOMConversionError: If units are incompatible and conversion fails.
            This prevents dangerous inventory errors (e.g., treating 225 G as 225 KG).
            The calling transaction will be rolled back automatically.
    """
    if line_unit != component_unit:
        total_qty, was_converted = convert_quantity_safe(db, bom_qty, line_unit, component_unit)
        if was_converted:
            notes = f"{reference_prefix}{reference_code}: " + \
                format_conversion_note(bom_qty, line_unit, total_qty, component_unit, component_name)
        else:
            # Conversion failed (incompatible units) - ABORT to prevent inventory errors
            # Using bom_qty would be dangerous: e.g., 225 G treated as 225 KG = massive error
            error_msg = (
                f"UOM conversion failed for {reference_prefix}{reference_code}: "
                f"Cannot convert {line_unit} to {component_unit} for component {component_sku} ({component_name}). "
                f"Attempted to convert {bom_qty} {line_unit} but units are incompatible. "
                f"Transaction aborted to prevent inventory errors."
            )
            logger.error(error_msg)
            raise UOMConversionError(error_msg)
    else:
        total_qty = bom_qty
        notes = f"{reference_prefix}{reference_code}: {total_qty} {component_unit} of {component_name}"
    
    return total_qty, notes


def get_or_create_default_location(db: Session) -> InventoryLocation:
    """Get or create the default warehouse location."""
    location = db.query(InventoryLocation).filter(InventoryLocation.type == "warehouse").first()
    if not location:
        location = InventoryLocation(
            name="Main Warehouse",
            code="MAIN",
            type="warehouse",
            active=True
        )
        db.add(location)
        db.flush()
    return location


def get_or_create_inventory(
    db: Session,
    product_id: int,
    location_id: int
) -> Inventory:
    """Get or create an inventory record for a product at a location."""
    inventory = db.query(Inventory).filter(
        Inventory.product_id == product_id,
        Inventory.location_id == location_id
    ).first()

    if not inventory:
        inventory = Inventory(
            product_id=product_id,
            location_id=location_id,
            on_hand_quantity=Decimal("0"),
            allocated_quantity=Decimal("0")
        )
        db.add(inventory)
        db.flush()
    else:
        # Validate allocated doesn't exceed on_hand (consistency check)
        allocated = Decimal(str(inventory.allocated_quantity))
        on_hand = Decimal(str(inventory.on_hand_quantity))
        if allocated > on_hand:
            logger.warning(
                f"Inventory consistency issue detected: Product {product_id}, Location {location_id}: "
                f"Allocated ({allocated}) exceeds On Hand ({on_hand}). "
                f"Available quantity would be negative."
            )

    return inventory


def validate_inventory_consistency(
    db: Session,
    product_id: Optional[int] = None,
    location_id: Optional[int] = None,
    auto_fix: bool = False
) -> List[Dict[str, Any]]:
    """
    Validate inventory consistency: allocated should not exceed on_hand.
    
    Args:
        db: Database session
        product_id: Optional filter by product
        location_id: Optional filter by location
        auto_fix: If True, automatically fix inconsistencies by reducing allocated to on_hand
        
    Returns:
        List of inconsistency records found/fixed
    """
    query = db.query(Inventory)
    if product_id:
        query = query.filter(Inventory.product_id == product_id)
    if location_id:
        query = query.filter(Inventory.location_id == location_id)
    
    inconsistencies = []
    for inv in query.all():
        allocated = Decimal(str(inv.allocated_quantity))
        on_hand = Decimal(str(inv.on_hand_quantity))
        available = on_hand - allocated
        
        if allocated > on_hand:
            inconsistency = {
                "product_id": inv.product_id,
                "location_id": inv.location_id,
                "on_hand": float(on_hand),
                "allocated": float(allocated),
                "available": float(available),
                "issue": "allocated_exceeds_on_hand",
                "fixed": False,
            }
            
            if auto_fix:
                # Fix by reducing allocated to on_hand
                inv.allocated_quantity = on_hand
                inv.updated_at = datetime.utcnow()
                inconsistency["fixed"] = True
                inconsistency["new_allocated"] = float(on_hand)
                logger.info(
                    f"Fixed inventory inconsistency: Product {inv.product_id}, "
                    f"Location {inv.location_id}: Reduced allocated from {allocated} to {on_hand}"
                )
            
            inconsistencies.append(inconsistency)
    
    if auto_fix and inconsistencies:
        db.commit()
    
    return inconsistencies


def create_inventory_transaction(
    db: Session,
    product_id: int,
    location_id: int,
    transaction_type: str,
    quantity: Decimal,
    reference_type: str,
    reference_id: int,
    notes: Optional[str] = None,
    cost_per_unit: Optional[Decimal] = None,
    created_by: Optional[str] = None,
    approval_reason: Optional[str] = None,
    approved_by: Optional[str] = None,
    allow_negative: bool = False,
) -> InventoryTransaction:
    """
    Create an inventory transaction and update inventory quantities.

    Args:
        db: Database session
        product_id: Product being transacted
        location_id: Location for the transaction
        transaction_type: receipt, issue, consumption, adjustment, negative_adjustment
        quantity: Quantity (positive for receipt, positive for issue/consumption - will be subtracted)
        reference_type: production_order, sales_order, etc.
        reference_id: ID of the reference document
        notes: Optional notes
        cost_per_unit: Optional cost per unit
        created_by: User who created the transaction
        approval_reason: Reason for negative inventory approval (required if negative)
        approved_by: User approving negative inventory (required if negative)
        allow_negative: If True, allow negative inventory with approval

    Returns:
        Created InventoryTransaction

    Raises:
        ValueError: If negative inventory would occur without approval
    """
    # Get or create inventory record
    inventory = get_or_create_inventory(db, product_id, location_id)

    # Check for negative inventory for consumption transactions
    requires_approval = False
    if transaction_type in ["issue", "consumption", "shipment", "scrap"]:
        # Calculate what available quantity would be after this transaction
        current_available = Decimal(str(inventory.on_hand_quantity)) - Decimal(str(inventory.allocated_quantity))
        new_available = current_available - quantity
        
        if new_available < 0:
            if not allow_negative or not approval_reason or not approved_by:
                requires_approval = True
                # Don't raise error - create transaction but mark as requiring approval
                # The calling code should handle the approval workflow
            else:
                # Negative inventory is allowed with approval
                logger.warning(
                    f"Negative inventory transaction approved: Product {product_id}, "
                    f"Available: {current_available}, Consuming: {quantity}, "
                    f"New Available: {new_available}, Reason: {approval_reason}, "
                    f"Approved by: {approved_by}"
                )

    # Create transaction record
    transaction = InventoryTransaction(
        product_id=product_id,
        location_id=location_id,
        transaction_type=transaction_type if not requires_approval else "negative_adjustment",
        quantity=quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        cost_per_unit=cost_per_unit,
        created_by=created_by,
        created_at=datetime.utcnow(),
        requires_approval=requires_approval,
        approval_reason=approval_reason,
        approved_by=approved_by,
        approved_at=datetime.utcnow() if approved_by else None,
    )
    db.add(transaction)

    # Only update inventory if approved or not requiring approval
    if not requires_approval or (allow_negative and approved_by):
        # Update inventory based on transaction type
        if transaction_type == "receipt":
            inventory.on_hand_quantity = Decimal(str(inventory.on_hand_quantity)) + quantity
        elif transaction_type == "adjustment":
            # Adjustment can be positive or negative - quantity is already signed
            # For adjustments, we set the quantity directly (not add/subtract)
            # But since we're using create_inventory_transaction, we need to handle it
            # The adjustment endpoint will handle setting the exact quantity
            inventory.on_hand_quantity = Decimal(str(inventory.on_hand_quantity)) - quantity
        elif transaction_type in ["issue", "consumption", "shipment", "scrap", "negative_adjustment"]:
            inventory.on_hand_quantity = Decimal(str(inventory.on_hand_quantity)) - quantity

        inventory.updated_at = datetime.utcnow()
    else:
        # Transaction created but inventory not updated - requires approval
        logger.info(
            f"Inventory transaction {transaction.id} created but requires approval "
            f"for negative inventory: Product {product_id}, Quantity: {quantity}"
        )

    return transaction


def reserve_production_materials(
    db: Session,
    production_order: ProductionOrder,
    created_by: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Reserve (allocate) materials when a production order is scheduled.
    
    This increases the allocated_quantity on inventory records, reducing
    available quantity without actually consuming the materials.
    
    Materials are reserved based on BOM quantity * ordered quantity.
    
    Args:
        db: Database session
        production_order: The production order being scheduled
        created_by: User scheduling the order
    
    Returns:
        List of reservation records with details about what was reserved
    """
    reservations = []
    location = get_or_create_default_location(db)
    
    # Get BOM for the product
    bom = db.query(BOM).filter(
        BOM.product_id == production_order.product_id,
        BOM.active.is_(True)
    ).first()
    
    if not bom:
        logger.warning(f"No active BOM found for product {production_order.product_id} - no materials to reserve")
        return reservations
    
    quantity_ordered = Decimal(str(production_order.quantity_ordered or 0))
    
    # Get BOM lines for production consumption
    bom_lines = db.query(BOMLine).filter(
        BOMLine.bom_id == bom.id,
        BOMLine.consume_stage == "production",
    ).all()
    
    for line in bom_lines:
        # Skip cost-only items (machine time, overhead)
        if line.is_cost_only:
            continue
        
        # Skip non-inventory items
        component = db.query(Product).filter(Product.id == line.component_id).first()
        if not component:
            continue
        
        # Calculate quantity to reserve (BOM qty per unit * ordered units)
        # Apply scrap factor if any
        base_qty = Decimal(str(line.quantity))
        scrap_factor = Decimal(str(line.scrap_factor or 0)) / Decimal("100")
        qty_with_scrap = base_qty * (Decimal("1") + scrap_factor)
        bom_qty = qty_with_scrap * quantity_ordered
        
        # UOM Conversion: Convert BOM line unit to component's inventory unit
        line_unit = (line.unit or component.unit or "EA").upper()
        component_unit = (component.unit or "EA").upper()
        
        try:
            total_qty, _ = convert_and_generate_notes(
                db=db,
                bom_qty=bom_qty,
                line_unit=line_unit,
                component_unit=component_unit,
                component_name=component.name,
                component_sku=component.sku,
                reference_prefix="Reserved for PO#",
                reference_code=production_order.code,
            )
        except UOMConversionError as e:
            logger.error(f"Failed to reserve materials: {e}")
            continue
        
        # Get or create inventory record
        inventory = get_or_create_inventory(db, line.component_id, location.id)
        
        # Increase allocated quantity
        current_allocated = Decimal(str(inventory.allocated_quantity))
        current_on_hand = Decimal(str(inventory.on_hand_quantity))
        new_allocated = current_allocated + total_qty
        available_after = current_on_hand - new_allocated
        
        inventory.allocated_quantity = new_allocated
        inventory.updated_at = datetime.utcnow()
        
        # Create reservation transaction for audit trail
        txn = InventoryTransaction(
            product_id=line.component_id,
            location_id=location.id,
            transaction_type="reservation",
            quantity=total_qty,
            reference_type="production_order",
            reference_id=production_order.id,
            notes=f"Reserved for PO#{production_order.code}: {total_qty} {component_unit} of {component.name}",
            cost_per_unit=get_effective_cost_per_inventory_unit(component),
            created_by=created_by,
            created_at=datetime.utcnow(),
        )
        db.add(txn)
        
        reservation_info = {
            "product_id": line.component_id,
            "product_sku": component.sku,
            "product_name": component.name,
            "quantity_reserved": float(total_qty),
            "unit": component_unit,
            "on_hand": float(current_on_hand),
            "allocated_after": float(new_allocated),
            "available_after": float(available_after),
            "is_shortage": available_after < 0,
        }
        reservations.append(reservation_info)
        
        if available_after < 0:
            logger.warning(
                f"Material shortage after reservation: {component.sku} - "
                f"Available: {available_after} {component_unit} (shortage of {-available_after})"
            )
        else:
            logger.info(
                f"Reserved {total_qty} {component_unit} of {component.sku} "
                f"for PO#{production_order.code}"
            )
    
    return reservations


def release_production_reservations(
    db: Session,
    production_order: ProductionOrder,
    created_by: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Release (un-allocate) materials that were reserved for a production order.
    
    Called when:
    - Production order is cancelled/unscheduled
    - Before consuming actuals (to release then consume)
    
    Args:
        db: Database session
        production_order: The production order
        created_by: User performing the action
    
    Returns:
        List of release records
    """
    releases = []
    # Ensure default location exists (not used directly but needed for consistency)
    _location = get_or_create_default_location(db)

    # Find all reservation transactions for this PO
    reservation_txns = db.query(InventoryTransaction).filter(
        InventoryTransaction.reference_type == "production_order",
        InventoryTransaction.reference_id == production_order.id,
        InventoryTransaction.transaction_type == "reservation",
    ).all()
    
    for txn in reservation_txns:
        # Decrease allocated quantity
        inventory = db.query(Inventory).filter(
            Inventory.product_id == txn.product_id,
            Inventory.location_id == txn.location_id,
        ).first()
        
        if inventory:
            current_allocated = Decimal(str(inventory.allocated_quantity))
            release_qty = Decimal(str(txn.quantity))
            new_allocated = max(Decimal("0"), current_allocated - release_qty)
            
            inventory.allocated_quantity = new_allocated
            inventory.updated_at = datetime.utcnow()
            
            # Create release transaction for audit
            release_txn = InventoryTransaction(
                product_id=txn.product_id,
                location_id=txn.location_id,
                transaction_type="reservation_release",
                quantity=release_qty,
                reference_type="production_order",
                reference_id=production_order.id,
                notes=f"Released reservation for PO#{production_order.code}",
                created_by=created_by,
                created_at=datetime.utcnow(),
            )
            db.add(release_txn)
            
            component = db.query(Product).filter(Product.id == txn.product_id).first()
            releases.append({
                "product_id": txn.product_id,
                "product_sku": component.sku if component else "Unknown",
                "quantity_released": float(release_qty),
                "new_allocated": float(new_allocated),
            })
            
            logger.info(
                f"Released reservation of {release_qty} for PO#{production_order.code}"
            )
    
    return releases


def consume_from_material_lots(
    db: Session,
    component_id: int,
    quantity: Decimal,
    production_order_id: int,
    bom_line_id: Optional[int] = None,
) -> List[ProductionLotConsumption]:
    """
    Consume material from available lots using FIFO (oldest first).

    Creates ProductionLotConsumption records linking production orders to material lots.
    Updates MaterialLot.quantity_consumed for each lot used.

    Args:
        db: Database session
        component_id: Product ID of the component being consumed
        quantity: Total quantity to consume (in component's inventory unit)
        production_order_id: Production order consuming the material
        bom_line_id: Optional BOM line ID

    Returns:
        List of ProductionLotConsumption records created
    """
    consumptions = []

    # Get available lots for this component (FIFO by received_date)
    available_lots = db.query(MaterialLot).filter(
        MaterialLot.product_id == component_id,
        MaterialLot.status == "active",
    ).order_by(MaterialLot.received_date.asc()).all()

    if not available_lots:
        logger.debug(f"No active MaterialLots found for component {component_id}")
        return consumptions

    remaining = quantity
    for lot in available_lots:
        if remaining <= Decimal("0"):
            break

        # Calculate available quantity in this lot
        available = (
            lot.quantity_received
            - lot.quantity_consumed
            - lot.quantity_scrapped
            + lot.quantity_adjusted
        )

        if available <= Decimal("0"):
            continue

        # Consume from this lot
        consume_qty = min(available, remaining)

        # Create consumption record
        consumption = ProductionLotConsumption(
            production_order_id=production_order_id,
            material_lot_id=lot.id,
            bom_line_id=bom_line_id,
            quantity_consumed=consume_qty,
            consumed_at=datetime.utcnow(),
        )
        db.add(consumption)
        consumptions.append(consumption)

        # Update lot's consumed quantity
        lot.quantity_consumed = Decimal(str(lot.quantity_consumed or 0)) + consume_qty

        # Check if lot is now depleted
        new_available = (
            lot.quantity_received
            - lot.quantity_consumed
            - lot.quantity_scrapped
            + lot.quantity_adjusted
        )
        if new_available <= Decimal("0"):
            lot.status = "depleted"
            logger.info(f"MaterialLot {lot.lot_number} depleted")

        remaining -= consume_qty
        logger.debug(
            f"Consumed {consume_qty} from lot {lot.lot_number}, "
            f"remaining in lot: {new_available}"
        )

    if remaining > Decimal("0"):
        logger.warning(
            f"Could not fully consume {quantity} for component {component_id}. "
            f"Remaining {remaining} not tracked in lots."
        )

    return consumptions


def consume_production_materials(
    db: Session,
    production_order: ProductionOrder,
    quantity_completed: Decimal,
    created_by: Optional[str] = None,
    release_reservations: bool = True,
) -> List[InventoryTransaction]:
    """
    Consume raw materials based on BOM when production order completes.

    Only consumes items with consume_stage='production' and cost_only=False.
    
    If release_reservations=True (default), first releases any existing 
    reservations before consuming actual quantities.

    Args:
        db: Database session
        production_order: The completed production order
        quantity_completed: Number of units completed (actual, may differ from ordered)
        created_by: User completing the order
        release_reservations: If True, release reservations before consuming

    Returns:
        List of created inventory transactions
    """
    # Release reservations first if requested
    if release_reservations:
        release_production_reservations(db, production_order, created_by)
    transactions = []
    location = get_or_create_default_location(db)

    # Get BOM for the product
    bom = db.query(BOM).filter(
        BOM.product_id == production_order.product_id,
        BOM.active.is_(True)
    ).first()

    if not bom:
        logger.warning(f"No active BOM found for product {production_order.product_id}")
        return transactions

    # Get BOM lines for production consumption
    bom_lines = db.query(BOMLine).filter(
        BOMLine.bom_id == bom.id,
        BOMLine.consume_stage == "production",
    ).all()

    for line in bom_lines:
        # Skip cost-only items (machine time, overhead)
        if line.is_cost_only:
            continue

        # Skip non-inventory items
        component = db.query(Product).filter(Product.id == line.component_id).first()
        if not component:
            continue

        # Calculate quantity to consume (BOM qty per unit * completed units)
        # Apply scrap factor if any
        base_qty = Decimal(str(line.quantity))
        scrap_factor = Decimal(str(line.scrap_factor or 0)) / Decimal("100")
        qty_with_scrap = base_qty * (Decimal("1") + scrap_factor)
        bom_qty = qty_with_scrap * quantity_completed

        # UOM Conversion: Convert BOM line unit to component's inventory unit
        # e.g., BOM says 225.23 G, but component is stored in KG
        line_unit = (line.unit or component.unit or "EA").upper()
        component_unit = (component.unit or "EA").upper()

        total_qty, notes = convert_and_generate_notes(
            db=db,
            bom_qty=bom_qty,
            line_unit=line_unit,
            component_unit=component_unit,
            component_name=component.name,
            component_sku=component.sku,
            reference_prefix="Consumed for PO#",
            reference_code=production_order.code,
        )

        # Create consumption transaction
        txn = create_inventory_transaction(
            db=db,
            product_id=line.component_id,
            location_id=location.id,
            transaction_type="consumption",
            quantity=total_qty,
            reference_type="production_order",
            reference_id=production_order.id,
            notes=notes,
            cost_per_unit=get_effective_cost_per_inventory_unit(component),
            created_by=created_by,
        )
        transactions.append(txn)

        # Record lot consumption for traceability (FIFO)
        lot_consumptions = consume_from_material_lots(
            db=db,
            component_id=line.component_id,
            quantity=total_qty,
            production_order_id=production_order.id,
            bom_line_id=line.id,
        )

        logger.info(
            f"Consumed {total_qty} {component_unit} of {component.sku} "
            f"for production order {production_order.id}"
            f"{f' (tracked in {len(lot_consumptions)} lot(s))' if lot_consumptions else ''}"
        )

    return transactions


def receive_finished_goods(
    db: Session,
    production_order: ProductionOrder,
    quantity_completed: Decimal,
    created_by: Optional[str] = None,
) -> Tuple[Optional[InventoryTransaction], Optional[InventoryTransaction]]:
    """
    Add finished goods to inventory when production order completes.
    Handles overruns by creating separate transactions for ordered vs overrun quantities.

    Args:
        db: Database session
        production_order: The completed production order
        quantity_completed: Number of units completed (may exceed ordered)
        created_by: User completing the order

    Returns:
        Tuple of (ordered_receipt_txn, overrun_receipt_txn) - overrun_txn is None if no overrun
    """
    location = get_or_create_default_location(db)

    product = db.query(Product).filter(Product.id == production_order.product_id).first()
    if not product:
        logger.error(f"Product {production_order.product_id} not found for production order")
        return None, None

    quantity_ordered = Decimal(str(production_order.quantity_ordered or 0))
    overrun_qty = max(Decimal("0"), quantity_completed - quantity_ordered)

    # Create receipt transaction for ordered quantity
    ordered_txn = create_inventory_transaction(
        db=db,
        product_id=production_order.product_id,
        location_id=location.id,
        transaction_type="receipt",
        quantity=quantity_ordered,
        reference_type="production_order",
        reference_id=production_order.id,
        notes=f"Completed production PO#{production_order.code} (ordered quantity)",
        cost_per_unit=get_effective_cost_per_inventory_unit(product),
        created_by=created_by,
    )

    overrun_txn = None
    if overrun_qty > 0:
        # Create separate receipt transaction for overrun (MTS stock)
        overrun_txn = create_inventory_transaction(
            db=db,
            product_id=production_order.product_id,
            location_id=location.id,
            transaction_type="receipt",
            quantity=overrun_qty,
            reference_type="production_order",
            reference_id=production_order.id,
            notes=f"MTS overrun from PO#{production_order.code}: {overrun_qty} units added to stock",
            cost_per_unit=get_effective_cost_per_inventory_unit(product),
            created_by=created_by,
        )
        logger.info(
            f"Received {quantity_completed} units of {product.sku} "
            f"from production order {production_order.id} "
            f"({quantity_ordered} ordered + {overrun_qty} MTS overrun)"
        )
    else:
        logger.info(
            f"Received {quantity_completed} units of {product.sku} "
            f"from production order {production_order.id}"
        )

    return ordered_txn, overrun_txn


def process_production_completion(
    db: Session,
    production_order: ProductionOrder,
    quantity_completed: Decimal,
    created_by: Optional[str] = None,
) -> Tuple[List[InventoryTransaction], Optional[InventoryTransaction], Optional[InventoryTransaction]]:
    """
    Process all inventory transactions for production order completion.

    1. Consumes raw materials based on BOM (production stage items)
    2. Adds finished goods to inventory (ordered quantity)
    3. Adds overrun quantity to inventory as MTS stock (if any)

    Args:
        db: Database session
        production_order: The completed production order
        quantity_completed: Number of units completed (may exceed ordered)
        created_by: User completing the order

    Returns:
        Tuple of (material_consumption_txns, ordered_receipt_txn, overrun_receipt_txn)
    """
    # Consume materials (based on actual quantity completed, including overrun)
    consumption_txns = consume_production_materials(
        db=db,
        production_order=production_order,
        quantity_completed=quantity_completed,
        created_by=created_by,
    )

    # Receive finished goods (handles overruns automatically)
    ordered_txn, overrun_txn = receive_finished_goods(
        db=db,
        production_order=production_order,
        quantity_completed=quantity_completed,
        created_by=created_by,
    )

    return consumption_txns, ordered_txn, overrun_txn


def consume_shipping_materials(
    db: Session,
    sales_order: SalesOrder,
    created_by: Optional[str] = None,
) -> List[InventoryTransaction]:
    """
    Consume packaging materials based on BOM when order ships.

    Only consumes items with consume_stage='shipping' from the order's product BOMs.

    Args:
        db: Database session
        sales_order: The sales order being shipped
        created_by: User processing the shipment

    Returns:
        List of created inventory transactions
    """
    transactions = []
    location = get_or_create_default_location(db)

    # Get products to ship - either from lines or legacy single-product format
    products_to_ship = []

    if sales_order.lines:
        for line in sales_order.lines:
            if line.product_id:
                products_to_ship.append((line.product_id, line.quantity))
    elif sales_order.product_id:
        products_to_ship.append((sales_order.product_id, sales_order.quantity or 1))

    for product_id, qty in products_to_ship:
        # Get BOM for product
        bom = db.query(BOM).filter(
            BOM.product_id == product_id,
            BOM.active.is_(True)
        ).first()

        if not bom:
            continue

        # Get BOM lines for shipping consumption
        bom_lines = db.query(BOMLine).filter(
            BOMLine.bom_id == bom.id,
            BOMLine.consume_stage == "shipping",
        ).all()

        for line in bom_lines:
            if line.is_cost_only:
                continue

            component = db.query(Product).filter(Product.id == line.component_id).first()
            if not component:
                continue

            # Calculate quantity to consume
            bom_qty = Decimal(str(line.quantity)) * Decimal(str(qty))

            # UOM Conversion: Convert BOM line unit to component's inventory unit
            line_unit = (line.unit or component.unit or "EA").upper()
            component_unit = (component.unit or "EA").upper()

            total_qty, notes = convert_and_generate_notes(
                db=db,
                bom_qty=bom_qty,
                line_unit=line_unit,
                component_unit=component_unit,
                component_name=component.name,
                component_sku=component.sku,
                reference_prefix="Shipping materials for SO#",
                reference_code=sales_order.order_number,
            )

            txn = create_inventory_transaction(
                db=db,
                product_id=line.component_id,
                location_id=location.id,
                transaction_type="consumption",
                quantity=total_qty,
                reference_type="sales_order",
                reference_id=sales_order.id,
                notes=notes,
                cost_per_unit=get_effective_cost_per_inventory_unit(component),
                created_by=created_by,
            )
            transactions.append(txn)

            logger.info(
                f"Consumed {total_qty} {component_unit} of {component.sku} "
                f"for shipping order {sales_order.id}"
            )

    return transactions


def issue_shipped_goods(
    db: Session,
    sales_order: SalesOrder,
    created_by: Optional[str] = None,
) -> List[InventoryTransaction]:
    """
    Issue finished goods from inventory when order ships.

    Args:
        db: Database session
        sales_order: The sales order being shipped
        created_by: User processing the shipment

    Returns:
        List of created inventory transactions
    """
    transactions = []
    location = get_or_create_default_location(db)

    # Get products to ship
    products_to_ship = []

    if sales_order.lines:
        for line in sales_order.lines:
            if line.product_id:
                products_to_ship.append((line.product_id, line.quantity))
    elif sales_order.product_id:
        products_to_ship.append((sales_order.product_id, sales_order.quantity or 1))

    for product_id, qty in products_to_ship:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            continue

        txn = create_inventory_transaction(
            db=db,
            product_id=product_id,
            location_id=location.id,
            transaction_type="shipment",
            quantity=Decimal(str(qty)),
            reference_type="sales_order",
            reference_id=sales_order.id,
            notes=f"Shipped for SO#{sales_order.order_number}: {product.name}",
            cost_per_unit=get_effective_cost_per_inventory_unit(product),
            created_by=created_by,
        )
        transactions.append(txn)

        logger.info(
            f"Issued {qty} units of {product.sku} "
            f"for sales order {sales_order.id}"
        )

    return transactions


def process_shipment(
    db: Session,
    sales_order: SalesOrder,
    created_by: Optional[str] = None,
) -> Tuple[List[InventoryTransaction], List[InventoryTransaction]]:
    """
    Process all inventory transactions for shipping an order.

    1. Consumes packaging materials (shipping stage BOM items)
    2. Issues finished goods from inventory

    Args:
        db: Database session
        sales_order: The sales order being shipped
        created_by: User processing the shipment

    Returns:
        Tuple of (packaging_consumption_txns, goods_issue_txns)
    """
    # Consume packaging materials
    packaging_txns = consume_shipping_materials(
        db=db,
        sales_order=sales_order,
        created_by=created_by,
    )

    # Issue finished goods
    issue_txns = issue_shipped_goods(
        db=db,
        sales_order=sales_order,
        created_by=created_by,
    )

    # Track consumed products for potential MRP recalculation
    # This is called from the endpoint which handles the actual trigger,
    # but we track here for future incremental MRP support
    consumed_product_ids = set()
    for txn in packaging_txns:
        consumed_product_ids.add(txn.product_id)
    
    # Log consumed products for MRP tracking
    if consumed_product_ids:
        logger.debug(
            f"Packaging materials consumed for SO {sales_order.id}",
            extra={
                "sales_order_id": sales_order.id,
                "consumed_product_ids": list(consumed_product_ids)
            }
        )

    return packaging_txns, issue_txns
