"""
User-Customer Access model

Maps which customers a portal user can access.
Enables multi-customer access (e.g., Jane at KOA can order for multiple campground locations).
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class UserCustomerAccess(Base):
    """
    Join table linking Users to Customers they can access.

    A User can have access to multiple Customers (e.g., multiple locations).
    Each Customer can have multiple Users with access.

    Use cases:
    - Regional manager ordering for multiple campground locations
    - Franchise owner accessing all franchise locations
    - Sales rep managing multiple customer accounts
    """

    __tablename__ = "user_customer_access"
    __table_args__ = (UniqueConstraint("user_id", "customer_id", name="uq_user_customer"),)

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)

    # Access Control
    role = Column(String(20), nullable=False, default="member")
    # Roles:
    # - admin: Full access, can add/remove other users
    # - member: Can place orders, view history
    # - viewer: Read-only access to orders

    # Default customer for this user (only one can be default)
    is_default = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="customer_access", foreign_keys=[user_id])
    customer = relationship("Customer", back_populates="user_access")
    granted_by_user = relationship("User", foreign_keys=[granted_by])

    def __repr__(self):
        return f"<UserCustomerAccess(user_id={self.user_id}, customer_id={self.customer_id}, role='{self.role}')>"
