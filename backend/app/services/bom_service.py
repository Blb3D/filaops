"""
BOM Auto-Creation Service

Handles automatic creation of products and BOMs from accepted quotes.
Creates three-line BOMs:
1. Material line (filament) - looked up via Product + Inventory (unified item master)
2. Packaging line (shipping box)
3. Machine time line (production cost @ $1.50/hr fully-burdened)
"""
import re
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from decimal import Decimal

from app.models import Product, Quote, BOM, BOMLine
from app.services.material_service import (
    get_material_product_for_bom,
    get_material_product,
    create_material_product,
    MaterialColorNotAvailableError,
    MaterialNotFoundError,
    ColorNotFoundError,
)

# Machine time costing constants
# These can be moved to system_settings table later for runtime configuration
MACHINE_TIME_SKU = "MFG-MACHINE-TIME"  # Manufacturing overhead cost
MACHINE_HOURLY_RATE = Decimal("1.50")  # $1.50/hr fully-burdened rate (depreciation + electricity + maintenance)

# Legacy SKU for migration
LEGACY_MACHINE_TIME_SKU = "SVC-MACHINE-TIME"


def get_or_create_machine_time_product(db: Session) -> Product:
    """
    Get or create the machine time manufacturing cost product.

    This is a manufacturing overhead product used to track production/machine costs on BOMs.
    Unit is HR (hours), cost is the fully-burdened hourly rate.
    NOT physical inventory - just a cost allocation for job costing.

    Args:
        db: Database session

    Returns:
        Product object for machine time
    """
    # Try to find existing machine time product (check new SKU first, then legacy)
    machine_time = db.query(Product).filter(Product.sku == MACHINE_TIME_SKU).first()

    if not machine_time:
        # Check for legacy SKU and migrate it
        machine_time = db.query(Product).filter(Product.sku == LEGACY_MACHINE_TIME_SKU).first()
        if machine_time:
            # Migrate: update SKU and category
            machine_time.sku = MACHINE_TIME_SKU
            machine_time.category = "Manufacturing"
            machine_time.type = "overhead"
            machine_time.name = "Machine Time - 3D Printer (Mfg Overhead)"
            db.commit()

    if machine_time:
        # Update cost if rate changed (in case constant was updated)
        if machine_time.cost != MACHINE_HOURLY_RATE:
            machine_time.cost = MACHINE_HOURLY_RATE
            db.commit()
        return machine_time

    # Create new machine time manufacturing cost product
    machine_time = Product(
        sku=MACHINE_TIME_SKU,
        name="Machine Time - 3D Printer (Mfg Overhead)",
        description="Manufacturing overhead: fully-burdened machine time cost including depreciation, "
                    f"electricity, and maintenance. Rate: ${MACHINE_HOURLY_RATE}/hr. "
                    "Not physical inventory - cost allocation only.",
        category="Manufacturing",
        type="overhead",
        unit="HR",
        cost=MACHINE_HOURLY_RATE,
        is_raw_material=False,
        has_bom=False,
        track_lots=False,
        track_serials=False,
        is_public=False,
        sales_channel="internal",
        active=True,
    )

    db.add(machine_time)
    db.commit()
    db.refresh(machine_time)

    return machine_time


def parse_box_dimensions(box_name: str) -> Optional[Tuple[float, float, float]]:
    """
    Parse box dimensions from product name.

    Expected formats:
    - "4x4x4in", "5x5x5in", "8x8x16in" (with "in" suffix)
    - "9x6x4 Black Shipping Box", "12x9x4 Black Shipping Boxes" (without "in" suffix)

    Args:
        box_name: Product name containing dimensions

    Returns:
        Tuple of (length, width, height) in inches, or None if not parseable
    """
    # Match patterns like "4x4x4in", "8x8x16in"
    pattern_with_in = r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*in'
    match = re.search(pattern_with_in, box_name, re.IGNORECASE)

    if match:
        length, width, height = float(match.group(1)), float(match.group(2)), float(match.group(3))
        return (length, width, height)

    # Match patterns like "9x6x4 Black", "12x9x4" (dimensions at start of name)
    pattern_no_in = r'^(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)'
    match = re.search(pattern_no_in, box_name)

    if match:
        length, width, height = float(match.group(1)), float(match.group(2)), float(match.group(3))
        return (length, width, height)

    return None


