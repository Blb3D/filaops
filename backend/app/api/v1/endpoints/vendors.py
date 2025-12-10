"""
Vendors API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.session import get_db
from app.logging_config import get_logger
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.purchasing import (
    VendorCreate,
    VendorUpdate,
    VendorListResponse,
    VendorResponse,
)

router = APIRouter()
logger = get_logger(__name__)


def _generate_vendor_code(db: Session) -> str:
    """Generate next vendor code (VND-001, VND-002, etc.)"""
    last = db.query(Vendor).order_by(desc(Vendor.code)).first()
    if last and last.code.startswith("VND-"):
        try:
            num = int(last.code.split("-")[1])
            return f"VND-{num + 1:03d}"
        except (IndexError, ValueError):
            pass
    return "VND-001"


# ============================================================================
# Vendor CRUD
# ============================================================================

@router.get("/", response_model=List[VendorListResponse])
async def list_vendors(
    search: Optional[str] = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List all vendors

    - **search**: Search by name, code, or contact
    - **active_only**: Only show active vendors
    """
    query = db.query(Vendor)

    if active_only:
        query = query.filter(Vendor.is_active.is_(True))

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Vendor.name.ilike(search_filter)) |
            (Vendor.code.ilike(search_filter)) |
            (Vendor.contact_name.ilike(search_filter)) |
            (Vendor.email.ilike(search_filter))
        )

    vendors = query.order_by(Vendor.name).offset(skip).limit(limit).all()

    # Get PO counts for each vendor
    po_counts = dict(
        db.query(
            PurchaseOrder.vendor_id,
            func.count(PurchaseOrder.id)
        ).group_by(PurchaseOrder.vendor_id).all()
    )

    result = []
    for v in vendors:
        result.append(VendorListResponse(
            id=v.id,
            code=v.code,
            name=v.name,
            contact_name=v.contact_name,
            email=v.email,
            phone=v.phone,
            city=v.city,
            state=v.state,
            payment_terms=v.payment_terms,
            is_active=v.is_active,
            po_count=po_counts.get(v.id, 0)
        ))

    return result


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
):
    """Get vendor details by ID"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.post("/", response_model=VendorResponse, status_code=201)
async def create_vendor(
    request: VendorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new vendor"""
    # Generate code if not provided
    code = request.code if request.code else _generate_vendor_code(db)

    # Check for duplicate code
    existing = db.query(Vendor).filter(Vendor.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Vendor code '{code}' already exists")

    vendor = Vendor(
        code=code,
        name=request.name,
        contact_name=request.contact_name,
        email=request.email,
        phone=request.phone,
        website=request.website,
        address_line1=request.address_line1,
        address_line2=request.address_line2,
        city=request.city,
        state=request.state,
        postal_code=request.postal_code,
        country=request.country,
        payment_terms=request.payment_terms,
        account_number=request.account_number,
        tax_id=request.tax_id,
        lead_time_days=request.lead_time_days,
        rating=request.rating,
        notes=request.notes,
        is_active=request.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    logger.info(f"Created vendor {vendor.code}: {vendor.name}")
    return vendor


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: int,
    request: VendorUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a vendor"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Check for duplicate code if changing
    if request.code and request.code != vendor.code:
        existing = db.query(Vendor).filter(Vendor.code == request.code).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Vendor code '{request.code}' already exists")

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)

    vendor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vendor)

    logger.info(f"Updated vendor {vendor.code}")
    return vendor


@router.delete("/{vendor_id}")
async def delete_vendor(
    vendor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a vendor (soft delete - marks as inactive)

    Will fail if vendor has associated purchase orders
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Check for POs
    po_count = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.vendor_id == vendor_id
    ).scalar()

    if po_count > 0:
        # Soft delete
        vendor.is_active = False
        vendor.updated_at = datetime.utcnow()
        db.commit()
        return {"message": f"Vendor {vendor.code} deactivated (has {po_count} POs)"}
    else:
        # Hard delete if no POs
        db.delete(vendor)
        db.commit()
        return {"message": f"Vendor {vendor.code} deleted"}
