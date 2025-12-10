"""
Feature flag system for tier-based access control (Open/Pro/Enterprise)
"""
from enum import Enum
from functools import wraps
from typing import Optional, Callable, Any
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import get_db
from app.models.user import User
from app.api.v1.deps import get_current_user


class Tier(str, Enum):
    """Product tier levels"""
    OPEN = "open"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Tier hierarchy for comparison
TIER_LEVELS = {
    Tier.OPEN: 0,
    Tier.PRO: 1,
    Tier.ENTERPRISE: 2,
}


def get_current_tier(db: Session, user: Optional[User] = None) -> Tier:
    """
    Get the current tier for a user or system.
    
    Priority:
    1. User's license (from database - TODO: implement license table)
    2. Environment variable (for testing/self-hosted)
    3. Default to OPEN
    
    In Pro launch, this will check:
    - User subscription/license from database
    - Organization tier
    - Trial status
    """
    # TODO: Check user's license from database
    # For now, check environment variable for testing
    # In production, query licenses table:
    # license = db.query(License).filter(
    #     License.user_id == user.id,
    #     License.status == 'active',
    #     License.expires_at > datetime.utcnow()
    # ).first()
    # if license:
    #     return license.tier
    
    tier_str = getattr(settings, "TIER", "open").lower()
    return Tier(tier_str) if tier_str in [t.value for t in Tier] else Tier.OPEN


def tier_level(tier: Tier) -> int:
    """Get numeric level for tier comparison"""
    return TIER_LEVELS.get(tier, 0)


def require_tier(minimum_tier: Tier):
    """
    Decorator to gate endpoints by tier.
    
    Usage:
        @router.get("/quotes/generate")
        @require_tier(Tier.PRO)
        async def generate_quote(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
            *args,
            current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db),
            **kwargs
        ) -> Any:
            current_tier = get_current_tier(db, current_user)
            
            if tier_level(current_tier) < tier_level(minimum_tier):
                tier_names = {
                    Tier.PRO: "Pro",
                    Tier.ENTERPRISE: "Enterprise"
                }
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "TIER_REQUIRED",
                        "message": f"This feature requires {tier_names.get(minimum_tier, minimum_tier.value)} tier",
                        "current_tier": current_tier.value,
                        "required_tier": minimum_tier.value,
                        "upgrade_url": "https://filaops.com/pricing"
                    }
                )
            
            return await func(*args, current_user=current_user, db=db, **kwargs)
        return wrapper
    return decorator


# Feature availability helpers
def has_feature(tier: Tier, feature: str) -> bool:
    """Check if a tier has access to a specific feature"""
    feature_map = {
        "quote_portal": [Tier.PRO, Tier.ENTERPRISE],
        "b2b_portal": [Tier.PRO, Tier.ENTERPRISE],
        "integrations": [Tier.PRO, Tier.ENTERPRISE],
        "ml_time_estimation": [Tier.ENTERPRISE],
        "printer_fleet": [Tier.ENTERPRISE],
        "advanced_analytics": [Tier.ENTERPRISE],
        "accounting_module": [Tier.PRO, Tier.ENTERPRISE],
        "auto_scheduling": [Tier.PRO, Tier.ENTERPRISE],
    }
    return tier in feature_map.get(feature, [])


def get_available_features(tier: Tier) -> list[str]:
    """Get list of available features for a tier"""
    all_features = [
        "quote_portal", "b2b_portal", "integrations",
        "ml_time_estimation", "printer_fleet", "advanced_analytics",
        "accounting_module"
    ]
    return [f for f in all_features if has_feature(tier, f)]

