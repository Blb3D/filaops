"""
Unit tests for authentication utilities

Testing password hashing, JWT token generation, and validation
Following TDD approach - write tests first, then implement
"""
import pytest
from datetime import datetime, timedelta, timezone


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a valid bcrypt hash"""
        from app.core.security import hash_password

        password = "TestPassword123!"
        hashed = hash_password(password)

        # Bcrypt hashes always start with $2b$ and are 60 characters
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60

    def test_hash_password_different_each_time(self):
        """Test that same password generates different hashes (salt)"""
        from app.core.security import hash_password

        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Should be different due to random salt
        assert hash1 != hash2

    def test_verify_password_correct_password(self):
        """Test that verify_password returns True for correct password"""
        from app.core.security import hash_password, verify_password

        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self):
        """Test that verify_password returns False for incorrect password"""
        from app.core.security import hash_password, verify_password

        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive"""
        from app.core.security import hash_password, verify_password

        password = "TestPassword123!"
        wrong_case = "testpassword123!"
        hashed = hash_password(password)

        assert verify_password(wrong_case, hashed) is False


class TestJWTTokens:
    """Test JWT token generation and validation"""

    def test_create_access_token_valid_structure(self):
        """Test that create_access_token generates valid JWT"""
        from app.core.security import create_access_token

        user_id = 123
        token = create_access_token(user_id)

        # JWT tokens have 3 parts separated by dots
        assert isinstance(token, str)
        assert len(token.split('.')) == 3

    def test_create_access_token_contains_user_id(self):
        """Test that access token payload contains user_id"""
        from app.core.security import create_access_token, decode_token

        user_id = 123
        token = create_access_token(user_id)
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("sub") == str(user_id)  # 'sub' is standard JWT claim for subject
        assert payload.get("type") == "access"

    def test_create_access_token_has_expiration(self):
        """Test that access token has expiration time"""
        from app.core.security import create_access_token, decode_token

        user_id = 123
        token = create_access_token(user_id)
        payload = decode_token(token)

        assert payload is not None
        assert "exp" in payload
        assert "iat" in payload  # issued at

    def test_create_access_token_custom_expires_delta(self):
        """Test creating token with custom expiration"""
        from app.core.security import create_access_token, decode_token

        user_id = 123
        expires_delta = timedelta(hours=2)
        token = create_access_token(user_id, expires_delta=expires_delta)
        payload = decode_token(token)

        assert payload is not None
        # Check expiration is approximately 2 hours from now
        exp_timestamp = payload.get("exp")
        expected_exp = datetime.now(timezone.utc) + expires_delta
        actual_exp = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

        # Allow 5 second tolerance
        assert abs((actual_exp - expected_exp).total_seconds()) < 5

    def test_create_refresh_token_valid_structure(self):
        """Test that create_refresh_token generates valid JWT"""
        from app.core.security import create_refresh_token

        user_id = 123
        token = create_refresh_token(user_id)

        assert isinstance(token, str)
        assert len(token.split('.')) == 3

    def test_create_refresh_token_longer_expiration(self):
        """Test that refresh tokens have longer expiration than access tokens"""
        from app.core.security import create_access_token, create_refresh_token, decode_token

        user_id = 123
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)

        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        assert access_payload is not None
        assert refresh_payload is not None

        # Refresh token should expire later than access token
        assert refresh_payload["exp"] > access_payload["exp"]

    def test_create_refresh_token_contains_correct_type(self):
        """Test that refresh token payload has type='refresh'"""
        from app.core.security import create_refresh_token, decode_token

        user_id = 123
        token = create_refresh_token(user_id)
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("type") == "refresh"
        assert payload.get("sub") == str(user_id)

    def test_decode_token_valid_token(self):
        """Test decoding a valid token returns payload"""
        from app.core.security import create_access_token, decode_token

        user_id = 123
        token = create_access_token(user_id)
        payload = decode_token(token)

        assert payload is not None
        assert isinstance(payload, dict)
        assert "sub" in payload
        assert "exp" in payload

    def test_decode_token_invalid_token(self):
        """Test decoding invalid token returns None"""
        from app.core.security import decode_token

        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)

        assert payload is None

    def test_decode_token_expired_token(self):
        """Test decoding expired token returns None"""
        from app.core.security import create_access_token, decode_token

        user_id = 123
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(user_id, expires_delta=expires_delta)

        payload = decode_token(token)
        assert payload is None  # Should return None for expired token

    def test_decode_token_tampered_token(self):
        """Test decoding tampered token returns None"""
        from app.core.security import create_access_token, decode_token

        user_id = 123
        token = create_access_token(user_id)

        # Tamper with the token by corrupting the signature part
        # JWT format: header.payload.signature
        parts = token.split('.')
        assert len(parts) == 3, "Token should have 3 parts"

        # Corrupt the signature by reversing it (guaranteed to be different)
        corrupted_signature = parts[2][::-1]
        tampered_token = f"{parts[0]}.{parts[1]}.{corrupted_signature}"

        payload = decode_token(tampered_token)
        assert payload is None

    def test_get_user_from_token_valid(self):
        """Test extracting user_id from valid token"""
        from app.core.security import create_access_token, get_user_from_token

        user_id = 123
        token = create_access_token(user_id)
        extracted_user_id = get_user_from_token(token)

        assert extracted_user_id == user_id

    def test_get_user_from_token_invalid(self):
        """Test extracting user_id from invalid token returns None"""
        from app.core.security import get_user_from_token

        invalid_token = "invalid.token.here"
        extracted_user_id = get_user_from_token(invalid_token)

        assert extracted_user_id is None

    def test_get_user_from_token_type_validation(self):
        """Test that get_user_from_token validates token type"""
        from app.core.security import create_access_token, create_refresh_token, get_user_from_token

        user_id = 123
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)

        # Access token should work
        assert get_user_from_token(access_token, expected_type="access") == user_id

        # Refresh token with expected_type="access" should fail
        assert get_user_from_token(refresh_token, expected_type="access") is None

        # Refresh token with expected_type="refresh" should work
        assert get_user_from_token(refresh_token, expected_type="refresh") == user_id


class TestTokenHelpers:
    """Test helper functions for token management"""

    def test_hash_refresh_token(self):
        """Test that refresh tokens are hashed for storage"""
        from app.core.security import hash_refresh_token

        token = "some-refresh-token-string"
        hashed = hash_refresh_token(token)

        # Should return a hex string (SHA256 produces 64 hex characters)
        assert isinstance(hashed, str)
        assert len(hashed) == 64
        assert all(c in '0123456789abcdef' for c in hashed)

    def test_hash_refresh_token_consistent(self):
        """Test that same token produces same hash"""
        from app.core.security import hash_refresh_token

        token = "some-refresh-token-string"
        hash1 = hash_refresh_token(token)
        hash2 = hash_refresh_token(token)

        assert hash1 == hash2

    def test_hash_refresh_token_different_for_different_tokens(self):
        """Test that different tokens produce different hashes"""
        from app.core.security import hash_refresh_token

        token1 = "token-one"
        token2 = "token-two"
        hash1 = hash_refresh_token(token1)
        hash2 = hash_refresh_token(token2)

        assert hash1 != hash2
