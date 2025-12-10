"""
Accounting View Endpoints

Provides endpoints for viewing inventory flow through accounting lens:
- Raw Materials (1300) → WIP (1310) → Finished Goods (1320) → COGS (5100)

These are views into the inventory data, formatted for accounting purposes.
Actual QuickBooks integration will come in Phase 4.
"""
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.inventory import Inventory, InventoryTransaction
from app.models.product import Product
from app.models.production_order import ProductionOrder
from app.models.sales_order import SalesOrder


router = APIRouter(prefix="/accounting", tags=["Accounting"])


# Account codes matching ACCOUNTING_ARCHITECTURE.md
ACCOUNTS = {
    "1300": "Inventory - Raw Materials",
    "1310": "Inventory - Work in Progress",
    "1320": "Inventory - Finished Goods",
    "5100": "COGS - Material Cost",
}


@router.get("/inventory-by-account")
async def get_inventory_by_account(
    db: Session = Depends(get_db),
):
    """
    Get inventory balances organized by accounting category.

    Maps product categories to account codes:
    - Raw Materials (1300): MAT-*, consumables
    - WIP (1310): Products currently in production
    - Finished Goods (1320): PRD-*, completed products
    """
    # Get all inventory with product info
    inventory_items = db.query(
        Inventory,
        Product
    ).join(Product).filter(
        Inventory.on_hand_quantity > 0
    ).all()

    accounts: Dict[str, Dict[str, Any]] = {
        code: {
            "account_code": code,
            "account_name": name,
            "total_value": Decimal("0"),
            "total_units": Decimal("0"),
            "items": [],
        }
        for code, name in ACCOUNTS.items()
        if code.startswith("1")  # Asset accounts only
    }

    for inv, product in inventory_items:
        # Determine account based on SKU pattern
        if product.sku.startswith("MAT-"):
            account = "1300"
        elif product.sku.startswith("PKG-"):
            account = "1300"  # Packaging is raw material
        elif product.sku.startswith("PRD-"):
            account = "1320"  # Products are finished goods
        elif product.sku.startswith("SVC-"):
            continue  # Skip services
        else:
            account = "1300"  # Default to raw materials

        # Calculate value (use product standard_cost if available)
        unit_cost = getattr(product, 'standard_cost', None) or Decimal("0")
        total_value = inv.on_hand_quantity * unit_cost

        accounts[account]["total_value"] += total_value
        accounts[account]["total_units"] += inv.on_hand_quantity
        accounts[account]["items"].append({
            "product_id": product.id,
            "sku": product.sku,
            "name": product.name,
            "on_hand": float(inv.on_hand_quantity),
            "allocated": float(inv.allocated_quantity),
            "available": float(inv.available_quantity) if inv.available_quantity else float(inv.on_hand_quantity - inv.allocated_quantity),
            "unit_cost": float(unit_cost),
            "total_value": float(total_value),
        })

    # Calculate WIP from production orders
    wip_orders = db.query(ProductionOrder).filter(
        ProductionOrder.status.in_(['in_progress', 'printed'])
    ).all()

    wip_value = Decimal("0")
    wip_items = []
    for po in wip_orders:
        # Estimate WIP value from reserved materials
        reserved = db.query(
            func.sum(func.abs(InventoryTransaction.quantity) * func.coalesce(InventoryTransaction.cost_per_unit, 0))
        ).filter(
            InventoryTransaction.reference_type == 'production_order',
            InventoryTransaction.reference_id == po.id,
            InventoryTransaction.transaction_type == 'reservation'
        ).scalar() or Decimal("0")

        wip_value += reserved
        wip_items.append({
            "production_order_id": po.id,
            "code": po.code,
            "status": po.status,
            "estimated_value": float(reserved),
        })

    accounts["1310"]["total_value"] = wip_value
    accounts["1310"]["items"] = wip_items

    return {
        "as_of": datetime.utcnow().isoformat(),
        "accounts": list(accounts.values()),
        "summary": {
            "raw_materials": float(accounts["1300"]["total_value"]),
            "wip": float(accounts["1310"]["total_value"]),
            "finished_goods": float(accounts["1320"]["total_value"]),
            "total_inventory": float(
                accounts["1300"]["total_value"] +
                accounts["1310"]["total_value"] +
                accounts["1320"]["total_value"]
            ),
        },
    }


