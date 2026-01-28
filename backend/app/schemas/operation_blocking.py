"""
Schemas for operation-level blocking check responses.
"""

from typing import Optional, List
from pydantic import BaseModel


class IncomingSupplyInfo(BaseModel):
    """Info about incoming supply from a purchase order."""

    purchase_order_id: int
    purchase_order_code: str
    quantity: float
    expected_date: Optional[str] = None


class MaterialIssueInfo(BaseModel):
    """Material availability info for an operation."""

    product_id: int
    product_sku: str
    product_name: Optional[str] = None
    quantity_required: float
    quantity_available: float
    quantity_short: float
    unit: str = "EA"
    consume_stage: str = "production"
    incoming_supply: Optional[IncomingSupplyInfo] = None


class CanStartResponse(BaseModel):
    """Response for quick can-start check."""

    can_start: bool
    blocking_issues: List[MaterialIssueInfo] = []


class OperationBlockingResponse(BaseModel):
    """Full blocking issues response for an operation."""

    operation_id: int
    operation_code: Optional[str] = None
    operation_name: Optional[str] = None
    can_start: bool
    blocking_issues: List[MaterialIssueInfo] = []
    material_issues: List[MaterialIssueInfo] = []
