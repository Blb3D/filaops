"""
Unit tests for ScrapService

Tests verify:
1. Cascade calculation includes materials from current + prior operations
2. Scrap records created with correct quantities and costs
3. GL journal entries balanced (DR Scrap 5020 = CR WIP 1210)
4. Downstream operations auto-skipped when no good pieces remain
5. Replacement production orders linked correctly (remake_of_id)
6. Validation rejects invalid scrap reasons and quantities

Run with:
    cd backend
    pytest tests/services/test_scrap_service.py -v

Run with coverage:
    pytest tests/services/test_scrap_service.py -v --cov=app/services/scrap_service
"""
import pytest
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.scrap_service import (
    calculate_scrap_cascade,
    process_operation_scrap,
    auto_skip_downstream_operations,
    create_replacement_production_order,
    get_prior_operations_inclusive,
    ScrapError,
)
from app.models.production_order import (
    ProductionOrder,
    ProductionOrderOperation,
    ProductionOrderOperationMaterial,
    ScrapRecord,
)
from app.models.product import Product
from app.models.scrap_reason import ScrapReason
from app.models.accounting import GLJournalEntry, GLJournalEntryLine


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
        db.rollback()  # Rollback any changes
        db.close()


@pytest.fixture
def test_product(db: Session) -> Product:
    """Create a test finished good product."""
    product = Product(
        sku=f"TEST-FG-{datetime.utcnow().timestamp():.0f}",
        name="Test Finished Good",
        item_type="finished_good",
        standard_cost=Decimal("10.00"),
        active=True,
    )
    db.add(product)
    db.flush()
    return product


@pytest.fixture
def test_material(db: Session) -> Product:
    """Create a test raw material."""
    material = Product(
        sku=f"TEST-MAT-{datetime.utcnow().timestamp():.0f}",
        name="Test Material",
        item_type="raw_material",
        standard_cost=Decimal("2.50"),
        active=True,
    )
    db.add(material)
    db.flush()
    return material


@pytest.fixture
def test_scrap_reason(db: Session) -> ScrapReason:
    """Create a test scrap reason."""
    reason = db.query(ScrapReason).filter(ScrapReason.code == "test_reason").first()
    if not reason:
        reason = ScrapReason(
            code="test_reason",
            name="Test Reason",
            description="Test scrap reason for testing",
            category="production",
            active=True,
        )
        db.add(reason)
        db.flush()
    return reason


@pytest.fixture
def test_production_order(db: Session, test_product: Product) -> ProductionOrder:
    """Create a test production order with operations."""
    po = ProductionOrder(
        code=f"PO-TEST-{datetime.utcnow().timestamp():.0f}",
        product_id=test_product.id,
        quantity_ordered=Decimal("10"),
        quantity_completed=Decimal("0"),
        quantity_scrapped=Decimal("0"),
        source="test",
        status="in_progress",
    )
    db.add(po)
    db.flush()
    return po


@pytest.fixture
def test_operations(
    db: Session,
    test_production_order: ProductionOrder,
    test_material: Product
) -> list[ProductionOrderOperation]:
    """Create test operations for the production order."""
    ops = []
    for i in range(1, 4):
        op = ProductionOrderOperation(
            production_order_id=test_production_order.id,
            work_center_id=1,
            sequence=i * 10,
            operation_code=f"OP{i * 10}",
            operation_name=f"Operation {i}",
            status="pending" if i > 1 else "complete",
            quantity_completed=Decimal("10") if i == 1 else Decimal("0"),
            quantity_scrapped=Decimal("0"),
        )
        db.add(op)
        db.flush()
        ops.append(op)

        # Add material to first two operations
        if i <= 2:
            mat = ProductionOrderOperationMaterial(
                production_order_operation_id=op.id,
                component_id=test_material.id,
                quantity_required=Decimal("10.0") * Decimal(str(i)),  # 10, 20
                quantity_allocated=Decimal("0"),
                quantity_consumed=Decimal("0"),
                unit="EA",
                status="pending",
            )
            db.add(mat)

    db.flush()
    return ops


# ============================================================================
# Tests: calculate_scrap_cascade
# ============================================================================

