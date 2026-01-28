"""
Entity Member Model

Stores LLC members/partners for multi-member LLCs and S-corps.
Used for K-1 allocation and capital account tracking.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, func

from app.db.base import Base


class EntityMember(Base):
    """
    LLC Member or Partnership Partner for K-1 allocation.

    member_type values:
        - individual: Natural person
        - entity: Another LLC, corporation, or partnership
        - trust: Trust or estate

    status values:
        - active: Currently a member with ownership
        - inactive: Temporarily not participating
        - withdrawn: No longer a member (end_date set)
    """

    __tablename__ = "entity_members"

    id = Column(Integer, primary_key=True)

    # Member identification
    name = Column(String(255), nullable=False)
    member_type = Column(String(20), nullable=False, default="individual")
    tax_id_last4 = Column(String(4), nullable=True)  # Last 4 of SSN/EIN for verification

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip = Column(String(20), nullable=True)

    # Ownership details
    ownership_percentage = Column(Numeric(5, 2), nullable=False)  # e.g., 50.00 for 50%
    capital_account = Column(Numeric(18, 4), nullable=False, default=0)  # Running balance

    # Status
    is_managing_member = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="active")
    effective_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<EntityMember(id={self.id}, name={self.name}, ownership={self.ownership_percentage}%)>"
