"""
Test data factories for FilaOps.

Provides functions to create test entities with sensible defaults.
Used by scenarios.py to create interconnected test data.

Usage:
    from tests.factories import create_test_user, create_test_product

    def test_something(db_session):
        user = create_test_user(db_session, email="test@example.com")
        product = create_test_product(db_session, name="Widget")
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.core.security import hash_password


# =============================================================================
# SEQUENCE MANAGEMENT
# =============================================================================

_sequences: Dict[str, int] = {}


def reset_sequences():
    """Reset all sequences. Call between tests for predictable IDs."""
    global _sequences
    _sequences = {}


def _next(name: str) -> int:
    """Get next sequence number for a given entity type."""
    _sequences[name] = _sequences.get(name, 0) + 1
    return _sequences[name]


def _code(prefix: str, name: str) -> str:
    """Generate a code like SO-2025-0001."""
    seq = _next(name)
    return f"{prefix}-{datetime.now().year}-{seq:04d}"


# =============================================================================
# USER FACTORY
# =============================================================================


def create_test_user(
    db: Session, email: Optional[str] = None, password: str = "TestPass123!", account_type: str = "admin", **overrides
) -> "User":
    """
    Create or get a test user (get-or-create semantics).

    If user with given email already exists, returns the existing user.
    This enables idempotent seeding for E2E tests.

    Args:
        db: Database session
        email: User email (auto-generated if not provided)
        password: Plain text password (will be hashed)
        account_type: 'admin', 'customer', or 'operator'
        **overrides: Additional field overrides

    Returns:
        Created or existing User instance
    """
    from app.models.user import User

    seq = _next("user")
    target_email = email or f"testuser{seq}@example.com"

    # Check if user already exists (idempotent for E2E tests)
    existing = db.query(User).filter_by(email=target_email).first()
    if existing:
        return existing

    user = User(
        email=target_email,
        password_hash=hash_password(password),
        first_name=overrides.pop("first_name", f"Test{seq}"),
        last_name=overrides.pop("last_name", "User"),
        company_name=overrides.pop("company_name", None),
        account_type=account_type,
        status=overrides.pop("status", "active"),
        customer_number=overrides.pop("customer_number", f"CUST-{seq:04d}" if account_type == "customer" else None),
        **overrides,
    )
    db.add(user)
    db.flush()
    return user


# =============================================================================
# VENDOR FACTORY
# =============================================================================


def create_test_vendor(db: Session, name: Optional[str] = None, **overrides) -> "Vendor":
    """
    Create a test vendor.

    Args:
        db: Database session
        name: Vendor name (auto-generated if not provided)
        **overrides: Additional field overrides

    Returns:
        Created Vendor instance
    """
    from app.models.vendor import Vendor

    seq = _next("vendor")

    vendor = Vendor(
        code=overrides.pop("code", f"VND-{seq:03d}"),
        name=name or f"Test Vendor {seq}",
        contact_name=overrides.pop("contact_name", f"Contact {seq}"),
        email=overrides.pop("email", f"vendor{seq}@example.com"),
        phone=overrides.pop("phone", f"555-{seq:04d}"),
        lead_time_days=overrides.pop("lead_time_days", 3),
        payment_terms=overrides.pop("payment_terms", "Net 30"),
        is_active=overrides.pop("is_active", True),
        **overrides,
    )
    db.add(vendor)
    db.flush()
    return vendor


# =============================================================================
# PRODUCT FACTORY
# =============================================================================


def create_test_product(
    db: Session,
    sku: Optional[str] = None,
    name: Optional[str] = None,
    item_type: str = None,
    product_type: str = None,  # Alias for item_type
    procurement_type: str = "make",
    **overrides,
) -> "Product":
    """
    Create a test product.

    Args:
        db: Database session
        sku: Product SKU (auto-generated if not provided)
        name: Product name (auto-generated if not provided)
        item_type: 'finished_good', 'component', 'supply', 'service'
        product_type: Alias for item_type (material -> supply)
        procurement_type: 'make', 'buy', 'make_or_buy'
        **overrides: Additional field overrides

    Returns:
        Created Product instance
    """
    from app.models.product import Product

    seq = _next("product")

    # Handle product_type as alias for item_type
    # Map common aliases: material -> supply
    resolved_item_type = item_type
    if resolved_item_type is None:
        if product_type == "material":
            resolved_item_type = "supply"
        elif product_type == "service":
            resolved_item_type = "service"
        elif product_type:
            resolved_item_type = product_type
        else:
            resolved_item_type = "finished_good"

    product = Product(
        sku=sku or f"PROD-{seq:04d}",
        name=name or f"Test Product {seq}",
        description=overrides.pop("description", f"Test product {seq}"),
        unit=overrides.pop("unit", "EA"),
        item_type=resolved_item_type,
        procurement_type=procurement_type,
        standard_cost=overrides.pop("standard_cost", Decimal("10.00")),
        selling_price=overrides.pop("selling_price", Decimal("25.00")),
        active=overrides.pop("active", True),
        **overrides,
    )
    db.add(product)
    db.flush()
    return product


def create_test_material(
    db: Session,
    sku: Optional[str] = None,
    name: Optional[str] = None,
    unit: str = "G",
    purchase_uom: str = "KG",
    purchase_factor: Decimal = Decimal("1000"),
    **overrides,
) -> "Product":
    """
    Create a test raw material (material item).

    Args:
        db: Database session
        sku: Material SKU (auto-generated if not provided)
        name: Material name (auto-generated if not provided)
        unit: Storage/consumption unit (default: G for grams)
        purchase_uom: Purchase unit from vendor (default: KG)
        purchase_factor: Conversion factor from purchase_uom to unit (default: 1000)
        **overrides: Additional field overrides

    Returns:
        Created Product instance configured as raw material
    """
    from app.models.product import Product

    seq = _next("material")

    material = Product(
        sku=sku or f"MAT-{seq:04d}",
        name=name or f"Test Material {seq}",
        description=overrides.pop("description", f"Test material {seq}"),
        unit=unit,
        purchase_uom=purchase_uom,
        purchase_factor=purchase_factor,
        item_type="material",
        procurement_type="buy",
        is_raw_material=True,
        standard_cost=overrides.pop("standard_cost", Decimal("25.00")),  # $/KG
        active=overrides.pop("active", True),
        **overrides,
    )
    db.add(material)
    db.flush()
    return material


# =============================================================================
# BOM FACTORY
# =============================================================================


def create_test_bom(
    db: Session, product: "Product", lines: Optional[List[Dict[str, Any]]] = None, **overrides
) -> "BOM":
    """
    Create a test BOM with lines.

    Args:
        db: Database session
        product: Product this BOM is for
        lines: List of {"component": Product, "quantity": Decimal, ...}
        **overrides: Additional field overrides

    Returns:
        Created BOM instance with lines
    """
    from app.models.bom import BOM, BOMLine

    seq = _next("bom")

    bom = BOM(
        product_id=product.id,
        code=overrides.pop("code", f"BOM-{product.sku}"),
        name=overrides.pop("name", f"BOM for {product.name}"),
        version=overrides.pop("version", 1),
        revision=overrides.pop("revision", "1.0"),
        active=overrides.pop("active", True),
        **overrides,
    )
    db.add(bom)
    db.flush()

    # Create BOM lines
    if lines:
        total_cost = Decimal("0")
        for i, line_data in enumerate(lines, 1):
            component = line_data["component"]
            qty = Decimal(str(line_data.get("quantity", 1)))

            bom_line = BOMLine(
                bom_id=bom.id,
                component_id=component.id,
                quantity=qty,
                sequence=i,
                scrap_factor=Decimal(str(line_data.get("scrap_factor", 0))),
            )
            db.add(bom_line)
            total_cost += qty * (component.standard_cost or Decimal("0"))

        bom.total_cost = total_cost
        db.flush()

    return bom


def create_test_bom_line(
    db: Session,
    bom: "BOM",
    component: "Product",
    quantity: Decimal = Decimal("1"),
    unit: str = "EA",
    sequence: int = None,
    consume_stage: str = "production",
    is_cost_only: bool = False,
    scrap_factor: Decimal = Decimal("0"),
    **overrides,
) -> "BOMLine":
    """
    Create a test BOM line.

    Args:
        db: Database session
        bom: BOM this line belongs to
        component: Component product
        quantity: Quantity per unit
        unit: Unit of measure
        sequence: Line sequence (auto-generated if not provided)
        consume_stage: When material is consumed (production, assembly, shipping, any)
        is_cost_only: If True, line is for costing only, not inventory
        scrap_factor: Scrap percentage
        **overrides: Additional field overrides

    Returns:
        Created BOMLine instance
    """
    from app.models.bom import BOMLine

    if sequence is None:
        # Auto-increment sequence
        existing = db.query(BOMLine).filter(BOMLine.bom_id == bom.id).count()
        sequence = (existing + 1) * 10

    line = BOMLine(
        bom_id=bom.id,
        component_id=component.id,
        sequence=sequence,
        quantity=quantity,
        unit=unit,
        consume_stage=consume_stage,
        is_cost_only=is_cost_only,
        scrap_factor=scrap_factor,
        **overrides,
    )
    db.add(line)
    db.flush()
    return line


# =============================================================================
# SALES ORDER FACTORY
# =============================================================================


def create_test_sales_order(
    db: Session,
    user: "User",
    product: Optional["Product"] = None,
    lines: Optional[List[Dict[str, Any]]] = None,
    **overrides,
) -> "SalesOrder":
    """
    Create a test sales order.

    For quote-based orders: provide product and quantity in overrides
    For line-item orders: provide lines list

    Args:
        db: Database session
        user: User placing the order
        product: Product for quote-based order
        lines: List of {"product": Product, "quantity": int, "unit_price": Decimal}
        **overrides: Additional field overrides

    Returns:
        Created SalesOrder instance
    """
    from app.models.sales_order import SalesOrder, SalesOrderLine

    order_number = _code("SO", "sales_order")
    quantity = overrides.pop("quantity", 1)
    unit_price = overrides.pop("unit_price", Decimal("25.00"))

    # Calculate totals
    if product:
        unit_price = product.selling_price or unit_price
    total_price = unit_price * quantity
    tax_amount = overrides.pop("tax_amount", Decimal("0"))
    shipping_cost = overrides.pop("shipping_cost", Decimal("0"))
    grand_total = total_price + tax_amount + shipping_cost

    so = SalesOrder(
        order_number=order_number,
        user_id=user.id,
        customer_id=overrides.pop("customer_id", user.id if user.account_type == "customer" else None),
        customer_name=overrides.pop("customer_name", user.full_name),
        customer_email=overrides.pop("customer_email", user.email),
        product_id=product.id if product else None,
        product_name=product.name if product else None,
        quantity=quantity,
        material_type=overrides.pop("material_type", "PLA"),
        finish=overrides.pop("finish", "standard"),
        unit_price=unit_price,
        total_price=total_price,
        tax_amount=tax_amount,
        shipping_cost=shipping_cost,
        grand_total=grand_total,
        status=overrides.pop("status", "confirmed"),
        payment_status=overrides.pop("payment_status", "paid"),
        order_type=overrides.pop("order_type", "line_item" if lines else "quote_based"),
        source=overrides.pop("source", "portal"),
        estimated_completion_date=overrides.pop("estimated_completion_date", datetime.utcnow() + timedelta(days=7)),
        **overrides,
    )
    db.add(so)
    db.flush()

    # Create lines for line-item orders
    if lines:
        for line_data in lines:
            line_product = line_data["product"]
            line_qty = Decimal(str(line_data.get("quantity", 1)))
            line_price = Decimal(str(line_data.get("unit_price", line_product.selling_price or 25)))

            sol = SalesOrderLine(
                sales_order_id=so.id,
                product_id=line_product.id,
                quantity=line_qty,
                unit_price=line_price,
                total=line_qty * line_price,
            )
            db.add(sol)
        db.flush()

    return so


# =============================================================================
# PRODUCTION ORDER FACTORY
# =============================================================================


def create_test_production_order(
    db: Session,
    product: "Product",
    quantity: int = 10,
    sales_order: Optional["SalesOrder"] = None,
    sales_order_line: Optional["SalesOrderLine"] = None,
    **overrides,
) -> "ProductionOrder":
    """
    Create a test production order.

    Args:
        db: Database session
        product: Product to produce
        quantity: Quantity to produce
        sales_order: Linked sales order (for MTO)
        sales_order_line: Linked sales order line
        **overrides: Additional field overrides

    Returns:
        Created ProductionOrder instance
    """
    from app.models.production_order import ProductionOrder

    code = _code("WO", "production_order")

    po = ProductionOrder(
        code=code,
        product_id=product.id,
        quantity_ordered=Decimal(str(quantity)),
        quantity_completed=Decimal(str(overrides.pop("quantity_completed", 0))),
        quantity_scrapped=Decimal(str(overrides.pop("quantity_scrapped", 0))),
        status=overrides.pop("status", "draft"),
        source=overrides.pop("source", "manual" if not sales_order else "sales_order"),
        sales_order_id=sales_order.id if sales_order else None,
        sales_order_line_id=sales_order_line.id if sales_order_line else None,
        priority=overrides.pop("priority", 3),
        due_date=overrides.pop("due_date", date.today() + timedelta(days=7)),
        **overrides,
    )
    db.add(po)
    db.flush()
    return po


# =============================================================================
# PURCHASE ORDER FACTORY
# =============================================================================


def create_test_purchase_order(
    db: Session, vendor: "Vendor", lines: Optional[List[Dict[str, Any]]] = None, **overrides
) -> "PurchaseOrder":
    """
    Create a test purchase order.

    Args:
        db: Database session
        vendor: Vendor for the PO
        lines: List of {"product": Product, "quantity": int, "unit_cost": Decimal}
        **overrides: Additional field overrides

    Returns:
        Created PurchaseOrder instance with lines
    """
    from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine

    po_number = _code("PO", "purchase_order")

    po = PurchaseOrder(
        po_number=po_number,
        vendor_id=vendor.id,
        status=overrides.pop("status", "draft"),
        order_date=overrides.pop("order_date", date.today()),
        expected_date=overrides.pop("expected_date", date.today() + timedelta(days=vendor.lead_time_days or 3)),
        **overrides,
    )
    db.add(po)
    db.flush()

    # Create lines
    subtotal = Decimal("0")
    if lines:
        for i, line_data in enumerate(lines, 1):
            line_product = line_data["product"]
            line_qty = Decimal(str(line_data.get("quantity", 1)))
            line_cost = Decimal(str(line_data.get("unit_cost", line_product.standard_cost or 10)))
            line_total = line_qty * line_cost

            pol = PurchaseOrderLine(
                purchase_order_id=po.id,
                product_id=line_product.id,
                line_number=i,
                quantity_ordered=line_qty,
                quantity_received=Decimal("0"),
                unit_cost=line_cost,
                line_total=line_total,
            )
            db.add(pol)
            subtotal += line_total

        po.subtotal = subtotal
        po.total_amount = subtotal
        db.flush()

    return po


# =============================================================================
# INVENTORY LOCATION FACTORY
# =============================================================================


def create_test_location(db: Session, name: Optional[str] = None, **overrides) -> "InventoryLocation":
    """
    Create a test inventory location.

    Args:
        db: Database session
        name: Location name
        **overrides: Additional field overrides

    Returns:
        Created InventoryLocation instance
    """
    from app.models.inventory import InventoryLocation

    seq = _next("location")

    location = InventoryLocation(
        name=name or f"Location {seq}",
        code=overrides.pop("code", f"LOC-{seq:03d}"),
        type=overrides.pop("type", "warehouse"),
        active=overrides.pop("active", True),
        **overrides,
    )
    db.add(location)
    db.flush()
    return location


def get_or_create_default_location(db: Session) -> "InventoryLocation":
    """
    Get or create a default inventory location for testing.
    """
    from app.models.inventory import InventoryLocation

    location = db.query(InventoryLocation).filter_by(code="TEST-DEFAULT").first()
    if not location:
        location = create_test_location(db, name="Test Default Location", code="TEST-DEFAULT")
    return location


# Alias for create_test_location
def create_test_inventory_location(
    db: Session,
    code: Optional[str] = None,
    name: str = "Test Location",
    location_type: str = "warehouse",
    active: bool = True,
    **overrides,
) -> "InventoryLocation":
    """Alias for create_test_location with different parameter names."""
    return create_test_location(db, name=name, code=code, type=location_type, active=active, **overrides)


# =============================================================================
# INVENTORY FACTORY
# =============================================================================


def create_test_inventory(
    db: Session,
    product: "Product",
    quantity: Decimal = None,
    location: Optional["InventoryLocation"] = None,
    on_hand: Decimal = None,
    allocated: Decimal = None,
    **overrides,
) -> "Inventory":
    """
    Create or update inventory for a product.

    Args:
        db: Database session
        product: Product to add inventory for
        quantity: Quantity on hand (legacy, use on_hand instead)
        location: Inventory location (default location created if not provided)
        on_hand: On hand quantity (alternative to quantity)
        allocated: Allocated quantity
        **overrides: Additional field overrides

    Returns:
        Created or updated Inventory instance
    """
    from app.models.inventory import Inventory

    # Get or create default location if not provided
    if location is None:
        location = get_or_create_default_location(db)

    # Handle on_hand/quantity parameter (on_hand takes precedence)
    on_hand_qty = on_hand if on_hand is not None else (quantity if quantity is not None else Decimal("100"))
    allocated_qty = allocated if allocated is not None else overrides.pop("allocated_quantity", Decimal("0"))

    # Check if inventory record already exists for this product/location
    inv = db.query(Inventory).filter_by(product_id=product.id, location_id=location.id).first()

    if inv:
        inv.on_hand_quantity = on_hand_qty
        inv.allocated_quantity = allocated_qty
    else:
        inv = Inventory(
            product_id=product.id,
            location_id=location.id,
            on_hand_quantity=on_hand_qty,
            allocated_quantity=allocated_qty,
            **overrides,
        )
        db.add(inv)

    db.flush()
    return inv


def create_test_inventory_transaction(
    db: Session, product: "Product", quantity: Decimal, transaction_type: str = "adjustment", **overrides
) -> "InventoryTransaction":
    """
    Create an inventory transaction.

    Args:
        db: Database session
        product: Product for the transaction
        quantity: Transaction quantity (positive for in, negative for out)
        transaction_type: Type of transaction
        **overrides: Additional field overrides

    Returns:
        Created InventoryTransaction instance
    """
    from app.models.inventory import InventoryTransaction

    txn = InventoryTransaction(
        product_id=product.id,
        transaction_type=transaction_type,
        quantity=quantity,
        reference=overrides.pop("reference", f"TEST-{_next('txn'):04d}"),
        notes=overrides.pop("notes", "Test transaction"),
        **overrides,
    )
    db.add(txn)
    db.flush()
    return txn


# =============================================================================
# WORK CENTER FACTORY
# =============================================================================


def create_test_work_center(
    db: Session,
    code: Optional[str] = None,
    name: str = "Test Work Center",
    center_type: str = "production",
    is_active: bool = True,
) -> "WorkCenter":
    """
    Create a test work center.

    Args:
        db: Database session
        code: Work center code (auto-generated if not provided)
        name: Work center name
        center_type: Type of work center
        is_active: Whether work center is active

    Returns:
        Created or existing WorkCenter instance
    """
    from app.models.work_center import WorkCenter

    if code is None:
        code = f"WC-{datetime.now().strftime('%H%M%S%f')}"

    # Check if exists (idempotent)
    existing = db.query(WorkCenter).filter(WorkCenter.code == code).first()
    if existing:
        return existing

    wc = WorkCenter(code=code, name=name, center_type=center_type, is_active=is_active)
    db.add(wc)
    db.flush()
    return wc


# =============================================================================
# RESOURCE/MACHINE FACTORY
# =============================================================================


def create_test_resource(
    db: Session,
    work_center: "WorkCenter",
    code: Optional[str] = None,
    name: str = "Test Resource",
    status: str = "available",
    is_active: bool = True,
) -> "Machine":
    """
    Create a test resource/machine.

    Args:
        db: Database session
        work_center: Parent work center
        code: Resource code (auto-generated if not provided)
        name: Resource name
        status: Resource status (available, busy, maintenance, offline)
        is_active: Whether resource is active

    Returns:
        Created or existing Machine instance
    """
    from app.models.work_center import Machine

    if code is None:
        code = f"RES-{datetime.now().strftime('%H%M%S%f')}"

    # Check if exists (idempotent)
    existing = db.query(Machine).filter(Machine.code == code).first()
    if existing:
        return existing

    resource = Machine(work_center_id=work_center.id, code=code, name=name, status=status, is_active=is_active)
    db.add(resource)
    db.flush()
    return resource


# =============================================================================
# PRODUCTION ORDER OPERATION FACTORY
# =============================================================================


def create_test_po_operation(
    db: Session,
    production_order: "ProductionOrder",
    work_center: "WorkCenter",
    sequence: int = 10,
    operation_code: str = "OP",
    operation_name: str = "Test Operation",
    status: str = "pending",
    planned_run_minutes: int = 60,
    resource: Optional["Machine"] = None,
    actual_start: Optional[datetime] = None,
    actual_end: Optional[datetime] = None,
    scheduled_start: Optional[datetime] = None,
    scheduled_end: Optional[datetime] = None,
    quantity_completed: Optional[Decimal] = None,
    quantity_scrapped: Optional[Decimal] = None,
) -> "ProductionOrderOperation":
    """
    Create a test production order operation.

    Args:
        db: Database session
        production_order: Parent production order
        work_center: Work center for this operation
        sequence: Operation sequence number
        operation_code: Short code for operation
        operation_name: Display name for operation
        status: Operation status (pending, queued, running, complete, skipped)
        planned_run_minutes: Planned run time in minutes
        resource: Specific resource/machine assigned
        actual_start: Actual start time
        actual_end: Actual end time
        scheduled_start: Scheduled start time
        scheduled_end: Scheduled end time
        quantity_completed: Good quantity completed
        quantity_scrapped: Bad quantity scrapped

    Returns:
        Created ProductionOrderOperation instance
    """
    from app.models.production_order import ProductionOrderOperation

    op = ProductionOrderOperation(
        production_order_id=production_order.id,
        work_center_id=work_center.id,
        resource_id=resource.id if resource else None,
        sequence=sequence,
        operation_code=operation_code,
        operation_name=operation_name,
        status=status,
        planned_setup_minutes=Decimal("0"),
        planned_run_minutes=Decimal(str(planned_run_minutes)),
        actual_start=actual_start,
        actual_end=actual_end,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        quantity_completed=quantity_completed or Decimal("0"),
        quantity_scrapped=quantity_scrapped or Decimal("0"),
    )
    db.add(op)
    db.flush()
    return op


# =============================================================================
# ROUTING FACTORY
# =============================================================================


def create_test_routing(
    db: Session, product: "Product", code: Optional[str] = None, name: str = "Test Routing", is_active: bool = True
) -> "Routing":
    """
    Create a test routing.

    Args:
        db: Database session
        product: Product this routing is for
        code: Routing code (auto-generated if not provided)
        name: Routing name
        is_active: Whether routing is active

    Returns:
        Created Routing instance
    """
    from app.models.manufacturing import Routing

    if code is None:
        code = f"RTG-{datetime.now().strftime('%H%M%S%f')}"

    routing = Routing(product_id=product.id, code=code, name=name, is_active=is_active)
    db.add(routing)
    db.flush()
    return routing


# =============================================================================
# ROUTING OPERATION FACTORY
# =============================================================================


def create_test_routing_operation(
    db: Session,
    routing: "Routing",
    work_center: "WorkCenter",
    sequence: int = 10,
    operation_code: str = "PRINT",
    operation_name: str = "Test Operation",
    setup_time_minutes: float = 5,
    run_time_minutes: float = 30,
) -> "RoutingOperation":
    """
    Create a test routing operation.

    Args:
        db: Database session
        routing: Parent routing
        work_center: Work center for this operation
        sequence: Operation sequence number
        operation_code: Short code for operation
        operation_name: Display name for operation
        setup_time_minutes: Setup time in minutes
        run_time_minutes: Run time per unit in minutes

    Returns:
        Created RoutingOperation instance
    """
    from app.models.manufacturing import RoutingOperation

    routing_op = RoutingOperation(
        routing_id=routing.id,
        work_center_id=work_center.id,
        sequence=sequence,
        operation_code=operation_code,
        operation_name=operation_name,
        setup_time_minutes=Decimal(str(setup_time_minutes)),
        run_time_minutes=Decimal(str(run_time_minutes)),
    )
    db.add(routing_op)
    db.flush()
    return routing_op
