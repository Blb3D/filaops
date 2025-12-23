"""
Material Traceability API Endpoints

Provides forward and backward traceability for quality management.
Enables DHR (Device History Record) generation and recall impact analysis.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.material_spool import MaterialSpool, ProductionOrderSpool
from app.models.production_order import ProductionOrder
from app.models.product import Product
from app.models.sales_order import SalesOrder, SalesOrderLine
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.vendor import Vendor
from app.models.traceability import SerialNumber
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

# ============================================================================
# Forward Traceability (Spool → Products → Customers)
# ============================================================================

@router.get("/forward/spool/{spool_id}")
async def trace_forward_from_spool(
    spool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trace a spool forward to all products and customers.
    
    Returns:
    - Spool details (material, lot, vendor)
    - All production orders that used this spool
    - All sales orders linked to those production orders
    - Serial numbers produced
    - Customer information
    """
    # Get spool with relationships
    spool = db.query(MaterialSpool).options(
        joinedload(MaterialSpool.product),
        joinedload(MaterialSpool.location),
    ).filter(MaterialSpool.id == spool_id).first()
    
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")
    
    # Get all production orders that used this spool
    spool_usage = db.query(ProductionOrderSpool).options(
        joinedload(ProductionOrderSpool.production_order).joinedload(ProductionOrder.product),
        joinedload(ProductionOrderSpool.production_order).joinedload(ProductionOrder.sales_order),
    ).filter(
        ProductionOrderSpool.spool_id == spool_id
    ).order_by(desc(ProductionOrderSpool.created_at)).all()
    
    # Get purchase order info if available
    purchase_info = None
    if spool.product:
        po_line = db.query(PurchaseOrderLine).filter(
            PurchaseOrderLine.product_id == spool.product.id
        ).order_by(desc(PurchaseOrderLine.created_at)).first()
        
        if po_line:
            po = db.query(PurchaseOrder).options(
                joinedload(PurchaseOrder.vendor)
            ).filter(PurchaseOrder.id == po_line.purchase_order_id).first()
            
            if po:
                purchase_info = {
                    "po_number": po.po_number,
                    "vendor_name": po.vendor.name if po.vendor else None,
                    "order_date": po.order_date.isoformat() if po.order_date else None,
                    "received_date": po.received_date.isoformat() if po.received_date else None,
                }
    
    # Build usage tree
    usage_tree = []
    total_consumed_g = Decimal("0")
    affected_customers = set()
    affected_sales_orders = set()
    total_units_produced = 0
    
    for usage in spool_usage:
        po = usage.production_order
        if not po:
            continue
        
        # Get serial numbers for this production order
        serials = db.query(SerialNumber).filter(
            SerialNumber.production_order_id == po.id
        ).all()
        
        # Get sales order info
        sales_order_info = None
        if po.sales_order:
            sales_order_info = {
                "id": po.sales_order.id,
                "order_number": po.sales_order.order_number,
                "customer_name": po.sales_order.customer_name,
                "customer_email": po.sales_order.customer_email,
                "ship_date": po.sales_order.ship_date.isoformat() if po.sales_order.ship_date else None,
                "status": po.sales_order.status,
            }
            affected_customers.add(po.sales_order.customer_name or po.sales_order.customer_email)
            affected_sales_orders.add(po.sales_order.order_number)
        
        consumed_g = float(usage.weight_consumed_kg or 0)  # Actually in grams
        total_consumed_g += Decimal(str(consumed_g))
        total_units_produced += int(po.quantity_completed or 0)
        
        usage_tree.append({
            "production_order": {
                "id": po.id,
                "code": po.code,
                "product_sku": po.product.sku if po.product else None,
                "product_name": po.product.name if po.product else None,
                "quantity_produced": float(po.quantity_completed or 0),
                "completed_date": po.completed_date.isoformat() if po.completed_date else None,
                "status": po.status,
            },
            "material_consumed_g": consumed_g,
            "sales_order": sales_order_info,
            "serial_numbers": [
                {
                    "serial_number": sn.serial_number,
                    "status": sn.status,
                    "created_at": sn.created_at.isoformat() if sn.created_at else None,
                }
                for sn in serials
            ],
        })
    
    return {
        "spool": {
            "id": spool.id,
            "spool_number": spool.spool_number,
            "material_sku": spool.product.sku if spool.product else None,
            "material_name": spool.product.name if spool.product else None,
            "initial_weight_g": float(spool.initial_weight_kg or 0),  # Actually grams
            "current_weight_g": float(spool.current_weight_kg or 0),  # Actually grams
            "consumed_g": float(total_consumed_g),
            "remaining_percent": spool.weight_remaining_percent if hasattr(spool, 'weight_remaining_percent') else 0,
            "status": spool.status,
            "supplier_lot_number": spool.supplier_lot_number,
            "received_date": spool.received_date.isoformat() if spool.received_date else None,
            "expiry_date": spool.expiry_date.isoformat() if spool.expiry_date else None,
            "location": spool.location.name if spool.location else None,
        },
        "purchase_info": purchase_info,
        "usage": usage_tree,
        "summary": {
            "total_production_orders": len(usage_tree),
            "total_consumed_g": float(total_consumed_g),
            "total_units_produced": total_units_produced,
            "affected_sales_orders": len(affected_sales_orders),
            "affected_customers": len(affected_customers),
            "customers": list(affected_customers),
        }
    }

