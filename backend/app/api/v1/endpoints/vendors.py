"""
Vendors API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.session import get_db
from app.logging_config import get_logger
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.deps import get_pagination_params
from app.models.user import User
from app.schemas.purchasing import (
    VendorCreate,
    VendorUpdate,
    VendorListResponse,
    VendorResponse,
)
from app.schemas.common import PaginationParams, ListResponse, PaginationMeta

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


@router.get("/", response_model=ListResponse[VendorListResponse])
async def list_vendors(
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    search: Optional[str] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all vendors with pagination

    - **search**: Search by name, code, or contact
    - **active_only**: Only show active vendors
    - **offset**: Number of records to skip (default: 0)
    - **limit**: Maximum records to return (default: 50, max: 500)
    """
    query = db.query(Vendor)

    if active_only:
        query = query.filter(Vendor.is_active.is_(True))  # noqa: E712

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Vendor.name.ilike(search_filter))
            | (Vendor.code.ilike(search_filter))
            | (Vendor.contact_name.ilike(search_filter))
            | (Vendor.email.ilike(search_filter))
        )

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    vendors = query.order_by(Vendor.name).offset(pagination.offset).limit(pagination.limit).all()

    # Get PO counts for each vendor
    po_counts = dict(
        db.query(PurchaseOrder.vendor_id, func.count(PurchaseOrder.id)).group_by(PurchaseOrder.vendor_id).all()
    )

    result = []
    for v in vendors:
        result.append(
            VendorListResponse(
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
                po_count=po_counts.get(v.id, 0),
            )
        )

    return ListResponse(
        items=result,
        pagination=PaginationMeta(total=total, offset=pagination.offset, limit=pagination.limit, returned=len(result)),
    )


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: int,
    current_user: User = Depends(get_current_user),
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


@router.get("/{vendor_id}/metrics")
async def get_vendor_metrics(
    vendor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get vendor performance metrics

    Returns:
    - Total PO count
    - Total spend
    - Average lead time (days from ordered to received)
    - On-time delivery percentage
    - Recent POs
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Get all POs for this vendor
    pos = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.vendor_id == vendor_id)
        .order_by(desc(PurchaseOrder.created_at))
        .all()
    )

    total_pos = len(pos)
    total_spend = sum(float(po.total_amount or 0) for po in pos)

    # Calculate average lead time (ordered -> received)
    lead_times = []
    on_time_count = 0
    received_count = 0

    for po in pos:
        if po.order_date and po.received_date:
            days = (po.received_date - po.order_date).days
            lead_times.append(days)
            received_count += 1

            # Check if on-time (received on or before expected)
            if po.expected_date and po.received_date <= po.expected_date:
                on_time_count += 1

    avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else None
    on_time_pct = (on_time_count / received_count * 100) if received_count > 0 else None

    # Get recent POs (last 10)
    recent_pos = [
        {
            "id": po.id,
            "po_number": po.po_number,
            "status": po.status,
            "order_date": po.order_date.isoformat() if po.order_date else None,
            "total_amount": float(po.total_amount or 0),
        }
        for po in pos[:10]
    ]

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.name,
        "total_pos": total_pos,
        "total_spend": round(total_spend, 2),
        "avg_lead_time_days": round(avg_lead_time, 1) if avg_lead_time else None,
        "on_time_delivery_pct": round(on_time_pct, 1) if on_time_pct else None,
        "recent_pos": recent_pos,
    }


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
    po_count = db.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.vendor_id == vendor_id).scalar()

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
