"""
Integration tests for quote endpoints

Tests the full API flow for quote creation, file upload, pricing, and workflow management

NOTE: These tests are for a customer portal quoting feature that has not been implemented yet.
The current quotes API is an admin-only manual quote management system.
Skipping until the customer portal upload feature is built.
"""
import pytest

# Skip all tests in this module - customer portal quoting feature not yet implemented
pytestmark = pytest.mark.skip(reason="Customer portal quote upload feature not yet implemented")
import io
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import get_db


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database for each test"""
    from app.models.user import User, RefreshToken
    from app.models.quote import Quote, QuoteFile
    from app.models.product import Product
    from app.models.bom import BOM, BOMLine

    # Create tables
    User.__table__.create(bind=engine, checkfirst=True)
    RefreshToken.__table__.create(bind=engine, checkfirst=True)
    Product.__table__.create(bind=engine, checkfirst=True)
    BOM.__table__.create(bind=engine, checkfirst=True)
    BOMLine.__table__.create(bind=engine, checkfirst=True)
    Quote.__table__.create(bind=engine, checkfirst=True)
    QuoteFile.__table__.create(bind=engine, checkfirst=True)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop tables in reverse order to handle foreign keys
        QuoteFile.__table__.drop(bind=engine, checkfirst=True)
        Quote.__table__.drop(bind=engine, checkfirst=True)
        BOMLine.__table__.drop(bind=engine, checkfirst=True)
        BOM.__table__.drop(bind=engine, checkfirst=True)
        Product.__table__.drop(bind=engine, checkfirst=True)
        RefreshToken.__table__.drop(bind=engine, checkfirst=True)
        User.__table__.drop(bind=engine, checkfirst=True)


@pytest.fixture
def client(db_session):
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user(client):
    """Create and authenticate a test user"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
        }
    )
    access_token = response.json()["access_token"]
    user_id = response.json()["id"]
    return {"token": access_token, "id": user_id}


@pytest.fixture
def mock_file_storage():
    """Mock file storage service"""
    import uuid

    def generate_file_metadata(*args, **kwargs):
        """Generate unique file metadata for each call"""
        unique_id = str(uuid.uuid4())[:8]
        return {
            'original_filename': 'test_model.3mf',
            'stored_filename': f'test_model_{unique_id}.3mf',
            'file_path': f'/uploads/test_model_{unique_id}.3mf',
            'file_size_bytes': 1024000,  # 1MB
            'file_format': '.3mf',
            'mime_type': 'application/octet-stream',
            'file_hash': f'{unique_id}def456',
        }

    with patch("app.api.v1.endpoints.quotes.file_storage") as mock:
        mock.validate_file.return_value = (True, None)
        mock.save_file = AsyncMock(side_effect=generate_file_metadata)
        yield mock


@pytest.fixture
def mock_bambu_client():
    """Mock Bambu Suite client"""
    with patch("app.api.v1.endpoints.quotes.bambu_client") as mock:
        mock.generate_quote = AsyncMock(return_value={
            'success': True,
            'material_grams': Decimal('125.5'),
            'print_time_hours': Decimal('6.25'),
            'material_cost': Decimal('3.14'),
            'labor_cost': Decimal('9.38'),
            'unit_price': Decimal('25.04'),
            'total_price': Decimal('25.04'),
            'dimensions_x': Decimal('100.0'),
            'dimensions_y': Decimal('100.0'),
            'dimensions_z': Decimal('50.0'),
        })
        yield mock


