"""
Status Sync Service - Auto-update parent entities when children complete

This module handles automatic status transitions:
- SalesOrder status updates when all ProductionOrders complete
- Fulfillment status updates when production is ready

Triggered by production_orders.py when a PO is completed.
"""
from sqlalchemy.orm import Session

from app.models.sales_order import SalesOrder
from app.models.production_order import ProductionOrder
from app.logging_config import get_logger

logger = get_logger(__name__)


def sync_on_production_complete(db: Session, production_order: ProductionOrder) -> bool:
    """
    Called when a production order is completed.
    Updates parent SalesOrder if ALL production orders for it are done.

    Args:
        db: Database session
        production_order: The just-completed production order

    Returns:
        True if SalesOrder was updated, False otherwise
    """
    if not production_order.sales_order_id:
        return False

    sales_order = db.query(SalesOrder).filter(
        SalesOrder.id == production_order.sales_order_id
    ).first()

    if not sales_order:
        logger.warning(
            f"Production order {production_order.code} references non-existent "
            f"sales order {production_order.sales_order_id}"
        )
        return False

    # Get all production orders for this sales order
    all_production_orders = db.query(ProductionOrder).filter(
        ProductionOrder.sales_order_id == sales_order.id
    ).all()

    if not all_production_orders:
        return False

    # Check if ALL are completed or closed
    completed_statuses = {"completed", "closed"}
    all_complete = all(
        po.status in completed_statuses for po in all_production_orders
    )

    if not all_complete:
        return False

    # All production orders complete - update sales order
    updated = False

    # Update fulfillment_status if pending
    if sales_order.fulfillment_status == "pending":
        sales_order.fulfillment_status = "ready"
        logger.info(
            f"Auto-updated {sales_order.order_number} fulfillment_status to 'ready' "
            f"(all {len(all_production_orders)} production orders complete)"
        )
        updated = True

    # Update order status if in_production
    if sales_order.status == "in_production":
        sales_order.status = "ready_to_ship"
        logger.info(
            f"Auto-updated {sales_order.order_number} status to 'ready_to_ship'"
        )
        updated = True

    return updated


def check_sales_order_production_status(db: Session, sales_order_id: int) -> dict:
    """
    Check the production status for a sales order.

    Args:
        db: Database session
        sales_order_id: ID of the sales order

    Returns:
        Dict with production status info
    """
    production_orders = db.query(ProductionOrder).filter(
        ProductionOrder.sales_order_id == sales_order_id
    ).all()

    if not production_orders:
        return {
            "has_production_orders": False,
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "pending": 0,
            "all_complete": False,
        }

    completed = sum(1 for po in production_orders if po.status in ("completed", "closed"))
    in_progress = sum(1 for po in production_orders if po.status == "in_progress")
    pending = sum(1 for po in production_orders if po.status in ("pending", "scheduled"))

    return {
        "has_production_orders": True,
        "total": len(production_orders),
        "completed": completed,
        "in_progress": in_progress,
        "pending": pending,
        "all_complete": completed == len(production_orders),
    }
