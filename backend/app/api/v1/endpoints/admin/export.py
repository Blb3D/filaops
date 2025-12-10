"""
Export functionality for products, orders, inventory
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io
from datetime import datetime

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_admin_user
from app.models.user import User
from app.models.product import Product
from app.models.sales_order import SalesOrder

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/products")
async def export_products(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Export products to CSV"""
    products = db.query(Product).filter(Product.active.is_(True)).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'SKU', 'Name', 'Description', 'Item Type', 'Procurement Type',
        'Unit', 'Standard Cost', 'Selling Price', 'On Hand Qty',
        'Reorder Point', 'Active'
    ])
    
    # Data rows
    for p in products:
        on_hand = sum([inv.on_hand_quantity for inv in p.inventory])
        writer.writerow([
            p.sku, p.name, p.description or '', p.item_type, p.procurement_type,
            p.unit, p.standard_cost or 0, p.selling_price or 0, on_hand,
            p.reorder_point or 0, p.active
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=products_export_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )


@router.get("/orders")
async def export_orders(
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Export sales orders to CSV"""
    query = db.query(SalesOrder)
    
    if start_date:
        query = query.filter(SalesOrder.created_at >= start_date)
    if end_date:
        query = query.filter(SalesOrder.created_at <= end_date)
    
    orders = query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Order Number', 'Customer', 'Status', 'Total', 'Created Date', 'Line Items'
    ])
    
    for order in orders:
        line_items = ', '.join([f"{line.product_sku} x{line.quantity}" for line in order.lines])
        customer_name = order.user.company_name if order.user and order.user.company_name else (
            order.user.email if order.user else 'N/A'
        )
        writer.writerow([
            order.order_number,
            customer_name,
            order.status,
            float(order.total_price) if order.total_price else 0,
            order.created_at.strftime('%Y-%m-%d') if order.created_at else '',
            line_items
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=orders_export_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )

