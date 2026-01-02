"""
Production Order model

Manufacturing Orders (MOs) track the production of finished goods.
Integrates with:
- BOMs (materials to consume)
- Routings (process steps to follow)
- Work Centers & Resources (where/how work happens)
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class ProductionOrder(Base):
    """
    Production Order (Manufacturing Order) - the core scheduling entity.

    Lifecycle: draft → released → in_progress → complete

    Can be created from:
    - Manual entry
    - Sales order demand
    - MRP planned orders
    """
    __tablename__ = "production_orders"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)

    # References (all indexed for query performance)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, index=True)
    bom_id = Column(Integer, ForeignKey('boms.id'), nullable=True, index=True)
    routing_id = Column(Integer, ForeignKey('routings.id'), nullable=True, index=True)
    sales_order_id = Column(Integer, ForeignKey('sales_orders.id'), nullable=True, index=True)
    sales_order_line_id = Column(Integer, ForeignKey('sales_order_lines.id'), nullable=True, index=True)

    # Parent/Child for split orders
    parent_order_id = Column(Integer, ForeignKey('production_orders.id'), nullable=True, index=True)
    split_sequence = Column(Integer, nullable=True)  # 1, 2, 3... for child orders

    # Quantities
    quantity_ordered = Column(Numeric(18, 4), nullable=False)
    quantity_completed = Column(Numeric(18, 4), default=0, nullable=False)
    quantity_scrapped = Column(Numeric(18, 4), default=0, nullable=False)

    # Legacy alias for quantity_ordered
    @property
    def quantity(self):
        return self.quantity_ordered

    # Source: manual, sales_order, mrp_planned
    source = Column(String(50), default='manual', nullable=False)

    # Status (Manufacturing Workflow)
    # Lifecycle: draft → released → scheduled → in_progress → completed → closed
    # QC paths: completed → qc_hold → (scrapped | rework | closed)
    # Status meanings:
    #   - draft: Created but not ready for production
    #   - released: Materials allocated, ready to schedule
    #   - scheduled: Assigned to work center/printer, queued
    #   - in_progress: Job actively running
    #   - completed: Job finished, awaiting QC
    #   - qc_hold: QC inspection failed, awaiting decision
    #   - scrapped: Parts rejected, needs remake
    #   - closed: Parts accepted, inventory updated, WO complete
    #   - cancelled: WO terminated
    #   - on_hold: Production paused
    status = Column(String(50), default='draft', nullable=False, index=True)

    # QC Status (Quality Control)
    # Values: not_required, pending, in_progress, passed, failed, waived
    # Workflow: completed → pending → in_progress → (passed | failed)
    #   - not_required: Auto-pass for trusted products
    #   - pending: Awaiting QC inspector assignment
    #   - in_progress: Inspector reviewing parts
    #   - passed: Parts accepted, ready for inventory
    #   - failed: Parts rejected, WO moves to qc_hold status
    #   - waived: Failed but accepted anyway (document reason in notes)
    qc_status = Column(String(50), default='not_required', nullable=False)
    qc_notes = Column(Text, nullable=True)
    qc_inspected_by = Column(String(100), nullable=True)
    qc_inspected_at = Column(DateTime, nullable=True)

    # Priority: 1 (highest) to 5 (lowest)
    priority = Column(Integer, default=3, nullable=False)

    # Scheduling
    due_date = Column(Date, nullable=True, index=True)
    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)

    # Time tracking (minutes)
    estimated_time_minutes = Column(Integer, nullable=True)
    actual_time_minutes = Column(Integer, nullable=True)

    # Costs
    estimated_material_cost = Column(Numeric(18, 4), nullable=True)
    estimated_labor_cost = Column(Numeric(18, 4), nullable=True)
    estimated_total_cost = Column(Numeric(18, 4), nullable=True)
    actual_material_cost = Column(Numeric(18, 4), nullable=True)
    actual_labor_cost = Column(Numeric(18, 4), nullable=True)
    actual_total_cost = Column(Numeric(18, 4), nullable=True)

    # Assignment
    assigned_to = Column(String(100), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Scrap/Remake tracking
    scrap_reason = Column(String(100), nullable=True)  # adhesion, layer_shift, stringing, warping, nozzle_clog, other
    scrapped_at = Column(DateTime, nullable=True)
    remake_of_id = Column(Integer, ForeignKey('production_orders.id'), nullable=True)  # Links remake to original failed WO

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    released_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    product = relationship("Product", back_populates="production_orders")
    bom = relationship("BOM", foreign_keys=[bom_id])
    routing = relationship("Routing", foreign_keys=[routing_id])
    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id], backref="production_orders")
    print_jobs = relationship("PrintJob", back_populates="production_order")
    operations = relationship("ProductionOrderOperation", back_populates="production_order",
                              cascade="all, delete-orphan", order_by="ProductionOrderOperation.sequence")
    # Parent/Child split relationships
    parent_order = relationship("ProductionOrder", remote_side=[id], backref="child_orders", foreign_keys=[parent_order_id])
    # Scrap/Remake relationships
    original_order = relationship("ProductionOrder", remote_side=[id], backref="remakes", foreign_keys=[remake_of_id])
    # Spool tracking
    spools_used = relationship("ProductionOrderSpool", back_populates="production_order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProductionOrder {self.code}: {self.quantity_ordered} x {self.product.sku if self.product else 'N/A'}>"

    @property
    def quantity_remaining(self):
        """Quantity still to produce"""
        return float(self.quantity_ordered or 0) - float(self.quantity_completed or 0)

    @property
    def completion_percent(self):
        """Percentage complete"""
        if not self.quantity_ordered:
            return 0
        return round((float(self.quantity_completed or 0) / float(self.quantity_ordered)) * 100, 1)

    @property
    def is_complete(self):
        """True if all quantity is completed"""
        return self.quantity_remaining <= 0

    @property
    def is_scrapped(self):
        """True if this WO was scrapped"""
        return self.status == 'scrapped' or self.scrapped_at is not None

    @property
    def is_remake(self):
        """True if this WO is a remake of a failed WO"""
        return self.remake_of_id is not None
    
    @property
    def is_qc_required(self):
        """True if QC inspection is required"""
        return self.qc_status != 'not_required'
    
    @property
    def is_ready_for_qc(self):
        """True if WO is ready for quality inspection"""
        return self.status == 'completed' and self.qc_status == 'pending'
    
    @property
    def can_close(self):
        """True if WO can be closed (all checks passed)"""
        return (
            self.status == 'completed' and
            self.qc_status in ['passed', 'not_required', 'waived'] and
            self.quantity_completed >= self.quantity_ordered
        )
    
    @property
    def needs_remake(self):
        """True if WO was scrapped and needs remake"""
        return self.is_scrapped and self.quantity_scrapped > 0


class ProductionOrderOperation(Base):
    """
    A single operation/step within a production order.

    Created by copying from the product's routing when the MO is released.
    Tracks actual execution vs planned at the operation level.
    """
    __tablename__ = "production_order_operations"

    id = Column(Integer, primary_key=True, index=True)
    production_order_id = Column(Integer, ForeignKey('production_orders.id', ondelete='CASCADE'), nullable=False)
    routing_operation_id = Column(Integer, ForeignKey('routing_operations.id'), nullable=True)
    work_center_id = Column(Integer, ForeignKey('work_centers.id'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id', ondelete='SET NULL'), nullable=True)  # Specific printer/resource assigned

    # Sequence and identification
    sequence = Column(Integer, nullable=False)
    operation_code = Column(String(50), nullable=True)
    operation_name = Column(String(200), nullable=True)

    # Status: pending, queued, running, complete, skipped
    status = Column(String(50), default='pending', nullable=False, index=True)

    # Quantities
    quantity_completed = Column(Numeric(18, 4), default=0, nullable=False)
    quantity_scrapped = Column(Numeric(18, 4), default=0, nullable=False)
    scrap_reason = Column(String(100), nullable=True)  # adhesion, layer_shift, stringing, warping, nozzle_clog, other

    # Planned times (minutes) - copied from routing
    planned_setup_minutes = Column(Numeric(10, 2), default=0, nullable=False)
    planned_run_minutes = Column(Numeric(10, 2), nullable=False)

    # Actual times (minutes) - tracked during execution
    actual_setup_minutes = Column(Numeric(10, 2), nullable=True)
    actual_run_minutes = Column(Numeric(10, 2), nullable=True)

    # Scheduling
    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)

    # Bambu integration
    bambu_task_id = Column(String(100), nullable=True)
    bambu_plate_index = Column(Integer, nullable=True)

    # Labor tracking
    operator_id = Column(Integer, nullable=True)  # User who performed the operation
    operator_name = Column(String(100), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    production_order = relationship("ProductionOrder", back_populates="operations")
    routing_operation = relationship("RoutingOperation")
    work_center = relationship("WorkCenter")
    resource = relationship("Resource", foreign_keys=[resource_id])
    materials = relationship("ProductionOrderOperationMaterial", back_populates="operation",
                            cascade="all, delete-orphan", order_by="ProductionOrderOperationMaterial.id")

    def __repr__(self):
        return f"<ProductionOrderOperation {self.sequence}: {self.operation_name} ({self.status})>"

    @property
    def is_complete(self):
        return self.status == 'complete'

    @property
    def is_running(self):
        return self.status == 'running'

    @property
    def efficiency_percent(self):
        """Actual vs planned run time efficiency"""
        if not self.planned_run_minutes or not self.actual_run_minutes:
            return None
        return round((float(self.planned_run_minutes) / float(self.actual_run_minutes)) * 100, 1)


class ProductionOrderMaterial(Base):
    """
    Material overrides for production orders.
    
    Tracks when materials are substituted or quantities adjusted during production.
    Example: BOM calls for Bambu PLA Red, but we use Elegoo PLA Red instead.
    
    This ensures:
    - Correct inventory consumption (from actual material used)
    - Accurate COGS (using actual material cost)
    - Audit trail of substitutions
    """
    __tablename__ = "production_order_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    production_order_id = Column(Integer, ForeignKey('production_orders.id'), nullable=False, index=True)
    bom_line_id = Column(Integer, ForeignKey('bom_lines.id'), nullable=True)  # Original BOM line
    
    # Original material from BOM
    original_product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    original_quantity = Column(Numeric(18, 4), nullable=False)  # From BOM
    
    # Substituted/adjusted material
    substitute_product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    planned_quantity = Column(Numeric(18, 4), nullable=False)  # Adjusted quantity to use
    actual_quantity_used = Column(Numeric(18, 4), nullable=True)  # Recorded on completion
    
    # Audit trail
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    production_order = relationship("ProductionOrder", backref="material_overrides")
    original_product = relationship("Product", foreign_keys=[original_product_id])
    substitute_product = relationship("Product", foreign_keys=[substitute_product_id])
    
    def __repr__(self):
        return f"<ProductionOrderMaterial PO#{self.production_order_id}: {self.original_product_id} → {self.substitute_product_id}>"


class ProductionOrderOperationMaterial(Base):
    """
    Material consumption tracking for a specific production order operation.
    
    This is the INSTANCE - tracks actual consumption with lot numbers.
    Created when a PO is released by copying from RoutingOperationMaterial.
    
    Lifecycle:
    1. Created with status='pending' when PO released
    2. status='allocated' when inventory reserved at op start
    3. status='consumed' when operation completes
    4. status='returned' if excess returned to inventory
    
    Examples:
    - PO-001 OP-10: Black PLA 370g required, Lot #L2024-001, 370g consumed
    - PO-001 OP-50: 6x6x6 Box 10 EA required, 10 EA consumed
    """
    __tablename__ = "production_order_operation_materials"

    id = Column(Integer, primary_key=True, index=True)
    production_order_operation_id = Column(Integer, 
                                           ForeignKey('production_order_operations.id', ondelete='CASCADE'), 
                                           nullable=False, index=True)
    component_id = Column(Integer, ForeignKey('products.id'), nullable=False, index=True)
    routing_operation_material_id = Column(Integer, 
                                           ForeignKey('routing_operation_materials.id', ondelete='SET NULL'),
                                           nullable=True)  # Link back to template
    
    # Planned quantities (calculated from routing × PO qty)
    quantity_required = Column(Numeric(18, 6), nullable=False)
    unit = Column(String(20), default="EA", nullable=False)
    
    # Actual consumption tracking
    quantity_allocated = Column(Numeric(18, 6), default=0, nullable=False)
    quantity_consumed = Column(Numeric(18, 6), default=0, nullable=False)
    
    # Lot tracking (for traceability)
    lot_number = Column(String(100), nullable=True)
    inventory_transaction_id = Column(Integer, ForeignKey('inventory_transactions.id'), nullable=True)
    
    # Status: pending, allocated, consumed, returned
    status = Column(String(20), default="pending", nullable=False)
    
    # Metadata
    consumed_at = Column(DateTime, nullable=True)
    consumed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    operation = relationship("ProductionOrderOperation", back_populates="materials")
    component = relationship("Product", foreign_keys=[component_id])
    routing_material = relationship("RoutingOperationMaterial")
    transaction = relationship("InventoryTransaction")
    consumed_by_user = relationship("User", foreign_keys=[consumed_by])

    def __repr__(self):
        return f"<POOpMaterial {self.component.sku if self.component else 'N/A'}: {self.quantity_required} {self.unit} ({self.status})>"

    @property
    def quantity_remaining(self):
        """Quantity still to be consumed"""
        return float(self.quantity_required or 0) - float(self.quantity_consumed or 0)

    @property
    def is_fully_consumed(self):
        """True if all required quantity has been consumed"""
        return self.quantity_remaining <= 0

    @property
    def is_allocated(self):
        """True if inventory has been allocated"""
        return self.status in ('allocated', 'consumed')

    @property
    def shortage_quantity(self):
        """Quantity short (if allocated < required)"""
        shortfall = float(self.quantity_required or 0) - float(self.quantity_allocated or 0)
        return max(0, shortfall)