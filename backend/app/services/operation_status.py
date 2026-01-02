"""
Service layer for operation status transitions.
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.production_order import (
    ProductionOrder,
    ProductionOrderOperation,
    ProductionOrderOperationMaterial
)
from app.models.work_center import Machine
from app.services.operation_blocking import check_operation_blocking
from app.services.resource_scheduling import check_resource_available_now


logger = logging.getLogger(__name__)


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


def get_operation_max_quantity(
    po: ProductionOrder,
    op: ProductionOrderOperation
) -> Decimal:
    """
    Get maximum quantity allowed for this operation.

    Rules:
    - First operation: order quantity (allows over-production for MTS)
    - Subsequent operations: previous completed op's qty_completed
    - If previous op was skipped, inherit from the op before that

    Returns:
        Maximum quantity (good + bad) allowed for this operation
    """
    ops = sorted(po.operations, key=lambda x: x.sequence)

    # Find this op's position
    op_index = None
    for i, o in enumerate(ops):
        if o.id == op.id:
            op_index = i
            break

    if op_index is None or op_index == 0:
        # First operation - max is order quantity
        return po.quantity_ordered

    # Walk backwards to find last completed operation
    for i in range(op_index - 1, -1, -1):
        prev = ops[i]
        if prev.status == 'complete':
            return prev.quantity_completed
        elif prev.status == 'skipped':
            continue  # Keep looking back
        else:
            # Previous op not done yet - shouldn't happen if sequence enforced
            return Decimal("0")

    # No completed ops before this one - use order qty
    return po.quantity_ordered


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
    - All complete/skipped AND qty_completed >= qty_ordered → complete
    - All complete/skipped AND qty_completed < qty_ordered → short
    - Any running or mixed → in_progress
    """
    if not po.operations:
        return po.status  # No operations, keep current

    statuses = [op.status for op in po.operations]

    if all(s == 'pending' for s in statuses):
        return 'released'
    elif all(s in ('complete', 'skipped') for s in statuses):
        # All operations done - check if we met the quantity requirement
        qty_ordered = po.quantity_ordered or Decimal("0")
        qty_completed = po.quantity_completed or Decimal("0")

        if qty_completed >= qty_ordered:
            return 'complete'
        else:
            # Under-production: not enough good pieces to fulfill order
            return 'short'
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


