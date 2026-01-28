"""
Tests for GET /api/v1/items/{id}/demand-summary endpoint.

TDD: Write tests first, then implement to make them pass.
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


def parse_decimal(value) -> Decimal:
    """Parse a JSON value (string or number) as Decimal for comparison."""
    return Decimal(str(value))


class TestItemDemandSummary:
    """Tests for item demand summary endpoint."""

    def test_item_not_found(self, client, admin_headers):
        """Non-existent item returns 404."""
        response = client.get("/api/v1/items/99999/demand-summary", headers=admin_headers)
        assert response.status_code == 404

    def test_item_no_allocations(self, client, db_session, admin_headers):
        """Item with inventory but no allocations shows simple quantities."""
        reset_sequences()

        # Setup: Create material item with inventory
        material = create_test_material(db_session, sku="SIMPLE-MAT")
        create_test_inventory(db_session, product=material, quantity=Decimal("100"))
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/items/{material.id}/demand-summary", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["item_id"] == material.id
        assert data["sku"] == "SIMPLE-MAT"
        assert parse_decimal(data["quantities"]["on_hand"]) == Decimal("100")
        assert parse_decimal(data["quantities"]["allocated"]) == Decimal("0")
        assert parse_decimal(data["quantities"]["available"]) == Decimal("100")
        assert data["allocations"] == []
        assert data["shortage"]["is_short"] is False

    def test_item_with_production_order_allocation(self, client, db_session, admin_headers):
        """Item allocated to production order shows in allocations."""
        reset_sequences()

        # Setup
        # 1. Create a material (the component)
        material = create_test_material(db_session, sku="MAT-ALLOCATED", name="Allocated Material")
        create_test_inventory(db_session, product=material, quantity=Decimal("100"))

        # 2. Create a finished product that uses this material
        product = create_test_product(db_session, sku="PROD-USES-MAT", name="Product Using Material")

        # 3. Create BOM linking product to material (2 units per product)
        create_test_bom(db_session, product=product, lines=[{"component": material, "quantity": Decimal("2")}])

        # 4. Create a customer and sales order
        customer = create_test_user(db_session, email="customer@example.com", account_type="customer")
        so = create_test_sales_order(db_session, user=customer, product=product, status="confirmed", quantity=25)

        # 5. Create production order linked to sales order
        po = create_test_production_order(db_session, product=product, quantity=25, sales_order=so, status="released")
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/items/{material.id}/demand-summary", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        # 25 units * 2 per = 50 allocated
        assert parse_decimal(data["quantities"]["allocated"]) == Decimal("50")
        assert parse_decimal(data["quantities"]["available"]) == Decimal("50")  # 100 - 50

        # Check allocation details
        assert len(data["allocations"]) == 1
        alloc = data["allocations"][0]
        assert alloc["type"] == "production_order"
        assert alloc["reference_code"] == po.code
        assert parse_decimal(alloc["quantity"]) == Decimal("50")
        assert alloc["linked_sales_order"] is not None
        assert alloc["linked_sales_order"]["code"] == so.order_number

    def test_item_with_incoming_purchase(self, client, db_session, admin_headers):
        """Item with incoming purchase order."""
        reset_sequences()

        # Setup
        material = create_test_material(db_session, sku="MAT-INCOMING", name="Incoming Material")
        create_test_inventory(db_session, product=material, quantity=Decimal("20"))

        vendor = create_test_vendor(db_session, name="Test Vendor")
        purchase_order = create_test_purchase_order(
            db_session,
            vendor=vendor,
            status="ordered",
            lines=[{"product": material, "quantity": 100, "unit_cost": Decimal("10.00")}],
        )
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/items/{material.id}/demand-summary", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert parse_decimal(data["quantities"]["on_hand"]) == Decimal("20")
        assert parse_decimal(data["quantities"]["incoming"]) == Decimal("100")
        assert parse_decimal(data["quantities"]["projected"]) == Decimal("120")  # 20 + 100

        assert len(data["incoming"]) == 1
        inc = data["incoming"][0]
        assert inc["type"] == "purchase_order"
        assert inc["reference_code"] == purchase_order.po_number
        assert parse_decimal(inc["quantity"]) == Decimal("100")
        assert inc["vendor"] == "Test Vendor"

    def test_item_with_shortage(self, client, db_session, admin_headers):
        """Item with more allocated than available shows shortage."""
        reset_sequences()

        # Setup
        material = create_test_material(db_session, sku="MAT-SHORT", name="Short Material")
        create_test_inventory(db_session, product=material, quantity=Decimal("30"))

        product = create_test_product(db_session, sku="PROD-NEEDS-MAT")
        create_test_bom(db_session, product=product, lines=[{"component": material, "quantity": Decimal("1")}])

        # Two production orders consuming more than available
        create_test_production_order(db_session, product=product, quantity=25, status="released")
        create_test_production_order(db_session, product=product, quantity=20, status="released")
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/items/{material.id}/demand-summary", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        # 25 + 20 = 45 allocated, only 30 on hand
        assert parse_decimal(data["quantities"]["on_hand"]) == Decimal("30")
        assert parse_decimal(data["quantities"]["allocated"]) == Decimal("45")
        assert parse_decimal(data["quantities"]["available"]) == Decimal("-15")  # Negative = shortage

        assert data["shortage"]["is_short"] is True
        assert parse_decimal(data["shortage"]["quantity"]) == Decimal("15")
        # Both production orders are affected by shortage
        assert len(data["shortage"]["blocking_orders"]) >= 1

    def test_excludes_completed_production_orders(self, client, db_session, admin_headers):
        """Completed/closed production orders don't count as allocations."""
        reset_sequences()

        # Setup
        material = create_test_material(db_session, sku="MAT-COMPLETE-TEST")
        create_test_inventory(db_session, product=material, quantity=Decimal("100"))

        product = create_test_product(db_session, sku="PROD-COMPLETE-TEST")
        create_test_bom(db_session, product=product, lines=[{"component": material, "quantity": Decimal("5")}])

        # Create completed production order (should NOT be counted)
        create_test_production_order(db_session, product=product, quantity=10, status="closed", quantity_completed=10)

        # Create active production order (SHOULD be counted)
        create_test_production_order(db_session, product=product, quantity=5, status="released")
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/items/{material.id}/demand-summary", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        # Only the active order counts: 5 units * 5 per = 25 allocated
        # The completed order (10 units * 5 = 50) should NOT be counted
        assert parse_decimal(data["quantities"]["allocated"]) == Decimal("25")
        assert parse_decimal(data["quantities"]["available"]) == Decimal("75")  # 100 - 25
        assert len(data["allocations"]) == 1  # Only the released order

    def test_excludes_received_purchase_order_lines(self, client, db_session, admin_headers):
        """Fully received purchase order lines don't count as incoming."""
        reset_sequences()

        # Setup
        material = create_test_material(db_session, sku="MAT-RECEIVED-TEST")
        create_test_inventory(db_session, product=material, quantity=Decimal("50"))

        vendor = create_test_vendor(db_session)

        # Create received PO (should NOT be counted as incoming)
        create_test_purchase_order(
            db_session,
            vendor=vendor,
            status="received",  # Fully received
            lines=[{"product": material, "quantity": 100}],
        )

        # Create ordered PO (SHOULD be counted as incoming)
        create_test_purchase_order(
            db_session, vendor=vendor, status="ordered", lines=[{"product": material, "quantity": 75}]
        )
        db_session.commit()

        # Execute
        response = client.get(f"/api/v1/items/{material.id}/demand-summary", headers=admin_headers)

        # Verify
        assert response.status_code == 200
        data = response.json()

        # Only the ordered PO counts
        assert parse_decimal(data["quantities"]["incoming"]) == Decimal("75")
        assert parse_decimal(data["quantities"]["projected"]) == Decimal("125")  # 50 + 75
        assert len(data["incoming"]) == 1


class TestItemDemandWithScenarios:
    """Tests using seeded scenarios for integration testing."""

    def test_full_demand_chain_scenario(self, client, db_session, admin_headers):
        """Verify endpoint with full-demand-chain scenario."""
        from tests.scenarios import seed_scenario

        result = seed_scenario(db_session, "full-demand-chain")

        # Get PLA material (should have shortage)
        pla_id = result["materials"]["pla"]["id"]

        response = client.get(f"/api/v1/items/{pla_id}/demand-summary", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify quantities from scenario
        # PLA: 10000g (10kg) on hand, needs 12500g for BOM (50 units * 250g)
        assert parse_decimal(data["quantities"]["on_hand"]) == Decimal("10000")
        assert parse_decimal(data["quantities"]["allocated"]) > 0  # Some allocation from WO

        # Verify the demand chain is visible
        if data["allocations"]:
            alloc = data["allocations"][0]
            assert alloc["type"] == "production_order"
            # The WO should be linked to the sales order
            if alloc.get("linked_sales_order"):
                assert "SO-" in alloc["linked_sales_order"]["code"]
