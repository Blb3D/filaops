"""
Inventory Transaction Service

Handles automatic inventory transactions for:
- Production completion (consume materials, add finished goods)
- Shipping (consume packaging materials, issue finished goods)
"""
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.inventory import Inventory, InventoryTransaction, InventoryLocation
from app.models.product import Product
from app.models.bom import BOM, BOMLine
from app.models.production_order import ProductionOrder
from app.models.sales_order import SalesOrder
from app.logging_config import get_logger
from app.services.uom_service import convert_quantity_safe, format_conversion_note, UOMConversionError

logger = get_logger(__name__)


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

    return inventory


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
) -> InventoryTransaction:
    """
    Create an inventory transaction and update inventory quantities.

    Args:
        db: Database session
        product_id: Product being transacted
        location_id: Location for the transaction
        transaction_type: receipt, issue, consumption, adjustment
        quantity: Quantity (positive for receipt, positive for issue/consumption - will be subtracted)
        reference_type: production_order, sales_order, etc.
        reference_id: ID of the reference document
        notes: Optional notes
        cost_per_unit: Optional cost per unit
        created_by: User who created the transaction

    Returns:
        Created InventoryTransaction
    """
    # Get or create inventory record
    inventory = get_or_create_inventory(db, product_id, location_id)

    # Create transaction record
    transaction = InventoryTransaction(
        product_id=product_id,
        location_id=location_id,
        transaction_type=transaction_type,
        quantity=quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        cost_per_unit=cost_per_unit,
        created_by=created_by,
        created_at=datetime.utcnow()
    )
    db.add(transaction)

    # Update inventory based on transaction type
    if transaction_type == "receipt":
        inventory.on_hand_quantity = Decimal(str(inventory.on_hand_quantity)) + quantity
    elif transaction_type in ["issue", "consumption", "shipment"]:
        inventory.on_hand_quantity = Decimal(str(inventory.on_hand_quantity)) - quantity

    inventory.updated_at = datetime.utcnow()

    return transaction


def consume_production_materials(
    db: Session,
    production_order: ProductionOrder,
    quantity_completed: Decimal,
    created_by: Optional[str] = None,
) -> List[InventoryTransaction]:
    """
    Consume raw materials based on BOM when production order completes.

    Only consumes items with consume_stage='production' and cost_only=False.

    Args:
        db: Database session
        production_order: The completed production order
        quantity_completed: Number of units completed
        created_by: User completing the order

    Returns:
        List of created inventory transactions
    """
    transactions = []
    location = get_or_create_default_location(db)

    # Get BOM for the product
    bom = db.query(BOM).filter(
        BOM.product_id == production_order.product_id,
        BOM.active == True
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
            cost_per_unit=component.cost,
            created_by=created_by,
        )
        transactions.append(txn)

        logger.info(
            f"Consumed {total_qty} {component_unit} of {component.sku} "
            f"for production order {production_order.id}"
        )

    return transactions


def receive_finished_goods(
    db: Session,
    production_order: ProductionOrder,
    quantity_completed: Decimal,
    created_by: Optional[str] = None,
) -> Optional[InventoryTransaction]:
    """
    Add finished goods to inventory when production order completes.

    Args:
        db: Database session
        production_order: The completed production order
        quantity_completed: Number of units completed
        created_by: User completing the order

    Returns:
        Created inventory transaction, or None if product not found
    """
    location = get_or_create_default_location(db)

    product = db.query(Product).filter(Product.id == production_order.product_id).first()
    if not product:
        logger.error(f"Product {production_order.product_id} not found for production order")
        return None

    # Create receipt transaction for finished goods
    txn = create_inventory_transaction(
        db=db,
        product_id=production_order.product_id,
        location_id=location.id,
        transaction_type="receipt",
        quantity=quantity_completed,
        reference_type="production_order",
        reference_id=production_order.id,
        notes=f"Completed production PO#{production_order.code}",
        cost_per_unit=product.cost,
        created_by=created_by,
    )

    logger.info(
        f"Received {quantity_completed} units of {product.sku} "
        f"from production order {production_order.id}"
    )

    return txn


def process_production_completion(
    db: Session,
    production_order: ProductionOrder,
    quantity_completed: Decimal,
    created_by: Optional[str] = None,
) -> Tuple[List[InventoryTransaction], Optional[InventoryTransaction]]:
    """
    Process all inventory transactions for production order completion.

    1. Consumes raw materials based on BOM (production stage items)
    2. Adds finished goods to inventory

    Args:
        db: Database session
        production_order: The completed production order
        quantity_completed: Number of units completed
        created_by: User completing the order

    Returns:
        Tuple of (material_consumption_txns, finished_goods_receipt_txn)
    """
    # Consume materials
    consumption_txns = consume_production_materials(
        db=db,
        production_order=production_order,
        quantity_completed=quantity_completed,
        created_by=created_by,
    )

    # Receive finished goods
    receipt_txn = receive_finished_goods(
        db=db,
        production_order=production_order,
        quantity_completed=quantity_completed,
        created_by=created_by,
    )

    return consumption_txns, receipt_txn


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
            BOM.active == True
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
                cost_per_unit=component.cost,
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
            cost_per_unit=product.cost,
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
