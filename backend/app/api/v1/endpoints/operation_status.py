"""
API endpoints for operation status transitions.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.schemas.operation_status import (
    OperationStartRequest,
    OperationCompleteRequest,
    OperationSkipRequest,
    OperationResponse,
    OperationListItem,
    ProductionOrderSummary,
    NextOperationInfo,
)
from app.schemas.operation_blocking import (
    CanStartResponse,
    OperationBlockingResponse,
)
from app.services.operation_status import (
    OperationError,
    start_operation,
    complete_operation,
    skip_operation,
    list_operations,
    get_next_operation,
)
from app.services.operation_blocking import (
    OperationBlockingError,
    can_operation_start,
    check_operation_blocking,
)
from app.services.resource_scheduling import (
    schedule_operation as schedule_operation_service,
)
from app.services.operation_generation import (
    generate_operations_manual,
)
from app.schemas.resource_scheduling import (
    ScheduleOperationRequest,
    ScheduleOperationResponse,
)
from app.schemas.routing_operations import (
    GenerateOperationsRequest,
    GenerateOperationsResponse,
)
from app.models.production_order import ProductionOrder, ProductionOrderOperation
from app.models.work_center import Machine


router = APIRouter()


def build_operation_response(op, po, next_op=None) -> OperationResponse:
    """Build response from operation model."""
    resource_code = None
    if op.resource:
        resource_code = op.resource.code

    # Get current operation sequence for PO
    current_seq = None
    for o in sorted(po.operations, key=lambda x: x.sequence):
        if o.status not in ('complete', 'skipped'):
            current_seq = o.sequence
            break

    next_op_info = None
    if next_op:
        next_op_info = NextOperationInfo(
            id=next_op.id,
            sequence=next_op.sequence,
            operation_code=next_op.operation_code,
            operation_name=next_op.operation_name,
            status=next_op.status,
            work_center_code=next_op.work_center.code if next_op.work_center else None,
            work_center_name=next_op.work_center.name if next_op.work_center else None,
        )

    return OperationResponse(
        id=op.id,
        sequence=op.sequence,
        operation_code=op.operation_code,
        operation_name=op.operation_name,
        status=op.status,
        resource_id=op.resource_id,
        resource_code=resource_code,
        planned_run_minutes=op.planned_run_minutes,
        actual_start=op.actual_start,
        actual_end=op.actual_end,
        actual_run_minutes=op.actual_run_minutes,
        quantity_completed=op.quantity_completed,
        quantity_scrapped=op.quantity_scrapped,
        notes=op.notes,
        production_order=ProductionOrderSummary(
            id=po.id,
            code=po.code,
            status=po.status,
            current_operation_sequence=current_seq,
        ),
        next_operation=next_op_info,
    )


@router.get(
    "/{po_id}/operations",
    response_model=List[OperationListItem],
    summary="List operations for a production order"
)
def get_operations(
    po_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get all operations for a production order, ordered by sequence.
    """
    try:
        ops = list_operations(db, po_id)
    except OperationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    result = []
    for op in ops:
        result.append(OperationListItem(
            id=op.id,
            sequence=op.sequence,
            operation_code=op.operation_code,
            operation_name=op.operation_name,
            status=op.status,
            work_center_id=op.work_center_id,
            work_center_code=op.work_center.code if op.work_center else None,
            work_center_name=op.work_center.name if op.work_center else None,
            resource_id=op.resource_id,
            resource_code=op.resource.code if op.resource else None,
            planned_setup_minutes=op.planned_setup_minutes,
            planned_run_minutes=op.planned_run_minutes,
            actual_start=op.actual_start,
            actual_end=op.actual_end,
            quantity_completed=op.quantity_completed,
            quantity_scrapped=op.quantity_scrapped,
        ))

    return result


