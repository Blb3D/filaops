/**
 * E2E Test Configuration
 * 
 * Centralized credentials and config for all E2E tests.
 * Must match backend test user (backend/scripts/seed_test_data.py)
 */

/// <reference types="node" />

export const E2E_CONFIG = {
  // Test credentials - must match backend seeded test user
  email: process.env.E2E_ADMIN_EMAIL || 'e2e-test@filaops.local',
  password: process.env.E2E_ADMIN_PASSWORD || 'TestPass123!',
  name: 'E2E Test User',
  
  // API URLs
  baseUrl: (typeof process !== 'undefined' ? process.env.VITE_API_URL : undefined) || 'http://127.0.0.1:8000',
  
  // Timeouts
  defaultTimeout: 10000,
  authTimeout: 15000,
};
