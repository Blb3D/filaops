"""
Schemas for routing and operation generation.
"""
from typing import Optional, List
from pydantic import BaseModel


class RoutingOperationInfo(BaseModel):
    """Information about a routing operation."""
    id: int
    sequence: int
    operation_code: Optional[str] = None
    operation_name: Optional[str] = None
    work_center_id: Optional[int] = None
    work_center_code: Optional[str] = None
    setup_time_minutes: Optional[float] = None
    run_time_minutes: Optional[float] = None

    class Config:
        from_attributes = True


class ProductRoutingResponse(BaseModel):
    """Response with product routing details."""
    product_id: int
    routing_id: Optional[int] = None
    routing_code: Optional[str] = None
    routing_name: Optional[str] = None
    is_active: bool = False
    operations: List[RoutingOperationInfo] = []


class ReleaseResponse(BaseModel):
    """Response from releasing a production order."""
    success: bool
    production_order_id: int
    status: str
    operations_created: int
    message: str


class GenerateOperationsRequest(BaseModel):
    """Request to generate operations."""
    force: bool = False


class GenerateOperationsResponse(BaseModel):
    """Response from generating operations."""
    success: bool
    operations_created: int
    message: str
