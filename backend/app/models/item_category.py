"""
Item Category model - hierarchical categories for products/items
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class ItemCategory(Base):
    """
    Hierarchical category structure for all items (products, components, supplies, etc.)

    Examples:
        FILAMENT > PLA
        FILAMENT > PETG
        PACKAGING > Boxes
        FINISHED_GOODS > Standard Products
    """

    __tablename__ = "item_categories"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # 'FILAMENT', 'PLA', 'PACKAGING'
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("item_categories.id"), nullable=True)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Self-referential relationship for hierarchy
    parent = relationship("ItemCategory", remote_side=[id], backref="children")

    # Relationship to products
    products = relationship("Product", back_populates="item_category")

    def __repr__(self):
        return f"<ItemCategory {self.code}: {self.name}>"

    @property
    def full_path(self) -> str:
        """Return full category path like 'FILAMENT > PLA'"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name
