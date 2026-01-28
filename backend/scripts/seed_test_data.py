"""
Seed test data for E2E tests

Creates a test user if it doesn't exist.
Safe to run multiple times.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password


def seed_test_user():
    """Create test user for E2E tests if it doesn't exist."""
    db = SessionLocal()

    try:
        # Test user credentials
        TEST_EMAIL = "e2e-test@filaops.local"
        TEST_PASSWORD = "TestPass123!"
        TEST_NAME = "E2E Test User"

        # Check if test user already exists
        existing = db.query(User).filter(User.email == TEST_EMAIL).first()

        if existing:
            print(f"ℹ️  Test user already exists: {TEST_EMAIL}")
            return

        # Create test user
        test_user = User(
            first_name="E2E",
            last_name="Test User",
            email=TEST_EMAIL,
            password_hash=hash_password(TEST_PASSWORD),
            status="active",
            account_type="admin",
        )

        db.add(test_user)
        db.commit()
        print(f"✅ Created test user for E2E tests: {TEST_EMAIL}")

    except Exception as e:
        print(f"⚠️  Error creating test user: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_test_user()
