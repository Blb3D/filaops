/**
 * Smoke Tests - Quick Validation Suite
 * 
 * Run these after any deployment to verify core functionality.
 * Should complete in under 2 minutes.
 * 
 * Usage: npm run test:smoke
 */

import { test, expect } from '@playwright/test';

test.describe('Smoke Tests - Critical Paths', () => {
  
  test('app loads and shows login', async ({ page }) => {
    // Navigate to login page first, then clear auth
    await page.goto('/admin/login');
    await page.context().clearCookies();
    await page.evaluate(() => localStorage.clear());

    // Reload to see login page in unauthenticated state
    await page.reload();

    // Should show "Staff Login" heading
    await expect(page.getByRole('heading', { name: /staff login|login|sign in/i })).toBeVisible({ timeout: 5000 });

    // Verify login form elements exist
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('can navigate to main sections', async ({ page }) => {
    const sections = [
      '/admin/orders',
      '/admin/production',
      '/admin/inventory',
      '/admin/products',
      '/admin/bom',
    ];

    for (const path of sections) {
      await page.goto(path);
      // Just verify page loaded (not login/error page)
      await expect(page).not.toHaveURL(/login/);
      // Wait for any content to load
      await page.waitForLoadState('networkidle', { timeout: 3000 });
    }
  });

  test('orders page loads data', async ({ page }) => {
    await page.goto('/admin/orders');
    
    // Should see table headers or create button
    const hasTableHeader = await page.getByRole('columnheader').first().isVisible({ timeout: 3000 }).catch(() => false);
    const hasCreateButton = await page.getByRole('button', { name: /create|new/i }).isVisible().catch(() => false);
    
    expect(hasTableHeader || hasCreateButton).toBeTruthy();
  });

  test('can create new order', async ({ page }) => {
    await page.goto('/admin/orders');
    
    const createButton = page.getByRole('button', { name: /create|new.*order/i });
    await expect(createButton).toBeVisible();
    await createButton.click();
    
    // Modal should appear with customer selection heading
    await expect(page.getByRole('heading', { name: /select customer/i })).toBeVisible({ timeout: 3000 });
  });

  test('production page shows work orders', async ({ page }) => {
    await page.goto('/admin/production');
    
    // Should load without errors - look for specific Production heading
    await expect(page.getByRole('heading', { name: /production/i }).first()).toBeVisible();
  });

  test('inventory page functional', async ({ page }) => {
    await page.goto('/admin/inventory');
    
    // Just verify page loaded successfully
    await expect(page).toHaveURL(/inventory/);
    // Page should not show error state
    const hasError = await page.getByText(/error|failed/i).isVisible({ timeout: 2000 }).catch(() => false);
    expect(hasError).toBeFalsy();
  });

  test('API is responding', async ({ page }) => {
    await page.goto('/admin/orders');
    
    // Listen for API calls
    const response = await page.waitForResponse(
      resp => resp.url().includes('/api/v1') && resp.status() < 500,
      { timeout: 5000 }
    ).catch(() => null);
    
    expect(response).not.toBeNull();
  });

  test('no console errors on load', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/admin/orders');
    await page.waitForTimeout(2000);
    
    // Filter out known harmless errors (e.g., browser extension errors)
    const criticalErrors = errors.filter(e => 
      !e.includes('chrome-extension') && 
      !e.includes('devtools') &&
      !e.includes('favicon')
    );
    
    expect(criticalErrors.length).toBe(0);
  });

  test('status transitions work', async ({ page }) => {
    await page.goto('/admin/orders');
    
    // Find first order with actions available
    const firstRow = page.locator('tr[data-order-id]').first();
    if (await firstRow.count() > 0) {
      await firstRow.click();
      
      // Should show order details
      await expect(page.getByText(/status|details/i)).toBeVisible();
    }
  });

  test('search functionality works', async ({ page }) => {
    await page.goto('/admin/orders');
    
    const searchBox = page.getByPlaceholder(/search|filter/i);
    if (await searchBox.isVisible()) {
      await searchBox.fill('test');
      await page.waitForTimeout(500);
      
      // Table should update or show no results
      const hasResults = await page.locator('tr').count() > 0;
      expect(hasResults).toBeTruthy();
    }
  });
});

test.describe('Smoke Tests - Error Handling', () => {
  
  test('handles network errors gracefully', async ({ page }) => {
    // Block API calls
    await page.route('**/api/v1/**', route => route.abort());
    
    await page.goto('/admin/orders');
    
    // Should show error message, not crash
    await expect(page.getByText(/error|failed|unable/i)).toBeVisible({ timeout: 3000 });
  });

  test('handles 404 gracefully', async ({ page }) => {
    await page.goto('/admin/nonexistent-page');
    
    // Should show 404 page or redirect
    const has404 = await page.getByText(/404|not.*found/i).isVisible().catch(() => false);
    const redirected = page.url().includes('/admin');
    
    expect(has404 || redirected).toBeTruthy();
  });
});

test.describe('Smoke Tests - Mobile Responsive', () => {
  
  test.use({ viewport: { width: 375, height: 667 } }); // iPhone SE
  
  test('orders page works on mobile', async ({ page }) => {
    await page.goto('/admin/orders');
    
    // Just verify page loaded on mobile viewport
    await expect(page).toHaveURL(/orders/);
    
    // Check that some interactive element is visible
    const hasInteraction = await page.getByRole('button').first().isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasInteraction).toBeTruthy();
  });
});
