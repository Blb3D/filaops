"""
Product UOM Service

Provides validation and auto-configuration for product units of measure.
Uses centralized configuration from app.core.uom_config.

IMPORTANT: All UOM constants come from uom_config.py - do not hardcode here.
"""

from typing import Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.item_category import ItemCategory
from app.core.uom_config import (
    get_uom_config,
    is_material,
    validate_material_uom,
    validate_uom_consistency,
    get_material_sku_prefixes,
)


# Category codes that indicate filament (continuous materials)
FILAMENT_CATEGORY_CODES = {
    "FILAMENT",
    "PLA",
    "PETG",
    "ABS",
    "TPU",
    "ASA",
    "NYLON",
    "PLA_BASIC",
    "PLA_MATTE",
    "PLA_SILK",
    "PLA_SILK_MULTI",
    "PETG_BASIC",
    "PETG_HF",
    "PETG_CF",
    "PETG_TRANSLUCENT",
    "ABS_GF",
    "TPU_68D",
    "TPU_95A",
    "MATERIAL",
    "MATERIALS",
}


def is_filament_category(db: Session, category_id: Optional[int]) -> bool:
    """
    Check if a category (or its parent) is a filament category.

    Walks up the category tree to check for filament indicators.
    """
    if not category_id:
        return False

    # Walk up the category tree
    category = db.query(ItemCategory).filter(ItemCategory.id == category_id).first()
    while category:
        if category.code and category.code.upper() in FILAMENT_CATEGORY_CODES:
            return True
        if category.parent_id:
            category = db.query(ItemCategory).filter(ItemCategory.id == category.parent_id).first()
        else:
            break

    return False


def is_filament_sku(sku: Optional[str]) -> bool:
    """Check if SKU indicates a filament/material product."""
    if not sku:
        return False
    return sku.upper().startswith(get_material_sku_prefixes())


def is_hardware_sku(sku: Optional[str]) -> bool:
    """Check if SKU indicates a hardware product."""
    if not sku:
        return False
    return sku.upper().startswith(("HW-",))


def get_recommended_uoms(
    db: Session,
    sku: Optional[str] = None,
    category_id: Optional[int] = None,
    item_type: Optional[str] = None,
) -> Tuple[str, str, bool, Decimal]:
    """
    Get recommended UOM settings based on SKU, category, and item_type.

    Returns:
        Tuple of (purchase_uom, unit, is_raw_material, purchase_factor)

    Detection priority:
    1. item_type == 'material' (explicit)
    2. Category is filament category
    3. SKU starts with material prefix
    """
    # Use centralized config
    uom_config = get_uom_config(
        item_type=item_type,
        category_is_filament=is_filament_category(db, category_id),
        sku=sku,
    )

    return (
        uom_config.purchase_uom,
        uom_config.unit,
        uom_config.is_raw_material,
        uom_config.purchase_factor,
    )


def validate_product_uoms(
    db: Session,
    product: Product,
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a product's UOMs are correctly configured.

    For materials: Validates consistency (all fields present, factor positive)
    For others: Basic validation only

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Determine if this should be a material
    is_mat = is_material(
        item_type=product.item_type,
        material_type_id=product.material_type_id,
    )

    if not is_mat:
        # Also check by SKU and category
        if is_filament_sku(product.sku) or is_filament_category(db, product.category_id):
            is_mat = True

    if is_mat:
        # Validate material UOM configuration (consistency check)
        errors = validate_material_uom(
            unit=product.unit,
            purchase_uom=product.purchase_uom,
            purchase_factor=product.purchase_factor,
        )

        # Additional validation: is_raw_material should be True
        if not product.is_raw_material:
            errors.append("Material products should have is_raw_material=True")

        if errors:
            return (False, "; ".join(errors))
    else:
        # Non-material: basic consistency check
        errors = validate_uom_consistency(
            unit=product.unit,
            purchase_uom=product.purchase_uom,
            purchase_factor=product.purchase_factor,
        )

        if errors:
            return (False, "; ".join(errors))

    return (True, None)


def auto_configure_product_uoms(
    db: Session,
    product: Product,
    force: bool = False,
) -> bool:
    """
    Auto-configure a product's UOMs based on detection logic.

    Uses DEFAULT_MATERIAL_UOM (filament profile: G/KG/1000) for materials.
    Users can override after creation for CNC/laser materials.

    Args:
        db: Database session
        product: Product to configure
        force: If True, overwrite existing values. If False, only set if not already set.

    Returns:
        True if changes were made
    """
    purchase_uom, unit, is_raw_material, purchase_factor = get_recommended_uoms(
        db,
        sku=product.sku,
        category_id=product.category_id,
        item_type=product.item_type,
    )

    changed = False

    # Update purchase_uom
    if force or not product.purchase_uom:
        if product.purchase_uom != purchase_uom:
            product.purchase_uom = purchase_uom
            changed = True

    # Update unit
    if force or not product.unit or product.unit == "EA":
        if product.unit != unit:
            product.unit = unit
            changed = True

    # Update purchase_factor
    if force or not product.purchase_factor:
        if product.purchase_factor != purchase_factor:
            product.purchase_factor = purchase_factor
            changed = True

    # Update is_raw_material
    if force or not product.is_raw_material:
        if product.is_raw_material != is_raw_material and is_raw_material:
            product.is_raw_material = is_raw_material
            changed = True

    return changed


def get_cost_display_info(product: Product) -> dict:
    """
    Get display information for product cost.

    Returns dict with:
        - cost: The effective cost value
        - cost_unit: What the cost is per (e.g., 'KG', 'EA')
        - storage_unit: What inventory is tracked in
        - needs_conversion: Whether cost conversion is needed
    """
    purchase_uom = (product.purchase_uom or product.unit or "EA").upper()
    storage_unit = (product.unit or "EA").upper()
    cost = product.standard_cost or product.average_cost or product.last_cost

    return {
        "cost": float(cost) if cost else None,
        "cost_unit": purchase_uom,
        "storage_unit": storage_unit,
        "needs_conversion": purchase_uom != storage_unit,
        "cost_display": f"${float(cost):.2f}/{purchase_uom}" if cost else None,
    }
