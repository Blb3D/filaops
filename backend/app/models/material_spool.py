"""
Material Spool Model

Tracks individual filament spools/rolls for traceability and weight management.
Each spool represents a physical roll of material (e.g., PLA-BLK-001).
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class MaterialSpool(Base):
    """Material Spool model - tracks individual filament spools"""

    __tablename__ = "material_spools"

    id = Column(Integer, primary_key=True, index=True)

    # Spool identification
    spool_number = Column(String(100), unique=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # Weight tracking
    initial_weight_kg = Column(Numeric(10, 3), nullable=False)  # Weight when received
    current_weight_kg = Column(Numeric(10, 3), nullable=False)  # Estimated remaining weight

    # Status and lifecycle
    status = Column(String(50), default="active", nullable=False)  # active, empty, expired, damaged
    received_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiry_date = Column(DateTime, nullable=True)  # Optional material shelf life

    # Location tracking
    location_id = Column(Integer, ForeignKey("inventory_locations.id"), nullable=True)

    # Traceability
    supplier_lot_number = Column(String(100), nullable=True)  # Supplier's lot/batch number
    notes = Column(Text, nullable=True)  # Condition, issues, etc.

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)

    # Relationships
    product = relationship("Product", back_populates="spools")
    location = relationship("InventoryLocation")

    # Production order usage (via junction table)
    production_orders = relationship("ProductionOrderSpool", back_populates="spool", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MaterialSpool {self.spool_number}: {self.current_weight_kg}kg remaining>"

    @property
    def weight_remaining_percent(self):
        """Calculate percentage of weight remaining"""
        if self.initial_weight_kg <= 0:
            return 0
        return float(self.current_weight_kg / self.initial_weight_kg * 100)

    @property
    def is_low(self):
        """Check if spool is running low (< 10% remaining)"""
        return self.weight_remaining_percent < 10 and self.status == "active"

    @property
    def is_empty(self):
        """Check if spool is effectively empty (< 50g threshold)"""
        return float(self.current_weight_kg) < 0.05 or self.status == "empty"


class ProductionOrderSpool(Base):
    """Junction table linking production orders to spools used"""

    __tablename__ = "production_order_spools"

    id = Column(Integer, primary_key=True, index=True)

    production_order_id = Column(Integer, ForeignKey("production_orders.id"), nullable=False)
    spool_id = Column(Integer, ForeignKey("material_spools.id"), nullable=False)

    # Weight consumed from this spool for this production order
    weight_consumed_kg = Column(Numeric(10, 3), nullable=False, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)

    # Relationships
    production_order = relationship("ProductionOrder", back_populates="spools_used")
    spool = relationship("MaterialSpool", back_populates="production_orders")

    def __repr__(self):
        return f"<ProductionOrderSpool PO#{self.production_order_id} -> Spool#{self.spool_id}: {self.weight_consumed_kg}kg>"
