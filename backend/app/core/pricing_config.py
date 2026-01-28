"""
FilaOps Pricing Configuration

This module contains all pricing rules, markups, and business logic
for the customer portal quote engine.

Based on business analysis date: 2025-11-24
Approved pricing model: 3.5x-4.5x markup structure

All configuration values are now loaded from Settings (environment variables).
See backend/app/core/settings.py for configuration options.
"""

from typing import Dict, List
from decimal import Decimal

from app.logging_config import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


# ============================================================================
# MATERIAL COSTS (per gram) - Loaded from Settings
# ============================================================================

MATERIAL_COSTS: Dict[str, Decimal] = settings.material_costs


# ============================================================================
# MARKUP MULTIPLIERS (material-specific) - Loaded from Settings
# ============================================================================

MARKUP_MULTIPLIERS: Dict[str, Decimal] = settings.markup_multipliers


# ============================================================================
# MACHINE COSTS - Loaded from Settings
# ============================================================================

MACHINE_HOURLY_RATE: Decimal = Decimal(str(settings.MACHINE_HOURLY_RATE))


# ============================================================================
# PRINT FARM CAPACITY - Loaded from Settings
# ============================================================================

PRINTER_FLEET = settings.printer_fleet_config


# ============================================================================
# QUANTITY DISCOUNTS - Loaded from Settings
# ============================================================================

QUANTITY_DISCOUNTS: List[Dict] = settings.quantity_discounts


# ============================================================================
# FINISH OPTIONS & UPCHARGES - Loaded from Settings
# ============================================================================

FINISH_COSTS: Dict[str, Decimal] = settings.finish_costs


# ============================================================================
# RUSH ORDER MULTIPLIERS - Loaded from Settings
# ============================================================================

RUSH_MULTIPLIERS: Dict[str, Decimal] = settings.rush_multipliers


# ============================================================================
# BUSINESS RULES - Loaded from Settings
# ============================================================================

MINIMUM_ORDER_VALUE: Decimal = Decimal(str(settings.MINIMUM_ORDER_VALUE))
MAX_FILE_SIZE_MB: int = settings.MAX_FILE_SIZE_MB
AUTO_APPROVE_THRESHOLD: Decimal = Decimal(str(settings.AUTO_APPROVE_THRESHOLD))
QUOTE_EXPIRATION_DAYS: int = settings.QUOTE_EXPIRATION_DAYS


# ============================================================================
# AUTO-APPROVE RULES (ABS/ASA RESTRICTIONS) - Loaded from Settings
# ============================================================================

ABS_ASA_SIZE_LIMITS = settings.abs_asa_size_limits


# ============================================================================
# CONTACT & NOTIFICATIONS - Loaded from Settings
# ============================================================================

BUSINESS_EMAIL: str = settings.BUSINESS_EMAIL
BUSINESS_NAME: str = settings.BUSINESS_NAME


# ============================================================================
# DELIVERY ESTIMATION - Loaded from Settings
# ============================================================================

DELIVERY_ESTIMATION = settings.delivery_estimation


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_material_cost(material_type: str) -> Decimal:
    """Get cost per gram for a material type"""
    return MATERIAL_COSTS.get(material_type.upper(), MATERIAL_COSTS["PLA"])


def get_markup_multiplier(material_type: str) -> Decimal:
    """Get markup multiplier for a material type"""
    return MARKUP_MULTIPLIERS.get(material_type.upper(), MARKUP_MULTIPLIERS["PLA"])


def calculate_quantity_discount(quantity: int) -> Decimal:
    """Calculate discount percentage based on quantity"""
    for tier in QUANTITY_DISCOUNTS:
        if quantity >= tier["min_quantity"]:
            return tier["discount"]
    return Decimal("0.0")


def get_finish_cost(finish_type: str) -> Decimal:
    """Get upcharge for finish type"""
    return FINISH_COSTS.get(finish_type.lower(), FINISH_COSTS["standard"])


def get_rush_multiplier(rush_type: str) -> Decimal:
    """Get rush order multiplier"""
    return RUSH_MULTIPLIERS.get(rush_type.lower(), RUSH_MULTIPLIERS["standard"])


def should_auto_approve(total_price: Decimal, material_type: str, dimensions_mm: Dict[str, float]) -> bool:
    """
    Determine if order should be auto-approved

    Rules:
    1. Must be under $50
    2. If ABS/ASA: must not exceed size limits

    Args:
        total_price: Total order price
        material_type: Material type (PLA, ABS, etc.)
        dimensions_mm: Dict with 'x', 'y', 'z' dimensions in mm

    Returns:
        True if order should auto-approve, False if requires manual review
    """
    # Check price threshold
    if total_price >= AUTO_APPROVE_THRESHOLD:
        return False

    # Check ABS/ASA size restrictions
    if material_type.upper() in ["ABS", "ASA"]:
        if (
            dimensions_mm.get("x", 0) > ABS_ASA_SIZE_LIMITS["max_x_mm"]
            or dimensions_mm.get("y", 0) > ABS_ASA_SIZE_LIMITS["max_y_mm"]
            or dimensions_mm.get("z", 0) > ABS_ASA_SIZE_LIMITS["max_z_mm"]
        ):
            return False  # Requires manual review

    return True  # Auto-approve