class TestCalculateScrapCascade:
    """Tests for calculate_scrap_cascade function."""

    def test_cascade_includes_prior_operations(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
        test_material: Product,
    ):
        """Verify cascade includes materials from all prior operations."""
        # Mark second operation as running for scrap
        test_operations[1].status = "running"
        db.flush()

        result = calculate_scrap_cascade(
            db=db,
            po_id=test_production_order.id,
            op_id=test_operations[1].id,
            quantity=2,
        )

        # Should have materials from op 1 and op 2
        assert result["operations_affected"] == 2
        assert len(result["materials_consumed"]) == 2

        # Verify cost calculation (qty_per_unit * scrap_qty * unit_cost)
        # Op1: 10/10 = 1 per unit * 2 scrapped * $2.50 = $5.00
        # Op2: 20/10 = 2 per unit * 2 scrapped * $2.50 = $10.00
        # Total = $15.00
        assert result["total_cost"] == 15.0

    def test_cascade_first_operation_only(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
        test_material: Product,
    ):
        """Scrapping at first operation only includes its materials."""
        result = calculate_scrap_cascade(
            db=db,
            po_id=test_production_order.id,
            op_id=test_operations[0].id,
            quantity=2,
        )

        assert result["operations_affected"] == 1
        assert len(result["materials_consumed"]) == 1

    def test_cascade_invalid_po_raises_error(self, db: Session):
        """Invalid production order ID raises ScrapError."""
        with pytest.raises(ScrapError) as exc_info:
            calculate_scrap_cascade(db, 999999, 1, 1)

        assert exc_info.value.status_code == 404

    def test_cascade_invalid_operation_raises_error(
        self,
        db: Session,
        test_production_order: ProductionOrder,
    ):
        """Invalid operation ID raises ScrapError."""
        with pytest.raises(ScrapError) as exc_info:
            calculate_scrap_cascade(db, test_production_order.id, 999999, 1)

        assert exc_info.value.status_code == 404


# ============================================================================
# Tests: process_operation_scrap
# ============================================================================

class TestProcessOperationScrap:
    """Tests for process_operation_scrap function."""

    def test_scrap_creates_journal_entry(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
        test_scrap_reason: ScrapReason,
    ):
        """Scrap creates balanced GL journal entry."""
        result = process_operation_scrap(
            db=db,
            po_id=test_production_order.id,
            op_id=test_operations[0].id,
            quantity_scrapped=2,
            scrap_reason_code=test_scrap_reason.code,
            notes="Test scrap",
        )

        assert result["success"] is True
        assert result["journal_entry_number"] is not None

        # Verify journal entry is balanced
        entry = db.query(GLJournalEntry).filter(
            GLJournalEntry.entry_number == result["journal_entry_number"]
        ).first()

        total_dr = sum(l.debit_amount or Decimal("0") for l in entry.lines)
        total_cr = sum(l.credit_amount or Decimal("0") for l in entry.lines)
        assert total_dr == total_cr

    def test_scrap_creates_scrap_records(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
        test_scrap_reason: ScrapReason,
    ):
        """Scrap creates ScrapRecord entries."""
        result = process_operation_scrap(
            db=db,
            po_id=test_production_order.id,
            op_id=test_operations[0].id,
            quantity_scrapped=2,
            scrap_reason_code=test_scrap_reason.code,
        )

        assert result["scrap_records_created"] >= 1

        # Verify scrap records exist
        records = db.query(ScrapRecord).filter(
            ScrapRecord.production_order_id == test_production_order.id
        ).all()
        assert len(records) >= 1

    def test_scrap_updates_quantities(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
        test_scrap_reason: ScrapReason,
    ):
        """Scrap updates operation and PO scrap quantities."""
        original_po_scrapped = test_production_order.quantity_scrapped or Decimal("0")
        original_op_scrapped = test_operations[0].quantity_scrapped or Decimal("0")

        process_operation_scrap(
            db=db,
            po_id=test_production_order.id,
            op_id=test_operations[0].id,
            quantity_scrapped=3,
            scrap_reason_code=test_scrap_reason.code,
        )

        db.refresh(test_production_order)
        db.refresh(test_operations[0])

        assert test_production_order.quantity_scrapped == original_po_scrapped + 3
        assert test_operations[0].quantity_scrapped == original_op_scrapped + 3

    def test_scrap_invalid_reason_raises_error(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
    ):
        """Invalid scrap reason raises ScrapError."""
        with pytest.raises(ScrapError) as exc_info:
            process_operation_scrap(
                db=db,
                po_id=test_production_order.id,
                op_id=test_operations[0].id,
                quantity_scrapped=2,
                scrap_reason_code="invalid_reason_xxx",
            )

        assert exc_info.value.status_code == 400

    def test_scrap_exceeds_available_raises_error(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
        test_scrap_reason: ScrapReason,
    ):
        """Scrapping more than available raises ScrapError."""
        # First op has 10 completed
        with pytest.raises(ScrapError) as exc_info:
            process_operation_scrap(
                db=db,
                po_id=test_production_order.id,
                op_id=test_operations[0].id,
                quantity_scrapped=15,  # More than 10 completed
                scrap_reason_code=test_scrap_reason.code,
            )

        assert exc_info.value.status_code == 400
        assert "available to scrap" in exc_info.value.message.lower()


