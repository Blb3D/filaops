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
def seed_default_location():
    """Seed default inventory location required by all inventory-related tests.

    Tests create Inventory records with location_id=1, so this location
    must exist before any test runs.
    """
    from app.db.session import SessionLocal
    from app.models.inventory import InventoryLocation

    db = SessionLocal()
    try:
        existing = db.query(InventoryLocation).filter(InventoryLocation.id == 1).first()
        if not existing:
            location = InventoryLocation(
                id=1,
                name="Default Warehouse",
                code="DEFAULT",
                type="warehouse",
                active=True,
            )
            db.add(location)
            db.commit()
        yield
    finally:
        db.close()
