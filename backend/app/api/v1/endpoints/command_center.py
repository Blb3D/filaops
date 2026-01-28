"""
Command Center API endpoints.

Provides dashboard data for the "What do I need to do NOW?" view.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.deps import get_current_admin_user
from app.models.user import User
from app.services.command_center import (
    get_action_items,
    get_today_summary,
    get_resource_statuses,
)
from app.schemas.command_center import (
    ActionItemsResponse,
    TodaySummary,
    ResourcesResponse,
)

router = APIRouter()


@router.get("/action-items", response_model=ActionItemsResponse)
def get_action_items_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """
    Get prioritized list of action items requiring attention.

    Returns items sorted by priority (critical first) then by age (oldest first).

    Action item types:
    - blocked_po: Production orders blocked by material shortages (Priority 1)
    - overdue_so: Sales orders past due date (Priority 1)
    - due_today_so: Sales orders due today (Priority 2)
    - overrunning_op: Operations exceeding 2x estimated time (Priority 3)
    - idle_resource: Resources with work waiting (Priority 4)
    """
    return get_action_items(db)


@router.get("/summary", response_model=TodaySummary)
def get_summary_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """
    Get aggregate statistics for today's operations.

    Returns counts for:
    - Orders: due today, ready to ship, shipped, overdue
    - Production: in progress, blocked, completed today, operations running
    - Resources: total, busy, idle, down
    """
    return get_today_summary(db)


@router.get("/resources", response_model=ResourcesResponse)
def get_resources_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """
    Get current status of all resources/machines.

    Returns each resource with:
    - Current status (running, idle, maintenance, offline)
    - Current operation details if running
    - Count of pending operations in work center
    """
    return get_resource_statuses(db)
