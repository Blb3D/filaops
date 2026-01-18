"""
PriceLevel model for B2B pricing tiers

Price levels define discount percentages for different customer tiers:
- Tier A (25%) - Premium partners
- Tier B (20%) - Preferred partners
- Tier C (10%) - Standard wholesale
- Tier D (0%) - Retail pricing
"""
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class PriceLevel(Base):
    """
    Price level model for B2B discount tiers

    Each customer can be assigned a price level which determines
    their base discount percentage on all products.
    """
    __tablename__ = "price_levels"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Price Level Info
    code = Column(String(10), unique=True, nullable=False, index=True)  # A, B, C, D
    name = Column(String(50), nullable=False)  # "Tier A - Premium"
    discount_percent = Column(Numeric(5, 2), nullable=False, default=0)  # 25.00 = 25%
    description = Column(Text, nullable=True)

    # Display
    sort_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    customers = relationship("Customer", back_populates="price_level")

    def __repr__(self):
        return f"<PriceLevel(code='{self.code}', discount={self.discount_percent}%)>"

    @property
    def discount_multiplier(self) -> Decimal:
        """
        Get the multiplier to apply to prices.

        Example: 25% discount -> multiplier of 0.75
        """
        return Decimal('1') - (Decimal(str(self.discount_percent)) / Decimal('100'))
