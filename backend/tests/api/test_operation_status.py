"""
Tests for operation status transition endpoints.

TDD: Write tests first, then implement to make them pass.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from tests.factories import (
    create_test_product,
    create_test_production_order,
    create_test_work_center,
    create_test_resource,
    create_test_po_operation,
)


class TestListOperations:
    """Tests for GET /api/v1/production-orders/{po_id}/operations"""

    @pytest.mark.api
    def test_list_operations_success(self, client, db, admin_token):
        """List operations for a production order."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-001")
        wc_print = create_test_work_center(db, code="WC-PRINT", name="Print Station")
        wc_clean = create_test_work_center(db, code="WC-CLEAN", name="Cleaning")

        po = create_test_production_order(db, product=product, quantity=10, status="released")

        op1 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc_print,
            sequence=10,
            operation_code="PRINT",
            operation_name="3D Print",
            planned_run_minutes=240,
            status="pending",
        )
        op2 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc_clean,
            sequence=20,
            operation_code="CLEAN",
            operation_name="Post-Print Clean",
            planned_run_minutes=30,
            status="pending",
        )
        db.commit()

        # Execute
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations", headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["sequence"] == 10
        assert data[0]["operation_code"] == "PRINT"
        assert data[0]["status"] == "pending"
        assert data[1]["sequence"] == 20
        assert data[1]["operation_code"] == "CLEAN"

    @pytest.mark.api
    def test_list_operations_po_not_found(self, client, db, admin_token):
        """Non-existent PO returns 404."""
        response = client.get(
            "/api/v1/production-orders/99999/operations", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404


class TestStartOperation:
    """Tests for POST /api/v1/production-orders/{po_id}/operations/{op_id}/start"""

    @pytest.mark.api
    def test_start_first_operation_success(self, client, db, admin_token):
        """Start first operation in sequence."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-002")
        wc = create_test_work_center(db, code="WC-PRINT-2", name="Print Station")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-01", name="Printer 1")

        po = create_test_production_order(db, product=product, quantity=10, status="released")
        op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            operation_name="3D Print",
            planned_run_minutes=240,
            status="pending",
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"resource_id": resource.id, "operator_name": "John D"},
        )

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "running"
        assert data["resource_id"] == resource.id
        assert data["actual_start"] is not None
        assert data["production_order"]["status"] == "in_progress"

    @pytest.mark.api
    def test_start_operation_previous_not_complete(self, client, db, admin_token):
        """Cannot start operation if previous not complete."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-003")
        wc = create_test_work_center(db, code="WC-PRINT-3", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="released")
        op1 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            status="pending",  # Not complete!
        )
        op2 = create_test_po_operation(
            db, production_order=po, work_center=wc, sequence=20, operation_code="CLEAN", status="pending"
        )
        db.commit()

        # Execute - try to start op2 when op1 not done
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op2.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={},
        )

        # Verify
        assert response.status_code == 400
        assert "previous operation" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_start_operation_already_running(self, client, db, admin_token):
        """Cannot start operation that is already running."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-004")
        wc = create_test_work_center(db, code="WC-PRINT-4", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            status="running",  # Already running
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={},
        )

        # Verify
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_start_operation_po_derives_in_progress(self, client, db, admin_token):
        """Starting first operation sets PO status to in_progress."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-005")
        wc = create_test_work_center(db, code="WC-PRINT-5", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="released")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc, sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        assert po.status == "released"

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={},
        )

        # Verify
        assert response.status_code == 200

        # Refresh PO from DB
        db.refresh(po)
        assert po.status == "in_progress"