@router.post(
    "/{po_id}/operations/{op_id}/start",
    response_model=OperationResponse,
    summary="Start an operation"
)
def start_operation_endpoint(
    po_id: int,
    op_id: int,
    request: OperationStartRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Start an operation.

    Validations:
    - Operation must be in pending or queued status
    - Previous operation must be complete or skipped
    - Resource must not have conflicting scheduled operation
    """
    try:
        op = start_operation(
            db=db,
            po_id=po_id,
            op_id=op_id,
            resource_id=request.resource_id,
            operator_name=request.operator_name,
            notes=request.notes,
        )
        db.commit()
    except OperationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    po = db.get(ProductionOrder, po_id)
    next_op = get_next_operation(db, po, op)

    return build_operation_response(op, po, next_op)


@router.post(
    "/{po_id}/operations/{op_id}/complete",
    response_model=OperationResponse,
    summary="Complete an operation"
)
def complete_operation_endpoint(
    po_id: int,
    op_id: int,
    request: OperationCompleteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Complete an operation.

    Validations:
    - Operation must be in running status

    Side effects:
    - Updates PO status if this is the last operation
    - Consumes materials for this operation stage
    """
    try:
        op = complete_operation(
            db=db,
            po_id=po_id,
            op_id=op_id,
            quantity_completed=request.quantity_completed,
            quantity_scrapped=request.quantity_scrapped,
            actual_run_minutes=request.actual_run_minutes,
            notes=request.notes,
        )
        db.commit()
    except OperationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    po = db.get(ProductionOrder, po_id)
    next_op = get_next_operation(db, po, op)

    return build_operation_response(op, po, next_op)


@router.post(
    "/{po_id}/operations/{op_id}/skip",
    response_model=OperationResponse,
    summary="Skip an operation"
)
def skip_operation_endpoint(
    po_id: int,
    op_id: int,
    request: OperationSkipRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Skip an operation with a reason.

    Use cases:
    - Customer waived QC requirement
    - Operation not applicable for this product variant
    """
    try:
        op = skip_operation(
            db=db,
            po_id=po_id,
            op_id=op_id,
            reason=request.reason,
        )
        db.commit()
    except OperationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    po = db.get(ProductionOrder, po_id)
    next_op = get_next_operation(db, po, op)

    return build_operation_response(op, po, next_op)


# =============================================================================
# Operation Blocking Check Endpoints (API-402)
# =============================================================================

@router.get(
    "/{po_id}/operations/{op_id}/can-start",
    response_model=CanStartResponse,
    summary="Check if operation can start"
)
def check_can_start(
    po_id: int,
    op_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Quick check if an operation can start based on material availability.

    Only checks materials for THIS operation's consume stage.
    For example, PRINT only checks production materials, not shipping materials.
    """
    try:
        result = can_operation_start(db, po_id, op_id)
        return result
    except OperationBlockingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/{po_id}/operations/{op_id}/blocking-issues",
    response_model=OperationBlockingResponse,
    summary="Get detailed blocking issues for operation"
)
def get_blocking_issues(
    po_id: int,
    op_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get detailed blocking issues for an operation.

    Returns all material checks, not just blocking ones.
    Useful for showing full material requirements and availability.
    """
    try:
        result = check_operation_blocking(db, po_id, op_id)
        return result
    except OperationBlockingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# Resource Scheduling Endpoints (API-403)
# =============================================================================

@router.post(
    "/{po_id}/operations/{op_id}/schedule",
    response_model=ScheduleOperationResponse,
    summary="Schedule an operation on a resource"
)
def schedule_operation_endpoint(
    po_id: int,
    op_id: int,
    request: ScheduleOperationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Schedule an operation on a resource with time slot validation.

    Validates:
    - Resource exists
    - Operation exists and belongs to this PO
    - No time conflicts with existing scheduled operations

    Returns 409 Conflict if scheduling would create a conflict.
    """
    # Validate PO exists
    po = db.get(ProductionOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")

    # Validate operation exists and belongs to PO
    op = db.get(ProductionOrderOperation, op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")
    if op.production_order_id != po_id:
        raise HTTPException(
            status_code=404,
            detail=f"Operation {op_id} does not belong to production order {po_id}"
        )

    # Validate resource exists
    resource = db.get(Machine, request.resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Attempt to schedule
    success, conflicts = schedule_operation_service(
        db=db,
        operation=op,
        resource_id=request.resource_id,
        scheduled_start=request.scheduled_start,
        scheduled_end=request.scheduled_end,
    )

    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Scheduling conflict with {len(conflicts)} existing operation(s)"
        )

    db.commit()

    return ScheduleOperationResponse(success=True)


# =============================================================================
# Operation Generation Endpoint (API-404)
# =============================================================================

@router.post(
    "/{po_id}/operations/generate",
    response_model=GenerateOperationsResponse,
    summary="Generate operations from routing"
)
def generate_operations(
    po_id: int,
    request: GenerateOperationsRequest = GenerateOperationsRequest(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Manually generate operations from routing.

    - Use force=True to replace existing operations
    - Without force, fails if operations already exist
    """
    po = db.get(ProductionOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")

    try:
        created_ops = generate_operations_manual(db, po, force=request.force)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return GenerateOperationsResponse(
        success=True,
        operations_created=len(created_ops),
        message=f"Generated {len(created_ops)} operations from routing"
    )
