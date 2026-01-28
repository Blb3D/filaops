"""
Catalog models for B2B product visibility control

Catalogs allow admins to:
- Create product groupings (e.g., "Public", "KOA Custom", "Wholesale Partners")
- Assign products to one or more catalogs
- Assign customers to one or more catalogs
- Portal shows products from customer's assigned catalogs + public catalogs
"""

from decimal import Decimal
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Catalog(Base):
    """
    Catalog definition for product visibility grouping.

    Examples:
    - PUBLIC: Default catalog, visible to all customers
    - KOA-CUSTOM: Custom products only for KOA Kampgrounds
    - WHOLESALE: Products available to wholesale partners
    """

    __tablename__ = "catalogs"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Catalog Info
    code = Column(String(50), unique=True, nullable=False, index=True)  # PUBLIC, KOA-CUSTOM
    name = Column(String(100), nullable=False)  # "Public Catalog"
    description = Column(Text, nullable=True)

    # Visibility Settings
    is_default = Column(Boolean, nullable=False, default=False)  # New products auto-assigned
    is_public = Column(Boolean, nullable=False, default=True, index=True)  # Visible to all portal users

    # Display
    sort_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    catalog_products = relationship("CatalogProduct", back_populates="catalog", cascade="all, delete-orphan")
    customer_catalogs = relationship("CustomerCatalog", back_populates="catalog", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Catalog(code='{self.code}', name='{self.name}', public={self.is_public})>"


class CatalogProduct(Base):
    """
    Many-to-many relationship between catalogs and products.

    Allows optional price override per catalog (e.g., special KOA pricing).
    """

    __tablename__ = "catalog_products"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    catalog_id = Column(Integer, ForeignKey("catalogs.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)

    # Optional catalog-specific price override
    price_override = Column(Numeric(12, 4), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    # Relationships
    catalog = relationship("Catalog", back_populates="catalog_products")
    product = relationship("Product", back_populates="catalog_products")

    def __repr__(self):
        return f"<CatalogProduct(catalog_id={self.catalog_id}, product_id={self.product_id})>"

    @property
    def effective_price(self) -> Decimal:
        """Get the effective price (override or product's selling price)."""
        if self.price_override is not None:
            return Decimal(str(self.price_override))
        return Decimal(str(self.product.selling_price)) if self.product else Decimal("0")


class CustomerCatalog(Base):
    """
    Many-to-many relationship between customers and catalogs.

    Determines which catalogs (and thus products) a customer can see in the portal.
    """

    __tablename__ = "customer_catalogs"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="customer_catalogs")
    catalog = relationship("Catalog", back_populates="customer_catalogs")

    def __repr__(self):
        return f"<CustomerCatalog(customer_id={self.customer_id}, catalog_id={self.catalog_id})>"
