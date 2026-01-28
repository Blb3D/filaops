"""
Customer Management Endpoints (Admin Only)

Handles customer CRUD operations for admin users.
Customers are users with account_type='customer'.

Note: Customer portal login is a Pro feature. In open source, customers
are CRM records for order management. They cannot log in to a portal.
"""

from typing import List, Optional
from datetime import datetime, timezone
import secrets
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.db.session import get_db
from app.models.user import User
from app.models.sales_order import SalesOrder
from app.models.quote import Quote
from app.api.v1.endpoints.auth import get_current_admin_user
from app.core.security import hash_password
from app.logging_config import get_logger
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerListResponse,
    CustomerResponse,
    CustomerSearchResult,
)

router = APIRouter(prefix="/customers", tags=["Admin - Customer Management"])

logger = get_logger(__name__)


def generate_customer_number(db: Session) -> str:
    """Generate next customer number like CUST-001"""
    last_customer = db.query(User).filter(User.customer_number.isnot(None)).order_by(desc(User.customer_number)).first()
    if last_customer and last_customer.customer_number:
        try:
            last_num = int(last_customer.customer_number.split("-")[1])
            return f"CUST-{last_num + 1:03d}"
        except (IndexError, ValueError):
            pass
    return "CUST-001"


# ============================================================================
# LIST & SEARCH ENDPOINTS
# ============================================================================


@router.get("/", response_model=List[CustomerListResponse])
async def list_customers(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    include_inactive: bool = False,
):
    """
    List all customers with optional filters.

    Admin only. Returns customers (users with account_type='customer').
    """
    query = db.query(User).filter(User.account_type == "customer")

    # Status filter
    if status_filter:
        query = query.filter(User.status == status_filter)
    elif not include_inactive:
        query = query.filter(User.status == "active")

    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term))
            | (User.first_name.ilike(search_term))
            | (User.last_name.ilike(search_term))
            | (User.company_name.ilike(search_term))
            | (User.customer_number.ilike(search_term))
            | (User.phone.ilike(search_term))
        )

    # Order by most recent first
    query = query.order_by(desc(User.created_at))

    # Get total count before pagination (for future pagination metadata)
    _total = query.count()
    customers = query.offset(skip).limit(limit).all()

    # Build response with stats
    result = []
    for customer in customers:
        # Get order stats
        order_stats = (
            db.query(
                func.count(SalesOrder.id).label("order_count"),
                func.sum(SalesOrder.grand_total).label("total_spent"),
                func.max(SalesOrder.created_at).label("last_order"),
            )
            .filter(SalesOrder.user_id == customer.id, SalesOrder.status != "cancelled")
            .first()
        )

        # Build full name
        full_name = None
        if customer.first_name and customer.last_name:
            full_name = f"{customer.first_name} {customer.last_name}"
        elif customer.first_name:
            full_name = customer.first_name
        elif customer.last_name:
            full_name = customer.last_name

        result.append(
            {
                "id": customer.id,
                "customer_number": customer.customer_number,
                "email": customer.email,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "company_name": customer.company_name,
                "phone": customer.phone,
                "status": customer.status,
                "full_name": full_name,
                "shipping_address_line1": customer.shipping_address_line1,
                "shipping_city": customer.shipping_city,
                "shipping_state": customer.shipping_state,
                "shipping_zip": customer.shipping_zip,
                "order_count": order_stats.order_count or 0,
                "total_spent": float(order_stats.total_spent or 0),
                "last_order_date": order_stats.last_order,
                "created_at": customer.created_at,
            }
        )

    return result


