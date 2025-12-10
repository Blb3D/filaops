"""
Transaction Audit Service

Validates that all expected inventory transactions exist for orders at each stage.
Reports missing transactions for debugging and compliance.

Expected Transaction Flow (per ACCOUNTING_ARCHITECTURE.md):
1. Production Start: reservation (materials + packaging)
2. Production Complete: consumption (materials), receipt (finished goods)
3. Shipping: consumption (packaging), adjustment (finished goods out)
4. Scrap/Fail: scrap transaction (write off WIP)
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.sales_order import SalesOrder
from app.models.production_order import ProductionOrder
from app.models.inventory import InventoryTransaction, Inventory
from app.models.bom import BOM


@dataclass
class TransactionGap:
    """Represents a missing or incomplete transaction"""
    order_id: int
    order_number: str
    order_status: str
    production_order_id: Optional[int]
    production_status: Optional[str]
    gap_type: str  # 'missing_reservation', 'missing_consumption', 'missing_receipt', etc.
    expected_product_id: Optional[int]
    expected_sku: Optional[str]
    expected_quantity: Optional[Decimal]
    details: str


@dataclass
class AuditResult:
    """Results of a transaction audit"""
    audit_timestamp: datetime
    total_orders_checked: int
    orders_with_gaps: int
    total_gaps: int
    gaps: List[TransactionGap] = field(default_factory=list)
    summary_by_type: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_timestamp": self.audit_timestamp.isoformat(),
            "total_orders_checked": self.total_orders_checked,
            "orders_with_gaps": self.orders_with_gaps,
            "total_gaps": self.total_gaps,
            "summary_by_type": self.summary_by_type,
            "gaps": [
                {
                    "order_id": g.order_id,
                    "order_number": g.order_number,
                    "order_status": g.order_status,
                    "production_order_id": g.production_order_id,
                    "production_status": g.production_status,
                    "gap_type": g.gap_type,
                    "expected_sku": g.expected_sku,
                    "expected_quantity": float(g.expected_quantity) if g.expected_quantity else None,
                    "details": g.details,
                }
                for g in self.gaps
            ],
        }


class TransactionAuditService:
    """
    Audits inventory transactions to find gaps in the order-to-ship lifecycle.
    """

    def __init__(self, db: Session):
        self.db = db

    def run_full_audit(self,
                       include_statuses: List[str] = None,
                       order_ids: List[int] = None) -> AuditResult:
        """
        Run a full audit of all orders or specific orders.

        Args:
            include_statuses: Filter to specific order statuses
            order_ids: Audit specific order IDs only
        """
        result = AuditResult(
            audit_timestamp=datetime.utcnow(),
            total_orders_checked=0,
            orders_with_gaps=0,
            total_gaps=0,
        )

        # Build query
        query = self.db.query(SalesOrder)

        if order_ids:
            query = query.filter(SalesOrder.id.in_(order_ids))
        elif include_statuses:
            query = query.filter(SalesOrder.status.in_(include_statuses))
        else:
            # Default: check orders that should have transactions
            query = query.filter(SalesOrder.status.in_([
                'in_production', 'ready_to_ship', 'shipped', 'delivered'
            ]))

        orders = query.all()
        result.total_orders_checked = len(orders)

        orders_with_issues = set()

        for order in orders:
            gaps = self._audit_order(order)
            if gaps:
                orders_with_issues.add(order.id)
                result.gaps.extend(gaps)

        result.orders_with_gaps = len(orders_with_issues)
        result.total_gaps = len(result.gaps)

        # Summarize by gap type
        for gap in result.gaps:
            result.summary_by_type[gap.gap_type] = result.summary_by_type.get(gap.gap_type, 0) + 1

        return result

    def _audit_order(self, order: SalesOrder) -> List[TransactionGap]:
        """Audit a single sales order for transaction gaps."""
        gaps = []

        # Get production orders for this sales order
        production_orders = self.db.query(ProductionOrder).filter(
            ProductionOrder.sales_order_id == order.id
        ).all()

        if not production_orders and order.status in ['in_production', 'ready_to_ship', 'shipped']:
            gaps.append(TransactionGap(
                order_id=order.id,
                order_number=order.order_number,
                order_status=order.status,
                production_order_id=None,
                production_status=None,
                gap_type='missing_production_order',
                expected_product_id=None,
                expected_sku=None,
                expected_quantity=None,
                details=f"Order {order.order_number} is {order.status} but has no production order"
            ))
            return gaps

        for po in production_orders:
            po_gaps = self._audit_production_order(order, po)
            gaps.extend(po_gaps)

        return gaps

    def _audit_production_order(self, order: SalesOrder, po: ProductionOrder) -> List[TransactionGap]:
        """Audit a single production order for expected transactions."""
        gaps = []

        # Get BOM for this production order
        bom = self._get_bom_for_po(po)

        if not bom and po.status not in ['pending', 'scheduled']:
            gaps.append(TransactionGap(
                order_id=order.id,
                order_number=order.order_number,
                order_status=order.status,
                production_order_id=po.id,
                production_status=po.status,
                gap_type='missing_bom',
                expected_product_id=po.product_id,
                expected_sku=None,
                expected_quantity=None,
                details=f"Production order {po.code} has no BOM"
            ))
            return gaps

        # Check transactions based on production order status
        if po.status in ['in_progress', 'printed', 'completed']:
            # Should have reservations from start_production
            reservation_gaps = self._check_reservations(order, po, bom)
            gaps.extend(reservation_gaps)

        if po.status in ['printed', 'completed']:
            # Should have material consumption from complete_print
            consumption_gaps = self._check_material_consumption(order, po, bom)
            gaps.extend(consumption_gaps)

            # Should have finished goods receipt
            receipt_gaps = self._check_finished_goods_receipt(order, po)
            gaps.extend(receipt_gaps)

        if order.status == 'shipped':
            # Should have packaging consumption from buy_label
            packaging_gaps = self._check_packaging_consumption(order, po, bom)
            gaps.extend(packaging_gaps)

        return gaps

    def _get_bom_for_po(self, po: ProductionOrder) -> Optional[BOM]:
        """Get the BOM for a production order."""
        if po.bom_id:
            return self.db.query(BOM).filter(BOM.id == po.bom_id).first()
        elif po.product_id:
            return self.db.query(BOM).filter(
                BOM.product_id == po.product_id,
                BOM.active.is_(True)
            ).first()
        return None

    def _check_reservations(self, order: SalesOrder, po: ProductionOrder, bom: Optional[BOM]) -> List[TransactionGap]:
        """Check that material reservations exist for production-stage BOM items."""
        gaps = []

        if not bom or not bom.lines:
            return gaps

        from app.models.product import Product

        for line in bom.lines:
            # Check production-stage items (materials)
            consume_stage = getattr(line, 'consume_stage', 'production')
            if consume_stage != 'production':
                continue

            # Skip non-inventory cost items - they're for job costing, not physical inventory
            # SVC-* = legacy services, MFG-* = manufacturing overhead (machine time)
            component = self.db.query(Product).filter(Product.id == line.component_id).first()
            if component and component.sku.startswith(("SVC-", "MFG-")):
                continue

            # Look for reservation transaction
            reservation = self.db.query(InventoryTransaction).filter(
                InventoryTransaction.reference_type == 'production_order',
                InventoryTransaction.reference_id == po.id,
                InventoryTransaction.product_id == line.component_id,
                InventoryTransaction.transaction_type == 'reservation'
            ).first()

            if not reservation:
                from app.models.product import Product
                component = self.db.query(Product).filter(Product.id == line.component_id).first()

                gaps.append(TransactionGap(
                    order_id=order.id,
                    order_number=order.order_number,
                    order_status=order.status,
                    production_order_id=po.id,
                    production_status=po.status,
                    gap_type='missing_material_reservation',
                    expected_product_id=line.component_id,
                    expected_sku=component.sku if component else None,
                    expected_quantity=line.quantity,
                    details=f"Missing reservation for {component.sku if component else line.component_id}"
                ))

        return gaps

    def _check_material_consumption(self, order: SalesOrder, po: ProductionOrder, bom: Optional[BOM]) -> List[TransactionGap]:
        """Check that material consumption transactions exist after print completion."""
        gaps = []

        if not bom or not bom.lines:
            return gaps

        from app.models.product import Product

        for line in bom.lines:
            consume_stage = getattr(line, 'consume_stage', 'production')
            if consume_stage != 'production':
                continue

            # Skip non-inventory cost items (SVC-*, MFG-*)
            component = self.db.query(Product).filter(Product.id == line.component_id).first()
            if component and component.sku.startswith(("SVC-", "MFG-")):
                continue

            consumption = self.db.query(InventoryTransaction).filter(
                InventoryTransaction.reference_type == 'production_order',
                InventoryTransaction.reference_id == po.id,
                InventoryTransaction.product_id == line.component_id,
                InventoryTransaction.transaction_type == 'consumption'
            ).first()

            if not consumption:
                from app.models.product import Product
                component = self.db.query(Product).filter(Product.id == line.component_id).first()

                gaps.append(TransactionGap(
                    order_id=order.id,
                    order_number=order.order_number,
                    order_status=order.status,
                    production_order_id=po.id,
                    production_status=po.status,
                    gap_type='missing_material_consumption',
                    expected_product_id=line.component_id,
                    expected_sku=component.sku if component else None,
                    expected_quantity=line.quantity,
                    details=f"Missing consumption for {component.sku if component else line.component_id}"
                ))

        return gaps

    def _check_finished_goods_receipt(self, order: SalesOrder, po: ProductionOrder) -> List[TransactionGap]:
        """Check that finished goods were received after print completion."""
        gaps = []

        # Look for receipt of finished goods
        receipt = self.db.query(InventoryTransaction).filter(
            InventoryTransaction.reference_type == 'production_order',
            InventoryTransaction.reference_id == po.id,
            InventoryTransaction.transaction_type == 'receipt'
        ).first()

        if not receipt:
            from app.models.product import Product
            product = self.db.query(Product).filter(Product.id == po.product_id).first() if po.product_id else None

            gaps.append(TransactionGap(
                order_id=order.id,
                order_number=order.order_number,
                order_status=order.status,
                production_order_id=po.id,
                production_status=po.status,
                gap_type='missing_finished_goods_receipt',
                expected_product_id=po.product_id,
                expected_sku=product.sku if product else None,
                expected_quantity=Decimal(str(po.quantity)),
                details=f"No finished goods receipt for {product.sku if product else 'unknown product'}"
            ))

        return gaps

    def _check_packaging_consumption(self, order: SalesOrder, po: ProductionOrder, bom: Optional[BOM]) -> List[TransactionGap]:
        """Check that shipping-stage items (packaging) were consumed at shipping."""
        gaps = []

        if not bom or not bom.lines:
            return gaps

        for line in bom.lines:
            consume_stage = getattr(line, 'consume_stage', 'production')
            if consume_stage != 'shipping':
                continue

            # Look for consumption at shipping (reference_type = 'shipment')
            consumption = self.db.query(InventoryTransaction).filter(
                InventoryTransaction.reference_type.in_(['shipment', 'consolidated_shipment']),
                InventoryTransaction.reference_id == order.id,
                InventoryTransaction.product_id == line.component_id,
                InventoryTransaction.transaction_type == 'consumption'
            ).first()

            if not consumption:
                from app.models.product import Product
                component = self.db.query(Product).filter(Product.id == line.component_id).first()

                gaps.append(TransactionGap(
                    order_id=order.id,
                    order_number=order.order_number,
                    order_status=order.status,
                    production_order_id=po.id,
                    production_status=po.status,
                    gap_type='missing_packaging_consumption',
                    expected_product_id=line.component_id,
                    expected_sku=component.sku if component else None,
                    expected_quantity=line.quantity,
                    details=f"Missing packaging consumption for {component.sku if component else line.component_id}"
                ))

        return gaps

    def audit_single_order(self, order_id: int) -> AuditResult:
        """Convenience method to audit a single order."""
        return self.run_full_audit(order_ids=[order_id])

    def get_transaction_timeline(self, order_id: int) -> List[Dict[str, Any]]:
        """
        Get all transactions related to an order in chronological order.
        Useful for debugging what actually happened.
        """
        order = self.db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
        if not order:
            return []

        # Get production orders
        production_orders = self.db.query(ProductionOrder).filter(
            ProductionOrder.sales_order_id == order_id
        ).all()

        po_ids = [po.id for po in production_orders]

        # Get all related transactions
        transactions = self.db.query(InventoryTransaction).filter(
            # Production order related
            ((InventoryTransaction.reference_type == 'production_order') &
             (InventoryTransaction.reference_id.in_(po_ids))) |
            # Shipment related
            ((InventoryTransaction.reference_type.in_(['shipment', 'consolidated_shipment'])) &
             (InventoryTransaction.reference_id == order_id))
        ).order_by(InventoryTransaction.created_at).all()

        from app.models.product import Product

        timeline = []
        for txn in transactions:
            product = self.db.query(Product).filter(Product.id == txn.product_id).first()

            timeline.append({
                "timestamp": txn.created_at.isoformat() if txn.created_at else None,
                "transaction_type": txn.transaction_type,
                "reference_type": txn.reference_type,
                "reference_id": txn.reference_id,
                "product_id": txn.product_id,
                "product_sku": product.sku if product else None,
                "quantity": float(txn.quantity) if txn.quantity else 0,
                "notes": txn.notes,
            })

        return timeline
