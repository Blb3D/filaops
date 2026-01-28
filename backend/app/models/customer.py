"""
Customer model for CRM

Customers can be:
- B2B organizations: company_name is primary, first_name/last_name is contact
- B2C individuals: first_name/last_name is primary, company_name may be empty

Customers can:
- Have multiple portal users (via users.customer_id FK)
- Be assigned a price level for B2B pricing
- Have orders, quotes, and other records linked to them
- Exist as CRM records without portal access (walk-ins, phone orders)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Customer(Base):
    """
    Customer model representing a B2B organization/company

    This is separate from User - a Customer can have multiple Users
    (portal logins) associated with it via users.customer_id FK.
    """

    __tablename__ = "customers"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Customer Identification
    customer_number = Column(String(50), unique=True, nullable=True, index=True)  # CUST-0001
    company_name = Column(String(200), nullable=True, index=True)
    first_name = Column(String(100), nullable=True)  # Contact/individual first name
    last_name = Column(String(100), nullable=True)  # Contact/individual last name
    email = Column(String(255), nullable=True, index=True)  # Primary contact email
    phone = Column(String(20), nullable=True)

    # Account Status
    status = Column(String(20), nullable=False, default="active", index=True)  # active, inactive, suspended

    # Price Level FK (for B2B pricing)
    price_level_id = Column(Integer, ForeignKey("price_levels.id"), nullable=True)

    # Billing Address
    billing_address_line1 = Column(String(255), nullable=True)
    billing_address_line2 = Column(String(255), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(50), nullable=True)
    billing_zip = Column(String(20), nullable=True)
    billing_country = Column(String(100), nullable=True, default="USA")

    # Shipping Address (default for orders)
    shipping_address_line1 = Column(String(255), nullable=True)
    shipping_address_line2 = Column(String(255), nullable=True)
    shipping_city = Column(String(100), nullable=True)
    shipping_state = Column(String(50), nullable=True)
    shipping_zip = Column(String(20), nullable=True)
    shipping_country = Column(String(100), nullable=True, default="USA")

    # Metadata
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    price_level = relationship("PriceLevel", back_populates="customers")
    users = relationship("User", back_populates="customer")  # Portal users for this customer (legacy single-customer)
    customer_catalogs = relationship("CustomerCatalog", back_populates="customer", cascade="all, delete-orphan")

    # Multi-user access (B2B portal)
    user_access = relationship("UserCustomerAccess", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer(id={self.id}, number='{self.customer_number}', company='{self.company_name}')>"

    @property
    def full_name(self) -> str:
        """Get contact/individual full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or ""

    @property
    def display_name(self) -> str:
        """Get display name (company name, full name, or email)"""
        return self.company_name or self.full_name or self.email or f"Customer #{self.id}"

    @property
    def is_active(self) -> bool:
        """Check if customer account is active"""
        return self.status == "active"

    @property
    def full_shipping_address(self) -> str:
        """Get formatted shipping address"""
        parts = [
            self.shipping_address_line1,
            self.shipping_address_line2,
            f"{self.shipping_city}, {self.shipping_state} {self.shipping_zip}".strip(", "),
            self.shipping_country,
        ]
        return "\n".join(p for p in parts if p)

    @property
    def full_billing_address(self) -> str:
        """Get formatted billing address"""
        parts = [
            self.billing_address_line1,
            self.billing_address_line2,
            f"{self.billing_city}, {self.billing_state} {self.billing_zip}".strip(", "),
            self.billing_country,
        ]
        return "\n".join(p for p in parts if p)
