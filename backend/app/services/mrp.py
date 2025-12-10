"""
MRP (Material Requirements Planning) Service

Core MRP calculation logic:
1. BOM Explosion - recursively expand BOMs to get all component requirements
2. Net Requirements - compare gross requirements vs available inventory
3. Planned Orders - generate purchase/production orders for shortages
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Product, BOM, BOMLine, Inventory, ProductionOrder,
    PurchaseOrder, PurchaseOrderLine, MRPRun, PlannedOrder
)


# ============================================================================
# Data Classes for MRP Calculations
# ============================================================================

@dataclass
class ComponentRequirement:
    """A single component requirement from BOM explosion"""
    product_id: int
    product_sku: str
    product_name: str
    bom_level: int
    gross_quantity: Decimal
    scrap_factor: Decimal = Decimal("0")
    parent_product_id: Optional[int] = None
    source_demand_type: Optional[str] = None
    source_demand_id: Optional[int] = None
    due_date: Optional[date] = None


@dataclass
class NetRequirement:
    """Net requirement after inventory netting"""
    product_id: int
    product_sku: str
    product_name: str
    gross_quantity: Decimal
    on_hand_quantity: Decimal
    allocated_quantity: Decimal
    available_quantity: Decimal
    incoming_quantity: Decimal
    safety_stock: Decimal
    net_shortage: Decimal
    lead_time_days: int
    reorder_point: Optional[Decimal] = None
    min_order_qty: Optional[Decimal] = None
    item_type: str = "component"


@dataclass
class MRPResult:
    """Result of an MRP run"""
    run_id: int
    orders_processed: int = 0
    components_analyzed: int = 0
    shortages_found: int = 0
    planned_orders_created: int = 0
    requirements: List[NetRequirement] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# ============================================================================
# MRP Service
# ============================================================================

class MRPService:
    """Material Requirements Planning service"""

    def __init__(self, db: Session):
        self.db = db

    def run_mrp(
        self,
        planning_horizon_days: int = 30,
        include_draft_orders: bool = True,
        regenerate_planned: bool = True,
        user_id: Optional[int] = None
    ) -> MRPResult:
        """
        Run full MRP calculation.

        Args:
            planning_horizon_days: How far ahead to plan
            include_draft_orders: Include draft production orders in demand
            regenerate_planned: Delete existing unfirmed planned orders first
            user_id: User running the MRP

        Returns:
            MRPResult with statistics and generated orders
        """
        # Create MRP run record
        mrp_run = MRPRun(
            run_date=datetime.utcnow(),
            planning_horizon_days=planning_horizon_days,
            status="running",
            created_by=user_id
        )
        self.db.add(mrp_run)
        self.db.flush()

        result = MRPResult(run_id=mrp_run.id)

        try:
            # Step 1: Delete unfirmed planned orders if requested
            if regenerate_planned:
                self._delete_unfirmed_planned_orders()

            # Step 2: Get production orders within planning horizon
            horizon_date = date.today() + timedelta(days=planning_horizon_days)
            production_orders = self._get_production_orders(
                horizon_date, include_draft_orders
            )
            result.orders_processed = len(production_orders)

            # Step 3: Explode BOMs for all production orders
            all_requirements: Dict[int, ComponentRequirement] = {}
            for po in production_orders:
                requirements = self.explode_bom(
                    product_id=po.product_id,
                    quantity=po.quantity_ordered - po.quantity_completed,
                    source_demand_type="production_order",
                    source_demand_id=po.id,
                    due_date=po.due_date or date.today()
                )
                # Aggregate by product_id
                for req in requirements:
                    if req.product_id in all_requirements:
                        all_requirements[req.product_id].gross_quantity += req.gross_quantity
                    else:
                        all_requirements[req.product_id] = req

            result.components_analyzed = len(all_requirements)

            # Step 4: Calculate net requirements
            net_requirements = self.calculate_net_requirements(
                list(all_requirements.values())
            )
            result.requirements = net_requirements

            # Step 5: Generate planned orders for shortages
            shortages = [r for r in net_requirements if r.net_shortage > 0]
            result.shortages_found = len(shortages)

            planned_orders = self.generate_planned_orders(
                shortages, mrp_run.id, user_id
            )
            result.planned_orders_created = len(planned_orders)

            # Update MRP run record
            mrp_run.status = "completed"
            mrp_run.orders_processed = result.orders_processed
            mrp_run.components_analyzed = result.components_analyzed
            mrp_run.shortages_found = result.shortages_found
            mrp_run.planned_orders_created = result.planned_orders_created
            mrp_run.completed_at = datetime.utcnow()

            self.db.commit()

        except Exception as e:
            mrp_run.status = "failed"
            mrp_run.error_message = str(e)
            self.db.commit()
            result.errors.append(str(e))
            raise

        return result

    def explode_bom(
        self,
        product_id: int,
        quantity: Decimal,
        source_demand_type: Optional[str] = None,
        source_demand_id: Optional[int] = None,
        due_date: Optional[date] = None,
        level: int = 0,
        parent_product_id: Optional[int] = None,
        visited: Optional[set] = None
    ) -> List[ComponentRequirement]:
        """
        Recursively explode a BOM to get all component requirements.

        Handles multi-level BOMs and detects circular references.

        Args:
            product_id: Product to explode
            quantity: Quantity needed
            source_demand_type: What triggered this demand
            source_demand_id: ID of source demand
            due_date: When material is needed
            level: Current BOM level (0=direct components)
            parent_product_id: Parent product in explosion
            visited: Set of visited product_ids to detect cycles

        Returns:
            List of ComponentRequirement for all components at all levels
        """
        if visited is None:
            visited = set()

        # Circular reference detection
        if product_id in visited:
            return []
        visited.add(product_id)

        requirements = []

        # Get active BOM for this product
        bom = self.db.query(BOM).filter(
            BOM.product_id == product_id,
            BOM.active.is_(True)
        ).first()

        if not bom:
            # No BOM = no components needed
            visited.discard(product_id)
            return requirements

        # Process each BOM line
        for line in bom.lines:
            component = line.component

            # Calculate quantity with scrap factor
            scrap_factor = Decimal(str(line.scrap_factor or 0))
            adjusted_qty = quantity * line.quantity * (1 + scrap_factor / 100)

            req = ComponentRequirement(
                product_id=component.id,
                product_sku=component.sku,
                product_name=component.name,
                bom_level=level,
                gross_quantity=adjusted_qty,
                scrap_factor=scrap_factor,
                parent_product_id=parent_product_id or product_id,
                source_demand_type=source_demand_type,
                source_demand_id=source_demand_id,
                due_date=due_date
            )
            requirements.append(req)

            # Recursively explode if component has a BOM
            if component.has_bom:
                sub_requirements = self.explode_bom(
                    product_id=component.id,
                    quantity=adjusted_qty,
                    source_demand_type=source_demand_type,
                    source_demand_id=source_demand_id,
                    due_date=due_date,
                    level=level + 1,
                    parent_product_id=product_id,
                    visited=visited.copy()
                )
                requirements.extend(sub_requirements)

        visited.discard(product_id)
        return requirements

    def calculate_net_requirements(
        self,
        requirements: List[ComponentRequirement]
    ) -> List[NetRequirement]:
        """
        Calculate net requirements by comparing gross requirements to available inventory.

        Formula: Net = Gross - Available - Incoming + Safety Stock

        Args:
            requirements: List of gross component requirements

        Returns:
            List of NetRequirement with shortage calculations
        """
        net_requirements = []
        product_ids = [r.product_id for r in requirements]

        # Get inventory levels for all products at once
        inventory_by_product = self._get_inventory_levels(product_ids)

        # Get incoming supply (open POs)
        incoming_by_product = self._get_incoming_supply(product_ids)

        # Get product details
        products = {
            p.id: p for p in
            self.db.query(Product).filter(Product.id.in_(product_ids)).all()
        }

        for req in requirements:
            product = products.get(req.product_id)
            if not product:
                continue

            inv = inventory_by_product.get(req.product_id, {
                "on_hand": Decimal("0"),
                "allocated": Decimal("0"),
                "available": Decimal("0")
            })
            incoming = incoming_by_product.get(req.product_id, Decimal("0"))
            safety_stock = Decimal(str(product.safety_stock or 0))

            # Net requirement calculation
            # Net = Gross - Available - Incoming + Safety Stock
            available_supply = inv["available"] + incoming
            net_shortage = req.gross_quantity - available_supply + safety_stock

            # Don't report negative shortages
            if net_shortage < 0:
                net_shortage = Decimal("0")

            net_req = NetRequirement(
                product_id=req.product_id,
                product_sku=req.product_sku,
                product_name=req.product_name,
                gross_quantity=req.gross_quantity,
                on_hand_quantity=inv["on_hand"],
                allocated_quantity=inv["allocated"],
                available_quantity=inv["available"],
                incoming_quantity=incoming,
                safety_stock=safety_stock,
                net_shortage=net_shortage,
                lead_time_days=product.lead_time_days or 7,
                reorder_point=product.reorder_point,
                min_order_qty=product.min_order_qty,
                item_type=product.item_type or "component"
            )
            net_requirements.append(net_req)

        return net_requirements

    def generate_planned_orders(
        self,
        shortages: List[NetRequirement],
        mrp_run_id: int,
        user_id: Optional[int] = None
    ) -> List[PlannedOrder]:
        """
        Generate planned orders for material shortages.

        Creates purchase orders for raw materials/supplies and
        production orders for items with BOMs.

        Args:
            shortages: List of NetRequirement with shortages
            mrp_run_id: ID of the MRP run
            user_id: User running MRP

        Returns:
            List of created PlannedOrder records
        """
        planned_orders = []

        for shortage in shortages:
            if shortage.net_shortage <= 0:
                continue

            # Get the product to determine order type
            product = self.db.query(Product).get(shortage.product_id)
            if not product:
                continue

            # Determine order type based on item type and BOM
            if product.has_bom:
                order_type = "production"
            else:
                order_type = "purchase"

            # Apply minimum order quantity
            order_qty = shortage.net_shortage
            if shortage.min_order_qty and order_qty < shortage.min_order_qty:
                order_qty = shortage.min_order_qty

            # Calculate dates with lead time offset
            due_date = date.today() + timedelta(days=14)  # Default 2 weeks
            lead_time = shortage.lead_time_days or 7
            start_date = due_date - timedelta(days=lead_time)

            # Don't create orders with start dates in the past
            if start_date < date.today():
                start_date = date.today()

            planned_order = PlannedOrder(
                order_type=order_type,
                product_id=shortage.product_id,
                quantity=order_qty,
                due_date=due_date,
                start_date=start_date,
                source_demand_type="mrp_calculation",
                mrp_run_id=mrp_run_id,
                status="planned",
                created_by=user_id,
                created_at=datetime.utcnow()
            )
            self.db.add(planned_order)
            planned_orders.append(planned_order)

        self.db.flush()
        return planned_orders

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_production_orders(
        self,
        horizon_date: date,
        include_draft: bool
    ) -> List[ProductionOrder]:
        """Get production orders within planning horizon"""
        statuses = ["released", "in_progress"]
        if include_draft:
            statuses.append("draft")

        return self.db.query(ProductionOrder).filter(
            ProductionOrder.status.in_(statuses),
            ProductionOrder.due_date <= horizon_date if ProductionOrder.due_date else True
        ).all()

    def _get_inventory_levels(
        self,
        product_ids: List[int]
    ) -> Dict[int, Dict[str, Decimal]]:
        """Get inventory levels for multiple products"""
        result = {}

        # Sum inventory across all locations
        inventory_query = self.db.query(
            Inventory.product_id,
            func.sum(Inventory.on_hand_quantity).label("on_hand"),
            func.sum(Inventory.allocated_quantity).label("allocated")
        ).filter(
            Inventory.product_id.in_(product_ids)
        ).group_by(Inventory.product_id).all()

        for row in inventory_query:
            on_hand = Decimal(str(row.on_hand or 0))
            allocated = Decimal(str(row.allocated or 0))
            result[row.product_id] = {
                "on_hand": on_hand,
                "allocated": allocated,
                "available": on_hand - allocated
            }

        return result

    def _get_incoming_supply(
        self,
        product_ids: List[int]
    ) -> Dict[int, Decimal]:
        """Get incoming supply from open purchase orders"""
        result = defaultdict(Decimal)

        # Query open PO lines
        open_statuses = ["draft", "ordered", "partially_received"]
        po_lines = self.db.query(
            PurchaseOrderLine.product_id,
            func.sum(
                PurchaseOrderLine.quantity_ordered - PurchaseOrderLine.quantity_received
            ).label("incoming")
        ).join(PurchaseOrder).filter(
            PurchaseOrderLine.product_id.in_(product_ids),
            PurchaseOrder.status.in_(open_statuses)
        ).group_by(PurchaseOrderLine.product_id).all()

        for row in po_lines:
            result[row.product_id] = Decimal(str(row.incoming or 0))

        return dict(result)

    def _delete_unfirmed_planned_orders(self):
        """Delete planned orders that haven't been firmed"""
        self.db.query(PlannedOrder).filter(
            PlannedOrder.status == "planned"
        ).delete()
        self.db.flush()

    # ========================================================================
    # Planned Order Actions
    # ========================================================================

    def firm_planned_order(
        self,
        planned_order_id: int,
        user_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> PlannedOrder:
        """
        Firm a planned order - locks it so MRP won't delete it.
        """
        order = self.db.query(PlannedOrder).get(planned_order_id)
        if not order:
            raise ValueError(f"Planned order {planned_order_id} not found")

        if order.status != "planned":
            raise ValueError(f"Can only firm orders with status 'planned', got '{order.status}'")

        order.status = "firmed"
        order.firmed_at = datetime.utcnow()
        if notes:
            order.notes = (order.notes or "") + f"\nFirmed: {notes}"

        self.db.commit()
        return order

    def release_planned_order(
        self,
        planned_order_id: int,
        vendor_id: Optional[int] = None,
        user_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Tuple[PlannedOrder, Optional[int]]:
        """
        Release a planned order - converts it to an actual PO or MO.

        Returns:
            Tuple of (PlannedOrder, created_order_id)
        """
        order = self.db.query(PlannedOrder).get(planned_order_id)
        if not order:
            raise ValueError(f"Planned order {planned_order_id} not found")

        if order.status not in ("planned", "firmed"):
            raise ValueError(f"Cannot release order with status '{order.status}'")

        created_order_id = None

        if order.order_type == "purchase":
            if not vendor_id:
                raise ValueError("vendor_id required for purchase orders")
            created_order_id = self._create_purchase_order(order, vendor_id, user_id)
            order.converted_to_po_id = created_order_id
        else:
            created_order_id = self._create_production_order(order, user_id)
            order.converted_to_mo_id = created_order_id

        order.status = "released"
        order.released_at = datetime.utcnow()
        if notes:
            order.notes = (order.notes or "") + f"\nReleased: {notes}"

        self.db.commit()
        return order, created_order_id

    def _create_purchase_order(
        self,
        planned_order: PlannedOrder,
        vendor_id: int,
        user_id: Optional[int]
    ) -> int:
        """Create a purchase order from a planned order"""
        # Generate PO number
        year = datetime.utcnow().year
        last_po = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.po_number.like(f"PO-{year}-%")
        ).order_by(PurchaseOrder.po_number.desc()).first()

        if last_po:
            last_num = int(last_po.po_number.split("-")[2])
            next_num = last_num + 1
        else:
            next_num = 1

        po_number = f"PO-{year}-{next_num:04d}"

        # Get product for cost
        product = self.db.query(Product).get(planned_order.product_id)
        unit_cost = product.standard_cost or product.last_cost or Decimal("0")

        # Create PO
        po = PurchaseOrder(
            po_number=po_number,
            vendor_id=vendor_id,
            status="draft",
            order_date=date.today(),
            expected_date=planned_order.due_date,
            notes=f"Created from planned order {planned_order.id}",
            created_by=str(user_id) if user_id else None
        )
        self.db.add(po)
        self.db.flush()

        # Create PO line
        line = PurchaseOrderLine(
            purchase_order_id=po.id,
            product_id=planned_order.product_id,
            line_number=1,
            quantity_ordered=planned_order.quantity,
            quantity_received=Decimal("0"),
            unit_cost=unit_cost,
            line_total=unit_cost * planned_order.quantity
        )
        self.db.add(line)

        # Update PO totals
        po.subtotal = line.line_total
        po.total_amount = line.line_total

        return po.id

    def _create_production_order(
        self,
        planned_order: PlannedOrder,
        user_id: Optional[int]
    ) -> int:
        """Create a production order from a planned order"""
        # Generate PO code (Production Order)
        year = datetime.utcnow().year
        last_po = self.db.query(ProductionOrder).filter(
            ProductionOrder.code.like(f"PO-{year}-%")
        ).order_by(ProductionOrder.code.desc()).first()

        if last_po:
            last_num = int(last_po.code.split("-")[2])
            next_num = last_num + 1
        else:
            next_num = 1

        po_code = f"PO-{year}-{next_num:04d}"

        # Get active BOM for product
        bom = self.db.query(BOM).filter(
            BOM.product_id == planned_order.product_id,
            BOM.active.is_(True)
        ).first()

        po = ProductionOrder(
            code=po_code,
            product_id=planned_order.product_id,
            bom_id=bom.id if bom else None,
            quantity_ordered=planned_order.quantity,
            quantity_completed=Decimal("0"),
            quantity_scrapped=Decimal("0"),
            status="draft",
            source="mrp_planned",
            due_date=planned_order.due_date,
            notes=f"Created from planned order {planned_order.id}",
            created_by=str(user_id) if user_id else None
        )
        self.db.add(po)
        self.db.flush()

        return po.id

    # ========================================================================
    # Supply/Demand Timeline
    # ========================================================================

    def get_supply_demand_timeline(
        self,
        product_id: int,
        days_ahead: int = 30
    ) -> Dict:
        """
        Get supply and demand timeline for a product.

        Returns chronological list of supply/demand events with running balance.
        """
        product = self.db.query(Product).get(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        # Get current inventory
        inv_total = self.db.query(
            func.sum(Inventory.on_hand_quantity),
            func.sum(Inventory.allocated_quantity)
        ).filter(Inventory.product_id == product_id).first()

        on_hand = Decimal(str(inv_total[0] or 0))
        allocated = Decimal(str(inv_total[1] or 0))
        available = on_hand - allocated

        entries = []
        running_balance = available

        # Starting point
        entries.append({
            "date": date.today(),
            "entry_type": "on_hand",
            "source_type": "inventory",
            "source_id": None,
            "source_code": None,
            "quantity": available,
            "running_balance": running_balance
        })

        horizon = date.today() + timedelta(days=days_ahead)

        # Get demand from production orders (as component)
        # This requires BOM explosion which is expensive, so we simplify
        # by just looking at direct demand from production orders
        demands = self._get_product_demands(product_id, horizon)
        supplies = self._get_product_supplies(product_id, horizon)

        # Combine and sort by date
        all_events = demands + supplies
        all_events.sort(key=lambda x: (x["date"], x["entry_type"] == "demand"))

        for event in all_events:
            if event["entry_type"] == "demand":
                running_balance -= event["quantity"]
            else:
                running_balance += event["quantity"]
            event["running_balance"] = running_balance
            entries.append(event)

        # Find projected shortage date
        shortage_date = None
        safety_stock = Decimal(str(product.safety_stock or 0))
        for entry in entries:
            if entry["running_balance"] < safety_stock:
                shortage_date = entry["date"]
                break

        # Calculate days of supply
        daily_demand = sum(
            e["quantity"] for e in entries
            if e["entry_type"] == "demand"
        )
        if daily_demand > 0 and days_ahead > 0:
            avg_daily = daily_demand / days_ahead
            if avg_daily > 0:
                days_of_supply = int(available / avg_daily)
            else:
                days_of_supply = None
        else:
            days_of_supply = None

        return {
            "product_id": product_id,
            "product_sku": product.sku,
            "product_name": product.name,
            "current_on_hand": on_hand,
            "current_available": available,
            "safety_stock": safety_stock,
            "entries": entries,
            "projected_shortage_date": shortage_date,
            "days_of_supply": days_of_supply
        }

    def _get_product_demands(self, product_id: int, horizon: date) -> List[Dict]:
        """Get demand events for a product"""
        demands = []

        # Production orders where this product IS the product being made
        # (these consume components, not this item)
        # Instead, look for production orders that CONSUME this product via BOM

        # For simplicity, check if this is a component in any active production orders
        # This is expensive, so in a real system you'd maintain a demand table

        # Simplified: just return empty for now
        # Full implementation would query BOM lines and trace back to production orders

        return demands

    def _get_product_supplies(self, product_id: int, horizon: date) -> List[Dict]:
        """Get supply events for a product"""
        supplies = []

        # Open purchase order lines
        po_lines = self.db.query(PurchaseOrderLine, PurchaseOrder).join(
            PurchaseOrder
        ).filter(
            PurchaseOrderLine.product_id == product_id,
            PurchaseOrder.status.in_(["draft", "ordered", "partially_received"]),
            PurchaseOrder.expected_date <= horizon if PurchaseOrder.expected_date else True
        ).all()

        for line, po in po_lines:
            incoming = line.quantity_ordered - line.quantity_received
            if incoming > 0:
                supplies.append({
                    "date": po.expected_date or date.today(),
                    "entry_type": "supply",
                    "source_type": "purchase_order",
                    "source_id": po.id,
                    "source_code": po.po_number,
                    "quantity": incoming,
                    "running_balance": None
                })

        # Planned orders
        planned = self.db.query(PlannedOrder).filter(
            PlannedOrder.product_id == product_id,
            PlannedOrder.status.in_(["planned", "firmed"]),
            PlannedOrder.due_date <= horizon
        ).all()

        for po in planned:
            supplies.append({
                "date": po.due_date,
                "entry_type": "supply",
                "source_type": "planned_order",
                "source_id": po.id,
                "source_code": f"PLN-{po.id}",
                "quantity": po.quantity,
                "running_balance": None
            })

        return supplies
