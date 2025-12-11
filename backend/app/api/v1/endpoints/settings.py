"""
Company Settings API Endpoints

Manage company-wide settings including:
- Company info (name, address, contact)
- Logo upload
- Tax configuration
- Quote settings
"""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models.user import User
from app.models.company_settings import CompanySettings
from app.api.v1.endpoints.auth import get_current_user
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])


# ============================================================================
# SCHEMAS
# ============================================================================

class CompanySettingsResponse(BaseModel):
    """Company settings response"""
    id: int
    company_name: Optional[str] = None
    company_address_line1: Optional[str] = None
    company_address_line2: Optional[str] = None
    company_city: Optional[str] = None
    company_state: Optional[str] = None
    company_zip: Optional[str] = None
    company_country: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    company_website: Optional[str] = None

    # Logo info (not the data itself)
    has_logo: bool = False
    logo_filename: Optional[str] = None

    # Tax
    tax_enabled: bool = False
    tax_rate: Optional[Decimal] = None
    tax_rate_percent: Optional[float] = None  # For display (e.g., 8.25)
    tax_name: Optional[str] = None
    tax_registration_number: Optional[str] = None

    # Quote settings
    default_quote_validity_days: int = 30
    quote_terms: Optional[str] = None
    quote_footer: Optional[str] = None

    updated_at: datetime

    model_config = {"from_attributes": True}


class CompanySettingsUpdate(BaseModel):
    """Update company settings"""
    company_name: Optional[str] = Field(None, max_length=255)
    company_address_line1: Optional[str] = Field(None, max_length=255)
    company_address_line2: Optional[str] = Field(None, max_length=255)
    company_city: Optional[str] = Field(None, max_length=100)
    company_state: Optional[str] = Field(None, max_length=50)
    company_zip: Optional[str] = Field(None, max_length=20)
    company_country: Optional[str] = Field(None, max_length=100)
    company_phone: Optional[str] = Field(None, max_length=30)
    company_email: Optional[str] = Field(None, max_length=255)
    company_website: Optional[str] = Field(None, max_length=255)

    # Tax (rate as percent, e.g., 8.25 for 8.25%)
    tax_enabled: Optional[bool] = None
    tax_rate_percent: Optional[float] = Field(None, ge=0, le=100)
    tax_name: Optional[str] = Field(None, max_length=50)
    tax_registration_number: Optional[str] = Field(None, max_length=100)

    # Quote settings
    default_quote_validity_days: Optional[int] = Field(None, ge=1, le=365)
    quote_terms: Optional[str] = Field(None, max_length=2000)
    quote_footer: Optional[str] = Field(None, max_length=1000)


# ============================================================================
# HELPER: Get or Create Settings
# ============================================================================

