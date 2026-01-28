"""
Shared test fixtures for FilaOps ERP tests

Provides database setup, client creation, and user fixtures.
Uses PostgreSQL test database (filaops_test) by default.
Set TEST_USE_POSTGRES=false to use SQLite in-memory for faster tests.
"""

import os

# Set test environment variables BEFORE any app imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-not-for-production")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import create_access_token, hash_password
from app.core.limiter import limiter

# Disable rate limiting for tests
limiter.enabled = False


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
USE_POSTGRES = os.getenv("TEST_USE_POSTGRES", "true").lower() == "true"

if USE_POSTGRES:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "Admin")
    DB_NAME = os.getenv("TEST_DB_NAME", "filaops_test")
    SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False, pool_pre_ping=True)
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables(engine):
    """Create all tables for testing using SQLAlchemy metadata"""
    # Import all models to ensure they're registered with Base
    # This imports all models via the models __init__.py
    from app.models import (  # noqa: F401
        User,
        RefreshToken,
        Product,
        BOM,
        BOMLine,
        Quote,
        SalesOrder,
        SalesOrderLine,
        ProductionOrder,
        Inventory,
        InventoryTransaction,
        ScrapReason,
        UnitOfMeasure,
        CompanySettings,
        PurchaseOrder,
        PurchaseOrderLine,
        Vendor,
        InventoryLocation,
    )

    # Drop existing tables first to avoid schema conflicts with Alembic migrations
    # This ensures tests use the current model schema, not outdated migration schema
    drop_tables(engine)

    # Create all tables at once - handles foreign keys and self-references properly
    Base.metadata.create_all(bind=engine)


def drop_tables(engine):
    """Drop all tables after testing"""
    if USE_POSTGRES:
        # PostgreSQL requires CASCADE to drop tables with foreign key dependencies
        with engine.connect() as conn:
            # Get all table names from metadata
            table_names = list(Base.metadata.tables.keys())
            if table_names:
                # Drop all tables with CASCADE
                for table_name in table_names:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
                conn.commit()
    else:
        # SQLite handles dependencies properly
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test"""
    create_tables(engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        drop_tables(engine)


@pytest.fixture
def db(db_session):
    """Alias for db_session - provides 'db' fixture name for tests"""
    return db_session


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
def admin_user(db_session):
    """Create an admin user for testing"""
    from app.models.user import User

    user = User(
        email="admin@test.com",
        password_hash=hash_password("AdminPass123!"),
        first_name="Admin",
        last_name="User",
        account_type="admin",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def customer_user(db_session):
    """Create a customer user for testing"""
    from app.models.user import User

    user = User(
        email="customer@test.com",
        password_hash=hash_password("CustomerPass123!"),
        first_name="Customer",
        last_name="User",
        account_type="customer",
        status="active",
        customer_number="CUST-0001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    """Generate an access token for the admin user"""
    return create_access_token(admin_user.id)


@pytest.fixture
def customer_token(customer_user):
    """Generate an access token for the customer user"""
    return create_access_token(customer_user.id)


@pytest.fixture
def admin_headers(admin_token):
    """Return authorization headers for admin user"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def customer_headers(customer_token):
    """Return authorization headers for customer user"""
    return {"Authorization": f"Bearer {customer_token}"}


@pytest.fixture
def sample_product(db_session):
    """Create a sample product for testing"""
    from app.models.product import Product

    product = Product(
        sku="TEST-PROD-001",
        name="Test Product",
        description="A test product for unit testing",
        unit="EA",
        standard_cost=Decimal("10.00"),
        selling_price=Decimal("25.00"),
        active=True,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def sample_material(db_session):
    """Create a sample raw material for BOM testing"""
    from app.models.product import Product

    material = Product(
        sku="MAT-TEST-PLA",
        name="Test PLA Filament",
        description="Test material",
        unit="KG",
        standard_cost=Decimal("20.00"),
        is_raw_material=True,
        active=True,
    )
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)
    return material


@pytest.fixture
def sample_box(db_session):
    """Create a sample packaging material"""
    from app.models.product import Product

    box = Product(
        sku="PKG-BOX-4X4",
        name="4x4x4 Shipping Box",
        description="Small shipping box",
        unit="EA",
        standard_cost=Decimal("0.50"),
        is_raw_material=True,
        active=True,
    )
    db_session.add(box)
    db_session.commit()
    db_session.refresh(box)
    return box


@pytest.fixture
def sample_bom(db_session, sample_product, sample_material, sample_box):
    """Create a sample BOM with lines for testing"""
    from app.models.bom import BOM, BOMLine

    bom = BOM(
        product_id=sample_product.id,
        code=f"BOM-{sample_product.sku}",
        name=f"BOM for {sample_product.name}",
        version=1,
        revision="1.0",
        active=True,
        total_cost=Decimal("10.50"),
    )
    db_session.add(bom)
    db_session.flush()

    # Add material line
    line1 = BOMLine(
        bom_id=bom.id,
        component_id=sample_material.id,
        quantity=Decimal("0.50"),
        sequence=1,
        scrap_factor=Decimal("5.00"),
        notes="Material line",
    )
    db_session.add(line1)

    # Add box line
    line2 = BOMLine(
        bom_id=bom.id,
        component_id=sample_box.id,
        quantity=Decimal("1.00"),
        sequence=2,
        scrap_factor=Decimal("0.00"),
        notes="Packaging line",
    )
    db_session.add(line2)

    db_session.commit()
    db_session.refresh(bom)
    return bom


@pytest.fixture
def sample_quote(db_session, customer_user):
    """Create a sample quote for testing"""
    from app.models.quote import Quote

    quote = Quote(
        user_id=customer_user.id,
        quote_number="Q-2025-TEST-001",
        product_name="Test Custom Print",
        quantity=1,
        material_type="PLA_BASIC",
        color="BLK",
        finish="standard",
        total_price=Decimal("25.00"),
        file_format=".3mf",
        file_size_bytes=1024000,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(quote)
    db_session.commit()
    db_session.refresh(quote)
    return quote


@pytest.fixture
def sample_sales_order(db_session, customer_user, sample_quote):
    """Create a sample sales order for testing"""
    from app.models.sales_order import SalesOrder

    order = SalesOrder(
        user_id=customer_user.id,
        quote_id=sample_quote.id,
        order_number="SO-2025-TEST-001",
        order_type="quote_based",
        source="portal",
        product_name="Test Custom Print",
        quantity=1,
        material_type="PLA_BASIC",
        finish="standard",
        unit_price=Decimal("25.00"),
        total_price=Decimal("25.00"),
        grand_total=Decimal("32.00"),
        status="confirmed",
        payment_status="paid",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order