@router.get("/search", response_model=List[CustomerSearchResult])
async def search_customers(
    q: str = Query(..., min_length=1, description="Search term"),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
):
    """
    Quick search for customer dropdown/autocomplete.

    Returns lightweight results for fast UI.
    """
    search_term = f"%{q}%"
    customers = (
        db.query(User)
        .filter(
            User.account_type == "customer",
            User.status == "active",
            (User.email.ilike(search_term))
            | (User.first_name.ilike(search_term))
            | (User.last_name.ilike(search_term))
            | (User.company_name.ilike(search_term))
            | (User.customer_number.ilike(search_term)),
        )
        .order_by(User.last_name, User.first_name)
        .limit(limit)
        .all()
    )

    result = []
    for c in customers:
        full_name = None
        if c.first_name and c.last_name:
            full_name = f"{c.first_name} {c.last_name}"
        elif c.first_name:
            full_name = c.first_name
        elif c.last_name:
            full_name = c.last_name

        result.append(
            {
                "id": c.id,
                "customer_number": c.customer_number,
                "email": c.email,
                "full_name": full_name,
                "company_name": c.company_name,
            }
        )

    return result


# ============================================================================
# GET & CREATE ENDPOINTS
# ============================================================================


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get a single customer with full details.

    Admin only.
    """
    customer = db.query(User).filter(User.id == customer_id, User.account_type == "customer").first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    # Get stats
    order_count = (
        db.query(func.count(SalesOrder.id))
        .filter(SalesOrder.user_id == customer_id, SalesOrder.status != "cancelled")
        .scalar()
        or 0
    )

    quote_count = db.query(func.count(Quote.id)).filter(Quote.user_id == customer_id).scalar() or 0

    total_spent = (
        db.query(func.sum(SalesOrder.grand_total))
        .filter(SalesOrder.user_id == customer_id, SalesOrder.status != "cancelled")
        .scalar()
        or 0
    )

    return {
        "id": customer.id,
        "customer_number": customer.customer_number,
        "email": customer.email,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "company_name": customer.company_name,
        "phone": customer.phone,
        "status": customer.status,
        "email_verified": customer.email_verified,
        "billing_address_line1": customer.billing_address_line1,
        "billing_address_line2": customer.billing_address_line2,
        "billing_city": customer.billing_city,
        "billing_state": customer.billing_state,
        "billing_zip": customer.billing_zip,
        "billing_country": customer.billing_country,
        "shipping_address_line1": customer.shipping_address_line1,
        "shipping_address_line2": customer.shipping_address_line2,
        "shipping_city": customer.shipping_city,
        "shipping_state": customer.shipping_state,
        "shipping_zip": customer.shipping_zip,
        "shipping_country": customer.shipping_country,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "last_login_at": customer.last_login_at,
        "order_count": order_count,
        "quote_count": quote_count,
        "total_spent": float(total_spent),
    }


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    request: CustomerCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create a new customer.

    Admin only. Creates user with account_type='customer'.
    """
    # Check for existing email
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Generate customer number
    customer_number = generate_customer_number(db)

    # Use random unusable password - portal login is a Pro feature
    # In open source, customers are CRM records only (no login capability)
    password_hashed = hash_password(secrets.token_urlsafe(32))

    # Set timestamps explicitly
    now = datetime.now(timezone.utc)

    customer = User(
        customer_number=customer_number,
        email=request.email,
        password_hash=password_hashed,
        first_name=request.first_name,
        last_name=request.last_name,
        company_name=request.company_name,
        phone=request.phone,
        status=request.status or "active",
        account_type="customer",
        email_verified=False,
        billing_address_line1=request.billing_address_line1,
        billing_address_line2=request.billing_address_line2,
        billing_city=request.billing_city,
        billing_state=request.billing_state,
        billing_zip=request.billing_zip,
        billing_country=request.billing_country or "USA",
        shipping_address_line1=request.shipping_address_line1,
        shipping_address_line2=request.shipping_address_line2,
        shipping_city=request.shipping_city,
        shipping_state=request.shipping_state,
        shipping_zip=request.shipping_zip,
        shipping_country=request.shipping_country or "USA",
        created_by=current_admin.id,
        created_at=now,
        updated_at=now,
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    logger.info(
        "Customer created",
        extra={
            "customer_number": customer_number,
            "customer_id": customer.id,
            "admin_id": current_admin.id,
            "admin_email": current_admin.email,
        },
    )

    return {
        "id": customer.id,
        "customer_number": customer.customer_number,
        "email": customer.email,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "company_name": customer.company_name,
        "phone": customer.phone,
        "status": customer.status,
        "email_verified": customer.email_verified,
        "billing_address_line1": customer.billing_address_line1,
        "billing_address_line2": customer.billing_address_line2,
        "billing_city": customer.billing_city,
        "billing_state": customer.billing_state,
        "billing_zip": customer.billing_zip,
        "billing_country": customer.billing_country,
        "shipping_address_line1": customer.shipping_address_line1,
        "shipping_address_line2": customer.shipping_address_line2,
        "shipping_city": customer.shipping_city,
        "shipping_state": customer.shipping_state,
        "shipping_zip": customer.shipping_zip,
        "shipping_country": customer.shipping_country,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "last_login_at": customer.last_login_at,
        "order_count": 0,
        "quote_count": 0,
        "total_spent": 0.0,
    }


# ============================================================================
# UPDATE & DELETE ENDPOINTS
# ============================================================================


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    request: CustomerUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Update a customer.

    Admin only. Partial update supported.
    """
    customer = db.query(User).filter(User.id == customer_id, User.account_type == "customer").first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    # Check for duplicate email if changing
    if request.email and request.email != customer.email:
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(customer, field, value)

    customer.updated_by = current_admin.id
    db.commit()
    db.refresh(customer)

    logger.info(
        "Customer updated",
        extra={
            "customer_number": customer.customer_number,
            "customer_id": customer.id,
            "admin_id": current_admin.id,
            "admin_email": current_admin.email,
        },
    )

    # Get stats for response
    order_count = (
        db.query(func.count(SalesOrder.id))
        .filter(SalesOrder.user_id == customer_id, SalesOrder.status != "cancelled")
        .scalar()
        or 0
    )

    quote_count = db.query(func.count(Quote.id)).filter(Quote.user_id == customer_id).scalar() or 0

    total_spent = (
        db.query(func.sum(SalesOrder.grand_total))
        .filter(SalesOrder.user_id == customer_id, SalesOrder.status != "cancelled")
        .scalar()
        or 0
    )

    return {
        "id": customer.id,
        "customer_number": customer.customer_number,
        "email": customer.email,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "company_name": customer.company_name,
        "phone": customer.phone,
        "status": customer.status,
        "email_verified": customer.email_verified,
        "billing_address_line1": customer.billing_address_line1,
        "billing_address_line2": customer.billing_address_line2,
        "billing_city": customer.billing_city,
        "billing_state": customer.billing_state,
        "billing_zip": customer.billing_zip,
        "billing_country": customer.billing_country,
        "shipping_address_line1": customer.shipping_address_line1,
        "shipping_address_line2": customer.shipping_address_line2,
        "shipping_city": customer.shipping_city,
        "shipping_state": customer.shipping_state,
        "shipping_zip": customer.shipping_zip,
        "shipping_country": customer.shipping_country,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "last_login_at": customer.last_login_at,
        "order_count": order_count,
        "quote_count": quote_count,
        "total_spent": float(total_spent),
    }


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Delete a customer (soft delete by setting status to 'deleted').

    Admin only. Customers with orders cannot be fully deleted.
    """
    customer = db.query(User).filter(User.id == customer_id, User.account_type == "customer").first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    # Check for orders
    order_count = db.query(func.count(SalesOrder.id)).filter(SalesOrder.user_id == customer_id).scalar() or 0

    if order_count > 0:
        # Soft delete - set status to inactive
        customer.status = "inactive"
        db.commit()
        logger.info(
            "Customer deactivated",
            extra={
                "customer_number": customer.customer_number,
                "customer_id": customer.id,
                "admin_id": current_admin.id,
                "admin_email": current_admin.email,
                "order_count": order_count,
            },
        )
    else:
        # Hard delete - no orders
        db.delete(customer)
        db.commit()
        logger.info(
            "Customer deleted",
            extra={
                "customer_number": customer.customer_number,
                "customer_id": customer_id,
                "admin_id": current_admin.id,
                "admin_email": current_admin.email,
            },
        )

    return None


# ============================================================================
# CUSTOMER ORDERS
# ============================================================================


@router.get("/{customer_id}/orders")
async def get_customer_orders(
    customer_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get recent orders for a customer.

    Admin only.
    """
    customer = db.query(User).filter(User.id == customer_id, User.account_type == "customer").first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    orders = (
        db.query(SalesOrder)
        .filter(SalesOrder.user_id == customer_id)
        .order_by(desc(SalesOrder.created_at))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status,
            "grand_total": float(o.grand_total or 0),
            "payment_status": o.payment_status,
            "created_at": o.created_at,
        }
        for o in orders
    ]


# ============================================================================
# CSV IMPORT
# ============================================================================


# Column mapping for common e-commerce platforms
# Maps various column names to our standard field names
COLUMN_MAPPINGS = {
    # Email variations
    "email": "email",
    "e-mail": "email",
    "email_address": "email",
    "billing_email": "email",
    "billing email": "email",
    "customer_email": "email",
    "buyer_email": "email",  # TikTok Shop, Etsy
    "buyer email": "email",
    "customer email": "email",
    # First name variations
    "first_name": "first_name",
    "firstname": "first_name",
    "first name": "first_name",
    "billing_first_name": "first_name",
    "billing first name": "first_name",
    "contact_first_name": "first_name",
    "ship_name": "first_name",  # Etsy uses combined name in ship_name
    "shipping name": "first_name",  # Squarespace uses "Shipping Name"
    "shipping_name": "first_name",
    "billing name": "first_name",  # Squarespace billing name
    "billing_name": "first_name",
    "buyer_name": "first_name",  # TikTok Shop, Etsy
    "buyer name": "first_name",
    "customer_name": "first_name",  # TikTok Shop
    "customer name": "first_name",
    # Last name variations
    "last_name": "last_name",
    "lastname": "last_name",
    "last name": "last_name",
    "billing_last_name": "last_name",
    "billing last name": "last_name",
    "contact_last_name": "last_name",
    # Shopify uses Last Name (capital L, N)
    "Last Name": "last_name",
    "LastName": "last_name",
    # Company variations
    "company_name": "company_name",
    "company": "company_name",
    "billing_company": "company_name",
    "billing company": "company_name",
    # Phone variations
    "phone": "phone",
    "telephone": "phone",
    "phone_number": "phone",
    "billing_phone": "phone",
    "billing phone": "phone",
    # Billing address line 1
    "billing_address_line1": "billing_address_line1",
    "billing_address_1": "billing_address_line1",
    "billing address 1": "billing_address_line1",
    "billing_address1": "billing_address_line1",
    "billingaddress1": "billing_address_line1",
    "address1": "billing_address_line1",
    "address_1": "billing_address_line1",
    "address 1": "billing_address_line1",
    "street_address": "billing_address_line1",
    "street": "billing_address_line1",
    # Billing address line 2
    "billing_address_line2": "billing_address_line2",
    "billing_address_2": "billing_address_line2",
    "billing address 2": "billing_address_line2",
    "billing_address2": "billing_address_line2",
    "billingaddress2": "billing_address_line2",
    "address2": "billing_address_line2",
    "address_2": "billing_address_line2",
    "address 2": "billing_address_line2",
    # Billing city
    "billing_city": "billing_city",
    "billing city": "billing_city",
    "city": "billing_city",
    # Shopify uses City (capital C)
    "City": "billing_city",
    # Billing state/province
    "billing_state": "billing_state",
    "billing state": "billing_state",
    "billing_province": "billing_state",
    "billing province": "billing_state",
    "province": "billing_state",
    "state": "billing_state",
    "province_code": "billing_state",
    # Shopify uses Province or Province Code
    "Province": "billing_state",
    "Province Code": "billing_state",
    "ProvinceCode": "billing_state",
    # Billing zip/postal
    "billing_zip": "billing_zip",
    "billing zip": "billing_zip",
    "billing_postcode": "billing_zip",
    "billing postcode": "billing_zip",
    "billing_postal_code": "billing_zip",
    "zip": "billing_zip",
    "postcode": "billing_zip",
    "postal_code": "billing_zip",
    # Shopify uses Zip or Postal Code
    "Zip": "billing_zip",
    "Postal Code": "billing_zip",
    "PostalCode": "billing_zip",
    # Billing country
    "billing_country": "billing_country",
    "billing country": "billing_country",
    "country": "billing_country",
    "country_code": "billing_country",
    # Shopify uses Country or Country Code
    "Country": "billing_country",
    "Country Code": "billing_country",
    "CountryCode": "billing_country",
    # Shipping address line 1
    "shipping_address_line1": "shipping_address_line1",
    "shipping_address_1": "shipping_address_line1",
    "shipping address 1": "shipping_address_line1",
    "shipping_address1": "shipping_address_line1",
    "shippingaddress1": "shipping_address_line1",
    "ship_address1": "shipping_address_line1",
    "ship address1": "shipping_address_line1",
    "shipping address": "shipping_address_line1",  # TikTok Shop (combined address)
    "shipping_address": "shipping_address_line1",
    "ship_to_address": "shipping_address_line1",  # Amazon Business
    "ship to address": "shipping_address_line1",
    # Shipping address line 2
    "shipping_address_line2": "shipping_address_line2",
    "shipping_address_2": "shipping_address_line2",
    "shipping address 2": "shipping_address_line2",
    "shipping_address2": "shipping_address_line2",
    "shippingaddress2": "shipping_address_line2",
    "ship_address2": "shipping_address_line2",
    # Shipping city
    "shipping_city": "shipping_city",
    "shipping city": "shipping_city",
    "ship_city": "shipping_city",
    "ship_to_city": "shipping_city",  # Amazon Business
    "ship to city": "shipping_city",
    # Shipping state/province
    "shipping_state": "shipping_state",
    "shipping state": "shipping_state",
    "shipping_province": "shipping_state",
    "shipping province": "shipping_state",
    "ship_state": "shipping_state",
    "ship_to_state": "shipping_state",  # Amazon Business
    "ship to state": "shipping_state",
    "ship_to_province": "shipping_state",
    "ship to province": "shipping_state",
    # Shipping zip/postal
    "shipping_zip": "shipping_zip",
    "shipping zip": "shipping_zip",
    "shipping_postcode": "shipping_zip",
    "shipping postcode": "shipping_zip",
    "ship_zip": "shipping_zip",
    "ship_zipcode": "shipping_zip",
    "ship_to_zip": "shipping_zip",  # Amazon Business
    "ship to zip": "shipping_zip",
    "ship_to_postcode": "shipping_zip",
    "ship to postcode": "shipping_zip",
    # Shipping country
    "shipping_country": "shipping_country",
    "shipping country": "shipping_country",
    "ship_country": "shipping_country",
    "ship_to_country": "shipping_country",  # Amazon Business
    "ship to country": "shipping_country",
}


def normalize_column_name(col: str) -> str:
    """Normalize a column name to our standard field name."""
    # Clean up the column name
    normalized = col.strip().lower().replace(" ", "_").replace("-", "_")
    # Look up in mappings
    return COLUMN_MAPPINGS.get(normalized, normalized)


def map_row_to_fields(row: dict) -> dict:
    """Map a CSV row with various column names to our standard fields."""
    result = {
        "email": "",
        "first_name": "",
        "last_name": "",
        "company_name": "",
        "phone": "",
        "billing_address_line1": "",
        "billing_address_line2": "",
        "billing_city": "",
        "billing_state": "",
        "billing_zip": "",
        "billing_country": "USA",
        "shipping_address_line1": "",
        "shipping_address_line2": "",
        "shipping_city": "",
        "shipping_state": "",
        "shipping_zip": "",
        "shipping_country": "USA",
    }

    for original_col, value in row.items():
        if not value:
            continue
        value = value.strip()
        if not value:
            continue

        # Normalize the column name
        field_name = normalize_column_name(original_col)

        # Only set if it's a recognized field
        if field_name in result:
            # Don't overwrite with empty or with duplicate mappings
            if not result[field_name] or result[field_name] == "USA":
                result[field_name] = value

    # Handle combined name fields (like Etsy's "Buyer Name" or "Ship Name")
    # If we have no first/last name but have a combined name field
    if not result["first_name"] and not result["last_name"]:
        for col, value in row.items():
            col_lower = col.strip().lower()
            if col_lower in (
                "name",
                "full_name",
                "fullname",
                "buyer_name",
                "buyer name",
                "customer_name",
                "customer name",
                "contact_name",
                "contact name",
            ):
                if value and value.strip():
                    parts = value.strip().split(" ", 1)
                    result["first_name"] = parts[0]
                    if len(parts) > 1:
                        result["last_name"] = parts[1]
                    break

    # Copy billing to shipping if shipping is empty (common pattern)
    if not result["shipping_address_line1"] and result["billing_address_line1"]:
        result["shipping_address_line1"] = result["billing_address_line1"]
        result["shipping_address_line2"] = result["billing_address_line2"]
        result["shipping_city"] = result["billing_city"]
        result["shipping_state"] = result["billing_state"]
        result["shipping_zip"] = result["billing_zip"]
        result["shipping_country"] = result["billing_country"] or "USA"

    # Default countries
    if not result["billing_country"]:
        result["billing_country"] = "USA"
    if not result["shipping_country"]:
        result["shipping_country"] = "USA"

    return result


@router.get("/import/template")
async def download_customer_template(
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Download a CSV template for customer import.
    """
    headers = [
        "email",
        "first_name",
        "last_name",
        "company_name",
        "phone",
        "billing_address_line1",
        "billing_address_line2",
        "billing_city",
        "billing_state",
        "billing_zip",
        "billing_country",
        "shipping_address_line1",
        "shipping_address_line2",
        "shipping_city",
        "shipping_state",
        "shipping_zip",
        "shipping_country",
    ]

    # Example row
    example = [
        "john@example.com",
        "John",
        "Smith",
        "Acme Corp",
        "555-123-4567",
        "123 Main St",
        "Suite 100",
        "Springfield",
        "IL",
        "62701",
        "USA",
        "123 Main St",
        "Suite 100",
        "Springfield",
        "IL",
        "62701",
        "USA",
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(example)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customer_import_template.csv"},
    )


@router.post("/import/preview")
async def preview_customer_import(
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Preview CSV import - validates data and returns parsed rows with errors.

    Supports exports from:
    - Shopify (First Name, Last Name, Email, Company, Address1, etc.)
    - WooCommerce (Billing First Name, Billing Email, Billing Address 1, etc.)
    - Squarespace (contacts export)
    - Etsy (order exports with Buyer Name, Ship Address, etc.)
    - TikTok Shop (order exports with Buyer Email, Buyer Name, etc.)
    - Generic CSV with common column names
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    # Try to detect and handle BOM (byte order mark)
    if text.startswith("\ufeff"):
        text = text[1:]

    reader = csv.DictReader(io.StringIO(text))

    # Detect format from headers
    headers = reader.fieldnames or []
    detected_format = "Unknown"
    headers_lower = [h.lower().strip() for h in headers]

    if any("billing" in h and "first" in h for h in headers_lower):
        detected_format = "WooCommerce"
    elif any(h in ("first name", "last name") for h in headers_lower) and "company" in headers_lower:
        detected_format = "Shopify"
    elif any("ship_" in h or ("buyer" in h and "name" in h) for h in headers_lower):
        detected_format = "Etsy/TikTok Shop"
    elif any("unit_price" in h or "cost_price" in h for h in headers_lower):
        detected_format = "TikTok Shop"
    elif "email" in headers_lower:
        detected_format = "Generic/Squarespace"

    rows = []
    existing_emails = set(e[0].lower() for e in db.query(User.email).filter(User.account_type == "customer").all())
    seen_emails = set()

    for i, raw_row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        row_errors = []

        # Use smart mapping to normalize columns
        mapped_data = map_row_to_fields(raw_row)

        # Required field: email
        email = mapped_data.get("email", "").lower().strip()
        if not email:
            row_errors.append("Email is required")
        elif "@" not in email:
            row_errors.append("Invalid email format")
        elif email in existing_emails:
            row_errors.append("Email already exists in database")
        elif email in seen_emails:
            row_errors.append("Duplicate email in CSV")
        else:
            seen_emails.add(email)

        # Update email in mapped data
        mapped_data["email"] = email

        rows.append({"row_number": i, "data": mapped_data, "errors": row_errors, "valid": len(row_errors) == 0})

    valid_count = sum(1 for r in rows if r["valid"])
    error_count = len(rows) - valid_count

    return {
        "total_rows": len(rows),
        "valid_rows": valid_count,
        "error_rows": error_count,
        "detected_format": detected_format,
        "rows": rows[:100],  # Limit preview to first 100 rows
        "truncated": len(rows) > 100,
    }


@router.post("/import")
async def import_customers(
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Import customers from CSV file.

    Supports exports from Shopify, WooCommerce, Squarespace, Etsy, TikTok Shop, and generic CSV.
    Automatically maps common column names to our standard fields.

    Skips rows with errors (duplicate emails, missing required fields).
    Returns count of imported vs skipped.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    # Handle BOM
    if text.startswith("\ufeff"):
        text = text[1:]

    reader = csv.DictReader(io.StringIO(text))

    existing_emails = set(e[0].lower() for e in db.query(User.email).all())

    imported = 0
    skipped = 0
    errors = []

    for i, raw_row in enumerate(reader, start=2):
        # Use smart mapping to normalize columns
        mapped_data = map_row_to_fields(raw_row)

        email = mapped_data.get("email", "").lower().strip()

        # Skip invalid rows
        if not email or "@" not in email:
            skipped += 1
            errors.append({"row": i, "reason": "Invalid or missing email"})
            continue

        if email in existing_emails:
            skipped += 1
            errors.append({"row": i, "reason": f"Email {email} already exists"})
            continue

        # Generate customer number
        customer_number = generate_customer_number(db)

        # Create customer
        now = datetime.now(timezone.utc)
        customer = User(
            customer_number=customer_number,
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            first_name=mapped_data.get("first_name", "") or None,
            last_name=mapped_data.get("last_name", "") or None,
            company_name=mapped_data.get("company_name", "") or None,
            phone=mapped_data.get("phone", "") or None,
            status="active",
            account_type="customer",
            email_verified=False,
            billing_address_line1=mapped_data.get("billing_address_line1", "") or None,
            billing_address_line2=mapped_data.get("billing_address_line2", "") or None,
            billing_city=mapped_data.get("billing_city", "") or None,
            billing_state=mapped_data.get("billing_state", "") or None,
            billing_zip=mapped_data.get("billing_zip", "") or None,
            billing_country=mapped_data.get("billing_country", "") or "USA",
            shipping_address_line1=mapped_data.get("shipping_address_line1", "") or None,
            shipping_address_line2=mapped_data.get("shipping_address_line2", "") or None,
            shipping_city=mapped_data.get("shipping_city", "") or None,
            shipping_state=mapped_data.get("shipping_state", "") or None,
            shipping_zip=mapped_data.get("shipping_zip", "") or None,
            shipping_country=mapped_data.get("shipping_country", "") or "USA",
            created_by=current_admin.id,
            created_at=now,
            updated_at=now,
        )

        try:
            db.add(customer)
            db.flush()  # Flush to catch any database errors early
            existing_emails.add(email)  # Track to prevent duplicates within same import
            imported += 1
        except Exception as e:
            db.rollback()
            skipped += 1
            errors.append({"row": i, "reason": f"Database error: {str(e)}", "email": email})
            continue

    db.commit()

    logger.info(
        "Customer CSV import completed",
        extra={
            "admin_id": current_admin.id,
            "admin_email": current_admin.email,
            "imported": imported,
            "skipped": skipped,
        },
    )

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:20],  # Return first 20 errors
        "message": f"Successfully imported {imported} customers"
        + (f", skipped {skipped} rows with errors" if skipped else ""),
    }
