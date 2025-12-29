"""
Tests for GET /sales-orders/{id}/fulfillment-status (API-301)

Tests the fulfillment status endpoint for sales orders.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from tests.factories import (
    create_test_user, create_test_product, create_test_sales_order,
    create_test_inventory, create_test_vendor, create_test_purchase_order,
    get_or_create_default_location, reset_sequences
)


class TestFulfillmentStatusEndpoint:
    """Tests for GET /sales-orders/{id}/fulfillment-status"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        """Reset sequences before each test."""
        reset_sequences()

    def test_ready_to_ship_all_lines_allocated(self, client, db_session, admin_headers):
        """Order with all lines fully allocated should be ready_to_ship."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")
        order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        # Get the order line and set allocated quantity
        order_line = order.lines[0]
        order_line.allocated_quantity = Decimal("10")
        db_session.commit()

        # Act
        response = client.get(
            f"/api/v1/sales-orders/{order.id}/fulfillment-status",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["state"] == "ready_to_ship"
        assert data["summary"]["lines_total"] == 1
        assert data["summary"]["lines_ready"] == 1
        assert data["summary"]["fulfillment_percent"] == 100.0
        assert data["summary"]["can_ship_complete"] is True

    def test_partially_ready_some_lines_allocated(self, client, db_session, admin_headers):
        """Order with some lines allocated should be partially_ready."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product1 = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament 1")
        product2 = create_test_product(db_session, sku="FIL-TEST-002", name="Test Filament 2")
        order = create_test_sales_order(
            db_session,
            user=user,
            lines=[
                {"product": product1, "quantity": 10, "unit_price": Decimal("25.00")},
                {"product": product2, "quantity": 10, "unit_price": Decimal("25.00")},
            ]
        )
        # Fully allocate line1, no allocation for line2
        order.lines[0].allocated_quantity = Decimal("10")
        order.lines[1].allocated_quantity = Decimal("0")
        db_session.commit()

        # Act
        response = client.get(
            f"/api/v1/sales-orders/{order.id}/fulfillment-status",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["state"] == "partially_ready"
        assert data["summary"]["lines_ready"] == 1
        assert data["summary"]["lines_blocked"] == 1
        assert data["summary"]["fulfillment_percent"] == 50.0
        assert data["summary"]["can_ship_partial"] is True
        assert data["summary"]["can_ship_complete"] is False

    def test_blocked_no_lines_allocated(self, client, db_session, admin_headers):
        """Order with no allocations should be blocked."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")
        order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        # No allocation - leave allocated_quantity as default (0)
        db_session.commit()

        # Act
        response = client.get(
            f"/api/v1/sales-orders/{order.id}/fulfillment-status",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["state"] == "blocked"
        assert data["summary"]["lines_ready"] == 0
        assert data["summary"]["can_ship_partial"] is False

    def test_line_details_include_shortage(self, client, db_session, admin_headers):
        """Line status should include shortage amount."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")
        order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        # Partial allocation
        order.lines[0].allocated_quantity = Decimal("7")
        db_session.commit()

        # Act
        response = client.get(
            f"/api/v1/sales-orders/{order.id}/fulfillment-status",
            headers=admin_headers
        )

        # Assert
        data = response.json()
        line_status = data["lines"][0]
        assert line_status["quantity_ordered"] == 10.0
        assert line_status["quantity_allocated"] == 7.0
        assert line_status["shortage"] == 3.0
        assert line_status["is_ready"] is False
        assert "need 3" in line_status["blocking_reason"].lower()

    def test_404_for_nonexistent_order(self, client, admin_headers):
        """Should return 404 for nonexistent order."""
        # Act
        response = client.get(
            "/api/v1/sales-orders/99999/fulfillment-status",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 404

    def test_requires_authentication(self, client):
        """Should require auth token."""
        # Act
        response = client.get("/api/v1/sales-orders/1/fulfillment-status")

        # Assert
        assert response.status_code == 401

    def test_shipped_order_shows_shipped_state(self, client, db_session, admin_headers):
        """Shipped orders should show shipped state."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")
        order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}],
            status="shipped"
        )
        order.lines[0].shipped_quantity = Decimal("10")
        db_session.commit()

        # Act
        response = client.get(
            f"/api/v1/sales-orders/{order.id}/fulfillment-status",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["state"] == "shipped"

    def test_cancelled_order_shows_cancelled_state(self, client, db_session, admin_headers):
        """Cancelled orders should show cancelled state."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")
        order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}],
            status="cancelled"
        )
        db_session.commit()

        # Act
        response = client.get(
            f"/api/v1/sales-orders/{order.id}/fulfillment-status",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["state"] == "cancelled"


class TestBulkFulfillmentStatus:
    """Tests for ?include_fulfillment=true (API-302)"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        """Reset sequences before each test."""
        reset_sequences()

    def test_list_without_flag_no_fulfillment(self, client, db_session, admin_headers):
        """Default list should NOT include fulfillment field."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")
        order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        db_session.commit()

        # Act
        response = client.get("/api/v1/sales-orders/", headers=admin_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        # Find our order in the list
        order_item = next((o for o in data if o["id"] == order.id), None)
        assert order_item is not None
        # Fulfillment should be None or not present
        assert order_item.get("fulfillment") is None

    def test_list_with_flag_includes_fulfillment(self, client, db_session, admin_headers):
        """With flag, response includes fulfillment summary."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")
        order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        # Fully allocate the line
        order.lines[0].allocated_quantity = Decimal("10")
        db_session.commit()

        # Act
        response = client.get(
            "/api/v1/sales-orders/?include_fulfillment=true",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        # Find our order in the list
        order_item = next((o for o in data if o["id"] == order.id), None)
        assert order_item is not None
        # Fulfillment should be present with summary fields
        assert order_item["fulfillment"] is not None
        assert order_item["fulfillment"]["state"] == "ready_to_ship"
        assert order_item["fulfillment"]["lines_total"] == 1
        assert order_item["fulfillment"]["lines_ready"] == 1
        assert order_item["fulfillment"]["fulfillment_percent"] == 100.0
        assert order_item["fulfillment"]["can_ship_complete"] is True

    def test_list_fulfillment_matches_detail(self, client, db_session, admin_headers):
        """Bulk fulfillment summary matches single-order endpoint."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")
        order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        # Partial allocation
        order.lines[0].allocated_quantity = Decimal("7")
        db_session.commit()

        # Act - get bulk list
        list_response = client.get(
            "/api/v1/sales-orders/?include_fulfillment=true",
            headers=admin_headers
        )
        # Act - get single order detail
        detail_response = client.get(
            f"/api/v1/sales-orders/{order.id}/fulfillment-status",
            headers=admin_headers
        )

        # Assert
        assert list_response.status_code == 200
        assert detail_response.status_code == 200

        list_data = list_response.json()
        detail_data = detail_response.json()

        # Find order in list
        order_item = next((o for o in list_data if o["id"] == order.id), None)
        assert order_item is not None

        # Compare summary fields
        list_summary = order_item["fulfillment"]
        detail_summary = detail_data["summary"]

        assert list_summary["state"] == detail_summary["state"]
        assert list_summary["lines_total"] == detail_summary["lines_total"]
        assert list_summary["lines_ready"] == detail_summary["lines_ready"]
        assert list_summary["lines_blocked"] == detail_summary["lines_blocked"]
        assert list_summary["fulfillment_percent"] == detail_summary["fulfillment_percent"]
        assert list_summary["can_ship_partial"] == detail_summary["can_ship_partial"]
        assert list_summary["can_ship_complete"] == detail_summary["can_ship_complete"]


