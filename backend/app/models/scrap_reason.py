"""
Scrap Reason Model

Stores configurable reasons for scrapping production orders.
Allows shops to define their own failure modes specific to their processes.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime

from app.db.base import Base


class ScrapReason(Base):
    """
    A reason for scrapping a production order.

    Examples:
    - adhesion: Print failed to adhere to build plate
    - layer_shift: Layer shift during print
    - spaghetti: Print became spaghetti (detached from bed)
    """
    __tablename__ = "scrap_reasons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "adhesion", "layer_shift"
    name = Column(String(100), nullable=False)  # Display name, e.g., "Bed Adhesion Failure"
    description = Column(Text, nullable=True)  # Longer explanation
    active = Column(Boolean, default=True, nullable=False)
    sequence = Column(Integer, default=0)  # For ordering in dropdowns

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<ScrapReason {self.code}: {self.name}>"
