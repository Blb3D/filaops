"""
Integration tests for authentication endpoints

Tests the full API flow for user registration, login, token refresh, and profile retrieval
Following TDD approach - write tests first, then implement
"""
import pytest
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
    # Only create User and RefreshToken tables for auth tests
    from app.models.user import User, RefreshToken

    User.__table__.create(bind=engine, checkfirst=True)
    RefreshToken.__table__.create(bind=engine, checkfirst=True)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
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


class TestUserRegistration:
    """Test user registration endpoint: POST /api/v1/auth/register"""

    def test_register_new_user_success(self, client):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert "id" in data
        assert "password" not in data  # Password should not be returned
        assert "password_hash" not in data  # Hash should not be returned

    def test_register_returns_access_token(self, client):
        """Test that registration returns access token for immediate login"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email_fails(self, client):
        """Test that registering with existing email fails"""
        # Register first user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123!",
                "first_name": "First",
                "last_name": "User",
            }
        )

        # Try to register with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "DifferentPass456!",
                "first_name": "Second",
                "last_name": "User",
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email_fails(self, client):
        """Test that invalid email format is rejected"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        )

        assert response.status_code == 422  # Validation error

    def test_register_weak_password_fails(self, client):
        """Test that weak passwords are rejected"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "weak",  # Too short, no numbers, no special chars
                "first_name": "John",
                "last_name": "Doe",
            }
        )

        assert response.status_code == 422  # Validation error

    def test_register_missing_required_fields(self, client):
        """Test that missing required fields are rejected"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                # Missing password
            }
        )

        assert response.status_code == 422

    def test_register_optional_fields(self, client):
        """Test registration with optional fields"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp",
                "phone": "555-1234",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["company_name"] == "Acme Corp"
        assert data["phone"] == "555-1234"


class TestUserLogin:
    """Test user login endpoint: POST /api/v1/auth/login"""

    def test_login_with_valid_credentials(self, client):
        """Test successful login with correct credentials"""
        # Register a user first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        )

        # Login with correct credentials
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "user@example.com",  # OAuth2 uses 'username' field
                "password": "SecurePass123!",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_wrong_password(self, client):
        """Test that login fails with incorrect password"""
        # Register a user first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        )

        # Try to login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "user@example.com",
                "password": "WrongPassword456!",
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_with_nonexistent_email(self, client):
        """Test that login fails with non-existent email"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword123!",
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_updates_last_login_timestamp(self, client, db_session):
        """Test that successful login updates last_login_at timestamp"""
        from app.models.user import User

        # Register a user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        )

        # Check last_login_at before login
        user_before = db_session.query(User).filter(User.email == "user@example.com").first()
        last_login_before = user_before.last_login_at

        # Login
        client.post(
            "/api/v1/auth/login",
            data={
                "username": "user@example.com",
                "password": "SecurePass123!",
            }
        )

        # Check last_login_at after login
        db_session.refresh(user_before)
        assert user_before.last_login_at is not None
        if last_login_before is not None:
            assert user_before.last_login_at > last_login_before


class TestTokenRefresh:
    """Test token refresh endpoint: POST /api/v1/auth/refresh"""

    def test_refresh_token_with_valid_token(self, client):
        """Test refreshing access token with valid refresh token"""
        # Register and get tokens
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        )
        refresh_token = response.json()["refresh_token"]

        # Refresh the token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data  # Should get a new refresh token too
        assert data["token_type"] == "bearer"

    def test_refresh_token_with_invalid_token(self, client):
        """Test that invalid refresh token is rejected"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_refresh_token_with_access_token_fails(self, client):
        """Test that using access token instead of refresh token fails"""
        # Register and get tokens
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        )
        access_token = response.json()["access_token"]

        # Try to refresh with access token (should fail)
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token}
        )

        assert response.status_code == 401


class TestGetCurrentUser:
    """Test get current user endpoint: GET /api/v1/auth/me"""

    def test_get_current_user_with_valid_token(self, client):
        """Test getting current user profile with valid access token"""
        # Register a user
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        )
        access_token = response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert "password" not in data
        assert "password_hash" not in data

    def test_get_current_user_without_token(self, client):
        """Test that accessing /me without token returns 401"""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_get_current_user_with_invalid_token(self, client):
        """Test that invalid token returns 401"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401

    def test_get_current_user_with_refresh_token_fails(self, client):
        """Test that refresh token cannot be used for /me endpoint"""
        # Register and get tokens
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
            }
        )
        refresh_token = response.json()["refresh_token"]

        # Try to access /me with refresh token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )

        assert response.status_code == 401