class TestCompleteOperation:
    """Tests for POST /api/v1/production-orders/{po_id}/operations/{op_id}/complete"""

    @pytest.mark.api
    def test_complete_operation_success(self, client, db, admin_token):
        """Complete a running operation."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-006")
        wc = create_test_work_center(db, code="WC-PRINT-6", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            status="running",
            actual_start=datetime.utcnow() - timedelta(hours=2),
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 10, "quantity_scrapped": 0},
        )

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "complete"
        assert data["actual_end"] is not None
        assert Decimal(data["quantity_completed"]) == Decimal("10")

    @pytest.mark.api
    def test_complete_operation_not_running(self, client, db, admin_token):
        """Cannot complete operation that is not running."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-007")
        wc = create_test_work_center(db, code="WC-PRINT-7", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="released")
        op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            status="pending",  # Not running
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 10},
        )

        # Verify
        assert response.status_code == 400
        assert "not running" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_complete_last_operation_completes_po(self, client, db, admin_token):
        """Completing last operation sets PO status to complete."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-008")
        wc = create_test_work_center(db, code="WC-PRINT-8", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op1 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            status="complete",  # Already done
            quantity_completed=Decimal("10"),  # Must set completed qty for next op validation
        )
        op2 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=20,
            operation_code="CLEAN",
            status="running",  # Last one, running
            actual_start=datetime.utcnow() - timedelta(minutes=30),
        )
        db.commit()

        # Execute - complete the last operation
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op2.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 10},
        )

        # Verify
        assert response.status_code == 200

        # PO should now be complete
        db.refresh(po)
        assert po.status == "complete"

    @pytest.mark.api
    def test_complete_operation_returns_next_operation(self, client, db, admin_token):
        """Completing operation returns info about next operation."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-009")
        wc_print = create_test_work_center(db, code="WC-PRINT-9", name="Print Station")
        wc_clean = create_test_work_center(db, code="WC-CLEAN-9", name="Cleaning")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op1 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc_print,
            sequence=10,
            operation_code="PRINT",
            operation_name="3D Print",
            status="running",
            actual_start=datetime.utcnow() - timedelta(hours=2),
        )
        op2 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc_clean,
            sequence=20,
            operation_code="CLEAN",
            operation_name="Post-Print Clean",
            status="pending",
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op1.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 10},
        )

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert "next_operation" in data
        assert data["next_operation"]["id"] == op2.id
        assert data["next_operation"]["operation_code"] == "CLEAN"
        assert data["next_operation"]["status"] == "pending"