# ============================================================================
# Tests: auto_skip_downstream_operations
# ============================================================================

class TestAutoSkipDownstream:
    """Tests for auto_skip_downstream_operations function."""

    def test_skips_pending_downstream_ops(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
    ):
        """All pending downstream operations are skipped."""
        # First op complete with 0 good pieces
        test_operations[0].quantity_completed = Decimal("5")
        test_operations[0].quantity_scrapped = Decimal("5")
        test_operations[0].status = "complete"
        db.flush()

        skipped = auto_skip_downstream_operations(
            db, test_production_order, test_operations[0]
        )

        # Ops 2 and 3 should be skipped
        assert skipped == 2
        db.refresh(test_operations[1])
        db.refresh(test_operations[2])
        assert test_operations[1].status == "skipped"
        assert test_operations[2].status == "skipped"

    def test_does_not_skip_completed_ops(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
    ):
        """Already completed operations are not skipped."""
        # Make second op complete
        test_operations[1].status = "complete"
        test_operations[1].quantity_completed = Decimal("5")
        db.flush()

        skipped = auto_skip_downstream_operations(
            db, test_production_order, test_operations[0]
        )

        # Only op 3 should be skipped (op 2 is already complete)
        assert skipped == 1
        db.refresh(test_operations[1])
        assert test_operations[1].status == "complete"


# ============================================================================
# Tests: create_replacement_production_order
# ============================================================================

class TestCreateReplacementOrder:
    """Tests for create_replacement_production_order function."""

    def test_replacement_links_to_original(
        self,
        db: Session,
        test_production_order: ProductionOrder,
    ):
        """Replacement PO has remake_of_id pointing to original."""
        replacement = create_replacement_production_order(
            db=db,
            original_po=test_production_order,
            quantity=5,
            scrap_reason="test_reason",
        )

        assert replacement.remake_of_id == test_production_order.id
        assert replacement.quantity_ordered == Decimal("5")
        assert replacement.status == "draft"
        assert replacement.source == "remake"

    def test_replacement_inherits_product_and_routing(
        self,
        db: Session,
        test_production_order: ProductionOrder,
    ):
        """Replacement PO has same product/BOM/routing as original."""
        replacement = create_replacement_production_order(
            db=db,
            original_po=test_production_order,
            quantity=3,
            scrap_reason="test_reason",
        )

        assert replacement.product_id == test_production_order.product_id
        assert replacement.bom_id == test_production_order.bom_id
        assert replacement.routing_id == test_production_order.routing_id

    def test_replacement_has_scrap_reason_in_notes(
        self,
        db: Session,
        test_production_order: ProductionOrder,
    ):
        """Replacement PO notes include scrap reason."""
        replacement = create_replacement_production_order(
            db=db,
            original_po=test_production_order,
            quantity=2,
            scrap_reason="layer_shift",
        )

        assert "layer_shift" in replacement.notes
        assert test_production_order.code in replacement.notes


# ============================================================================
# Tests: get_prior_operations_inclusive
# ============================================================================

class TestGetPriorOperationsInclusive:
    """Tests for get_prior_operations_inclusive function."""

    def test_returns_operations_up_to_target(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
    ):
        """Returns all operations from first to target."""
        result = get_prior_operations_inclusive(
            test_production_order,
            test_operations[1]  # Second operation
        )

        assert len(result) == 2
        assert result[0].id == test_operations[0].id
        assert result[1].id == test_operations[1].id

    def test_returns_single_for_first_operation(
        self,
        db: Session,
        test_production_order: ProductionOrder,
        test_operations: list[ProductionOrderOperation],
    ):
        """Returns only first operation when targeting first."""
        result = get_prior_operations_inclusive(
            test_production_order,
            test_operations[0]  # First operation
        )

        assert len(result) == 1
        assert result[0].id == test_operations[0].id
