"""
License Key Management for FilaOps

Generates and validates JWT-based license keys.
Keys are self-contained (no phone-home required).

License Key Format:
FILAOPS-{TIER}-{token_part1}-{token_part2}-{token_part3}

Example:
FILAOPS-PRO-a1b2c3d4-e5f6g7h8-i9j0k1l2
"""

import jwt
from datetime import datetime
from typing import Optional, Dict
from app.core.features import get_features_for_tier, LICENSING_ENABLED

# ============================================================================
# IMPORTANT: Change this to a random secret in production!
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
# ============================================================================
LICENSE_SIGNING_KEY = "filaops-license-secret-change-this-in-production"


class LicenseException(Exception):
    """Base exception for license errors"""

    pass


class LicenseExpiredException(LicenseException):
    """Raised when license has expired"""

    pass


class InvalidLicenseException(LicenseException):
    """Raised when license is invalid or tampered"""

    pass


# ============================================================================
# License Generation (For you to use when selling licenses)
# ============================================================================


def generate_license_key(
    customer_email: str,
    tier: str,
    expires_at: Optional[datetime] = None,
    max_users: int = 999,
    organization_name: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Generate a signed JWT license key.

    Args:
        customer_email: Customer's email address
        tier: Subscription tier (community, professional, enterprise)
        expires_at: Expiration date (None = perpetual)
        max_users: Maximum number of users allowed
        organization_name: Organization name
        notes: Internal notes (not included in key)

    Returns:
        Formatted license key string

    Example:
        key = generate_license_key(
            customer_email="alice@example.com",
            tier="professional",
            expires_at=datetime.now() + timedelta(days=365),
            max_users=10,
            organization_name="Acme Corp"
        )
        # Returns: FILAOPS-PRO-abc12345-xyz67890-def09876
    """
    tier_lower = tier.lower()

    payload = {
        "email": customer_email,
        "tier": tier_lower,
        "issued_at": datetime.utcnow().isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "max_users": max_users,
        "org_name": organization_name,
        "features": get_features_for_tier(tier_lower),
        "version": "1.0",
    }

    # Sign with JWT
    token = jwt.encode(payload, LICENSE_SIGNING_KEY, algorithm="HS256")

    # Format nicely: FILAOPS-{TIER}-{part1}-{part2}-{part3}
    tier_prefix = {
        "community": "COM",
        "professional": "PRO",
        "enterprise": "ENT",
    }.get(tier_lower, "COM")

    # Split token into chunks for readability
    chunks = [token[i : i + 8] for i in range(0, min(len(token), 24), 8)]
    formatted = f"FILAOPS-{tier_prefix}-{'-'.join(chunks[:3])}"

    return formatted


# ============================================================================
# License Validation
# ============================================================================


def validate_license_key(license_key: str) -> Dict:
    """
    Validate and decode a license key.

    Args:
        license_key: License key string

    Returns:
        Dict with license info:
        {
            "valid": True,
            "tier": "professional",
            "email": "alice@example.com",
            "features": [...],
            "expires_at": "2026-12-31",
            "max_users": 10,
            "org_name": "Acme Corp",
            "days_remaining": 365
        }

    Raises:
        InvalidLicenseException: If key is invalid
        LicenseExpiredException: If key has expired
    """
    # If licensing is disabled, return a fake "unlimited" license
    if not LICENSING_ENABLED:
        return {
            "valid": True,
            "tier": "enterprise",  # Everyone gets everything!
            "email": "community@filaops.com",
            "features": get_features_for_tier("enterprise"),
            "expires_at": None,
            "max_users": 999999,
            "org_name": "Community Edition",
            "days_remaining": None,
            "licensing_enabled": False,
        }

    try:
        # Remove formatting: FILAOPS-PRO-abc-xyz-def -> abcxyzdef
        if not license_key.startswith("FILAOPS-"):
            raise InvalidLicenseException("Invalid license key format")

        # Extract token part
        parts = license_key.split("-")
        if len(parts) < 4:
            raise InvalidLicenseException("Invalid license key format")

        # Rejoin token parts (skip FILAOPS and tier prefix)
        token = "".join(parts[2:])

        # Decode JWT
        payload = jwt.decode(token, LICENSE_SIGNING_KEY, algorithms=["HS256"])

        # Check expiration
        expires_at = payload.get("expires_at")
        days_remaining = None

        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at)
            if datetime.utcnow() > expires_dt:
                raise LicenseExpiredException(f"License expired on {expires_dt.strftime('%Y-%m-%d')}")
            days_remaining = (expires_dt - datetime.utcnow()).days

        return {
            "valid": True,
            "tier": payload["tier"],
            "email": payload["email"],
            "features": payload["features"],
            "expires_at": expires_at,
            "max_users": payload.get("max_users", 999),
            "org_name": payload.get("org_name"),
            "days_remaining": days_remaining,
            "issued_at": payload.get("issued_at"),
            "licensing_enabled": True,
        }

    except jwt.InvalidSignatureError:
        raise InvalidLicenseException("License key signature is invalid. Key may have been tampered with.")
    except jwt.DecodeError:
        raise InvalidLicenseException("License key format is invalid. Please check the key.")
    except jwt.ExpiredSignatureError:
        raise LicenseExpiredException("License has expired")
    except KeyError as e:
        raise InvalidLicenseException(f"License key is missing required field: {e}")


# ============================================================================
# Quick Validation Helpers
# ============================================================================


def is_license_valid(license_key: str) -> bool:
    """
    Quick check if license is valid (doesn't raise exceptions).

    Args:
        license_key: License key string

    Returns:
        True if valid, False otherwise
    """
    try:
        result = validate_license_key(license_key)
        return result["valid"]
    except (InvalidLicenseException, LicenseExpiredException):
        return False


def get_license_tier(license_key: str) -> str:
    """
    Get tier from license key (returns 'community' if invalid).

    Args:
        license_key: License key string

    Returns:
        Tier string (community, professional, enterprise)
    """
    try:
        result = validate_license_key(license_key)
        return result["tier"]
    except (InvalidLicenseException, LicenseExpiredException):
        return "community"


# ============================================================================
# License Info Formatting
# ============================================================================


def format_license_info(license_info: Dict) -> str:
    """
    Format license info for display.

    Args:
        license_info: Dict from validate_license_key()

    Returns:
        Formatted string for display
    """
    if not license_info.get("licensing_enabled"):
        return "FilaOps Community Edition - All Features Unlocked"

    tier_display = {
        "community": "Community",
        "professional": "Professional",
        "enterprise": "Enterprise",
    }.get(license_info["tier"], "Unknown")

    lines = [
        f"FilaOps {tier_display} Edition",
        f"Licensed to: {license_info.get('org_name') or license_info['email']}",
    ]

    if license_info["expires_at"]:
        lines.append(f"Expires: {license_info['expires_at'][:10]}")
        if license_info.get("days_remaining"):
            lines.append(f"Days remaining: {license_info['days_remaining']}")
    else:
        lines.append("License: Perpetual")

    lines.append(f"Max users: {license_info['max_users']}")

    return "\n".join(lines)
