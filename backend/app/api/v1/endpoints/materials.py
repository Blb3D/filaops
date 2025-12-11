"""
Material API Endpoints

Provides material type and color options for the quote portal.
"""
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import csv
import io
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.user import User
from app.api.v1.deps import get_current_user
from app.models.material import MaterialType, Color, MaterialColor
from app.models.product import Product
from app.models.inventory import Inventory, InventoryLocation
from app.services.material_service import (
    get_portal_material_options,
    get_available_material_types,
    get_available_colors_for_material,
    MaterialNotFoundError,
    ColorNotFoundError,
)
# MaterialInventory removed - using unified Inventory table (Phase 1.4)


router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class ColorOption(BaseModel):
    """Color option for dropdown"""
    code: str
    name: str
    hex: str | None
    hex_secondary: str | None = None
    in_stock: bool = True  # Whether this color is marked in stock
    quantity_kg: float = 0.0  # Available quantity in kg for lead time calculation


class MaterialTypeOption(BaseModel):
    """Material type with available colors"""
    code: str
    name: str
    description: str | None
    base_material: str
    price_multiplier: float
    strength_rating: int | None
    requires_enclosure: bool
    colors: List[ColorOption]


class MaterialOptionsResponse(BaseModel):
    """Response containing all material options for portal"""
    materials: List[MaterialTypeOption]


class SimpleColorOption(BaseModel):
    """Simple color option"""
    code: str
    name: str
    hex: str | None


class ColorsResponse(BaseModel):
    """Response containing colors for a material type"""
    material_type: str
    colors: List[SimpleColorOption]


