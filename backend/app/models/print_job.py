"""
Print Job model
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class PrintJob(Base):
    """Print Job model - matches print_jobs table"""

    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)

    # References
    production_order_id = Column(Integer, ForeignKey("production_orders.id"), nullable=True)
    printer_id = Column(Integer, ForeignKey("printers.id"), nullable=True)

    # File info
    gcode_file = Column(String(500), nullable=True)

    # Status and priority
    status = Column(String(50), nullable=False, default="queued")
    # queued, assigned, printing, completed, failed
    priority = Column(String(20), default="normal")

    # Timing
    estimated_time_minutes = Column(Integer, nullable=True)
    actual_time_minutes = Column(Integer, nullable=True)

    # Material
    estimated_material_grams = Column(Numeric(18, 4), nullable=True)
    actual_material_grams = Column(Numeric(18, 4), nullable=True)

    # Variance tracking
    variance_percent = Column(Numeric(5, 2), nullable=True)

    # Timestamps
    queued_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    production_order = relationship("ProductionOrder", back_populates="print_jobs")
    printer = relationship("Printer", back_populates="print_jobs")

    def __repr__(self):
        return f"<PrintJob {self.id}: {self.status}>"