class TestEnhancedSOListFiltering:
    """Tests for fulfillment state filtering and sorting (API-303)"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        """Reset sequences before each test."""
        reset_sequences()

    def test_filter_by_ready_to_ship(self, client, db_session, admin_headers):
        """Filter should return only ready_to_ship orders."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")

        # Create ready_to_ship order (fully allocated)
        ready_order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        ready_order.lines[0].allocated_quantity = Decimal("10")

        # Create blocked order (no allocation)
        product2 = create_test_product(db_session, sku="FIL-TEST-002", name="Test Filament 2")
        blocked_order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product2, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        # No allocation - stays blocked

        db_session.commit()

        # Act
        response = client.get(
            "/api/v1/sales-orders/?include_fulfillment=true&fulfillment_state=ready_to_ship",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Should only contain ready_to_ship orders
        for order in data:
            assert order["fulfillment"]["state"] == "ready_to_ship"
        # Our ready order should be in results
        order_ids = [o["id"] for o in data]
        assert ready_order.id in order_ids
        assert blocked_order.id not in order_ids

    def test_filter_by_multiple_states(self, client, db_session, admin_headers):
        """Filter by comma-separated states should return matching orders."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")

        # Create ready_to_ship order
        ready_order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        ready_order.lines[0].allocated_quantity = Decimal("10")

        # Create blocked order
        product2 = create_test_product(db_session, sku="FIL-TEST-002", name="Test Filament 2")
        blocked_order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product2, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        # No allocation - stays blocked

        # Create shipped order
        product3 = create_test_product(db_session, sku="FIL-TEST-003", name="Test Filament 3")
        shipped_order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product3, "quantity": 10, "unit_price": Decimal("25.00")}],
            status="shipped"
        )
        shipped_order.lines[0].shipped_quantity = Decimal("10")

        db_session.commit()

        # Act - filter by ready_to_ship and blocked
        response = client.get(
            "/api/v1/sales-orders/?include_fulfillment=true&fulfillment_state=ready_to_ship,blocked",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        order_ids = [o["id"] for o in data]
        # Ready and blocked should be in results
        assert ready_order.id in order_ids
        assert blocked_order.id in order_ids
        # Shipped should NOT be in results
        assert shipped_order.id not in order_ids

    def test_sort_by_fulfillment_priority_asc(self, client, db_session, admin_headers):
        """Sort by fulfillment_priority should order by actionability."""
        # Arrange
        user = create_test_user(db_session, account_type="admin")

        # Create blocked order first
        product1 = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament 1")
        blocked_order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product1, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        # No allocation - blocked

        # Create ready_to_ship order second
        product2 = create_test_product(db_session, sku="FIL-TEST-002", name="Test Filament 2")
        ready_order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product2, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        ready_order.lines[0].allocated_quantity = Decimal("10")

        # Create shipped order last
        product3 = create_test_product(db_session, sku="FIL-TEST-003", name="Test Filament 3")
        shipped_order = create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product3, "quantity": 10, "unit_price": Decimal("25.00")}],
            status="shipped"
        )
        shipped_order.lines[0].shipped_quantity = Decimal("10")

        db_session.commit()

        # Act - sort by fulfillment_priority ascending (most actionable first)
        response = client.get(
            "/api/v1/sales-orders/?include_fulfillment=true&sort_by=fulfillment_priority&sort_order=asc",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

        # Find our orders in results
        order_positions = {}
        for idx, order in enumerate(data):
            if order["id"] == ready_order.id:
                order_positions["ready"] = idx
            elif order["id"] == blocked_order.id:
                order_positions["blocked"] = idx
            elif order["id"] == shipped_order.id:
                order_positions["shipped"] = idx

        # Priority order: ready_to_ship(1) < blocked(3) < shipped(4)
        assert order_positions["ready"] < order_positions["blocked"]
        assert order_positions["blocked"] < order_positions["shipped"]

    def test_invalid_state_returns_400(self, client, db_session, admin_headers):
        """Invalid fulfillment state should return 400 error."""
        # Arrange - create at least one order so the endpoint doesn't fail for other reasons
        user = create_test_user(db_session, account_type="admin")
        product = create_test_product(db_session, sku="FIL-TEST-001", name="Test Filament")
        create_test_sales_order(
            db_session,
            user=user,
            lines=[{"product": product, "quantity": 10, "unit_price": Decimal("25.00")}]
        )
        db_session.commit()

        # Act
        response = client.get(
            "/api/v1/sales-orders/?fulfillment_state=invalid_state",
            headers=admin_headers
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "invalid_state" in data["detail"].lower()
