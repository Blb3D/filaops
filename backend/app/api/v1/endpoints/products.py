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
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

class ProductCreate(BaseModel):
    """Create product request"""
    sku: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit: str = "EA"
    cost: Optional[float] = None
    selling_price: Optional[float] = None
    is_raw_material: bool = False
    active: bool = True


class ProductUpdate(BaseModel):
    """Update product request"""
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    cost: Optional[float] = None
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
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List products with optional filtering

    - **category**: Filter by category (e.g., 'Finished Goods', 'Raw Materials')
    - **active_only**: Only show active products (default: True)
    - **search**: Search by SKU or name
    - **limit**: Max results (default: 50)
    - **offset**: Pagination offset (default: 0)
    """
    try:
        # Build query
        query = db.query(Product)

        # Apply filters
        if active_only:
            query = query.filter(Product.active.is_(True))

        if category:
            query = query.filter(Product.category == category)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Product.sku.like(search_pattern)) |
                (Product.name.like(search_pattern))
            )

        # Get total count
        total = query.count()

        # Get paginated results
        products = query.order_by(Product.id).offset(offset).limit(limit).all()

        return ProductListResponse(
            total=total,
            items=[ProductResponse.from_orm(p) for p in products]
        )

    except Exception as e:
        logger.error(f"Failed to list products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id}", response_model=ProductResponse)
async def get_product(
    id: int,
    db: Session = Depends(get_db)
):
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
async def get_product_by_sku(
    sku: str,
    db: Session = Depends(get_db)
):
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
    request: ProductCreate,
    db: Session = Depends(get_db)
):
    """Create a new product"""
    try:
        # Check if SKU already exists
        existing = db.query(Product).filter(Product.sku == request.sku).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Product with SKU '{request.sku}' already exists"
            )

        # Create product
        product = Product(
            sku=request.sku,
            name=request.name,
            description=request.description,
            category=request.category,
            unit=request.unit,
            cost=request.cost,
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
    id: int,
    request: ProductUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing product"""
    try:
        product = db.query(Product).filter(Product.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {id} not found")

        # Check SKU uniqueness if changing
        if request.sku and request.sku != product.sku:
            existing = db.query(Product).filter(Product.sku == request.sku).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product with SKU '{request.sku}' already exists"
                )

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
