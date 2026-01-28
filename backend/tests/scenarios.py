"""
Test data scenarios for E2E testing.

Each scenario creates a complete, interconnected set of test data.
Called via the /api/v1/test/seed endpoint.

Scenarios:
    - empty: Just a test user for login
    - basic: Sample data (users, products, vendors)
    - low-stock-with-allocations: For demand pegging tests
    - production-in-progress: Various production order states
    - full-demand-chain: Complete SO->WO->PO chain for traceability
    - so-with-blocking-issues: Sales order with fulfillment problems
"""

from decimal import Decimal
from typing import Dict, Any
from sqlalchemy.orm import Session

from tests.factories import (
    create_test_user,
    create_test_vendor,
    create_test_product,
    create_test_material,
    create_test_bom,
    create_test_sales_order,
    create_test_production_order,
    create_test_purchase_order,
    create_test_inventory,
    reset_sequences,
)


def seed_empty(db: Session) -> Dict[str, Any]:
    """
    Empty scenario - just creates a test admin user for login.
    Use when you want to test from a clean slate.
    """
    user = create_test_user(
        db,
        email="admin@filaops.test",
        password="TestPass123!",
        account_type="admin",
        first_name="Admin",
        last_name="User",
    )
    db.commit()

    return {"scenario": "empty", "user": {"id": user.id, "email": user.email, "account_type": user.account_type}}


def seed_basic(db: Session) -> Dict[str, Any]:
    """
    Basic scenario with sample data:
    - 1 admin user
    - 1 customer user
    - 2 vendors
    - 3 raw materials
    - 2 finished products with BOMs
    - Initial inventory for materials
    """
    # Users
    admin = create_test_user(
        db,
        email="admin@filaops.test",
        password="TestPass123!",
        account_type="admin",
        first_name="Admin",
        last_name="User",
    )
    customer = create_test_user(
        db,
        email="customer@filaops.test",
        password="TestPass123!",
        account_type="customer",
        first_name="Test",
        last_name="Customer",
        company_name="Acme Corporation",
    )

    # Vendors
    amazon = create_test_vendor(db, name="Amazon Business", lead_time_days=2)
    filament_vendor = create_test_vendor(db, name="Filament World", lead_time_days=5)

    # Raw materials (filament: purchased in KG, stored/consumed in G)
    # Costs are stored per purchase_uom ($/KG) to match vendor pricing
    pla_black = create_test_material(
        db,
        sku="PLA-BLK",
        name="PLA Filament Black",
        unit="G",
        purchase_uom="KG",
        purchase_factor=Decimal("1000"),  # 1 KG = 1000 G
        standard_cost=Decimal("25.00"),  # $/KG
    )
    pla_white = create_test_material(
        db,
        sku="PLA-WHT",
        name="PLA Filament White",
        unit="G",
        purchase_uom="KG",
        purchase_factor=Decimal("1000"),  # 1 KG = 1000 G
        standard_cost=Decimal("25.00"),  # $/KG
    )
    hardware_kit = create_test_material(
        db, sku="HW-M3-KIT", name="M3 Hardware Kit", unit="EA", standard_cost=Decimal("5.00")
    )

    # Finished products
    widget = create_test_product(
        db,
        sku="WIDGET-01",
        name="Widget Assembly",
        item_type="finished_good",
        procurement_type="make",
        selling_price=Decimal("49.99"),
        standard_cost=Decimal("15.00"),
    )
    gadget = create_test_product(
        db,
        sku="GADGET-PRO",
        name="Gadget Pro",
        item_type="finished_good",
        procurement_type="make",
        selling_price=Decimal("89.99"),
        standard_cost=Decimal("30.00"),
    )

    # BOMs (filament quantities in grams)
    widget_bom = create_test_bom(
        db,
        widget,
        lines=[
            {"component": pla_black, "quantity": Decimal("150")},  # 150g per widget
            {"component": hardware_kit, "quantity": Decimal("1")},
        ],
    )
    gadget_bom = create_test_bom(
        db,
        gadget,
        lines=[
            {"component": pla_black, "quantity": Decimal("250")},  # 250g per gadget
            {"component": pla_white, "quantity": Decimal("100")},  # 100g per gadget
            {"component": hardware_kit, "quantity": Decimal("2")},
        ],
    )

    # Initial inventory (filament in grams)
    create_test_inventory(db, pla_black, Decimal("10000"))  # 10 kg = 10000g
    create_test_inventory(db, pla_white, Decimal("5000"))  # 5 kg = 5000g
    create_test_inventory(db, hardware_kit, Decimal("100"))  # 100 kits

    db.commit()

    return {
        "scenario": "basic",
        "users": {
            "admin": {"id": admin.id, "email": admin.email},
            "customer": {"id": customer.id, "email": customer.email},
        },
        "vendors": [
            {"id": amazon.id, "code": amazon.code, "name": amazon.name},
            {"id": filament_vendor.id, "code": filament_vendor.code, "name": filament_vendor.name},
        ],
        "materials": [
            {"id": pla_black.id, "sku": pla_black.sku},
            {"id": pla_white.id, "sku": pla_white.sku},
            {"id": hardware_kit.id, "sku": hardware_kit.sku},
        ],
        "products": [
            {"id": widget.id, "sku": widget.sku, "bom_id": widget_bom.id},
            {"id": gadget.id, "sku": gadget.sku, "bom_id": gadget_bom.id},
        ],
    }


