"""
UOM Configuration - Single Source of Truth

This module defines ALL UOM-related constants and logic for materials.
Every other file that needs UOM information MUST import from here.

DO NOT duplicate these values elsewhere. If you need to change material UOM
behavior, change it HERE and it will propagate everywhere.

DEFAULT RULES FOR MATERIALS (Filament):
- Storage unit: G (grams) - for precision tracking of consumption
- Purchase unit: KG (kilograms) - how vendors sell filament
- Purchase factor: 1000 - conversion from KG to G (1 KG = 1000 G)
- Cost reference: KG - costs (standard_cost, last_cost) are stored as $/KG
- is_raw_material: True - materials are consumed in production

NOTE: These are DEFAULTS for filament. CNC/laser users may use different
UOM configurations (e.g., sheets as EA/EA/1, bar stock as IN/FT/12).
Validation checks consistency, not specific values.

COST CALCULATION EXAMPLE:
- Filament purchased at $25/KG
- Inventory shows 500 G on hand
- Inventory value = 500 G × ($25/KG ÷ 1000) = 500 × $0.025 = $12.50

ROLL SIZE CLARIFICATION:
- purchase_factor is the UNIT CONVERSION, not package size
- A 500g roll is simply 0.5 KG on the PO line
- purchase_factor stays at 1000 regardless of roll size
"""

from decimal import Decimal
from typing import NamedTuple, Optional, List


class UOMConfig(NamedTuple):
    """Configuration for a product's unit of measure settings."""

    unit: str  # Storage/consumption unit (G for filament)
    purchase_uom: str  # How vendors sell it (KG for filament)
    purchase_factor: Decimal  # Conversion: purchase_uom -> unit (1000 for KG->G)
    is_raw_material: bool  # Whether this is consumed in production
    cost_reference_unit: str  # What unit costs are stored per (KG for filament)


# =============================================================================
# MATERIAL UOM PROFILES
# =============================================================================
# These are named profiles for common material types.
# DEFAULT_MATERIAL_UOM is used when creating new materials.
# Users can override these values for CNC/laser/other applications.

# Filament profile - default for 3D printing (most FilaOps users)
FILAMENT_UOM = UOMConfig(
    unit="G",  # Store and consume in grams
    purchase_uom="KG",  # Buy in kilograms
    purchase_factor=Decimal("1000"),  # 1 KG = 1000 G
    is_raw_material=True,  # Consumed in production
    cost_reference_unit="KG",  # Costs are $/KG
)

# Sheet stock profile - for CNC/laser (placeholder for future)
SHEET_UOM = UOMConfig(
    unit="EA",  # Store in each (per sheet)
    purchase_uom="EA",  # Buy in each
    purchase_factor=Decimal("1"),  # No conversion
    is_raw_material=True,  # Consumed in production
    cost_reference_unit="EA",  # Costs are $/EA
)

# Linear stock profile - for CNC (placeholder for future)
LINEAR_UOM = UOMConfig(
    unit="IN",  # Store in inches
    purchase_uom="FT",  # Buy in feet
    purchase_factor=Decimal("12"),  # 1 FT = 12 IN
    is_raw_material=True,  # Consumed in production
    cost_reference_unit="FT",  # Costs are $/FT
)

# Resin profile - for SLA printing (placeholder for future)
RESIN_UOM = UOMConfig(
    unit="ML",  # Store in milliliters
    purchase_uom="L",  # Buy in liters
    purchase_factor=Decimal("1000"),  # 1 L = 1000 ML
    is_raw_material=True,  # Consumed in production
    cost_reference_unit="L",  # Costs are $/L
)

# Default for item_type='material' - filament for 3D printing
# Users can override when creating materials for CNC/laser/etc.
DEFAULT_MATERIAL_UOM = FILAMENT_UOM

# Default for non-material items
DEFAULT_UOM = UOMConfig(
    unit="EA",  # Store in each
    purchase_uom="EA",  # Buy in each
    purchase_factor=Decimal("1"),  # No conversion
    is_raw_material=False,  # Not a raw material
    cost_reference_unit="EA",  # Costs are $/EA
)

