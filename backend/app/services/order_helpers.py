"""
Order Helpers - Unified handling for quote-based vs line-item orders

This module provides helper functions to abstract away the difference between:
- Quote-based orders: product_id and quantity on the SalesOrder itself
- Line-item orders: products in SalesOrderLine records

Use these helpers instead of duplicating `if order.lines: ... else: order.product_id`
throughout the codebase.
"""
from typing import List, Tuple, Optional
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.sales_order import SalesOrder
from app.models.product import Product


def get_order_products(sales_order: SalesOrder) -> List[Tuple[int, Decimal]]:
    """
    Get (product_id, quantity) tuples from a sales order.
    Handles BOTH order types (quote_based and line_item) in ONE place.

    Args:
        sales_order: The SalesOrder to extract products from

    Returns:
        List of (product_id, quantity) tuples
    """
    products = []

    if sales_order.order_type == "line_item" and sales_order.lines:
        for line in sales_order.lines:
            if line.product_id:
                qty = Decimal(str(line.quantity or 1))
                products.append((line.product_id, qty))
    elif sales_order.product_id:
        qty = Decimal(str(sales_order.quantity or 1))
        products.append((sales_order.product_id, qty))

    return products


def get_order_product_ids(sales_order: SalesOrder) -> List[int]:
    """
    Get just the product IDs from a sales order.

    Args:
        sales_order: The SalesOrder to extract product IDs from

    Returns:
        List of product IDs
    """
    return [product_id for product_id, _ in get_order_products(sales_order)]


def get_order_total_quantity(sales_order: SalesOrder) -> Decimal:
    """
    Get the total quantity of all products in a sales order.

    Args:
        sales_order: The SalesOrder to sum quantities for

    Returns:
        Total quantity across all products
    """
    return sum(qty for _, qty in get_order_products(sales_order))


def get_order_primary_product(
    db: Session,
    sales_order: SalesOrder
) -> Optional[Product]:
    """
    Get the primary (first) product for a sales order.

    For quote-based orders, this is the order's product.
    For line-item orders, this is the first line's product.

    Args:
        db: Database session
        sales_order: The SalesOrder

    Returns:
        Product if found, None otherwise
    """
    products = get_order_products(sales_order)
    if not products:
        return None

    product_id = products[0][0]
    return db.query(Product).filter(Product.id == product_id).first()


def is_quote_based_order(sales_order: SalesOrder) -> bool:
    """Check if this is a quote-based order (vs line-item)."""
    return sales_order.order_type == "quote_based"


def is_line_item_order(sales_order: SalesOrder) -> bool:
    """Check if this is a line-item order (vs quote-based)."""
    return sales_order.order_type == "line_item"
