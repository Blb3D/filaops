"""
Production Order Pydantic Schemas

Manufacturing Orders (MOs) for tracking production of finished goods.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class ProductionOrderStatus(str, Enum):
    """Production order status"""
    DRAFT = "draft"
    RELEASED = "released"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class ProductionOrderSource(str, Enum):
    """How the production order was created"""
    MANUAL = "manual"
    SALES_ORDER = "sales_order"
    MRP_PLANNED = "mrp_planned"


class OperationStatus(str, Enum):
    """Operation execution status"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    SKIPPED = "skipped"


# ============================================================================
# Production Order Operation Schemas
# ============================================================================

class ProductionOrderOperationBase(BaseModel):
    """Base operation fields"""
    work_center_id: int
    resource_id: Optional[int] = None
    sequence: int = Field(..., ge=1)
    operation_code: Optional[str] = Field(None, max_length=50)
    operation_name: Optional[str] = Field(None, max_length=200)
    planned_setup_minutes: Decimal = Field(0, ge=0)
    planned_run_minutes: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class ProductionOrderOperationCreate(ProductionOrderOperationBase):
    """Create a new operation (usually auto-created from routing)"""
    routing_operation_id: Optional[int] = None


class ProductionOrderOperationUpdate(BaseModel):
    """Update an operation - typically during execution"""
    resource_id: Optional[int] = None
    status: Optional[OperationStatus] = None
    quantity_completed: Optional[Decimal] = Field(None, ge=0)
    quantity_scrapped: Optional[Decimal] = Field(None, ge=0)
    actual_setup_minutes: Optional[Decimal] = Field(None, ge=0)
    actual_run_minutes: Optional[Decimal] = Field(None, ge=0)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    bambu_task_id: Optional[str] = Field(None, max_length=100)
    bambu_plate_index: Optional[int] = None
    operator_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class ProductionOrderOperationResponse(BaseModel):
    """Operation response with full details"""
    id: int
    production_order_id: int
    routing_operation_id: Optional[int] = None
    work_center_id: int
    work_center_code: Optional[str] = None
    work_center_name: Optional[str] = None
    resource_id: Optional[int] = None
    resource_code: Optional[str] = None
    resource_name: Optional[str] = None

    sequence: int
    operation_code: Optional[str] = None
    operation_name: Optional[str] = None
    status: str

    quantity_completed: Decimal = 0
    quantity_scrapped: Decimal = 0

    planned_setup_minutes: Decimal = 0
    planned_run_minutes: Decimal
    actual_setup_minutes: Optional[Decimal] = None
    actual_run_minutes: Optional[Decimal] = None

    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None

    bambu_task_id: Optional[str] = None
    bambu_plate_index: Optional[int] = None
    operator_name: Optional[str] = None
    notes: Optional[str] = None

    # Computed
    is_complete: bool = False
    is_running: bool = False
    efficiency_percent: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Production Order Schemas
# ============================================================================

class ProductionOrderBase(BaseModel):
    """Base production order fields"""
    product_id: int
    quantity_ordered: Decimal = Field(..., gt=0)
    due_date: Optional[date] = None
    priority: int = Field(3, ge=1, le=5, description="1=highest, 5=lowest")
    notes: Optional[str] = None


class ProductionOrderCreate(ProductionOrderBase):
    """Create a new production order"""
    bom_id: Optional[int] = None
    routing_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    sales_order_line_id: Optional[int] = None
    source: ProductionOrderSource = ProductionOrderSource.MANUAL
    assigned_to: Optional[str] = Field(None, max_length=100)


