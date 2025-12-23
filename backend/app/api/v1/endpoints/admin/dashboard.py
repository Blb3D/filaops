"""
Admin Dashboard Endpoints

Central hub for admin operations - provides summary data and navigation context
"""
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User
from app.models.quote import Quote
from app.models.sales_order import SalesOrder
from app.models.production_order import ProductionOrder
from app.models.bom import BOM
from app.models.product import Product
from app.api.v1.deps import get_current_staff_user

router = APIRouter(prefix="/dashboard", tags=["Admin - Dashboard"])


# ============================================================================
# SCHEMAS
# ============================================================================

class ModuleInfo(BaseModel):
    """Info about an admin module"""
    name: str
    description: str
    route: str
    icon: str
    badge_count: Optional[int] = None
    badge_type: Optional[str] = None  # info, warning, error


class DashboardSummary(BaseModel):
    """Summary counts for dashboard"""
    # Quotes
    pending_quotes: int
    quotes_today: int

    # Orders
    pending_orders: int
    orders_needing_review: int
    orders_in_production: int
    orders_ready_to_ship: int

    # Production
    active_production_orders: int
    boms_needing_review: int

    # Revenue (last 30 days)
    revenue_30_days: Decimal
    orders_30_days: int


class DashboardResponse(BaseModel):
    """Full dashboard response"""
    summary: DashboardSummary
    modules: List[ModuleInfo]
    recent_orders: List[dict]
    pending_bom_reviews: List[dict]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Get admin dashboard with summary stats and module navigation.

    Admin only. This is the main hub for backoffice operations.
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = now - timedelta(days=30)

    # ========== SUMMARY STATS ==========

    # Quotes
    pending_quotes = db.query(Quote).filter(Quote.status == "pending").count()
    quotes_today = db.query(Quote).filter(Quote.created_at >= today_start).count()

    # Orders needing attention
    pending_orders = db.query(SalesOrder).filter(
        SalesOrder.status.in_(["pending", "confirmed"])
    ).count()

    # Orders where BOM might need review (quote-based without approved BOM)
    orders_needing_review = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.order_type == "quote_based",
            SalesOrder.status.in_(["pending", "confirmed"]),
        )
        .count()
    )

    orders_in_production = db.query(SalesOrder).filter(
        SalesOrder.status == "in_production"
    ).count()

    orders_ready_to_ship = db.query(SalesOrder).filter(
        SalesOrder.status == "ready_to_ship"
    ).count()

    # Production
    active_production_orders = db.query(ProductionOrder).filter(
        ProductionOrder.status.in_(["pending", "released", "in_progress"])
    ).count()

    # BOMs for custom products that might need review
    boms_needing_review = (
        db.query(BOM)
        .join(Product)
        .filter(
            Product.type == "custom",
            BOM.active.is_(True),  # noqa: E712
        )
        .count()
    )

    # Revenue (last 30 days)
    revenue_result = (
        db.query(func.sum(SalesOrder.grand_total))
        .filter(
            SalesOrder.payment_status == "paid",
            SalesOrder.paid_at >= thirty_days_ago,
        )
        .scalar()
    )
    revenue_30_days = revenue_result or Decimal("0")

    orders_30_days = (
        db.query(SalesOrder)
        .filter(SalesOrder.created_at >= thirty_days_ago)
        .count()
    )

    summary = DashboardSummary(
        pending_quotes=pending_quotes,
        quotes_today=quotes_today,
        pending_orders=pending_orders,
        orders_needing_review=orders_needing_review,
        orders_in_production=orders_in_production,
        orders_ready_to_ship=orders_ready_to_ship,
        active_production_orders=active_production_orders,
        boms_needing_review=boms_needing_review,
        revenue_30_days=revenue_30_days,
        orders_30_days=orders_30_days,
    )

    # ========== MODULES ==========

    modules = [
        ModuleInfo(
            name="BOM Management",
            description="View and edit Bills of Materials",
            route="/admin/bom",
            icon="list",
            badge_count=boms_needing_review if boms_needing_review > 0 else None,
            badge_type="warning" if boms_needing_review > 0 else None,
        ),
        ModuleInfo(
            name="Order Review",
            description="Review and release orders to production",
            route="/admin/orders",
            icon="clipboard-check",
            badge_count=orders_needing_review if orders_needing_review > 0 else None,
            badge_type="info" if orders_needing_review > 0 else None,
        ),
        ModuleInfo(
            name="Production",
            description="Manage production orders and print jobs",
            route="/admin/production",
            icon="printer",
            badge_count=active_production_orders if active_production_orders > 0 else None,
            badge_type="info",
        ),
        ModuleInfo(
            name="Shipping",
            description="Create labels and ship orders",
            route="/admin/shipping",
            icon="truck",
            badge_count=orders_ready_to_ship if orders_ready_to_ship > 0 else None,
            badge_type="warning" if orders_ready_to_ship > 0 else None,
        ),
        ModuleInfo(
            name="Inventory",
            description="View stock levels and transactions",
            route="/admin/inventory",
            icon="archive",
        ),
        ModuleInfo(
            name="Items",
            description="Manage products and materials",
            route="/admin/items",
            icon="cube",
        ),
        ModuleInfo(
            name="Customers",
            description="View and manage customer accounts",
            route="/admin/customers",
            icon="users",
        ),
        ModuleInfo(
            name="Reports",
            description="Sales, production, and financial reports",
            route="/admin/reports",
            icon="chart-bar",
        ),
    ]

    # ========== RECENT ORDERS ==========

    recent_orders_query = (
        db.query(SalesOrder)
        .filter(SalesOrder.status.in_(["pending", "confirmed", "in_production"]))
        .order_by(desc(SalesOrder.created_at))
        .limit(10)
        .all()
    )

    recent_orders = [
        {
            "id": order.id,
            "order_number": order.order_number,
            "product_name": order.product_name,
            "status": order.status,
            "payment_status": order.payment_status,
            "grand_total": float(order.grand_total) if order.grand_total else 0,
            "created_at": order.created_at.isoformat(),
        }
        for order in recent_orders_query
    ]

    # ========== PENDING BOM REVIEWS ==========

    pending_bom_query = (
        db.query(BOM)
        .join(Product)
        .filter(
            Product.type == "custom",
            BOM.active.is_(True),  # noqa: E712
        )
        .order_by(desc(BOM.created_at))
        .limit(10)
        .all()
    )

    pending_bom_reviews = [
        {
            "bom_id": bom.id,
            "product_sku": bom.product.sku if bom.product else None,
            "product_name": bom.product.name if bom.product else None,
            "total_cost": float(bom.total_cost) if bom.total_cost else None,
            "line_count": len(bom.lines),
            "created_at": bom.created_at.isoformat(),
        }
        for bom in pending_bom_query
    ]

    return DashboardResponse(
        summary=summary,
        modules=modules,
        recent_orders=recent_orders,
        pending_bom_reviews=pending_bom_reviews,
    )


