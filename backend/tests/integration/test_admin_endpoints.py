"""
Integration tests for Admin endpoints

Tests BOM management, dashboard, and admin-only access control
"""

from decimal import Decimal


class TestAdminAccessControl:
    """Test admin-only access restrictions"""

    def test_dashboard_requires_authentication(self, client):
        """Test that dashboard returns 401 without auth"""
        response = client.get("/api/v1/admin/dashboard/")
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_dashboard_requires_admin_role(self, client, customer_headers):
        """Test that dashboard returns 403 for non-staff users (customers)"""
        response = client.get("/api/v1/admin/dashboard/", headers=customer_headers)
        assert response.status_code == 403
        assert "staff access required" in response.json()["detail"].lower()

    def test_dashboard_allows_admin(self, client, admin_headers):
        """Test that admin can access dashboard"""
        response = client.get("/api/v1/admin/dashboard/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "modules" in data

    def test_bom_list_requires_admin(self, client, customer_headers):
        """Test that BOM list requires admin access"""
        response = client.get("/api/v1/admin/bom/", headers=customer_headers)
        assert response.status_code == 403

    def test_bom_list_allows_admin(self, client, admin_headers):
        """Test that admin can access BOM list"""
        response = client.get("/api/v1/admin/bom/", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDashboardEndpoints:
    """Test admin dashboard endpoints"""

    def test_dashboard_returns_summary(self, client, admin_headers, sample_quote, sample_sales_order):
        """Test that dashboard returns proper summary data"""
        response = client.get("/api/v1/admin/dashboard/", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        summary = data["summary"]

        # Check summary fields exist
        assert "pending_quotes" in summary
        assert "quotes_today" in summary
        assert "pending_orders" in summary
        assert "orders_in_production" in summary
        assert "revenue_30_days" in summary

        # We have 1 pending quote
        assert summary["pending_quotes"] >= 1

    def test_dashboard_returns_modules(self, client, admin_headers):
        """Test that dashboard returns module navigation"""
        response = client.get("/api/v1/admin/dashboard/", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        modules = data["modules"]

        assert len(modules) > 0

        # Check module structure
        first_module = modules[0]
        assert "name" in first_module
        assert "description" in first_module
        assert "route" in first_module
        assert "icon" in first_module

        # Check BOM Management module exists
        module_names = [m["name"] for m in modules]
        assert "BOM Management" in module_names

    def test_dashboard_stats_endpoint(self, client, admin_headers):
        """Test quick stats endpoint"""
        response = client.get("/api/v1/admin/dashboard/stats", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert "pending_quotes" in data
        assert "pending_orders" in data
        assert "ready_to_ship" in data

    def test_dashboard_modules_endpoint(self, client, admin_headers):
        """Test modules list endpoint"""
        response = client.get("/api/v1/admin/dashboard/modules", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Check module structure
        for module in data:
            assert "name" in module
            assert "key" in module
            assert "api_route" in module

    def test_profit_summary_endpoint(self, client, admin_headers):
        """Test profit summary endpoint returns proper structure"""
        response = client.get("/api/v1/admin/dashboard/profit-summary", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()

        # Check all required fields exist
        assert "revenue_this_month" in data
        assert "revenue_ytd" in data
        assert "cogs_this_month" in data
        assert "cogs_ytd" in data
        assert "gross_profit_this_month" in data
        assert "gross_profit_ytd" in data

        # Check that values are numeric (can be 0 or positive)
        assert isinstance(float(data["revenue_this_month"]), (int, float))
        assert isinstance(float(data["revenue_ytd"]), (int, float))
        assert isinstance(float(data["cogs_this_month"]), (int, float))
        assert isinstance(float(data["cogs_ytd"]), (int, float))
        assert isinstance(float(data["gross_profit_this_month"]), (int, float))
        assert isinstance(float(data["gross_profit_ytd"]), (int, float))

        # Check margin percentages (can be None if no revenue)
        if data["gross_margin_percent_this_month"] is not None:
            assert isinstance(float(data["gross_margin_percent_this_month"]), (int, float))
        if data["gross_margin_percent_ytd"] is not None:
            assert isinstance(float(data["gross_margin_percent_ytd"]), (int, float))

    def test_profit_summary_requires_admin(self, client, customer_headers):
        """Test that profit summary requires admin access"""
        response = client.get("/api/v1/admin/dashboard/profit-summary", headers=customer_headers)
        assert response.status_code == 403


class TestBOMListEndpoint:
    """Test BOM listing and filtering"""

    def test_list_boms_empty(self, client, admin_headers):
        """Test listing BOMs when none exist"""
        response = client.get("/api/v1/admin/bom/", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_boms_with_data(self, client, admin_headers, sample_bom):
        """Test listing BOMs returns data"""
        response = client.get("/api/v1/admin/bom/", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1

        bom = data[0]
        assert bom["id"] == sample_bom.id
        assert bom["product_sku"] == "TEST-PROD-001"
        assert bom["line_count"] == 2

    def test_list_boms_pagination(self, client, admin_headers, sample_bom):
        """Test BOM list pagination"""
        response = client.get("/api/v1/admin/bom/?skip=0&limit=10", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) <= 10

    def test_list_boms_filter_by_product(self, client, admin_headers, sample_bom):
        """Test filtering BOMs by product_id"""
        response = client.get(f"/api/v1/admin/bom/?product_id={sample_bom.product_id}", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_boms_filter_active_only(self, client, admin_headers, sample_bom, db_session):
        """Test filtering only active BOMs"""
        # Deactivate the sample BOM
        sample_bom.active = False
        db_session.commit()

        response = client.get("/api/v1/admin/bom/?active_only=true", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

        # Include inactive
        response = client.get("/api/v1/admin/bom/?active_only=false", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_boms_search(self, client, admin_headers, sample_bom):
        """Test BOM search by product SKU"""
        response = client.get("/api/v1/admin/bom/?search=TEST-PROD", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get("/api/v1/admin/bom/?search=NONEXISTENT", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0


class TestBOMDetailEndpoint:
    """Test getting single BOM details"""

    def test_get_bom_success(self, client, admin_headers, sample_bom):
        """Test getting a single BOM with lines"""
        response = client.get(f"/api/v1/admin/bom/{sample_bom.id}", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == sample_bom.id
        assert data["product_sku"] == "TEST-PROD-001"
        assert data["version"] == 1
        assert len(data["lines"]) == 2

        # Check line details
        lines = data["lines"]
        material_line = next((line for line in lines if line["sequence"] == 1), None)
        assert material_line is not None
        assert material_line["component_sku"] == "MAT-TEST-PLA"
        assert float(material_line["quantity"]) == 0.50

    def test_get_bom_not_found(self, client, admin_headers):
        """Test 404 for non-existent BOM"""
        response = client.get("/api/v1/admin/bom/99999", headers=admin_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_bom_by_product(self, client, admin_headers, sample_bom):
        """Test getting BOM by product ID"""
        response = client.get(f"/api/v1/admin/bom/product/{sample_bom.product_id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["id"] == sample_bom.id

    def test_get_bom_by_product_not_found(self, client, admin_headers):
        """Test 404 when product has no BOM"""
        response = client.get("/api/v1/admin/bom/product/99999", headers=admin_headers)
        assert response.status_code == 404


class TestBOMCreateEndpoint:
    """Test BOM creation"""

    def test_create_bom_success(self, client, admin_headers, sample_product, sample_material):
        """Test creating a new BOM"""
        response = client.post(
            "/api/v1/admin/bom/",
            headers=admin_headers,
            json={
                "product_id": sample_product.id,
                "code": "NEW-BOM-001",
                "name": "New Test BOM",
                "version": 1,
                "lines": [
                    {
                        "component_id": sample_material.id,
                        "quantity": 1.5,
                        "sequence": 1,
                        "scrap_factor": 2.0,
                        "notes": "Test material line",
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "NEW-BOM-001"
        assert data["name"] == "New Test BOM"
        assert len(data["lines"]) == 1
        assert data["total_cost"] is not None

    def test_create_bom_without_lines(self, client, admin_headers, sample_product):
        """Test creating BOM without lines"""
        response = client.post(
            "/api/v1/admin/bom/",
            headers=admin_headers,
            json={"product_id": sample_product.id, "code": "EMPTY-BOM", "name": "Empty BOM"},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["lines"]) == 0

    def test_create_bom_invalid_product(self, client, admin_headers):
        """Test creating BOM for non-existent product"""
        response = client.post(
            "/api/v1/admin/bom/",
            headers=admin_headers,
            json={"product_id": 99999, "code": "INVALID-BOM", "name": "Invalid BOM"},
        )

        assert response.status_code == 404
        assert "product not found" in response.json()["detail"].lower()

    def test_create_bom_invalid_component(self, client, admin_headers, sample_product):
        """Test creating BOM with invalid component"""
        response = client.post(
            "/api/v1/admin/bom/",
            headers=admin_headers,
            json={
                "product_id": sample_product.id,
                "code": "BAD-BOM",
                "name": "BOM with bad component",
                "lines": [{"component_id": 99999, "quantity": 1.0}],
            },
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()


class TestBOMUpdateEndpoint:
    """Test BOM updates"""

    def test_update_bom_success(self, client, admin_headers, sample_bom):
        """Test updating BOM header fields"""
        response = client.patch(
            f"/api/v1/admin/bom/{sample_bom.id}",
            headers=admin_headers,
            json={"name": "Updated BOM Name", "notes": "Updated notes"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated BOM Name"
        assert data["notes"] == "Updated notes"

    def test_update_bom_version(self, client, admin_headers, sample_bom):
        """Test updating BOM version"""
        response = client.patch(
            f"/api/v1/admin/bom/{sample_bom.id}", headers=admin_headers, json={"version": 2, "revision": "2.0"}
        )

        assert response.status_code == 200
        assert response.json()["version"] == 2
        assert response.json()["revision"] == "2.0"

    def test_update_bom_not_found(self, client, admin_headers):
        """Test updating non-existent BOM"""
        response = client.patch("/api/v1/admin/bom/99999", headers=admin_headers, json={"name": "New Name"})

        assert response.status_code == 404

    def test_delete_bom(self, client, admin_headers, sample_bom, db_session):
        """Test soft deleting BOM"""
        response = client.delete(f"/api/v1/admin/bom/{sample_bom.id}", headers=admin_headers)

        assert response.status_code == 204

        # Verify soft delete
        db_session.refresh(sample_bom)
        assert sample_bom.active == False


class TestBOMLineEndpoints:
    """Test BOM line management"""

    def test_add_line_to_bom(self, client, admin_headers, sample_bom, db_session):
        """Test adding a new line to existing BOM"""
        from app.models.product import Product

        # Create another component
        component = Product(
            sku="NEW-COMP-001",
            name="New Component",
            unit="EA",
            standard_cost=Decimal("5.00"),
            active=True,
        )
        db_session.add(component)
        db_session.commit()

        response = client.post(
            f"/api/v1/admin/bom/{sample_bom.id}/lines",
            headers=admin_headers,
            json={"component_id": component.id, "quantity": 2.0, "sequence": 3, "notes": "New line added"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["component_sku"] == "NEW-COMP-001"
        assert float(data["quantity"]) == 2.0
        assert float(data["line_cost"]) == 10.0  # 2 * $5.00

    def test_add_line_invalid_component(self, client, admin_headers, sample_bom):
        """Test adding line with invalid component"""
        response = client.post(
            f"/api/v1/admin/bom/{sample_bom.id}/lines",
            headers=admin_headers,
            json={"component_id": 99999, "quantity": 1.0},
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_update_line(self, client, admin_headers, sample_bom, db_session):
        """Test updating a BOM line"""
        # Get a line ID
        from app.models.bom import BOMLine

        line = db_session.query(BOMLine).filter(BOMLine.bom_id == sample_bom.id).first()

        response = client.patch(
            f"/api/v1/admin/bom/{sample_bom.id}/lines/{line.id}",
            headers=admin_headers,
            json={"quantity": 0.75, "notes": "Updated quantity"},
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["quantity"]) == 0.75
        assert data["notes"] == "Updated quantity"

    def test_delete_line(self, client, admin_headers, sample_bom, db_session):
        """Test deleting a BOM line"""
        from app.models.bom import BOMLine

        line = db_session.query(BOMLine).filter(BOMLine.bom_id == sample_bom.id).first()
        line_id = line.id

        response = client.delete(f"/api/v1/admin/bom/{sample_bom.id}/lines/{line_id}", headers=admin_headers)

        assert response.status_code == 204

        # Verify deletion
        deleted_line = db_session.query(BOMLine).filter(BOMLine.id == line_id).first()
        assert deleted_line is None


class TestBOMUtilityEndpoints:
    """Test BOM utility operations"""

    def test_recalculate_bom_cost(self, client, admin_headers, sample_bom):
        """Test BOM cost recalculation"""
        response = client.post(f"/api/v1/admin/bom/{sample_bom.id}/recalculate", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["bom_id"] == sample_bom.id
        assert "new_cost" in data
        assert "line_costs" in data
        assert len(data["line_costs"]) == 2

    def test_copy_bom(self, client, admin_headers, sample_bom, db_session):
        """Test copying BOM to another product"""
        from app.models.product import Product

        # Create target product
        target = Product(
            sku="TARGET-PROD",
            name="Target Product",
            unit="EA",
            active=True,
        )
        db_session.add(target)
        db_session.commit()

        response = client.post(
            f"/api/v1/admin/bom/{sample_bom.id}/copy",
            headers=admin_headers,
            json={"target_product_id": target.id, "include_lines": True, "new_version": 1},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["product_id"] == target.id
        assert data["product_sku"] == "TARGET-PROD"
        assert len(data["lines"]) == 2  # Lines should be copied

    def test_copy_bom_without_lines(self, client, admin_headers, sample_bom, db_session):
        """Test copying BOM without lines"""
        from app.models.product import Product

        target = Product(
            sku="TARGET-PROD-2",
            name="Target Product 2",
            unit="EA",
            active=True,
        )
        db_session.add(target)
        db_session.commit()

        response = client.post(
            f"/api/v1/admin/bom/{sample_bom.id}/copy",
            headers=admin_headers,
            json={"target_product_id": target.id, "include_lines": False},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["lines"]) == 0


class TestBOMValidation:
    """Test input validation for BOM operations"""

    def test_create_bom_negative_quantity(self, client, admin_headers, sample_product, sample_material):
        """Test that negative quantities are rejected"""
        response = client.post(
            "/api/v1/admin/bom/",
            headers=admin_headers,
            json={
                "product_id": sample_product.id,
                "code": "BAD-BOM",
                "lines": [{"component_id": sample_material.id, "quantity": -1.0}],
            },
        )

        assert response.status_code == 422  # Validation error

    def test_update_line_invalid_scrap_factor(self, client, admin_headers, sample_bom, db_session):
        """Test that scrap factor > 100 is rejected"""
        from app.models.bom import BOMLine

        line = db_session.query(BOMLine).filter(BOMLine.bom_id == sample_bom.id).first()

        response = client.patch(
            f"/api/v1/admin/bom/{sample_bom.id}/lines/{line.id}", headers=admin_headers, json={"scrap_factor": 150.0}
        )

        assert response.status_code == 422