# Future: Material profile selector options
# This will be used by a dropdown in the UI to pre-fill UOM values
MATERIAL_PROFILES = {
    "filament": FILAMENT_UOM,
    "sheet": SHEET_UOM,
    "linear": LINEAR_UOM,
    "resin": RESIN_UOM,
    # "custom" would use user-entered values
}


# =============================================================================
# MATERIAL DETECTION FUNCTIONS
# =============================================================================


def is_material_item_type(item_type: Optional[str]) -> bool:
    """
    Check if item_type indicates a material product.

    Handles both enum values and plain strings.

    Args:
        item_type: The item_type value (string or enum)

    Returns:
        True if item_type is 'material'
    """
    if not item_type:
        return False
    # Handle both enum and string values
    item_type_str = item_type.value if hasattr(item_type, "value") else str(item_type)
    return item_type_str.lower() == "material"


def is_material(
    item_type: Optional[str] = None,
    material_type_id: Optional[int] = None,
) -> bool:
    """
    Determine if a product is a material (filament, sheet stock, etc.).

    Detection priority:
    1. item_type == 'material' (explicit, preferred)
    2. material_type_id is not None (legacy filament detection)

    Args:
        item_type: The product's item_type field
        material_type_id: The product's material_type_id field

    Returns:
        True if the product is a material
    """
    # Priority 1: Explicit item_type='material'
    if is_material_item_type(item_type):
        return True

    # Priority 2: Legacy detection via material_type_id
    if material_type_id is not None:
        return True

    return False


def get_uom_config(
    item_type: Optional[str] = None,
    material_type_id: Optional[int] = None,
    category_is_filament: bool = False,
    sku: Optional[str] = None,
) -> UOMConfig:
    """
    Get the UOM configuration for a product.

    This is the SINGLE FUNCTION that determines UOM settings.
    All UOM decisions should flow through this function.

    Detection priority (most specific to least):
    1. item_type == 'material' (explicit)
    2. item_type == 'supply' AND material_type_id IS NOT NULL (legacy)
    3. category_is_filament == True (category-based)
    4. SKU starts with 'MAT-' or 'FIL-' (SKU-based fallback)

    Args:
        item_type: Product's item_type field
        material_type_id: Product's material_type_id field
        category_is_filament: Whether product's category is a filament category
        sku: Product's SKU (for fallback detection)

    Returns:
        UOMConfig with appropriate settings (DEFAULT_MATERIAL_UOM for materials)
    """
    # Normalize item_type to lowercase string
    item_type_str = None
    if item_type:
        item_type_str = item_type.value if hasattr(item_type, "value") else str(item_type)
        item_type_str = item_type_str.lower()

    # Priority 1: Explicit item_type='material'
    if item_type_str == "material":
        return DEFAULT_MATERIAL_UOM

    # Priority 2: Legacy - supply with material_type_id
    if item_type_str == "supply" and material_type_id is not None:
        return DEFAULT_MATERIAL_UOM

    # Priority 3: Category-based detection
    if category_is_filament:
        return DEFAULT_MATERIAL_UOM

    # Priority 4: SKU prefix fallback
    if sku:
        sku_upper = sku.upper()
        if sku_upper.startswith(("MAT-", "FIL-")):
            return DEFAULT_MATERIAL_UOM

    return DEFAULT_UOM


def get_uom_config_for_product(product) -> UOMConfig:
    """
    Convenience function to get UOM config directly from a Product model.

    Args:
        product: A Product model instance

    Returns:
        UOMConfig with appropriate settings
    """
    return get_uom_config(
        item_type=getattr(product, "item_type", None),
        material_type_id=getattr(product, "material_type_id", None),
        sku=getattr(product, "sku", None),
    )


# =============================================================================
# COST CALCULATION HELPERS
# =============================================================================


def get_cost_per_storage_unit(
    cost: Decimal,
    purchase_factor: Decimal,
) -> Decimal:
    """
    Convert cost from purchase_uom to storage unit for inventory valuation.

    Example: $25/KG with factor 1000 -> $0.025/G

    Args:
        cost: Cost per purchase_uom (e.g., $/KG)
        purchase_factor: Conversion factor (e.g., 1000 for KG->G)

    Returns:
        Cost per storage unit (e.g., $/G)
    """
    if not cost or not purchase_factor:
        return Decimal("0")
    return cost / purchase_factor