class ProductionOrderUpdate(BaseModel):
    """Update a production order"""
    quantity_ordered: Optional[Decimal] = Field(None, gt=0)
    quantity_completed: Optional[Decimal] = Field(None, ge=0)
    quantity_scrapped: Optional[Decimal] = Field(None, ge=0)
    status: Optional[ProductionOrderStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    due_date: Optional[date] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    assigned_to: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class ProductionOrderStatusUpdate(BaseModel):
    """Update just the status (with optional timestamps)"""
    status: ProductionOrderStatus
    notes: Optional[str] = None


class ProductionOrderListResponse(BaseModel):
    """Summary for list views"""
    id: int
    code: str
    product_id: int
    product_sku: Optional[str] = None
    product_name: Optional[str] = None

    quantity_ordered: Decimal
    quantity_completed: Decimal = 0
    quantity_remaining: float = 0
    completion_percent: float = 0

    status: str
    priority: int
    source: str

    due_date: Optional[date] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None

    sales_order_id: Optional[int] = None
    sales_order_code: Optional[str] = None

    assigned_to: Optional[str] = None
    operation_count: int = 0
    current_operation: Optional[str] = None  # Name of current/next operation

    created_at: datetime

    class Config:
        from_attributes = True


class ProductionOrderResponse(BaseModel):
    """Full production order details"""
    id: int
    code: str

    # References
    product_id: int
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    bom_id: Optional[int] = None
    bom_code: Optional[str] = None
    routing_id: Optional[int] = None
    routing_code: Optional[str] = None
    sales_order_id: Optional[int] = None
    sales_order_code: Optional[str] = None
    sales_order_line_id: Optional[int] = None

    # Quantities
    quantity_ordered: Decimal
    quantity_completed: Decimal = 0
    quantity_scrapped: Decimal = 0
    quantity_remaining: float = 0
    completion_percent: float = 0

    # Status
    source: str
    status: str
    priority: int

    # Scheduling
    due_date: Optional[date] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None

    # Time
    estimated_time_minutes: Optional[int] = None
    actual_time_minutes: Optional[int] = None

    # Costs
    estimated_material_cost: Optional[Decimal] = None
    estimated_labor_cost: Optional[Decimal] = None
    estimated_total_cost: Optional[Decimal] = None
    actual_material_cost: Optional[Decimal] = None
    actual_labor_cost: Optional[Decimal] = None
    actual_total_cost: Optional[Decimal] = None

    # Assignment
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

    # Operations
    operations: List[ProductionOrderOperationResponse] = []

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    released_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Bulk Operations
# ============================================================================

class ProductionOrderBulkCreate(BaseModel):
    """Create multiple production orders"""
    orders: List[ProductionOrderCreate]


class ProductionOrderBulkStatusUpdate(BaseModel):
    """Update status of multiple orders"""
    order_ids: List[int]
    status: ProductionOrderStatus


# ============================================================================
# Schedule/Queue Views
# ============================================================================

class ProductionQueueItem(BaseModel):
    """Item for the production queue/kanban view"""
    id: int
    code: str
    product_sku: str
    product_name: str
    quantity_ordered: Decimal
    quantity_completed: Decimal = 0
    status: str
    priority: int
    due_date: Optional[date] = None
    current_operation_name: Optional[str] = None
    current_work_center_code: Optional[str] = None
    is_late: bool = False
    days_until_due: Optional[int] = None

    class Config:
        from_attributes = True


class WorkCenterQueue(BaseModel):
    """Operations queued at a work center"""
    work_center_id: int
    work_center_code: str
    work_center_name: str
    queued_operations: List[ProductionOrderOperationResponse] = []
    running_operations: List[ProductionOrderOperationResponse] = []
    total_queued_minutes: float = 0


class ProductionScheduleSummary(BaseModel):
    """Summary stats for the production schedule"""
    total_orders: int = 0
    orders_by_status: dict = {}
    orders_due_today: int = 0
    orders_overdue: int = 0
    orders_in_progress: int = 0
    total_quantity_to_produce: float = 0


# ============================================================================
# Split Order Schemas
# ============================================================================

class SplitQuantity(BaseModel):
    """Quantity for a single split order"""
    quantity: int = Field(..., gt=0, description="Quantity for this split")


class ProductionOrderSplitRequest(BaseModel):
    """Request to split a production order into multiple child orders"""
    splits: List[SplitQuantity] = Field(
        ...,
        min_length=2,
        description="List of quantities for each split (must have at least 2)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "splits": [
                    {"quantity": 25},
                    {"quantity": 25}
                ]
            }
        }


class ProductionOrderSplitResponse(BaseModel):
    """Response from splitting a production order"""
    parent_order_id: int
    parent_order_code: str
    parent_status: str
    child_orders: List[ProductionOrderListResponse]
    message: str


# ============================================================================
# Scrap Reason Schemas
# ============================================================================

class ScrapReasonDetail(BaseModel):
    """Detailed scrap reason information"""
    id: int
    code: str
    name: str
    description: Optional[str] = None
    sequence: int

    class Config:
        from_attributes = True


class ScrapReasonUpdate(BaseModel):
    """Update schema for scrap reasons"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    active: Optional[bool] = None
    sequence: Optional[int] = Field(None, ge=0)

    class Config:
        from_attributes = True


class ScrapReasonsResponse(BaseModel):
    """Response for scrap reasons endpoint"""
    reasons: List[str] = Field(..., description="List of scrap reason codes")
    details: List[ScrapReasonDetail] = Field(..., description="Detailed scrap reason information")
    descriptions: dict[str, str] = Field(..., description="Map of code to description")

    class Config:
        from_attributes = True
