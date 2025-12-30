"""
Tests for operation-level blocking check endpoints.

TDD: Write tests first, then implement to make them pass.
"""
import pytest
from decimal import Decimal

from tests.factories import (
    create_test_user,
    create_test_product,
    create_test_production_order,
    create_test_work_center,
    create_test_po_operation,
    create_test_bom,
    create_test_bom_line,
    create_test_inventory,
    create_test_inventory_location,
)


class TestOperationCanStart:
    """Tests for GET /api/v1/production-orders/{po_id}/operations/{op_id}/can-start"""

    @pytest.mark.api
    def test_can_start_materials_available(self, client, db, admin_token):
        """Operation can start when its materials are available."""
        # Setup: Product with BOM
        product = create_test_product(db, sku="WIDGET-001", name="Widget")
        filament = create_test_product(db, sku="PLA-BLACK", name="Black PLA", product_type="material")

        bom = create_test_bom(db, product=product)
        create_test_bom_line(
            db, bom=bom, component=filament,
            quantity=Decimal("0.5"), unit="KG",
            consume_stage="production"
        )

        # Setup: Inventory with enough filament
        location = create_test_inventory_location(db, code="WH-01", name="Warehouse")
        create_test_inventory(
            db, product=filament, location=location,
            on_hand=Decimal("10.0"), allocated=Decimal("0")
        )

        # Setup: Production order with PRINT operation
        wc = create_test_work_center(db, code="WC-PRINT-BLK1", name="Print Station")
        po = create_test_production_order(db, product=product, quantity=10, status="released")
        po.bom_id = bom.id

        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Execute
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["can_start"] is True
        assert data["blocking_issues"] == []

    @pytest.mark.api
    def test_cannot_start_materials_short(self, client, db, admin_token):
        """Operation cannot start when its materials are short."""
        # Setup: Product with BOM
        product = create_test_product(db, sku="WIDGET-002", name="Widget")
        filament = create_test_product(db, sku="PLA-WHITE", name="White PLA", product_type="material")

        bom = create_test_bom(db, product=product)
        create_test_bom_line(
            db, bom=bom, component=filament,
            quantity=Decimal("0.5"), unit="KG",
            consume_stage="production"
        )

        # Setup: Inventory with NOT ENOUGH filament (need 5kg for 10 units, only have 2kg)
        location = create_test_inventory_location(db, code="WH-02", name="Warehouse")
        create_test_inventory(
            db, product=filament, location=location,
            on_hand=Decimal("2.0"), allocated=Decimal("0")
        )

        # Setup: Production order with PRINT operation
        wc = create_test_work_center(db, code="WC-PRINT-BLK2", name="Print Station")
        po = create_test_production_order(db, product=product, quantity=10, status="released")
        po.bom_id = bom.id

        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Execute
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["can_start"] is False
        assert len(data["blocking_issues"]) == 1
        assert data["blocking_issues"][0]["product_sku"] == "PLA-WHITE"
        assert float(data["blocking_issues"][0]["quantity_short"]) == 3.0  # Need 5, have 2

    @pytest.mark.api
    def test_print_not_blocked_by_shipping_materials(self, client, db, admin_token):
        """PRINT operation not blocked by missing shipping materials."""
        # Setup: Product with BOM - both production and shipping materials
        product = create_test_product(db, sku="WIDGET-003", name="Widget")
        filament = create_test_product(db, sku="PLA-RED", name="Red PLA", product_type="material")
        boxes = create_test_product(db, sku="BOX-SMALL", name="Small Box", product_type="material")

        bom = create_test_bom(db, product=product)
        create_test_bom_line(
            db, bom=bom, component=filament,
            quantity=Decimal("0.5"), unit="KG",
            consume_stage="production"  # Consumed at PRINT
        )
        create_test_bom_line(
            db, bom=bom, component=boxes,
            quantity=Decimal("1"), unit="EA",
            consume_stage="shipping"  # Consumed at PACK
        )

        # Setup: Filament in stock, boxes OUT OF STOCK
        location = create_test_inventory_location(db, code="WH-03", name="Warehouse")
        create_test_inventory(
            db, product=filament, location=location,
            on_hand=Decimal("10.0"), allocated=Decimal("0")
        )
        # NO inventory for boxes!

        # Setup: Production order with PRINT operation
        wc = create_test_work_center(db, code="WC-PRINT-BLK3", name="Print Station")
        po = create_test_production_order(db, product=product, quantity=10, status="released")
        po.bom_id = bom.id

        op_print = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        # Execute - check PRINT operation
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op_print.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify - PRINT can start even though boxes are missing
        assert response.status_code == 200
        data = response.json()

        assert data["can_start"] is True  # KEY ASSERTION
        assert data["blocking_issues"] == []

    @pytest.mark.api
    def test_pack_blocked_by_missing_boxes(self, client, db, admin_token):
        """PACK operation IS blocked by missing shipping materials."""
        # Setup: Same as above
        product = create_test_product(db, sku="WIDGET-004", name="Widget")
        filament = create_test_product(db, sku="PLA-BLUE", name="Blue PLA", product_type="material")
        boxes = create_test_product(db, sku="BOX-MED", name="Medium Box", product_type="material")

        bom = create_test_bom(db, product=product)
        create_test_bom_line(
            db, bom=bom, component=filament,
            quantity=Decimal("0.5"), unit="KG",
            consume_stage="production"
        )
        create_test_bom_line(
            db, bom=bom, component=boxes,
            quantity=Decimal("1"), unit="EA",
            consume_stage="shipping"
        )

        # Setup: Filament in stock, boxes OUT OF STOCK
        location = create_test_inventory_location(db, code="WH-04", name="Warehouse")
        create_test_inventory(
            db, product=filament, location=location,
            on_hand=Decimal("10.0"), allocated=Decimal("0")
        )

        # Setup: Production order with PACK operation (after PRINT is done)
        wc_print = create_test_work_center(db, code="WC-PRINT-BLK4", name="Print Station")
        wc_pack = create_test_work_center(db, code="WC-PACK-BLK4", name="Pack Station")

        po = create_test_production_order(db, product=product, quantity=10, status="in_progress")
        po.bom_id = bom.id

        op_print = create_test_po_operation(
            db, production_order=po, work_center=wc_print,
            sequence=10, operation_code="PRINT", status="complete"
        )
        op_pack = create_test_po_operation(
            db, production_order=po, work_center=wc_pack,
            sequence=20, operation_code="PACK", status="pending"
        )
        db.commit()

        # Execute - check PACK operation
        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op_pack.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify - PACK is blocked by missing boxes
        assert response.status_code == 200
        data = response.json()

        assert data["can_start"] is False  # KEY ASSERTION
        assert len(data["blocking_issues"]) == 1
        assert data["blocking_issues"][0]["product_sku"] == "BOX-MED"

    @pytest.mark.api
    def test_no_bom_can_start(self, client, db, admin_token):
        """Operation with no BOM can always start (no materials to check)."""
        product = create_test_product(db, sku="SERVICE-001", name="Service Item")
        wc = create_test_work_center(db, code="WC-SVC-BLK", name="Service")

        po = create_test_production_order(db, product=product, quantity=1, status="released")
        # NO BOM assigned

        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="WORK", status="pending"
        )
        db.commit()

        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.json()["can_start"] is True


