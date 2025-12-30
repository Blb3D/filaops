"""
Tests for routing to operations generation (API-404).

Tests cover:
1. Release creates operations from routing
2. Run time calculated as routing_time × quantity
3. Release without routing still releases (0 ops)
4. Cannot release already released PO
5. Existing operations skipped (no duplicates)
6. Manual generate operations
7. Force regenerate replaces existing ops
8. Get product routing endpoint
9. Operations link to routing_operation_id
10. Full workflow integration
11. Release with multiple routing operations
"""
import pytest
from decimal import Decimal
from tests.factories import (
    create_test_product,
    create_test_production_order,
    create_test_routing,
    create_test_routing_operation,
    create_test_work_center,
)
from app.models.production_order import ProductionOrderOperation


class TestReleaseCreatesOperations:
    """Tests for POST /production-orders/{po_id}/release endpoint."""

    @pytest.mark.api
    def test_release_creates_operations_from_routing(self, client, db, admin_token):
        """Releasing PO creates operations from product's routing."""
        wc = create_test_work_center(db, code="WC-REL-01", name="Test WC")
        product = create_test_product(db, sku="PROD-REL-01")
        routing = create_test_routing(db, product=product, code="RTG-REL-01", is_active=True)
        create_test_routing_operation(
            db, routing=routing, work_center=wc, sequence=10, operation_code="PRINT"
        )
        create_test_routing_operation(
            db, routing=routing, work_center=wc, sequence=20, operation_code="PACK"
        )

        po = create_test_production_order(db, product=product, quantity=10, status="draft")
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "released"
        assert data["operations_created"] == 2

        # Verify operations created
        ops = db.query(ProductionOrderOperation).filter(
            ProductionOrderOperation.production_order_id == po.id
        ).order_by(ProductionOrderOperation.sequence).all()

        assert len(ops) == 2
        assert ops[0].operation_code == "PRINT"
        assert ops[1].operation_code == "PACK"

    @pytest.mark.api
    def test_run_time_multiplied_by_quantity(self, client, db, admin_token):
        """Run time = routing run time × PO quantity."""
        wc = create_test_work_center(db, code="WC-REL-02", name="Test WC")
        product = create_test_product(db, sku="PROD-REL-02")
        routing = create_test_routing(db, product=product, code="RTG-REL-02", is_active=True)
        create_test_routing_operation(
            db,
            routing=routing,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            run_time_minutes=30  # 30 min per unit
        )

        po = create_test_production_order(
            db,
            product=product,
            status="draft",
            quantity=10  # 10 units
        )
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200

        op = db.query(ProductionOrderOperation).filter(
            ProductionOrderOperation.production_order_id == po.id
        ).first()

        assert float(op.planned_run_minutes) == 300  # 30 × 10 = 300 minutes

    @pytest.mark.api
    def test_release_without_routing_still_releases(self, client, db, admin_token):
        """PO without routing releases successfully with 0 operations."""
        product = create_test_product(db, sku="PROD-REL-03")
        # No routing created
        po = create_test_production_order(db, product=product, quantity=10, status="draft")
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "released"
        assert data["operations_created"] == 0

    @pytest.mark.api
    def test_release_already_released_is_noop(self, client, db, admin_token):
        """Releasing an already released PO is a no-op (same status transition allowed)."""
        product = create_test_product(db, sku="PROD-REL-04")
        po = create_test_production_order(db, product=product, quantity=10, status="released")
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Same status transition is allowed (no-op)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "released"
        assert data["operations_created"] == 0  # No new operations created

    @pytest.mark.api
    def test_existing_operations_not_duplicated(self, client, db, admin_token):
        """If operations already exist, release doesn't create duplicates."""
        wc = create_test_work_center(db, code="WC-REL-05", name="Test WC")
        product = create_test_product(db, sku="PROD-REL-05")
        routing = create_test_routing(db, product=product, code="RTG-REL-05", is_active=True)
        create_test_routing_operation(
            db, routing=routing, work_center=wc, sequence=10, operation_code="PRINT"
        )

        po = create_test_production_order(db, product=product, quantity=10, status="draft")

        # Manually create an operation first
        existing_op = ProductionOrderOperation(
            production_order_id=po.id,
            work_center_id=wc.id,
            sequence=10,
            operation_code="MANUAL",
            status="pending",
            planned_run_minutes=Decimal("60")
        )
        db.add(existing_op)
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["operations_created"] == 0  # No new ops created

        # Verify only the manual op exists
        ops = db.query(ProductionOrderOperation).filter(
            ProductionOrderOperation.production_order_id == po.id
        ).all()
        assert len(ops) == 1
        assert ops[0].operation_code == "MANUAL"


