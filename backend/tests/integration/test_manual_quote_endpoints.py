"""
Integration tests for manual quote management endpoints

Tests the new manual quote creation system (v1.2.0) including:
- Creating quotes without file upload
- Quote status management
- Quote to order conversion
- Image upload for quotes
- PDF generation with company settings
- Tax calculations
"""
import pytest
import io
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.models.quote import Quote
from app.models.sales_order import SalesOrder
from app.models.company_settings import CompanySettings


class TestManualQuoteCreation:
    """Test manual quote creation without file upload"""

    def test_create_manual_quote_minimal(self, client, admin_headers):
        """Test creating a minimal manual quote"""
        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Custom Widget",
                "quantity": 5,
                "unit_price": "12.50"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["product_name"] == "Custom Widget"
        assert data["quantity"] == 5
        assert float(data["unit_price"]) == 12.50
        assert float(data["subtotal"]) == 62.50  # 5 * 12.50
        assert data["status"] == "pending"
        assert data["quote_number"].startswith("Q-")

    def test_create_manual_quote_with_customer(self, client, admin_headers, customer_user):
        """Test creating quote linked to a customer"""
        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Custom Part",
                "quantity": 1,
                "unit_price": "25.00",
                "customer_id": customer_user.id,
                "customer_name": "John Doe",
                "customer_email": "john@example.com"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["customer_id"] == customer_user.id
        assert data["customer_name"] == "John Doe"
        assert data["customer_email"] == "john@example.com"

    def test_create_manual_quote_with_material_details(self, client, admin_headers):
        """Test creating quote with material and color"""
        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Test Widget",
                "quantity": 3,
                "unit_price": "15.00",
                "material_type": "PETG",
                "color": "Black",
                "customer_notes": "Please package carefully",
                "admin_notes": "Use premium material"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["material_type"] == "PETG"
        assert data["color"] == "Black"
        assert data["customer_notes"] == "Please package carefully"
        assert data["admin_notes"] == "Use premium material"

    def test_create_manual_quote_with_custom_validity(self, client, admin_headers):
        """Test creating quote with custom validity period"""
        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Widget",
                "quantity": 1,
                "unit_price": "10.00",
                "valid_days": 60
            }
        )

        assert response.status_code == 201
        data = response.json()
        
        # Check expiration date is approximately 60 days from now
        expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
        expected_expiry = datetime.utcnow() + timedelta(days=60)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_create_manual_quote_invalid_customer_id(self, client, admin_headers):
        """Test creating quote with non-existent customer ID fails"""
        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Widget",
                "quantity": 1,
                "unit_price": "10.00",
                "customer_id": 99999  # Non-existent
            }
        )

        assert response.status_code == 400
        assert "customer not found" in response.json()["detail"].lower()

    def test_create_manual_quote_validation(self, client, admin_headers):
        """Test quote validation rules"""
        # Missing required fields
        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Widget",
                "quantity": 1
                # Missing unit_price
            }
        )
        assert response.status_code == 422

        # Negative price
        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Widget",
                "quantity": 1,
                "unit_price": "-10.00"
            }
        )
        assert response.status_code == 422

        # Invalid quantity
        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Widget",
                "quantity": 0,
                "unit_price": "10.00"
            }
        )
        assert response.status_code == 422


