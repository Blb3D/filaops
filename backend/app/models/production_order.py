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

    # References
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    bom_id = Column(Integer, ForeignKey('boms.id'), nullable=True)
    routing_id = Column(Integer, ForeignKey('routings.id'), nullable=True)
    sales_order_id = Column(Integer, ForeignKey('sales_orders.id'), nullable=True)
    sales_order_line_id = Column(Integer, ForeignKey('sales_order_lines.id'), nullable=True)

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

    # Status: draft, released, in_progress, complete, cancelled, on_hold
    status = Column(String(50), default='draft', nullable=False, index=True)

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
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=True)  # Specific machine assigned

    # Sequence and identification
    sequence = Column(Integer, nullable=False)
    operation_code = Column(String(50), nullable=True)
    operation_name = Column(String(200), nullable=True)

    # Status: pending, queued, running, complete, skipped
    status = Column(String(50), default='pending', nullable=False, index=True)

    # Quantities
    quantity_completed = Column(Numeric(18, 4), default=0, nullable=False)
    quantity_scrapped = Column(Numeric(18, 4), default=0, nullable=False)

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
    resource = relationship("Resource")

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