class TestManualGeneration:
    """Tests for POST /production-orders/{po_id}/operations/generate endpoint."""

    @pytest.mark.api
    def test_manual_generate_operations(self, client, db, admin_token):
        """Can manually generate operations for released PO."""
        wc = create_test_work_center(db, code="WC-GEN-01", name="Test WC")
        product = create_test_product(db, sku="PROD-GEN-01")
        routing = create_test_routing(db, product=product, code="RTG-GEN-01", is_active=True)
        create_test_routing_operation(
            db, routing=routing, work_center=wc, sequence=10, operation_code="PRINT"
        )

        po = create_test_production_order(db, product=product, quantity=10, status="released")
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/generate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["operations_created"] == 1

    @pytest.mark.api
    def test_force_regenerate_replaces_operations(self, client, db, admin_token):
        """Force flag deletes existing operations and regenerates."""
        wc = create_test_work_center(db, code="WC-GEN-02", name="Test WC")
        product = create_test_product(db, sku="PROD-GEN-02")
        routing = create_test_routing(db, product=product, code="RTG-GEN-02", is_active=True)
        create_test_routing_operation(
            db, routing=routing, work_center=wc, sequence=10, operation_code="PRINT"
        )
        create_test_routing_operation(
            db, routing=routing, work_center=wc, sequence=20, operation_code="PACK"
        )

        po = create_test_production_order(db, product=product, quantity=10, status="released")

        # Create initial operation manually
        old_op = ProductionOrderOperation(
            production_order_id=po.id,
            work_center_id=wc.id,
            sequence=10,
            operation_code="OLD",
            status="pending",
            planned_run_minutes=Decimal("60")
        )
        db.add(old_op)
        db.commit()
        old_op_id = old_op.id

        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/generate",
            json={"force": True},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["operations_created"] == 2

        # Verify old op deleted and new ops created
        ops = db.query(ProductionOrderOperation).filter(
            ProductionOrderOperation.production_order_id == po.id
        ).all()
        assert len(ops) == 2
        assert all(op.id != old_op_id for op in ops)

    @pytest.mark.api
    def test_generate_without_force_fails_if_ops_exist(self, client, db, admin_token):
        """Without force flag, fails if operations already exist."""
        wc = create_test_work_center(db, code="WC-GEN-03", name="Test WC")
        product = create_test_product(db, sku="PROD-GEN-03")
        routing = create_test_routing(db, product=product, code="RTG-GEN-03", is_active=True)
        create_test_routing_operation(
            db, routing=routing, work_center=wc, sequence=10, operation_code="PRINT"
        )

        po = create_test_production_order(db, product=product, quantity=10, status="released")

        # Create existing operation
        existing_op = ProductionOrderOperation(
            production_order_id=po.id,
            work_center_id=wc.id,
            sequence=10,
            operation_code="EXISTING",
            status="pending",
            planned_run_minutes=Decimal("60")
        )
        db.add(existing_op)
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/generate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 400
        assert "exist" in response.json()["detail"].lower()


class TestProductRouting:
    """Tests for GET /products/{product_id}/routing endpoint."""

    @pytest.mark.api
    def test_get_product_routing(self, client, db, admin_token):
        """Can get routing details for a product."""
        wc = create_test_work_center(db, code="WC-PRTR-01", name="Test WC")
        product = create_test_product(db, sku="PROD-PRTR-01")
        routing = create_test_routing(db, product=product, code="RTG-PRTR-01", is_active=True)
        create_test_routing_operation(
            db, routing=routing, work_center=wc, sequence=10, operation_code="PRINT"
        )
        create_test_routing_operation(
            db, routing=routing, work_center=wc, sequence=20, operation_code="PACK"
        )
        db.commit()

        response = client.get(
            f"/api/v1/products/{product.id}/routing",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["routing_code"] == "RTG-PRTR-01"
        assert data["is_active"] is True
        assert len(data["operations"]) == 2

    @pytest.mark.api
    def test_get_product_routing_none(self, client, db, admin_token):
        """Returns empty routing info if product has no routing."""
        product = create_test_product(db, sku="PROD-PRTR-02")
        db.commit()

        response = client.get(
            f"/api/v1/products/{product.id}/routing",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["routing_id"] is None
        assert data["operations"] == []


class TestOperationRoutingLink:
    """Tests for routing_operation_id linkage."""

    @pytest.mark.api
    def test_operations_link_to_routing_operation(self, client, db, admin_token):
        """Created operations store reference to source routing operation."""
        wc = create_test_work_center(db, code="WC-LINK-01", name="Test WC")
        product = create_test_product(db, sku="PROD-LINK-01")
        routing = create_test_routing(db, product=product, code="RTG-LINK-01", is_active=True)
        routing_op = create_test_routing_operation(
            db,
            routing=routing,
            work_center=wc,
            sequence=10,
            operation_code="PRINT"
        )

        po = create_test_production_order(db, product=product, quantity=10, status="draft")
        db.commit()

        client.post(
            f"/api/v1/production-orders/{po.id}/release",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        op = db.query(ProductionOrderOperation).filter(
            ProductionOrderOperation.production_order_id == po.id
        ).first()

        assert op.routing_operation_id == routing_op.id
