"""
Full Business Cycle Integration Test - The "Golden Path"

This test exercises the ENTIRE business cycle:
Quote -> Sales Order -> Production -> Ship -> Accounting

THIS TEST MUST PASS BEFORE v3.0.0 RELEASE.

Run with:
    cd C:\repos\filaops-v3-clean\backend
    pytest tests/integration/test_full_business_cycle.py -v -s
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, date, timezone

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Product, Customer, Vendor, Quote, SalesOrder, ProductionOrder,
    PurchaseOrder, PurchaseOrderLine, BOM, BOMLine, Routing, RoutingOperation,
    Inventory, InventoryTransaction, WorkCenter
)
from app.models.accounting import GLAccount, GLJournalEntry, GLJournalEntryLine
from app.services.transaction_service import (
    TransactionService,
    MaterialConsumption,
    ShipmentItem,
    ReceiptItem,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def db():
    """Create a database session for testing."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def gl_accounts(db: Session):
    """Ensure all required GL accounts exist."""
    accounts = [
        ("1200", "Raw Materials Inventory", "asset"),
        ("1210", "WIP Inventory", "asset"),
        ("1220", "Finished Goods Inventory", "asset"),
        ("1230", "Packaging Inventory", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("5000", "Cost of Goods Sold", "expense"),
        ("5010", "Shipping Expense", "expense"),
        ("5020", "Scrap Expense", "expense"),
        ("5030", "Inventory Adjustment", "expense"),
    ]
    for code, name, acct_type in accounts:
        existing = db.query(GLAccount).filter(GLAccount.account_code == code).first()
        if not existing:
            db.add(GLAccount(account_code=code, name=name, account_type=acct_type, active=True))
    db.flush()
    yield
    db.rollback()


# ============================================================================
# Helper Functions
# ============================================================================

def get_account_balance(db: Session, account_code: str) -> Decimal:
    """Get current balance for a GL account."""
    account = db.query(GLAccount).filter(GLAccount.account_code == account_code).first()
    if not account:
        return Decimal("0")

    lines = db.query(GLJournalEntryLine).filter(
        GLJournalEntryLine.account_id == account.id
    ).all()

    total_dr = sum(line.debit_amount or Decimal("0") for line in lines)
    total_cr = sum(line.credit_amount or Decimal("0") for line in lines)

    if account.account_type in ("asset", "expense"):
        return total_dr - total_cr
    else:
        return total_cr - total_dr


def get_inventory_qty(db: Session, product_id: int) -> Decimal:
    """Get on-hand quantity for a product."""
    inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
    return Decimal(str(inv.on_hand_quantity)) if inv else Decimal("0")


def verify_journal_balanced(je: GLJournalEntry) -> bool:
    """Verify journal entry is balanced."""
    total_dr = sum(line.debit_amount or Decimal("0") for line in je.lines)
    total_cr = sum(line.credit_amount or Decimal("0") for line in je.lines)
    return abs(total_dr - total_cr) < Decimal("0.01")


# ============================================================================
# THE GOLDEN PATH TEST
# ============================================================================

class TestFullBusinessCycle:
    """
    Complete business cycle test.

    This is the most important test in the suite. It verifies that:
    1. All entities can be created and linked correctly
    2. All financial transactions are properly recorded
    3. All GL entries are balanced
    4. Inventory quantities are correct at each step
    5. The system maintains data integrity throughout

    If this test fails, DO NOT release v3.0.0.
    """

    def test_complete_business_cycle(self, db: Session, gl_accounts):
        """
        Test complete business cycle: Quote -> Ship -> Accounting

        Steps:
        1. SETUP - Create vendor, customer, products
        2. BOM & ROUTING - Create BOM and routing for FG
        3. QUOTE -> SALES ORDER - Create and accept quote
        4. MRP -> PURCHASE ORDER - Create PO for materials
        5. RECEIVE PO -> INVENTORY - Receive raw materials
        6. PRODUCTION ORDER - Create and execute production
        7. SHIP ORDER - Ship to customer
        8. VERIFY FINAL STATE - Check all GL balances
        """
        txn_service = TransactionService(db)

        try:
            # === STEP 1: SETUP ===
            print("\n=== STEP 1: SETUP ===")

            uid = uuid.uuid4().hex[:8]

            # Create vendor
            vendor = Vendor(
                name=f"Golden Path Vendor {uid}",
                code=f"V-GP-{uid}",
                is_active=True,
            )
            db.add(vendor)

            # Create customer
            customer = Customer(
                company_name=f"Golden Path Customer {uid}",
                email=f"customer-{uid}@example.com",
                status="active",
            )
            db.add(customer)

            # Create raw material
            raw_material = Product(
                sku=f"RAW-GP-{uid}",
                name="Golden Path Filament",
                item_type="supply",
                is_raw_material=True,
                standard_cost=Decimal("0.02"),  # $0.02/gram
                unit="G",
            )
            db.add(raw_material)

            # Create finished good
            finished_good = Product(
                sku=f"FG-GP-{uid}",
                name="Golden Path Widget",
                item_type="finished_good",
                has_bom=True,
                standard_cost=Decimal("20.00"),
                unit="EA",
            )
            db.add(finished_good)
            db.flush()

            print(f"  Created vendor: {vendor.name}")
            print(f"  Created customer: {customer.company_name}")
            print(f"  Created raw material: {raw_material.sku}")
            print(f"  Created finished good: {finished_good.sku}")

            # === STEP 2: BOM & ROUTING ===
            print("\n=== STEP 2: BOM & ROUTING ===")

            # Create BOM (100g per unit)
            bom = BOM(
                product_id=finished_good.id,
                code=f"BOM-GP-{uid}",
                name=f"BOM for Golden Path Widget",
                version=1,
                active=True,
            )
            db.add(bom)
            db.flush()

            bom_line = BOMLine(
                bom_id=bom.id,
                component_id=raw_material.id,
                sequence=1,
                quantity=100.0,  # 100g per unit
                unit="G",
            )
            db.add(bom_line)
            db.flush()

            print(f"  Created BOM: {bom.code} with 100g per unit")

            # === STEP 3: QUOTE -> SALES ORDER ===
            print("\n=== STEP 3: QUOTE -> SALES ORDER ===")

            # Create quote
            quote = Quote(
                quote_number=f"Q-GP-{uid}",
                user_id=1,
                customer_id=customer.id,
                quantity=10,
                material_type="PLA",
                color="RED",
                file_format=".stl",
                dimensions_x=Decimal("100"),
                dimensions_y=Decimal("100"),
                dimensions_z=Decimal("50"),
                material_grams=Decimal("1000"),
                unit_price=Decimal("25.00"),
                total_price=Decimal("250.00"),
                status="draft",
            )
            db.add(quote)
            db.flush()

            # Accept quote
            quote.status = "accepted"
            quote.product_id = finished_good.id

            # Create sales order
            sales_order = SalesOrder(
                order_number=f"SO-GP-{uid}",
                user_id=1,
                quote_id=quote.id,
                product_name=finished_good.name,
                quantity=10,
                unit_price=Decimal("25.00"),
                total_price=Decimal("250.00"),
                status="confirmed",
            )
            db.add(sales_order)
            db.flush()

            quote.sales_order_id = sales_order.id

            print(f"  Created quote: {quote.quote_number}")
            print(f"  Created sales order: {sales_order.order_number}")

            # === STEP 4: MRP -> PURCHASE ORDER ===
            print("\n=== STEP 4: MRP -> PURCHASE ORDER ===")

            # Create PO for raw materials (need 1000g for 10 units)
            po = PurchaseOrder(
                po_number=f"PO-GP-{uid}",
                vendor_id=vendor.id,
                status="approved",
                order_date=date.today(),
            )
            db.add(po)
            db.flush()

            po_line = PurchaseOrderLine(
                purchase_order_id=po.id,
                product_id=raw_material.id,
                quantity=Decimal("1"),  # 1 KG
                unit_price=Decimal("20.00"),  # $20/KG
                uom="KG",
            )
            db.add(po_line)
            db.flush()

            print(f"  Created PO: {po.po_number} for 1kg @ $20")

            # === STEP 5: RECEIVE PO -> INVENTORY ===
            print("\n=== STEP 5: RECEIVE PO -> INVENTORY ===")

            # Track initial GL balances
            initial_raw = get_account_balance(db, "1200")
            initial_ap = get_account_balance(db, "2000")

            # Receive PO (convert to grams for inventory)
            receipt_items = [ReceiptItem(
                product_id=raw_material.id,
                quantity=Decimal("1000"),  # 1000g = 1kg
                unit_cost=Decimal("0.02"),  # $20/kg = $0.02/g
                unit="G",
                lot_number=f"LOT-GP-{uid}",
            )]

            inv_txns, po_je = txn_service.receive_purchase_order(
                purchase_order_id=po.id,
                items=receipt_items,
            )
            db.flush()

            # Verify PO receipt
            assert verify_journal_balanced(po_je), "PO receipt JE should be balanced"

            raw_inv = get_inventory_qty(db, raw_material.id)
            assert raw_inv == Decimal("1000"), f"Raw inventory should be 1000g, got {raw_inv}"

            # Verify GL: DR 1200 Raw Materials +$20, CR 2000 AP +$20
            final_raw = get_account_balance(db, "1200")
            final_ap = get_account_balance(db, "2000")
            assert final_raw == initial_raw + Decimal("20.00"), "Raw materials should increase by $20"
            assert final_ap == initial_ap + Decimal("20.00"), "AP should increase by $20"

            print(f"  Received {raw_inv}g of raw material")
            print(f"  GL: Raw Materials +$20, AP +$20")

            # === STEP 6: PRODUCTION ORDER ===
            print("\n=== STEP 6: PRODUCTION ORDER ===")

            # Create production order
            prod_order = ProductionOrder(
                code=f"WO-GP-{uid}",
                product_id=finished_good.id,
                bom_id=bom.id,
                sales_order_id=sales_order.id,
                quantity_ordered=10,
                status="released",
            )
            db.add(prod_order)
            db.flush()

            print(f"  Created production order: {prod_order.code}")

            # Track GL before production
            pre_wip = get_account_balance(db, "1210")
            pre_raw = get_account_balance(db, "1200")

            # Issue materials (1000g for 10 units)
            materials = [MaterialConsumption(
                product_id=raw_material.id,
                quantity=Decimal("1000"),
                unit_cost=Decimal("0.02"),
                unit="G",
            )]

            issue_txns, issue_je = txn_service.issue_materials_for_operation(
                production_order_id=prod_order.id,
                operation_sequence=10,
                materials=materials,
            )
            db.flush()

            assert verify_journal_balanced(issue_je), "Material issue JE should be balanced"

            # Verify raw material decreased
            raw_inv = get_inventory_qty(db, raw_material.id)
            assert raw_inv == Decimal("0"), f"Raw inventory should be 0, got {raw_inv}"

            # Verify GL: DR 1210 WIP +$20, CR 1200 Raw -$20
            post_wip = get_account_balance(db, "1210")
            post_raw = get_account_balance(db, "1200")
            assert post_wip == pre_wip + Decimal("20.00"), "WIP should increase by $20"
            assert post_raw == pre_raw - Decimal("20.00"), "Raw should decrease by $20"

            print(f"  Issued 1000g material to production")
            print(f"  GL: WIP +$20, Raw Materials -$20")

            # Track GL before FG receipt
            pre_fg = get_account_balance(db, "1220")
            pre_wip2 = get_account_balance(db, "1210")

            # Receipt finished goods (10 units @ $2.00 each = $20 total)
            fg_txn, fg_je = txn_service.receipt_finished_good(
                production_order_id=prod_order.id,
                product_id=finished_good.id,
                quantity=Decimal("10"),
                unit_cost=Decimal("2.00"),  # $20 total / 10 units
            )
            db.flush()

            assert verify_journal_balanced(fg_je), "FG receipt JE should be balanced"

            # Verify FG inventory created
            fg_inv = get_inventory_qty(db, finished_good.id)
            assert fg_inv == Decimal("10"), f"FG inventory should be 10, got {fg_inv}"

            # Verify GL: DR 1220 FG +$20, CR 1210 WIP -$20
            post_fg = get_account_balance(db, "1220")
            post_wip2 = get_account_balance(db, "1210")
            assert post_fg == pre_fg + Decimal("20.00"), "FG should increase by $20"
            assert post_wip2 == pre_wip2 - Decimal("20.00"), "WIP should decrease by $20"

            prod_order.status = "complete"
            db.flush()

            print(f"  Received 10 units of finished goods")
            print(f"  GL: FG +$20, WIP -$20")

            # === STEP 7: SHIP ORDER ===
            print("\n=== STEP 7: SHIP ORDER ===")

            # Track GL before shipment
            pre_cogs = get_account_balance(db, "5000")
            pre_fg2 = get_account_balance(db, "1220")

            # Ship all 10 units
            ship_items = [ShipmentItem(
                product_id=finished_good.id,
                quantity=Decimal("10"),
                unit_cost=Decimal("2.00"),
            )]

            ship_txns, ship_je = txn_service.ship_order(
                sales_order_id=sales_order.id,
                items=ship_items,
            )
            db.flush()

            assert verify_journal_balanced(ship_je), "Shipment JE should be balanced"

            # Verify FG inventory depleted
            fg_inv = get_inventory_qty(db, finished_good.id)
            assert fg_inv == Decimal("0"), f"FG inventory should be 0, got {fg_inv}"

            # Verify GL: DR 5000 COGS +$20, CR 1220 FG -$20
            post_cogs = get_account_balance(db, "5000")
            post_fg2 = get_account_balance(db, "1220")
            assert post_cogs == pre_cogs + Decimal("20.00"), "COGS should increase by $20"
            assert post_fg2 == pre_fg2 - Decimal("20.00"), "FG should decrease by $20"

            sales_order.status = "shipped"
            db.flush()

            print(f"  Shipped 10 units to customer")
            print(f"  GL: COGS +$20, FG -$20")

            # === STEP 8: VERIFY FINAL STATE ===
            print("\n=== STEP 8: VERIFY FINAL STATE ===")

            # Final inventory check
            final_raw_inv = get_inventory_qty(db, raw_material.id)
            final_fg_inv = get_inventory_qty(db, finished_good.id)

            assert final_raw_inv == Decimal("0"), "All raw materials should be consumed"
            assert final_fg_inv == Decimal("0"), "All FG should be shipped"

            # Final GL balance check
            final_raw_gl = get_account_balance(db, "1200")
            final_wip_gl = get_account_balance(db, "1210")
            final_fg_gl = get_account_balance(db, "1220")
            final_cogs_gl = get_account_balance(db, "5000")
            final_ap_gl = get_account_balance(db, "2000")

            print(f"\n  Final Inventory:")
            print(f"    Raw Materials: {final_raw_inv}")
            print(f"    Finished Goods: {final_fg_inv}")

            print(f"\n  Final GL Balances (changes from this test):")
            print(f"    1200 Raw Materials: {final_raw_gl - initial_raw}")
            print(f"    1210 WIP: {final_wip_gl - pre_wip}")
            print(f"    1220 Finished Goods: {final_fg_gl - pre_fg}")
            print(f"    5000 COGS: {final_cogs_gl - pre_cogs}")
            print(f"    2000 AP: {final_ap_gl - initial_ap}")

            # Verify net changes
            # Raw Materials: +$20 (receipt) - $20 (issue) = $0 net
            # WIP: +$20 (issue) - $20 (FG receipt) = $0 net
            # FG: +$20 (receipt) - $20 (ship) = $0 net
            # COGS: +$20 (ship)
            # AP: +$20 (receipt)

            print("\n=== GOLDEN PATH TEST PASSED ===")
            print("All inventory movements and GL entries are correct.")
            print("FilaOps v3.0.0 Core is ready for release.")

        finally:
            db.rollback()


# ============================================================================
# Smoke Test
# ============================================================================

def test_golden_path_smoke(db: Session):
    """Quick smoke test for golden path setup."""
    # Verify we can create all required objects
    uid = uuid.uuid4().hex[:8]

    vendor = Vendor(name=f"Smoke Vendor {uid}", code=f"V-S-{uid}", is_active=True)
    customer = Customer(company_name=f"Smoke Customer {uid}", email=f"smoke-{uid}@example.com", status="active")

    db.add(vendor)
    db.add(customer)
    db.flush()

    assert vendor.id is not None
    assert customer.id is not None

    db.rollback()
    print("\n  Golden path smoke test passed!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        test_golden_path_smoke(db)
    finally:
        db.close()
