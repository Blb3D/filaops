"""
Maintenance Pydantic Schemas

Schemas for printer maintenance log operations.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from decimal import Decimal


# ============================================================================
# Enums
# ============================================================================


class MaintenanceType(str, Enum):
    """Types of maintenance activities"""

    ROUTINE = "routine"
    REPAIR = "repair"
    CALIBRATION = "calibration"
    CLEANING = "cleaning"


# ============================================================================
# Maintenance CRUD Schemas
# ============================================================================


class MaintenanceLogBase(BaseModel):
    """Base maintenance log fields"""

    maintenance_type: MaintenanceType = Field(..., description="Type of maintenance performed")
    description: Optional[str] = Field(None, description="Description of maintenance performed")
    performed_by: Optional[str] = Field(None, max_length=100, description="Person who performed maintenance")
    performed_at: datetime = Field(..., description="When maintenance was performed")
    next_due_at: Optional[datetime] = Field(None, description="When next maintenance is due")
    cost: Optional[Decimal] = Field(None, ge=0, description="Cost of maintenance")
    downtime_minutes: Optional[int] = Field(None, ge=0, description="Printer downtime in minutes")
    parts_used: Optional[str] = Field(None, description="Parts used (comma-separated)")
    notes: Optional[str] = Field(None, description="Additional notes")


class MaintenanceLogCreate(MaintenanceLogBase):
    """Create a new maintenance log entry"""

    pass


class MaintenanceLogUpdate(BaseModel):
    """Update an existing maintenance log entry"""

    maintenance_type: Optional[MaintenanceType] = None
    description: Optional[str] = None
    performed_by: Optional[str] = Field(None, max_length=100)
    performed_at: Optional[datetime] = None
    next_due_at: Optional[datetime] = None
    cost: Optional[Decimal] = Field(None, ge=0)
    downtime_minutes: Optional[int] = Field(None, ge=0)
    parts_used: Optional[str] = None
    notes: Optional[str] = None


class MaintenanceLogResponse(MaintenanceLogBase):
    """Maintenance log response with printer info"""

    id: int
    printer_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MaintenanceLogWithPrinter(MaintenanceLogResponse):
    """Maintenance log response with printer details"""

    printer_code: str
    printer_name: str


class MaintenanceLogListResponse(BaseModel):
    """Paginated list of maintenance logs"""

    items: List[MaintenanceLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Maintenance Due Response
# ============================================================================


class PrinterMaintenanceDue(BaseModel):
    """Printer that is due for maintenance"""

    printer_id: int
    printer_code: str
    printer_name: str
    last_maintenance_date: Optional[datetime]
    next_due_date: Optional[datetime]
    days_overdue: Optional[int] = Field(None, description="Number of days overdue (negative = not due yet)")
    last_maintenance_type: Optional[MaintenanceType]


class MaintenanceDueResponse(BaseModel):
    """List of printers due for maintenance"""

    printers: List[PrinterMaintenanceDue]
    total_overdue: int
    total_due_soon: int = Field(..., description="Due within next 7 days")
