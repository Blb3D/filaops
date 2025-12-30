"""
Resource scheduling service with conflict detection.

Handles scheduling operations on resources and detecting time conflicts.
"""
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.production_order import ProductionOrderOperation
from app.models.work_center import Machine

# Terminal statuses don't block scheduling
TERMINAL_STATUSES = ['complete', 'skipped', 'cancelled']


def get_resource_schedule(
    db: Session,
    resource_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[ProductionOrderOperation]:
    """
    Get scheduled operations for a resource within date range.

    Args:
        db: Database session
        resource_id: Resource to check
        start_date: Optional filter - operations ending after this time
        end_date: Optional filter - operations starting before this time

    Returns:
        List of operations scheduled on this resource
    """
    query = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.resource_id == resource_id,
        ProductionOrderOperation.status.notin_(TERMINAL_STATUSES),
        ProductionOrderOperation.scheduled_start.isnot(None),
        ProductionOrderOperation.scheduled_end.isnot(None)
    )

    if start_date:
        query = query.filter(ProductionOrderOperation.scheduled_end > start_date)
    if end_date:
        query = query.filter(ProductionOrderOperation.scheduled_start < end_date)

    return query.order_by(ProductionOrderOperation.scheduled_start).all()


def find_conflicts(
    db: Session,
    resource_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_operation_id: Optional[int] = None
) -> List[ProductionOrderOperation]:
    """
    Find operations that conflict with proposed time range.

    Two operations conflict if:
    - Same resource
    - Time ranges overlap: (start1 < end2) AND (start2 < end1)
    - Neither in terminal status

    Args:
        db: Database session
        resource_id: Resource to check
        start_time: Proposed start
        end_time: Proposed end
        exclude_operation_id: Operation to exclude (for rescheduling)

    Returns:
        List of conflicting operations
    """
    query = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.resource_id == resource_id,
        ProductionOrderOperation.status.notin_(TERMINAL_STATUSES),
        ProductionOrderOperation.scheduled_start.isnot(None),
        ProductionOrderOperation.scheduled_end.isnot(None),
        # Overlap condition
        ProductionOrderOperation.scheduled_start < end_time,
        ProductionOrderOperation.scheduled_end > start_time
    )

    if exclude_operation_id:
        query = query.filter(ProductionOrderOperation.id != exclude_operation_id)

    return query.all()


def find_running_operations(
    db: Session,
    resource_id: int,
    exclude_operation_id: Optional[int] = None
) -> List[ProductionOrderOperation]:
    """
    Find operations currently running on a resource.

    Args:
        db: Database session
        resource_id: Resource to check
        exclude_operation_id: Operation to exclude

    Returns:
        List of running operations
    """
    query = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.resource_id == resource_id,
        ProductionOrderOperation.status == 'running'
    )

    if exclude_operation_id:
        query = query.filter(ProductionOrderOperation.id != exclude_operation_id)

    return query.all()


def check_resource_available_now(
    db: Session,
    resource_id: int
) -> Tuple[bool, Optional[ProductionOrderOperation]]:
    """
    Check if resource is available to start work now.

    Args:
        db: Database session
        resource_id: Resource to check

    Returns:
        Tuple of (is_available, blocking_operation)
    """
    running = find_running_operations(db, resource_id)
    if running:
        return False, running[0]
    return True, None


def schedule_operation(
    db: Session,
    operation: ProductionOrderOperation,
    resource_id: int,
    scheduled_start: datetime,
    scheduled_end: datetime
) -> Tuple[bool, List[ProductionOrderOperation]]:
    """
    Schedule an operation on a resource with conflict validation.

    Args:
        db: Database session
        operation: Operation to schedule
        resource_id: Target resource
        scheduled_start: Start time
        scheduled_end: End time

    Returns:
        Tuple of (success, conflicts)
        - If success=True, operation was scheduled
        - If success=False, conflicts contains blocking operations
    """
    # Check for conflicts
    conflicts = find_conflicts(
        db, resource_id, scheduled_start, scheduled_end,
        exclude_operation_id=operation.id
    )

    if conflicts:
        return False, conflicts

    # Schedule the operation
    operation.resource_id = resource_id
    operation.scheduled_start = scheduled_start
    operation.scheduled_end = scheduled_end
    operation.status = 'queued'  # Move from pending to queued

    db.flush()

    return True, []