def seed_low_stock_with_allocations(db: Session) -> Dict[str, Any]:
    """
    Scenario for testing demand pegging and low stock views:
    - Products with low stock levels
    - Production orders consuming materials
    - Sales orders linked to production orders
    - Clear allocation chain for traceability
    """
    base = seed_basic(db)

    from app.models import User, Product, Vendor

    customer = db.query(User).filter_by(email="customer@filaops.test").first()
    gadget = db.query(Product).filter_by(sku="GADGET-PRO").first()
    vendor = db.query(Vendor).first()
    pla_black = db.query(Product).filter_by(sku="PLA-BLK").first()

    if not customer or not gadget or not vendor or not pla_black:
        raise ValueError("Base scenario data not found. Run seed_basic first.")

    # Create sales order for 50 gadgets
    so = create_test_sales_order(
        db, user=customer, product=gadget, quantity=50, status="confirmed", payment_status="paid"
    )

    # Create production order linked to SO
    wo1 = create_test_production_order(db, product=gadget, quantity=50, sales_order=so, status="released")

    # This creates demand for:
    # - 12500g PLA black (50 × 250g)
    # - 5000g PLA white (50 × 100g)
    # - 100 hardware kits (50 × 2)
    # But we only have:
    # - 10000g PLA black (shortage of 2500g)
    # - 5000g PLA white (exact)
    # - 100 hardware kits (exact)

    # Create a purchase order to cover the shortage
    # PO is in KG (purchase UOM), inventory converts to G (storage UOM)
    po = create_test_purchase_order(
        db,
        vendor=vendor,
        status="ordered",
        lines=[
            {"product": pla_black, "quantity": 5, "unit_cost": Decimal("25.00")}  # 5 KG @ $25/KG
        ],
    )

    db.commit()

    return {
        **base,
        "scenario": "low-stock-with-allocations",
        "sales_order": {"id": so.id, "order_number": so.order_number},
        "production_order": {"id": wo1.id, "code": wo1.code},
        "purchase_order": {"id": po.id, "po_number": po.po_number},
        "shortage": {
            "product_sku": pla_black.sku,
            "on_hand": 10000,  # grams
            "needed": 12500,  # grams
            "shortage_qty": 2500,  # grams
        },
    }


def seed_production_in_progress(db: Session) -> Dict[str, Any]:
    """
    Scenario for testing production views:
    - Multiple production orders in different statuses
    - Mix of MTO (make-to-order) and MTS (make-to-stock) orders
    - Various completion percentages
    """
    base = seed_basic(db)

    from app.models import User, Product

    customer = db.query(User).filter_by(email="customer@filaops.test").first()
    widget = db.query(Product).filter_by(sku="WIDGET-01").first()
    gadget = db.query(Product).filter_by(sku="GADGET-PRO").first()

    # MTO order - in progress (40% complete)
    so1 = create_test_sales_order(db, user=customer, product=widget, quantity=25, status="in_production")
    wo1 = create_test_production_order(
        db, product=widget, quantity=25, sales_order=so1, status="in_progress", quantity_completed=10
    )

    # MTO order - released (ready to start)
    so2 = create_test_sales_order(db, user=customer, product=gadget, quantity=15, status="confirmed")
    wo2 = create_test_production_order(db, product=gadget, quantity=15, sales_order=so2, status="released")

    # MTS order - draft
    wo3 = create_test_production_order(db, product=widget, quantity=50, status="draft")

    # MTS order - complete
    wo4 = create_test_production_order(db, product=widget, quantity=20, status="closed", quantity_completed=20)

    db.commit()

    return {
        **base,
        "scenario": "production-in-progress",
        "production_orders": [
            {"id": wo1.id, "code": wo1.code, "status": "in_progress", "so": so1.order_number, "percent": 40},
            {"id": wo2.id, "code": wo2.code, "status": "released", "so": so2.order_number, "percent": 0},
            {"id": wo3.id, "code": wo3.code, "status": "draft", "so": None, "percent": 0},
            {"id": wo4.id, "code": wo4.code, "status": "closed", "so": None, "percent": 100},
        ],
    }


