/**
 * Form validation utilities for FilaOps frontend
 *
 * Provides reusable validation functions and helpers for form fields.
 * Returns user-friendly error messages suitable for display.
 */

/**
 * Validates required fields
 * @param {string} value - Field value to validate
 * @param {string} fieldName - Human-readable field name for error message
 * @returns {string|null} Error message or null if valid
 */
export function validateRequired(value, fieldName) {
  if (value === null || value === undefined || value === '') {
    return `${fieldName} is required`;
  }
  if (typeof value === 'string' && value.trim() === '') {
    return `${fieldName} is required`;
  }
  return null;
}

/**
 * Validates email format
 * @param {string} email - Email address to validate
 * @returns {string|null} Error message or null if valid
 */
export function validateEmail(email) {
  if (!email) return null; // Use validateRequired separately for required emails

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return 'Please enter a valid email address';
  }
  return null;
}

/**
 * Validates numeric values
 * @param {string|number} value - Value to validate
 * @param {string} fieldName - Human-readable field name
 * @param {Object} options - Validation options
 * @param {number} options.min - Minimum value (inclusive)
 * @param {number} options.max - Maximum value (inclusive)
 * @param {boolean} options.allowZero - Whether zero is allowed (default: true)
 * @param {boolean} options.allowNegative - Whether negative values are allowed (default: false)
 * @returns {string|null} Error message or null if valid
 */
export function validateNumber(value, fieldName, options = {}) {
  if (value === '' || value === null || value === undefined) {
    return null; // Use validateRequired separately
  }

  const num = parseFloat(value);

  if (isNaN(num)) {
    return `${fieldName} must be a valid number`;
  }

  if (!options.allowNegative && num < 0) {
    return `${fieldName} cannot be negative`;
  }

  if (!options.allowZero && num === 0) {
    return `${fieldName} must be greater than zero`;
  }

  if (options.min !== undefined && num < options.min) {
    return `${fieldName} must be at least ${options.min}`;
  }

  if (options.max !== undefined && num > options.max) {
    return `${fieldName} must be no more than ${options.max}`;
  }

  return null;
}

/**
 * Validates string length
 * @param {string} value - String to validate
 * @param {string} fieldName - Human-readable field name
 * @param {Object} options - Validation options
 * @param {number} options.min - Minimum length
 * @param {number} options.max - Maximum length
 * @returns {string|null} Error message or null if valid
 */
export function validateLength(value, fieldName, options = {}) {
  if (!value) return null; // Use validateRequired separately

  const length = value.length;

  if (options.min !== undefined && length < options.min) {
    return `${fieldName} must be at least ${options.min} characters`;
  }

  if (options.max !== undefined && length > options.max) {
    return `${fieldName} must be no more than ${options.max} characters`;
  }

  return null;
}

/**
 * Validates SKU format (alphanumeric, hyphens, underscores)
 * @param {string} sku - SKU to validate
 * @returns {string|null} Error message or null if valid
 */
export function validateSKU(sku) {
  if (!sku) return null; // Use validateRequired separately

  const skuRegex = /^[A-Z0-9_-]+$/;
  if (!skuRegex.test(sku)) {
    return 'SKU must contain only uppercase letters, numbers, hyphens, and underscores';
  }

  if (sku.length < 2) {
    return 'SKU must be at least 2 characters';
  }

  if (sku.length > 50) {
    return 'SKU must be no more than 50 characters';
  }

  return null;
}

/**
 * Validates phone number (basic US format)
 * @param {string} phone - Phone number to validate
 * @returns {string|null} Error message or null if valid
 */
export function validatePhone(phone) {
  if (!phone) return null; // Use validateRequired separately

  // Remove all non-numeric characters
  const cleaned = phone.replace(/\D/g, '');

  if (cleaned.length !== 10) {
    return 'Phone number must be 10 digits';
  }

  return null;
}

/**
 * Validates ZIP code (US format)
 * @param {string} zip - ZIP code to validate
 * @returns {string|null} Error message or null if valid
 */
