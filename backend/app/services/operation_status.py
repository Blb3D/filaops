"""
Service layer for operation status transitions.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.production_order import ProductionOrder, ProductionOrderOperation
from app.models.work_center import Machine
from app.services.operation_blocking import check_operation_blocking
from app.services.resource_scheduling import check_resource_available_now


class OperationError(Exception):
    """Custom exception for operation errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self):
        return self.message


def get_operation_with_validation(
    db: Session,
    po_id: int,
    op_id: int
) -> Tuple[ProductionOrder, ProductionOrderOperation]:
    """
    Get operation and validate it belongs to the specified PO.

    Returns:
        Tuple of (ProductionOrder, ProductionOrderOperation)

    Raises:
        OperationError: If PO or operation not found, or operation doesn't belong to PO
    """
    po = db.get(ProductionOrder, po_id)
    if not po:
        raise OperationError(f"Production order {po_id} not found", 404)

    op = db.get(ProductionOrderOperation, op_id)
    if not op:
        raise OperationError(f"Operation {op_id} not found", 404)

    if op.production_order_id != po_id:
        raise OperationError(f"Operation {op_id} does not belong to production order {po_id}", 404)

    return po, op


def get_previous_operation(
    db: Session,
    po: ProductionOrder,
    current_op: ProductionOrderOperation
) -> Optional[ProductionOrderOperation]:
    """Get the previous operation in sequence."""
    ops = sorted(po.operations, key=lambda x: x.sequence)

    for i, op in enumerate(ops):
        if op.id == current_op.id and i > 0:
            return ops[i - 1]

    return None


def get_next_operation(
    db: Session,
    po: ProductionOrder,
    current_op: ProductionOrderOperation
) -> Optional[ProductionOrderOperation]:
    """Get the next operation in sequence."""
    ops = sorted(po.operations, key=lambda x: x.sequence)

    for i, op in enumerate(ops):
        if op.id == current_op.id and i < len(ops) - 1:
            return ops[i + 1]

    return None


def derive_po_status(po: ProductionOrder) -> str:
    """
    Derive PO status from its operations.

    Rules:
    - All pending → released
    - All complete/skipped → complete
    - Any running or mixed → in_progress
    """
    if not po.operations:
        return po.status  # No operations, keep current

    statuses = [op.status for op in po.operations]

    if all(s == 'pending' for s in statuses):
        return 'released'
    elif all(s in ('complete', 'skipped') for s in statuses):
        return 'complete'
    else:
        return 'in_progress'


def update_po_status(db: Session, po: ProductionOrder) -> None:
    """Update PO status based on operations."""
    new_status = derive_po_status(po)

    if po.status != new_status:
        po.status = new_status
        po.updated_at = datetime.utcnow()

        if new_status == 'in_progress' and not po.actual_start:
            po.actual_start = datetime.utcnow()
        elif new_status == 'complete' and not po.actual_end:
            po.actual_end = datetime.utcnow()
            po.completed_at = datetime.utcnow()


def start_operation(
    db: Session,
    po_id: int,
    op_id: int,
    resource_id: Optional[int] = None,
    operator_name: Optional[str] = None,
    notes: Optional[str] = None
) -> ProductionOrderOperation:
    """
    Start an operation.

    Validations:
    - Operation must be pending or queued
    - Previous operation (by sequence) must be complete or skipped
    - Resource must not have conflicting scheduled operation

    Returns:
        Updated operation

    Raises:
        OperationError: If validation fails
    """
    po, op = get_operation_with_validation(db, po_id, op_id)

    # Check operation status
    if op.status == 'running':
        raise OperationError("Operation is already running", 400)
    if op.status in ('complete', 'skipped'):
        raise OperationError(f"Operation is already {op.status}", 400)
    if op.status not in ('pending', 'queued'):
        raise OperationError(f"Cannot start operation in status '{op.status}'", 400)

    # Check previous operation is complete
    prev_op = get_previous_operation(db, po, op)
    if prev_op and prev_op.status not in ('complete', 'skipped'):
        raise OperationError(
            f"Previous operation (sequence {prev_op.sequence}) must be complete before starting this one",
            400
        )

    # Check material availability for this operation (API-402)
    blocking_result = check_operation_blocking(db, po_id, op_id)
    if not blocking_result["can_start"]:
        short_materials = [m["product_sku"] for m in blocking_result["blocking_issues"]]
        raise OperationError(
            f"Operation blocked by material shortages: {', '.join(short_materials)}",
            400
        )

    # Validate resource if provided
    if resource_id:
        resource = db.get(Machine, resource_id)
        if not resource:
            raise OperationError(f"Resource {resource_id} not found", 404)

        # Check for double-booking (API-403)
        is_available, blocking_op = check_resource_available_now(db, resource_id)
        if not is_available:
            raise OperationError(
                f"Resource is busy with another running operation (operation {blocking_op.id})",
                409
            )
        op.resource_id = resource_id

    # Update operation
    op.status = 'running'
    op.actual_start = datetime.utcnow()
    op.operator_name = operator_name
    if notes:
        op.notes = notes
    op.updated_at = datetime.utcnow()

    # Update PO status
    update_po_status(db, po)

    db.flush()
    return op


