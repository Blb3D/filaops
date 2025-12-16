import { defineConfig, devices } from '@playwright/test';

/**
 * FilaOps E2E Test Configuration
 *
 * Run tests: npm run test:e2e
 * Run specific: npm run test:e2e -- --grep "customers"
 * Run with UI: npm run test:e2e -- --ui
 */

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: false, // Serial execution for workflow tests
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker to avoid parallel auth issues
  reporter: 'html',
  timeout: 60000, // 60s timeout per test

  use: {
    // Use DEV environment (5174) - PROD is 5173
    baseURL: process.env.BASE_URL || 'http://localhost:5174',
    trace: 'on-first-retry',
    // No screenshots by default - E2E workflow test enables them explicitly
    screenshot: 'off',
  },

  projects: [
    // Setup project - runs first to authenticate
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
      testDir: './e2e',
    },
    // Main tests - depend on setup and use stored auth
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Use stored auth state from setup
        storageState: './e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],

  // Docker containers should be running before tests
  // DEV: docker-compose -f docker-compose.dev.yml up -d
});
