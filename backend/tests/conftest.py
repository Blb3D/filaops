"""
Pytest configuration and fixtures for the test suite.
"""
import pytest
import sys
from pathlib import Path

# Add the backend directory to the path so imports work correctly
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture(scope="session", autouse=True)
def seed_test_data():
    """Seed default records required by tests.

    Seeds:
    - InventoryLocation id=1 (tests create Inventory with location_id=1)
    - User id=1 (tests create Quotes with user_id=1)
    - WorkCenter id=1 (tests create ProductionOrderOperations with work_center_id)
    """
    from app.db.session import SessionLocal
    from app.models.inventory import InventoryLocation
    from app.models.user import User
    from app.models.work_center import WorkCenter

    db = SessionLocal()
    try:
        # Seed default inventory location
        if not db.query(InventoryLocation).filter(InventoryLocation.id == 1).first():
            db.add(InventoryLocation(
                id=1, name="Default Warehouse", code="DEFAULT",
                type="warehouse", active=True,
            ))

        # Seed default test user
        if not db.query(User).filter(User.id == 1).first():
            db.add(User(
                id=1, email="test@filaops.dev",
                password_hash="not-a-real-hash",
                first_name="Test", last_name="User",
            ))

        # Seed default work center
        if not db.query(WorkCenter).filter(WorkCenter.id == 1).first():
            db.add(WorkCenter(
                id=1, code="TEST-WC", name="Test Work Center",
            ))

        db.commit()
        yield
    finally:
        db.close()