def consume_operation_materials(
    db: Session,
    op: ProductionOrderOperation,
    quantity_completed: Decimal,
    quantity_scrapped: Decimal
) -> List[dict]:
    """
    Consume materials for a completed operation.

    For each ProductionOrderOperationMaterial:
    - Update quantity_consumed to quantity_required (full consumption)
    - Set status to 'consumed'
    - Record consumed_at timestamp

    Note: This consumes the full planned amount regardless of yield.
    For 3D printing, filament is fully consumed whether the part is good or bad.
    Inventory adjustment can be done separately if actual usage differs.

    Args:
        db: Database session
        op: The operation being completed
        quantity_completed: Good quantity produced
        quantity_scrapped: Bad quantity produced

    Returns:
        List of consumed material summaries
    """
    consumed_materials = []

    # Get materials for this operation
    materials = db.query(ProductionOrderOperationMaterial).filter(
        ProductionOrderOperationMaterial.production_order_operation_id == op.id
    ).all()

    for mat in materials:
        # Skip already consumed or cost-only materials
        if mat.status == 'consumed':
            logger.info(f"Material {mat.id} already consumed, skipping")
            continue

        # For 3D printing, consume full planned amount
        # (filament is used whether part is good or scrapped)
        qty_to_consume = mat.quantity_required or Decimal("0")

        # Update material record
        mat.quantity_consumed = qty_to_consume
        mat.status = 'consumed'
        mat.consumed_at = datetime.utcnow()
        mat.updated_at = datetime.utcnow()

        consumed_materials.append({
            "material_id": mat.id,
            "component_id": mat.component_id,
            "quantity_consumed": float(qty_to_consume),
            "unit": mat.unit
        })

        logger.info(
            f"Consumed material {mat.id}: {qty_to_consume} {mat.unit} "
            f"for operation {op.id}"
        )

    return consumed_materials


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
    scrap_reason: Optional[str] = None,
    actual_run_minutes: Optional[int] = None,
    notes: Optional[str] = None
) -> ProductionOrderOperation:
    """
    Complete an operation.

    Validations:
    - Operation must be running
    - quantity_completed + quantity_scrapped <= max_allowed
      (max_allowed = previous op's qty_completed, or order qty for first op)

    Side effects:
    - Updates PO status if last operation
    - Consumes materials for this operation (marks as consumed)

    Returns:
        Updated operation

    Raises:
        OperationError: If validation fails
    """
    po, op = get_operation_with_validation(db, po_id, op_id)

    # Check operation status
    if op.status != 'running':
        raise OperationError("Operation is not running, cannot complete", 400)

    # Validate quantity doesn't exceed max allowed
    max_qty = get_operation_max_quantity(po, op)
    total_qty = quantity_completed + quantity_scrapped

    if total_qty > max_qty:
        raise OperationError(
            f"Total quantity ({total_qty}) exceeds maximum allowed ({max_qty}). "
            f"Good + Bad cannot exceed input from previous operation.",
            400
        )

    # Update operation
    op.status = 'complete'
    op.actual_end = datetime.utcnow()
    op.quantity_completed = quantity_completed
    op.quantity_scrapped = quantity_scrapped
    op.scrap_reason = scrap_reason

    # Calculate actual run time if not provided
    if actual_run_minutes is not None:
        op.actual_run_minutes = actual_run_minutes
    elif op.actual_start:
        elapsed = datetime.utcnow() - op.actual_start
        op.actual_run_minutes = int(elapsed.total_seconds() / 60)

    if notes:
        op.notes = notes
    op.updated_at = datetime.utcnow()

    # Consume materials for this operation
    consumed = consume_operation_materials(db, op, quantity_completed, quantity_scrapped)
    if consumed:
        logger.info(f"Consumed {len(consumed)} materials for operation {op.id}")

    # Auto-skip downstream operations if no good pieces remain
    if quantity_completed == Decimal("0"):
        skipped = auto_skip_downstream_operations(db, po, op)
        if skipped > 0:
            logger.info(f"Auto-skipped {skipped} downstream operations due to 0 good pieces")

    # Update PO quantities BEFORE deriving status
    po.quantity_completed = quantity_completed
    po.quantity_scrapped = (po.quantity_scrapped or Decimal("0")) + quantity_scrapped

    # Update PO status (uses quantity_completed to determine complete vs short)
    update_po_status(db, po)

    db.flush()
    return op


def auto_skip_downstream_operations(
    db: Session,
    po: ProductionOrder,
    completed_op: ProductionOrderOperation
) -> int:
    """
    Auto-skip all downstream operations when no pieces remain.

    Called when an operation completes with quantity_completed = 0.
    All subsequent pending/queued operations are marked as skipped
    with reason indicating no pieces from previous operation.

    Args:
        db: Database session
        po: Production order
        completed_op: The operation that just completed with 0 good pieces

    Returns:
        Number of operations skipped
    """
    ops = sorted(po.operations, key=lambda x: x.sequence)
    skipped_count = 0

    # Find ops after this one
    found_current = False
    for op in ops:
        if op.id == completed_op.id:
            found_current = True
            continue

        if not found_current:
            continue

        # Only skip pending/queued ops
        if op.status in ('pending', 'queued'):
            op.status = 'skipped'
            op.notes = f"SKIPPED: Auto-skipped - no pieces from operation {completed_op.sequence}"
            op.updated_at = datetime.utcnow()
            skipped_count += 1
            logger.info(f"Auto-skipped operation {op.id} (seq {op.sequence}) due to 0 pieces from op {completed_op.sequence}")

    return skipped_count


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