def determine_best_box(quote: Quote, db: Session) -> Optional[Product]:
    """
    Determine the best shipping box based on part dimensions and quantity.

    Uses 3D bin packing logic:
    1. Convert part dimensions from mm to inches
    2. Calculate total volume needed (with packing efficiency)
    3. Find smallest box where:
       - Volume is sufficient
       - Largest part dimension fits

    Args:
        quote: Quote object with dimensions and quantity
        db: Database session

    Returns:
        Product object for best box, or None if no suitable box found
    """
    # Convert part dimensions from mm to inches
    part_l_in = float(quote.dimensions_x) / 25.4
    part_w_in = float(quote.dimensions_y) / 25.4
    part_h_in = float(quote.dimensions_z) / 25.4

    # Calculate volume needed
    part_volume = part_l_in * part_w_in * part_h_in

    # Packing efficiency: 75% for single item, 65% for multiple (accounts for padding/air)
    packing_efficiency = 0.75 if quote.quantity == 1 else 0.65
    total_volume_needed = (part_volume * quote.quantity) / packing_efficiency

    # Largest part dimension (must fit in box)
    max_part_dimension = max(part_l_in, part_w_in, part_h_in)

    # Get all box products from database
    # Search for boxes by:
    # 1. Products with "box" in the name
    # 2. Products in packaging/shipping categories
    box_products = db.query(Product).filter(
        and_(
            Product.active== True,
            Product.name.like('%box%')  # Match boxes by name
        )
    ).all()

    # Find suitable boxes
    suitable_boxes = []

    for box in box_products:
        dimensions = parse_box_dimensions(box.name)
        if not dimensions:
            continue

        box_l, box_w, box_h = dimensions
        box_volume = box_l * box_w * box_h

        # Check if box is large enough
        if box_volume < total_volume_needed:
            continue

        # Check if largest part dimension fits
        box_min_dimension = min(box_l, box_w, box_h)
        if max_part_dimension > box_min_dimension:
            continue

        # This box works - add to candidates with volume for sorting
        suitable_boxes.append((box, box_volume))

    if not suitable_boxes:
        return None

    # Return smallest suitable box (minimum volume)
    suitable_boxes.sort(key=lambda x: x[1])
    return suitable_boxes[0][0]


def generate_custom_product_sku(quote: Quote, db: Session) -> str:
    """
    Generate a unique SKU for a custom product from a quote.

    Format: PRD-CUS-{year}-{quote_id}
    Example: PRD-CUS-2025-042

    Args:
        quote: Quote object
        db: Database session

    Returns:
        Generated SKU string
    """
    year = datetime.utcnow().year
    sku = f"PRD-CUS-{year}-{quote.id:03d}"

    # Ensure uniqueness (should be guaranteed, but check anyway)
    existing = db.query(Product).filter(Product.sku == sku).first()
    if existing:
        # Fallback: append timestamp
        timestamp = int(datetime.utcnow().timestamp())
        sku = f"PRD-CUS-{year}-{quote.id:03d}-{timestamp}"

    return sku


