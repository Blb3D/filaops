"""
Unit tests for UOM service
"""

from app.models.product import Product
from app.services.uom_service import get_product_consumption_uom


def test_get_product_consumption_uom_with_unit(db_session):
    """Test getting consumption UOM when product has unit set"""
    # Setup: Create product with unit='G'
    product = Product(sku="TEST-MAT-G", name="Test Material (Grams)", unit="G", is_raw_material=True)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    # Test
    product_id: int = int(product.id)  # type: ignore[arg-type]
    uom = get_product_consumption_uom(db_session, product_id)
    assert uom == "G"

    # Cleanup
    db_session.delete(product)
    db_session.commit()


def test_get_product_consumption_uom_no_unit_material(db_session):
    """Test getting consumption UOM for material without unit (defaults to KG)"""
    # Setup: Create material product without unit
    product = Product(sku="TEST-MAT-2", name="Test Material 2", unit=None, is_raw_material=True)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    # Test
    product_id: int = int(product.id)  # type: ignore[arg-type]
    uom = get_product_consumption_uom(db_session, product_id)
    assert uom == "KG"  # Should default to KG for materials

    # Cleanup
    db_session.delete(product)
    db_session.commit()


def test_get_product_consumption_uom_with_kg_unit(db_session):
    """Test getting consumption UOM when product has KG unit"""
    # Setup: Create product with unit='KG'
    product = Product(sku="TEST-MAT-KG", name="Test Material (KG)", unit="KG", is_raw_material=True)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    # Test
    product_id: int = int(product.id)  # type: ignore[arg-type]
    uom = get_product_consumption_uom(db_session, product_id)
    assert uom == "KG"

    # Cleanup
    db_session.delete(product)
    db_session.commit()


def test_get_product_consumption_uom_product_not_found(db_session):
    """Test getting consumption UOM when product doesn't exist"""
    # Test
    uom = get_product_consumption_uom(db_session, 99999)  # Non-existent ID
    assert uom == "KG"  # Should return default


def test_get_product_consumption_uom_non_material(db_session):
    """Test getting consumption UOM for non-material product"""
    # Setup: Create non-material product
    product = Product(sku="TEST-COMP", name="Test Component", unit="EA", is_raw_material=False)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    # Test
    product_id: int = int(product.id)  # type: ignore[arg-type]
    uom = get_product_consumption_uom(db_session, product_id)
    assert uom == "EA"

    # Cleanup
    db_session.delete(product)
    db_session.commit()


def test_get_product_consumption_uom_case_insensitive(db_session):
    """Test that unit codes are normalized to uppercase"""
    # Setup: Create product with lowercase unit
    product = Product(
        sku="TEST-MAT-LOWER",
        name="Test Material Lowercase",
        unit="kg",  # lowercase
        is_raw_material=True,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    # Test
    product_id: int = int(product.id)  # type: ignore[arg-type]
    uom = get_product_consumption_uom(db_session, product_id)
    assert uom == "KG"  # Should be uppercase

    # Cleanup
    db_session.delete(product)
    db_session.commit()
