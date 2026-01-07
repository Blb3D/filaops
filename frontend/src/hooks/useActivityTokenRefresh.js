/**
 * Activity-Based Token Refresh Hook
 *
 * Prevents users from losing work due to session expiration while actively working.
 * Tracks user activity and automatically refreshes the access token before it expires.
 */
import { useEffect, useRef, useCallback } from "react";
import { API_URL } from "../config/api";

// How often to check if token needs refresh (in ms)
const CHECK_INTERVAL = 60 * 1000; // 1 minute

// Refresh token when it will expire within this many minutes
const REFRESH_THRESHOLD_MINUTES = 5;

// Consider user inactive after this many minutes of no activity
const INACTIVITY_TIMEOUT_MINUTES = 25;

/**
 * Decode JWT token to get expiration time
 * @param {string} token - JWT token
 * @returns {number|null} - Expiration timestamp in ms, or null if invalid
 */
function getTokenExpiration(token) {
  if (!token) return null;

  try {
    // JWT format: header.payload.signature
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    // Decode payload (base64url)
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));

    // exp is in seconds, convert to ms
    if (payload.exp) {
      return payload.exp * 1000;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Hook to automatically refresh auth tokens based on user activity
 *
 * Usage:
 *   useActivityTokenRefresh(); // Call once in your app root or layout
 */
export default function useActivityTokenRefresh() {
  const lastActivityRef = useRef(Date.now());
  const isRefreshingRef = useRef(false);

  // Update last activity timestamp on user interaction
  const updateActivity = useCallback(() => {
    lastActivityRef.current = Date.now();
  }, []);

  // Refresh the access token using the refresh token
  const refreshToken = useCallback(async () => {
    if (isRefreshingRef.current) return false;

    const refreshTokenValue = localStorage.getItem("adminRefreshToken");
    if (!refreshTokenValue) {
      return false;
    }

    isRefreshingRef.current = true;

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refreshTokenValue }),
      });

      if (!response.ok) {
        // Refresh token is invalid/expired - user needs to log in again
        console.warn("Token refresh failed - session may have expired");
        return false;
      }

      const data = await response.json();

      // Update stored tokens
      localStorage.setItem("adminToken", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("adminRefreshToken", data.refresh_token);
      }

      console.debug("Token refreshed successfully");
      return true;
    } catch (error) {
      console.error("Token refresh error:", error);
      return false;
    } finally {
      isRefreshingRef.current = false;
    }
  }, []);

  // Check if token needs refresh
  const checkAndRefresh = useCallback(() => {
    const token = localStorage.getItem("adminToken");
    if (!token) return;

    const expiration = getTokenExpiration(token);
    if (!expiration) return;

    const now = Date.now();
    const timeUntilExpiry = expiration - now;
    const thresholdMs = REFRESH_THRESHOLD_MINUTES * 60 * 1000;
    const inactivityMs = INACTIVITY_TIMEOUT_MINUTES * 60 * 1000;

    // Check if user has been active recently
    const timeSinceActivity = now - lastActivityRef.current;
    const isUserActive = timeSinceActivity < inactivityMs;

    // If token expires soon and user is active, refresh it
    if (timeUntilExpiry < thresholdMs && timeUntilExpiry > 0 && isUserActive) {
      console.debug(`Token expires in ${Math.round(timeUntilExpiry / 1000 / 60)} min, user active - refreshing`);
      refreshToken();
    }
  }, [refreshToken]);

  useEffect(() => {
    // Activity event listeners
    const events = ["mousedown", "keydown", "mousemove", "scroll", "touchstart"];

    // Throttle activity updates to avoid excessive calls
    let activityTimeout = null;
    const throttledActivity = () => {
      if (!activityTimeout) {
        updateActivity();
        activityTimeout = setTimeout(() => {
          activityTimeout = null;
        }, 5000); // Only update once every 5 seconds max
      }
    };

    // Add event listeners
    events.forEach(event => {
      window.addEventListener(event, throttledActivity, { passive: true });
    });

    // Set up periodic token check
    const intervalId = setInterval(checkAndRefresh, CHECK_INTERVAL);

    // Initial check
    checkAndRefresh();

    // Cleanup
    return () => {
      events.forEach(event => {
        window.removeEventListener(event, throttledActivity);
      });
      clearInterval(intervalId);
      if (activityTimeout) clearTimeout(activityTimeout);
    };
  }, [updateActivity, checkAndRefresh]);
}