# ============================================================================
# Backward Traceability (Product → Spools → Vendor)
# ============================================================================

@router.get("/backward/serial/{serial_number}")
async def trace_backward_from_serial(
    serial_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trace a serial number back to source materials and vendor.
    
    Returns:
    - Serial number details
    - Production order details
    - Product details
    - All spools used in production
    - Purchase order and vendor info for each spool
    - Sales order info
    """
    # Get serial number
    serial = db.query(SerialNumber).options(
        joinedload(SerialNumber.production_order).joinedload(ProductionOrder.product),
        joinedload(SerialNumber.production_order).joinedload(ProductionOrder.sales_order),
    ).filter(SerialNumber.serial_number == serial_number).first()
    
    if not serial:
        raise HTTPException(status_code=404, detail=f"Serial number '{serial_number}' not found")
    
    po = serial.production_order
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found for this serial")
    
    # Get all spools used in this production order
    spools_used = db.query(ProductionOrderSpool).options(
        joinedload(ProductionOrderSpool.spool).joinedload(MaterialSpool.product),
        joinedload(ProductionOrderSpool.spool).joinedload(MaterialSpool.location),
    ).filter(
        ProductionOrderSpool.production_order_id == po.id
    ).all()
    
    # Build material lineage
    material_lineage = []
    for spool_usage in spools_used:
        spool = spool_usage.spool
        if not spool:
            continue
        
        # Get purchase order info
        purchase_info = None
        if spool.product:
            po_line = db.query(PurchaseOrderLine).filter(
                PurchaseOrderLine.product_id == spool.product.id
            ).order_by(desc(PurchaseOrderLine.created_at)).first()
            
            if po_line:
                purchase_order = db.query(PurchaseOrder).options(
                    joinedload(PurchaseOrder.vendor)
                ).filter(PurchaseOrder.id == po_line.purchase_order_id).first()
                
                if purchase_order:
                    purchase_info = {
                        "po_number": purchase_order.po_number,
                        "vendor_name": purchase_order.vendor.name if purchase_order.vendor else None,
                        "vendor_id": purchase_order.vendor_id,
                        "order_date": purchase_order.order_date.isoformat() if purchase_order.order_date else None,
                        "received_date": purchase_order.received_date.isoformat() if purchase_order.received_date else None,
                    }
        
        material_lineage.append({
            "spool": {
                "id": spool.id,
                "spool_number": spool.spool_number,
                "material_sku": spool.product.sku if spool.product else None,
                "material_name": spool.product.name if spool.product else None,
                "supplier_lot_number": spool.supplier_lot_number,
                "received_date": spool.received_date.isoformat() if spool.received_date else None,
                "expiry_date": spool.expiry_date.isoformat() if spool.expiry_date else None,
            },
            "weight_consumed_g": float(spool_usage.weight_consumed_kg or 0),  # Actually grams
            "purchase_order": purchase_info,
        })
    
    # Sales order info
    sales_order_info = None
    if po.sales_order:
        sales_order_info = {
            "id": po.sales_order.id,
            "order_number": po.sales_order.order_number,
            "customer_name": po.sales_order.customer_name,
            "customer_email": po.sales_order.customer_email,
            "ship_date": po.sales_order.ship_date.isoformat() if po.sales_order.ship_date else None,
            "status": po.sales_order.status,
        }
    
    return {
        "serial_number": {
            "serial_number": serial.serial_number,
            "status": serial.status,
            "created_at": serial.created_at.isoformat() if serial.created_at else None,
        },
        "product": {
            "id": po.product.id if po.product else None,
            "sku": po.product.sku if po.product else None,
            "name": po.product.name if po.product else None,
        },
        "production_order": {
            "id": po.id,
            "code": po.code,
            "quantity_produced": float(po.quantity_completed or 0),
            "completed_date": po.completed_date.isoformat() if po.completed_date else None,
            "status": po.status,
        },
        "sales_order": sales_order_info,
        "material_lineage": material_lineage,
        "traceability_chain": {
            "complete": len(material_lineage) > 0,
            "spools_used": len(material_lineage),
            "vendors": len(set(m["purchase_order"]["vendor_name"] for m in material_lineage if m["purchase_order"])),
        }
    }

@router.get("/backward/sales-order/{so_id}")
async def trace_backward_from_sales_order(
    so_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trace a sales order back to all source materials.
    
    Useful for: "What materials went into this entire order?"
    """
    # Get sales order
    sales_order = db.query(SalesOrder).filter(SalesOrder.id == so_id).first()
    
    if not sales_order:
        raise HTTPException(status_code=404, detail="Sales order not found")
    
    # Get all production orders for this sales order
    production_orders = db.query(ProductionOrder).options(
        joinedload(ProductionOrder.product)
    ).filter(
        ProductionOrder.sales_order_id == so_id
    ).all()
    
    # Collect all spools used
    all_spools = {}
    total_material_g = Decimal("0")
    
    for po in production_orders:
        spools_used = db.query(ProductionOrderSpool).options(
            joinedload(ProductionOrderSpool.spool).joinedload(MaterialSpool.product)
        ).filter(
            ProductionOrderSpool.production_order_id == po.id
        ).all()
        
        for spool_usage in spools_used:
            spool = spool_usage.spool
            if not spool:
                continue
            
            weight_g = Decimal(str(spool_usage.weight_consumed_kg or 0))
            total_material_g += weight_g
            
            if spool.id not in all_spools:
                all_spools[spool.id] = {
                    "spool_number": spool.spool_number,
                    "material_sku": spool.product.sku if spool.product else None,
                    "material_name": spool.product.name if spool.product else None,
                    "supplier_lot_number": spool.supplier_lot_number,
                    "total_consumed_g": 0,
                    "used_in_orders": [],
                }
            
            all_spools[spool.id]["total_consumed_g"] += float(weight_g)
            all_spools[spool.id]["used_in_orders"].append({
                "production_order_code": po.code,
                "product_sku": po.product.sku if po.product else None,
                "weight_consumed_g": float(weight_g),
            })
    
    return {
        "sales_order": {
            "id": sales_order.id,
            "order_number": sales_order.order_number,
            "customer_name": sales_order.customer_name,
            "customer_email": sales_order.customer_email,
            "status": sales_order.status,
        },
        "production_orders": [
            {
                "code": po.code,
                "product_sku": po.product.sku if po.product else None,
                "product_name": po.product.name if po.product else None,
                "quantity": float(po.quantity_completed or 0),
            }
            for po in production_orders
        ],
        "materials_used": list(all_spools.values()),
        "summary": {
            "total_production_orders": len(production_orders),
            "unique_spools": len(all_spools),
            "total_material_g": float(total_material_g),
        }
    }

# ============================================================================
# Recall Impact Analysis
# ============================================================================

@router.post("/recall-impact")
async def calculate_recall_impact(
    spool_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calculate the impact of recalling specific spools.
    
    Returns:
    - All affected production orders
    - All affected sales orders
    - All affected customers
    - All affected serial numbers
    """
    if not spool_ids:
        raise HTTPException(status_code=400, detail="No spool IDs provided")
    
    # Get all affected production orders
    affected_pos = db.query(ProductionOrderSpool).options(
        joinedload(ProductionOrderSpool.production_order).joinedload(ProductionOrder.product),
        joinedload(ProductionOrderSpool.production_order).joinedload(ProductionOrder.sales_order),
        joinedload(ProductionOrderSpool.spool),
    ).filter(
        ProductionOrderSpool.spool_id.in_(spool_ids)
    ).all()
    
    affected_sales_orders = {}
    affected_customers = set()
    affected_serials = []
    affected_products = set()
    
    for po_spool in affected_pos:
        po = po_spool.production_order
        if not po:
            continue
        
        # Track product
        if po.product:
            affected_products.add(f"{po.product.sku} - {po.product.name}")
        
        # Track sales order
        if po.sales_order:
            so = po.sales_order
            if so.id not in affected_sales_orders:
                affected_sales_orders[so.id] = {
                    "order_number": so.order_number,
                    "customer_name": so.customer_name,
                    "customer_email": so.customer_email,
                    "ship_date": so.ship_date.isoformat() if so.ship_date else None,
                    "status": so.status,
                    "production_orders": [],
                }
            
            affected_sales_orders[so.id]["production_orders"].append(po.code)
            affected_customers.add(so.customer_name or so.customer_email)
        
        # Get serial numbers
        serials = db.query(SerialNumber).filter(
            SerialNumber.production_order_id == po.id
        ).all()
        
        for serial in serials:
            affected_serials.append({
                "serial_number": serial.serial_number,
                "production_order": po.code,
                "product_sku": po.product.sku if po.product else None,
                "status": serial.status,
            })
    
    # Get spool details
    spools = db.query(MaterialSpool).options(
        joinedload(MaterialSpool.product)
    ).filter(MaterialSpool.id.in_(spool_ids)).all()
    
    spool_details = [
        {
            "id": spool.id,
            "spool_number": spool.spool_number,
            "material_sku": spool.product.sku if spool.product else None,
            "material_name": spool.product.name if spool.product else None,
            "supplier_lot_number": spool.supplier_lot_number,
        }
        for spool in spools
    ]
    
    return {
        "spools": spool_details,
        "impact": {
            "production_orders_affected": len(set(ps.production_order_id for ps in affected_pos)),
            "sales_orders_affected": len(affected_sales_orders),
            "customers_affected": len(affected_customers),
            "serial_numbers_affected": len(affected_serials),
            "products_affected": len(affected_products),
        },
        "sales_orders": list(affected_sales_orders.values()),
        "customers": list(affected_customers),
        "serial_numbers": affected_serials,
        "products": list(affected_products),
        "severity": "HIGH" if len(affected_customers) > 10 else "MEDIUM" if len(affected_customers) > 0 else "LOW",
    }