def seed_full_demand_chain(db: Session) -> Dict[str, Any]:
    """
    Complete demand chain for E2E traceability testing:

    Customer Order -> Sales Order -> Production Order -> Material Requirements
                                                      -> Purchase Order (for shortages)

    Creates a realistic scenario with:
    - Customer placing an order
    - Sales order confirmed and paid
    - Production order created and released
    - Material requirements calculated
    - Purchase order created for shortages
    """
    # Admin user
    admin = create_test_user(
        db,
        email="admin@filaops.test",
        password="TestPass123!",
        account_type="admin",
        first_name="Admin",
        last_name="User",
    )

    # Customer
    customer = create_test_user(
        db,
        email="customer@acme.test",
        password="TestPass123!",
        account_type="customer",
        first_name="John",
        last_name="Smith",
        company_name="Acme Corporation",
    )

    # Vendor
    vendor = create_test_vendor(db, name="Filament Depot", lead_time_days=3)

    # Raw materials (filament: purchased in KG, stored/consumed in G)
    # Costs are stored per purchase_uom ($/KG) to match vendor pricing
    pla = create_test_material(
        db,
        sku="PLA-BLK-DC",  # Different SKU for this scenario to avoid conflicts
        name="Black PLA Filament",
        unit="G",
        purchase_uom="KG",
        purchase_factor=Decimal("1000"),  # 1 KG = 1000 G
        standard_cost=Decimal("25.00"),  # $/KG
    )
    hardware = create_test_material(
        db, sku="HW-INSERT-M3", name="M3 Heat Set Inserts", unit="EA", standard_cost=Decimal("0.15")
    )
    packaging = create_test_material(
        db, sku="PKG-BOX-SM", name="Small Shipping Box", unit="EA", standard_cost=Decimal("0.50")
    )

    # Finished product
    product = create_test_product(
        db,
        sku="GADGET-PRO-01",
        name="Gadget Pro",
        item_type="finished_good",
        procurement_type="make",
        selling_price=Decimal("89.99"),
        standard_cost=Decimal("35.00"),
    )

    # BOM (filament quantities in grams)
    bom = create_test_bom(
        db,
        product,
        lines=[
            {"component": pla, "quantity": Decimal("250")},  # 250g per unit
            {"component": hardware, "quantity": Decimal("4")},  # 4 inserts per unit
            {"component": packaging, "quantity": Decimal("1")},  # 1 box per unit
        ],
    )

    # Inventory (intentionally short, filament in grams)
    create_test_inventory(db, pla, Decimal("10000"))  # Have 10kg = 10000g
    create_test_inventory(db, hardware, Decimal("150"))  # Have 150 inserts
    create_test_inventory(db, packaging, Decimal("100"))  # Have 100 boxes

    # Sales order for 50 units
    # Needs: 12500g PLA, 200 inserts, 50 boxes
    # Short on: PLA (2500g), inserts (50)
    so = create_test_sales_order(
        db, user=customer, product=product, quantity=50, status="confirmed", payment_status="paid"
    )

    # Production order linked to SO
    wo = create_test_production_order(
        db, product=product, quantity=50, sales_order=so, status="released", bom_id=bom.id
    )

    # Purchase order for shortages
    # PO is in KG (purchase UOM), inventory converts to G (storage UOM)
    po = create_test_purchase_order(
        db,
        vendor=vendor,
        status="ordered",
        lines=[
            {"product": pla, "quantity": 5, "unit_cost": Decimal("25.00")},  # 5 KG @ $25/KG
            {"product": hardware, "quantity": 100, "unit_cost": Decimal("0.15")},
        ],
    )

    db.commit()

    return {
        "scenario": "full-demand-chain",
        "users": {
            "admin": {"id": admin.id, "email": admin.email},
            "customer": {"id": customer.id, "email": customer.email, "company": customer.company_name},
        },
        "vendor": {"id": vendor.id, "code": vendor.code, "name": vendor.name},
        "materials": {
            "pla": {"id": pla.id, "sku": pla.sku, "on_hand": 10000, "needed": 12500},  # grams
            "hardware": {"id": hardware.id, "sku": hardware.sku, "on_hand": 150, "needed": 200},
            "packaging": {"id": packaging.id, "sku": packaging.sku, "on_hand": 100, "needed": 50},
        },
        "product": {"id": product.id, "sku": product.sku, "bom_id": bom.id},
        "sales_order": {"id": so.id, "order_number": so.order_number},
        "production_order": {"id": wo.id, "code": wo.code},
        "purchase_order": {"id": po.id, "po_number": po.po_number},
    }


