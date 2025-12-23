"""
Items API Endpoints - Unified item management for products, components, supplies, and services
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
import csv
import io

from decimal import Decimal
from app.db.session import get_db
from app.logging_config import get_logger
from app.models import Product, ItemCategory, Inventory, BOM, BOMLine
from app.models.inventory import InventoryLocation
from app.models.manufacturing import Routing
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.item import (
    ItemType,
    ProcurementType,
    ItemCategoryCreate,
    ItemCategoryUpdate,
    ItemCategoryResponse,
    ItemCategoryTreeNode,
    ItemCreate,
    ItemUpdate,
    ItemListResponse,
    ItemResponse,
    ItemCSVImportResult,
    ItemBulkUpdateRequest,
    MaterialItemCreate,
)

router = APIRouter()
logger = get_logger(__name__)

# Default pricing markup (from quoter: PLA/PETG=3.5x, ABS/ASA=4.0x, TPU=4.5x)
# Using 3.5x as default since PLA is most common
DEFAULT_PRICE_MARKUP = 3.5


# ============================================================================
# Inline UOM Conversion (fallback when database UOM table is empty)
# ============================================================================

UOM_CONVERSIONS = {
    # Mass conversions (to KG)
    'G': {'base': 'KG', 'factor': Decimal('0.001')},
    'KG': {'base': 'KG', 'factor': Decimal('1')},
    'LB': {'base': 'KG', 'factor': Decimal('0.453592')},
    'OZ': {'base': 'KG', 'factor': Decimal('0.0283495')},
    # Length conversions (to M)
    'MM': {'base': 'M', 'factor': Decimal('0.001')},
    'CM': {'base': 'M', 'factor': Decimal('0.01')},
    'M': {'base': 'M', 'factor': Decimal('1')},
    'IN': {'base': 'M', 'factor': Decimal('0.0254')},
    'FT': {'base': 'M', 'factor': Decimal('0.3048')},
    # Volume conversions (to L)
    'ML': {'base': 'L', 'factor': Decimal('0.001')},
    'L': {'base': 'L', 'factor': Decimal('1')},
    # Count units (no conversion)
    'EA': {'base': 'EA', 'factor': Decimal('1')},
    'PK': {'base': 'PK', 'factor': Decimal('1')},
    'BOX': {'base': 'BOX', 'factor': Decimal('1')},
    'ROLL': {'base': 'ROLL', 'factor': Decimal('1')},
}


def convert_uom_inline(quantity: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """
    Convert quantity using inline conversion factors (no database lookup).
    Used as fallback when database UOM table is empty.
    """
    from_unit = (from_unit or 'EA').upper().strip()
    to_unit = (to_unit or 'EA').upper().strip()
    
    if from_unit == to_unit:
        return quantity
    
    from_info = UOM_CONVERSIONS.get(from_unit)
    to_info = UOM_CONVERSIONS.get(to_unit)
    
    if not from_info or not to_info:
        return quantity  # Unknown unit, return as-is
    
    if from_info['base'] != to_info['base']:
        return quantity  # Incompatible bases
    
    # Convert: from_unit -> base -> to_unit
    quantity_in_base = quantity * from_info['factor']
    quantity_in_target = quantity_in_base / to_info['factor']
    
    return quantity_in_target


# ============================================================================
# Item Categories
# ============================================================================

@router.get("/categories", response_model=List[ItemCategoryResponse])
async def list_categories(
    include_inactive: bool = False,
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    List all item categories

    - **include_inactive**: Include inactive categories
    - **parent_id**: Filter to children of a specific parent (null for root categories)
    """
    query = db.query(ItemCategory)

    if not include_inactive:
        query = query.filter(ItemCategory.is_active.is_(True))  # noqa: E712

    if parent_id is not None:
        query = query.filter(ItemCategory.parent_id == parent_id)

    categories = query.order_by(ItemCategory.sort_order, ItemCategory.name).all()

    result = []
    for cat in categories:
        resp = ItemCategoryResponse(
            id=cat.id,
            code=cat.code,
            name=cat.name,
            parent_id=cat.parent_id,
            description=cat.description,
            sort_order=cat.sort_order,
            is_active=cat.is_active,
            parent_name=cat.parent.name if cat.parent else None,
            full_path=cat.full_path,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
        )
        result.append(resp)

    return result


@router.get("/categories/tree", response_model=List[ItemCategoryTreeNode])
async def get_category_tree(
    db: Session = Depends(get_db),
):
    """Get categories as a nested tree structure"""
    # Get all active categories
    categories = db.query(ItemCategory).filter(
        ItemCategory.is_active.is_(True)
    ).order_by(ItemCategory.sort_order, ItemCategory.name).all()

    # Build tree
    def build_tree(parent_id: Optional[int] = None) -> List[ItemCategoryTreeNode]:
        nodes = []
        for cat in categories:
            if cat.parent_id == parent_id:
                node = ItemCategoryTreeNode(
                    id=cat.id,
                    code=cat.code,
                    name=cat.name,
                    description=cat.description,
                    is_active=cat.is_active,
                    children=build_tree(cat.id),
                )
                nodes.append(node)
        return nodes

    return build_tree(None)


