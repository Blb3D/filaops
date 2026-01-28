"""
Maintenance Log Model

Tracks maintenance activities on printers for preventive maintenance scheduling.
Freemium feature: Basic maintenance logging and scheduling.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class MaintenanceLog(Base):
    """
    Maintenance Log model - tracks printer maintenance activities

    Supports:
    - Routine maintenance (cleaning, lubrication, etc.)
    - Repairs (part replacements, fixes)
    - Calibration (bed leveling, extrusion calibration)
    - Cleaning (nozzle cleaning, bed cleaning)
    """

    __tablename__ = "maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Printer relationship
    printer_id = Column(Integer, ForeignKey("printers.id", ondelete="CASCADE"), nullable=False, index=True)

    # Maintenance details
    maintenance_type = Column(String(50), nullable=False, index=True)
    # Valid types: routine, repair, calibration, cleaning

    description = Column(Text, nullable=True)
    performed_by = Column(String(100), nullable=True)
    performed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Next maintenance scheduling
    next_due_at = Column(DateTime, nullable=True, index=True)

    # Cost tracking
    cost = Column(Numeric(10, 2), nullable=True)

    # Downtime tracking (for OEE calculations)
    downtime_minutes = Column(Integer, nullable=True)

    # Parts used (comma-separated list for simplicity)
    parts_used = Column(Text, nullable=True)

    # Additional notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    printer = relationship("Printer", back_populates="maintenance_logs")

    def __repr__(self):
        return f"<MaintenanceLog {self.id}: {self.maintenance_type} on Printer {self.printer_id}>"
