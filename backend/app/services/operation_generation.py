"""
Operation generation service.

Copies routing operations to production order operations on release.
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.manufacturing import Routing, RoutingOperation
from app.models.production_order import ProductionOrder, ProductionOrderOperation


def get_active_routing(db: Session, product_id: int) -> Optional[Routing]:
    """
    Get the active routing for a product.

    Args:
        db: Database session
        product_id: Product to get routing for

    Returns:
        Active Routing or None if no routing defined
    """
    return db.query(Routing).filter(
        Routing.product_id == product_id,
        Routing.is_active == True  # noqa: E712
    ).first()


def get_routing_operations(db: Session, routing_id: int) -> List[RoutingOperation]:
    """
    Get operations for a routing, ordered by sequence.

    Args:
        db: Database session
        routing_id: Routing to get operations for

    Returns:
        List of RoutingOperation ordered by sequence
    """
    return db.query(RoutingOperation).filter(
        RoutingOperation.routing_id == routing_id
    ).order_by(RoutingOperation.sequence).all()


def generate_operations_from_routing(
    db: Session,
    production_order: ProductionOrder,
    routing: Routing
) -> List[ProductionOrderOperation]:
    """
    Generate PO operations from a routing template.

    Maps routing operation fields to PO operation fields:
    - sequence → sequence
    - operation_code → operation_code
    - work_center_id → work_center_id
    - setup_time_minutes → planned_setup_minutes
    - run_time_minutes × quantity → planned_run_minutes
    - routing_operation.id → routing_operation_id

    Args:
        db: Database session
        production_order: PO to create operations for
        routing: Routing template to copy from

    Returns:
        List of created ProductionOrderOperation records
    """
    routing_ops = get_routing_operations(db, routing.id)
    created_ops = []

    for routing_op in routing_ops:
        # Calculate run time based on PO quantity
        run_time = float(routing_op.run_time_minutes or 0)
        quantity = float(production_order.quantity_ordered or 1)
        planned_run = run_time * quantity

        po_op = ProductionOrderOperation(
            production_order_id=production_order.id,
            routing_operation_id=routing_op.id,
            sequence=routing_op.sequence,
            operation_code=routing_op.operation_code,
            operation_name=routing_op.operation_name,
            work_center_id=routing_op.work_center_id,
            planned_setup_minutes=routing_op.setup_time_minutes or 0,
            planned_run_minutes=planned_run,
            status='pending'
        )
        db.add(po_op)
        created_ops.append(po_op)

    db.flush()
    for op in created_ops:
        db.refresh(op)

    return created_ops


def release_production_order(
    db: Session,
    production_order: ProductionOrder
) -> Tuple[ProductionOrder, List[ProductionOrderOperation]]:
    """
    Release a production order and generate operations from routing.

    Args:
        db: Database session
        production_order: PO to release

    Returns:
        Tuple of (updated PO, list of created operations)

    Raises:
        ValueError: If PO is not in draft status
    """
    if production_order.status != 'draft':
        raise ValueError(f"Cannot release PO in status '{production_order.status}'. Must be 'draft'.")

    # Check if operations already exist
    existing_ops = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.production_order_id == production_order.id
    ).count()

    created_ops = []

    if existing_ops == 0:
        # Get routing and generate operations
        routing = get_active_routing(db, production_order.product_id)
        if routing:
            created_ops = generate_operations_from_routing(db, production_order, routing)

    # Update status to released
    production_order.status = 'released'
    db.flush()
    db.refresh(production_order)

    return production_order, created_ops


def generate_operations_manual(
    db: Session,
    production_order: ProductionOrder,
    force: bool = False
) -> List[ProductionOrderOperation]:
    """
    Manually trigger operation generation for a PO.

    Args:
        db: Database session
        production_order: PO to generate operations for
        force: If True, delete existing operations and regenerate

    Returns:
        List of created operations

    Raises:
        ValueError: If operations exist and force=False
    """
    # Check for existing operations
    existing_ops = db.query(ProductionOrderOperation).filter(
        ProductionOrderOperation.production_order_id == production_order.id
    ).all()

    if existing_ops and not force:
        raise ValueError("Operations already exist. Use force=True to regenerate.")

    if existing_ops and force:
        # Delete existing operations
        for op in existing_ops:
            db.delete(op)
        db.flush()

    # Get routing
    routing = get_active_routing(db, production_order.product_id)
    if not routing:
        return []

    return generate_operations_from_routing(db, production_order, routing)


def get_product_routing_details(
    db: Session,
    product_id: int
) -> Optional[dict]:
    """
    Get routing details for a product (for UI display).

    Args:
        db: Database session
        product_id: Product to get routing for

    Returns:
        Dict with routing info and operations, or None
    """
    routing = get_active_routing(db, product_id)
    if not routing:
        return None

    operations = get_routing_operations(db, routing.id)

    return {
        'routing_id': routing.id,
        'routing_code': routing.code,
        'routing_name': routing.name,
        'is_active': routing.is_active,
        'operations': [
            {
                'id': op.id,
                'sequence': op.sequence,
                'operation_code': op.operation_code,
                'operation_name': op.operation_name,
                'work_center_id': op.work_center_id,
                'work_center_code': op.work_center.code if op.work_center else None,
                'setup_time_minutes': float(op.setup_time_minutes) if op.setup_time_minutes else None,
                'run_time_minutes': float(op.run_time_minutes) if op.run_time_minutes else None
            }
            for op in operations
        ]
    }