class TestSkipOperation:
    """Tests for POST /api/v1/production-orders/{po_id}/operations/{op_id}/skip"""

    @pytest.mark.api
    def test_skip_operation_success(self, client, db, admin_token):
        """Skip an operation with reason."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-010")
        wc = create_test_work_center(db, code="WC-QC-10", name="QC Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op1 = create_test_po_operation(
            db, production_order=po, work_center=wc, sequence=10, operation_code="PRINT", status="complete"
        )
        op2 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=20,
            operation_code="QC",
            operation_name="QC Inspect",
            status="pending",
        )
        db.commit()

        # Execute
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op2.id}/skip",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "Customer waived QC requirement"},
        )

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "skipped"
        assert "customer waived" in data["notes"].lower()

    @pytest.mark.api
    def test_skip_operation_requires_reason(self, client, db, admin_token):
        """Skipping operation requires a reason."""
        # Setup
        product = create_test_product(db, sku="TEST-PROD-011")
        wc = create_test_work_center(db, code="WC-QC-11", name="QC Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc, sequence=10, operation_code="QC", status="pending"
        )
        db.commit()

        # Execute - no reason provided
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/skip",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={},
        )

        # Verify
        assert response.status_code == 422  # Validation error


class TestQuantityValidation:
    """Tests for quantity validation on complete."""

    @pytest.mark.api
    def test_complete_qty_exceeds_order_qty(self, client, db, admin_token):
        """Cannot complete with qty > order quantity for first op."""
        # Setup
        product = create_test_product(db, sku="TEST-QTY-001")
        wc = create_test_work_center(db, code="WC-QTY-1", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc, sequence=10, operation_code="PRINT", status="running"
        )
        db.commit()

        # Execute - try to complete with 15 (exceeds order qty of 10)
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 15, "quantity_scrapped": 0},
        )

        # Verify
        assert response.status_code == 400
        assert "exceeds maximum" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_complete_qty_with_scrap_exceeds_max(self, client, db, admin_token):
        """Cannot complete with good + bad > max quantity."""
        # Setup
        product = create_test_product(db, sku="TEST-QTY-002")
        wc = create_test_work_center(db, code="WC-QTY-2", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op = create_test_po_operation(
            db, production_order=po, work_center=wc, sequence=10, operation_code="PRINT", status="running"
        )
        db.commit()

        # Execute - 8 good + 5 bad = 13 > 10
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 8, "quantity_scrapped": 5},
        )

        # Verify
        assert response.status_code == 400
        assert "exceeds maximum" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_complete_second_op_limited_by_first_op(self, client, db, admin_token):
        """Second operation max qty = first op's qty_completed."""
        # Setup
        product = create_test_product(db, sku="TEST-QTY-003")
        wc = create_test_work_center(db, code="WC-QTY-3", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op1 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            status="complete",
            quantity_completed=Decimal("8"),
            quantity_scrapped=Decimal("2"),
        )
        op2 = create_test_po_operation(
            db, production_order=po, work_center=wc, sequence=20, operation_code="CLEAN", status="running"
        )
        db.commit()

        # Execute - try to complete with 10 (but only 8 came from op1)
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op2.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 10, "quantity_scrapped": 0},
        )

        # Verify
        assert response.status_code == 400
        assert "exceeds maximum" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_complete_second_op_with_valid_qty(self, client, db, admin_token):
        """Second operation can complete with qty <= first op's qty_completed."""
        # Setup
        product = create_test_product(db, sku="TEST-QTY-004")
        wc = create_test_work_center(db, code="WC-QTY-4", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op1 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            status="complete",
            quantity_completed=Decimal("8"),
            quantity_scrapped=Decimal("2"),
        )
        op2 = create_test_po_operation(
            db, production_order=po, work_center=wc, sequence=20, operation_code="CLEAN", status="running"
        )
        db.commit()

        # Execute - complete with 8 (matches op1's good qty)
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op2.id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantity_completed": 7, "quantity_scrapped": 1, "scrap_reason": "DEFECT"},
        )

        # Verify - 7 + 1 = 8 which equals op1's qty_completed
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"

    @pytest.mark.api
    def test_operations_list_includes_quantity_input(self, client, db, admin_token):
        """Operations list includes quantity_input field."""
        # Setup
        product = create_test_product(db, sku="TEST-QTY-005")
        wc = create_test_work_center(db, code="WC-QTY-5", name="Print Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        op1 = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            status="complete",
            quantity_completed=Decimal("8"),
        )
        op2 = create_test_po_operation(
            db, production_order=po, work_center=wc, sequence=20, operation_code="CLEAN", status="pending"
        )
        db.commit()

        # Execute
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations", headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()

        # First op should show order qty (10)
        assert Decimal(data[0]["quantity_input"]) == Decimal("10")
        # Second op should show first op's qty_completed (8)
        assert Decimal(data[1]["quantity_input"]) == Decimal("8")


class TestOperationNotFound:
    """Tests for 404 scenarios."""

    @pytest.mark.api
    def test_start_operation_not_found(self, client, db, admin_token):
        """Non-existent operation returns 404."""
        product = create_test_product(db, sku="TEST-PROD-012")
        po = create_test_production_order(db, product=product, quantity=10, status="released")
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/99999/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={},
        )
        assert response.status_code == 404

    @pytest.mark.api
    def test_operation_wrong_po(self, client, db, admin_token):
        """Operation from different PO returns 404."""
        product = create_test_product(db, sku="TEST-PROD-013")
        wc = create_test_work_center(db, code="WC-TEST-13", name="Test")

        po1 = create_test_production_order(db, product=product, quantity=10, status="released")
        po2 = create_test_production_order(db, product=product, quantity=5, status="released")

        op = create_test_po_operation(
            db, production_order=po1, work_center=wc, sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Try to start op from po1 using po2's URL
        response = client.post(
            f"/api/v1/production-orders/{po2.id}/operations/{op.id}/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={},
        )
        assert response.status_code == 404
