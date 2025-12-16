"""
Inventory models
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean, Computed
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class InventoryLocation(Base):
    """Inventory Location model - matches inventory_locations table"""
    __tablename__ = "inventory_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=True)
    type = Column(String(50), nullable=True)  # warehouse, shelf, bin, etc.
    parent_id = Column(Integer, ForeignKey('inventory_locations.id'), nullable=True)
    active = Column(Boolean, default=True, nullable=True)

    # Self-referential relationship for hierarchy
    parent = relationship("InventoryLocation", remote_side=[id], backref="children")

    # Inventory in this location
    inventory_items = relationship("Inventory", back_populates="location")

    def __repr__(self):
        return f"<InventoryLocation {self.code}: {self.name}>"


class Inventory(Base):
    """Inventory model - matches inventory table"""
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)

    # References
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('inventory_locations.id'), nullable=False)

    # Quantities
    on_hand_quantity = Column(Numeric(10, 2), default=0, nullable=False)
    allocated_quantity = Column(Numeric(10, 2), default=0, nullable=False)
    # available_quantity is a computed column in SQL Server (on_hand - allocated)
    available_quantity = Column(Numeric(10, 2), Computed("on_hand_quantity - allocated_quantity"))

    # Metadata
    last_counted = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="inventory_items")
    location = relationship("InventoryLocation", back_populates="inventory_items")

    def __repr__(self):
        return f"<Inventory {self.product.sku if self.product else 'N/A'}: {self.available_quantity}>"


class InventoryTransaction(Base):
    """Inventory Transaction model - matches inventory_transactions table"""
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)

    # References
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('inventory_locations.id'), nullable=True)

    # Transaction details
    transaction_type = Column(String(50), nullable=False)
    # receipt, shipment, adjustment, consumption, transfer, reservation, scrap

    reference_type = Column(String(50), nullable=True)
    # sales_order, purchase_order, production_order, print_job, adjustment

    reference_id = Column(Integer, nullable=True)

    # Quantities
    quantity = Column(Numeric(18, 4), nullable=False)

    # Tracking
    lot_number = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)

    # Costs
    cost_per_unit = Column(Numeric(18, 4), nullable=True)
    # total_cost is a computed column (quantity * cost_per_unit)

    # Notes
    notes = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)

    # Relationships
    location = relationship("InventoryLocation")
    product = relationship("Product")

    def __repr__(self):
        return f"<InventoryTransaction {self.transaction_type}: {self.quantity}>"
