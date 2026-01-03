"""
Product UOM Service

Provides validation and auto-configuration for product units of measure
based on category to prevent cost calculation errors.

RULES:
- Filament (MAT-*, FIL-*): purchase_uom=KG, unit=G, is_raw_material=True
- Hardware (HW-*): purchase_uom=EA, unit=EA
- Packaging: Flexible, but cost must match units
- Everything else: purchase_uom should match unit unless explicitly different
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.item_category import ItemCategory


# Category codes that indicate filament (continuous materials)
FILAMENT_CATEGORY_CODES = {
    'FILAMENT', 'PLA', 'PETG', 'ABS', 'TPU', 'ASA', 'NYLON',
    'PLA_BASIC', 'PLA_MATTE', 'PLA_SILK', 'PLA_SILK_MULTI',
    'PETG_BASIC', 'PETG_HF', 'PETG_CF', 'PETG_TRANSLUCENT',
    'ABS_GF', 'TPU_68D', 'TPU_95A'
}

# SKU prefixes that indicate filament
FILAMENT_SKU_PREFIXES = ('MAT-', 'FIL-')

# Hardware prefixes
HARDWARE_SKU_PREFIXES = ('HW-',)

# Packaging prefixes
PACKAGING_SKU_PREFIXES = ('PKG-', 'BOX-', 'BAG-')


def is_filament_category(db: Session, category_id: Optional[int]) -> bool:
    """
    Check if a category (or its parent) is a filament category.
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


def is_filament_sku(sku: str) -> bool:
    """Check if SKU indicates a filament product."""
    if not sku:
        return False
    return sku.upper().startswith(FILAMENT_SKU_PREFIXES)


def is_hardware_sku(sku: str) -> bool:
    """Check if SKU indicates a hardware product."""
    if not sku:
        return False
    return sku.upper().startswith(HARDWARE_SKU_PREFIXES)


def get_recommended_uoms(
    db: Session,
    sku: Optional[str] = None,
    category_id: Optional[int] = None,
) -> Tuple[str, str, bool]:
    """
    Get recommended purchase_uom, unit, and is_raw_material based on SKU and category.
    
    Returns:
        Tuple of (purchase_uom, unit, is_raw_material)
    """
    # Check filament by SKU or category
    if is_filament_sku(sku) or is_filament_category(db, category_id):
        return ('KG', 'G', True)
    
    # Check hardware by SKU
    if is_hardware_sku(sku):
        return ('EA', 'EA', False)
    
    # Default
    return ('EA', 'EA', False)


def validate_product_uoms(
    db: Session,
    product: Product,
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a product's UOMs are correctly configured.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    sku = product.sku or ''
    purchase_uom = (product.purchase_uom or 'EA').upper()
    storage_unit = (product.unit or 'EA').upper()
    
    # Filament validation
    if is_filament_sku(sku) or is_filament_category(db, product.category_id):
        if purchase_uom not in ('KG', 'LB'):
            return (False, f"Filament products should have purchase_uom='KG' (got '{purchase_uom}')")
        if storage_unit not in ('G', 'OZ'):
            return (False, f"Filament products should have unit='G' for storage (got '{storage_unit}')")
        if not product.is_raw_material:
            return (False, "Filament products should have is_raw_material=True")
    
    # Hardware validation
    if is_hardware_sku(sku):
        if purchase_uom != 'EA' or storage_unit != 'EA':
            return (False, f"Hardware products should use 'EA' for both purchase and storage units")
    
    # Cost sanity check for filaments
    if purchase_uom == 'KG' and storage_unit == 'G':
        cost = product.standard_cost or product.average_cost or product.last_cost
        if cost is not None:
            cost_float = float(cost)
            # Filament typically costs $15-50/KG
            if cost_float < 1:
                return (False, f"Cost {cost_float} looks like $/G but should be $/KG for filament")
            if cost_float > 500:
                return (False, f"Cost {cost_float}/KG seems too high - verify this is correct")
    
    return (True, None)


def auto_configure_product_uoms(
    db: Session,
    product: Product,
    force: bool = False,
) -> bool:
    """
    Auto-configure a product's UOMs based on SKU and category.
    
    Args:
        db: Database session
        product: Product to configure
        force: If True, overwrite existing values. If False, only set if not already set.
    
    Returns:
        True if changes were made
    """
    recommended_purchase, recommended_storage, recommended_raw = get_recommended_uoms(
        db, product.sku, product.category_id
    )
    
    changed = False
    
    if force or not product.purchase_uom:
        if product.purchase_uom != recommended_purchase:
            product.purchase_uom = recommended_purchase
            changed = True
    
    if force or not product.unit or product.unit == 'EA':
        if product.unit != recommended_storage:
            product.unit = recommended_storage
            changed = True
    
    if force or not product.is_raw_material:
        if product.is_raw_material != recommended_raw and recommended_raw:
            product.is_raw_material = recommended_raw
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
    purchase_uom = (product.purchase_uom or product.unit or 'EA').upper()
    storage_unit = (product.unit or 'EA').upper()
    cost = product.standard_cost or product.average_cost or product.last_cost
    
    return {
        'cost': float(cost) if cost else None,
        'cost_unit': purchase_uom,
        'storage_unit': storage_unit,
        'needs_conversion': purchase_uom != storage_unit,
        'cost_display': f"${float(cost):.2f}/{purchase_uom}" if cost else None,
    }
