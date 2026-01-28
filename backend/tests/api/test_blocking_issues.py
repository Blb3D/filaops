"""
Tests for GET /api/v1/sales-orders/{id}/blocking-issues endpoint.

API-201: Sales Order Blocking Issues Endpoint
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


class TestSalesOrderBlockingIssues:
    """Tests for sales order blocking issues endpoint."""

    def test_order_not_found(self, client, admin_headers):
        """Non-existent order returns 404."""
        response = client.get("/api/v1/sales-orders/99999/blocking-issues", headers=admin_headers)
        assert response.status_code == 404

    def test_order_can_fulfill_no_issues(self, client, db_session, admin_headers):
        """Order with sufficient inventory shows can_fulfill=true."""
        reset_sequences()

        # Setup: Create product with inventory
        product = create_test_product(db_session, sku="PROD-IN-STOCK", name="In Stock Product")
        create_test_inventory(db_session, product=product, quantity=Decimal("100"))

        customer = create_test_user(db_session, email="customer@test.com", account_type="customer")
        so = create_test_sales_order(db_session, user=customer, product=product, quantity=10, status="confirmed")
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/sales-orders/{so.id}/blocking-issues", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["sales_order_id"] == so.id
        assert data["sales_order_code"] == so.order_number
        assert data["status_summary"]["can_fulfill"] is True
        assert data["status_summary"]["blocking_count"] == 0
        assert data["resolution_actions"] == []

    def test_order_production_incomplete(self, client, db_session, admin_headers):
        """Order with incomplete production shows blocking issue."""
        reset_sequences()

        # Setup: Create product that needs production
        product = create_test_product(db_session, sku="PROD-NEEDS-WO", name="Made To Order")
        product.has_bom = True
        db_session.flush()

        # Create a material component
        material = create_test_material(db_session, sku="MAT-COMPONENT")
        create_test_bom(db_session, product=product, lines=[{"component": material, "quantity": Decimal("1")}])
        create_test_inventory(db_session, product=material, quantity=Decimal("100"))

        customer = create_test_user(db_session, email="customer@test.com", account_type="customer")
        so = create_test_sales_order(db_session, user=customer, product=product, quantity=10, status="confirmed")

        # Create incomplete production order
        wo = create_test_production_order(
            db_session, product=product, quantity=10, sales_order=so, status="released", quantity_completed=0
        )
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/sales-orders/{so.id}/blocking-issues", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["status_summary"]["can_fulfill"] is False
        assert data["status_summary"]["blocking_count"] >= 1

        # Check for production_incomplete issue
        line_issues = data["line_issues"]
        assert len(line_issues) == 1
        blocking = line_issues[0]["blocking_issues"]
        issue_types = [i["type"] for i in blocking]
        assert "production_incomplete" in issue_types

        # Check resolution actions
        actions = data["resolution_actions"]
        assert len(actions) >= 1
        action_texts = [a["action"] for a in actions]
        assert any("WO-" in a for a in action_texts)

    def test_order_material_shortage(self, client, db_session, admin_headers):
        """Order with material shortage shows blocking issue."""
        reset_sequences()

        # Setup: Product with BOM
        product = create_test_product(db_session, sku="PROD-MAT-SHORT")
        product.has_bom = True
        db_session.flush()

        material = create_test_material(db_session, sku="MAT-SHORT")
        create_test_bom(
            db_session,
            product=product,
            lines=[
                {"component": material, "quantity": Decimal("5")}  # 5 units per product
            ],
        )
        # Only 20 material available, need 50 (10 * 5)
        create_test_inventory(db_session, product=material, quantity=Decimal("20"))

        customer = create_test_user(db_session, email="customer@test.com", account_type="customer")
        so = create_test_sales_order(db_session, user=customer, product=product, quantity=10, status="confirmed")

        # Create production order that will expose the shortage
        wo = create_test_production_order(db_session, product=product, quantity=10, sales_order=so, status="released")
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/sales-orders/{so.id}/blocking-issues", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["status_summary"]["can_fulfill"] is False

        # Check for material_shortage issue
        line_issues = data["line_issues"]
        assert len(line_issues) == 1
        blocking = line_issues[0]["blocking_issues"]
        issue_types = [i["type"] for i in blocking]
        assert "material_shortage" in issue_types

        # Find the shortage issue and verify details
        shortage_issue = next(i for i in blocking if i["type"] == "material_shortage")
        assert shortage_issue["reference_code"] == "MAT-SHORT"
        assert shortage_issue["details"]["shortage"] == 30.0  # 50 needed - 20 available

    def test_order_purchase_pending(self, client, db_session, admin_headers):
        """Order with pending purchase shows warning and resolution action."""
        reset_sequences()

        # Setup
        product = create_test_product(db_session, sku="PROD-PO-PENDING")
        product.has_bom = True
        db_session.flush()

        material = create_test_material(db_session, sku="MAT-PO-PENDING")
        create_test_bom(db_session, product=product, lines=[{"component": material, "quantity": Decimal("1")}])
        create_test_inventory(db_session, product=material, quantity=Decimal("5"))  # Short

        vendor = create_test_vendor(db_session, name="Test Vendor")
        po = create_test_purchase_order(
            db_session, vendor=vendor, status="ordered", lines=[{"product": material, "quantity": 50}]
        )

        customer = create_test_user(db_session, email="customer@test.com", account_type="customer")
        so = create_test_sales_order(db_session, user=customer, product=product, quantity=10, status="confirmed")

        wo = create_test_production_order(db_session, product=product, quantity=10, sales_order=so, status="released")
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/sales-orders/{so.id}/blocking-issues", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        # Check for purchase_pending warning
        line_issues = data["line_issues"]
        blocking = line_issues[0]["blocking_issues"]
        issue_types = [i["type"] for i in blocking]
        assert "purchase_pending" in issue_types

        # Expedite PO should be first resolution action
        actions = data["resolution_actions"]
        assert len(actions) >= 1
        assert "Expedite" in actions[0]["action"]
        assert po.po_number in actions[0]["action"]


class TestBlockingIssuesWithScenarios:
    """Tests using seeded scenarios for integration testing."""

    def test_full_demand_chain_scenario(self, client, db_session, admin_headers):
        """Verify endpoint with full-demand-chain scenario."""
        from tests.scenarios import seed_scenario

        result = seed_scenario(db_session, "full-demand-chain")

        so_id = result["sales_order"]["id"]

        response = client.get(f"/api/v1/sales-orders/{so_id}/blocking-issues", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # Should have blocking issues (scenario designed to have shortages)
        assert data["status_summary"]["can_fulfill"] is False
        assert data["status_summary"]["blocking_count"] >= 1

        # Should show production and material issues
        line_issues = data["line_issues"]
        assert len(line_issues) >= 1

        # Should have resolution actions
        assert len(data["resolution_actions"]) >= 1

    def test_so_with_blocking_issues_scenario(self, client, db_session, admin_headers):
        """Verify endpoint with so-with-blocking-issues scenario."""
        from tests.scenarios import seed_scenario, SCENARIOS

        # Only run if scenario exists
        if "so-with-blocking-issues" not in SCENARIOS:
            return  # Skip if scenario not implemented

        result = seed_scenario(db_session, "so-with-blocking-issues")

        so_id = result["sales_order"]["id"]

        response = client.get(f"/api/v1/sales-orders/{so_id}/blocking-issues", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # This scenario is designed to have blocking issues
        assert data["status_summary"]["can_fulfill"] is False
