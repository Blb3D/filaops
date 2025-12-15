"""
Inventory Locations Management API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.api.v1.deps import get_current_staff_user
from app.models.user import User
from app.models.inventory import InventoryLocation

router = APIRouter(prefix="/locations", tags=["locations"])


class LocationCreate(BaseModel):
    code: str
    name: str
    type: Optional[str] = "warehouse"
    parent_id: Optional[int] = None


class LocationUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    parent_id: Optional[int] = None
    active: Optional[bool] = None


class LocationResponse(BaseModel):
    id: int
    code: Optional[str]
    name: str
    type: Optional[str]
    parent_id: Optional[int]
    active: Optional[bool]

    class Config:
        from_attributes = True


@router.get("")
async def list_locations(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """List all inventory locations"""
    query = db.query(InventoryLocation)
    if not include_inactive:
        query = query.filter(InventoryLocation.active == True)  # noqa: E712

    locations = query.order_by(InventoryLocation.code).all()
    return [
        {
            "id": loc.id,
            "code": loc.code,
            "name": loc.name,
            "type": loc.type,
            "parent_id": loc.parent_id,
            "active": loc.active,
        }
        for loc in locations
    ]


@router.get("/{location_id}")
async def get_location(
    location_id: int,
    current_user: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """Get a single location by ID"""
    location = db.query(InventoryLocation).filter(InventoryLocation.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    return {
        "id": location.id,
        "code": location.code,
        "name": location.name,
        "type": location.type,
        "parent_id": location.parent_id,
        "active": location.active,
    }


@router.post("")
async def create_location(
    location: LocationCreate,
    current_user: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """Create a new inventory location"""
    # Check for duplicate code
    existing = db.query(InventoryLocation).filter(InventoryLocation.code == location.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Location code '{location.code}' already exists")

    # Validate parent if provided
    if location.parent_id:
        parent = db.query(InventoryLocation).filter(InventoryLocation.id == location.parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent location not found")
        if not parent.active:
            raise HTTPException(status_code=400, detail="Parent location is inactive")

    new_location = InventoryLocation(
        code=location.code,
        name=location.name,
        type=location.type,
        parent_id=location.parent_id,
        active=True,
    )
    db.add(new_location)
    db.commit()
    db.refresh(new_location)

    return {
        "id": new_location.id,
        "code": new_location.code,
        "name": new_location.name,
        "type": new_location.type,
        "parent_id": new_location.parent_id,
        "active": new_location.active,
    }


@router.put("/{location_id}")
async def update_location(
    location_id: int,
    location: LocationUpdate,
    current_user: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """Update an inventory location"""
    existing = db.query(InventoryLocation).filter(InventoryLocation.id == location_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Location not found")

    # Check for duplicate code if changing
    if location.code and location.code != existing.code:
        duplicate = db.query(InventoryLocation).filter(
            InventoryLocation.code == location.code,
            InventoryLocation.id != location_id
        ).first()
        if duplicate:
            raise HTTPException(status_code=400, detail=f"Location code '{location.code}' already exists")

    # Update fields
    if location.code is not None:
        existing.code = location.code
    if location.name is not None:
        existing.name = location.name
    if location.type is not None:
        existing.type = location.type
    if location.parent_id is not None:
        # Prevent self-reference
        if location.parent_id == location_id:
            raise HTTPException(status_code=400, detail="A location cannot be its own parent")
        # Validate parent exists and is active
        parent = db.query(InventoryLocation).filter(InventoryLocation.id == location.parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent location not found")
        if not parent.active:
            raise HTTPException(status_code=400, detail="Parent location is inactive")
        existing.parent_id = location.parent_id
    if location.active is not None:
        existing.active = location.active

    db.commit()
    db.refresh(existing)

    return {
        "id": existing.id,
        "code": existing.code,
        "name": existing.name,
        "type": existing.type,
        "parent_id": existing.parent_id,
        "active": existing.active,
    }


@router.delete("/{location_id}")
async def delete_location(
    location_id: int,
    current_user: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """Soft delete (deactivate) an inventory location"""
    location = db.query(InventoryLocation).filter(InventoryLocation.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Don't allow deleting MAIN warehouse
    if location.code == "MAIN":
        raise HTTPException(status_code=400, detail="Cannot delete the main warehouse")

    location.active = False
    db.commit()

    return {"message": "Location deactivated"}
