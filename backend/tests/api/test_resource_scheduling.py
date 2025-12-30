"""
Tests for resource scheduling and conflict detection (API-403).

Tests cover:
1. Get resource schedule with date filters
2. Schedule operation - success when no conflicts
3. Schedule operation - fails with 409 when conflict exists
4. Adjacent time slots don't conflict
5. Completed operations don't block scheduling
6. Check conflicts endpoint
7. Start operation blocked if resource busy
"""
import pytest
from datetime import datetime, timedelta
from tests.factories import (
    create_test_product,
    create_test_production_order,
    create_test_po_operation,
    create_test_resource,
    create_test_work_center,
)


class TestResourceSchedule:
    """Tests for GET /api/v1/resources/{id}/schedule endpoint."""

    @pytest.mark.api
    def test_get_resource_schedule_empty(self, client, db, admin_token):
        """Resource with no scheduled operations returns empty list."""
        wc = create_test_work_center(db, code="WC-SCHED-01", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-SCH-01", name="Printer 1")
        db.commit()

        response = client.get(
            f"/api/v1/resources/{resource.id}/schedule",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["operations"] == []

    @pytest.mark.api
    def test_get_resource_schedule_with_operations(self, client, db, admin_token):
        """Returns scheduled operations for resource."""
        wc = create_test_work_center(db, code="WC-SCHED-02", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-SCH-02", name="Printer 2")
        product = create_test_product(db, sku="PROD-SCHED-02")
        po = create_test_production_order(db, product=product, quantity=10, status="released")

        now = datetime.utcnow()
        op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            resource=resource,
            sequence=10,
            operation_code="PRINT",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
            status="queued"
        )
        db.commit()

        response = client.get(
            f"/api/v1/resources/{resource.id}/schedule",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["operations"]) == 1
        assert data["operations"][0]["operation_id"] == op.id

    @pytest.mark.api
    def test_get_resource_schedule_date_filter(self, client, db, admin_token):
        """Date filters exclude operations outside range."""
        wc = create_test_work_center(db, code="WC-SCHED-03", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-SCH-03", name="Printer 3")
        product = create_test_product(db, sku="PROD-SCHED-03")
        po = create_test_production_order(db, product=product, quantity=10, status="released")

        now = datetime.utcnow()
        # Op in the past
        past_op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            resource=resource,
            sequence=10,
            operation_code="PRINT",
            scheduled_start=now - timedelta(days=2),
            scheduled_end=now - timedelta(days=1),
            status="queued"
        )
        # Op in the future
        future_op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            resource=resource,
            sequence=20,
            operation_code="CLEAN",
            scheduled_start=now + timedelta(days=1),
            scheduled_end=now + timedelta(days=2),
            status="queued"
        )
        db.commit()

        # Filter to only future
        response = client.get(
            f"/api/v1/resources/{resource.id}/schedule",
            params={"start_date": now.isoformat()},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["operations"]) == 1
        assert data["operations"][0]["operation_id"] == future_op.id


class TestConflictCheck:
    """Tests for GET /api/v1/resources/{id}/conflicts endpoint."""

    @pytest.mark.api
    def test_no_conflicts_when_empty(self, client, db, admin_token):
        """No conflicts on empty resource."""
        wc = create_test_work_center(db, code="WC-CONF-01", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-CONF-01", name="Printer 1")
        db.commit()

        now = datetime.utcnow()
        response = client.get(
            f"/api/v1/resources/{resource.id}/conflicts",
            params={
                "start": now.isoformat(),
                "end": (now + timedelta(hours=2)).isoformat()
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False
        assert data["conflicts"] == []

    @pytest.mark.api
    def test_detects_overlapping_conflict(self, client, db, admin_token):
        """Detects conflict when time ranges overlap."""
        wc = create_test_work_center(db, code="WC-CONF-02", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-CONF-02", name="Printer 2")
        product = create_test_product(db, sku="PROD-CONF-02")
        po = create_test_production_order(db, product=product, quantity=10, status="released")

        now = datetime.utcnow()
        # Existing operation: 10:00 - 12:00
        existing_op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            resource=resource,
            sequence=10,
            operation_code="PRINT",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
            status="queued"
        )
        db.commit()

        # Check 11:00 - 13:00 (overlaps)
        response = client.get(
            f"/api/v1/resources/{resource.id}/conflicts",
            params={
                "start": (now + timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=3)).isoformat()
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is True
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["operation_id"] == existing_op.id

    @pytest.mark.api
    def test_adjacent_slots_no_conflict(self, client, db, admin_token):
        """Adjacent time slots (end = start) don't conflict."""
        wc = create_test_work_center(db, code="WC-CONF-03", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-CONF-03", name="Printer 3")
        product = create_test_product(db, sku="PROD-CONF-03")
        po = create_test_production_order(db, product=product, quantity=10, status="released")

        now = datetime.utcnow()
        # Existing: 10:00 - 12:00
        create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            resource=resource,
            sequence=10,
            operation_code="PRINT",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
            status="queued"
        )
        db.commit()

        # Check 12:00 - 14:00 (adjacent, should not conflict)
        response = client.get(
            f"/api/v1/resources/{resource.id}/conflicts",
            params={
                "start": (now + timedelta(hours=2)).isoformat(),
                "end": (now + timedelta(hours=4)).isoformat()
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False

    @pytest.mark.api
    def test_completed_ops_dont_conflict(self, client, db, admin_token):
        """Completed operations don't block scheduling."""
        wc = create_test_work_center(db, code="WC-CONF-04", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-CONF-04", name="Printer 4")
        product = create_test_product(db, sku="PROD-CONF-04")
        po = create_test_production_order(db, product=product, quantity=10, status="released")

        now = datetime.utcnow()
        # Completed operation in same time slot
        create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            resource=resource,
            sequence=10,
            operation_code="PRINT",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
            status="complete"  # Already done
        )
        db.commit()

        # Same time slot should be available
        response = client.get(
            f"/api/v1/resources/{resource.id}/conflicts",
            params={
                "start": now.isoformat(),
                "end": (now + timedelta(hours=2)).isoformat()
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False


class TestScheduleOperation:
    """Tests for POST /api/v1/production-orders/{po_id}/operations/{op_id}/schedule."""

    @pytest.mark.api
    def test_schedule_success(self, client, db, admin_token):
        """Successfully schedule operation when no conflicts."""
        wc = create_test_work_center(db, code="WC-SCH-OP-01", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-SCH-OP-01", name="Printer 1")
        product = create_test_product(db, sku="PROD-SCH-OP-01")
        po = create_test_production_order(db, product=product, quantity=10, status="released")
        op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            status="pending"
        )
        db.commit()

        now = datetime.utcnow()
        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/schedule",
            json={
                "resource_id": resource.id,
                "scheduled_start": now.isoformat(),
                "scheduled_end": (now + timedelta(hours=2)).isoformat()
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify operation updated
        db.refresh(op)
        assert op.resource_id == resource.id
        assert op.status == "queued"

    @pytest.mark.api
    def test_schedule_conflict_returns_409(self, client, db, admin_token):
        """Returns 409 when scheduling would create conflict."""
        wc = create_test_work_center(db, code="WC-SCH-OP-02", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-SCH-OP-02", name="Printer 2")
        product = create_test_product(db, sku="PROD-SCH-OP-02")
        po = create_test_production_order(db, product=product, quantity=10, status="released")

        now = datetime.utcnow()
        # Existing scheduled operation
        create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            resource=resource,
            sequence=10,
            operation_code="PRINT",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
            status="queued"
        )

        # Try to schedule another in same slot
        new_op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            sequence=20,
            operation_code="CLEAN",
            status="pending"
        )
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{new_op.id}/schedule",
            json={
                "resource_id": resource.id,
                "scheduled_start": (now + timedelta(hours=1)).isoformat(),
                "scheduled_end": (now + timedelta(hours=3)).isoformat()
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 409


class TestStartOperationResourceCheck:
    """Tests for resource availability check when starting operation."""

    @pytest.mark.api
    def test_start_blocked_if_resource_busy(self, client, db, admin_token):
        """Cannot start operation if assigned resource has running operation."""
        wc = create_test_work_center(db, code="WC-START-01", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-START-01", name="Printer 1")
        product = create_test_product(db, sku="PROD-START-01")

        # First PO with running operation on resource
        po1 = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        running_op = create_test_po_operation(
            db,
            production_order=po1,
            work_center=wc,
            resource=resource,
            sequence=10,
            operation_code="PRINT",
            status="running"
        )

        # Second PO with pending operation we want to start
        po2 = create_test_production_order(db, product=product, quantity=5, status="released")
        new_op = create_test_po_operation(
            db,
            production_order=po2,
            work_center=wc,
            sequence=10,
            operation_code="PRINT",
            status="pending"
        )
        db.commit()

        # Try to start operation on po2 using the same resource that's busy on po1
        response = client.post(
            f"/api/v1/production-orders/{po2.id}/operations/{new_op.id}/start",
            json={"resource_id": resource.id},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 409
        detail = response.json()["detail"].lower()
        assert "resource" in detail or "busy" in detail

    @pytest.mark.api
    def test_start_allowed_if_resource_free(self, client, db, admin_token):
        """Can start operation if resource has no running operations."""
        wc = create_test_work_center(db, code="WC-START-02", name="Test WC")
        resource = create_test_resource(db, work_center=wc, code="PRINTER-START-02", name="Printer 2")
        product = create_test_product(db, sku="PROD-START-02")
        po = create_test_production_order(db, product=product, quantity=10, status="released")

        op = create_test_po_operation(
            db,
            production_order=po,
            work_center=wc,
            resource=resource,
            sequence=10,
            operation_code="PRINT",
            status="pending"
        )
        db.commit()

        response = client.post(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/start",
            json={"resource_id": resource.id},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        db.refresh(op)
        assert op.status == "running"
