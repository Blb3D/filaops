/**
 * TypeScript-style JSDoc type definitions for API responses
 * These match the standardized backend responses from Sprint 1-2
 */

/**
 * @typedef {Object} PaginationMeta
 * @property {number} total - Total number of records matching the query
 * @property {number} offset - Current offset (number of records skipped)
 * @property {number} limit - Maximum records per page
 * @property {number} returned - Actual number of records in this response
 */

/**
 * @template T
 * @typedef {Object} ListResponse
 * @property {T[]} items - Array of items
 * @property {PaginationMeta} pagination - Pagination metadata
 */

/**
 * @typedef {Object} ApiErrorResponse
 * @property {string} error - Machine-readable error code (e.g., "NOT_FOUND", "VALIDATION_ERROR")
 * @property {string} message - Human-readable error message
 * @property {Record<string, any>} [details] - Additional error context
 * @property {string} timestamp - ISO 8601 timestamp of when error occurred
 */

/**
 * @typedef {Object} ValidationErrorDetail
 * @property {string} field - Field that caused the error
 * @property {string} message - Error message for this field
 * @property {string} type - Error type identifier
 */

/**
 * Enhanced ApiError class that includes standardized error structure
 */
export class StandardApiError extends Error {
  /**
   * @param {number} status - HTTP status code
   * @param {ApiErrorResponse} errorResponse - Standardized error response
   */
  constructor(status, errorResponse) {
    super(errorResponse.message);
    this.name = "StandardApiError";
    this.status = status;
    this.errorCode = errorResponse.error;
    this.details = errorResponse.details;
    this.timestamp = errorResponse.timestamp;
  }

  /**
   * Check if this is a specific error type
   * @param {string} code - Error code to check (e.g., "NOT_FOUND")
   * @returns {boolean}
   */
  isErrorCode(code) {
    return this.errorCode === code;
  }

  /**
   * Get validation errors if this is a validation error
   * @returns {ValidationErrorDetail[]|null}
   */
  getValidationErrors() {
    if (this.errorCode === "VALIDATION_ERROR" && this.details?.errors) {
      return this.details.errors;
    }
    return null;
  }

  /**
   * Check if this is a not found error
   * @returns {boolean}
   */
  isNotFound() {
    return this.errorCode === "NOT_FOUND";
  }

  /**
   * Check if this is an authentication error
   * @returns {boolean}
   */
  isAuthError() {
    return [
      "AUTHENTICATION_ERROR",
      "INVALID_CREDENTIALS",
      "TOKEN_EXPIRED",
      "INVALID_TOKEN",
    ].includes(this.errorCode);
  }

  /**
   * Check if this is a permission error
   * @returns {boolean}
   */
  isPermissionDenied() {
    return this.errorCode === "PERMISSION_DENIED";
  }
}

/**
 * Parse error response and create StandardApiError if it matches the format
 * @param {number} status - HTTP status code
 * @param {any} payload - Response payload
 * @returns {StandardApiError|null}
 */
export function parseStandardError(status, payload) {
  if (
    payload &&
    typeof payload === "object" &&
    "error" in payload &&
    "message" in payload &&
    "timestamp" in payload
  ) {
    return new StandardApiError(status, payload);
  }
  return null;
}