def get_inventory_value(
    quantity_in_storage_unit: Decimal,
    cost_per_purchase_uom: Decimal,
    purchase_factor: Decimal,
) -> Decimal:
    """
    Calculate inventory value given quantity and cost.

    Example: 500 G x ($25/KG / 1000) = $12.50

    Args:
        quantity_in_storage_unit: Quantity in storage units (e.g., grams)
        cost_per_purchase_uom: Cost per purchase UOM (e.g., $/KG)
        purchase_factor: Conversion factor (e.g., 1000 for KG->G)

    Returns:
        Inventory value in dollars
    """
    cost_per_unit = get_cost_per_storage_unit(cost_per_purchase_uom, purchase_factor)
    return quantity_in_storage_unit * cost_per_unit


def get_inventory_value_for_product(
    product,
    quantity_in_storage_unit: Decimal,
) -> Decimal:
    """
    Calculate inventory value for a product.

    Uses product's cost fields (standard_cost, average_cost, last_cost) in priority order.

    Args:
        product: Product model instance
        quantity_in_storage_unit: Quantity in storage units

    Returns:
        Inventory value in dollars
    """
    cost = (
        getattr(product, "standard_cost", None)
        or getattr(product, "average_cost", None)
        or getattr(product, "last_cost", None)
        or Decimal("0")
    )
    purchase_factor = getattr(product, "purchase_factor", None) or Decimal("1")

    return get_inventory_value(quantity_in_storage_unit, cost, purchase_factor)


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_material_uom(
    unit: Optional[str],
    purchase_uom: Optional[str],
    purchase_factor: Optional[Decimal],
) -> List[str]:
    """
    Validate that a material's UOM configuration is INTERNALLY CONSISTENT.

    Does NOT require specific values (G/KG/1000) - allows CNC/laser materials
    with different UOM configurations (e.g., EA/EA/1 for sheets).

    Validates:
    - All three fields are present
    - purchase_factor is positive
    - If unit == purchase_uom, factor should be 1

    Args:
        unit: The product's storage unit
        purchase_uom: The product's purchase UOM
        purchase_factor: The product's purchase factor

    Returns:
        List of error messages (empty list = valid)
    """
    errors = []

    # Must have all three fields
    if not unit:
        errors.append("Material must have a storage unit (e.g., G, EA, IN)")

    if not purchase_uom:
        errors.append("Material must have a purchase UOM (e.g., KG, EA, FT)")

    if not purchase_factor or purchase_factor <= 0:
        errors.append("Material must have a positive purchase factor")

    # If same unit, factor should be 1
    if unit and purchase_uom and purchase_factor:
        if unit.upper() == purchase_uom.upper() and purchase_factor != Decimal("1"):
            errors.append(
                f"When unit and purchase_uom are both '{unit}', " f"purchase_factor should be 1, not {purchase_factor}"
            )

    return errors


def validate_uom_consistency(
    unit: Optional[str],
    purchase_uom: Optional[str],
    purchase_factor: Optional[Decimal],
) -> List[str]:
    """
    Validate UOM configuration for any product (not just materials).

    Less strict than validate_material_uom - allows missing values
    for non-material products.

    Args:
        unit: The product's storage unit
        purchase_uom: The product's purchase UOM
        purchase_factor: The product's purchase factor

    Returns:
        List of error messages (empty list = valid)
    """
    errors = []

    # If purchase_factor is set, it should be positive
    if purchase_factor is not None and purchase_factor <= 0:
        errors.append("purchase_factor must be positive")

    # If unit and purchase_uom are the same, factor should be 1 (if set)
    if unit and purchase_uom and purchase_factor:
        if unit.upper() == purchase_uom.upper() and purchase_factor != Decimal("1"):
            errors.append(f"When unit and purchase_uom are both '{unit}', " f"purchase_factor should be 1")

    return errors


def get_material_sku_prefixes() -> tuple:
    """Return valid SKU prefixes for materials."""
    return ("MAT-", "FIL-")


def get_default_material_sku_prefix() -> str:
    """Return the default SKU prefix for new materials."""
    return "MAT"