def auto_create_product_and_bom(quote: Quote, db: Session) -> Tuple[Product, BOM]:
    """
    Auto-create a custom product and BOM from an accepted quote.

    Creates:
    1. Custom product with type='custom'
    2. BOM with 3 lines:
       - Line 1: Material (filament) based on quote.material_type and quote.color
       - Line 2: Shipping box based on dimensions and quantity
       - Line 3: Machine time based on quote.print_time_hours

    Args:
        quote: Accepted quote object
        db: Database session

    Returns:
        Tuple of (Product, BOM)

    Raises:
        ValueError: If required quote data is missing or invalid
        RuntimeError: If material or box cannot be found
    """
    # Validate quote has required data
    if not quote.material_type:
        raise ValueError("Quote must have material_type specified")
    if not quote.color:
        raise ValueError("Quote must have color specified")
    if not quote.dimensions_x or not quote.dimensions_y or not quote.dimensions_z:
        raise ValueError("Quote must have dimensions specified")
    if not quote.quantity or quote.quantity < 1:
        raise ValueError("Quote must have valid quantity")

    # Step 1: Create custom product
    product_sku = generate_custom_product_sku(quote, db)

    product = Product(
        sku=product_sku,
        name=f"Custom Print - Quote #{quote.quote_number}",
        description=f"Auto-created from quote {quote.quote_number}. "
                    f"Material: {quote.material_type}, Color: {quote.color}",
        category="Finished Goods",
        type="custom",
        cost=float(quote.unit_price) if quote.unit_price else None,
        selling_price=float(quote.total_price) if quote.total_price else None,
        gcode_file_path=quote.gcode_file_path,  # Link to the sliced G-code
        has_bom=True,
        active=True
    )

    db.add(product)
    db.flush()  # Get product.id

    # Step 2: Collect material information
    # Check for multi-material (from quote.materials) vs single material (from quote.material_type/color)
    material_entries = []

    if quote.materials and len(quote.materials) > 0:
        # Multi-material quote - use QuoteMaterial entries
        for qm in quote.materials:
            # Fall back to quote's main color if slot color is None
            slot_color = qm.color_code or quote.color
            slot_material = qm.material_type or quote.material_type

            try:
                mat_product = get_material_product(
                    db,
                    material_type_code=slot_material,
                    color_code=slot_color
                )
                if not mat_product:
                    mat_product = create_material_product(
                        db,
                        material_type_code=slot_material,
                        color_code=slot_color,
                        commit=False # Commit will be done at the end of the service
                    )

                material_entries.append({
                    "product": mat_product,
                    "grams": float(qm.material_grams),
                    "slot": qm.slot_number,
                    "is_primary": qm.is_primary,
                    "color_name": qm.color_name or slot_color,
                })
            except (MaterialNotFoundError, ColorNotFoundError) as e:
                raise RuntimeError(
                    f"Could not find material for slot {qm.slot_number}: {slot_material} + {slot_color}. "
                    f"Error: {str(e)}. "
                    f"Please ensure material inventory is set up for this combination."
                )
    else:
        # Single material quote - use quote.material_type and quote.color
        try:
            material_product = get_material_product(
                db,
                material_type_code=quote.material_type,
                color_code=quote.color
            )
            if not material_product:
                material_product = create_material_product(
                    db,
                    material_type_code=quote.material_type,
                    color_code=quote.color,
                    commit=False # Commit will be done at the end of the service
                )
            material_entries.append({
                "product": material_product,
                "grams": float(quote.material_grams) if quote.material_grams else 0.0,
                "slot": 1,
                "is_primary": True,
                "color_name": quote.color,
            })
        except (MaterialNotFoundError, ColorNotFoundError) as e:
            raise RuntimeError(
                f"Could not find material for quote: {quote.material_type} + {quote.color}. "
                f"Error: {str(e)}. "
                f"Please ensure material inventory is set up for this combination."
            )

    # Step 3: Find best shipping box
    box_product = determine_best_box(quote, db)
    if not box_product:
        raise RuntimeError(
            f"Could not find suitable shipping box for part dimensions "
            f"{quote.dimensions_x}x{quote.dimensions_y}x{quote.dimensions_z}mm, qty={quote.quantity}"
        )

    # Step 4: Create BOM
    # Build materials list for notes
    if len(material_entries) > 1:
        materials_desc = ", ".join([f"{e['color_name']}" for e in material_entries])
        material_note = f"Multi-material ({len(material_entries)} colors): {materials_desc}"
    else:
        material_note = f"Material: {quote.material_type} {quote.color}"

    bom = BOM(
        product_id=product.id,
        code=f"BOM-{product_sku}",
        name=f"BOM for {product.name}",
        version=1,
        revision="1.0",
        active=True,
        notes=f"Auto-created from quote {quote.quote_number}. "
              f"{material_note}. Qty: {quote.quantity}."
    )

    db.add(bom)
    db.flush()  # Get bom.id

    # Step 5: Create BOM Lines for Materials (one per material/color)
    # For multi-material prints, each slot gets its own BOM line
    line_sequence = 1
    for entry in material_entries:
        mat_product = entry["product"]
        mat_grams = entry["grams"]
        slot = entry["slot"]
        color_name = entry["color_name"]

        # Material quantity = weight in kg (converted from grams)
        material_quantity_per_part = mat_grams / 1000.0
        total_material_quantity = material_quantity_per_part * quote.quantity

        slot_info = f" (Slot {slot})" if len(material_entries) > 1 else ""
        bom_line_material = BOMLine(
            bom_id=bom.id,
            component_id=mat_product.id,
            sequence=line_sequence,
            quantity=total_material_quantity,  # Total material for all parts (in kg)
            notes=f"Material{slot_info}: {mat_product.name}. "
                  f"{quote.quantity} parts @ {material_quantity_per_part:.3f}kg each. "
                  f"Color: {color_name}. SKU: {mat_product.sku}"
        )

        db.add(bom_line_material)
        line_sequence += 1

    # Step 6: Create BOM Line for Packaging (after all materials)
    # Packaging is consumed at SHIPPING stage, not production
    # This allows shipper to change box if needed (consolidation, different size, etc.)
    bom_line_box = BOMLine(
        bom_id=bom.id,
        component_id=box_product.id,
        sequence=line_sequence,
        quantity=1.0,  # One box per order
        consume_stage='shipping',  # Consumed when label is purchased, not at production
        notes=f"Shipping box: {box_product.name}"
    )

    db.add(bom_line_box)
    line_sequence += 1

    # Step 7: Create BOM Line for Machine Time (if print time available)
    if quote.print_time_hours and float(quote.print_time_hours) > 0:
        machine_time_product = get_or_create_machine_time_product(db)
        print_hours = float(quote.print_time_hours)
        machine_cost = print_hours * float(MACHINE_HOURLY_RATE)

        bom_line_machine = BOMLine(
            bom_id=bom.id,
            component_id=machine_time_product.id,
            sequence=line_sequence,
            quantity=print_hours,  # Hours of machine time
            notes=f"Machine time: {print_hours:.2f}hr @ ${MACHINE_HOURLY_RATE}/hr = ${machine_cost:.2f}"
        )

        db.add(bom_line_machine)

    # Step 8: Link product to quote
    quote.product_id = product.id

    # Commit all changes
    db.commit()
    db.refresh(product)
    db.refresh(bom)

    return product, bom


