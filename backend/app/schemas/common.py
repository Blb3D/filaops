"""
Common API Response Schemas

Provides standardized error responses and pagination models for consistent API behavior.
"""
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Error Response Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Additional error details for debugging."""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: Optional[str] = Field(None, description="Detailed error message")
    type: Optional[str] = Field(None, description="Error type")


class ErrorResponse(BaseModel):
    """
    Standardized error response for all API errors.

    This provides a consistent structure for error responses across the entire API,
    making it easier for clients to handle errors uniformly.

    Error Codes:
        - VALIDATION_ERROR: Request validation failed (400)
        - AUTHENTICATION_ERROR: Authentication required or failed (401)
        - INVALID_CREDENTIALS: Invalid email/password (401)
        - TOKEN_EXPIRED: Authentication token expired (401)
        - INVALID_TOKEN: Invalid authentication token (401)
        - PERMISSION_DENIED: User lacks permission (403)
        - NOT_FOUND: Resource not found (404)
        - CONFLICT: Resource conflict (409)
        - DUPLICATE_ERROR: Duplicate resource (409)
        - CONCURRENCY_ERROR: Concurrent modification detected (409)
        - BUSINESS_RULE_ERROR: Business rule violation (422)
        - INSUFFICIENT_INVENTORY: Not enough inventory (422)
        - QUOTE_EXPIRED: Quote has expired (422)
        - PRODUCTION_NOT_READY: Production cannot proceed (422)
        - DATABASE_ERROR: Database operation failed (500)
        - INTEGRATION_ERROR: External service error (500)
        - INTERNAL_ERROR: Unexpected internal error (500)
        - SERVICE_UNAVAILABLE: Service temporarily unavailable (503)

    Example:
        {
            "error": "NOT_FOUND",
            "message": "Product with ID 123 not found",
            "details": {
                "resource": "Product",
                "resource_id": "123"
            },
            "timestamp": "2025-12-23T10:30:00Z"
        }
    """
    error: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context for debugging"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred (UTC)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "NOT_FOUND",
                "message": "Product with ID 123 not found",
                "details": {
                    "resource": "Product",
                    "resource_id": "123"
                },
                "timestamp": "2025-12-23T10:30:00Z"
            }
        }


class ValidationErrorResponse(ErrorResponse):
    """
    Specialized error response for validation errors.

    Provides detailed information about validation failures including
    which fields failed validation and why.
    """
    error: str = Field(default="VALIDATION_ERROR", description="Always VALIDATION_ERROR")
    details: Dict[str, Any] = Field(
        ...,
        description="Validation error details with 'errors' list"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {
                    "errors": [
                        {
                            "field": "email",
                            "message": "Invalid email format",
                            "type": "value_error.email"
                        }
                    ]
                },
                "timestamp": "2025-12-23T10:30:00Z"
            }
        }


# ============================================================================
# Pagination Models
# ============================================================================

class PaginationParams(BaseModel):
    """
    Standardized pagination parameters for list endpoints.

    All list endpoints should accept these parameters for consistent pagination behavior.
    Uses offset-based pagination which is simple and predictable.
    """
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip (for pagination)"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of records to return (1-500)"
    )

    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Ensure limit is within acceptable range."""
        if v < 1:
            return 1
        if v > 500:
            return 500
        return v

    @field_validator('offset')
    @classmethod
    def validate_offset(cls, v: int) -> int:
        """Ensure offset is non-negative."""
        return max(0, v)


class PaginationMeta(BaseModel):
    """
    Pagination metadata included in list responses.

    Provides information about the current page and total records,
    making it easy for clients to implement pagination controls.
    """
    total: int = Field(..., description="Total number of records matching the query")
    offset: int = Field(..., description="Current offset (number of records skipped)")
    limit: int = Field(..., description="Maximum records per page")
    returned: int = Field(..., description="Number of records in this response")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 150,
                "offset": 0,
                "limit": 50,
                "returned": 50
            }
        }


# ============================================================================
# Generic Response Wrappers
# ============================================================================

T = TypeVar('T')


class ListResponse(BaseModel, Generic[T]):
    """
    Standardized list response wrapper with pagination.

    All list endpoints should return this structure for consistency.
    The generic type T represents the item type in the list.

    Example:
        {
            "items": [...],
            "pagination": {
                "total": 150,
                "offset": 0,
                "limit": 50,
                "returned": 50
            }
        }
    """
    items: List[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "pagination": {
                    "total": 150,
                    "offset": 0,
                    "limit": 50,
                    "returned": 50
                }
            }
        }


class DetailResponse(BaseModel, Generic[T]):
    """
    Standardized detail response wrapper for single resources.

    Provides a consistent structure for single-resource responses.
    The generic type T represents the resource type.
    """
    data: T = Field(..., description="Resource data")

    class Config:
        json_schema_extra = {
            "example": {
                "data": {}
            }
        }


class MessageResponse(BaseModel):
    """
    Simple message response for operations that don't return data.

    Used for operations like delete, cancel, etc. where only a
    confirmation message is needed.
    """
    message: str = Field(..., description="Operation result message")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully"
            }
        }


class StatusResponse(BaseModel):
    """
    Status response for health checks and similar endpoints.
    """
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Status check timestamp (UTC)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-12-23T10:30:00Z"
            }
        }