class TestQuoteUpload:
    """Test quote upload endpoint: POST /api/v1/quotes/upload"""

    def test_upload_3mf_file_success(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test successful upload of .3mf file"""
        file_content = b"fake 3mf file content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("test_model.3mf", file, "application/octet-stream")},
            data={
                "product_name": "Test Product",
                "quantity": 1,
                "material_type": "PLA",
                "finish": "standard",
                "rush_level": "standard",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["product_name"] == "Test Product"
        assert data["quantity"] == 1
        assert data["material_type"] == "PLA"
        assert data["finish"] == "standard"
        assert data["rush_level"] == "standard"
        assert "quote_number" in data
        assert data["quote_number"].startswith("Q-")
        assert "unit_price" in data
        assert "total_price" in data

    def test_upload_stl_file_success(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test successful upload of .stl file"""
        file_content = b"fake stl file content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("test_model.stl", file, "application/octet-stream")},
            data={
                "quantity": 5,
                "material_type": "PETG",
                "finish": "smooth",
                "rush_level": "rush",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["quantity"] == 5
        assert data["material_type"] == "PETG"
        assert data["finish"] == "smooth"
        assert data["rush_level"] == "rush"

    def test_upload_without_authentication(self, client, mock_file_storage, mock_bambu_client):
        """Test that upload without authentication fails"""
        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/v1/quotes/upload",
            files={"file": ("test_model.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        assert response.status_code == 401

    def test_upload_invalid_file_format(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that invalid file formats are rejected"""
        mock_file_storage.validate_file.return_value = (False, "Invalid file format. Only .3mf and .stl files are allowed")

        file_content = b"fake pdf content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("document.pdf", file, "application/pdf")},
            data={
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        assert response.status_code == 400
        assert "Invalid file format" in response.json()["detail"]

    def test_upload_file_too_large(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that oversized files are rejected"""
        mock_file_storage.validate_file.return_value = (False, "File size exceeds maximum allowed size (100MB)")

        file_content = b"x" * (101 * 1024 * 1024)  # 101MB
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("huge_model.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        assert response.status_code == 400
        assert "exceeds maximum" in response.json()["detail"].lower()

    def test_upload_with_all_materials(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test upload with different material types"""
        materials = ["PLA", "PETG", "ABS", "ASA", "TPU"]

        for material in materials:
            file_content = b"fake file content"
            file = io.BytesIO(file_content)

            response = client.post(
                "/api/v1/quotes/upload",
                headers={"Authorization": f"Bearer {authenticated_user['token']}"},
                files={"file": (f"model_{material.lower()}.3mf", file, "application/octet-stream")},
                data={
                    "quantity": 1,
                    "material_type": material,
                }
            )

            assert response.status_code == 201
            assert response.json()["material_type"] == material

    def test_upload_generates_sequential_quote_numbers(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that quote numbers are generated sequentially"""
        quote_numbers = []

        for i in range(3):
            file_content = b"fake file content"
            file = io.BytesIO(file_content)

            response = client.post(
                "/api/v1/quotes/upload",
                headers={"Authorization": f"Bearer {authenticated_user['token']}"},
                files={"file": (f"model_{i}.3mf", file, "application/octet-stream")},
                data={
                    "quantity": 1,
                    "material_type": "PLA",
                }
            )

            assert response.status_code == 201
            quote_numbers.append(response.json()["quote_number"])

        # Check sequential numbering
        year = datetime.utcnow().year
        assert quote_numbers[0] == f"Q-{year}-001"
        assert quote_numbers[1] == f"Q-{year}-002"
        assert quote_numbers[2] == f"Q-{year}-003"


class TestQuotePricing:
    """Test quote pricing calculations"""

    def test_pricing_under_50_auto_approved(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that quotes under $50 are auto-approved"""
        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('50.0'),
            'print_time_hours': Decimal('2.5'),
            'material_cost': Decimal('1.25'),
            'labor_cost': Decimal('3.75'),
            'unit_price': Decimal('10.00'),
            'total_price': Decimal('10.00'),
            'dimensions_x': Decimal('50.0'),
            'dimensions_y': Decimal('50.0'),
            'dimensions_z': Decimal('25.0'),
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("small_model.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert float(data["total_price"]) < 50.0
        assert data["status"] == "approved"
        assert data["auto_approved"] is True
        assert data["auto_approve_eligible"] is True
        assert data["approval_method"] == "auto"

    def test_pricing_over_50_requires_review(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that quotes over $50 require manual review"""
        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('250.0'),
            'print_time_hours': Decimal('12.5'),
            'material_cost': Decimal('6.25'),
            'labor_cost': Decimal('18.75'),
            'unit_price': Decimal('55.00'),
            'total_price': Decimal('55.00'),
            'dimensions_x': Decimal('150.0'),
            'dimensions_y': Decimal('150.0'),
            'dimensions_z': Decimal('75.0'),
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("large_model.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert float(data["total_price"]) > 50.0
        assert data["status"] == "pending"
        assert data["auto_approved"] is False
        assert data["auto_approve_eligible"] is False
        assert "exceeds $50 threshold" in data["requires_review_reason"]

    def test_rush_pricing_more_expensive_than_standard(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that rush orders cost more than standard orders"""
        # Create standard order
        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('100.0'),
            'print_time_hours': Decimal('5.0'),
            'material_cost': Decimal('2.50'),
            'labor_cost': Decimal('7.50'),
            'unit_price': Decimal('20.00'),
            'total_price': Decimal('20.00'),
            'dimensions_x': Decimal('100.0'),
            'dimensions_y': Decimal('100.0'),
            'dimensions_z': Decimal('50.0'),
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        standard_response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("model_standard.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
                "rush_level": "standard",
            }
        )

        # Create rush order with higher pricing
        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('100.0'),
            'print_time_hours': Decimal('5.0'),
            'material_cost': Decimal('2.50'),
            'labor_cost': Decimal('7.50'),
            'unit_price': Decimal('25.00'),  # +25% for rush
            'total_price': Decimal('25.00'),
            'dimensions_x': Decimal('100.0'),
            'dimensions_y': Decimal('100.0'),
            'dimensions_z': Decimal('50.0'),
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        rush_response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("model_rush.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
                "rush_level": "rush",
            }
        )

        standard_price = float(standard_response.json()["total_price"])
        rush_price = float(rush_response.json()["total_price"])

        assert rush_price > standard_price

    def test_quantity_multiplies_price(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that quantity correctly multiplies the total price"""
        unit_price = Decimal('15.00')
        quantity = 10

        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('75.0'),
            'print_time_hours': Decimal('3.75'),
            'material_cost': Decimal('1.88'),
            'labor_cost': Decimal('5.63'),
            'unit_price': unit_price,
            'total_price': unit_price * quantity,
            'dimensions_x': Decimal('75.0'),
            'dimensions_y': Decimal('75.0'),
            'dimensions_z': Decimal('37.5'),
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("model_batch.3mf", file, "application/octet-stream")},
            data={
                "quantity": quantity,
                "material_type": "PLA",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert float(data["unit_price"]) == float(unit_price)
        assert float(data["total_price"]) == float(unit_price * quantity)


class TestQuoteWorkflow:
    """Test quote workflow and status transitions"""

    def test_get_user_quotes_list(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test retrieving list of user's quotes"""
        # Create multiple quotes
        for i in range(3):
            file_content = b"fake file content"
            file = io.BytesIO(file_content)

            client.post(
                "/api/v1/quotes/upload",
                headers={"Authorization": f"Bearer {authenticated_user['token']}"},
                files={"file": (f"model_{i}.3mf", file, "application/octet-stream")},
                data={
                    "quantity": 1,
                    "material_type": "PLA",
                }
            )

        # Get quotes list
        response = client.get(
            "/api/v1/quotes/",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("quote_number" in quote for quote in data)

    def test_get_quote_details(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test retrieving detailed quote information"""
        # Create a quote
        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        create_response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("model.3mf", file, "application/octet-stream")},
            data={
                "product_name": "Test Product",
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        quote_id = create_response.json()["id"]

        # Get quote details
        response = client.get(
            f"/api/v1/quotes/{quote_id}",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == quote_id
        assert data["product_name"] == "Test Product"
        assert "files" in data  # Should include file information

    def test_get_quote_details_unauthorized(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that users cannot access other users' quotes"""
        # Create a quote as first user
        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        create_response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("model.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        quote_id = create_response.json()["id"]

        # Register second user
        second_user = client.post(
            "/api/v1/auth/register",
            json={
                "email": "seconduser@example.com",
                "password": "SecurePass123!",
                "first_name": "Second",
                "last_name": "User",
            }
        )
        second_token = second_user.json()["access_token"]

        # Try to access first user's quote
        response = client.get(
            f"/api/v1/quotes/{quote_id}",
            headers={"Authorization": f"Bearer {second_token}"},
        )

        assert response.status_code == 403

    def test_accept_approved_quote(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test accepting an approved quote"""
        # Create auto-approved quote (under $50)
        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('50.0'),
            'print_time_hours': Decimal('2.5'),
            'material_cost': Decimal('1.25'),
            'labor_cost': Decimal('3.75'),
            'unit_price': Decimal('10.00'),
            'total_price': Decimal('10.00'),
            'dimensions_x': Decimal('50.0'),
            'dimensions_y': Decimal('50.0'),
            'dimensions_z': Decimal('25.0'),
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        create_response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("model.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
                "color": "BLK",  # Color is required for BOM creation
            }
        )

        quote_id = create_response.json()["id"]
        assert create_response.json()["status"] == "approved"

        # Accept the quote - mock BOM creation since it requires material_types table
        with patch('app.api.v1.endpoints.quotes.auto_create_product_and_bom') as mock_bom:
            # Mock returns (product, bom) tuple
            mock_product = MagicMock()
            mock_product.id = 1
            mock_product.sku = "CUSTOM-TEST"
            mock_bom_obj = MagicMock()
            mock_bom_obj.id = 1
            mock_bom.return_value = (mock_product, mock_bom_obj)

            response = client.post(
                f"/api/v1/quotes/{quote_id}/accept",
                headers={"Authorization": f"Bearer {authenticated_user['token']}"},
                json={"customer_notes": "Looks good!"}
            )

        assert response.status_code == 200, f"Accept failed (status={response.status_code}): {response.text}"
        data = response.json()
        assert data["status"] == "accepted"
        assert data["customer_notes"] == "Looks good!"

    def test_cannot_accept_pending_quote(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that pending quotes cannot be accepted"""
        # Create quote requiring review (over $50)
        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('250.0'),
            'print_time_hours': Decimal('12.5'),
            'material_cost': Decimal('6.25'),
            'labor_cost': Decimal('18.75'),
            'unit_price': Decimal('55.00'),
            'total_price': Decimal('55.00'),
            'dimensions_x': Decimal('150.0'),
            'dimensions_y': Decimal('150.0'),
            'dimensions_z': Decimal('75.0'),
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        create_response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("model.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        quote_id = create_response.json()["id"]
        assert create_response.json()["status"] == "pending"

        # Try to accept pending quote
        response = client.post(
            f"/api/v1/quotes/{quote_id}/accept",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            json={}
        )

        assert response.status_code == 400
        assert "Cannot accept quote" in response.json()["detail"]

    def test_update_quote_status_to_approved(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test manually approving a quote (admin action)"""
        # Create quote requiring review
        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('250.0'),
            'print_time_hours': Decimal('12.5'),
            'material_cost': Decimal('6.25'),
            'labor_cost': Decimal('18.75'),
            'unit_price': Decimal('55.00'),
            'total_price': Decimal('55.00'),
            'dimensions_x': Decimal('150.0'),
            'dimensions_y': Decimal('150.0'),
            'dimensions_z': Decimal('75.0'),
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        create_response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("model.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        quote_id = create_response.json()["id"]

        # Manually approve
        response = client.patch(
            f"/api/v1/quotes/{quote_id}/status",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            json={
                "status": "approved",
                "admin_notes": "Manually reviewed and approved"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approval_method"] == "manual"
        assert data["admin_notes"] == "Manually reviewed and approved"

    def test_reject_quote_with_reason(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test rejecting a quote with reason"""
        # Create quote
        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        create_response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("model.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        quote_id = create_response.json()["id"]

        # Reject quote
        response = client.patch(
            f"/api/v1/quotes/{quote_id}/status",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            json={
                "status": "rejected",
                "rejection_reason": "File contains errors"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "File contains errors"

    def test_quote_expiration(self, client, authenticated_user, mock_file_storage, mock_bambu_client, db_session):
        """Test that expired quotes cannot be accepted"""
        from app.models.quote import Quote

        # Create auto-approved quote
        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('50.0'),
            'print_time_hours': Decimal('2.5'),
            'material_cost': Decimal('1.25'),
            'labor_cost': Decimal('3.75'),
            'unit_price': Decimal('10.00'),
            'total_price': Decimal('10.00'),
            'dimensions_x': Decimal('50.0'),
            'dimensions_y': Decimal('50.0'),
            'dimensions_z': Decimal('25.0'),
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        create_response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("model.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "PLA",
            }
        )

        quote_id = create_response.json()["id"]

        # Manually set expiration to past
        quote = db_session.query(Quote).filter(Quote.id == quote_id).first()
        quote.expires_at = datetime.utcnow() - timedelta(days=1)
        db_session.commit()

        # Try to accept expired quote
        response = client.post(
            f"/api/v1/quotes/{quote_id}/accept",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            json={}
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()


class TestAutoApprovalLogic:
    """Test auto-approval rules"""

    def test_abs_large_dimensions_requires_review(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that ABS parts with large dimensions require review"""
        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('200.0'),
            'print_time_hours': Decimal('10.0'),
            'material_cost': Decimal('5.00'),
            'labor_cost': Decimal('15.00'),
            'unit_price': Decimal('40.00'),  # Under $50
            'total_price': Decimal('40.00'),
            'dimensions_x': Decimal('210.0'),  # Over 200mm
            'dimensions_y': Decimal('210.0'),  # Over 200mm
            'dimensions_z': Decimal('110.0'),  # Over 100mm
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("large_abs.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "ABS",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"  # Not auto-approved
        assert data["auto_approve_eligible"] is False
        assert "dimensions exceed limits" in data["requires_review_reason"].lower()

    def test_small_abs_part_auto_approved(self, client, authenticated_user, mock_file_storage, mock_bambu_client):
        """Test that small ABS parts are auto-approved"""
        mock_bambu_client.generate_quote.return_value = {
            'success': True,
            'material_grams': Decimal('50.0'),
            'print_time_hours': Decimal('2.5'),
            'material_cost': Decimal('1.40'),
            'labor_cost': Decimal('3.75'),
            'unit_price': Decimal('10.30'),
            'total_price': Decimal('10.30'),
            'dimensions_x': Decimal('100.0'),  # Under 200mm
            'dimensions_y': Decimal('100.0'),  # Under 200mm
            'dimensions_z': Decimal('50.0'),   # Under 100mm
        }

        file_content = b"fake file content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/v1/quotes/upload",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            files={"file": ("small_abs.3mf", file, "application/octet-stream")},
            data={
                "quantity": 1,
                "material_type": "ABS",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "approved"  # Auto-approved
        assert data["auto_approved"] is True