class TestOperationBlockingIssues:
    """Tests for GET /api/v1/production-orders/{po_id}/operations/{op_id}/blocking-issues"""

    @pytest.mark.api
    def test_blocking_issues_detail(self, client, db, admin_token):
        """Get detailed blocking issues for an operation."""
        # Setup
        product = create_test_product(db, sku="WIDGET-005", name="Widget")
        mat1 = create_test_product(db, sku="MAT-A", name="Material A", product_type="material")
        mat2 = create_test_product(db, sku="MAT-B", name="Material B", product_type="material")

        bom = create_test_bom(db, product=product)
        create_test_bom_line(db, bom=bom, component=mat1, quantity=Decimal("5"), consume_stage="production")
        create_test_bom_line(db, bom=bom, component=mat2, quantity=Decimal("3"), consume_stage="production")

        # Only mat1 in stock, mat2 missing
        location = create_test_inventory_location(db, code="WH-05", name="Warehouse")
        create_test_inventory(db, product=mat1, location=location, on_hand=Decimal("100"), allocated=Decimal("0"))
        # mat2 not in inventory

        wc = create_test_work_center(db, code="WC-BLK-05", name="Work Center")
        po = create_test_production_order(db, product=product, quantity=10, status="released")
        po.bom_id = bom.id

        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/blocking-issues",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["operation_id"] == op.id
        assert data["operation_code"] == "PRINT"
        assert data["can_start"] is False

        # Should only show mat2 as blocking (mat1 is fine)
        assert len(data["material_issues"]) == 2  # Both materials shown
        blocking = [m for m in data["material_issues"] if m["quantity_short"] > 0]
        assert len(blocking) == 1
        assert blocking[0]["product_sku"] == "MAT-B"
        assert float(blocking[0]["quantity_required"]) == 30.0  # 3 per unit * 10 units
        assert float(blocking[0]["quantity_available"]) == 0
        assert float(blocking[0]["quantity_short"]) == 30.0

    @pytest.mark.api
    def test_blocking_issues_considers_allocated(self, client, db, admin_token):
        """Blocking check considers allocated inventory."""
        product = create_test_product(db, sku="WIDGET-006", name="Widget")
        filament = create_test_product(db, sku="PLA-GREEN", name="Green PLA", product_type="material")

        bom = create_test_bom(db, product=product)
        create_test_bom_line(db, bom=bom, component=filament, quantity=Decimal("1"), consume_stage="production")

        # 10 on hand but 8 allocated = only 2 available
        location = create_test_inventory_location(db, code="WH-06", name="Warehouse")
        create_test_inventory(
            db, product=filament, location=location,
            on_hand=Decimal("10"), allocated=Decimal("8")
        )

        wc = create_test_work_center(db, code="WC-BLK-06", name="Work Center")
        po = create_test_production_order(db, product=product, quantity=5, status="released")  # Need 5
        po.bom_id = bom.id

        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/blocking-issues",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Need 5, only 2 available (10 - 8 allocated) = 3 short
        assert data["can_start"] is False
        assert len(data["material_issues"]) == 1
        assert float(data["material_issues"][0]["quantity_available"]) == 2.0
        assert float(data["material_issues"][0]["quantity_short"]) == 3.0

    @pytest.mark.api
    def test_cost_only_lines_ignored(self, client, db, admin_token):
        """BOM lines marked is_cost_only=True are not checked for availability."""
        product = create_test_product(db, sku="WIDGET-007", name="Widget")
        filament = create_test_product(db, sku="PLA-YELLOW", name="Yellow PLA", product_type="material")
        overhead = create_test_product(db, sku="OVERHEAD", name="Machine Overhead", product_type="service")

        bom = create_test_bom(db, product=product)
        create_test_bom_line(
            db, bom=bom, component=filament,
            quantity=Decimal("1"), consume_stage="production",
            is_cost_only=False
        )
        create_test_bom_line(
            db, bom=bom, component=overhead,
            quantity=Decimal("1"), consume_stage="production",
            is_cost_only=True  # Should be ignored
        )

        location = create_test_inventory_location(db, code="WH-07", name="Warehouse")
        create_test_inventory(db, product=filament, location=location, on_hand=Decimal("100"), allocated=Decimal("0"))
        # No inventory for overhead (and shouldn't matter)

        wc = create_test_work_center(db, code="WC-BLK-07", name="Work Center")
        po = create_test_production_order(db, product=product, quantity=10, status="released")
        po.bom_id = bom.id

        op = create_test_po_operation(
            db, production_order=po, work_center=wc,
            sequence=10, operation_code="PRINT", status="pending"
        )
        db.commit()

        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/{op.id}/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Should be able to start - overhead line is cost-only
        assert response.status_code == 200
        assert response.json()["can_start"] is True


class TestOperationNotFound:
    """Tests for 404 scenarios."""

    @pytest.mark.api
    def test_can_start_po_not_found(self, client, db, admin_token):
        response = client.get(
            "/api/v1/production-orders/99999/operations/1/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404

    @pytest.mark.api
    def test_can_start_op_not_found(self, client, db, admin_token):
        product = create_test_product(db, sku="TEST-404")
        po = create_test_production_order(db, product=product, quantity=1, status="released")
        db.commit()

        response = client.get(
            f"/api/v1/production-orders/{po.id}/operations/99999/can-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
