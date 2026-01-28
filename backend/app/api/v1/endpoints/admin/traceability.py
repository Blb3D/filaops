"""
Traceability API Endpoints - Serial Numbers, Material Lots, and Recall Queries

Supports tiered traceability for B2B compliance:
- NONE: No tracking (B2C default)
- LOT: Batch tracking only
- SERIAL: Individual part tracking
- FULL: LOT + SERIAL + Certificate of Conformance
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.product import Product
from app.models.production_order import ProductionOrder
from app.models.sales_order import SalesOrder
from app.models.vendor import Vendor
from app.models.traceability import SerialNumber, MaterialLot, ProductionLotConsumption, CustomerTraceabilityProfile
from app.schemas.traceability import (
    # Customer Profiles
    CustomerTraceabilityProfileCreate,
    CustomerTraceabilityProfileUpdate,
    CustomerTraceabilityProfileResponse,
    # Material Lots
    MaterialLotCreate,
    MaterialLotUpdate,
    MaterialLotResponse,
    MaterialLotListResponse,
    # Serial Numbers
    SerialNumberCreate,
    SerialNumberUpdate,
    SerialNumberResponse,
    SerialNumberListResponse,
    # Lot Consumption
    ProductionLotConsumptionCreate,
    ProductionLotConsumptionResponse,
    # Recall Queries
    RecallForwardQueryResponse,
    RecallBackwardQueryResponse,
    RecallAffectedProduct,
    MaterialLotUsed,
)

router = APIRouter(prefix="/traceability", tags=["Traceability"])


# =============================================================================
# Customer Traceability Profiles
# =============================================================================


@router.get("/profiles", response_model=List[CustomerTraceabilityProfileResponse])
async def list_traceability_profiles(
    traceability_level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all customer traceability profiles."""
    query = db.query(CustomerTraceabilityProfile)

    if traceability_level:
        query = query.filter(CustomerTraceabilityProfile.traceability_level == traceability_level)

    return query.all()


