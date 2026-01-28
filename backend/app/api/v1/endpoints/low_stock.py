"""
Low Stock → PO Workflow API Endpoints

Streamlined workflow for creating purchase orders from low-stock items:
- Get low-stock items grouped by preferred vendor
- Create PO with pre-populated items
"""

from decimal import Decimal
from typing import Optional
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.logging_config import get_logger
from app.models.product import Product
from app.models.vendor import Vendor
from app.models.inventory import Inventory
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.endpoints.purchase_orders import create_purchase_order
from app.models.user import User
from app.schemas.purchasing import (
    LowStockItem,
    LowStockByVendor,
    LowStockResponse,
    CreatePOFromLowStockRequest,
    CreatePOFromLowStockItem,
    PurchaseOrderCreate,
    POLineCreate,
    PurchaseOrderResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/low-stock", response_model=LowStockResponse)
async def get_low_stock_items(
    group_by_vendor: bool = Query(True, description="Group items by preferred vendor"),
    include_no_vendor: bool = Query(True, description="Include items with no preferred vendor"),
    db: Session = Depends(get_db),
):
    """
    Get all products below their reorder point, grouped by preferred vendor

    This powers the "Low Stock" tab in the purchasing module with
    one-click PO creation capability.

    Returns items grouped by vendor with:
    - Current quantity vs reorder point
    - Suggested order quantity (reorder_qty)
    - Last purchase cost for estimation
    """
    # Query products with inventory data
    # Get total on-hand across all locations
    inventory_subquery = (
        db.query(Inventory.product_id, func.sum(Inventory.on_hand_quantity).label("total_on_hand"))
        .group_by(Inventory.product_id)
        .subquery()
    )

    # Get products below reorder point
    low_stock_query = (
        db.query(Product, func.coalesce(inventory_subquery.c.total_on_hand, 0).label("on_hand"))
        .outerjoin(inventory_subquery, Product.id == inventory_subquery.c.product_id)
        .filter(
            Product.is_active.is_(True),
            Product.reorder_point.isnot(None),
            Product.reorder_point > 0,
        )
    )

    results = low_stock_query.all()

    # Filter to items actually below reorder point
    low_stock_items = []
    for product, on_hand in results:
        on_hand_decimal = Decimal(str(on_hand or 0))
        reorder_point = Decimal(str(product.reorder_point or 0))

        if on_hand_decimal < reorder_point:
            shortage = reorder_point - on_hand_decimal
            reorder_qty = Decimal(str(product.reorder_quantity or shortage))

            # Get preferred vendor name
            vendor_name = None
            if product.preferred_vendor_id:
                vendor = db.query(Vendor).filter(Vendor.id == product.preferred_vendor_id).first()
                if vendor:
                    vendor_name = vendor.name

            low_stock_items.append(
                LowStockItem(
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    current_qty=on_hand_decimal,
                    reorder_point=reorder_point,
                    reorder_qty=reorder_qty,
                    shortage=shortage,
                    unit=product.unit or "EA",
                    purchase_uom=getattr(product, "purchase_uom", None) or product.unit,
                    last_cost=Decimal(str(product.last_cost)) if product.last_cost else None,
                    preferred_vendor_id=product.preferred_vendor_id,
                    preferred_vendor_name=vendor_name,
                )
            )

    if not group_by_vendor:
        # Return as single group
        total_cost = sum(
            (item.reorder_qty * item.last_cost) if item.last_cost else Decimal(0) for item in low_stock_items
        )
        return LowStockResponse(
            total_items=len(low_stock_items),
            vendors=[
                LowStockByVendor(
                    vendor_id=None,
                    vendor_name="All Items",
                    items=low_stock_items,
                    total_estimated_cost=total_cost,
                )
            ],
        )

    # Group by vendor
    vendor_groups = defaultdict(list)
    for item in low_stock_items:
        vendor_key = item.preferred_vendor_id or 0  # 0 for no vendor
        vendor_groups[vendor_key].append(item)

    # Build response
    vendors_response = []

    # Get vendor details
    vendor_ids = [vid for vid in vendor_groups.keys() if vid != 0]
    vendors_map = {}
    if vendor_ids:
        vendors = db.query(Vendor).filter(Vendor.id.in_(vendor_ids)).all()
        vendors_map = {v.id: v for v in vendors}

    for vendor_id, items in vendor_groups.items():
        if vendor_id == 0:
            if not include_no_vendor:
                continue
            vendor_name = "No Preferred Vendor"
            vendor_code = None
        else:
            vendor = vendors_map.get(vendor_id)
            vendor_name = vendor.name if vendor else "Unknown Vendor"
            vendor_code = vendor.code if vendor else None

        total_cost = sum((item.reorder_qty * item.last_cost) if item.last_cost else Decimal(0) for item in items)

        vendors_response.append(
            LowStockByVendor(
                vendor_id=vendor_id if vendor_id != 0 else None,
                vendor_name=vendor_name,
                vendor_code=vendor_code,
                items=items,
                total_estimated_cost=total_cost,
            )
        )

    # Sort: vendors with items first, then by item count
    vendors_response.sort(key=lambda v: (-len(v.items), v.vendor_name))

    return LowStockResponse(
        total_items=len(low_stock_items),
        vendors=vendors_response,
    )


@router.post("/from-low-stock", response_model=PurchaseOrderResponse, status_code=201)
async def create_po_from_low_stock(
    request: CreatePOFromLowStockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a purchase order from selected low-stock items

    This is the "one-click" PO creation from the low-stock view.
    Takes selected items and creates a PO with:
    - Pre-populated quantities (from reorder_qty or user override)
    - Pre-populated costs (from last_cost or user override)
    - Proper UOM handling
    """
    # Verify vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == request.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if not request.items:
        raise HTTPException(status_code=400, detail="At least one item is required")

    # Build PO lines from request
    lines = []
    for item in request.items:
        # Get product for defaults
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        # Use provided values or defaults
        unit_cost = item.unit_cost
        if unit_cost is None:
            unit_cost = Decimal(str(product.last_cost or product.standard_cost or 0))

        purchase_unit = item.purchase_unit
        if not purchase_unit:
            purchase_unit = getattr(product, "purchase_uom", None) or product.unit or "EA"

        lines.append(
            POLineCreate(
                product_id=item.product_id,
                quantity_ordered=item.quantity,
                unit_cost=unit_cost,
                purchase_unit=purchase_unit,
            )
        )

    # Create PO using existing endpoint logic
    po_request = PurchaseOrderCreate(
        vendor_id=request.vendor_id,
        notes=request.notes or "Created from low-stock items",
        lines=lines,
    )

    # Call the create function directly
    return await create_purchase_order(po_request, current_user, db)


@router.post("/quick-reorder/{product_id}", response_model=PurchaseOrderResponse, status_code=201)
async def quick_reorder_product(
    product_id: int,
    quantity: Optional[Decimal] = Query(None, description="Override quantity (default: reorder_qty)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Quick one-click reorder for a single product

    Creates a PO for the product using:
    - Preferred vendor (required)
    - Reorder quantity (or override)
    - Last purchase cost
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.preferred_vendor_id:
        raise HTTPException(status_code=400, detail=f"Product {product.sku} has no preferred vendor. Set one first.")

    order_qty = quantity or Decimal(str(product.reorder_quantity or 1))

    request = CreatePOFromLowStockRequest(
        vendor_id=product.preferred_vendor_id,
        items=[
            CreatePOFromLowStockItem(
                product_id=product_id,
                quantity=order_qty,
            )
        ],
        notes=f"Quick reorder for {product.sku}",
    )

    return await create_po_from_low_stock(request, current_user, db)