def estimate_delivery_days(print_time_hours: float, quantity: int, rush_type: str = "standard") -> int:
    """
    Estimate delivery days based on print time and rush status

    Args:
        print_time_hours: Time to print one unit
        quantity: Number of units
        rush_type: Rush order type (standard, fast, rush_48h, rush_24h)

    Returns:
        Estimated delivery days
    """
    import math

    total_hours = print_time_hours * quantity

    # Calculate days based on daily printing capacity
    printing_days = math.ceil(total_hours / DELIVERY_ESTIMATION["printing_hours_per_day"])

    # Add processing buffer
    total_days = printing_days + DELIVERY_ESTIMATION["processing_buffer_days"]

    # Adjust for rush orders
    if rush_type in DELIVERY_ESTIMATION["rush_reduction_days"]:
        reduction = DELIVERY_ESTIMATION["rush_reduction_days"][rush_type]
        total_days = max(1, total_days - reduction)  # Minimum 1 day

    return total_days


# ============================================================================
# PRICING CALCULATION (Master Function)
# ============================================================================


def calculate_quote_price(
    material_grams: float,
    print_time_hours: float,
    material_type: str,
    quantity: int,
    finish: str = "standard",
    rush: str = "standard",
) -> Dict:
    """
    Calculate final quote price with all business rules applied

    Args:
        material_grams: Weight of material needed (grams)
        print_time_hours: Time to print (hours)
        material_type: Type of material (PLA, PETG, ABS, ASA, TPU)
        quantity: Number of units
        finish: Finish type (standard, cleanup, sanded, painted, custom)
        rush: Rush type (standard, fast, rush_48h, rush_24h)

    Returns:
        Dict with pricing breakdown:
        {
            'unit_price': Final price per unit,
            'total_price': Total order price,
            'base_cost': Cost to produce one unit,
            'material_cost': Material cost per unit,
            'machine_cost': Machine time cost per unit,
            'markup_applied': Markup multiplier used,
            'discount_percent': Quantity discount applied (%),
            'finish_upcharge': Finish upcharge per unit,
            'rush_multiplier': Rush multiplier applied,
            'estimated_delivery_days': Estimated delivery,
            'margin': Profit per unit
        }
    """
    # 1. Calculate base costs
    material_cost = Decimal(str(material_grams)) * get_material_cost(material_type)
    machine_cost = Decimal(str(print_time_hours)) * MACHINE_HOURLY_RATE
    base_cost = material_cost + machine_cost

    # 2. Apply material-specific markup
    markup = get_markup_multiplier(material_type)
    base_price = base_cost * markup

    # 3. Apply quantity discount
    discount = calculate_quantity_discount(quantity)
    discounted_price = base_price * (Decimal("1.0") - discount)

    # 4. Add finish upcharge
    finish_cost = get_finish_cost(finish)
    price_with_finish = discounted_price + finish_cost

    # 5. Apply rush multiplier
    rush_multiplier = get_rush_multiplier(rush)
    final_unit_price = price_with_finish * rush_multiplier

    # 6. Calculate total
    total_price = final_unit_price * quantity

    # 7. Apply minimum order value
    if total_price < MINIMUM_ORDER_VALUE:
        total_price = MINIMUM_ORDER_VALUE
        final_unit_price = MINIMUM_ORDER_VALUE / quantity

    # 8. Calculate delivery estimate
    delivery_days = estimate_delivery_days(print_time_hours, quantity, rush)

    # 9. Calculate margin
    margin = final_unit_price - base_cost

    return {
        "unit_price": round(float(final_unit_price), 2),
        "total_price": round(float(total_price), 2),
        "base_cost": round(float(base_cost), 2),
        "material_cost": round(float(material_cost), 2),
        "machine_cost": round(float(machine_cost), 2),
        "markup_applied": float(markup),
        "discount_percent": float(discount * 100),
        "finish_upcharge": float(finish_cost),
        "rush_multiplier": float(rush_multiplier),
        "estimated_delivery_days": delivery_days,
        "margin": round(float(margin), 2),
        "margin_percent": round(float((margin / final_unit_price) * 100), 1) if final_unit_price > 0 else 0,
    }


# ============================================================================
# VALIDATION
# ============================================================================


def validate_quote_parameters(material_type: str, quantity: int, finish: str, rush: str) -> tuple[bool, str]:
    """
    Validate quote parameters

    Returns:
        (is_valid, error_message)
    """
    # Validate material
    if material_type.upper() not in MATERIAL_COSTS:
        return False, f"Invalid material type: {material_type}. Available: {', '.join(MATERIAL_COSTS.keys())}"

    # Validate quantity
    if quantity < 1:
        return False, "Quantity must be at least 1"
    if quantity > 10000:
        return False, "Quantity exceeds maximum (10,000). Please contact us for bulk orders."

    # Validate finish
    if finish.lower() not in FINISH_COSTS:
        return False, f"Invalid finish type: {finish}. Available: {', '.join(FINISH_COSTS.keys())}"

    # Validate rush
    if rush.lower() not in RUSH_MULTIPLIERS:
        return False, f"Invalid rush type: {rush}. Available: {', '.join(RUSH_MULTIPLIERS.keys())}"

    return True, ""


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: 50-gram PLA part, 3-hour print, qty 10
    quote = calculate_quote_price(
        material_grams=50, print_time_hours=3, material_type="PLA", quantity=10, finish="standard", rush="standard"
    )

    logger.info(
        "Example quote calculated",
        extra={
            "unit_price": str(quote["unit_price"]),
            "total_price": str(quote["total_price"]),
            "margin_percent": quote["margin_percent"],
            "delivery_days": quote["estimated_delivery_days"],
        },
    )
