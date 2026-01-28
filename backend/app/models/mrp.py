"""
MRP (Material Requirements Planning) models.

- MRPRun: Audit trail of MRP calculation runs
- PlannedOrder: MRP-generated planned purchase/production orders
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class MRPRun(Base):
    """
    Audit trail for MRP calculation runs.
    Tracks what was processed and what was generated.
    """

    __tablename__ = "mrp_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    planning_horizon_days = Column(Integer, default=30, nullable=False)

    # Scope
    orders_processed = Column(Integer, default=0)
    components_analyzed = Column(Integer, default=0)

    # Results
    shortages_found = Column(Integer, default=0)
    planned_orders_created = Column(Integer, default=0)

    # Status
    status = Column(String(20), default="running", nullable=False)  # running, completed, failed, cancelled
    error_message = Column(Text, nullable=True)

    # Audit
    created_by = Column(Integer, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    planned_orders = relationship("PlannedOrder", back_populates="mrp_run")

    def __repr__(self):
        return f"<MRPRun {self.id}: {self.status} ({self.planned_orders_created} orders)>"


class PlannedOrder(Base):
    """
    MRP-generated planned orders.

    These represent suggested purchase orders or production orders
    to fulfill material requirements. They go through a lifecycle:
    - planned: MRP suggestion, can be auto-deleted on next run
    - firmed: User confirmed, won't be deleted by MRP
    - released: Converted to actual PO or MO
    - cancelled: No longer needed
    """

    __tablename__ = "planned_orders"

    id = Column(Integer, primary_key=True, index=True)

    # Order type
    order_type = Column(String(20), nullable=False)  # purchase, production

    # What needs to be ordered
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)

    # Timing
    due_date = Column(Date, nullable=False)  # When material is needed
    start_date = Column(Date, nullable=False)  # When to start (due_date - lead_time)

    # Pegging: what demand triggered this
    source_demand_type = Column(String(50), nullable=True)  # production_order, sales_order, forecast
    source_demand_id = Column(Integer, nullable=True)
    mrp_run_id = Column(Integer, ForeignKey("mrp_runs.id"), nullable=True)

    # Status
    status = Column(String(20), default="planned", nullable=False)  # planned, firmed, released, cancelled

    # Conversion tracking
    converted_to_po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    converted_to_mo_id = Column(Integer, ForeignKey("production_orders.id"), nullable=True)

    # Notes and audit
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    firmed_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)

    # Relationships
    product = relationship("Product")
    mrp_run = relationship("MRPRun", back_populates="planned_orders")
    converted_po = relationship("PurchaseOrder", foreign_keys=[converted_to_po_id])
    converted_mo = relationship("ProductionOrder", foreign_keys=[converted_to_mo_id])

    def __repr__(self):
        return f"<PlannedOrder {self.id}: {self.order_type} {self.quantity} of product {self.product_id}>"
