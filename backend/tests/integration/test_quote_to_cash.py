"""
Integration Test: Quote-to-Cash Flow

Tests the complete workflow:
1. Create quote with line items
2. Convert quote to sales order
3. Generate production order from SO
4. Allocate materials
5. Execute production operations
6. Complete production -> FG to inventory
7. Ship order -> COGS created
8. Verify all GL entries balanced

Run with:
    cd C:\repos\filaops-v3-clean\backend
    pytest tests/integration/test_quote_to_cash.py -v -s
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, date, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Product, Quote, SalesOrder, ProductionOrder,
    BOM, BOMLine, Inventory, Customer
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
def test_customer(db: Session):
    """Create a test customer."""
    customer = Customer(
        company_name=f"Test Customer {uuid.uuid4().hex[:8]}",
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        status="active",
    )
    db.add(customer)
    db.flush()
    yield customer
    db.rollback()


@pytest.fixture
def test_material(db: Session):
    """Create a test raw material with inventory."""
    uid = uuid.uuid4().hex[:8]
    product = Product(
        sku=f"MAT-{uid}",
        name="Test Filament",
        item_type="supply",
        is_raw_material=True,
        standard_cost=Decimal("0.02"),
        unit="G",
    )
    db.add(product)
    db.flush()

    # Add inventory
    inv = Inventory(
        product_id=product.id,
        location_id=1,
        on_hand_quantity=Decimal("10000"),  # 10kg
        allocated_quantity=Decimal("0"),
    )
    db.add(inv)
    db.flush()

    yield product
    db.rollback()


@pytest.fixture
def test_finished_good(db: Session):
    """Create a test finished good product."""
    uid = uuid.uuid4().hex[:8]
    product = Product(
        sku=f"FG-{uid}",
        name="Test Widget",
        item_type="finished_good",
        standard_cost=Decimal("15.00"),
        unit="EA",
    )
    db.add(product)
    db.flush()
    yield product
    db.rollback()


@pytest.fixture
def test_bom(db: Session, test_finished_good: Product, test_material: Product):
    """Create a test BOM linking FG to material."""
    bom = BOM(
        product_id=test_finished_good.id,
        code=f"BOM-{test_finished_good.sku}",
        name=f"BOM for {test_finished_good.name}",
        version=1,
        active=True,
    )
    db.add(bom)
    db.flush()

    # BOM line: 100g of material per unit
    line = BOMLine(
        bom_id=bom.id,
        component_id=test_material.id,
        sequence=1,
        quantity=100.0,  # 100 grams per unit
        unit="G",
    )
    db.add(line)
    db.flush()

    yield bom
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


def verify_journal_balanced(je: GLJournalEntry) -> bool:
    """Verify journal entry is balanced."""
    total_dr = sum(line.debit_amount or Decimal("0") for line in je.lines)
    total_cr = sum(line.credit_amount or Decimal("0") for line in je.lines)
    return abs(total_dr - total_cr) < Decimal("0.01")


# ============================================================================
# Integration Tests
# ============================================================================

class TestQuoteToCashFlow:
    """Test complete quote-to-cash workflow."""

    def test_complete_flow(
        self,
        db: Session,
        test_customer: Customer,
        test_finished_good: Product,
        test_material: Product,
        test_bom: BOM,
    ):
        """
        Test complete quote → sales order → production → ship flow.
        Verifies inventory movements and GL entries at each step.
        """
        txn_service = TransactionService(db)

        try:
            # Track initial balances
            initial_raw = get_account_balance(db, "1200")
            initial_wip = get_account_balance(db, "1210")
            initial_fg = get_account_balance(db, "1220")
            initial_cogs = get_account_balance(db, "5000")

            # Get initial inventory
            mat_inv = db.query(Inventory).filter(
                Inventory.product_id == test_material.id
            ).first()
            initial_mat_qty = mat_inv.on_hand_quantity

            # === Step 1: Create Quote ===
            quote = Quote(
                quote_number=f"Q-{uuid.uuid4().hex[:8]}",
                user_id=1,
                quantity=10,
                material_type="PLA",
                color="RED",
                file_format=".stl",
                file_size_bytes=102400,
                dimensions_x=Decimal("100"),
                dimensions_y=Decimal("100"),
                dimensions_z=Decimal("50"),
                material_grams=Decimal("1000"),  # 100g * 10 units
                unit_price=Decimal("25.00"),
                total_price=Decimal("250.00"),
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                status="draft",
            )
            db.add(quote)
            db.flush()

            # === Step 2: Accept Quote (creates product link) ===
            quote.status = "accepted"
            quote.product_id = test_finished_good.id
            db.flush()

            # === Step 3: Create Sales Order ===
            sales_order = SalesOrder(
                order_number=f"SO-{uuid.uuid4().hex[:8]}",
                user_id=1,
                quote_id=quote.id,
                product_name=test_finished_good.name,
                quantity=10,
                material_type="PLA",
                unit_price=Decimal("25.00"),
                total_price=Decimal("250.00"),
                grand_total=Decimal("250.00"),
                status="confirmed",
            )
            db.add(sales_order)
            db.flush()

            quote.sales_order_id = sales_order.id

            # === Step 4: Create Production Order ===
            production_order = ProductionOrder(
                code=f"PO-{uuid.uuid4().hex[:8]}",
                product_id=test_finished_good.id,
                bom_id=test_bom.id,
                sales_order_id=sales_order.id,
                quantity_ordered=10,
                status="released",
            )
            db.add(production_order)
            db.flush()

            # === Step 5: Issue Materials (100g * 10 = 1000g) ===
            materials = [MaterialConsumption(
                product_id=test_material.id,
                quantity=Decimal("1000"),
                unit_cost=Decimal("0.02"),
                unit="G",
            )]

            issue_txns, issue_je = txn_service.issue_materials_for_operation(
                production_order_id=production_order.id,
                operation_sequence=10,
                materials=materials,
            )
            db.flush()

            # Verify material issue JE is balanced
            assert verify_journal_balanced(issue_je), "Material issue JE should be balanced"

            # Verify inventory reduced
            db.refresh(mat_inv)
            assert mat_inv.on_hand_quantity == initial_mat_qty - Decimal("1000")

            # === Step 6: Receipt Finished Goods ===
            fg_txn, fg_je = txn_service.receipt_finished_good(
                production_order_id=production_order.id,
                product_id=test_finished_good.id,
                quantity=Decimal("10"),
                unit_cost=Decimal("2.00"),  # 1000g @ $0.02 = $20 / 10 units
            )
            db.flush()

            # Verify FG receipt JE is balanced
            assert verify_journal_balanced(fg_je), "FG receipt JE should be balanced"

            # Verify FG inventory created
            fg_inv = db.query(Inventory).filter(
                Inventory.product_id == test_finished_good.id
            ).first()
            assert fg_inv is not None
            assert fg_inv.on_hand_quantity == Decimal("10")

            # === Step 7: Ship Order ===
            ship_items = [ShipmentItem(
                product_id=test_finished_good.id,
                quantity=Decimal("10"),
                unit_cost=Decimal("2.00"),
            )]

            ship_txns, ship_je = txn_service.ship_order(
                sales_order_id=sales_order.id,
                items=ship_items,
            )
            db.flush()

            # Verify shipment JE is balanced
            assert verify_journal_balanced(ship_je), "Shipment JE should be balanced"

            # Verify FG inventory reduced to 0
            db.refresh(fg_inv)
            assert fg_inv.on_hand_quantity == Decimal("0")

            # === Step 8: Verify Final GL Balances ===
            final_raw = get_account_balance(db, "1200")
            final_wip = get_account_balance(db, "1210")
            final_fg = get_account_balance(db, "1220")
            final_cogs = get_account_balance(db, "5000")

            # Raw materials: decreased by $20 (1000g @ $0.02)
            assert final_raw == initial_raw - Decimal("20.00")

            # FG: should be zero (received and shipped)
            assert final_fg == initial_fg

            # COGS: increased by $20 (shipped FG)
            assert final_cogs == initial_cogs + Decimal("20.00")

        finally:
            db.rollback()


# ============================================================================
# Smoke Test
# ============================================================================

def test_quote_to_cash_smoke(db: Session):
    """Quick smoke test for quote-to-cash flow."""
    # Verify we can create basic objects
    quote = Quote(
        quote_number=f"Q-SMOKE-{uuid.uuid4().hex[:8]}",
        user_id=1,
        quantity=1,
        file_format=".stl",
        file_size_bytes=1024,
        total_price=Decimal("0"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status="draft",
    )
    db.add(quote)
    db.flush()

    assert quote.id is not None
    db.rollback()

    print("\n  Quote-to-cash smoke test passed!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        test_quote_to_cash_smoke(db)
    finally:
        db.close()
