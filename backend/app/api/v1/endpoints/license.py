"""
License activation endpoints for Pro/Enterprise tiers

DISABLED: This module is implemented but disabled until ready for production.
To enable:
1. Uncomment the router include in app/api/v1/__init__.py
2. Uncomment License model import in app/models/__init__.py
3. Uncomment license routes in frontend App.jsx
4. Create licenses table in database (scripts/create_licenses_table.sql)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import hashlib

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_admin_user
from app.models.user import User

# License model is disabled - see note at top of file
# from app.models.license import License  # Disabled until ready
from app.core.features import Tier

# Type stub for License to avoid undefined name errors when feature is disabled
# This will be removed when license feature is enabled
try:
    from app.models.license import License
except ImportError:
    License = None  # type: ignore

router = APIRouter(prefix="/license", tags=["license"])


class LicenseActivateRequest(BaseModel):
    license_key: str


class LicenseInfo(BaseModel):
    tier: str
    license_key: Optional[str] = None
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_valid: bool


def validate_license_key(license_key: str) -> tuple[bool, Optional[Tier], Optional[str]]:
    """
    Validate a license key and return (is_valid, tier, error_message)

    For now, this is a simple validation. In production, this would:
    - Check against a license server
    - Validate with Stripe subscription
    - Check expiration dates
    - Verify signature

    Format for testing:
    - PRO-XXXX-XXXX-XXXX (Pro tier)
    - ENT-XXXX-XXXX-XXXX (Enterprise tier)
    """
    if not license_key:
        return False, None, "License key is required"

    license_key = license_key.strip().upper()

    # Simple format validation
    if license_key.startswith("PRO-"):
        # For testing: PRO-1234-5678-9012
        if len(license_key) == 19 and license_key.count("-") == 3:
            return True, Tier.PRO, None
        return False, None, "Invalid Pro license key format"

    elif license_key.startswith("ENT-"):
        # For testing: ENT-1234-5678-9012
        if len(license_key) == 19 and license_key.count("-") == 3:
            return True, Tier.ENTERPRISE, None
        return False, None, "Invalid Enterprise license key format"

    # Special test keys (for development)
    if license_key == "TEST-PRO":
        return True, Tier.PRO, None
    if license_key == "TEST-ENTERPRISE":
        return True, Tier.ENTERPRISE, None

    return False, None, "Invalid license key format. Expected PRO-XXXX-XXXX-XXXX or ENT-XXXX-XXXX-XXXX"


@router.post("/activate", response_model=LicenseInfo)
async def activate_license(
    request: LicenseActivateRequest, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)
):
    """
    Activate a license key for Pro or Enterprise tier

    For testing, use:
    - PRO-1234-5678-9012 (Pro tier)
    - ENT-1234-5678-9012 (Enterprise tier)
    - TEST-PRO (Pro tier, development only)
    - TEST-ENTERPRISE (Enterprise tier, development only)
    """
    is_valid, tier, error_msg = validate_license_key(request.license_key)

    if not is_valid or tier is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg or "Invalid license key")

    # Hash the license key for storage
    license_key_hash = hashlib.sha256(request.license_key.encode()).hexdigest()
    tier_value = tier.value

    # Check if user already has an active license
    existing_license = (
        db.query(License)
        .filter(and_(License.user_id == current_user.id, License.status == "active", License.tier == tier_value))
        .first()
    )

    if existing_license:
        # Check if it's the same license key
        if existing_license.license_key_hash == license_key_hash:
            activated = existing_license.activated_at
            expires = existing_license.expires_at
            return LicenseInfo(
                tier=tier_value,
                license_key=request.license_key[:8] + "****" if len(request.license_key) > 8 else "****",
                activated_at=activated,
                expires_at=expires,
                is_valid=True,
            )
        else:
            # Revoke old license
            existing_license.status = "revoked"  # type: ignore
            existing_license.revoked_at = datetime.now(timezone.utc)  # type: ignore

    # Create new license
    now = datetime.now(timezone.utc)
    license = License(
        user_id=current_user.id,
        license_key_hash=license_key_hash,
        tier=tier_value,
        status="active",
        activated_at=now,
        expires_at=None,  # Would be set based on subscription
        created_at=now,
        updated_at=now,
    )

    db.add(license)
    db.commit()
    db.refresh(license)

    activated = license.activated_at
    expires = license.expires_at

    return LicenseInfo(
        tier=tier_value,
        license_key=request.license_key[:8] + "****" if len(request.license_key) > 8 else "****",
        activated_at=activated,
        expires_at=expires,
        is_valid=True,
    )


@router.get("/info", response_model=LicenseInfo)
async def get_license_info(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Get current license information"""
    # Disabled - just return tier from environment variable
    from app.core.features import get_current_tier

    tier = get_current_tier(db, current_user)

    return LicenseInfo(
        tier=tier.value, license_key=None, activated_at=None, expires_at=None, is_valid=tier != Tier.OPEN
    )

    # Disabled code below - uncomment when ready
    # # Check database for user's active license
    # active_license = db.query(License).filter(
    #     and_(
    #         License.user_id == current_user.id,
    #         License.status == 'active'
    #     )
    # ).order_by(License.activated_at.desc()).first()
    #
    # if active_license and active_license.is_active:
    #     activated = active_license.activated_at
    #     expires = active_license.expires_at
    #     return LicenseInfo(
    #         tier=str(active_license.tier),
    #         license_key=None,  # Never return full key
    #         activated_at=activated,
    #         expires_at=expires,
    #         is_valid=True
    #     )


@router.post("/deactivate")
async def deactivate_license(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Deactivate current license (revert to open tier)"""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="License management is not yet available. Coming in 2026!",
    )

    # Disabled code below - uncomment when ready
    # # Find and revoke user's active licenses
    # active_licenses = db.query(License).filter(
    #     and_(
    #         License.user_id == current_user.id,
    #         License.status == 'active'
    #     )
    # ).all()
    #
    # now = datetime.now(timezone.utc)
    # for lic in active_licenses:
    #     lic.status = 'revoked'  # type: ignore
    #     lic.revoked_at = now  # type: ignore
    #     lic.updated_at = now  # type: ignore
    #
    # db.commit()
    #
    # return {"message": "License deactivated", "tier": "open"}