class TestManualQuoteTaxCalculation:
    """Test tax calculation with company settings"""

    def test_quote_with_tax_enabled(self, client, admin_headers, db_session):
        """Test quote with tax when company settings enable it"""
        # Create company settings with tax
        settings = CompanySettings(
            id=1,
            tax_enabled=True,
            tax_rate=Decimal("0.0825"),  # 8.25%
            tax_name="Sales Tax"
        )
        db_session.add(settings)
        db_session.commit()

        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Widget",
                "quantity": 1,
                "unit_price": "100.00"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert float(data["subtotal"]) == 100.00
        assert float(data["tax_rate"]) == 0.0825
        assert float(data["tax_amount"]) == 8.25
        assert float(data["total_price"]) == 108.25

    def test_quote_with_tax_disabled(self, client, admin_headers, db_session):
        """Test quote without tax when company settings disable it"""
        settings = CompanySettings(
            id=1,
            tax_enabled=False
        )
        db_session.add(settings)
        db_session.commit()

        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Widget",
                "quantity": 1,
                "unit_price": "100.00"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert float(data["subtotal"]) == 100.00
        assert data["tax_rate"] is None
        assert data["tax_amount"] is None
        assert float(data["total_price"]) == 100.00

    def test_quote_with_explicit_tax_override(self, client, admin_headers, db_session):
        """Test explicitly applying/not applying tax"""
        settings = CompanySettings(
            id=1,
            tax_enabled=True,
            tax_rate=Decimal("0.10")
        )
        db_session.add(settings)
        db_session.commit()

        # Explicitly disable tax for this quote
        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Widget",
                "quantity": 1,
                "unit_price": "100.00",
                "apply_tax": False
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tax_rate"] is None
        assert float(data["total_price"]) == 100.00