@router.post("/categories", response_model=ItemCategoryResponse, status_code=201)
async def create_category(
    request: ItemCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new item category"""
    # Check for duplicate code
    existing = db.query(ItemCategory).filter(ItemCategory.code == request.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Category code '{request.code}' already exists")

    # Validate parent exists
    if request.parent_id:
        parent = db.query(ItemCategory).filter(ItemCategory.id == request.parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail=f"Parent category {request.parent_id} not found")

    category = ItemCategory(
        code=request.code.upper(),
        name=request.name,
        parent_id=request.parent_id,
        description=request.description,
        sort_order=request.sort_order or 0,
        is_active=request.is_active if request.is_active is not None else True,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    logger.info(f"Created category: {category.code}")

    return ItemCategoryResponse(
        id=category.id,
        code=category.code,
        name=category.name,
        parent_id=category.parent_id,
        description=category.description,
        sort_order=category.sort_order,
        is_active=category.is_active,
        parent_name=category.parent.name if category.parent else None,
        full_path=category.full_path,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.get("/categories/{category_id}", response_model=ItemCategoryResponse)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific category by ID"""
    category = db.query(ItemCategory).filter(ItemCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")

    return ItemCategoryResponse(
        id=category.id,
        code=category.code,
        name=category.name,
        parent_id=category.parent_id,
        description=category.description,
        sort_order=category.sort_order,
        is_active=category.is_active,
        parent_name=category.parent.name if category.parent else None,
        full_path=category.full_path,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.patch("/categories/{category_id}", response_model=ItemCategoryResponse)
async def update_category(
    category_id: int,
    request: ItemCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing category"""
    category = db.query(ItemCategory).filter(ItemCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")

    # Check for code conflict if changing code
    if request.code and request.code.upper() != category.code:
        existing = db.query(ItemCategory).filter(ItemCategory.code == request.code.upper()).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Category code '{request.code}' already exists")

    # Validate parent if changing
    if request.parent_id is not None and request.parent_id != category.parent_id:
        if request.parent_id == category_id:
            raise HTTPException(status_code=400, detail="Category cannot be its own parent")
        if request.parent_id:
            parent = db.query(ItemCategory).filter(ItemCategory.id == request.parent_id).first()
            if not parent:
                raise HTTPException(status_code=400, detail=f"Parent category {request.parent_id} not found")

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "code" and value:
            value = value.upper()
        setattr(category, field, value)

    category.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(category)

    logger.info(f"Updated category: {category.code}")

    return ItemCategoryResponse(
        id=category.id,
        code=category.code,
        name=category.name,
        parent_id=category.parent_id,
        description=category.description,
        sort_order=category.sort_order,
        is_active=category.is_active,
        parent_name=category.parent.name if category.parent else None,
        full_path=category.full_path,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete a category (set is_active=False)

    Will fail if category has active items or child categories.
    """
    category = db.query(ItemCategory).filter(ItemCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")

    # Check for child categories
    children = db.query(ItemCategory).filter(
        ItemCategory.parent_id == category_id,
        ItemCategory.is_active.is_(True)
    ).count()
    if children > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category with {children} active child categories"
        )

    # Check for items in this category
    items = db.query(Product).filter(
        Product.category_id == category_id,
        Product.active.is_(True)
    ).count()
    if items > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category with {items} active items"
        )

    category.is_active = False
    category.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Deleted (deactivated) category: {category.code}")

    return {"message": f"Category {category.code} deleted"}


# ============================================================================
# Items (Products with extended fields)
# ============================================================================

@router.get("", response_model=dict)
async def list_items(
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    procurement_type: Optional[str] = Query(None, description="Filter by procurement type: make, buy, make_or_buy"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search SKU or name"),
    active_only: bool = Query(True, description="Only show active items"),
    needs_reorder: bool = Query(False, description="Only show items below reorder point"),
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List items with filtering and pagination

    Returns items with inventory summary and reorder status.
    Max 2000 items per request to support dropdown selectors.
    """
    query = db.query(Product)

    # Filters
    if active_only:
        query = query.filter(Product.active.is_(True))  # noqa: E712

    if item_type:
        if item_type == "filament":
            # Filaments are supply items with a material_type_id
            query = query.filter(Product.material_type_id.isnot(None))
        else:
            query = query.filter(Product.item_type == item_type)

    if procurement_type:
        query = query.filter(Product.procurement_type == procurement_type)

    if category_id:
        # Get all descendant category IDs (including the selected one)
        category_ids = _get_category_and_descendants(db, category_id)
        query = query.filter(Product.category_id.in_(category_ids))

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Product.sku.ilike(search_pattern),
                Product.name.ilike(search_pattern),
                Product.upc.ilike(search_pattern),
            )
        )

    # Get total count before pagination
    total = query.count()

    # Load with category relationship
    query = query.options(joinedload(Product.item_category))

    # Order and paginate
    items = query.order_by(Product.sku).offset(offset).limit(limit).all()

    # Build response with inventory info
    result = []
    for item in items:
        # Get inventory totals
        inv = db.query(
            func.coalesce(func.sum(Inventory.on_hand_quantity), 0).label("on_hand"),
            func.coalesce(func.sum(Inventory.allocated_quantity), 0).label("allocated"),
        ).filter(Inventory.product_id == item.id).first()

        # STAR SCHEMA: Inventory stores GRAMS for materials, native unit for others
        # No conversion needed - inventory is already in transaction unit
        on_hand = float(inv.on_hand) if inv else 0
        allocated = float(inv.allocated) if inv else 0
        
        # Check if material for reorder point conversion
        is_material = item.material_type_id is not None
        reorder_point = float(item.reorder_point) if item.reorder_point else None
        if is_material and reorder_point:
            # Reorder point is stored in product_unit (KG), convert to grams for display
            reorder_point = reorder_point * 1000
        
        available = on_hand - allocated
        item_needs_reorder = reorder_point is not None and on_hand <= reorder_point

        # Skip if needs_reorder filter is on and item doesn't need reorder
        if needs_reorder and not item_needs_reorder:
            continue

        # Calculate suggested price from standard cost with markup
        suggested_price = None
        if item.standard_cost:
            suggested_price = float(item.standard_cost) * DEFAULT_PRICE_MARKUP

        result.append(ItemListResponse(
            id=item.id,
            sku=item.sku,
            name=item.name,
            item_type=item.item_type or "finished_good",
            procurement_type=item.procurement_type or "buy",
            category_id=item.category_id,
            category_name=item.item_category.name if item.item_category else None,
            unit=item.unit,
            standard_cost=item.standard_cost,
            average_cost=item.average_cost,
            selling_price=item.selling_price,
            suggested_price=suggested_price,
            active=item.active,
            on_hand_qty=on_hand,
            available_qty=available,
            reorder_point=reorder_point,
            needs_reorder=item_needs_reorder,
        ))

    return {
        "total": total,
        "items": result,
    }


@router.post("", response_model=ItemResponse, status_code=201)
async def create_item(
    request: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new item"""
    # Auto-generate SKU if not provided
    if not request.sku or request.sku.strip() == "":
        # Generate SKU based on item type and a sequence number
        item_type_prefix = {
            "finished_good": "FG",
            "component": "COMP",
            "supply": "SUP",
            "service": "SRV",
        }.get(request.item_type.value if hasattr(request.item_type, 'value') else str(request.item_type), "ITM")
        
        # Find the highest existing SKU with this prefix
        existing_skus = db.query(Product.sku).filter(
            Product.sku.like(f"{item_type_prefix}-%")
        ).all()
        
        max_num = 0
        for (sku,) in existing_skus:
            try:
                # Extract number from SKU like "FG-001" or "COMP-042"
                parts = sku.split("-")
                if len(parts) >= 2:
                    num = int(parts[-1])
                    max_num = max(max_num, num)
            except (ValueError, IndexError):
                pass
        
        # Generate new SKU with zero-padded number
        new_num = max_num + 1
        request.sku = f"{item_type_prefix}-{new_num:03d}"
    
    # Check for duplicate SKU
    existing = db.query(Product).filter(Product.sku == request.sku.upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"SKU '{request.sku}' already exists")

    # Validate category if provided
    if request.category_id:
        category = db.query(ItemCategory).filter(ItemCategory.id == request.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail=f"Category {request.category_id} not found")

    item = Product(
        sku=request.sku.upper(),
        name=request.name,
        description=request.description,
        unit=request.unit or "EA",
        item_type=request.item_type.value if request.item_type else "finished_good",
        procurement_type=request.procurement_type.value if request.procurement_type else "buy",
        category_id=request.category_id,
        cost_method=request.cost_method.value if request.cost_method else "average",
        standard_cost=request.standard_cost,
        selling_price=request.selling_price,
        weight_oz=request.weight_oz,
        length_in=request.length_in,
        width_in=request.width_in,
        height_in=request.height_in,
        lead_time_days=request.lead_time_days,
        min_order_qty=request.min_order_qty,
        reorder_point=request.reorder_point,
        upc=request.upc,
        legacy_sku=request.legacy_sku,
        is_raw_material=request.is_raw_material or False,
        track_lots=request.track_lots or False,
        track_serials=request.track_serials or False,
        active=True,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    logger.info(f"Created item: {item.sku}")

    return _build_item_response(item, db)


@router.post("/material", response_model=ItemResponse, status_code=201)
async def create_material_item(
    request: MaterialItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a material item (shortcut for supply items with material_type/color).

    This is a convenience endpoint for creating filament/material products.
    It automatically:
    - Sets item_type='supply'
    - Sets procurement_type='buy'
    - Sets unit='G' (grams) - STAR SCHEMA design
    - Links material_type_id and color_id
    - Creates Inventory record
    
    The SKU is auto-generated as: MAT-{material_type_code}-{color_code}
    Note: Costs are still tracked as $/KG, but quantities use grams.
    """
    from app.services.material_service import (
        create_material_product,
        get_material_type,
        get_color,
        MaterialNotFoundError,
        ColorNotFoundError,
    )
    from app.models.item_category import ItemCategory
    
    # Validate material type and color exist
    try:
        material_type = get_material_type(db, request.material_type_code)
        color = get_color(db, request.color_code)
    except MaterialNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ColorNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Check if product already exists
    sku = f"MAT-{material_type.code}-{color.code}"
    existing = db.query(Product).filter(Product.sku == sku).first()
    if existing:
        # Return existing product, but update fields if provided
        if request.cost_per_kg is not None:
            existing.standard_cost = request.cost_per_kg
        if request.selling_price is not None:
            existing.selling_price = request.selling_price
        if request.category_id is not None:
            existing.category_id = request.category_id
        
        # Update initial inventory if provided
        if request.initial_qty_kg and request.initial_qty_kg > 0:
            inventory = db.query(Inventory).filter(
                Inventory.product_id == existing.id
            ).first()
            if inventory:
                inventory.on_hand_quantity = request.initial_qty_kg
            else:
                # Get default location
                location = db.query(InventoryLocation).filter(
                    InventoryLocation.code == 'MAIN'
                ).first()
                if not location:
                    location = InventoryLocation(
                        name="Main Warehouse",
                        code="MAIN",
                        type="warehouse"
                    )
                    db.add(location)
                    db.flush()
                
                inventory = Inventory(
                    product_id=existing.id,
                    location_id=location.id,
                    on_hand_quantity=request.initial_qty_kg,
                    allocated_quantity=0
                )
                db.add(inventory)
        
        db.commit()
        db.refresh(existing)
        logger.info(f"Updated existing material item: {existing.sku}")
        return _build_item_response(existing, db)
    
    # Create new material product
    product = create_material_product(
        db,
        material_type_code=request.material_type_code,
        color_code=request.color_code,
        commit=False  # We'll commit after setting additional fields
    )
    
    # Override cost if provided
    if request.cost_per_kg is not None:
        product.standard_cost = request.cost_per_kg
    
    # Set selling price if provided
    if request.selling_price is not None:
        product.selling_price = request.selling_price
    
    # Set category if provided, otherwise try to find Materials category
    if request.category_id:
        category = db.query(ItemCategory).filter(ItemCategory.id == request.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail=f"Category {request.category_id} not found")
        product.category_id = request.category_id
    else:
        # Try to find a Materials category
        materials_category = db.query(ItemCategory).filter(
            ItemCategory.code.ilike('%MATERIAL%')
        ).first()
        if materials_category:
            product.category_id = materials_category.id
    
    # Set initial inventory quantity if provided
    if request.initial_qty_kg and request.initial_qty_kg > 0:
        # Find the inventory record we just created
        inventory = db.query(Inventory).filter(
            Inventory.product_id == product.id
        ).first()
        if inventory:
            inventory.on_hand_quantity = request.initial_qty_kg
    
    db.commit()
    db.refresh(product)
    
    logger.info(f"Created material item: {product.sku}")
    
    return _build_item_response(product, db)


# ============================================================================
# Low Stock / Reorder Alerts
# ============================================================================

@router.get("/low-stock")
async def get_low_stock_items(
    include_zero_reorder: bool = False,
    include_mrp_shortages: bool = Query(True, description="Include MRP shortages from active orders"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Get items that are below their reorder point OR have shortages from active orders.

    Returns items where:
    - available_quantity <= reorder_point (traditional low stock), OR
    - net_shortage > 0 from MRP explosion of active sales orders (MRP shortages)

    - **include_zero_reorder**: Include items with reorder_point = 0 or NULL (default: False)
    - **include_mrp_shortages**: Include items with shortages from active orders (default: True)
    - **limit**: Maximum number of items to return
    """
    from decimal import Decimal

    items_dict = {}  # product_id -> item data

    # 1. Get items below reorder point (traditional low stock)
    # Exclude "make" items - those need Work Orders, not Purchase Orders
    query = db.query(Product, Inventory).outerjoin(
        Inventory, Product.id == Inventory.product_id
    ).filter(
        Product.active.is_(True),  # noqa: E712
        Product.reorder_point.isnot(None),
        or_(Product.procurement_type != 'make', Product.procurement_type.is_(None)),
    )

    if not include_zero_reorder:
        query = query.filter(Product.reorder_point > 0)

    # Filter to items below reorder point
    query = query.filter(
        or_(
            Inventory.available_quantity <= Product.reorder_point,
            Inventory.id.is_(None)  # No inventory record = 0 stock
        )
    )

    results = query.limit(limit).all()

    for product, inventory in results:
        available = float(inventory.available_quantity) if inventory else 0
        on_hand = float(inventory.on_hand_quantity) if inventory else 0
        reorder_point = float(product.reorder_point) if product.reorder_point else 0
        shortfall = reorder_point - available

        items_dict[product.id] = {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "item_type": product.item_type,
            "procurement_type": product.procurement_type or "buy",
            "unit": product.unit,
            "category_name": product.item_category.name if product.item_category else None,
            "on_hand_qty": on_hand,
            "available_qty": available,
            "reorder_point": reorder_point,
            "shortfall": shortfall,  # Shortfall from reorder point
            "mrp_shortage": 0,  # Will be filled from MRP if applicable
            "cost": float(product.standard_cost or product.average_cost or 0),
            "preferred_vendor_id": product.preferred_vendor_id,
            "shortage_source": "reorder_point",  # or "mrp" or "both"
        }

    # 2. Get MRP shortages from active sales orders (if enabled)
    if include_mrp_shortages:
        from app.models.sales_order import SalesOrder, SalesOrderLine
        from app.services.mrp import MRPService

        # Get all active sales orders (not cancelled, not completed)
        active_orders = db.query(SalesOrder).filter(
            SalesOrder.status.notin_(["cancelled", "completed", "delivered"]),
        ).all()

        mrp_service = MRPService(db)
        
        # Aggregate requirements across all active orders
        all_requirements = []
        for order in active_orders:
            if order.order_type == "line_item":
                # Get order lines
                lines = db.query(SalesOrderLine).filter(
                    SalesOrderLine.sales_order_id == order.id
                ).all()
                
                for line in lines:
                    if line.product_id:
                        # Explode BOM for this line
                        try:
                            requirements = mrp_service.explode_bom(
                                product_id=line.product_id,
                                quantity=Decimal(str(line.quantity)),
                                source_demand_type="sales_order",
                                source_demand_id=order.id
                            )
                            all_requirements.extend(requirements)
                        except Exception:
                            # Skip if BOM explosion fails (no BOM, etc.)
                            continue
            elif order.order_type == "quote_based" and hasattr(order, 'quote_id') and order.quote_id:
                # For quote-based orders, get product from quote
                from app.models.quote import Quote
                quote = db.query(Quote).filter(Quote.id == order.quote_id).first()
                if quote and quote.product_id:
                    try:
                        requirements = mrp_service.explode_bom(
                            product_id=quote.product_id,
                            quantity=Decimal(str(order.quantity)),
                            source_demand_type="sales_order",
                            source_demand_id=order.id
                        )
                        all_requirements.extend(requirements)
                    except Exception:
                        # Skip if BOM explosion fails
                        continue
        
        # Aggregate requirements by product_id (sum quantities)
        aggregated_requirements = {}
        
        for req in all_requirements:
            key = req.product_id
            if key not in aggregated_requirements:
                aggregated_requirements[key] = {
                    "product_id": req.product_id,
                    "product_sku": req.product_sku,
                    "product_name": req.product_name,
                    "gross_quantity": req.gross_quantity,
                    "bom_level": req.bom_level,
                }
            else:
                aggregated_requirements[key]["gross_quantity"] += req.gross_quantity
        
        # Calculate net requirements
        if aggregated_requirements:
            from app.services.mrp import ComponentRequirement
            component_reqs = []
            for req_data in aggregated_requirements.values():
                component_reqs.append(
                    ComponentRequirement(
                        product_id=int(req_data["product_id"]),
                        product_sku=str(req_data["product_sku"]),
                        product_name=str(req_data["product_name"]),
                        bom_level=int(req_data["bom_level"]),
                        gross_quantity=Decimal(str(req_data["gross_quantity"])),
                    )
                )
            
            net_requirements = mrp_service.calculate_net_requirements(component_reqs)
            
            # Add MRP shortages to items_dict
            for net_req in net_requirements:
                if net_req.net_shortage > 0:
                    product_id = net_req.product_id
                    mrp_shortage = float(net_req.net_shortage)
                    
                    if product_id in items_dict:
                        # Update existing item (already verified as non-make item)
                        items_dict[product_id]["mrp_shortage"] = mrp_shortage
                        items_dict[product_id]["shortfall"] = max(
                            items_dict[product_id]["shortfall"],
                            mrp_shortage
                        )
                        items_dict[product_id]["shortage_source"] = "both"
                    else:
                        # Add new item (not below reorder point, but has MRP shortage)
                        # Skip "make" items - those need Work Orders, not Purchase Orders
                        product = db.query(Product).filter(Product.id == product_id).first()
                        if product and product.active and product.procurement_type != 'make':
                            inv = db.query(
                                func.coalesce(func.sum(Inventory.on_hand_quantity), 0).label("on_hand"),
                                func.coalesce(func.sum(Inventory.allocated_quantity), 0).label("allocated"),
                            ).filter(Inventory.product_id == product_id).first()
                            
                            on_hand = float(inv.on_hand) if inv else 0
                            allocated = float(inv.allocated) if inv else 0
                            available = on_hand - allocated
                            
                            items_dict[product_id] = {
                                "id": product.id,
                                "sku": product.sku,
                                "name": product.name,
                                "item_type": product.item_type,
                                "procurement_type": product.procurement_type or "buy",
                                "unit": product.unit,
                                "category_name": product.item_category.name if product.item_category else None,
                                "on_hand_qty": on_hand,
                                "available_qty": available,
                                "reorder_point": float(product.reorder_point) if product.reorder_point else None,
                                "shortfall": mrp_shortage,
                                "mrp_shortage": mrp_shortage,
                                "cost": float(product.standard_cost or product.average_cost or 0),
                                "preferred_vendor_id": product.preferred_vendor_id,
                                "shortage_source": "mrp",
                            }

    # Convert to list and sort by shortfall (most critical first)
    items = list(items_dict.values())
    items.sort(key=lambda x: x["shortfall"], reverse=True)

    # Limit results
    items = items[:limit]

    # Calculate enhanced summary
    critical_count = sum(1 for i in items if i["available_qty"] <= 0)
    urgent_count = sum(1 for i in items if i["reorder_point"] and 0 < i["available_qty"] <= i["reorder_point"] * 0.5)
    low_count = sum(1 for i in items if i["reorder_point"] and i["available_qty"] > i["reorder_point"] * 0.5)
    mrp_shortage_count = sum(1 for i in items if i["mrp_shortage"] > 0)
    total_shortfall_value = sum(i["shortfall"] * i["cost"] for i in items)

    return {
        "items": items,
        "count": len(items),
        "summary": {
            "total_items_low": len(items),
            "critical_count": critical_count,  # Zero or negative stock
            "urgent_count": urgent_count,  # Less than 50% of reorder point
            "low_count": low_count,  # Above 50% but below reorder point
            "mrp_shortage_count": mrp_shortage_count,  # Items with MRP-driven shortages
            "total_shortfall_value": total_shortfall_value,
        }
    }


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific item by ID"""
    item = db.query(Product).options(
        joinedload(Product.item_category)
    ).filter(Product.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    return _build_item_response(item, db)


@router.get("/sku/{sku}", response_model=ItemResponse)
async def get_item_by_sku(
    sku: str,
    db: Session = Depends(get_db),
):
    """Get a specific item by SKU"""
    item = db.query(Product).options(
        joinedload(Product.item_category)
    ).filter(Product.sku == sku.upper()).first()

    if not item:
        raise HTTPException(status_code=404, detail=f"Item with SKU '{sku}' not found")

    return _build_item_response(item, db)


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    request: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing item"""
    item = db.query(Product).filter(Product.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    # Check for SKU conflict if changing
    if request.sku and request.sku.upper() != item.sku:
        existing = db.query(Product).filter(Product.sku == request.sku.upper()).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"SKU '{request.sku}' already exists")

    # Validate category if changing
    if request.category_id is not None and request.category_id != item.category_id:
        if request.category_id:
            category = db.query(ItemCategory).filter(ItemCategory.id == request.category_id).first()
            if not category:
                raise HTTPException(status_code=400, detail=f"Category {request.category_id} not found")

    # Check if unit is changing - need to convert inventory quantities
    old_unit = item.unit
    unit_changing = False
    if request.unit and request.unit.upper() != (old_unit or "").upper():
        unit_changing = True
        new_unit = request.unit.upper().strip()
        old_unit_normalized = (old_unit or "EA").upper().strip()
        
        # Convert all inventory quantities to new unit
        if old_unit_normalized != new_unit:
            from app.services.uom_service import convert_quantity_safe
            from app.models.inventory import InventoryLocation
            
            # Get all inventory records for this product
            inventory_records = db.query(Inventory).filter(
                Inventory.product_id == item.id
            ).all()
            
            if inventory_records:
                # Check if conversion is possible
                test_qty = Decimal("1")
                converted_test, can_convert = convert_quantity_safe(
                    db, test_qty, old_unit_normalized, new_unit
                )
                
                if not can_convert:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Cannot change unit from {old_unit} to {new_unit}. "
                            f"Units are incompatible. Existing inventory would be invalidated."
                        )
                    )
                
                # Convert all inventory quantities
                for inv in inventory_records:
                    if inv.on_hand_quantity and inv.on_hand_quantity > 0:
                        converted_qty, success = convert_quantity_safe(
                            db, inv.on_hand_quantity, old_unit_normalized, new_unit
                        )
                        if success:
                            inv.on_hand_quantity = converted_qty
                            logger.info(
                                f"Converted inventory for {item.sku}: "
                                f"{inv.on_hand_quantity} {old_unit} -> {converted_qty} {new_unit}"
                            )
                    
                    if inv.allocated_quantity and inv.allocated_quantity > 0:
                        converted_allocated, success = convert_quantity_safe(
                            db, inv.allocated_quantity, old_unit_normalized, new_unit
                        )
                        if success:
                            inv.allocated_quantity = converted_allocated
                    
                    inv.updated_at = datetime.utcnow()
                
                logger.info(
                    f"Converted {len(inventory_records)} inventory records for {item.sku} "
                    f"from {old_unit} to {new_unit}"
                )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "sku" and value:
            value = value.upper()
        if field == "item_type" and value:
            value = value.value if hasattr(value, "value") else value
        if field == "procurement_type" and value:
            value = value.value if hasattr(value, "value") else value
        if field == "cost_method" and value:
            value = value.value if hasattr(value, "value") else value
        if field == "is_active":
            field = "active"
        setattr(item, field, value)

    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    logger.info(f"Updated item: {item.sku}")

    return _build_item_response(item, db)


@router.delete("/{item_id}")
async def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete an item (set active=False)

    Will fail if item has inventory on hand or is used in active BOMs.
    """
    item = db.query(Product).filter(Product.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    # Check for inventory
    inv = db.query(func.sum(Inventory.on_hand_quantity)).filter(
        Inventory.product_id == item_id
    ).scalar()
    if inv and float(inv) > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete item with {inv} units on hand"
        )

    # Check for active BOMs using this item
    bom_count = db.query(BOM).filter(
        BOM.product_id == item_id,
        BOM.active.is_(True)
    ).count()
    if bom_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete item used in {bom_count} active BOMs"
        )

    item.active = False
    item.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Deleted (deactivated) item: {item.sku}")

    return {"message": f"Item {item.sku} deleted"}


# ============================================================================
# Bulk Operations
# ============================================================================

@router.post("/import", response_model=ItemCSVImportResult)
async def import_items_csv(
    file: UploadFile = File(...),
    update_existing: bool = Query(False, description="Update items if SKU exists"),
    default_item_type: str = Query("finished_good", description="Default item type"),
    default_category_id: Optional[int] = Query(None, description="Default category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import items from CSV file

    Expected columns: sku, name, description, unit, item_type, category_id,
    standard_cost, selling_price, reorder_point, upc
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    result = ItemCSVImportResult(
        total_rows=0,
        created=0,
        updated=0,
        skipped=0,
        errors=[],
    )

    # Marketplace column mappings for SKU
    SKU_COLUMNS = [
        # Standard variations
        "sku", "SKU", "Sku", "product_sku", "Product SKU", "product-sku",
        # Shopify
        "Variant SKU", "variant_sku", "variant-sku", "VariantSKU",
        # TikTok Shop
        "SKU Code", "sku_code", "sku-code", "SKUCode",
        # Amazon (ASIN can be used as SKU)
        "ASIN", "asin", "Amazon ASIN",
        # Generic
        "Product Code", "product_code", "product-code",
        "Item SKU", "item_sku", "item-sku",
        "Product ID", "product_id", "product-id",
    ]
    
    # Marketplace column mappings for Name
    NAME_COLUMNS = [
        # Standard variations
        "name", "Name", "product_name", "Product Name", "product-name",
        # Squarespace
        "title", "Title", "Product Title", "product-title",
        # Shopify
        "Variant Title", "variant_title", "variant-title", "VariantTitle",
        # TikTok Shop
        "Product Title", "product_title", "product-title", "ProductTitle",
        # Amazon
        "Title", "title", "Product Title",
        # Generic
        "Item Name", "item_name", "item-name",
        "Product Name", "product-name",
    ]
    
    # Marketplace column mappings for Description
    DESCRIPTION_COLUMNS = [
        # Standard variations
        "description", "Description", "product_description", "Product Description",
        # Shopify
        "Body (HTML)", "body_html", "Body", "body", "Body HTML",
        # WooCommerce
        "Short Description", "short_description", "short-description", "Short description",
        "Description", "description",  # WooCommerce also has Description
        # Generic
        "Long Description", "long_description", "long-description",
        "Product Description", "product-description",
        "Item Description", "item_description",
    ]
    
    # Marketplace column mappings for Price
    PRICE_COLUMNS = [
        # Standard variations
        "selling_price", "Selling Price", "selling-price",
        "price", "Price",  # Squarespace, Generic
        # Shopify
        "Variant Price", "variant_price", "variant-price", "VariantPrice",
        "Variant Compare At Price", "variant_compare_at_price", "variant-compare-at-price",  # Original price
        # WooCommerce (Sale price takes priority)
        "Sale price", "sale_price", "sale-price", "Sale Price",
        "Regular price", "regular_price", "regular-price", "Regular Price",
        # TikTok Shop
        "Unit Price", "unit_price", "unit-price", "UnitPrice",
        # Generic
        "Retail Price", "retail_price", "retail-price",
        "List Price", "list_price", "list-price",
        "Selling Price", "selling-price",
    ]
    
    # Marketplace column mappings for Cost
    COST_COLUMNS = [
        # Standard variations
        "standard_cost", "Standard Cost", "standard-cost",
        "cost", "Cost",  # Squarespace, Generic
        # Shopify
        "Variant Cost", "variant_cost", "variant-cost", "VariantCost",
        # Squarespace
        "Wholesale Price", "wholesale_price", "wholesale-price",
        # TikTok Shop
        "Cost Price", "cost_price", "cost-price", "CostPrice",
        # Amazon Business
        "Purchase PPU", "purchase_ppu", "purchase-ppu",  # Per unit price
        "Item Subtotal", "item_subtotal",  # Could be cost
        # Generic
        "Purchase Cost", "purchase_cost", "purchase-cost",
        "Unit Cost", "unit_cost", "unit-cost",
        "Wholesale Cost", "wholesale_cost",
    ]

    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1

        try:
            # Find SKU using all possible column names
            sku = ""
            for col in SKU_COLUMNS:
                if row.get(col, "").strip():
                    sku = row.get(col, "").strip().upper()
                    break
            
            if not sku:
                result.errors.append({
                    "row": row_num, 
                    "error": "SKU is required. Looked for: sku, SKU, Variant SKU, Product SKU, etc."
                })
                result.skipped += 1
                continue

            # Find name using all possible column names
            name = ""
            for col in NAME_COLUMNS:
                if row.get(col, "").strip():
                    name = row.get(col, "").strip()
                    break
            
            if not name:
                result.errors.append({
                    "row": row_num, 
                    "error": "Name is required. Looked for: name, title, Product Name, Variant Title, etc.",
                    "sku": sku
                })
                result.skipped += 1
                continue

            # Check if exists
            existing = db.query(Product).filter(Product.sku == sku).first()

            if existing:
                # Protect seeded example items from being overwritten
                if existing.sku.startswith("SEED-EXAMPLE-"):
                    result.errors.append({
                        "row": row_num,
                        "error": f"SKU '{sku}' is a seeded example item and cannot be overwritten. Please use a different SKU.",
                        "sku": sku
                    })
                    result.skipped += 1
                    continue
                
                if not update_existing:
                    result.skipped += 1
                    continue

                # Update existing - use same column detection logic
                existing.name = name
                
                # Update description
                for col in DESCRIPTION_COLUMNS:
                    value = row.get(col, "").strip()
                    if value:
                        if "<" in value and ">" in value:
                            import re
                            existing.description = re.sub(r'<[^>]+>', '', value).strip()
                        else:
                            existing.description = value
                        break
                
                # Update unit
                unit = (row.get("unit", "") or row.get("Unit", "") or row.get("UOM", "")).strip()
                if unit:
                    existing.unit = unit
                
                # Update item type
                item_type_raw = (row.get("item_type", "") or row.get("Item Type", "") or row.get("Type", "")).strip()
                if item_type_raw:
                    item_type_map = {
                        "simple": "finished_good",
                        "variable": "finished_good",
                        "finished_good": "finished_good",
                        "component": "component",
                        "supply": "supply",
                        "service": "service",
                    }
                    existing.item_type = item_type_map.get(item_type_raw.lower(), existing.item_type)
                
                # Update category - handle all marketplace formats
                category_id_raw = (
                    row.get("category_id", "") or
                    row.get("Category ID", "") or
                    row.get("category-id", "")
                ).strip()
                if category_id_raw:
                    try:
                        existing.category_id = int(category_id_raw)
                    except ValueError:
                        pass
                else:
                    # Try category name (Squarespace, WooCommerce, etc.)
                    category_name_raw = (
                        row.get("Category", "") or
                        row.get("category", "") or
                        row.get("Categories", "") or  # WooCommerce (comma-separated)
                        row.get("Product Category", "") or
                        row.get("Type", "") or  # Shopify uses Type
                        row.get("Product Type", "")
                    ).strip()
                    
                    if category_name_raw:
                        # Handle WooCommerce comma-separated categories (take first)
                        if "," in category_name_raw:
                            category_name_raw = category_name_raw.split(",")[0].strip()
                        
                        # Try to find category by name (if categories exist)
                        from app.models.item_category import ItemCategory
                        category = db.query(ItemCategory).filter(
                            ItemCategory.name.ilike(f"%{category_name_raw}%")
                        ).first()
                        if category:
                            existing.category_id = category.id
                
                # Update cost
                cost_raw = ""
                for col in COST_COLUMNS:
                    if row.get(col, "").strip():
                        cost_raw = row.get(col, "").strip()
                        break
                if cost_raw:
                    cost_clean = cost_raw.replace("$", "").replace(",", "").replace("€", "").replace("£", "").strip()
                    try:
                        existing.standard_cost = float(cost_clean)
                    except ValueError:
                        pass
                
                # Update price
                selling_price_raw = ""
                for col in PRICE_COLUMNS:
                    value = row.get(col, "").strip()
                    if value:
                        if "sale" in col.lower() and value:
                            selling_price_raw = value
                            break
                        elif not selling_price_raw:
                            selling_price_raw = value
                if selling_price_raw:
                    price_clean = selling_price_raw.replace("$", "").replace(",", "").replace("€", "").replace("£", "").strip()
                    try:
                        existing.selling_price = float(price_clean)
                    except ValueError:
                        pass
                
                # Update reorder point
                if row.get("reorder_point"):
                    try:
                        existing.reorder_point = float(row["reorder_point"])
                    except ValueError:
                        pass
                
                # Update UPC - handle all marketplace formats
                upc = (
                    row.get("upc", "") or 
                    row.get("UPC", "") or
                    row.get("barcode", "") or
                    row.get("Barcode", "") or
                    row.get("EAN", "") or
                    row.get("GTIN", "") or
                    row.get("Product Code", "") or  # TikTok Shop
                    row.get("product_code", "") or
                    row.get("ASIN", "") or  # Amazon ASIN
                    row.get("asin", "")
                ).strip()
                if upc:
                    existing.upc = upc
                
                existing.updated_at = datetime.utcnow()
                result.updated += 1
            else:
                # Find price using all possible column names
                # Priority: Sale price (if exists) > Regular price > Variant price > Price
                selling_price_raw = ""
                for col in PRICE_COLUMNS:
                    value = row.get(col, "").strip()
                    if value:
                        # Prefer sale price if available (WooCommerce)
                        if "sale" in col.lower() and value:
                            selling_price_raw = value
                            break
                        elif not selling_price_raw:  # Use first found as fallback
                            selling_price_raw = value
                
                selling_price = None
                if selling_price_raw:
                    # Remove $ signs, commas, and currency symbols
                    selling_price_clean = selling_price_raw.replace("$", "").replace(",", "").replace("€", "").replace("£", "").strip()
                    try:
                        selling_price = float(selling_price_clean)
                    except ValueError:
                        result.errors.append({
                            "row": row_num, 
                            "error": f"Invalid price format: {selling_price_raw}", 
                            "sku": sku
                        })
                
                # Find cost using all possible column names
                cost_raw = ""
                for col in COST_COLUMNS:
                    if row.get(col, "").strip():
                        cost_raw = row.get(col, "").strip()
                        break
                
                standard_cost = None
                if cost_raw:
                    # Remove $ signs, commas, and currency symbols
                    cost_clean = cost_raw.replace("$", "").replace(",", "").replace("€", "").replace("£", "").strip()
                    try:
                        standard_cost = float(cost_clean)
                    except ValueError:
                        pass  # Cost is optional, just skip if invalid
                
                # Find description using all possible column names
                description = None
                for col in DESCRIPTION_COLUMNS:
                    value = row.get(col, "").strip()
                    if value:
                        # Strip HTML tags if present (Shopify exports HTML)
                        if "<" in value and ">" in value:
                            import re
                            description = re.sub(r'<[^>]+>', '', value).strip()
                        else:
                            description = value
                        break
                
                # Handle category - can be ID or name (all marketplace formats)
                final_category_id = default_category_id
                # Try category_id first (numeric)
                category_id_raw = (
                    row.get("category_id", "") or
                    row.get("Category ID", "") or
                    row.get("category-id", "")
                ).strip()
                if category_id_raw:
                    try:
                        final_category_id = int(category_id_raw)
                    except ValueError:
                        pass
                
                # If no numeric ID, try category name (Squarespace, WooCommerce, etc.)
                if not final_category_id or final_category_id == default_category_id:
                    category_name_raw = (
                        row.get("Category", "") or
                        row.get("category", "") or
                        row.get("Categories", "") or  # WooCommerce (comma-separated)
                        row.get("Product Category", "") or
                        row.get("Type", "") or  # Shopify uses Type
                        row.get("Product Type", "")
                    ).strip()
                    
                    if category_name_raw:
                        # Handle WooCommerce comma-separated categories (take first)
                        if "," in category_name_raw:
                            category_name_raw = category_name_raw.split(",")[0].strip()
                        
                        # Try to find category by name (if categories exist)
                        from app.models.item_category import ItemCategory
                        category = db.query(ItemCategory).filter(
                            ItemCategory.name.ilike(f"%{category_name_raw}%")
                        ).first()
                        if category:
                            final_category_id = category.id
                
                # Create new
                item = Product(
                    sku=sku,
                    name=name,
                    description=description,
                    unit=row.get("unit", "") or row.get("Unit", "") or "EA",
                    item_type=(row.get("item_type", "") or row.get("Item Type", "")).strip() or default_item_type,
                    category_id=final_category_id,
                    standard_cost=standard_cost,
                    selling_price=selling_price,
                    reorder_point=float(row["reorder_point"]) if row.get("reorder_point") else None,
                    upc=(row.get("upc", "") or row.get("UPC", "") or row.get("barcode", "") or row.get("Barcode", "") or row.get("EAN", "") or row.get("GTIN", "") or row.get("Product Code", "") or row.get("product_code", "") or row.get("ASIN", "") or row.get("asin", "")).strip() or None,
                    active=True,
                )
                db.add(item)
                result.created += 1

        except Exception as e:
            result.errors.append({"row": row_num, "error": str(e), "sku": row.get("sku", "")})
            result.skipped += 1

    db.commit()

    logger.info(f"CSV import complete: {result.created} created, {result.updated} updated, {result.skipped} skipped")

    return result


@router.post("/bulk-update")
async def bulk_update_items(
    request: ItemBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk update multiple items at once"""
    if not request.item_ids:
        raise HTTPException(status_code=400, detail="No items specified")

    # Validate category if provided
    if request.category_id:
        category = db.query(ItemCategory).filter(ItemCategory.id == request.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail=f"Category {request.category_id} not found")

    updated = 0
    errors = []
    
    for item_id in request.item_ids:
        item = db.query(Product).filter(Product.id == item_id).first()
        if not item:
            errors.append({"item_id": item_id, "error": "Item not found"})
            continue
            
        try:
            if request.category_id is not None:
                # Allow setting to None (0) to clear category
                if request.category_id == 0:
                    item.category_id = None
                else:
                    item.category_id = request.category_id
            if request.item_type is not None:
                # Handle both enum and string values
                item_type_value = request.item_type
                if hasattr(item_type_value, 'value'):
                    item_type_value = item_type_value.value
                # Validate item type
                valid_item_types = ['finished_good', 'component', 'supply', 'service']
                if item_type_value in valid_item_types:
                    item.item_type = item_type_value
                else:
                    raise ValueError(f"Invalid item_type: {item_type_value}")
            if request.procurement_type is not None:
                # Handle both enum and string values
                proc_type_value = request.procurement_type
                if hasattr(proc_type_value, 'value'):
                    proc_type_value = proc_type_value.value
                # Validate procurement type
                valid_proc_types = ['make', 'buy', 'make_or_buy']
                if proc_type_value in valid_proc_types:
                    item.procurement_type = proc_type_value
                else:
                    raise ValueError(f"Invalid procurement_type: {proc_type_value}")
            if request.is_active is not None:
                item.active = request.is_active
            item.updated_at = datetime.utcnow()
            updated += 1
        except Exception as e:
            errors.append({"item_id": item_id, "error": str(e)})

    db.commit()

    logger.info(f"Bulk update: {updated} items updated, {len(errors)} errors")

    return {
        "message": f"{updated} items updated",
        "updated_count": updated,
        "error_count": len(errors),
        "errors": errors
    }


# ============================================================================
# Recost Operations
# ============================================================================

def _recalculate_bom_cost(bom: BOM, db: Session) -> Decimal:
    """
    Recalculate BOM total cost from component standard_costs.

    For each BOM line:
      line_cost = component.standard_cost * quantity * (1 + scrap_factor/100)

    Handles UOM conversion when BOM line unit differs from component unit.
    E.g., if BOM line uses 25 G but component is priced per KG, converts 25 G to 0.025 KG.

    Updates bom.total_cost and returns the new value.
    """
    total = Decimal("0")

    # Get all BOM lines (BOMLine doesn't have active flag - only BOM does)
    lines = db.query(BOMLine).filter(
        BOMLine.bom_id == bom.id
    ).all()

    for line in lines:
        component = db.query(Product).filter(Product.id == line.component_id).first()
        if component:
            # Use standard_cost, fall back to average_cost, then last_cost
            component_cost = component.standard_cost or component.average_cost or component.last_cost
            if component_cost:
                qty = line.quantity or Decimal("0")
                scrap = line.scrap_factor or Decimal("0")
                effective_qty = qty * (1 + scrap / 100)

                # Handle UOM conversion: BOM line unit -> component unit
                component_unit = component.unit
                line_unit = line.unit

                if line_unit and component_unit and line_unit.upper() != component_unit.upper():
                    # Use inline conversion (more reliable than database lookup)
                    converted_qty = convert_uom_inline(effective_qty, line_unit, component_unit)
                    total += Decimal(str(component_cost)) * converted_qty
                else:
                    # Same unit or no unit specified, direct multiply
                    total += Decimal(str(component_cost)) * effective_qty

    # Update the BOM total_cost
    bom.total_cost = total
    bom.updated_at = datetime.utcnow()

    return total


def _calculate_item_cost(item: Product, db: Session) -> dict:
    """
    Calculate standard cost for an item.

    For manufactured items (with BOM):
      1. Recalculate BOM cost from component standard_costs
      2. Add Routing process cost
    For purchased items (no BOM):
      Use average_cost or last_cost from purchases

    Returns a dict with breakdown.
    """
    bom_cost = 0.0
    routing_cost = 0.0
    purchase_cost = 0.0
    bom_id = None
    routing_id = None
    cost_source = None

    # Check for active BOM (indicates manufactured item)
    bom = db.query(BOM).filter(
        BOM.product_id == item.id,
        BOM.active.is_(True)
    ).first()

    if bom:
        # Manufactured item: recalculate BOM + add Routing
        cost_source = "manufactured"
        bom_id = bom.id

        # Recalculate BOM cost from component standard_costs
        bom_cost = float(_recalculate_bom_cost(bom, db))

        # Get active Routing cost
        routing = db.query(Routing).filter(
            Routing.product_id == item.id,
            Routing.is_active.is_(True)
        ).first()
        if routing and routing.total_cost:
            routing_cost = float(routing.total_cost)
            routing_id = routing.id

        total_cost = bom_cost + routing_cost
    else:
        # Purchased item: use average_cost, fall back to last_cost
        cost_source = "purchased"
        if item.average_cost:
            purchase_cost = float(item.average_cost)
        elif item.last_cost:
            purchase_cost = float(item.last_cost)

        total_cost = purchase_cost

    return {
        "bom_id": bom_id,
        "bom_cost": bom_cost,
        "routing_id": routing_id,
        "routing_cost": routing_cost,
        "purchase_cost": purchase_cost,
        "total_cost": total_cost,
        "cost_source": cost_source,
    }


@router.post("/recost-all")
async def recost_all_items(
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    cost_source: Optional[str] = Query(None, description="Filter: 'manufactured' or 'purchased'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recost all items matching filters.

    - Manufactured items (with BOM): BOM cost + Routing cost
    - Purchased items (no BOM): Uses average_cost or last_cost from purchases

    - **item_type**: Filter by item type (e.g., 'finished_good', 'raw_material')
    - **category_id**: Filter by category (includes descendants)
    - **cost_source**: Filter by 'manufactured' (has BOM) or 'purchased' (no BOM)
    """
    query = db.query(Product).filter(Product.active.is_(True))  # noqa: E712

    if item_type:
        query = query.filter(Product.item_type == item_type)

    if category_id:
        category_ids = _get_category_and_descendants(db, category_id)
        query = query.filter(Product.category_id.in_(category_ids))

    items = query.all()

    updated = 0
    skipped = 0
    results = []

    for item in items:
        cost_data = _calculate_item_cost(item, db)

        # Filter by cost source if specified
        if cost_source and cost_data["cost_source"] != cost_source:
            continue

        # Skip if no cost to set
        if cost_data["total_cost"] == 0:
            skipped += 1
            continue

        # Update standard cost
        old_cost = float(item.standard_cost) if item.standard_cost else 0
        item.standard_cost = cost_data["total_cost"]
        item.updated_at = datetime.utcnow()
        updated += 1

        results.append({
            "id": item.id,
            "sku": item.sku,
            "old_cost": old_cost,
            "new_cost": cost_data["total_cost"],
            "cost_source": cost_data["cost_source"],
            "bom_cost": cost_data["bom_cost"],
            "routing_cost": cost_data["routing_cost"],
            "purchase_cost": cost_data["purchase_cost"],
        })

    db.commit()

    logger.info(f"Recost all: {updated} items updated, {skipped} skipped")

    return {
        "updated": updated,
        "skipped": skipped,
        "items": results,
    }


@router.post("/{item_id}/recost")
async def recost_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recost a single item.

    - Manufactured items (with BOM): BOM cost + Routing cost
    - Purchased items (no BOM): Uses average_cost or last_cost
    """
    item = db.query(Product).filter(Product.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    cost_data = _calculate_item_cost(item, db)

    old_cost = float(item.standard_cost) if item.standard_cost else 0
    item.standard_cost = cost_data["total_cost"]
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    logger.info(f"Recost item {item.sku}: ${old_cost:.4f} -> ${cost_data['total_cost']:.4f}")

    return {
        "id": item.id,
        "sku": item.sku,
        "name": item.name,
        "old_cost": old_cost,
        "new_cost": cost_data["total_cost"],
        "cost_source": cost_data["cost_source"],
        "bom_id": cost_data["bom_id"],
        "bom_cost": cost_data["bom_cost"],
        "routing_id": cost_data["routing_id"],
        "routing_cost": cost_data["routing_cost"],
        "purchase_cost": cost_data["purchase_cost"],
        "message": f"Standard cost updated: ${old_cost:.4f} -> ${cost_data['total_cost']:.4f}",
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _get_category_and_descendants(db: Session, category_id: int) -> list[int]:
    """
    Get a category ID and all its descendant category IDs.
    Used for filtering items by category hierarchy.
    """
    result = [category_id]

    # Get direct children
    children = db.query(ItemCategory.id).filter(
        ItemCategory.parent_id == category_id
    ).all()

    # Recursively get descendants
    for (child_id,) in children:
        result.extend(_get_category_and_descendants(db, child_id))

    return result


def _build_item_response(item: Product, db: Session) -> ItemResponse:
    """Build full item response with inventory and BOM info"""
    # Get inventory totals
    inv = db.query(
        func.coalesce(func.sum(Inventory.on_hand_quantity), 0).label("on_hand"),
        func.coalesce(func.sum(Inventory.allocated_quantity), 0).label("allocated"),
    ).filter(Inventory.product_id == item.id).first()

    on_hand = float(inv.on_hand) if inv else 0
    allocated = float(inv.allocated) if inv else 0

    # Get BOM count
    bom_count = db.query(BOM).filter(BOM.product_id == item.id, BOM.active.is_(True)).count()  # noqa: E712

    return ItemResponse(
        id=item.id,
        sku=item.sku,
        name=item.name,
        description=item.description,
        unit=item.unit,
        item_type=ItemType(item.item_type) if item.item_type else ItemType.FINISHED_GOOD,
        procurement_type=ProcurementType(item.procurement_type) if item.procurement_type else ProcurementType.BUY,
        category_id=item.category_id,
        cost_method=item.cost_method or "average",
        standard_cost=item.standard_cost,
        average_cost=item.average_cost,
        last_cost=item.last_cost,
        selling_price=item.selling_price,
        weight_oz=item.weight_oz,
        length_in=item.length_in,
        width_in=item.width_in,
        height_in=item.height_in,
        lead_time_days=item.lead_time_days,
        min_order_qty=item.min_order_qty,
        reorder_point=item.reorder_point,
        upc=item.upc,
        legacy_sku=item.legacy_sku,
        active=item.active,
        is_raw_material=item.is_raw_material,
        track_lots=item.track_lots,
        track_serials=item.track_serials,
        category_name=item.item_category.name if item.item_category else None,
        category_path=item.item_category.full_path if item.item_category else None,
        on_hand_qty=on_hand,
        available_qty=on_hand - allocated,
        allocated_qty=allocated,
        has_bom=item.has_bom or bom_count > 0,
        bom_count=bom_count,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
