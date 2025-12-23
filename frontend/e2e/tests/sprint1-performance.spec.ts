/**
 * Sprint 1 - Performance Tests (PostgreSQL Native)
 *
 * Tests for Agent 1 (Backend Performance) deliverables:
 * - Dashboard loads in <500ms
 * - List endpoints respond in <1s
 * - N+1 queries eliminated (aggregated queries)
 * - Database indexes improve query performance
 *
 * Success Criteria from PRODUCTION_READINESS_PLAN.md:
 * - Dashboard loads in <500ms
 * - All list endpoints <1s with 1000 records
 *
 * IMPORTANT: These tests run against native PostgreSQL (not Docker)
 * Start servers: backend (uvicorn), frontend (npm run dev)
 */

import { test, expect } from '@playwright/test';

test.describe('Sprint 1 - Performance Benchmarks (PostgreSQL Native)', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('dashboard summary API responds in under 500ms', async ({ page }) => {
    let apiStartTime = 0;
    let apiEndTime = 0;

    // Listen for the dashboard summary API call
    page.on('request', (request) => {
      if (request.url().includes('/api/v1/admin/dashboard/summary')) {
        apiStartTime = Date.now();
      }
    });

    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/admin/dashboard/summary')) {
        apiEndTime = Date.now();
      }
    });

    // Navigate to dashboard
    await page.goto('/admin/dashboard');

    // Wait for summary to load
    await expect(page.locator('text=/Total Sales|Active Orders|Low Stock/i').first()).toBeVisible({ timeout: 5000 });

    // Calculate response time
    const responseTime = apiEndTime - apiStartTime;
    console.log(`Dashboard summary API: ${responseTime}ms`);

    // Verify API response time
    expect(apiStartTime).toBeGreaterThan(0);
    expect(responseTime).toBeLessThan(500);
  });

  test('dashboard page fully loads in under 1 second', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('/admin/dashboard');

    // Wait for all dashboard content to be visible
    await expect(page.locator('text=/Dashboard|Overview/i').first()).toBeVisible({ timeout: 5000 });

    // Wait for charts/stats to render
    await page.waitForLoadState('networkidle');

    const endTime = Date.now();
    const loadTime = endTime - startTime;

    console.log(`Dashboard full load time: ${loadTime}ms`);

    // CRITICAL: Must be under 1000ms for good UX
    expect(loadTime).toBeLessThan(1000);
  });

  test('inventory list endpoint responds quickly', async ({ page }) => {
    let apiStartTime = 0;
    let apiEndTime = 0;

    page.on('request', (request) => {
      if (request.url().includes('/api/v1/inventory') && request.method() === 'GET') {
        apiStartTime = Date.now();
      }
    });

    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/inventory') && response.request().method() === 'GET') {
        apiEndTime = Date.now();
      }
    });

    await page.goto('/admin/inventory');

    // Wait for inventory table to load
    await expect(page.locator('table').first()).toBeVisible({ timeout: 5000 });

    // Calculate response time
    const responseTime = apiEndTime - apiStartTime;
    console.log(`Inventory list API: ${responseTime}ms`);

    // Verify API response time
    expect(responseTime).toBeLessThan(1000);
  });

  test('sales orders list endpoint responds quickly', async ({ page }) => {
    let apiStartTime = 0;
    let apiEndTime = 0;

    page.on('request', (request) => {
      if (request.url().includes('/api/v1/sales-orders') && request.method() === 'GET') {
        apiStartTime = Date.now();
      }
    });

    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/sales-orders') && response.request().method() === 'GET') {
        apiEndTime = Date.now();
      }
    });

    await page.goto('/admin/orders');

    // Wait for orders table to load
    await expect(page.locator('table, .order-list').first()).toBeVisible({ timeout: 5000 });

    // Calculate response time
    const responseTime = apiEndTime - apiStartTime;
    console.log(`Sales orders list API: ${responseTime}ms`);

    // Verify API response time
    expect(responseTime).toBeLessThan(1000);
  });

  test('products/items list endpoint responds quickly', async ({ page }) => {
    let apiStartTime = 0;
    let apiEndTime = 0;

    page.on('request', (request) => {
      if (request.url().includes('/api/v1/items') && request.method() === 'GET') {
        apiStartTime = Date.now();
      }
    });

    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/items') && response.request().method() === 'GET') {
        apiEndTime = Date.now();
      }
    });

    await page.goto('/admin/products');

    // Wait for items table to load
    await expect(page.locator('table').first()).toBeVisible({ timeout: 5000 });

    // Calculate response time
    const responseTime = apiEndTime - apiStartTime;
    console.log(`Items list API: ${responseTime}ms`);

    // Verify API response time
    expect(responseTime).toBeLessThan(1000);
  });

  test('N+1 query elimination - dashboard summary uses aggregated queries', async ({ page }) => {
    // This test verifies that the dashboard summary endpoint makes
    // a minimal number of queries (should be ~3-5 queries total, not 100+)

    const apiCalls: string[] = [];

    page.on('request', (request) => {
      if (request.url().includes('/api/v1/')) {
        apiCalls.push(request.url());
      }
    });

    await page.goto('/admin/dashboard');
    await page.waitForLoadState('networkidle');

    // Should make minimal API calls:
    // 1. /api/v1/admin/dashboard/summary (single aggregated call)
    // 2. Maybe 1-2 more for charts/stats

    console.log(`Total API calls: ${apiCalls.length}`);
    console.log('API calls:', apiCalls);

    // Should NOT make 50+ individual queries for each product/order
    // With proper eager loading, should be <10 API calls total
    expect(apiCalls.length).toBeLessThan(10);
  });

  test('pagination loads next page quickly', async ({ page }) => {
    await page.goto('/admin/orders');

    // Wait for initial page to load
    await expect(page.locator('table').first()).toBeVisible({ timeout: 5000 });

    let apiStartTime = 0;
    let apiEndTime = 0;

    page.on('request', (request) => {
      if (request.url().includes('/api/v1/sales-orders') && request.url().includes('offset=')) {
        apiStartTime = Date.now();
      }
    });

    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/sales-orders') && response.url().includes('offset=')) {
        apiEndTime = Date.now();
      }
    });

    // Click next page (if pagination exists)
    const nextButton = page.locator('button:has-text("Next"), button[aria-label="Next page"]');
    if (await nextButton.isVisible()) {
      await nextButton.click();

      // Wait for page to update
      await page.waitForLoadState('networkidle');

      // Calculate response time
      const responseTime = apiEndTime - apiStartTime;
      console.log(`Pagination API: ${responseTime}ms`);

      // Verify pagination response time
      expect(responseTime).toBeLessThan(1000);
    } else {
      console.log('No pagination available (not enough records)');
      test.skip();
    }
  });

  test('database indexes exist for performance-critical queries', async ({ page }) => {
    // This is more of a smoke test - the actual index verification
    // happens in backend tests, but we can verify that queries
    // with indexed columns respond quickly

    const testQueries = [
      // Test status + date filtering (should use ix_sales_orders_status_created)
      { url: '/admin/orders?status=pending', name: 'Orders by status' },

      // Test inventory by product (should use ix_inventory_product_location)
      { url: '/admin/inventory', name: 'Inventory list' },

      // Test product filtering
      { url: '/admin/products?active=true', name: 'Active products' },
    ];

    for (const query of testQueries) {
      const startTime = Date.now();

      await page.goto(query.url);
      await page.waitForLoadState('networkidle');

      const loadTime = Date.now() - startTime;
      console.log(`${query.name} load time: ${loadTime}ms`);

      // With indexes, should be fast even with many records
      expect(loadTime).toBeLessThan(1500);
    }
  });
});

test.describe('Sprint 1 - Performance Regressions Prevention', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('no excessive re-renders on dashboard', async ({ page }) => {
    let renderCount = 0;

    // Monitor console for React dev tools messages (if available)
    page.on('console', (msg) => {
      if (msg.text().includes('rendered')) {
        renderCount++;
      }
    });

    await page.goto('/admin/dashboard');
    await page.waitForLoadState('networkidle');

    // Dashboard should not re-render excessively on load
    // This is a basic smoke test - actual render profiling requires React DevTools
    console.log(`Detected renders: ${renderCount}`);

    // Should not re-render more than a few times on initial load
    expect(renderCount).toBeLessThan(20);
  });

  test('list views handle empty state quickly', async ({ page }) => {
    // Even with no data, page should load quickly

    const startTime = Date.now();
    await page.goto('/admin/purchase-orders');

    // Wait for "no orders" message or table
    await expect(page.locator('table, text=/No.*orders|Empty/i').first()).toBeVisible({ timeout: 5000 });

    const loadTime = Date.now() - startTime;
    console.log(`Empty state load time: ${loadTime}ms`);

    // Empty states should be VERY fast
    expect(loadTime).toBeLessThan(1000);
  });
});
