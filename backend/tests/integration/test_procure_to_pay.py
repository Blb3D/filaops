"""
Integration Test: Procure-to-Pay Flow

Tests the complete workflow:
1. Run MRP -> recommendations generated
2. Create PO from recommendation
3. Receive PO -> Raw materials to inventory
4. Verify AP accrual created
5. Verify inventory transaction linked to GL

Run with:
    cd C:\repos\filaops-v3-clean\backend
    pytest tests/integration/test_procure_to_pay.py -v -s
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, date, timezone

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Product, Vendor, PurchaseOrder, PurchaseOrderLine,
    Inventory, InventoryTransaction
)
from app.models.accounting import GLAccount, GLJournalEntry, GLJournalEntryLine
from app.services.transaction_service import TransactionService, ReceiptItem


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
def test_vendor(db: Session):
    """Create a test vendor."""
    vendor = Vendor(
        name=f"Test Vendor {uuid.uuid4().hex[:8]}",
        code=f"V-{uuid.uuid4().hex[:8]}",
        email=f"vendor-{uuid.uuid4().hex[:8]}@example.com",
        is_active=True,
    )
    db.add(vendor)
    db.flush()
    yield vendor
    db.rollback()


@pytest.fixture
def test_material(db: Session):
    """Create a test raw material."""
    uid = uuid.uuid4().hex[:8]
    product = Product(
        sku=f"MAT-P2P-{uid}",
        name="Test Filament for P2P",
        item_type="supply",
        is_raw_material=True,
        standard_cost=Decimal("25.00"),  # $25/KG
        unit="KG",
    )
    db.add(product)
    db.flush()
    yield product
    db.rollback()


@pytest.fixture
def gl_accounts(db: Session):
    """Ensure GL accounts exist."""
    accounts = [
        ("1200", "Raw Materials Inventory", "asset"),
        ("2000", "Accounts Payable", "liability"),
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


# ============================================================================
# Integration Tests
# ============================================================================

class TestProcureToPayFlow:
    """Test complete procure-to-pay workflow."""

    def test_po_receipt_creates_inventory_and_gl(
        self,
        db: Session,
        gl_accounts,
        test_vendor: Vendor,
        test_material: Product,
    ):
        """
        Test PO receipt creates inventory and GL entries.
        """
        txn_service = TransactionService(db)

        try:
            # Track initial balances
            initial_raw = get_account_balance(db, "1200")
            initial_ap = get_account_balance(db, "2000")
            initial_inv = get_inventory_qty(db, test_material.id)

            # === Step 1: Create Purchase Order ===
            po = PurchaseOrder(
                po_number=f"PO-{uuid.uuid4().hex[:8]}",
                vendor_id=test_vendor.id,
                status="approved",
                order_date=date.today(),
            )
            db.add(po)
            db.flush()

            # Add PO line
            po_line = PurchaseOrderLine(
                purchase_order_id=po.id,
                product_id=test_material.id,
                quantity=Decimal("5"),  # 5 KG
                unit_price=Decimal("25.00"),
                uom="KG",
            )
            db.add(po_line)
            db.flush()

            # === Step 2: Receive PO ===
            receipt_items = [ReceiptItem(
                product_id=test_material.id,
                quantity=Decimal("5000"),  # 5000g = 5kg
                unit_cost=Decimal("0.025"),  # $25/kg = $0.025/g
                unit="G",
                lot_number=f"LOT-{uuid.uuid4().hex[:8]}",
            )]

            inv_txns, je = txn_service.receive_purchase_order(
                purchase_order_id=po.id,
                items=receipt_items,
            )
            db.flush()

            # === Step 3: Verify Inventory Updated ===
            final_inv = get_inventory_qty(db, test_material.id)
            expected_qty = initial_inv + Decimal("5000")  # In grams
            assert final_inv == expected_qty, f"Inventory should be {expected_qty}, got {final_inv}"

            # === Step 4: Verify GL Entries ===
            # Raw Materials (DR): increased by $125 (5kg @ $25/kg)
            final_raw = get_account_balance(db, "1200")
            assert final_raw == initial_raw + Decimal("125.00")

            # Accounts Payable (CR): increased by $125
            final_ap = get_account_balance(db, "2000")
            assert final_ap == initial_ap + Decimal("125.00")

            # === Step 5: Verify Transaction Linked to JE ===
            assert len(inv_txns) == 1
            assert inv_txns[0].journal_entry_id == je.id
            assert inv_txns[0].transaction_type == "receipt"

            # === Step 6: Verify JE is Balanced ===
            total_dr = sum(line.debit_amount or Decimal("0") for line in je.lines)
            total_cr = sum(line.credit_amount or Decimal("0") for line in je.lines)
            assert abs(total_dr - total_cr) < Decimal("0.01"), "JE should be balanced"

        finally:
            db.rollback()

    def test_partial_po_receipt(
        self,
        db: Session,
        gl_accounts,
        test_vendor: Vendor,
        test_material: Product,
    ):
        """
        Test partial PO receipt.
        """
        txn_service = TransactionService(db)

        try:
            # Create PO
            po = PurchaseOrder(
                po_number=f"PO-PARTIAL-{uuid.uuid4().hex[:8]}",
                vendor_id=test_vendor.id,
                status="approved",
                order_date=date.today(),
            )
            db.add(po)
            db.flush()

            po_line = PurchaseOrderLine(
                purchase_order_id=po.id,
                product_id=test_material.id,
                quantity=Decimal("10"),  # 10 KG ordered
                unit_price=Decimal("25.00"),
                uom="KG",
                received_quantity=Decimal("0"),
            )
            db.add(po_line)
            db.flush()

            initial_inv = get_inventory_qty(db, test_material.id)

            # First receipt: 4kg (4000g)
            items1 = [ReceiptItem(
                product_id=test_material.id,
                quantity=Decimal("4000"),
                unit_cost=Decimal("0.025"),
                unit="G",
            )]
            txn_service.receive_purchase_order(po.id, items1)
            db.flush()

            mid_inv = get_inventory_qty(db, test_material.id)
            assert mid_inv == initial_inv + Decimal("4000")

            # Second receipt: 6kg (6000g)
            items2 = [ReceiptItem(
                product_id=test_material.id,
                quantity=Decimal("6000"),
                unit_cost=Decimal("0.025"),
                unit="G",
            )]
            txn_service.receive_purchase_order(po.id, items2)
            db.flush()

            final_inv = get_inventory_qty(db, test_material.id)
            assert final_inv == initial_inv + Decimal("10000")  # Full 10kg received

        finally:
            db.rollback()


# ============================================================================
# Smoke Test
# ============================================================================

def test_procure_to_pay_smoke(db: Session):
    """Quick smoke test."""
    # Verify we can create a PO
    po = PurchaseOrder(
        po_number=f"PO-SMOKE-{uuid.uuid4().hex[:8]}",
        status="draft",
        order_date=date.today(),
    )
    db.add(po)
    db.flush()

    assert po.id is not None
    db.rollback()

    print("\n  Procure-to-pay smoke test passed!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        test_procure_to_pay_smoke(db)
    finally:
        db.close()
