"""
API Dependencies

Authentication dependencies and common query parameter dependencies
that can be safely imported without triggering rate limiter initialization issues.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_user_from_token
from app.schemas.common import PaginationParams

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from access token

    Args:
        token: JWT access token from Authorization header
        db: Database session

    Returns:
        User object if token is valid

    Raises:
        HTTPException 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token and extract user ID
    user_id = get_user_from_token(token, expected_type="access")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to require admin access.

    Use this dependency for admin-only endpoints (user management,
    analytics, customer management, etc.)

    Args:
        current_user: Current authenticated user (from get_current_user)

    Returns:
        User object if user is an admin

    Raises:
        HTTPException 403 if user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_staff_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to require staff access (admin or operator).

    Use this dependency for endpoints accessible to both admins and operators
    (dashboard, orders, production, inventory, etc.)

    Args:
        current_user: Current authenticated user (from get_current_user)

    Returns:
        User object if user is admin or operator

    Raises:
        HTTPException 403 if user is not staff (admin/operator)
    """
    if current_user.account_type not in ("admin", "operator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    return current_user


def get_pagination_params(
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip (for pagination)"
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of records to return (1-500)"
    )
) -> PaginationParams:
    """
    Dependency for standardized pagination parameters.

    All list endpoints should use this dependency for consistent pagination behavior.
    Uses offset-based pagination which is simple and predictable.

    Args:
        offset: Number of records to skip (default: 0)
        limit: Maximum records to return (default: 50, max: 500)

    Returns:
        PaginationParams object with validated offset and limit

    Example:
        @router.get("/items")
        async def list_items(
            pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
            db: Session = Depends(get_db)
        ):
            items = db.query(Item).offset(pagination.offset).limit(pagination.limit).all()
            total = db.query(Item).count()
            return {
                "items": items,
                "pagination": {
                    "total": total,
                    "offset": pagination.offset,
                    "limit": pagination.limit,
                    "returned": len(items)
                }
            }
    """
    return PaginationParams(offset=offset, limit=limit)
