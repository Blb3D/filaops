"""
Vendor model for purchasing module
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Numeric
from datetime import datetime

from app.db.base import Base


class Vendor(Base):
    """Vendor/Supplier model"""

    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    code = Column(String(50), unique=True, nullable=False, index=True)  # VND-001
    name = Column(String(200), nullable=False)

    # Contact info
    contact_name = Column(String(100), nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(String(500), nullable=True)

    # Address
    address_line1 = Column(String(200), nullable=True)
    address_line2 = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True, default="USA")

    # Business terms
    payment_terms = Column(String(100), nullable=True)  # Net 30, COD, etc.
    account_number = Column(String(100), nullable=True)  # Our account with them
    tax_id = Column(String(50), nullable=True)

    # Performance tracking
    lead_time_days = Column(Integer, nullable=True)  # Average lead time
    rating = Column(Numeric(3, 2), nullable=True)  # 1.00-5.00 rating

    # Notes
    notes = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Vendor {self.code}: {self.name}>"
