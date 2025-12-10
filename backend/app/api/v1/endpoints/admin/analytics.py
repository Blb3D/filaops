"""
Pro-tier analytics endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_admin_user
from app.core.features import require_tier, Tier
from app.models.user import User
from app.models.sales_order import SalesOrder, SalesOrderLine
from app.models.product import Product
from app.models.inventory import Inventory
from pydantic import BaseModel

router = APIRouter(prefix="/analytics", tags=["analytics"])


class RevenueMetrics(BaseModel):
    total_revenue: Decimal
    revenue_30_days: Decimal
    revenue_90_days: Decimal
    revenue_365_days: Decimal
    average_order_value: Decimal
    revenue_growth: Optional[float] = None


class CustomerMetrics(BaseModel):
    total_customers: int
    active_customers_30_days: int
    new_customers_30_days: int
    average_customer_value: Decimal
    top_customers: list[dict]


class ProductMetrics(BaseModel):
    total_products: int
    top_selling_products: list[dict]
    low_stock_count: int
    products_with_bom: int


class ProfitMetrics(BaseModel):
    total_cost: Decimal
    total_revenue: Decimal
    gross_profit: Decimal
    gross_margin: float
    profit_by_product: list[dict]


class AnalyticsDashboard(BaseModel):
    revenue: RevenueMetrics
    customers: CustomerMetrics
    products: ProductMetrics
    profit: ProfitMetrics
    period_start: datetime
    period_end: datetime


@router.get("/dashboard", response_model=AnalyticsDashboard)
@require_tier(Tier.PRO)
async def get_analytics_dashboard(
    days: int = 30,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics dashboard (Pro feature)
    
    Returns revenue, customer, product, and profit metrics
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    prev_start = start_date - timedelta(days=days)
    
    # Revenue metrics - using total_price from SalesOrder
    revenue_query = db.query(
        func.sum(SalesOrder.total_price).label('total')
    ).filter(
        SalesOrder.status == 'completed'
    )
    
    total_revenue = revenue_query.scalar() or Decimal('0')
    revenue_30 = revenue_query.filter(
        SalesOrder.created_at >= end_date - timedelta(days=30)
    ).scalar() or Decimal('0')
    revenue_90 = revenue_query.filter(
        SalesOrder.created_at >= end_date - timedelta(days=90)
    ).scalar() or Decimal('0')
    revenue_365 = revenue_query.filter(
        SalesOrder.created_at >= end_date - timedelta(days=365)
    ).scalar() or Decimal('0')
    
    # Previous period for growth calculation
    prev_revenue = revenue_query.filter(
        and_(
            SalesOrder.created_at >= prev_start,
            SalesOrder.created_at < start_date
        )
    ).scalar() or Decimal('0')
    
    revenue_growth = None
    if prev_revenue > 0:
        revenue_growth = float(((revenue_30 - prev_revenue) / prev_revenue) * 100)
    
    # Average order value
    order_count = db.query(func.count(SalesOrder.id)).filter(
        SalesOrder.status == 'completed',
        SalesOrder.created_at >= start_date
    ).scalar() or 0
    
    avg_order_value = revenue_30 / order_count if order_count > 0 else Decimal('0')
    
    # Customer metrics - using User model
    total_customers = db.query(func.count(User.id)).filter(
        User.account_type == 'customer'
    ).scalar() or 0
    
    active_customers = db.query(func.count(func.distinct(SalesOrder.user_id))).filter(
        SalesOrder.created_at >= end_date - timedelta(days=30)
    ).scalar() or 0
    
    new_customers = db.query(func.count(User.id)).filter(
        User.account_type == 'customer',
        User.created_at >= end_date - timedelta(days=30)
    ).scalar() or 0
    
    # Top customers by revenue
    top_customers_query = db.query(
        User.company_name,
        User.id,
        func.sum(SalesOrder.total_price).label('revenue')
    ).join(SalesOrder).filter(
        SalesOrder.status == 'completed',
        SalesOrder.created_at >= start_date
    ).group_by(User.id, User.company_name).order_by(
        func.sum(SalesOrder.total_price).desc()
    ).limit(10).all()
    
    top_customers = [
        {
            "customer_id": c.id,
            "company_name": c.company_name or "N/A",
            "revenue": float(c.revenue)
        }
        for c in top_customers_query
    ]
    
    avg_customer_value = revenue_30 / active_customers if active_customers > 0 else Decimal('0')
    
    # Product metrics
    total_products = db.query(func.count(Product.id)).filter(
        Product.active== True
    ).scalar() or 0
    
    # Top selling products - using SalesOrderLine
    top_products_query = db.query(
        Product.sku,
        Product.name,
        func.sum(SalesOrderLine.quantity).label('qty_sold'),
        func.sum(SalesOrderLine.total_price).label('revenue')
    ).join(SalesOrderLine, Product.id == SalesOrderLine.product_id).join(
        SalesOrder
    ).filter(
        SalesOrder.status == 'completed',
        SalesOrder.created_at >= start_date
    ).group_by(Product.id, Product.sku, Product.name).order_by(
        func.sum(SalesOrderLine.quantity).desc()
    ).limit(10).all()
    
    top_products = [
        {
            "sku": p.sku,
            "name": p.name,
            "quantity_sold": float(p.qty_sold),
            "revenue": float(p.revenue)
        }
        for p in top_products_query
    ]
    
    # Low stock count
    low_stock_count = db.query(func.count(func.distinct(Product.id))).join(Inventory).filter(
        Inventory.on_hand_quantity < Product.reorder_point
    ).scalar() or 0
    
    # Products with BOM
    from app.models.bom import BOM
    products_with_bom = db.query(func.count(func.distinct(BOM.product_id))).scalar() or 0
    
    # Profit metrics
    total_cost = db.query(
        func.sum(SalesOrderLine.quantity * Product.standard_cost)
    ).join(Product).join(SalesOrder).filter(
        SalesOrder.status == 'completed',
        SalesOrder.created_at >= start_date
    ).scalar() or Decimal('0')
    
    gross_profit = revenue_30 - total_cost
    gross_margin = float((gross_profit / revenue_30 * 100)) if revenue_30 > 0 else 0.0
    
    # Profit by product
    profit_by_product_query = db.query(
        Product.sku,
        Product.name,
        func.sum(SalesOrderLine.quantity).label('qty'),
        func.sum(SalesOrderLine.total_price).label('revenue'),
        func.sum(SalesOrderLine.quantity * Product.standard_cost).label('cost')
    ).join(SalesOrderLine, Product.id == SalesOrderLine.product_id).join(
        SalesOrder
    ).filter(
        SalesOrder.status == 'completed',
        SalesOrder.created_at >= start_date
    ).group_by(Product.id, Product.sku, Product.name).having(
        func.sum(SalesOrderLine.total_price) > 0
    ).order_by(
        (func.sum(SalesOrderLine.total_price) - func.sum(SalesOrderLine.quantity * Product.standard_cost)).desc()
    ).limit(10).all()
    
    profit_by_product = [
        {
            "sku": p.sku,
            "name": p.name,
            "quantity": float(p.qty),
            "revenue": float(p.revenue),
            "cost": float(p.cost),
            "profit": float(p.revenue - p.cost),
            "margin": float(((p.revenue - p.cost) / p.revenue * 100)) if p.revenue > 0 else 0.0
        }
        for p in profit_by_product_query
    ]
    
    return AnalyticsDashboard(
        revenue=RevenueMetrics(
            total_revenue=total_revenue,
            revenue_30_days=revenue_30,
            revenue_90_days=revenue_90,
            revenue_365_days=revenue_365,
            average_order_value=avg_order_value,
            revenue_growth=revenue_growth
        ),
        customers=CustomerMetrics(
            total_customers=total_customers,
            active_customers_30_days=active_customers,
            new_customers_30_days=new_customers,
            average_customer_value=avg_customer_value,
            top_customers=top_customers
        ),
        products=ProductMetrics(
            total_products=total_products,
            top_selling_products=top_products,
            low_stock_count=low_stock_count,
            products_with_bom=products_with_bom
        ),
        profit=ProfitMetrics(
            total_cost=total_cost,
            total_revenue=revenue_30,
            gross_profit=gross_profit,
            gross_margin=gross_margin,
            profit_by_product=profit_by_product
        ),
        period_start=start_date,
        period_end=end_date
    )

