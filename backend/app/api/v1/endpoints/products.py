"""
Products API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.product import Product
from app.models.user import User
from app.logging_config import get_logger
from app.api.v1.deps import get_current_user
from app.services.operation_generation import get_product_routing_details
from app.schemas.routing_operations import (
    ProductRoutingResponse,
    RoutingOperationInfo,
)

router = APIRouter()
logger = get_logger(__name__)


def _product_has_transactions(db: Session, product_id: int) -> tuple[bool, str]:
    """
    Check if product has any transactional history that would prevent SKU changes.

    SKU changes are blocked once a product has:
    - Purchase order lines (PO history)
    - Inventory transactions (receipt/issue history)
    - Material lots (lot tracking history)

    Returns:
        tuple: (has_transactions: bool, reason: str)
    """
    from app.models.purchase_order import PurchaseOrderLine
    from app.models.inventory import InventoryTransaction
    from app.models.traceability import MaterialLot

    # Check purchase order lines
    po_lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.product_id == product_id).count()
    if po_lines > 0:
        return True, f"Product has {po_lines} purchase order line(s)"

    # Check inventory transactions
    inv_txns = db.query(InventoryTransaction).filter(InventoryTransaction.product_id == product_id).count()
    if inv_txns > 0:
        return True, f"Product has {inv_txns} inventory transaction(s)"

    # Check material lots
    lots = db.query(MaterialLot).filter(MaterialLot.product_id == product_id).count()
    if lots > 0:
        return True, f"Product has {lots} material lot(s)"

    return False, ""


class ProductCreate(BaseModel):
    """Create product request"""

    sku: str
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None  # FK to ItemCategory
    unit: str = "EA"
    standard_cost: Optional[float] = None  # Use standard_cost instead of legacy 'cost'
    selling_price: Optional[float] = None
    is_raw_material: bool = False
    active: bool = True


class ProductUpdate(BaseModel):
    """Update product request"""

    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None  # FK to ItemCategory
    unit: Optional[str] = None
    standard_cost: Optional[float] = None  # Use standard_cost instead of legacy 'cost'
    selling_price: Optional[float] = None
    is_raw_material: Optional[bool] = None
    active: Optional[bool] = None


class ProductResponse(BaseModel):
    """Product response"""

    id: int
    sku: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit: str
    cost: Optional[float] = None
    selling_price: Optional[float] = None
    weight: Optional[float] = None
    is_raw_material: bool
    has_bom: bool
    active: bool
    woocommerce_product_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Product list response"""

    total: int
    items: List[ProductResponse]


@router.get("", response_model=ProductListResponse)
async def list_products(
    category: Optional[str] = None,
    active_only: bool = True,
    search: Optional[str] = None,
    has_bom: Optional[bool] = None,
    procurement_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List products with optional filtering

    - **category**: Filter by category (e.g., 'Finished Goods', 'Raw Materials')
    - **active_only**: Only show active products (default: True)
    - **search**: Search by SKU or name
    - **has_bom**: Filter by whether product has a BOM (True/False)
    - **procurement_type**: Filter by procurement type ('make', 'buy', 'make_or_buy')
    - **limit**: Max results (default: 50)
    - **offset**: Pagination offset (default: 0)
    """
    try:
        # Build query
        query = db.query(Product)

        # Apply filters
        if active_only:
            query = query.filter(Product.active.is_(True))  # noqa: E712

        if category:
            # Filter by category name through ItemCategory relationship
            from app.models.item_category import ItemCategory

            query = query.join(ItemCategory, Product.category_id == ItemCategory.id).filter(
                ItemCategory.name.ilike(f"%{category}%")
            )

        if has_bom is not None:
            query = query.filter(Product.has_bom == has_bom)  # noqa: E712

        if procurement_type:
            query = query.filter(Product.procurement_type == procurement_type)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter((Product.sku.like(search_pattern)) | (Product.name.like(search_pattern)))

        # Get total count
        total = query.count()

        # Get paginated results
        products = query.order_by(Product.id).offset(offset).limit(limit).all()

        return ProductListResponse(total=total, items=[ProductResponse.from_orm(p) for p in products])

    except Exception as e:
        logger.error(f"Failed to list products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}", response_model=ProductResponse)
async def get_product(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a specific product by ID"""
    try:
        product = db.query(Product).filter(Product.id == id).first()

        if not product:
            raise HTTPException(status_code=404, detail=f"Product {id} not found")

        return ProductResponse.from_orm(product)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sku/{sku}", response_model=ProductResponse)
async def get_product_by_sku(sku: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a specific product by SKU"""
    try:
        product = db.query(Product).filter(Product.sku == sku).first()

        if not product:
            raise HTTPException(status_code=404, detail=f"Product with SKU {sku} not found")

        return ProductResponse.from_orm(product)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ProductResponse)
async def create_product(
    request: ProductCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Create a new product"""
    try:
        # Check if SKU already exists
        existing = db.query(Product).filter(Product.sku == request.sku).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Product with SKU '{request.sku}' already exists")

        # Create product
        product = Product(
            sku=request.sku,
            name=request.name,
            description=request.description,
            category_id=request.category_id,
            unit=request.unit,
            standard_cost=request.standard_cost,
            selling_price=request.selling_price,
            is_raw_material=request.is_raw_material,
            active=request.active,
        )

        db.add(product)
        db.commit()
        db.refresh(product)

        logger.info(f"Created product: {product.sku}")
        return ProductResponse.from_orm(product)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{id}", response_model=ProductResponse)
async def update_product(
    id: int, request: ProductUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Update an existing product"""
    try:
        product = db.query(Product).filter(Product.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {id} not found")

        # Check SKU uniqueness if changing
        if request.sku and request.sku != product.sku:
            # Prevent SKU changes on products with transactional history
            has_txns, reason = _product_has_transactions(db, id)
            if has_txns:
                raise HTTPException(
                    status_code=400, detail=f"Cannot change SKU: {reason}. Create a new product instead."
                )

            # Check uniqueness
            existing = db.query(Product).filter(Product.sku == request.sku).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Product with SKU '{request.sku}' already exists")

        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)

        db.commit()
        db.refresh(product)

        logger.info(f"Updated product: {product.sku}")
        return ProductResponse.from_orm(product)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Product Routing Endpoint (API-404)
# =============================================================================


@router.get("/{product_id}/routing", response_model=ProductRoutingResponse, summary="Get routing for a product")
def get_product_routing(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get routing details for a product."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    routing_info = get_product_routing_details(db, product_id)

    if not routing_info:
        return ProductRoutingResponse(product_id=product_id, routing_id=None, operations=[])

    return ProductRoutingResponse(
        product_id=product_id,
        routing_id=routing_info["routing_id"],
        routing_code=routing_info["routing_code"],
        routing_name=routing_info["routing_name"],
        is_active=routing_info["is_active"],
        operations=[RoutingOperationInfo(**op) for op in routing_info["operations"]],
    )
