/**
 * Centralized date formatting utilities with locale support.
 *
 * Uses the browser's locale by default (navigator.language) but can be
 * overridden via the settings if needed in the future.
 *
 * Usage:
 *   import { formatDate, formatDateTime, formatTime, formatRelativeDate } from '../lib/dateFormat';
 *
 *   formatDate(dateStr)          // "Jan 15, 2025" or locale equivalent
 *   formatDateTime(dateStr)      // "Jan 15, 2025, 3:30 PM"
 *   formatTime(dateStr)          // "3:30 PM"
 *   formatShortDate(dateStr)     // "Jan 15"
 *   formatRelativeDate(dateStr)  // "2 days ago", "in 3 hours", etc.
 */

/**
 * Get the user's preferred locale.
 * Returns browser locale, falling back to 'en-US' if unavailable.
 */
export function getUserLocale() {
  // Could be extended to read from user settings/localStorage
  return navigator?.language || 'en-US';
}

/**
 * Parse a date string or Date object safely.
 * @param {string|Date|number} dateInput - Date to parse
 * @returns {Date|null} - Parsed Date or null if invalid
 */
function parseDate(dateInput) {
  if (!dateInput) return null;
  try {
    const date = dateInput instanceof Date ? dateInput : new Date(dateInput);
    return isNaN(date.getTime()) ? null : date;
  } catch {
    return null;
  }
}

/**
 * Format a date in a human-readable format.
 * Example: "Jan 15, 2025"
 *
 * @param {string|Date|number} dateInput - Date to format
 * @param {Object} options - Additional Intl.DateTimeFormat options
 * @returns {string} - Formatted date string or empty string if invalid
 */
export function formatDate(dateInput, options = {}) {
  const date = parseDate(dateInput);
  if (!date) return '';

  const defaultOptions = {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  };

  return date.toLocaleDateString(getUserLocale(), { ...defaultOptions, ...options });
}

/**
 * Format a short date without year.
 * Example: "Jan 15"
 *
 * @param {string|Date|number} dateInput - Date to format
 * @returns {string} - Formatted date string or empty string if invalid
 */
export function formatShortDate(dateInput) {
  const date = parseDate(dateInput);
  if (!date) return '';

  return date.toLocaleDateString(getUserLocale(), {
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a date with time.
 * Example: "Jan 15, 2025, 3:30 PM"
 *
 * @param {string|Date|number} dateInput - Date to format
 * @param {Object} options - Additional Intl.DateTimeFormat options
 * @returns {string} - Formatted datetime string or empty string if invalid
 */
export function formatDateTime(dateInput, options = {}) {
  const date = parseDate(dateInput);
  if (!date) return '';

  const defaultOptions = {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  };

  return date.toLocaleString(getUserLocale(), { ...defaultOptions, ...options });
}

/**
 * Format a time only.
 * Example: "3:30 PM"
 *
 * @param {string|Date|number} dateInput - Date to format
 * @param {Object} options - Additional Intl.DateTimeFormat options
 * @returns {string} - Formatted time string or empty string if invalid
 */
export function formatTime(dateInput, options = {}) {
  const date = parseDate(dateInput);
  if (!date) return '';

  const defaultOptions = {
    hour: 'numeric',
    minute: '2-digit',
  };

  return date.toLocaleTimeString(getUserLocale(), { ...defaultOptions, ...options });
}

/**
 * Format a relative date (e.g., "2 days ago", "in 3 hours").
 * Falls back to formatted date if Intl.RelativeTimeFormat is unavailable.
 *
 * @param {string|Date|number} dateInput - Date to format
 * @returns {string} - Relative time string or formatted date if too far in past/future
 */
export function formatRelativeDate(dateInput) {
  const date = parseDate(dateInput);
  if (!date) return '';

  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffSec = Math.round(diffMs / 1000);
  const diffMin = Math.round(diffSec / 60);
  const diffHour = Math.round(diffMin / 60);
  const diffDay = Math.round(diffHour / 24);
  const diffWeek = Math.round(diffDay / 7);
  const diffMonth = Math.round(diffDay / 30);

  // Use Intl.RelativeTimeFormat if available
  if (typeof Intl !== 'undefined' && Intl.RelativeTimeFormat) {
    const rtf = new Intl.RelativeTimeFormat(getUserLocale(), { numeric: 'auto' });

    if (Math.abs(diffSec) < 60) {
      return rtf.format(diffSec, 'second');
    } else if (Math.abs(diffMin) < 60) {
      return rtf.format(diffMin, 'minute');
    } else if (Math.abs(diffHour) < 24) {
      return rtf.format(diffHour, 'hour');
    } else if (Math.abs(diffDay) < 7) {
      return rtf.format(diffDay, 'day');
    } else if (Math.abs(diffWeek) < 4) {
      return rtf.format(diffWeek, 'week');
    } else if (Math.abs(diffMonth) < 12) {
      return rtf.format(diffMonth, 'month');
    }
  }

  // Fall back to formatted date for dates more than a year away
  return formatDate(date);
}

/**
 * Format a date from milliseconds timestamp.
 * Wrapper for compatibility with existing time.js functions.
 *
 * @param {number} ms - Timestamp in milliseconds
 * @returns {string} - Formatted date string
 */
export function fmtDateLocalized(ms) {
  return formatShortDate(ms);
}

/**
 * Format a time from milliseconds timestamp.
 * Wrapper for compatibility with existing time.js functions.
 *
 * @param {number} ms - Timestamp in milliseconds
 * @returns {string} - Formatted time string
 */
export function fmtTimeLocalized(ms) {
  return formatTime(ms);
}