@router.get("/summary")
async def get_dashboard_summary(
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Get dashboard summary stats organized by module.

    Returns counts for quotes, orders, production, BOMs, and actionable alerts.
    """
    from app.models.product import Product
    from sqlalchemy import func
    from decimal import Decimal
    
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # Quotes
    pending_quotes = db.query(Quote).filter(Quote.status == "pending").count()
    quotes_this_week = db.query(Quote).filter(Quote.created_at >= week_ago).count()

    # Orders
    confirmed_orders = db.query(SalesOrder).filter(SalesOrder.status == "confirmed").count()
    in_production_orders = db.query(SalesOrder).filter(SalesOrder.status == "in_production").count()
    ready_to_ship_orders = db.query(SalesOrder).filter(SalesOrder.status == "ready_to_ship").count()
    
    # Overdue orders (orders past their estimated completion date)
    overdue_orders = db.query(SalesOrder).filter(
        SalesOrder.status.in_(["confirmed", "in_production"]),
        SalesOrder.estimated_completion_date.isnot(None),
        SalesOrder.estimated_completion_date < now
    ).count()

    # Production
    production_in_progress = db.query(ProductionOrder).filter(
        ProductionOrder.status == "in_progress"
    ).count()
    production_scheduled = db.query(ProductionOrder).filter(
        ProductionOrder.status.in_(["pending", "released"])
    ).count()

    # BOMs
    boms_needing_review = (
        db.query(BOM)
        .join(Product)
        .filter(BOM.active.is_(True))  # noqa: E712
        .count()
    )
    active_boms = db.query(BOM).filter(BOM.active.is_(True)).count()  # noqa: E712

    # Low Stock Items (below reorder point + MRP shortages)
    # Use the same logic as /items/low-stock endpoint - just get the count
    from app.models.inventory import Inventory
    from collections import defaultdict
    from app.models.sales_order import SalesOrderLine
    from app.services.mrp import MRPService, ComponentRequirement
    
    # 1. Get items below reorder point (count unique products)
    # OPTIMIZED: Single query aggregating inventory by product_id
    low_stock_products = set()

    # Get products with reorder points and their total inventory in one query
    inventory_by_product = db.query(
        Inventory.product_id,
        func.coalesce(func.sum(Inventory.available_quantity), 0).label("total_available")
    ).group_by(Inventory.product_id).all()

    # Create lookup dict for fast access
    inventory_lookup = {row.product_id: float(row.total_available) for row in inventory_by_product}

    # Get all products with reorder points
    products_with_reorder = db.query(Product.id, Product.reorder_point).filter(
        Product.active.is_(True),  # noqa: E712
        Product.reorder_point.isnot(None),
        Product.reorder_point > 0
    ).all()

    # Check each product against inventory (all in-memory, no additional queries)
    for product_id, reorder_point in products_with_reorder:
        available = inventory_lookup.get(product_id, 0)
        reorder_val = float(reorder_point) if reorder_point else 0

        if available <= reorder_val:
            low_stock_products.add(product_id)
    
    # 2. Get MRP shortages from active sales orders
    active_orders = db.query(SalesOrder).filter(
        SalesOrder.status.notin_(["cancelled", "completed", "delivered"])
    ).all()
    
    mrp_shortage_products = set()
    if active_orders:
        mrp_service = MRPService(db)
        all_requirements = []
        
        for order in active_orders:
            if order.order_type == "line_item":
                lines = db.query(SalesOrderLine).filter(
                    SalesOrderLine.sales_order_id == order.id
                ).all()
                for line in lines:
                    if line.product_id:
                        try:
                            requirements = mrp_service.explode_bom(
                                product_id=int(line.product_id),
                                quantity=Decimal(str(float(line.quantity))),
                                source_demand_type="sales_order",
                                source_demand_id=int(order.id)
                            )
                            all_requirements.extend(requirements)
                        except Exception:
                            continue
            elif order.order_type == "quote_based" and hasattr(order, 'product_id') and order.product_id:
                try:
                    order_qty = float(order.quantity) if order.quantity else 1.0
                    requirements = mrp_service.explode_bom(
                        product_id=int(order.product_id),
                        quantity=Decimal(str(order_qty)),
                        source_demand_type="sales_order",
                        source_demand_id=int(order.id)
                    )
                    all_requirements.extend(requirements)
                except Exception:
                    continue
        
        if all_requirements:
            # Aggregate by product_id
            aggregated = defaultdict(lambda: {"product_id": None, "gross_quantity": Decimal("0"), "bom_level": 0, "product_sku": "", "product_name": ""})
            for req in all_requirements:
                key = int(req.product_id)
                if aggregated[key]["product_id"] is None:
                    aggregated[key] = {
                        "product_id": int(req.product_id),
                        "product_sku": str(req.product_sku),
                        "product_name": str(req.product_name),
                        "gross_quantity": Decimal(str(req.gross_quantity)),
                        "bom_level": int(req.bom_level),
                    }
                else:
                    aggregated[key]["gross_quantity"] += Decimal(str(req.gross_quantity))
            
            # Calculate net requirements
            component_reqs = [
                ComponentRequirement(
                    product_id=int(data["product_id"]),
                    product_sku=str(data["product_sku"]),
                    product_name=str(data["product_name"]),
                    bom_level=int(data["bom_level"]),
                    gross_quantity=Decimal(str(data["gross_quantity"])),
                )
                for data in aggregated.values()
            ]
            
            net_requirements = mrp_service.calculate_net_requirements(component_reqs)
            for net_req in net_requirements:
                if float(net_req.net_shortage) > 0:
                    mrp_shortage_products.add(int(net_req.product_id))
    
    # Combine both sets (items below reorder point OR with MRP shortages)
    low_stock_count = len(low_stock_products | mrp_shortage_products)

    # Active orders count (for reference)
    active_orders_count = db.query(SalesOrder).filter(
        SalesOrder.status.in_(["confirmed", "in_production"])
    ).count()
    
    # Production orders ready to start (materials available)
    # Get released/pending production orders and check material availability
    from app.api.v1.endpoints.production_orders import check_material_availability
    from app.models.bom import BOMLine
    from app.models.inventory import Inventory
    
    ready_to_start_count = 0
    released_orders = db.query(ProductionOrder).filter(
        ProductionOrder.status.in_(["pending", "released"])
    ).all()
    
    for po in released_orders:
        if not po.bom_id:
            # No BOM = no materials needed, ready to start
            ready_to_start_count += 1
            continue
        
        bom = db.query(BOM).filter(BOM.id == po.bom_id).first()
        if not bom:
            continue
        
        bom_lines = db.query(BOMLine).filter(BOMLine.bom_id == bom.id).all()
        all_available = True
        
        qty_multiplier = Decimal(str(po.quantity_ordered or 1))
        
        for line in bom_lines:
            if line.is_cost_only:
                continue
            
            component = db.query(Product).filter(Product.id == line.component_id).first()
            if not component:
                continue
            
            # Calculate required quantity
            base_qty = Decimal(str(line.quantity or 0))
            scrap_factor = Decimal(str(line.scrap_factor or 0)) / Decimal("100")
            qty_with_scrap = base_qty * (Decimal("1") + scrap_factor)
            required_qty = qty_with_scrap * qty_multiplier
            
            # Check available inventory
            inv_result = db.query(
                func.sum(Inventory.available_quantity)
            ).filter(Inventory.product_id == line.component_id).scalar()
            available_qty = Decimal(str(inv_result or 0))
            
            if available_qty < required_qty:
                all_available = False
                break
        
        if all_available:
            ready_to_start_count += 1
    
    # Revenue metrics
    revenue_30_days = db.query(func.sum(SalesOrder.grand_total)).filter(
        SalesOrder.payment_status == "paid",
        SalesOrder.paid_at >= thirty_days_ago
    ).scalar() or Decimal("0")
    
    orders_30_days = db.query(SalesOrder).filter(
        SalesOrder.created_at >= thirty_days_ago
    ).count()

    return {
        "quotes": {
            "pending": pending_quotes,
            "this_week": quotes_this_week,
        },
        "orders": {
            "confirmed": confirmed_orders,
            "in_production": in_production_orders,
            "ready_to_ship": ready_to_ship_orders,
            "overdue": overdue_orders,
        },
        "production": {
            "in_progress": production_in_progress,
            "scheduled": production_scheduled,
            "ready_to_start": ready_to_start_count,
        },
        "boms": {
            "needs_review": boms_needing_review,
            "active": active_boms,
        },
        "inventory": {
            "low_stock_count": low_stock_count,
            "active_orders": active_orders_count,
        },
        "revenue": {
            "last_30_days": float(revenue_30_days),
            "orders_last_30_days": orders_30_days,
        },
    }


@router.get("/recent-orders")
async def get_recent_orders(
    limit: int = 5,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Get recent orders for dashboard display.
    """
    orders = (
        db.query(SalesOrder)
        .order_by(desc(SalesOrder.created_at))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": order.id,
            "order_number": order.order_number,
            "product_name": order.product_name,
            "customer_name": order.user.full_name if order.user else "Unknown",
            "status": order.status,
            "payment_status": order.payment_status,
            "grand_total": float(order.grand_total) if order.grand_total else 0,
            "total_price": float(order.grand_total) if order.grand_total else 0,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }
        for order in orders
    ]