def seed_so_with_blocking_issues(db: Session) -> Dict[str, Any]:
    """
    Sales order with various blocking issues for fulfillment testing:
    - Line 1: Ready to ship (production complete)
    - Line 2: In production (partial completion)
    - Line 3: Blocked by material shortage
    """
    base = seed_basic(db)

    from app.models import User, Product

    customer = db.query(User).filter_by(email="customer@filaops.test").first()
    widget = db.query(Product).filter_by(sku="WIDGET-01").first()
    gadget = db.query(Product).filter_by(sku="GADGET-PRO").first()

    if not customer or not widget or not gadget:
        raise ValueError("Base scenario data not found. Run seed_basic first.")

    # Multi-line sales order using line items
    so = create_test_sales_order(
        db,
        user=customer,
        quantity=0,  # Will be calculated from lines
        status="in_production",
        lines=[
            {"product": widget, "quantity": 25, "unit_price": widget.selling_price},
            {"product": gadget, "quantity": 15, "unit_price": gadget.selling_price},
            {"product": gadget, "quantity": 10, "unit_price": gadget.selling_price},
        ],
    )

    # Get the SO lines
    from app.models import SalesOrderLine

    lines = db.query(SalesOrderLine).filter_by(sales_order_id=so.id).all()

    # Line 1: Complete production
    wo1 = create_test_production_order(
        db,
        product=widget,
        quantity=25,
        sales_order=so,
        sales_order_line=lines[0] if len(lines) > 0 else None,
        status="closed",
        quantity_completed=25,
    )

    # Line 2: In progress (47% complete)
    wo2 = create_test_production_order(
        db,
        product=gadget,
        quantity=15,
        sales_order=so,
        sales_order_line=lines[1] if len(lines) > 1 else None,
        status="in_progress",
        quantity_completed=7,
    )

    # Line 3: Released but blocked by material
    wo3 = create_test_production_order(
        db,
        product=gadget,
        quantity=10,
        sales_order=so,
        sales_order_line=lines[2] if len(lines) > 2 else None,
        status="released",
    )

    db.commit()

    return {
        **base,
        "scenario": "so-with-blocking-issues",
        "sales_order": {
            "id": so.id,
            "order_number": so.order_number,
            "lines": [
                {"line": 1, "status": "ready", "wo": wo1.code},
                {"line": 2, "status": "in_progress", "wo": wo2.code, "percent": 47},
                {"line": 3, "status": "blocked", "wo": wo3.code, "reason": "material_shortage"},
            ],
        },
    }


# =============================================================================
# SCENARIO REGISTRY
# =============================================================================

SCENARIOS = {
    "empty": seed_empty,
    "basic": seed_basic,
    "low-stock-with-allocations": seed_low_stock_with_allocations,
    "production-in-progress": seed_production_in_progress,
    "production-mto": seed_production_in_progress,  # Alias
    "production-with-shortage": seed_low_stock_with_allocations,  # Alias
    "so-with-blocking-issues": seed_so_with_blocking_issues,
    "full-demand-chain": seed_full_demand_chain,
    "full-production-context": seed_full_demand_chain,  # Alias
}


def seed_scenario(db: Session, scenario_name: str) -> Dict[str, Any]:
    """
    Seed a test scenario by name.

    Args:
        db: Database session
        scenario_name: Name of scenario to seed

    Returns:
        Dict with created object IDs and metadata

    Raises:
        ValueError: If scenario name is unknown
    """
    if scenario_name not in SCENARIOS:
        available = ", ".join(sorted(SCENARIOS.keys()))
        raise ValueError(f"Unknown scenario: {scenario_name}. Available: {available}")

    # Reset sequences for predictable IDs
    reset_sequences()

    # Run the scenario
    return SCENARIOS[scenario_name](db)


def cleanup_test_data(db: Session) -> Dict[str, Any]:
    """
    Remove all test data. Use between tests or after E2E runs.

    WARNING: This truncates tables! Only use on test database.
    """
    from sqlalchemy import text

    # Order matters due to foreign keys
    tables = [
        "inventory_transactions",
        "inventory",
        "inventory_locations",
        "purchase_order_lines",
        "purchase_orders",
        "production_order_operations",
        "production_orders",
        "sales_order_lines",
        "sales_orders",
        "bom_lines",
        "boms",
        "quotes",
        "products",
        "vendors",
        "refresh_tokens",
        # "users",  # REMOVED: preserve admin accounts
    ]

    cleaned = []
    for table in tables:
        try:
            db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            cleaned.append(table)
        except Exception:
            # Table might not exist
            pass

    # Only delete test users (preserve real admin accounts)
    try:
        db.execute(text("DELETE FROM users WHERE email LIKE '%@filaops.test'"))
        cleaned.append("users (test accounts only)")
    except Exception:
        pass

    db.commit()

    return {"cleaned": True, "tables": cleaned}