def validate_quote_for_bom(quote: Quote, db: Session) -> Tuple[bool, str]:
    """
    Validate that a quote has all required data for BOM creation.
    
    Args:
        quote: Quote to validate
        db: Database session
    
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    errors = []
    
    if not quote.material_type:
        errors.append("Missing material_type")
    if not quote.color:
        errors.append("Missing color")
    if not quote.dimensions_x or not quote.dimensions_y or not quote.dimensions_z:
        errors.append("Missing dimensions")
    if not quote.quantity or quote.quantity < 1:
        errors.append("Invalid quantity")
    if not quote.material_grams:
        errors.append("Missing material_grams")
    
    # Check if material-color combo exists
    if quote.material_type and quote.color:
        try:
            product = get_material_product(
                db,
                material_type_code=quote.material_type,
                color_code=quote.color
            )
            if not product:
                # Try to create it to see if it's a valid combination
                create_material_product(
                    db,
                    material_type_code=quote.material_type,
                    color_code=quote.color,
                    commit=False
                )
                db.rollback() # Rollback the creation, we are only validating
        except Exception as e:
            errors.append(f"Material not available: {str(e)}")
    
    # Check if suitable box exists
    if quote.dimensions_x and quote.dimensions_y and quote.dimensions_z and quote.quantity:
        box = determine_best_box(quote, db)
        if not box:
            errors.append("No suitable shipping box found")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, "Valid"
