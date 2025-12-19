import { useState, useEffect } from 'react';
import { API_URL } from '../config/api';

/**
 * Update Checker Hook
 *
 * Checks for FilaOps updates once per day (stored in localStorage).
 * Provides update information, loading state, and dismissal functionality.
 */

const STORAGE_KEY_LAST_CHECK = 'filaops_last_update_check';
const STORAGE_KEY_UPDATE_AVAILABLE = 'filaops_update_available';
const STORAGE_KEY_DISMISSED = 'filaops_update_dismissed';
const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000; // 24 hours
const INITIAL_CHECK_DELAY = 5000; // 5 seconds after app loads

export const useUpdateChecker = () => {
    const [updateInfo, setUpdateInfo] = useState(null);
    const [isChecking, setIsChecking] = useState(false);
    const [error, setError] = useState(null);
    const [lastChecked, setLastChecked] = useState(null);

    const checkForUpdates = async () => {
        try {
            setIsChecking(true);
            setError(null);

            const response = await fetch(`${API_URL}/api/v1/system/updates/check`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            setUpdateInfo(data);
            setLastChecked(new Date());

            // Store in localStorage
            localStorage.setItem(STORAGE_KEY_LAST_CHECK, Date.now().toString());

            if (data.update_available) {
                localStorage.setItem(STORAGE_KEY_UPDATE_AVAILABLE, JSON.stringify({
                    version: data.latest_version,
                    checked_at: new Date().toISOString()
                }));
            } else {
                localStorage.removeItem(STORAGE_KEY_UPDATE_AVAILABLE);
            }

            return data;

        } catch (err) {
            console.error('Update check failed:', err);
            setError(err.message);

            // Try to load cached update info
            const cached = localStorage.getItem(STORAGE_KEY_UPDATE_AVAILABLE);
            if (cached) {
                try {
                    const cachedData = JSON.parse(cached);
                    // Only use cached data if it's less than 7 days old
                    const cacheAge = Date.now() - new Date(cachedData.checked_at).getTime();
                    if (cacheAge < 7 * 24 * 60 * 60 * 1000) {
                        setUpdateInfo({
                            update_available: true,
                            latest_version: cachedData.version,
                            current_version: 'unknown',
                            error: 'Using cached update info (network unavailable)'
                        });
                    }
                } catch (parseError) {
                    console.error('Failed to parse cached update info:', parseError);
                }
            }
        } finally {
            setIsChecking(false);
        }
    };

    const dismissUpdate = () => {
        if (updateInfo?.latest_version) {
            localStorage.setItem(STORAGE_KEY_DISMISSED, JSON.stringify({
                version: updateInfo.latest_version,
                dismissed_at: new Date().toISOString()
            }));

            // Update state to hide notification
            setUpdateInfo(prev => prev ? { ...prev, dismissed: true } : null);
        }
    };

    const checkDismissalStatus = () => {
        if (!updateInfo?.update_available) return false;

        const dismissed = localStorage.getItem(STORAGE_KEY_DISMISSED);
        if (!dismissed) return false;

        try {
            const dismissedData = JSON.parse(dismissed);
            return dismissedData.version === updateInfo.latest_version;
        } catch {
            return false;
        }
    };

    const shouldCheckForUpdates = () => {
        const lastCheck = localStorage.getItem(STORAGE_KEY_LAST_CHECK);
        if (!lastCheck) return true;

        const timeSinceLastCheck = Date.now() - parseInt(lastCheck);
        return timeSinceLastCheck > CHECK_INTERVAL_MS;
    };

    useEffect(() => {
        // Only check if it's been more than 24 hours since last check
        if (shouldCheckForUpdates()) {
            const timer = setTimeout(checkForUpdates, INITIAL_CHECK_DELAY);
            return () => clearTimeout(timer);
        } else {
            // Load cached data if available
            const cached = localStorage.getItem(STORAGE_KEY_UPDATE_AVAILABLE);
            if (cached) {
                try {
                    const cachedData = JSON.parse(cached);
                    setUpdateInfo({
                        update_available: true,
                        latest_version: cachedData.version,
                        cached: true
                    });

                    const lastCheck = localStorage.getItem(STORAGE_KEY_LAST_CHECK);
                    if (lastCheck) {
                        setLastChecked(new Date(parseInt(lastCheck)));
                    }
                } catch (error) {
                    console.error('Failed to load cached update info:', error);
                }
            }
        }
    }, []);

    return {
        updateInfo,
        isChecking,
        error,
        lastChecked,
        checkForUpdates,
        dismissUpdate,
        isDismissed: checkDismissalStatus(),
        hasUpdate: updateInfo?.update_available && !checkDismissalStatus()
    };
};