def get_or_create_settings(db: Session) -> CompanySettings:
    """
    Retrieve the singleton company settings row, creating and persisting a default record if none exists.
    
    If a settings row with id=1 is missing, a new CompanySettings with id=1 is created, committed to the database, and refreshed before being returned.
    
    Returns:
        CompanySettings: The settings instance for id 1 (existing or newly created and persisted).
    """
    settings = db.query(CompanySettings).filter(CompanySettings.id == 1).first()
    if not settings:
        settings = CompanySettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def settings_to_response(settings: CompanySettings) -> CompanySettingsResponse:
    """
    Build a CompanySettingsResponse from a CompanySettings ORM instance, computing derived fields.
    
    Parameters:
        settings (CompanySettings): ORM instance containing stored company settings.
    
    Returns:
        CompanySettingsResponse: Response model with fields copied from `settings`. The `tax_rate_percent`
        field is `float(settings.tax_rate) * 100` when `settings.tax_rate` is set, otherwise `None`.
        The `has_logo` field is `True` when `settings.logo_data` is not `None`, otherwise `False`.
    """
    tax_rate_percent = None
    if settings.tax_rate is not None:
        tax_rate_percent = float(settings.tax_rate) * 100

    return CompanySettingsResponse(
        id=settings.id,
        company_name=settings.company_name,
        company_address_line1=settings.company_address_line1,
        company_address_line2=settings.company_address_line2,
        company_city=settings.company_city,
        company_state=settings.company_state,
        company_zip=settings.company_zip,
        company_country=settings.company_country,
        company_phone=settings.company_phone,
        company_email=settings.company_email,
        company_website=settings.company_website,
        has_logo=settings.logo_data is not None,
        logo_filename=settings.logo_filename,
        tax_enabled=settings.tax_enabled,
        tax_rate=settings.tax_rate,
        tax_rate_percent=tax_rate_percent,
        tax_name=settings.tax_name,
        tax_registration_number=settings.tax_registration_number,
        default_quote_validity_days=settings.default_quote_validity_days,
        quote_terms=settings.quote_terms,
        quote_footer=settings.quote_footer,
        updated_at=settings.updated_at,
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/company", response_model=CompanySettingsResponse)
async def get_company_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the current company settings, creating a default settings row if none exists.
    
    Returns:
        CompanySettingsResponse: The company settings payload, including computed fields (e.g., `tax_rate_percent`) and logo metadata.
    """
    settings = get_or_create_settings(db)
    return settings_to_response(settings)


@router.patch("/company", response_model=CompanySettingsResponse)
async def update_company_settings(
    data: CompanySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update persisted company settings with the provided values.
    
    Only fields present in `data` are applied; unset fields are left unchanged. If `tax_rate_percent` is included, it is converted from a percentage (e.g., 20.0) to a fractional `Decimal` (e.g., Decimal('0.20')) and stored as `tax_rate`; if `tax_rate_percent` is present with value `None`, `tax_rate` is cleared. The settings' `updated_at` timestamp is set to the current UTC time before persisting.
    
    Parameters:
        data (CompanySettingsUpdate): Partial settings to apply; only provided fields are updated.
    
    Returns:
        CompanySettingsResponse: The updated company settings.
    
    Raises:
        HTTPException: With status 403 if the current user is not an administrator.
    """
    # Require admin role
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )

    settings = get_or_create_settings(db)

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # Handle tax_rate_percent -> tax_rate conversion
    if "tax_rate_percent" in update_data:
        percent = update_data.pop("tax_rate_percent")
        if percent is not None:
            settings.tax_rate = Decimal(str(percent / 100))
        else:
            settings.tax_rate = None

    for field, value in update_data.items():
        setattr(settings, field, value)

    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)

    logger.info(f"Company settings updated by {current_user.email}")
    return settings_to_response(settings)


@router.post("/company/logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload and store the company logo image, replacing any existing logo.
    
    Validates the caller has admin privileges, enforces an allowed image MIME type (PNG, JPEG, JPG, GIF, WebP), and enforces a maximum file size of 2 MB before saving the file bytes, filename, and MIME type to the company settings.
    
    Parameters:
        file (UploadFile): Uploaded image file. Allowed MIME types: "image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp". Maximum size: 2 MB.
    
    Returns:
        dict: {"message": "Logo uploaded successfully", "filename": <original filename>} on success.
    
    Raises:
        HTTPException: 403 if the current user is not an admin.
        HTTPException: 400 if the file MIME type is not allowed.
        HTTPException: 400 if the file size exceeds 2 MB.
    """
    # Require admin role
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )

    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PNG, JPEG, GIF, WebP"
        )

    # Limit file size (2MB)
    max_size = 2 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size: 2MB"
        )

    settings = get_or_create_settings(db)
    settings.logo_data = content
    settings.logo_filename = file.filename
    settings.logo_mime_type = file.content_type
    settings.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"Company logo uploaded by {current_user.email}")
    return {"message": "Logo uploaded successfully", "filename": file.filename}


@router.get("/company/logo")
async def get_company_logo(
    db: Session = Depends(get_db),
):
    """
    Retrieve the stored company logo image for public access (used by PDF generation).
    
    Returns:
        Response: HTTP response containing the image bytes with the correct MIME type and an inline Content-Disposition header using the stored filename (defaults to "logo.png").
    
    Raises:
        HTTPException: 404 if no company settings exist or no logo has been uploaded.
    """
    settings = db.query(CompanySettings).filter(CompanySettings.id == 1).first()

    if not settings or not settings.logo_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logo uploaded"
        )

    return Response(
        content=settings.logo_data,
        media_type=settings.logo_mime_type or "image/png",
        headers={
            "Content-Disposition": f'inline; filename="{settings.logo_filename or "logo.png"}"'
        }
    )


@router.delete("/company/logo")
async def delete_company_logo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove the stored company logo and its associated filename and MIME type from the company settings.
    
    This action requires an admin user; it clears the logo bytes and metadata, updates the settings' updated_at timestamp, and persists the change to the database.
    
    Returns:
        result (dict): Confirmation message with key "message" set to "Logo deleted".
    
    Raises:
        HTTPException: With status 403 if the current user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )

    settings = get_or_create_settings(db)
    settings.logo_data = None
    settings.logo_filename = None
    settings.logo_mime_type = None
    settings.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"Company logo deleted by {current_user.email}")
    return {"message": "Logo deleted"}