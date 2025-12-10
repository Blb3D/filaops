"""
Work Centers API Endpoints

CRUD operations for work centers and resources (machines).
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.logging_config import get_logger
from app.models.manufacturing import WorkCenter, Resource
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.manufacturing import (
    WorkCenterCreate,
    WorkCenterUpdate,
    WorkCenterResponse,
    WorkCenterListResponse,
    ResourceCreate,
    ResourceUpdate,
    ResourceResponse,
    ResourceStatus,
)

router = APIRouter()
logger = get_logger(__name__)


# ============================================================================
# Work Center CRUD
# ============================================================================

@router.get("/", response_model=List[WorkCenterListResponse])
async def list_work_centers(
    center_type: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """
    List all work centers.

    - **center_type**: Filter by type (machine, station, labor)
    - **active_only**: Only return active work centers
    """
    query = db.query(WorkCenter).options(joinedload(WorkCenter.resources))

    if center_type:
        query = query.filter(WorkCenter.center_type == center_type)

    if active_only:
        query = query.filter(WorkCenter.is_active== True)

    work_centers = query.order_by(WorkCenter.scheduling_priority.desc(), WorkCenter.name).all()

    result = []
    for wc in work_centers:
        total_rate = (
            float(wc.machine_rate_per_hour or 0) +
            float(wc.labor_rate_per_hour or 0) +
            float(wc.overhead_rate_per_hour or 0)
        )
        result.append(WorkCenterListResponse(
            id=wc.id,
            code=wc.code,
            name=wc.name,
            center_type=wc.center_type,
            capacity_hours_per_day=wc.capacity_hours_per_day,
            total_rate_per_hour=Decimal(str(total_rate)),
            resource_count=len([r for r in wc.resources if r.is_active]),
            is_bottleneck=wc.is_bottleneck,
            is_active=wc.is_active,
        ))

    return result


@router.post("/", response_model=WorkCenterResponse, status_code=status.HTTP_201_CREATED)
async def create_work_center(
    data: WorkCenterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new work center."""
    # Check for duplicate code
    existing = db.query(WorkCenter).filter(WorkCenter.code == data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Work center with code '{data.code}' already exists"
        )

    work_center = WorkCenter(
        code=data.code,
        name=data.name,
        description=data.description,
        center_type=data.center_type.value,
        capacity_hours_per_day=data.capacity_hours_per_day,
        capacity_units_per_hour=data.capacity_units_per_hour,
        machine_rate_per_hour=data.machine_rate_per_hour,
        labor_rate_per_hour=data.labor_rate_per_hour,
        overhead_rate_per_hour=data.overhead_rate_per_hour,
        is_bottleneck=data.is_bottleneck,
        scheduling_priority=data.scheduling_priority,
        is_active=data.is_active,
    )
    db.add(work_center)
    db.commit()
    db.refresh(work_center)

    logger.info(f"Created work center: {work_center.code}")

    return _build_work_center_response(work_center)


@router.get("/{wc_id}", response_model=WorkCenterResponse)
async def get_work_center(
    wc_id: int,
    db: Session = Depends(get_db),
):
    """Get a work center by ID."""
    work_center = db.query(WorkCenter).options(
        joinedload(WorkCenter.resources)
    ).filter(WorkCenter.id == wc_id).first()

    if not work_center:
        raise HTTPException(status_code=404, detail="Work center not found")

    return _build_work_center_response(work_center)