@router.get("/transactions-journal")
async def get_transactions_as_journal(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to look back"),
    order_id: Optional[int] = Query(None, description="Filter by sales order"),
):
    """
    Get inventory transactions formatted as journal entries.

    Each transaction maps to a debit/credit pair based on transaction type:
    - reservation: DR WIP (1310), CR Raw Materials (1300)
    - consumption: DR COGS (5100), CR WIP (1310)
    - receipt (finished goods): DR Finished Goods (1320), CR WIP (1310)
    - scrap: DR COGS (5100), CR WIP (1310)
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = db.query(InventoryTransaction).filter(
        InventoryTransaction.created_at >= cutoff
    ).order_by(InventoryTransaction.created_at.desc())

    if order_id:
        # Get production order IDs for this sales order
        po_ids = [po.id for po in db.query(ProductionOrder).filter(
            ProductionOrder.sales_order_id == order_id
        ).all()]

        query = query.filter(
            ((InventoryTransaction.reference_type == 'production_order') &
             (InventoryTransaction.reference_id.in_(po_ids))) |
            ((InventoryTransaction.reference_type.in_(['shipment', 'consolidated_shipment'])) &
             (InventoryTransaction.reference_id == order_id))
        )

    transactions = query.limit(200).all()

    journal_entries = []
    for txn in transactions:
        product = db.query(Product).filter(Product.id == txn.product_id).first()
        sku = product.sku if product else "N/A"

        # Skip services from journal
        if sku.startswith("SVC-"):
            continue

        qty = abs(float(txn.quantity)) if txn.quantity else 0
        unit_cost = float(txn.cost_per_unit) if txn.cost_per_unit else 0
        value = qty * unit_cost

        # Map transaction type to journal entry
        entry = {
            "date": txn.created_at.isoformat() if txn.created_at else None,
            "transaction_id": txn.id,
            "transaction_type": txn.transaction_type,
            "reference_type": txn.reference_type,
            "reference_id": txn.reference_id,
            "product_sku": sku,
            "quantity": qty,
            "unit_cost": unit_cost,
            "value": value,
            "debit_account": None,
            "credit_account": None,
            "notes": txn.notes,
        }

        # Determine accounts based on transaction type
        if txn.transaction_type == 'reservation':
            entry["debit_account"] = {"code": "1310", "name": "WIP", "amount": value}
            entry["credit_account"] = {"code": "1300", "name": "Raw Materials", "amount": value}
        elif txn.transaction_type == 'consumption':
            if txn.reference_type in ['shipment', 'consolidated_shipment']:
                # Packaging consumption at shipping
                entry["debit_account"] = {"code": "5100", "name": "COGS", "amount": value}
                entry["credit_account"] = {"code": "1300", "name": "Raw Materials", "amount": value}
            else:
                # Material consumption at production complete
                entry["debit_account"] = {"code": "5100", "name": "COGS", "amount": value}
                entry["credit_account"] = {"code": "1310", "name": "WIP", "amount": value}
        elif txn.transaction_type == 'receipt':
            if sku.startswith("PRD-"):
                # Finished goods receipt
                entry["debit_account"] = {"code": "1320", "name": "Finished Goods", "amount": value}
                entry["credit_account"] = {"code": "1310", "name": "WIP", "amount": value}
            else:
                # Raw material receipt
                entry["debit_account"] = {"code": "1300", "name": "Raw Materials", "amount": value}
                entry["credit_account"] = {"code": "2100", "name": "Accounts Payable", "amount": value}
        elif txn.transaction_type == 'scrap':
            entry["debit_account"] = {"code": "5100", "name": "COGS (Scrap)", "amount": value}
            entry["credit_account"] = {"code": "1310", "name": "WIP", "amount": value}
        elif txn.transaction_type == 'release':
            # Reservation released (e.g., consolidated shipping)
            entry["debit_account"] = {"code": "1300", "name": "Raw Materials", "amount": value}
            entry["credit_account"] = {"code": "1310", "name": "WIP", "amount": value}

        journal_entries.append(entry)

    return {
        "period": f"Last {days} days",
        "transaction_count": len(journal_entries),
        "entries": journal_entries,
    }


@router.get("/order-cost-breakdown/{order_id}")
async def get_order_cost_breakdown(
    order_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a cost breakdown for a specific sales order.

    Shows:
    - Material costs (consumed)
    - Labor/machine time (if tracked)
    - Packaging costs
    - Shipping costs
    - Total COGS
    - Gross margin
    """
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        return {"error": "Order not found"}

    # Get production orders
    production_orders = db.query(ProductionOrder).filter(
        ProductionOrder.sales_order_id == order_id
    ).all()

    po_ids = [po.id for po in production_orders]

    # Get all consumption transactions
    consumptions = db.query(InventoryTransaction).filter(
        InventoryTransaction.reference_type == 'production_order',
        InventoryTransaction.reference_id.in_(po_ids),
        InventoryTransaction.transaction_type == 'consumption'
    ).all()

    # Packaging consumptions
    packaging = db.query(InventoryTransaction).filter(
        InventoryTransaction.reference_type.in_(['shipment', 'consolidated_shipment']),
        InventoryTransaction.reference_id == order_id,
        InventoryTransaction.transaction_type == 'consumption'
    ).all()

    # Calculate costs
    material_cost = Decimal("0")
    labor_cost = Decimal("0")
    packaging_cost = Decimal("0")

    material_items = []
    for txn in consumptions:
        product = db.query(Product).filter(Product.id == txn.product_id).first()
        sku = product.sku if product else "N/A"
        qty = abs(float(txn.quantity)) if txn.quantity else 0
        unit_cost = float(txn.cost_per_unit) if txn.cost_per_unit else 0
        value = Decimal(str(qty * unit_cost))

        if sku.startswith("SVC-"):
            labor_cost += value
        else:
            material_cost += value
            material_items.append({
                "sku": sku,
                "quantity": qty,
                "unit_cost": unit_cost,
                "total": float(value),
            })

    packaging_items = []
    for txn in packaging:
        product = db.query(Product).filter(Product.id == txn.product_id).first()
        sku = product.sku if product else "N/A"
        qty = abs(float(txn.quantity)) if txn.quantity else 0
        unit_cost = float(txn.cost_per_unit) if txn.cost_per_unit else 0
        value = Decimal(str(qty * unit_cost))
        packaging_cost += value
        packaging_items.append({
            "sku": sku,
            "quantity": qty,
            "unit_cost": unit_cost,
            "total": float(value),
        })

    # Shipping cost from order
    shipping_cost = order.shipping_cost or Decimal("0")

    # Total COGS
    total_cogs = material_cost + labor_cost + packaging_cost + shipping_cost

    # Revenue and margin
    revenue = order.total_price or Decimal("0")
    gross_profit = revenue - total_cogs
    margin_pct = (gross_profit / revenue * 100) if revenue > 0 else Decimal("0")

    return {
        "order_id": order_id,
        "order_number": order.order_number,
        "order_status": order.status,
        "revenue": float(revenue),
        "costs": {
            "materials": {
                "total": float(material_cost),
                "items": material_items,
            },
            "labor": float(labor_cost),
            "packaging": {
                "total": float(packaging_cost),
                "items": packaging_items,
            },
            "shipping": float(shipping_cost),
        },
        "total_cogs": float(total_cogs),
        "gross_profit": float(gross_profit),
        "gross_margin_pct": float(margin_pct),
        "status_note": "Values may be incomplete if transactions are missing. Run /audit/transactions for gaps.",
    }


