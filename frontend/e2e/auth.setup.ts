import { test as setup, expect } from '@playwright/test';

const authFile = './e2e/.auth/user.json';

// Test credentials - same as in functional-workflow.spec.ts
const TEST_EMAIL = 'admin@test.com';
const TEST_PASSWORD = 'Admin123!';

setup('authenticate', async ({ page }) => {
  // Navigate to login
  await page.goto('/admin/login');
  await page.waitForLoadState('networkidle');

  // Fill and submit login form
  await page.fill('input[type="email"]', TEST_EMAIL);
  await page.fill('input[type="password"]', TEST_PASSWORD);
  await page.click('button[type="submit"]');

  // Wait for redirect away from login
  await page.waitForFunction(() => !window.location.href.includes('/login'), { timeout: 30000 });

  // Dismiss any promotional modals
  await page.waitForTimeout(500);
  const dontShow = page.locator('text="Don\'t show this again"');
  if (await dontShow.isVisible({ timeout: 1000 }).catch(() => false)) {
    await dontShow.click();
  }
  const gotIt = page.locator('text="Got it, thanks!"');
  if (await gotIt.isVisible({ timeout: 1000 }).catch(() => false)) {
    await gotIt.click();
  }

  // Verify we're logged in (should be on admin page)
  await expect(page.locator('text="Dashboard"').first()).toBeVisible({ timeout: 10000 });

  // Save authentication state
  await page.context().storageState({ path: authFile });
});