@router.put("/{wc_id}", response_model=WorkCenterResponse)
async def update_work_center(
    wc_id: int,
    data: WorkCenterUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a work center."""
    work_center = db.query(WorkCenter).filter(WorkCenter.id == wc_id).first()
    if not work_center:
        raise HTTPException(status_code=404, detail="Work center not found")

    # Check for duplicate code if changing
    if data.code and data.code != work_center.code:
        existing = db.query(WorkCenter).filter(WorkCenter.code == data.code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Work center with code '{data.code}' already exists"
            )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "center_type" and value:
            value = value.value
        setattr(work_center, field, value)

    work_center.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(work_center)

    logger.info(f"Updated work center: {work_center.code}")

    return _build_work_center_response(work_center)


@router.delete("/{wc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_center(
    wc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a work center (soft delete - marks as inactive)."""
    work_center = db.query(WorkCenter).filter(WorkCenter.id == wc_id).first()
    if not work_center:
        raise HTTPException(status_code=404, detail="Work center not found")

    work_center.is_active = False
    work_center.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Deactivated work center: {work_center.code}")


# ============================================================================
# Resources (Machines) CRUD
# ============================================================================

@router.get("/{wc_id}/resources", response_model=List[ResourceResponse])
async def list_resources(
    wc_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List all resources for a work center."""
    work_center = db.query(WorkCenter).filter(WorkCenter.id == wc_id).first()
    if not work_center:
        raise HTTPException(status_code=404, detail="Work center not found")

    query = db.query(Resource).filter(Resource.work_center_id == wc_id)

    if active_only:
        query = query.filter(Resource.is_active== True)

    resources = query.order_by(Resource.code).all()

    return [_build_resource_response(r, work_center) for r in resources]


@router.post("/{wc_id}/resources", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    wc_id: int,
    data: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new resource (machine) in a work center."""
    work_center = db.query(WorkCenter).filter(WorkCenter.id == wc_id).first()
    if not work_center:
        raise HTTPException(status_code=404, detail="Work center not found")

    resource = Resource(
        work_center_id=wc_id,
        code=data.code,
        name=data.name,
        machine_type=data.machine_type,
        serial_number=data.serial_number,
        bambu_device_id=data.bambu_device_id,
        bambu_ip_address=data.bambu_ip_address,
        capacity_hours_per_day=data.capacity_hours_per_day,
        status=data.status.value,
        is_active=data.is_active,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    logger.info(f"Created resource: {resource.code} in {work_center.code}")

    return _build_resource_response(resource, work_center)


@router.get("/resources/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: int,
    db: Session = Depends(get_db),
):
    """Get a resource by ID."""
    resource = db.query(Resource).options(
        joinedload(Resource.work_center)
    ).filter(Resource.id == resource_id).first()

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    return _build_resource_response(resource, resource.work_center)


@router.put("/resources/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: int,
    data: ResourceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a resource."""
    resource = db.query(Resource).options(
        joinedload(Resource.work_center)
    ).filter(Resource.id == resource_id).first()

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # If reassigning to different work center, validate it exists
    update_data = data.model_dump(exclude_unset=True)
    new_work_center = None
    if "work_center_id" in update_data and update_data["work_center_id"] != resource.work_center_id:
        new_work_center = db.query(WorkCenter).filter(
            WorkCenter.id == update_data["work_center_id"]
        ).first()
        if not new_work_center:
            raise HTTPException(status_code=404, detail="Target work center not found")

    # Update fields
    for field, value in update_data.items():
        if field == "status" and value:
            value = value.value
        setattr(resource, field, value)

    resource.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(resource)

    # Use new work center if reassigned
    work_center = new_work_center if new_work_center else resource.work_center
    logger.info(f"Updated resource: {resource.code}")

    return _build_resource_response(resource, work_center)


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a resource."""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    code = resource.code
    db.delete(resource)
    db.commit()

    logger.info(f"Deleted resource: {code}")


@router.patch("/resources/{resource_id}/status")
async def update_resource_status(
    resource_id: int,
    new_status: ResourceStatus,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Quick update of resource status."""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    old_status = resource.status
    resource.status = new_status.value
    resource.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Resource {resource.code} status: {old_status} -> {new_status.value}")

    return {"id": resource_id, "status": new_status.value}


# ============================================================================
# Helper Functions
# ============================================================================

def _build_work_center_response(wc: WorkCenter) -> WorkCenterResponse:
    """Build a work center response object."""
    total_rate = (
        float(wc.machine_rate_per_hour or 0) +
        float(wc.labor_rate_per_hour or 0) +
        float(wc.overhead_rate_per_hour or 0)
    )
    resource_count = len([r for r in wc.resources if r.is_active]) if wc.resources else 0

    return WorkCenterResponse(
        id=wc.id,
        code=wc.code,
        name=wc.name,
        description=wc.description,
        center_type=wc.center_type,
        capacity_hours_per_day=wc.capacity_hours_per_day,
        capacity_units_per_hour=wc.capacity_units_per_hour,
        machine_rate_per_hour=wc.machine_rate_per_hour,
        labor_rate_per_hour=wc.labor_rate_per_hour,
        overhead_rate_per_hour=wc.overhead_rate_per_hour,
        is_bottleneck=wc.is_bottleneck,
        scheduling_priority=wc.scheduling_priority,
        is_active=wc.is_active,
        created_at=wc.created_at,
        updated_at=wc.updated_at,
        resource_count=resource_count,
        total_rate_per_hour=Decimal(str(total_rate)),
    )


def _build_resource_response(r: Resource, wc: WorkCenter) -> ResourceResponse:
    """Build a resource response object."""
    return ResourceResponse(
        id=r.id,
        work_center_id=r.work_center_id,
        code=r.code,
        name=r.name,
        machine_type=r.machine_type,
        serial_number=r.serial_number,
        bambu_device_id=r.bambu_device_id,
        bambu_ip_address=r.bambu_ip_address,
        capacity_hours_per_day=r.capacity_hours_per_day,
        status=r.status,
        is_active=r.is_active,
        work_center_code=wc.code if wc else None,
        work_center_name=wc.name if wc else None,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


# ============================================================================
# Bambu Print Suite Sync
# ============================================================================

# Hardcoded printer data from Bambu Print Suite config files
# This maps serial numbers to friendly names, models, and IPs
BAMBU_PRINTERS = {
    "01P00A441800676": {
        "name": "Leonardo",
        "model": "P1S",
        "ip": "10.0.0.140",
        "access_code": "57108124",
    },
    "03919C452202053": {
        "name": "Michelangelo",
        "model": "A1",
        "ip": "10.0.0.224",
        "access_code": "28820913",
    },
    "03919C452202806": {
        "name": "Donatello",
        "model": "A1",
        "ip": "10.0.0.191",
        "access_code": "27880645",
    },
    "03919C441302283": {
        "name": "Raphael",
        "model": "A1",
        "ip": "",  # Not in status file yet
        "access_code": "41363670",
    },
}


@router.post("/sync-bambu")
async def sync_bambu_printers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sync printers from Bambu Print Suite configuration.

    Creates or updates resources in the FDM-POOL work center
    based on the known printer configuration.
    """
    # Find FDM-POOL work center
    fdm_pool = db.query(WorkCenter).filter(WorkCenter.code == "FDM-POOL").first()
    if not fdm_pool:
        raise HTTPException(
            status_code=404,
            detail="FDM-POOL work center not found. Create it first."
        )

    created = []
    updated = []
    skipped = []

    for serial, printer_info in BAMBU_PRINTERS.items():
        # Check if resource already exists (by serial number)
        existing = db.query(Resource).filter(
            Resource.serial_number == serial
        ).first()

        if existing:
            # Update existing resource
            changed = False
            if existing.name != printer_info["name"]:
                existing.name = printer_info["name"]
                changed = True
            if existing.machine_type != printer_info["model"]:
                existing.machine_type = printer_info["model"]
                changed = True
            if existing.bambu_ip_address != printer_info["ip"]:
                existing.bambu_ip_address = printer_info["ip"]
                changed = True
            if existing.work_center_id != fdm_pool.id:
                existing.work_center_id = fdm_pool.id
                changed = True

            if changed:
                existing.updated_at = datetime.utcnow()
                updated.append(printer_info["name"])
            else:
                skipped.append(printer_info["name"])
        else:
            # Create new resource
            resource = Resource(
                work_center_id=fdm_pool.id,
                code=f"PRINTER-{serial[-6:]}",
                name=printer_info["name"],
                machine_type=printer_info["model"],
                serial_number=serial,
                bambu_device_id=f"PRINTER-{serial[-6:]}",
                bambu_ip_address=printer_info["ip"],
                capacity_hours_per_day=Decimal("20"),  # 20 hrs/day per printer
                status="available",
                is_active=True,
            )
            db.add(resource)
            created.append(printer_info["name"])

    db.commit()

    # Update FDM-POOL capacity based on number of printers
    active_printers = len(created) + len(updated) + len(skipped)
    new_capacity = Decimal(str(active_printers * 20))  # 20 hrs per printer
    if fdm_pool.capacity_hours_per_day != new_capacity:
        fdm_pool.capacity_hours_per_day = new_capacity
        fdm_pool.updated_at = datetime.utcnow()
        db.commit()

    logger.info(f"Bambu sync: created={created}, updated={updated}, skipped={skipped}")

    return {
        "success": True,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "total_printers": active_printers,
        "pool_capacity_hours": float(new_capacity),
    }