export function validateZipCode(zip) {
  if (!zip) return null; // Use validateRequired separately

  const zipRegex = /^\d{5}(-\d{4})?$/;
  if (!zipRegex.test(zip)) {
    return 'ZIP code must be 5 digits or 5+4 format (e.g., 12345 or 12345-6789)';
  }

  return null;
}

/**
 * Validates that a value is within a specific set of options
 * @param {any} value - Value to validate
 * @param {Array} validOptions - Array of valid options
 * @param {string} fieldName - Human-readable field name
 * @returns {string|null} Error message or null if valid
 */
export function validateOptions(value, validOptions, fieldName) {
  if (!value) return null; // Use validateRequired separately

  if (!validOptions.includes(value)) {
    return `${fieldName} must be one of: ${validOptions.join(', ')}`;
  }

  return null;
}

/**
 * Validates quantity (positive number, optionally integer)
 * @param {string|number} quantity - Quantity to validate
 * @param {string} fieldName - Human-readable field name (default: "Quantity")
 * @param {boolean} requireInteger - Whether value must be an integer
 * @returns {string|null} Error message or null if valid
 */
export function validateQuantity(quantity, fieldName = 'Quantity', requireInteger = false) {
  if (quantity === '' || quantity === null || quantity === undefined) {
    return null; // Use validateRequired separately
  }

  const num = parseFloat(quantity);

  if (isNaN(num)) {
    return `${fieldName} must be a valid number`;
  }

  if (num <= 0) {
    return `${fieldName} must be greater than zero`;
  }

  if (requireInteger && !Number.isInteger(num)) {
    return `${fieldName} must be a whole number`;
  }

  return null;
}

/**
 * Validates price/cost (non-negative number with max 2 decimal places)
 * @param {string|number} price - Price to validate
 * @param {string} fieldName - Human-readable field name
 * @returns {string|null} Error message or null if valid
 */
export function validatePrice(price, fieldName) {
  if (price === '' || price === null || price === undefined) {
    return null; // Use validateRequired separately
  }

  const num = parseFloat(price);

  if (isNaN(num)) {
    return `${fieldName} must be a valid number`;
  }

  if (num < 0) {
    return `${fieldName} cannot be negative`;
  }

  // Check for more than 2 decimal places
  const decimalPart = price.toString().split('.')[1];
  if (decimalPart && decimalPart.length > 2) {
    return `${fieldName} can have at most 2 decimal places`;
  }

  return null;
}

/**
 * Validates a form object with multiple fields
 * @param {Object} formData - Object containing form field values
 * @param {Object} rules - Validation rules for each field
 * @returns {Object} Object with field names as keys and error messages as values
 *
 * Example:
 * const errors = validateForm(
 *   { name: '', email: 'invalid', quantity: -1 },
 *   {
 *     name: [(v) => validateRequired(v, 'Name')],
 *     email: [(v) => validateRequired(v, 'Email'), validateEmail],
 *     quantity: [(v) => validateRequired(v, 'Quantity'), (v) => validateQuantity(v)]
 *   }
 * );
 * // Returns: { name: 'Name is required', email: 'Please enter a valid email address', quantity: 'Quantity must be greater than zero' }
 */
export function validateForm(formData, rules) {
  const errors = {};

  for (const [fieldName, validators] of Object.entries(rules)) {
    const value = formData[fieldName];

    // Run each validator for this field
    for (const validator of validators) {
      const error = validator(value);
      if (error) {
        errors[fieldName] = error;
        break; // Stop at first error for this field
      }
    }
  }

  return errors;
}

/**
 * Checks if an errors object has any errors
 * @param {Object} errors - Errors object from validateForm
 * @returns {boolean} True if there are any errors
 */
export function hasErrors(errors) {
  return Object.keys(errors).length > 0;
}

/**
 * Gets the first error message from an errors object
 * @param {Object} errors - Errors object from validateForm
 * @returns {string|null} First error message or null if no errors
 */
export function getFirstError(errors) {
  const keys = Object.keys(errors);
  return keys.length > 0 ? errors[keys[0]] : null;
}