@router.get("/pending-bom-reviews")
async def get_pending_bom_reviews(
    limit: int = 5,
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Get BOMs that need admin review.
    """
    boms = (
        db.query(BOM)
        .filter(BOM.active.is_(True))  # noqa: E712
        .order_by(desc(BOM.created_at))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": bom.id,
            "code": bom.code,
            "name": bom.name,
            "total_cost": float(bom.total_cost) if bom.total_cost else 0,
            "line_count": len(bom.lines) if bom.lines else 0,
            "created_at": bom.created_at.isoformat() if bom.created_at else None,
        }
        for bom in boms
    ]


@router.get("/stats")
async def get_quick_stats(
    current_admin: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Get quick stats for dashboard header.

    Admin only. Lightweight endpoint for real-time updates.
    """
    pending_quotes = db.query(Quote).filter(Quote.status == "pending").count()
    pending_orders = db.query(SalesOrder).filter(
        SalesOrder.status.in_(["pending", "confirmed"])
    ).count()
    ready_to_ship = db.query(SalesOrder).filter(
        SalesOrder.status == "ready_to_ship"
    ).count()

    return {
        "pending_quotes": pending_quotes,
        "pending_orders": pending_orders,
        "ready_to_ship": ready_to_ship,
    }


@router.get("/modules")
async def get_modules(
    current_admin: User = Depends(get_current_staff_user),
):
    """
    Get list of available admin modules.

    Admin only. For building navigation UI.
    """
    return [
        {
            "name": "BOM Management",
            "key": "bom",
            "description": "View and edit Bills of Materials for products",
            "api_route": "/api/v1/admin/bom",
            "icon": "list",
        },
        {
            "name": "Order Review",
            "key": "orders",
            "description": "Review orders and release to production",
            "api_route": "/api/v1/sales-orders",
            "icon": "clipboard-check",
        },
        {
            "name": "Production",
            "key": "production",
            "description": "Manage production orders and print jobs",
            "api_route": "/api/v1/production-orders",
            "icon": "printer",
        },
        {
            "name": "Shipping",
            "key": "shipping",
            "description": "Create shipping labels and track shipments",
            "api_route": "/api/v1/shipping",
            "icon": "truck",
        },
        {
            "name": "Inventory",
            "key": "inventory",
            "description": "View stock levels and manage inventory",
            "api_route": "/api/v1/inventory",
            "icon": "archive",
        },
        {
            "name": "Products",
            "key": "products",
            "description": "Manage products, materials, and pricing",
            "api_route": "/api/v1/products",
            "icon": "cube",
        },
        {
            "name": "Customers",
            "key": "customers",
            "description": "View and manage customer accounts",
            "api_route": "/api/v1/auth/portal/customer",
            "icon": "users",
        },
    ]
