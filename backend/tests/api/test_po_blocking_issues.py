"""
Tests for GET /api/v1/production-orders/{id}/blocking-issues endpoint.

API-202: Production Order Blocking Issues Endpoint
"""

from decimal import Decimal

from tests.factories import (
    create_test_product,
    create_test_material,
    create_test_bom,
    create_test_user,
    create_test_vendor,
    create_test_sales_order,
    create_test_production_order,
    create_test_purchase_order,
    create_test_inventory,
    reset_sequences,
)


class TestProductionOrderBlockingIssues:
    """Tests for production order blocking issues endpoint."""

    def test_production_order_not_found(self, client, admin_headers):
        """Non-existent production order returns 404."""
        response = client.get("/api/v1/production-orders/99999/blocking-issues", headers=admin_headers)
        assert response.status_code == 404

    def test_production_order_no_issues(self, client, db_session, admin_headers):
        """Production order with sufficient materials shows can_produce=true."""
        reset_sequences()

        # Setup: Product with enough material
        material = create_test_material(db_session, sku="AVAIL-MAT", name="Available Material")
        create_test_inventory(db_session, product=material, quantity=Decimal("1000"))

        product = create_test_product(db_session, sku="PROD-AVAIL", name="Available Product")
        create_test_bom(db_session, product=product, lines=[{"component": material, "quantity": Decimal("1")}])

        wo = create_test_production_order(db_session, product=product, quantity=50, status="released")
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/production-orders/{wo.id}/blocking-issues", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["production_order_id"] == wo.id
        assert data["production_order_code"] == wo.code
        assert data["status_summary"]["can_produce"] is True
        assert data["status_summary"]["blocking_count"] == 0
        assert all(m["status"] == "ok" for m in data["material_issues"])

    def test_material_shortage_blocking(self, client, db_session, admin_headers):
        """Material shortage blocks production."""
        reset_sequences()

        # Setup: Need 100 (50 * 2), only have 30
        material = create_test_material(db_session, sku="SHORT-MAT", name="Short Material")
        create_test_inventory(db_session, product=material, quantity=Decimal("30"))

        product = create_test_product(db_session, sku="PROD-SHORT", name="Short Product")
        create_test_bom(
            db_session,
            product=product,
            lines=[
                {"component": material, "quantity": Decimal("2")}  # 2 units per product
            ],
        )

        wo = create_test_production_order(db_session, product=product, quantity=50, status="released")
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/production-orders/{wo.id}/blocking-issues", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["status_summary"]["can_produce"] is False
        assert data["status_summary"]["blocking_count"] >= 1

        # Find the material issue
        mat_issue = next(m for m in data["material_issues"] if m["product_sku"] == "SHORT-MAT")
        assert float(mat_issue["quantity_required"]) == 100.0
        assert float(mat_issue["quantity_available"]) == 30.0
        assert float(mat_issue["quantity_short"]) == 70.0
        assert mat_issue["status"] == "shortage"

    def test_material_shortage_with_incoming_po(self, client, db_session, admin_headers):
        """Shows incoming PO that will resolve shortage."""
        reset_sequences()

        material = create_test_material(db_session, sku="PEND-MAT", name="Pending Material")
        create_test_inventory(db_session, product=material, quantity=Decimal("20"))

        product = create_test_product(db_session, sku="PROD-PEND", name="Pending Product")
        create_test_bom(db_session, product=product, lines=[{"component": material, "quantity": Decimal("1")}])

        wo = create_test_production_order(db_session, product=product, quantity=50, status="released")

        # Incoming PO
        vendor = create_test_vendor(db_session, name="Test Vendor")
        po = create_test_purchase_order(
            db_session, vendor=vendor, status="ordered", lines=[{"product": material, "quantity": 100}]
        )
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/production-orders/{wo.id}/blocking-issues", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        mat_issue = next(m for m in data["material_issues"] if m["product_sku"] == "PEND-MAT")
        assert mat_issue["incoming_supply"] is not None
        assert mat_issue["incoming_supply"]["purchase_order_code"] == po.po_number
        assert float(mat_issue["incoming_supply"]["quantity"]) == 100.0

    def test_linked_sales_order_shown(self, client, db_session, admin_headers):
        """Shows linked sales order for MTO production."""
        reset_sequences()

        material = create_test_material(db_session, sku="MTO-MAT")
        create_test_inventory(db_session, product=material, quantity=Decimal("1000"))

        product = create_test_product(db_session, sku="MTO-PROD", name="MTO Product")
        create_test_bom(db_session, product=product, lines=[{"component": material, "quantity": Decimal("1")}])

        customer = create_test_user(
            db_session, email="customer@test.com", account_type="customer", company_name="Test Customer Inc"
        )

        so = create_test_sales_order(db_session, user=customer, product=product, quantity=25, status="confirmed")

        wo = create_test_production_order(db_session, product=product, quantity=25, sales_order=so, status="released")
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/production-orders/{wo.id}/blocking-issues", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["linked_sales_order"] is not None
        assert data["linked_sales_order"]["code"] == so.order_number
        assert "Test Customer" in data["linked_sales_order"]["customer"]

    def test_resolution_actions_generated(self, client, db_session, admin_headers):
        """Resolution actions are generated for blocking issues."""
        reset_sequences()

        material = create_test_material(db_session, sku="ACTION-MAT", name="Action Material")
        create_test_inventory(db_session, product=material, quantity=Decimal("10"))

        product = create_test_product(db_session, sku="ACTION-PROD", name="Action Product")
        create_test_bom(db_session, product=product, lines=[{"component": material, "quantity": Decimal("1")}])

        wo = create_test_production_order(db_session, product=product, quantity=50, status="released")

        vendor = create_test_vendor(db_session)
        po = create_test_purchase_order(
            db_session, vendor=vendor, status="ordered", lines=[{"product": material, "quantity": 100}]
        )
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/production-orders/{wo.id}/blocking-issues", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert len(data["resolution_actions"]) > 0
        # First action should be to expedite the PO
        first_action = data["resolution_actions"][0]
        assert "Expedite" in first_action["action"] or "PO" in first_action["action"]

    def test_multiple_material_shortages(self, client, db_session, admin_headers):
        """Multiple materials with different availability states."""
        reset_sequences()

        mat_ok = create_test_material(db_session, sku="MAT-OK", name="OK Material")
        mat_short = create_test_material(db_session, sku="MAT-SHORT", name="Short Material")
        mat_zero = create_test_material(db_session, sku="MAT-ZERO", name="Zero Material")

        create_test_inventory(db_session, product=mat_ok, quantity=Decimal("200"))
        create_test_inventory(db_session, product=mat_short, quantity=Decimal("30"))
        # mat_zero has no inventory

        product = create_test_product(db_session, sku="MULTI-PROD", name="Multi Material Product")
        create_test_bom(
            db_session,
            product=product,
            lines=[
                {"component": mat_ok, "quantity": Decimal("1")},
                {"component": mat_short, "quantity": Decimal("1")},
                {"component": mat_zero, "quantity": Decimal("1")},
            ],
        )

        wo = create_test_production_order(db_session, product=product, quantity=50, status="released")
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/production-orders/{wo.id}/blocking-issues", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert len(data["material_issues"]) == 3

        issue_ok = next(m for m in data["material_issues"] if m["product_sku"] == "MAT-OK")
        issue_short = next(m for m in data["material_issues"] if m["product_sku"] == "MAT-SHORT")
        issue_zero = next(m for m in data["material_issues"] if m["product_sku"] == "MAT-ZERO")

        assert issue_ok["status"] == "ok"
        assert issue_short["status"] == "shortage"
        assert issue_zero["status"] == "shortage"
        assert float(issue_zero["quantity_available"]) == 0.0


class TestPOBlockingIssuesWithScenarios:
    """Tests using seeded scenarios."""

    def test_full_demand_chain_scenario(self, client, db_session, admin_headers):
        """Verify with full-demand-chain scenario."""
        from tests.scenarios import seed_scenario

        result = seed_scenario(db_session, "full-demand-chain")
        wo_id = result["production_order"]["id"]

        response = client.get(f"/api/v1/production-orders/{wo_id}/blocking-issues", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # This scenario has material shortages
        assert data["status_summary"]["can_produce"] is False
        assert data["status_summary"]["blocking_count"] >= 1

        # Should show linked SO
        assert data["linked_sales_order"] is not None
        assert "Acme" in data["linked_sales_order"]["customer"]

        # Should have resolution actions
        assert len(data["resolution_actions"]) >= 1
