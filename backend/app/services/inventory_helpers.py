"""
Inventory Helper Functions

Utilities for handling material vs. non-material items in the inventory system.

IMPORTANT: This module uses the centralized UOM config. Do not hardcode
material detection logic here - use the functions from uom_config.py
"""

from decimal import Decimal
from app.models.product import Product
from app.core.uom_config import (
    is_material as _is_material,
    get_inventory_value_for_product,
    DEFAULT_MATERIAL_UOM,
)


def is_material(product: Product) -> bool:
    """
    Check if a product is a material (filament, sheet stock, etc.).

    Materials are identified by:
    1. item_type == 'material' (explicit, preferred)
    2. material_type_id is not None (legacy filaments)

    Args:
        product: Product model instance

    Returns:
        True if product is a material, False otherwise
    """
    return _is_material(
        item_type=product.item_type,
        material_type_id=product.material_type_id,
    )


def get_transaction_unit(product: Product) -> str:
    """
    Get the unit to use for inventory transactions.

    Uses the product's configured unit, falling back to defaults.

    Args:
        product: Product model instance

    Returns:
        Unit string (product.unit or "EA" as fallback)
    """
    return product.unit or "EA"


def convert_to_transaction_unit(quantity: float, from_unit: str, product: Product) -> float:
    """
    Convert quantity to the transaction unit for a product.

    For materials: Converts to storage unit using standard conversion factors
    For others: Returns quantity as-is (no conversion)

    Args:
        quantity: Quantity in from_unit
        from_unit: Source unit (KG, LB, EA, etc.)
        product: Product model instance

    Returns:
        Quantity in transaction unit
    """
    if not is_material(product):
        # Non-materials: no conversion needed
        return quantity

    # Materials: Convert to storage unit
    from_unit_upper = (from_unit or "").upper().strip()
    to_unit_upper = (product.unit or "G").upper().strip()

    # If same unit, no conversion
    if from_unit_upper == to_unit_upper:
        return quantity

    # Conversion factors to grams (for mass-based materials)
    conversion_to_grams = {
        "G": 1.0,
        "KG": 1000.0,
        "LB": 453.592,
        "OZ": 28.3495,
    }

    # Conversion factors to milliliters (for volume-based materials like resin)
    conversion_to_ml = {
        "ML": 1.0,
        "L": 1000.0,
        "GAL": 3785.41,
    }

    # Conversion factors to inches (for linear materials)
    conversion_to_inches = {
        "IN": 1.0,
        "FT": 12.0,
        "M": 39.3701,
        "CM": 0.393701,
    }

    # Try mass conversion (most common for filament)
    if from_unit_upper in conversion_to_grams and to_unit_upper in conversion_to_grams:
        from_factor = conversion_to_grams[from_unit_upper]
        to_factor = conversion_to_grams[to_unit_upper]
        return quantity * from_factor / to_factor

    # Try volume conversion (for resin)
    if from_unit_upper in conversion_to_ml and to_unit_upper in conversion_to_ml:
        from_factor = conversion_to_ml[from_unit_upper]
        to_factor = conversion_to_ml[to_unit_upper]
        return quantity * from_factor / to_factor

    # Try linear conversion (for bar stock)
    if from_unit_upper in conversion_to_inches and to_unit_upper in conversion_to_inches:
        from_factor = conversion_to_inches[from_unit_upper]
        to_factor = conversion_to_inches[to_unit_upper]
        return quantity * from_factor / to_factor

    # Unknown unit - log warning and return original
    import logging

    logging.warning(
        f"Unknown unit conversion '{from_unit}' to '{product.unit}' "
        f"for product {product.sku}, returning original quantity"
    )
    return quantity


def get_purchase_factor(product: Product) -> float:
    """
    Get the purchase factor for a product.

    The purchase factor converts from purchase_uom to unit.
    Uses product's configured value, falling back to defaults.

    Args:
        product: Product model instance

    Returns:
        Purchase factor as float
    """
    if product.purchase_factor:
        return float(product.purchase_factor)

    # Fallback for legacy materials without purchase_factor
    if is_material(product):
        return float(DEFAULT_MATERIAL_UOM.purchase_factor)

    return 1.0


def calculate_inventory_value(product: Product, quantity: Decimal) -> Decimal:
    """
    Calculate inventory value for a given quantity.

    Args:
        product: Product model instance
        quantity: Quantity in storage units

    Returns:
        Inventory value in dollars
    """
    return get_inventory_value_for_product(product, quantity)
