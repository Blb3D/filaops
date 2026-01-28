"""
Feature flags and tier information endpoints
"""

from typing import Dict, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.core.features import (
    get_current_tier,
    get_available_features,
    get_usage_summary,
    TIER_LIMITS,
    LICENSING_ENABLED,
    Tier,
)
from pydantic import BaseModel


router = APIRouter(prefix="/features", tags=["features"])


class ResourceUsage(BaseModel):
    allowed: bool
    limit: int
    current: int
    remaining: int
    upgrade_message: Optional[str] = None


class TierInfo(BaseModel):
    tier: str
    features: list[str]
    is_pro: bool
    is_enterprise: bool


class UsageSummary(BaseModel):
    tier: str
    licensing_enabled: bool
    resources: Dict[str, ResourceUsage]
    limits: Dict[str, int]


@router.get("/current", response_model=TierInfo)
async def get_current_tier_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's tier and available features"""
    tier = get_current_tier(db, current_user)
    features = get_available_features(tier)

    return TierInfo(
        tier=tier.value,
        features=features,
        is_pro=tier in (Tier.PRO, Tier.ENTERPRISE),
        is_enterprise=tier == Tier.ENTERPRISE,
    )


@router.get("/usage", response_model=UsageSummary)
async def get_usage_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get resource usage summary for current tier.

    Returns current usage vs limits for users, printers, etc.
    Useful for displaying in settings or dashboard.
    """
    tier = get_current_tier(db, current_user)
    usage = get_usage_summary(db, tier.value)

    # Get limits for current tier
    limits = TIER_LIMITS.get(tier.value, TIER_LIMITS["community"])

    return UsageSummary(
        tier=tier.value,
        licensing_enabled=LICENSING_ENABLED,
        resources=usage["resources"],
        limits=limits,
    )
