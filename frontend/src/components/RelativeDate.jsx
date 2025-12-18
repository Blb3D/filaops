import { useState, useEffect } from "react";

/**
 * RelativeDate - Displays dates in human-readable relative format
 *
 * Shows "2 hours ago", "Yesterday", "3 days ago", etc.
 * Falls back to absolute date for older dates.
 * Updates automatically every minute for recent dates.
 */

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const WEEK = 7 * DAY;
const MONTH = 30 * DAY;
const YEAR = 365 * DAY;

function formatRelative(date) {
  const now = new Date();
  const then = new Date(date);
  const diff = now - then;

  // Future dates
  if (diff < 0) {
    const absDiff = Math.abs(diff);
    if (absDiff < MINUTE) return "in a moment";
    if (absDiff < HOUR) {
      const mins = Math.round(absDiff / MINUTE);
      return `in ${mins} minute${mins === 1 ? "" : "s"}`;
    }
    if (absDiff < DAY) {
      const hours = Math.round(absDiff / HOUR);
      return `in ${hours} hour${hours === 1 ? "" : "s"}`;
    }
    if (absDiff < WEEK) {
      const days = Math.round(absDiff / DAY);
      return `in ${days} day${days === 1 ? "" : "s"}`;
    }
    // For far future, show absolute date
    return then.toLocaleDateString();
  }

  // Past dates
  if (diff < MINUTE) return "just now";
  if (diff < HOUR) {
    const mins = Math.round(diff / MINUTE);
    return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  }
  if (diff < DAY) {
    const hours = Math.round(diff / HOUR);
    return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  }
  if (diff < 2 * DAY) return "Yesterday";
  if (diff < WEEK) {
    const days = Math.round(diff / DAY);
    return `${days} days ago`;
  }
  if (diff < MONTH) {
    const weeks = Math.round(diff / WEEK);
    return `${weeks} week${weeks === 1 ? "" : "s"} ago`;
  }
  if (diff < YEAR) {
    const months = Math.round(diff / MONTH);
    return `${months} month${months === 1 ? "" : "s"} ago`;
  }

  // Over a year - show date
  return then.toLocaleDateString();
}

function formatAbsolute(date, options = {}) {
  const then = new Date(date);
  const { includeTime = true, short = false } = options;

  if (short) {
    return then.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  }

  if (includeTime) {
    return then.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  return then.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function RelativeDate({
  date,
  className = "",
  showAbsolute = false, // Always show absolute date instead of relative
  showTooltip = true, // Show absolute date on hover
  includeTime = true, // Include time in tooltip/absolute display
  updateInterval = 60000, // Update interval in ms (0 to disable)
}) {
  const [, setTick] = useState(0);

  // Auto-update for recent dates
  useEffect(() => {
    if (updateInterval <= 0 || showAbsolute) return;

    const timer = setInterval(() => {
      setTick((t) => t + 1);
    }, updateInterval);

    return () => clearInterval(timer);
  }, [updateInterval, showAbsolute]);

  if (!date) {
    return <span className={`text-gray-500 ${className}`}>—</span>;
  }

  const relativeText = formatRelative(date);
  const absoluteText = formatAbsolute(date, { includeTime });

  if (showAbsolute) {
    return <span className={className}>{absoluteText}</span>;
  }

  if (showTooltip) {
    return (
      <span className={`cursor-default ${className}`} title={absoluteText}>
        {relativeText}
      </span>
    );
  }

  return <span className={className}>{relativeText}</span>;
}

// Export helper functions for custom formatting
export { formatRelative, formatAbsolute };
