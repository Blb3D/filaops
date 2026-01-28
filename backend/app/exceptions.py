"""
FilaOps ERP - Custom Exception Hierarchy

Provides structured, typed exceptions with error codes for consistent
error handling across the application.

Usage:
    from app.exceptions import NotFoundError, ValidationError

    # In endpoint
    raise NotFoundError("Product", product_id)

    # With custom message
    raise ValidationError("SKU must be unique", field="sku")
"""
from typing import Any, Dict, Optional


class FilaOpsException(Exception):
    """
    Base exception for all FilaOps ERP errors.

    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code (e.g., "NOT_FOUND", "VALIDATION_ERROR")
        status_code: HTTP status code to return
        details: Additional context for debugging
    """

    error_code: str = "FILAOPS_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        result = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


# ===================
# 400 Bad Request Errors
# ===================


class ValidationError(FilaOpsException):
    """Raised when input validation fails."""

    error_code = "VALIDATION_ERROR"
    status_code = 400

    def __init__(
        self,
        message: str = "Validation failed",
        *,
        field: Optional[str] = None,
        value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        super().__init__(message, details=details)


class InvalidStateError(FilaOpsException):
    """Raised when an operation is invalid for the current state."""

    error_code = "INVALID_STATE"
    status_code = 400

    def __init__(
        self,
        message: str = "Operation not allowed in current state",
        *,
        current_state: Optional[str] = None,
        allowed_states: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if current_state:
            details["current_state"] = current_state
        if allowed_states:
            details["allowed_states"] = allowed_states
        super().__init__(message, details=details)


class DuplicateError(FilaOpsException):
    """Raised when attempting to create a duplicate resource."""

    error_code = "DUPLICATE_ERROR"
    status_code = 400

    def __init__(
        self,
        resource: str = "Resource",
        *,
        field: Optional[str] = None,
        value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["resource"] = resource
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        message = f"{resource} already exists"
        if field and value:
            message = f"{resource} with {field}='{value}' already exists"
        super().__init__(message, details=details)


# ===================
# 401 Unauthorized Errors
# ===================


class AuthenticationError(FilaOpsException):
    """Raised when authentication fails."""

    error_code = "AUTHENTICATION_ERROR"
    status_code = 401

    def __init__(
        self,
        message: str = "Authentication required",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""

    error_code = "INVALID_CREDENTIALS"

    def __init__(
        self,
        message: str = "Invalid email or password",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)


class TokenExpiredError(AuthenticationError):
    """Raised when token has expired."""

    error_code = "TOKEN_EXPIRED"

    def __init__(
        self,
        message: str = "Token has expired",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)


class InvalidTokenError(AuthenticationError):
    """Raised when token is invalid."""

    error_code = "INVALID_TOKEN"

    def __init__(
        self,
        message: str = "Invalid token",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)


# ===================
# 403 Forbidden Errors
# ===================


class PermissionDeniedError(FilaOpsException):
    """Raised when user lacks permission for an action."""

    error_code = "PERMISSION_DENIED"
    status_code = 403

    def __init__(
        self,
        message: str = "Permission denied",
        *,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if action:
            details["action"] = action
        if resource:
            details["resource"] = resource
        super().__init__(message, details=details)


# ===================
# 404 Not Found Errors
# ===================


class NotFoundError(FilaOpsException):
    """Raised when a resource is not found."""

    error_code = "NOT_FOUND"
    status_code = 404

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Any = None,
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["resource"] = resource
        if resource_id is not None:
            details["resource_id"] = str(resource_id)
        message = f"{resource} not found"
        if resource_id is not None:
            message = f"{resource} with ID {resource_id} not found"
        super().__init__(message, details=details)


# ===================
# 409 Conflict Errors
# ===================


class ConflictError(FilaOpsException):
    """Raised when there's a resource conflict."""

    error_code = "CONFLICT"
    status_code = 409

    def __init__(
        self,
        message: str = "Resource conflict",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)


class ConcurrencyError(ConflictError):
    """Raised when concurrent modification is detected."""

    error_code = "CONCURRENCY_ERROR"

    def __init__(
        self,
        message: str = "Resource was modified by another user",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)


# ===================
# 422 Unprocessable Entity Errors
# ===================


class BusinessRuleError(FilaOpsException):
    """Raised when a business rule is violated."""

    error_code = "BUSINESS_RULE_ERROR"
    status_code = 422

    def __init__(
        self,
        message: str = "Business rule violation",
        *,
        rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if rule:
            details["rule"] = rule
        super().__init__(message, details=details)


class InsufficientInventoryError(BusinessRuleError):
    """Raised when there's not enough inventory."""

    error_code = "INSUFFICIENT_INVENTORY"

    def __init__(
        self,
        product_name: str,
        *,
        requested: float,
        available: float,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["product"] = product_name
        details["requested"] = requested
        details["available"] = available
        message = f"Insufficient inventory for {product_name}: requested {requested}, available {available}"
        super().__init__(message, details=details)


class QuoteExpiredError(BusinessRuleError):
    """Raised when attempting to use an expired quote."""

    error_code = "QUOTE_EXPIRED"

    def __init__(
        self,
        quote_number: str,
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["quote_number"] = quote_number
        message = f"Quote {quote_number} has expired"
        super().__init__(message, details=details)


class ProductionNotReadyError(BusinessRuleError):
    """Raised when production cannot proceed."""

    error_code = "PRODUCTION_NOT_READY"

    def __init__(
        self,
        message: str = "Production order cannot proceed",
        *,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if reason:
            details["reason"] = reason
        super().__init__(message, details=details)


# ===================
# 500 Internal Server Errors
# ===================


class IntegrationError(FilaOpsException):
    """Raised when an external service integration fails."""

    error_code = "INTEGRATION_ERROR"
    status_code = 500

    def __init__(
        self,
        service: str,
        message: str = "External service error",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["service"] = service
        super().__init__(f"{service}: {message}", details=details)


class EasyPostError(IntegrationError):
    """Raised when EasyPost shipping integration fails."""

    error_code = "EASYPOST_ERROR"

    def __init__(
        self,
        message: str = "Shipping service error",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__("EasyPost", message, details=details)


class BambuSuiteError(IntegrationError):
    """Raised when Bambu Print Suite integration fails."""

    error_code = "BAMBU_SUITE_ERROR"

    def __init__(
        self,
        message: str = "Print suite error",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__("Bambu Print Suite", message, details=details)


class DatabaseError(FilaOpsException):
    """Raised when a database operation fails."""

    error_code = "DATABASE_ERROR"
    status_code = 500

    def __init__(
        self,
        message: str = "Database operation failed",
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)


class FileStorageError(FilaOpsException):
    """Raised when file storage operations fail."""

    error_code = "FILE_STORAGE_ERROR"
    status_code = 500

    def __init__(
        self,
        message: str = "File storage operation failed",
        *,
        filename: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if filename:
            details["filename"] = filename
        super().__init__(message, details=details)


# ===================
# 503 Service Unavailable Errors
# ===================


class ServiceUnavailableError(FilaOpsException):
    """Raised when a service is temporarily unavailable."""

    error_code = "SERVICE_UNAVAILABLE"
    status_code = 503

    def __init__(
        self,
        service: str = "Service",
        message: str = "temporarily unavailable",
        *,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["service"] = service
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(f"{service} {message}", details=details)