# MaterialInventoryCreate and MaterialInventoryResponse removed (Phase 1.4)
# Material creation now uses POST /api/v1/items/material with MaterialItemCreate schema

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/options", response_model=MaterialOptionsResponse)
def get_material_options(
    in_stock_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get all material options for the quote portal.
    
    Returns a hierarchical structure:
    - Material types (first dropdown)
    - Colors available for each material type (second dropdown)
    
    Only returns materials that are:
    - Active
    - Customer visible
    - Have at least one color in stock (if in_stock_only=True)
    """
    try:
        materials = get_portal_material_options(db)
        
        # Filter based on in_stock_only
        if in_stock_only:
            # Already filtered by get_portal_material_options
            pass
        
        return MaterialOptionsResponse(
            materials=[
                MaterialTypeOption(
                    code=m["code"],
                    name=m["name"],
                    description=m.get("description"),
                    base_material=m["base_material"],
                    price_multiplier=m["price_multiplier"],
                    strength_rating=m.get("strength_rating"),
                    requires_enclosure=m.get("requires_enclosure", False),
                    colors=[
                        ColorOption(
                            code=c["code"],
                            name=c["name"],
                            hex=c.get("hex"),
                            hex_secondary=c.get("hex_secondary"),
                            in_stock=c.get("in_stock", True),
                            quantity_kg=c.get("quantity_kg", 0.0),
                        )
                        for c in m["colors"]
                    ]
                )
                for m in materials
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DEPRECATED ENDPOINTS - Use /api/v1/items/material instead
# ============================================================================

# @router.post("/inventory", response_model=MaterialInventoryResponse)
# def create_material_inventory(...):
#     """
#     DEPRECATED: Use POST /api/v1/items/material instead.
#     
#     This endpoint is deprecated as part of Phase 2.2 (Materials API cleanup).
#     Material creation should now use the unified Items API:
#     POST /api/v1/items/material
#     
#     This endpoint will be removed in a future version.
#     """
#     raise HTTPException(
#         status_code=410,  # Gone
#         detail="This endpoint is deprecated. Use POST /api/v1/items/material instead."
#     )


@router.get("/types")
def list_material_types(
    customer_visible_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get list of material types (for first dropdown).

    Returns just the material types without colors.
    """
    try:
        materials = get_available_material_types(db, customer_visible_only=customer_visible_only)
        
        return {
            "materials": [
                {
                    "code": m.code,
                    "name": m.name,
                    "base_material": m.base_material,
                    "description": m.description,
                    "price_multiplier": float(m.price_multiplier),
                    "strength_rating": m.strength_rating,
                    "requires_enclosure": m.requires_enclosure,
                }
                for m in materials
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types/{material_type_code}/colors", response_model=ColorsResponse)
def list_colors_for_material(
    material_type_code: str,
    in_stock_only: bool = True,
    customer_visible_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get available colors for a specific material type (for second dropdown).

    Called when user selects a material type to populate the color dropdown.
    For admin use, set customer_visible_only=false to see all colors.
    """
    try:
        colors = get_available_colors_for_material(
            db,
            material_type_code=material_type_code,
            in_stock_only=in_stock_only,
            customer_visible_only=customer_visible_only
        )
        
        return ColorsResponse(
            material_type=material_type_code,
            colors=[
                SimpleColorOption(
                    code=c.code,
                    name=c.name,
                    hex=c.hex_code,
                )
                for c in colors
            ]
        )
    except MaterialNotFoundError:
        raise HTTPException(
            status_code=404, 
            detail=f"Material type not found: {material_type_code}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ColorCreate(BaseModel):
    """Schema for creating a new color"""
    name: str
    code: str | None = None  # Auto-generated if not provided
    hex_code: str | None = None


class ColorCreateResponse(BaseModel):
    """Response after creating a color"""
    id: int
    code: str
    name: str
    hex_code: str | None
    material_type_code: str
    message: str


@router.post("/types/{material_type_code}/colors", response_model=ColorCreateResponse)
def create_color_for_material(
    material_type_code: str,
    color_data: ColorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new color and link it to a material type.

    This endpoint allows creating colors on-the-fly when setting up materials,
    without requiring a CSV import.

    - Creates the color in the colors table
    - Creates a MaterialColor link to the specified material type
    - Returns the created color info
    """
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required to create colors"
        )

    # Find material type
    material_type = db.query(MaterialType).filter(
        MaterialType.code == material_type_code
    ).first()

    if not material_type:
        raise HTTPException(
            status_code=404,
            detail=f"Material type not found: {material_type_code}"
        )

    # Generate code if not provided
    color_code = color_data.code
    if not color_code:
        # Generate from name: "Mystic Blue" -> "MYSTIC_BLUE"
        color_code = color_data.name.upper().replace(" ", "_").replace("-", "_")
        # Ensure it's unique
        base_code = color_code
        counter = 1
        while db.query(Color).filter(Color.code == color_code).first():
            color_code = f"{base_code}_{counter}"
            counter += 1

    # Check if code already exists
    existing_color = db.query(Color).filter(Color.code == color_code).first()

    if existing_color:
        # Color exists - just need to link it to this material type
        color = existing_color

        # Check if already linked
        existing_link = db.query(MaterialColor).filter(
            MaterialColor.material_type_id == material_type.id,
            MaterialColor.color_id == color.id
        ).first()

        if existing_link:
            raise HTTPException(
                status_code=400,
                detail=f"Color '{color.name}' is already linked to {material_type.name}"
            )
    else:
        # Create new color
        color = Color(
            code=color_code,
            name=color_data.name,
            hex_code=color_data.hex_code,
            active=True,
            is_customer_visible=True,
            display_order=100
        )
        db.add(color)
        db.flush()

    # Create MaterialColor link
    material_color = MaterialColor(
        material_type_id=material_type.id,
        color_id=color.id,
        is_customer_visible=True,
        active=True
    )
    db.add(material_color)
    db.commit()
    db.refresh(color)

    return ColorCreateResponse(
        id=color.id,
        code=color.code,
        name=color.name,
        hex_code=color.hex_code,
        material_type_code=material_type_code,
        message=f"Color '{color.name}' created and linked to {material_type.name}"
    )


@router.get("/for-bom")
def get_materials_for_bom(
    db: Session = Depends(get_db)
):
    """
    Get all materials formatted for BOM usage.

    Returns materials with their linked product_id (creates Product records if needed).
    This is the proper way to add materials to BOMs - they become regular items.
    """
    from app.services.material_service import (
        get_available_material_types,
        get_available_colors_for_material,
    )
    from app.models.inventory import Inventory

    try:
        materials = get_available_material_types(db, customer_visible_only=False)
        result = []

        for material in materials:
            colors = get_available_colors_for_material(
                db,
                material.code,
                in_stock_only=False,
                customer_visible_only=False
            )

            for color in colors:
                # Get or create the product (this ensures it exists in products table)
                try:
                    product, _ = get_material_product_for_bom(
                        db,
                        material_type_code=material.code,
                        color_code=color.code,
                        require_in_stock=False
                    )

                    # Get inventory from unified Inventory table
                    from app.models.inventory import Inventory
                    inventory = db.query(Inventory).filter(
                        Inventory.product_id == product.id
                    ).first()

                    # Calculate available quantity
                    quantity_available = 0.0
                    in_stock = False
                    if inventory:
                        quantity_available = float(inventory.on_hand_quantity or 0)
                        in_stock = quantity_available > 0

                    result.append({
                        "id": product.id,  # This is the key - actual product_id for BOM
                        "sku": product.sku,
                        "name": f"{material.name} - {color.name}",
                        "description": material.description or f"{material.base_material} filament",
                        "item_type": "supply",
                        "procurement_type": "buy",
                        "unit": "kg",
                        "standard_cost": float(product.standard_cost) if product.standard_cost else float(material.base_price_per_kg),
                        "in_stock": in_stock,
                        "quantity_available": quantity_available,
                        "material_code": material.code,
                        "color_code": color.code,
                        "color_hex": color.hex_code,
                    })
                except Exception as e:
                    # Skip materials that can't be resolved
                    continue

        return {"items": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pricing/{material_type_code}")
def get_material_pricing(
    material_type_code: str,
    db: Session = Depends(get_db)
):
    """
    Get pricing information for a material type.
    
    Used by the quote engine to calculate prices.
    """
    try:
        materials = get_available_material_types(db, customer_visible_only=False)
        material = next((m for m in materials if m.code == material_type_code), None)
        
        if not material:
            raise HTTPException(
                status_code=404,
                detail=f"Material type not found: {material_type_code}"
            )
        
        return {
            "code": material.code,
            "name": material.name,
            "base_material": material.base_material,
            "density": float(material.density),
            "base_price_per_kg": float(material.base_price_per_kg),
            "price_multiplier": float(material.price_multiplier),
            "volumetric_flow_limit": float(material.volumetric_flow_limit) if material.volumetric_flow_limit else None,
            "nozzle_temp_min": material.nozzle_temp_min,
            "nozzle_temp_max": material.nozzle_temp_max,
            "bed_temp_min": material.bed_temp_min,
            "bed_temp_max": material.bed_temp_max,
            "requires_enclosure": material.requires_enclosure,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CSV IMPORT
# ============================================================================

class MaterialCSVImportResult(BaseModel):
    """Result of material CSV import"""
    total_rows: int
    created: int
    updated: int
    skipped: int
    errors: List[dict]


@router.get("/import/template")
async def download_material_import_template():
    """
    Download CSV template for material inventory import.
    
    Template format matches the standard material inventory CSV:
    - Category (e.g., "PLA Matte", "PLA Basic")
    - SKU (e.g., "MAT-FDM-PLA-MATTE-CHAR")
    - Name (e.g., "PLA Matte Charcoal")
    - Material Type (e.g., "PLA_MATTE")
    - Material Color Name (e.g., "Charcoal")
    - HEX Code (e.g., "#0C0C0C")
    - Unit (kg)
    - Status (Active)
    - Price (e.g., 19.99)
    - On Hand (g) (e.g., 1000)
    """
    template = """Category,SKU,Name,Material Type,Material Color Name,HEX Code,Unit,Status,Price,On Hand (g)
PLA Matte,MAT-FDM-PLA-MATTE-CHAR,PLA Matte Charcoal,PLA_MATTE,Charcoal,#0C0C0C,kg,Active,19.99,0
PLA Basic,MAT-FDM-PLA-BASIC-RED,PLA Basic Red,PLA_BASIC,Red,#FF0000,kg,Active,19.99,0
PLA Silk,MAT-FDM-PLA-SILK-GOLD,PLA Silk Gold,PLA_SILK,Gold,#F4A925,kg,Active,22.99,0"""
    
    return StreamingResponse(
        io.BytesIO(template.encode('utf-8')),
        media_type='text/csv',
        headers={"Content-Disposition": "attachment; filename=material_inventory_template.csv"}
    )


@router.post("/import", response_model=MaterialCSVImportResult)
async def import_materials_csv(
    file: UploadFile = File(...),
    update_existing: bool = Query(False, description="Update existing materials if SKU exists"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import material inventory from CSV file.
    
    Expected CSV format:
    - Category: Material category (e.g., "PLA Matte", "PLA Basic")
    - SKU: Product SKU (e.g., "MAT-FDM-PLA-MATTE-CHAR")
    - Name: Product name (e.g., "PLA Matte Charcoal")
    - Material Type: Material type code (e.g., "PLA_MATTE", "PLA_BASIC")
    - Material Color Name: Color name (e.g., "Charcoal", "Red")
    - HEX Code: Color hex code (e.g., "#0C0C0C")
    - Unit: Unit of measure (should be "kg")
    - Status: Active status (e.g., "Active")
    - Price: Price per kg (e.g., 19.99)
    - On Hand (g): Quantity in grams (will be converted to kg)
    
    Creates:
    - MaterialType (if doesn't exist)
    - Color (if doesn't exist)
    - MaterialColor link
    - Product with SKU
    - Inventory record with quantity
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')
    
    # Handle BOM
    if text.startswith('\ufeff'):
        text = text[1:]
    
    reader = csv.DictReader(io.StringIO(text))
    
    result = MaterialCSVImportResult(
        total_rows=0,
        created=0,
        updated=0,
        skipped=0,
        errors=[],
    )
    
    # Get or create default inventory location
    default_location = db.query(InventoryLocation).filter(
        InventoryLocation.code == "MAIN"
    ).first()
    
    if not default_location:
        default_location = InventoryLocation(
            code="MAIN",
            name="Main Warehouse",
            type="warehouse",
            active=True
        )
        db.add(default_location)
        db.commit()
        db.refresh(default_location)
    
    # Column name variations
    SKU_COLS = ["sku", "SKU", "Sku"]
    NAME_COLS = ["name", "Name", "Product Name"]
    MATERIAL_TYPE_COLS = ["material type", "Material Type", "material_type", "Material_Type"]
    COLOR_NAME_COLS = ["material color name", "Material Color Name", "material_color_name", "Color Name", "color name"]
    HEX_COLS = ["hex code", "HEX Code", "hex_code", "HEX", "hex"]
    PRICE_COLS = ["price", "Price", "PRICE"]
    ON_HAND_COLS = ["on hand (g)", "On Hand (g)", "on_hand_g", "On Hand", "on hand", "quantity", "Quantity"]
    
    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        sku = ""  # Initialize sku at the start of each loop
        
        try:
            # Find SKU
            for col in SKU_COLS:
                if row.get(col, "").strip():
                    sku = row.get(col, "").strip()
                    break
            
            if not sku:
                result.errors.append({
                    "row": row_num,
                    "error": "SKU is required",
                    "sku": ""
                })
                result.skipped += 1
                continue
            
            # Find material type
            material_type_code = ""
            for col in MATERIAL_TYPE_COLS:
                if row.get(col, "").strip():
                    material_type_code = row.get(col, "").strip().upper()
                    break
            
            if not material_type_code:
                result.errors.append({
                    "row": row_num,
                    "error": "Material Type is required",
                    "sku": sku
                })
                result.skipped += 1
                continue
            
            # Find color name
            color_name = ""
            for col in COLOR_NAME_COLS:
                if row.get(col, "").strip():
                    color_name = row.get(col, "").strip()
                    break
            
            if not color_name:
                result.errors.append({
                    "row": row_num,
                    "error": "Material Color Name is required",
                    "sku": sku
                })
                result.skipped += 1
                continue
            
            # Find hex code
            hex_code = ""
            for col in HEX_COLS:
                if row.get(col, "").strip():
                    hex_code = row.get(col, "").strip()
                    break
            
            # Find price
            price = None
            for col in PRICE_COLS:
                if row.get(col, "").strip():
                    try:
                        price_str = row.get(col, "").strip().replace("$", "").replace(",", "")
                        price = Decimal(price_str)
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Find on-hand quantity (in grams, convert to kg)
            on_hand_kg = Decimal("0.00")
            for col in ON_HAND_COLS:
                if row.get(col, "").strip():
                    try:
                        grams = Decimal(row.get(col, "").strip().replace(",", ""))
                        on_hand_kg = grams / Decimal("1000")  # Convert grams to kg
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Get or create material type
            material_type = db.query(MaterialType).filter(
                MaterialType.code == material_type_code
            ).first()
            
            if not material_type:
                # Try to infer base material from code
                base_material = "PLA"
                if "PETG" in material_type_code:
                    base_material = "PETG"
                elif "ABS" in material_type_code:
                    base_material = "ABS"
                elif "ASA" in material_type_code:
                    base_material = "ASA"
                elif "TPU" in material_type_code:
                    base_material = "TPU"
                elif "PAHT" in material_type_code:
                    base_material = "PAHT"
                elif "PC" in material_type_code:
                    base_material = "PC"
                
                # Create material type with defaults
                material_type = MaterialType(
                    code=material_type_code,
                    name=material_type_code.replace("_", " ").title(),
                    base_material=base_material,
                    density=Decimal("1.24"),  # Default, should be updated
                    base_price_per_kg=price or Decimal("20.00"),
                    price_multiplier=Decimal("1.0"),
                    active=True,
                    is_customer_visible=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(material_type)
                db.flush()
            
            # Generate color code from color name (uppercase, replace spaces with underscores)
            color_code = color_name.upper().replace(" ", "_").replace("-", "_")
            # Limit to 30 chars (Color.code max length)
            if len(color_code) > 30:
                color_code = color_code[:30]
            
            # Get or create color
            color = db.query(Color).filter(Color.code == color_code).first()
            
            if not color:
                color = Color(
                    code=color_code,
                    name=color_name,
                    hex_code=hex_code if hex_code else None,
                    active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(color)
                db.flush()
            elif hex_code and not color.hex_code:
                # Update hex code if missing
                color.hex_code = hex_code
                color.updated_at = datetime.now(timezone.utc)
            
            # Create MaterialColor link if doesn't exist
            material_color = db.query(MaterialColor).filter(
                MaterialColor.material_type_id == material_type.id,
                MaterialColor.color_id == color.id
            ).first()
            
            if not material_color:
                material_color = MaterialColor(
                    material_type_id=material_type.id,
                    color_id=color.id,
                    active=True
                )
                db.add(material_color)
            
            # Get or create product
            product = db.query(Product).filter(Product.sku == sku).first()
            
            if product:
                if not update_existing:
                    result.skipped += 1
                    continue
                result.updated += 1
            else:
                # Find name
                name = ""
                for col in NAME_COLS:
                    if row.get(col, "").strip():
                        name = row.get(col, "").strip()
                        break
                
                if not name:
                    name = f"{material_type.name} - {color_name}"
                
                product = Product(
                    sku=sku,
                    name=name,
                    description=f"Filament supply: {material_type.name} in {color_name}",
                    item_type="supply",
                    procurement_type="buy",
                    unit="kg",
                    standard_cost=float(price) if price else float(material_type.base_price_per_kg),
                    material_type_id=material_type.id,
                    color_id=color.id,
                    active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(product)
                db.flush()
                result.created += 1
            
            # Update product if needed
            if price and product.standard_cost != float(price):
                product.standard_cost = float(price)
                product.updated_at = datetime.now(timezone.utc)
            
            # Get or create inventory record
            inventory = db.query(Inventory).filter(
                Inventory.product_id == product.id,
                Inventory.location_id == default_location.id
            ).first()
            
            if not inventory:
                inventory = Inventory(
                    product_id=product.id,
                    location_id=default_location.id,
                    on_hand_quantity=on_hand_kg,
                    allocated_quantity=Decimal("0.00"),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(inventory)
            else:
                inventory.on_hand_quantity = on_hand_kg
                # available_quantity is computed automatically (on_hand - allocated)
                inventory.updated_at = datetime.now(timezone.utc)
            
            # Commit after each row (for now - can optimize later)
            try:
                db.commit()
            except Exception as commit_err:
                db.rollback()
                result.errors.append({
                    "row": row_num,
                    "error": f"Database error: {str(commit_err)}",
                    "sku": sku
                })
                result.skipped += 1
                continue
            
        except Exception as e:
            db.rollback()
            sku_value = sku if 'sku' in locals() and sku else ""
            result.errors.append({
                "row": row_num,
                "error": str(e),
                "sku": sku_value
            })
            result.skipped += 1
    
    return result