class TestQuoteRetrieval:
    """Test quote listing and retrieval endpoints"""

    def test_list_quotes(self, client, admin_headers, sample_quote):
        """Test listing all quotes"""
        response = client.get("/api/v1/quotes/", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(q["id"] == sample_quote.id for q in data)

    def test_list_quotes_with_status_filter(self, client, admin_headers, db_session):
        """Test filtering quotes by status"""
        # Create quotes with different statuses
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        q1 = Quote(
            user_id=admin.id,
            quote_number="Q-2025-001",
            product_name="Product 1",
            quantity=1,
            total_price=Decimal("10.00"),
            file_format="manual",
            file_size_bytes=0,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        q2 = Quote(
            user_id=admin.id,
            quote_number="Q-2025-002",
            product_name="Product 2",
            quantity=1,
            total_price=Decimal("20.00"),
            file_format="manual",
            file_size_bytes=0,
            status="approved",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add_all([q1, q2])
        db_session.commit()

        # Filter by pending
        response = client.get("/api/v1/quotes/?status=pending", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(q["status"] == "pending" for q in data)

        # Filter by approved
        response = client.get("/api/v1/quotes/?status=approved", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(q["status"] == "approved" for q in data)

    def test_list_quotes_with_search(self, client, admin_headers, db_session):
        """Test searching quotes"""
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        quote = Quote(
            user_id=admin.id,
            quote_number="Q-2025-SEARCH",
            product_name="Special Widget",
            customer_name="Alice Johnson",
            customer_email="alice@example.com",
            quantity=1,
            total_price=Decimal("10.00"),
            file_format="manual",
            file_size_bytes=0,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(quote)
        db_session.commit()

        # Search by quote number
        response = client.get("/api/v1/quotes/?search=SEARCH", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

        # Search by product name
        response = client.get("/api/v1/quotes/?search=Special", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

        # Search by customer name
        response = client.get("/api/v1/quotes/?search=Alice", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_quote_detail(self, client, admin_headers, sample_quote):
        """Test getting detailed quote information"""
        response = client.get(f"/api/v1/quotes/{sample_quote.id}", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_quote.id
        assert "quote_number" in data
        assert "product_name" in data
        assert "shipping_address_line1" in data  # Full detail fields

    def test_get_quote_not_found(self, client, admin_headers):
        """Test getting non-existent quote"""
        response = client.get("/api/v1/quotes/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_get_quote_stats(self, client, admin_headers, db_session):
        """Test quote statistics endpoint"""
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        # Create quotes with different statuses
        quotes = [
            Quote(
                user_id=admin.id,
                quote_number=f"Q-2025-STAT{i}",
                product_name=f"Product {i}",
                quantity=1,
                total_price=Decimal("100.00"),
                file_format="manual",
                file_size_bytes=0,
                status=status,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            for i, status in enumerate(["pending", "approved", "rejected", "converted"])
        ]
        db_session.add_all(quotes)
        db_session.commit()

        response = client.get("/api/v1/quotes/stats", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "pending" in data
        assert "approved" in data
        assert "rejected" in data
        assert "converted" in data
        assert "total_value" in data
        assert data["pending"] >= 1
        assert data["approved"] >= 1


class TestQuoteUpdate:
    """Test quote update functionality"""

    def test_update_quote_basic_fields(self, client, admin_headers, sample_quote):
        """Test updating basic quote fields"""
        response = client.patch(
            f"/api/v1/quotes/{sample_quote.id}",
            headers=admin_headers,
            json={
                "product_name": "Updated Product Name",
                "quantity": 10,
                "customer_notes": "Updated notes"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["product_name"] == "Updated Product Name"
        assert data["quantity"] == 10
        assert data["customer_notes"] == "Updated notes"

    def test_update_quote_pricing_recalculates(self, client, admin_headers, sample_quote):
        """Test that updating price/quantity recalculates totals"""
        response = client.patch(
            f"/api/v1/quotes/{sample_quote.id}",
            headers=admin_headers,
            json={
                "unit_price": "20.00",
                "quantity": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["unit_price"]) == 20.00
        assert data["quantity"] == 5
        assert float(data["subtotal"]) == 100.00

    def test_update_quote_shipping_address(self, client, admin_headers, sample_quote):
        """Test updating shipping address"""
        response = client.patch(
            f"/api/v1/quotes/{sample_quote.id}",
            headers=admin_headers,
            json={
                "shipping_name": "John Doe",
                "shipping_address_line1": "123 Main St",
                "shipping_city": "Anytown",
                "shipping_state": "CA",
                "shipping_zip": "12345"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["shipping_name"] == "John Doe"
        assert data["shipping_address_line1"] == "123 Main St"
        assert data["shipping_city"] == "Anytown"

    def test_update_quote_tax_setting(self, client, admin_headers, sample_quote, db_session):
        """Test changing tax application on existing quote"""
        # Set up company settings
        settings = CompanySettings(
            id=1,
            tax_enabled=True,
            tax_rate=Decimal("0.08")
        )
        db_session.add(settings)
        db_session.commit()

        # Update quote to apply tax
        response = client.patch(
            f"/api/v1/quotes/{sample_quote.id}",
            headers=admin_headers,
            json={"apply_tax": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tax_rate"] is not None
        assert data["tax_amount"] is not None

    def test_cannot_update_converted_quote(self, client, admin_headers, db_session):
        """Test that converted quotes cannot be edited"""
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        quote = Quote(
            user_id=admin.id,
            quote_number="Q-2025-CONVERTED",
            product_name="Product",
            quantity=1,
            total_price=Decimal("10.00"),
            file_format="manual",
            file_size_bytes=0,
            status="converted",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(quote)
        db_session.commit()

        response = client.patch(
            f"/api/v1/quotes/{quote.id}",
            headers=admin_headers,
            json={"product_name": "New Name"}
        )

        assert response.status_code == 400
        assert "cannot edit" in response.json()["detail"].lower()


class TestQuoteStatusManagement:
    """Test quote status transitions"""

    def test_approve_quote(self, client, admin_headers, sample_quote):
        """Test approving a pending quote"""
        response = client.patch(
            f"/api/v1/quotes/{sample_quote.id}/status",
            headers=admin_headers,
            json={"status": "approved"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_at"] is not None
        assert data["approval_method"] == "manual"

    def test_reject_quote_with_reason(self, client, admin_headers, sample_quote):
        """Test rejecting a quote with reason"""
        response = client.patch(
            f"/api/v1/quotes/{sample_quote.id}/status",
            headers=admin_headers,
            json={
                "status": "rejected",
                "rejection_reason": "Requirements not clear"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Requirements not clear"

    def test_accept_quote(self, client, admin_headers, sample_quote, db_session):
        """Test customer accepting a quote"""
        # First approve the quote
        sample_quote.status = "approved"
        db_session.commit()

        response = client.patch(
            f"/api/v1/quotes/{sample_quote.id}/status",
            headers=admin_headers,
            json={"status": "accepted"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_cancel_quote(self, client, admin_headers, sample_quote):
        """Test cancelling a quote"""
        response = client.patch(
            f"/api/v1/quotes/{sample_quote.id}/status",
            headers=admin_headers,
            json={"status": "cancelled"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_invalid_status_transition(self, client, admin_headers, sample_quote):
        """Test invalid status value"""
        response = client.patch(
            f"/api/v1/quotes/{sample_quote.id}/status",
            headers=admin_headers,
            json={"status": "invalid_status"}
        )

        assert response.status_code == 400

    def test_cannot_change_converted_quote_status(self, client, admin_headers, db_session):
        """Test that converted quote status cannot be changed"""
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        quote = Quote(
            user_id=admin.id,
            quote_number="Q-2025-LOCKED",
            product_name="Product",
            quantity=1,
            total_price=Decimal("10.00"),
            file_format="manual",
            file_size_bytes=0,
            status="converted",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(quote)
        db_session.commit()

        response = client.patch(
            f"/api/v1/quotes/{quote.id}/status",
            headers=admin_headers,
            json={"status": "pending"}
        )

        assert response.status_code == 400


class TestQuoteConversion:
    """Test converting quotes to sales orders"""

    def test_convert_approved_quote_to_order(self, client, admin_headers, db_session):
        """Test converting an approved quote to a sales order"""
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        quote = Quote(
            user_id=admin.id,
            quote_number="Q-2025-CONVERT",
            product_name="Product to Convert",
            customer_email="customer@test.com",
            quantity=5,
            unit_price=Decimal("15.00"),
            subtotal=Decimal("75.00"),
            total_price=Decimal("75.00"),
            file_format="manual",
            file_size_bytes=0,
            status="approved",
            shipping_name="John Doe",
            shipping_address_line1="123 Main St",
            shipping_city="Anytown",
            shipping_state="CA",
            shipping_zip="12345",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(quote)
        db_session.commit()

        response = client.post(
            f"/api/v1/quotes/{quote.id}/convert",
            headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert "order_number" in data
        assert data["order_number"].startswith("SO-")
        
        # Verify quote is marked as converted
        db_session.refresh(quote)
        assert quote.status == "converted"
        assert quote.sales_order_id is not None

    def test_convert_accepted_quote_to_order(self, client, admin_headers, db_session):
        """Test converting an accepted quote to a sales order"""
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        quote = Quote(
            user_id=admin.id,
            quote_number="Q-2025-ACCEPT",
            product_name="Accepted Product",
            quantity=1,
            unit_price=Decimal("25.00"),
            subtotal=Decimal("25.00"),
            total_price=Decimal("25.00"),
            file_format="manual",
            file_size_bytes=0,
            status="accepted",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(quote)
        db_session.commit()

        response = client.post(
            f"/api/v1/quotes/{quote.id}/convert",
            headers=admin_headers
        )

        assert response.status_code == 201

    def test_cannot_convert_pending_quote(self, client, admin_headers, sample_quote):
        """Test that pending quotes cannot be converted"""
        response = client.post(
            f"/api/v1/quotes/{sample_quote.id}/convert",
            headers=admin_headers
        )

        assert response.status_code == 400
        assert "must be approved or accepted" in response.json()["detail"].lower()

    def test_cannot_convert_expired_quote(self, client, admin_headers, db_session):
        """Test that expired quotes cannot be converted"""
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        quote = Quote(
            user_id=admin.id,
            quote_number="Q-2025-EXPIRED",
            product_name="Expired Product",
            quantity=1,
            total_price=Decimal("10.00"),
            file_format="manual",
            file_size_bytes=0,
            status="approved",
            expires_at=datetime.utcnow() - timedelta(days=1)  # Expired
        )
        db_session.add(quote)
        db_session.commit()

        response = client.post(
            f"/api/v1/quotes/{quote.id}/convert",
            headers=admin_headers
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_cannot_convert_already_converted_quote(self, client, admin_headers, db_session):
        """Test that already converted quotes cannot be reconverted"""
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        quote = Quote(
            user_id=admin.id,
            quote_number="Q-2025-ALREADY",
            product_name="Product",
            quantity=1,
            total_price=Decimal("10.00"),
            file_format="manual",
            file_size_bytes=0,
            status="approved",
            sales_order_id=1,  # Already has an order
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(quote)
        db_session.commit()

        response = client.post(
            f"/api/v1/quotes/{quote.id}/convert",
            headers=admin_headers
        )

        assert response.status_code == 400
        assert "already converted" in response.json()["detail"].lower()


class TestQuoteImageManagement:
    """Test quote image upload/retrieval/deletion"""

    def test_upload_quote_image(self, client, admin_headers, sample_quote):
        """Test uploading an image for a quote"""
        # Create fake image data
        image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        image_file = io.BytesIO(image_data)

        response = client.post(
            f"/api/v1/quotes/{sample_quote.id}/image",
            headers=admin_headers,
            files={"file": ("product.png", image_file, "image/png")}
        )

        assert response.status_code == 200
        assert "uploaded successfully" in response.json()["message"].lower()

    def test_upload_quote_image_invalid_type(self, client, admin_headers, sample_quote):
        """Test that invalid image types are rejected"""
        file_data = b"Not an image"
        file = io.BytesIO(file_data)

        response = client.post(
            f"/api/v1/quotes/{sample_quote.id}/image",
            headers=admin_headers,
            files={"file": ("document.pdf", file, "application/pdf")}
        )

        assert response.status_code == 400
        assert "invalid file type" in response.json()["detail"].lower()

    def test_upload_quote_image_too_large(self, client, admin_headers, sample_quote):
        """Test that oversized images are rejected"""
        # Create 6MB of fake data
        large_data = b"x" * (6 * 1024 * 1024)
        large_file = io.BytesIO(large_data)

        response = client.post(
            f"/api/v1/quotes/{sample_quote.id}/image",
            headers=admin_headers,
            files={"file": ("large.png", large_file, "image/png")}
        )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()

    def test_get_quote_image(self, client, admin_headers, sample_quote, db_session):
        """Test retrieving a quote image"""
        # Add image data to quote
        sample_quote.image_data = b"fake image data"
        sample_quote.image_filename = "test.png"
        sample_quote.image_mime_type = "image/png"
        db_session.commit()

        response = client.get(
            f"/api/v1/quotes/{sample_quote.id}/image",
            headers=admin_headers
        )

        assert response.status_code == 200
        assert response.content == b"fake image data"
        assert response.headers["content-type"] == "image/png"

    def test_get_quote_image_not_found(self, client, admin_headers, sample_quote):
        """Test getting image when none exists"""
        response = client.get(
            f"/api/v1/quotes/{sample_quote.id}/image",
            headers=admin_headers
        )

        assert response.status_code == 404

    def test_delete_quote_image(self, client, admin_headers, sample_quote, db_session):
        """Test deleting a quote image"""
        # Add image data to quote
        sample_quote.image_data = b"fake image data"
        sample_quote.image_filename = "test.png"
        db_session.commit()

        response = client.delete(
            f"/api/v1/quotes/{sample_quote.id}/image",
            headers=admin_headers
        )

        assert response.status_code == 200
        
        # Verify image was deleted
        db_session.refresh(sample_quote)
        assert sample_quote.image_data is None


class TestQuotePDFGeneration:
    """Test PDF generation for quotes"""

    def test_generate_quote_pdf_basic(self, client, admin_headers, sample_quote):
        """Test generating a basic PDF for a quote"""
        response = client.get(
            f"/api/v1/quotes/{sample_quote.id}/pdf",
            headers=admin_headers
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        assert sample_quote.quote_number in response.headers["content-disposition"]

    def test_generate_quote_pdf_with_company_settings(self, client, admin_headers, sample_quote, db_session):
        """Test PDF generation includes company settings"""
        # Create company settings
        settings = CompanySettings(
            id=1,
            company_name="Test Company Inc",
            company_address_line1="123 Business St",
            company_city="Cityville",
            company_state="CA",
            company_phone="555-1234",
            quote_terms="Payment due in 30 days",
            quote_footer="Thank you for your business!"
        )
        db_session.add(settings)
        db_session.commit()

        response = client.get(
            f"/api/v1/quotes/{sample_quote.id}/pdf",
            headers=admin_headers
        )

        assert response.status_code == 200
        # PDF content should be generated (can't easily verify content without PDF parser)

    def test_generate_quote_pdf_with_tax(self, client, admin_headers, db_session):
        """Test PDF generation with tax breakdown"""
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        settings = CompanySettings(
            id=1,
            tax_enabled=True,
            tax_rate=Decimal("0.0825"),
            tax_name="Sales Tax"
        )
        db_session.add(settings)

        quote = Quote(
            user_id=admin.id,
            quote_number="Q-2025-TAX",
            product_name="Taxable Product",
            quantity=1,
            unit_price=Decimal("100.00"),
            subtotal=Decimal("100.00"),
            tax_rate=Decimal("0.0825"),
            tax_amount=Decimal("8.25"),
            total_price=Decimal("108.25"),
            file_format="manual",
            file_size_bytes=0,
            status="approved",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(quote)
        db_session.commit()

        response = client.get(
            f"/api/v1/quotes/{quote.id}/pdf",
            headers=admin_headers
        )

        assert response.status_code == 200

    def test_generate_quote_pdf_not_found(self, client, admin_headers):
        """Test PDF generation for non-existent quote"""
        response = client.get(
            "/api/v1/quotes/99999/pdf",
            headers=admin_headers
        )

        assert response.status_code == 404


class TestQuoteDeletion:
    """Test quote deletion"""

    def test_delete_pending_quote(self, client, admin_headers, sample_quote):
        """Test deleting a pending quote"""
        quote_id = sample_quote.id

        response = client.delete(
            f"/api/v1/quotes/{quote_id}",
            headers=admin_headers
        )

        assert response.status_code == 204

        # Verify quote was deleted
        response = client.get(f"/api/v1/quotes/{quote_id}", headers=admin_headers)
        assert response.status_code == 404

    def test_cannot_delete_converted_quote(self, client, admin_headers, db_session):
        """Test that converted quotes cannot be deleted"""
        from app.models.user import User
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        
        quote = Quote(
            user_id=admin.id,
            quote_number="Q-2025-NODELETE",
            product_name="Product",
            quantity=1,
            total_price=Decimal("10.00"),
            file_format="manual",
            file_size_bytes=0,
            status="converted",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(quote)
        db_session.commit()

        response = client.delete(
            f"/api/v1/quotes/{quote.id}",
            headers=admin_headers
        )

        assert response.status_code == 400
        assert "cannot delete" in response.json()["detail"].lower()

    def test_delete_quote_not_found(self, client, admin_headers):
        """Test deleting non-existent quote"""
        response = client.delete(
            "/api/v1/quotes/99999",
            headers=admin_headers
        )

        assert response.status_code == 404


class TestQuoteNumberGeneration:
    """Test quote number generation logic"""

    def test_sequential_quote_numbers(self, client, admin_headers):
        """Test that quote numbers are generated sequentially"""
        year = datetime.utcnow().year
        quote_numbers = []

        for i in range(3):
            response = client.post(
                "/api/v1/quotes/",
                headers=admin_headers,
                json={
                    "product_name": f"Product {i}",
                    "quantity": 1,
                    "unit_price": "10.00"
                }
            )
            assert response.status_code == 201
            quote_numbers.append(response.json()["quote_number"])

        # Verify sequential numbering
        assert quote_numbers[0] == f"Q-{year}-001"
        assert quote_numbers[1] == f"Q-{year}-002"
        assert quote_numbers[2] == f"Q-{year}-003"

    def test_quote_numbers_include_year(self, client, admin_headers):
        """Test that quote numbers include the current year"""
        response = client.post(
            "/api/v1/quotes/",
            headers=admin_headers,
            json={
                "product_name": "Test Product",
                "quantity": 1,
                "unit_price": "10.00"
            }
        )

        assert response.status_code == 201
        quote_number = response.json()["quote_number"]
        year = datetime.utcnow().year
        assert f"-{year}-" in quote_number