@router.get("/cogs-summary")
async def get_cogs_summary(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days"),
):
    """
    Get COGS summary for recent period.

    Shows total cost of goods sold broken down by category.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get shipped orders in period
    shipped_orders = db.query(SalesOrder).filter(
        SalesOrder.status == 'shipped',
        SalesOrder.shipped_at >= cutoff
    ).all()

    total_revenue = Decimal("0")
    total_material = Decimal("0")
    total_labor = Decimal("0")
    total_packaging = Decimal("0")
    total_shipping = Decimal("0")

    for order in shipped_orders:
        total_revenue += order.total_price or Decimal("0")
        total_shipping += order.shipping_cost or Decimal("0")

        # Get costs from transactions
        po_ids = [po.id for po in db.query(ProductionOrder).filter(
            ProductionOrder.sales_order_id == order.id
        ).all()]

        consumptions = db.query(InventoryTransaction).filter(
            InventoryTransaction.reference_type == 'production_order',
            InventoryTransaction.reference_id.in_(po_ids),
            InventoryTransaction.transaction_type == 'consumption'
        ).all()

        for txn in consumptions:
            product = db.query(Product).filter(Product.id == txn.product_id).first()
            sku = product.sku if product else ""
            qty = abs(float(txn.quantity)) if txn.quantity else 0
            unit_cost = float(txn.cost_per_unit) if txn.cost_per_unit else 0
            value = Decimal(str(qty * unit_cost))

            if sku.startswith("SVC-"):
                total_labor += value
            else:
                total_material += value

        # Packaging
        pkg_consumptions = db.query(InventoryTransaction).filter(
            InventoryTransaction.reference_type.in_(['shipment', 'consolidated_shipment']),
            InventoryTransaction.reference_id == order.id,
            InventoryTransaction.transaction_type == 'consumption'
        ).all()

        for txn in pkg_consumptions:
            qty = abs(float(txn.quantity)) if txn.quantity else 0
            unit_cost = float(txn.cost_per_unit) if txn.cost_per_unit else 0
            total_packaging += Decimal(str(qty * unit_cost))

    total_cogs = total_material + total_labor + total_packaging + total_shipping
    gross_profit = total_revenue - total_cogs
    margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else Decimal("0")

    return {
        "period": f"Last {days} days",
        "orders_shipped": len(shipped_orders),
        "revenue": float(total_revenue),
        "cogs": {
            "materials": float(total_material),
            "labor": float(total_labor),
            "packaging": float(total_packaging),
            "shipping": float(total_shipping),
            "total": float(total_cogs),
        },
        "gross_profit": float(gross_profit),
        "gross_margin_pct": float(margin),
    }