@router.get("/profiles/{user_id}", response_model=CustomerTraceabilityProfileResponse)
async def get_traceability_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get traceability profile for a specific customer."""
    profile = db.query(CustomerTraceabilityProfile).filter(CustomerTraceabilityProfile.user_id == user_id).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Traceability profile not found")

    return profile


@router.post("/profiles", response_model=CustomerTraceabilityProfileResponse)
async def create_traceability_profile(
    request: CustomerTraceabilityProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a traceability profile for a customer."""
    # Check user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check profile doesn't already exist
    existing = (
        db.query(CustomerTraceabilityProfile).filter(CustomerTraceabilityProfile.user_id == request.user_id).first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists for this user")

    # Validate traceability level
    valid_levels = ["none", "lot", "serial", "full"]
    if request.traceability_level not in valid_levels:
        raise HTTPException(status_code=400, detail=f"Invalid traceability level. Must be one of: {valid_levels}")

    profile = CustomerTraceabilityProfile(**request.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Also update user's traceability_level for quick access (using ORM to prevent SQL injection)
    user.traceability_level = request.traceability_level
    db.commit()

    return profile


@router.patch("/profiles/{user_id}", response_model=CustomerTraceabilityProfileResponse)
async def update_traceability_profile(
    user_id: int,
    request: CustomerTraceabilityProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a customer's traceability profile."""
    profile = db.query(CustomerTraceabilityProfile).filter(CustomerTraceabilityProfile.user_id == user_id).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = request.model_dump(exclude_unset=True)

    # Validate traceability level if provided
    if "traceability_level" in update_data:
        valid_levels = ["none", "lot", "serial", "full"]
        if update_data["traceability_level"] not in valid_levels:
            raise HTTPException(status_code=400, detail=f"Invalid traceability level. Must be one of: {valid_levels}")

    for field, value in update_data.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)

    # Update user's quick-access field (using ORM to prevent SQL injection)
    if "traceability_level" in update_data:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.traceability_level = update_data["traceability_level"]
            db.commit()

    return profile


# =============================================================================
# Material Lots
# =============================================================================


@router.get("/lots", response_model=MaterialLotListResponse)
async def list_material_lots(
    product_id: Optional[int] = None,
    status: Optional[str] = None,
    vendor_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List material lots with filtering and pagination."""
    query = db.query(MaterialLot)

    if product_id:
        query = query.filter(MaterialLot.product_id == product_id)
    if status:
        query = query.filter(MaterialLot.status == status)
    if vendor_id:
        query = query.filter(MaterialLot.vendor_id == vendor_id)
    if search:
        query = query.filter(
            or_(
                MaterialLot.lot_number.ilike(f"%{search}%"),
                MaterialLot.vendor_lot_number.ilike(f"%{search}%"),
            )
        )

    total = query.count()

    lots = query.order_by(desc(MaterialLot.received_date)).offset((page - 1) * page_size).limit(page_size).all()

    # Calculate quantity_remaining for response
    items = []
    for lot in lots:
        lot_dict = {
            "id": lot.id,
            "lot_number": lot.lot_number,
            "product_id": lot.product_id,
            "vendor_id": lot.vendor_id,
            "purchase_order_id": lot.purchase_order_id,
            "vendor_lot_number": lot.vendor_lot_number,
            "quantity_received": lot.quantity_received,
            "quantity_consumed": lot.quantity_consumed,
            "quantity_scrapped": lot.quantity_scrapped,
            "quantity_adjusted": lot.quantity_adjusted,
            "quantity_remaining": lot.quantity_remaining,
            "status": lot.status,
            "certificate_of_analysis": lot.certificate_of_analysis,
            "coa_file_path": lot.coa_file_path,
            "inspection_status": lot.inspection_status,
            "manufactured_date": lot.manufactured_date,
            "expiration_date": lot.expiration_date,
            "received_date": lot.received_date,
            "unit_cost": lot.unit_cost,
            "location": lot.location,
            "notes": lot.notes,
            "created_at": lot.created_at,
            "updated_at": lot.updated_at,
        }
        items.append(MaterialLotResponse(**lot_dict))

    return MaterialLotListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/lots/{lot_id}", response_model=MaterialLotResponse)
async def get_material_lot(
    lot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific material lot by ID."""
    lot = db.query(MaterialLot).filter(MaterialLot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Material lot not found")

    return MaterialLotResponse(
        id=lot.id,
        lot_number=lot.lot_number,
        product_id=lot.product_id,
        vendor_id=lot.vendor_id,
        purchase_order_id=lot.purchase_order_id,
        vendor_lot_number=lot.vendor_lot_number,
        quantity_received=lot.quantity_received,
        quantity_consumed=lot.quantity_consumed,
        quantity_scrapped=lot.quantity_scrapped,
        quantity_adjusted=lot.quantity_adjusted,
        quantity_remaining=lot.quantity_remaining,
        status=lot.status,
        certificate_of_analysis=lot.certificate_of_analysis,
        coa_file_path=lot.coa_file_path,
        inspection_status=lot.inspection_status,
        manufactured_date=lot.manufactured_date,
        expiration_date=lot.expiration_date,
        received_date=lot.received_date,
        unit_cost=lot.unit_cost,
        location=lot.location,
        notes=lot.notes,
        created_at=lot.created_at,
        updated_at=lot.updated_at,
    )


@router.post("/lots", response_model=MaterialLotResponse)
async def create_material_lot(
    request: MaterialLotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new material lot (typically when receiving materials)."""
    # Check product exists
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check lot number is unique
    existing = db.query(MaterialLot).filter(MaterialLot.lot_number == request.lot_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Lot number already exists")

    lot_data = request.model_dump()
    if not lot_data.get("received_date"):
        lot_data["received_date"] = date.today()

    lot = MaterialLot(**lot_data)
    db.add(lot)
    db.commit()
    db.refresh(lot)

    return MaterialLotResponse(
        id=lot.id,
        lot_number=lot.lot_number,
        product_id=lot.product_id,
        vendor_id=lot.vendor_id,
        purchase_order_id=lot.purchase_order_id,
        vendor_lot_number=lot.vendor_lot_number,
        quantity_received=lot.quantity_received,
        quantity_consumed=lot.quantity_consumed or Decimal(0),
        quantity_scrapped=lot.quantity_scrapped or Decimal(0),
        quantity_adjusted=lot.quantity_adjusted or Decimal(0),
        quantity_remaining=lot.quantity_remaining,
        status=lot.status,
        certificate_of_analysis=lot.certificate_of_analysis,
        coa_file_path=lot.coa_file_path,
        inspection_status=lot.inspection_status,
        manufactured_date=lot.manufactured_date,
        expiration_date=lot.expiration_date,
        received_date=lot.received_date,
        unit_cost=lot.unit_cost,
        location=lot.location,
        notes=lot.notes,
        created_at=lot.created_at,
        updated_at=lot.updated_at,
    )


@router.patch("/lots/{lot_id}", response_model=MaterialLotResponse)
async def update_material_lot(
    lot_id: int,
    request: MaterialLotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a material lot."""
    lot = db.query(MaterialLot).filter(MaterialLot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Material lot not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lot, field, value)

    lot.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lot)

    return MaterialLotResponse(
        id=lot.id,
        lot_number=lot.lot_number,
        product_id=lot.product_id,
        vendor_id=lot.vendor_id,
        purchase_order_id=lot.purchase_order_id,
        vendor_lot_number=lot.vendor_lot_number,
        quantity_received=lot.quantity_received,
        quantity_consumed=lot.quantity_consumed,
        quantity_scrapped=lot.quantity_scrapped,
        quantity_adjusted=lot.quantity_adjusted,
        quantity_remaining=lot.quantity_remaining,
        status=lot.status,
        certificate_of_analysis=lot.certificate_of_analysis,
        coa_file_path=lot.coa_file_path,
        inspection_status=lot.inspection_status,
        manufactured_date=lot.manufactured_date,
        expiration_date=lot.expiration_date,
        received_date=lot.received_date,
        unit_cost=lot.unit_cost,
        location=lot.location,
        notes=lot.notes,
        created_at=lot.created_at,
        updated_at=lot.updated_at,
    )


@router.post("/lots/generate-number")
async def generate_lot_number(
    material_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate the next lot number for a material."""
    year = datetime.utcnow().year
    prefix = f"{material_code}-{year}-"

    # Find highest existing sequence for this prefix
    last_lot = (
        db.query(MaterialLot)
        .filter(MaterialLot.lot_number.like(f"{prefix}%"))
        .order_by(desc(MaterialLot.lot_number))
        .first()
    )

    if last_lot:
        try:
            seq = int(last_lot.lot_number.replace(prefix, ""))
            next_seq = seq + 1
        except ValueError:
            next_seq = 1
    else:
        next_seq = 1

    return {"lot_number": f"{prefix}{next_seq:04d}"}


# =============================================================================
# Serial Numbers
# =============================================================================


@router.get("/serials", response_model=SerialNumberListResponse)
async def list_serial_numbers(
    product_id: Optional[int] = None,
    production_order_id: Optional[int] = None,
    status: Optional[str] = None,
    sales_order_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List serial numbers with filtering and pagination."""
    query = db.query(SerialNumber)

    if product_id:
        query = query.filter(SerialNumber.product_id == product_id)
    if production_order_id:
        query = query.filter(SerialNumber.production_order_id == production_order_id)
    if status:
        query = query.filter(SerialNumber.status == status)
    if sales_order_id:
        query = query.filter(SerialNumber.sales_order_id == sales_order_id)
    if search:
        query = query.filter(SerialNumber.serial_number.ilike(f"%{search}%"))

    total = query.count()

    serials = query.order_by(desc(SerialNumber.manufactured_at)).offset((page - 1) * page_size).limit(page_size).all()

    return SerialNumberListResponse(
        items=serials,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/serials/{serial_id}", response_model=SerialNumberResponse)
async def get_serial_number(
    serial_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific serial number by ID."""
    serial = db.query(SerialNumber).filter(SerialNumber.id == serial_id).first()
    if not serial:
        raise HTTPException(status_code=404, detail="Serial number not found")
    return serial


@router.get("/serials/lookup/{serial_number}", response_model=SerialNumberResponse)
async def lookup_serial_number(
    serial_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Look up a serial number by the serial string."""
    serial = db.query(SerialNumber).filter(SerialNumber.serial_number == serial_number).first()
    if not serial:
        raise HTTPException(status_code=404, detail="Serial number not found")
    return serial


@router.post("/serials", response_model=List[SerialNumberResponse])
async def create_serial_numbers(
    request: SerialNumberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate serial numbers for a production order."""
    # Verify production order exists
    po = db.query(ProductionOrder).filter(ProductionOrder.id == request.production_order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")

    # Verify product exists
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Generate serial numbers
    today = datetime.utcnow()
    date_str = today.strftime("%Y%m%d")
    prefix = f"BLB-{date_str}-"

    # Find highest existing sequence for today
    last_serial = (
        db.query(SerialNumber)
        .filter(SerialNumber.serial_number.like(f"{prefix}%"))
        .order_by(desc(SerialNumber.serial_number))
        .first()
    )

    if last_serial:
        try:
            seq = int(last_serial.serial_number.replace(prefix, ""))
        except ValueError:
            seq = 0
    else:
        seq = 0

    created_serials = []
    for i in range(request.quantity):
        seq += 1
        serial = SerialNumber(
            serial_number=f"{prefix}{seq:04d}",
            product_id=request.product_id,
            production_order_id=request.production_order_id,
            status="manufactured",
            qc_passed=request.qc_passed,
            qc_notes=request.qc_notes,
            manufactured_at=today,
        )
        db.add(serial)
        created_serials.append(serial)

    db.commit()
    for s in created_serials:
        db.refresh(s)

    return created_serials


@router.patch("/serials/{serial_id}", response_model=SerialNumberResponse)
async def update_serial_number(
    serial_id: int,
    request: SerialNumberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a serial number (e.g., mark as sold, shipped, returned)."""
    serial = db.query(SerialNumber).filter(SerialNumber.id == serial_id).first()
    if not serial:
        raise HTTPException(status_code=404, detail="Serial number not found")

    update_data = request.model_dump(exclude_unset=True)

    # Handle status-based timestamp updates
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == "sold" and not serial.sold_at:
            serial.sold_at = datetime.utcnow()
        elif new_status == "shipped" and not serial.shipped_at:
            serial.shipped_at = datetime.utcnow()
        elif new_status == "returned" and not serial.returned_at:
            serial.returned_at = datetime.utcnow()

    for field, value in update_data.items():
        setattr(serial, field, value)

    db.commit()
    db.refresh(serial)
    return serial


# =============================================================================
# Lot Consumption Recording
# =============================================================================


@router.post("/consumptions", response_model=ProductionLotConsumptionResponse)
async def record_lot_consumption(
    request: ProductionLotConsumptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record material lot consumption for a production order."""
    # Verify production order exists
    po = db.query(ProductionOrder).filter(ProductionOrder.id == request.production_order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")

    # Verify material lot exists and has sufficient quantity
    lot = db.query(MaterialLot).filter(MaterialLot.id == request.material_lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Material lot not found")

    if lot.quantity_remaining < request.quantity_consumed:
        raise HTTPException(
            status_code=400, detail=f"Insufficient quantity in lot. Available: {lot.quantity_remaining}"
        )

    # Record consumption
    consumption = ProductionLotConsumption(**request.model_dump())
    db.add(consumption)

    # Update lot consumed quantity
    lot.quantity_consumed = lot.quantity_consumed + request.quantity_consumed

    # Check if lot is depleted
    if lot.quantity_remaining <= 0:
        lot.status = "depleted"

    lot.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(consumption)
    return consumption


@router.get("/consumptions/production/{production_order_id}")
async def get_production_lot_consumptions(
    production_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all lot consumptions for a production order."""
    consumptions = (
        db.query(ProductionLotConsumption)
        .filter(ProductionLotConsumption.production_order_id == production_order_id)
        .all()
    )

    return consumptions


# =============================================================================
# Recall Queries
# =============================================================================


@router.get("/recall/forward/{lot_number}", response_model=RecallForwardQueryResponse)
async def recall_forward_query(
    lot_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Forward recall query: What did we make with this lot?

    Returns all products/serial numbers that used material from this lot.
    """
    lot = db.query(MaterialLot).filter(MaterialLot.lot_number == lot_number).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Material lot not found")

    # Get the material name
    product = db.query(Product).filter(Product.id == lot.product_id).first()
    material_name = product.name if product else "Unknown"

    # Find all affected serial numbers through consumption records
    affected = (
        db.query(
            SerialNumber.serial_number,
            Product.name.label("product_name"),
            ProductionOrder.code.label("production_order_code"),
            SerialNumber.manufactured_at,
            SerialNumber.status,
            User.email.label("customer_email"),
            SalesOrder.order_number.label("sales_order_number"),
            SerialNumber.shipped_at,
        )
        .join(
            ProductionLotConsumption, ProductionLotConsumption.production_order_id == SerialNumber.production_order_id
        )
        .join(Product, Product.id == SerialNumber.product_id)
        .join(ProductionOrder, ProductionOrder.id == SerialNumber.production_order_id)
        .outerjoin(SalesOrder, SalesOrder.id == SerialNumber.sales_order_id)
        .outerjoin(User, User.id == SalesOrder.user_id)
        .filter(ProductionLotConsumption.material_lot_id == lot.id)
        .all()
    )

    affected_products = [
        RecallAffectedProduct(
            serial_number=row.serial_number,
            product_name=row.product_name,
            production_order_code=row.production_order_code,
            manufactured_at=row.manufactured_at,
            status=row.status,
            customer_email=row.customer_email,
            sales_order_number=row.sales_order_number,
            shipped_at=row.shipped_at,
        )
        for row in affected
    ]

    return RecallForwardQueryResponse(
        lot_number=lot.lot_number,
        material_name=material_name,
        quantity_received=lot.quantity_received,
        quantity_consumed=lot.quantity_consumed,
        affected_products=affected_products,
        total_affected=len(affected_products),
    )


@router.get("/recall/backward/{serial_number}", response_model=RecallBackwardQueryResponse)
async def recall_backward_query(
    serial_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Backward recall query: What material lots went into this serial number?

    Returns all material lots used to produce this unit.
    """
    serial = db.query(SerialNumber).filter(SerialNumber.serial_number == serial_number).first()
    if not serial:
        raise HTTPException(status_code=404, detail="Serial number not found")

    # Get product name
    product = db.query(Product).filter(Product.id == serial.product_id).first()
    product_name = product.name if product else "Unknown"

    # Find all material lots used in this production order
    lots_used = (
        db.query(
            MaterialLot.lot_number,
            Product.name.label("material_name"),
            Vendor.name.label("vendor_name"),
            MaterialLot.vendor_lot_number,
            ProductionLotConsumption.quantity_consumed,
        )
        .join(ProductionLotConsumption, ProductionLotConsumption.material_lot_id == MaterialLot.id)
        .join(Product, Product.id == MaterialLot.product_id)
        .outerjoin(Vendor, Vendor.id == MaterialLot.vendor_id)
        .filter(ProductionLotConsumption.production_order_id == serial.production_order_id)
        .all()
    )

    material_lots = [
        MaterialLotUsed(
            lot_number=row.lot_number,
            material_name=row.material_name,
            vendor_name=row.vendor_name,
            vendor_lot_number=row.vendor_lot_number,
            quantity_consumed=row.quantity_consumed,
        )
        for row in lots_used
    ]

    return RecallBackwardQueryResponse(
        serial_number=serial.serial_number,
        product_name=product_name,
        manufactured_at=serial.manufactured_at,
        material_lots_used=material_lots,
    )