def complete_operation(
    db: Session,
    po_id: int,
    op_id: int,
    quantity_completed: Decimal,
    quantity_scrapped: Decimal = Decimal("0"),
    actual_run_minutes: Optional[int] = None,
    notes: Optional[str] = None
) -> ProductionOrderOperation:
    """
    Complete an operation.

    Validations:
    - Operation must be running

    Side effects:
    - Updates PO status if last operation
    - TODO: Consume materials for this operation (API-402)

    Returns:
        Updated operation

    Raises:
        OperationError: If validation fails
    """
    po, op = get_operation_with_validation(db, po_id, op_id)

    # Check operation status
    if op.status != 'running':
        raise OperationError("Operation is not running, cannot complete", 400)

    # Update operation
    op.status = 'complete'
    op.actual_end = datetime.utcnow()
    op.quantity_completed = quantity_completed
    op.quantity_scrapped = quantity_scrapped

    # Calculate actual run time if not provided
    if actual_run_minutes is not None:
        op.actual_run_minutes = actual_run_minutes
    elif op.actual_start:
        elapsed = datetime.utcnow() - op.actual_start
        op.actual_run_minutes = int(elapsed.total_seconds() / 60)

    if notes:
        op.notes = notes
    op.updated_at = datetime.utcnow()

    # Update PO status
    update_po_status(db, po)

    # Update PO quantities
    po.quantity_completed = quantity_completed
    po.quantity_scrapped = (po.quantity_scrapped or Decimal("0")) + quantity_scrapped

    db.flush()
    return op


def skip_operation(
    db: Session,
    po_id: int,
    op_id: int,
    reason: str
) -> ProductionOrderOperation:
    """
    Skip an operation.

    Validations:
    - Operation must be pending or queued
    - Previous operation must be complete or skipped

    Returns:
        Updated operation

    Raises:
        OperationError: If validation fails
    """
    po, op = get_operation_with_validation(db, po_id, op_id)

    # Check operation status
    if op.status not in ('pending', 'queued'):
        raise OperationError(f"Cannot skip operation in status '{op.status}'", 400)

    # Check previous operation
    prev_op = get_previous_operation(db, po, op)
    if prev_op and prev_op.status not in ('complete', 'skipped'):
        raise OperationError(
            f"Previous operation (sequence {prev_op.sequence}) must be complete before skipping this one",
            400
        )

    # Update operation
    op.status = 'skipped'
    op.notes = f"SKIPPED: {reason}"
    op.updated_at = datetime.utcnow()

    # Update PO status
    update_po_status(db, po)

    db.flush()
    return op


def list_operations(
    db: Session,
    po_id: int
) -> List[ProductionOrderOperation]:
    """
    List operations for a production order.

    Returns:
        List of operations ordered by sequence

    Raises:
        OperationError: If PO not found
    """
    po = db.get(ProductionOrder, po_id)
    if not po:
        raise OperationError(f"Production order {po_id} not found", 404)

    return sorted(po.operations, key=lambda x: x.sequence)
