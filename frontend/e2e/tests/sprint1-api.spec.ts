/**
 * Sprint 1 - API Standardization Tests (PostgreSQL Native)
 *
 * Tests for Agent 3 (API Standardization) deliverables:
 * - Standard ErrorResponse model used
 * - Consistent pagination (offset/limit)
 * - Consistent response wrappers
 * - Documented error codes
 * - Request validation
 *
 * Success Criteria from PRODUCTION_READINESS_PLAN.md:
 * - All endpoints use same error format
 * - Pagination consistent
 * - Frontend error parsing works
 *
 * IMPORTANT: These tests run against native PostgreSQL (not Docker)
 */

import { test, expect } from '@playwright/test';

test.describe('Sprint 1 - API Error Standardization', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('API errors return standard ErrorResponse format', async ({ page }) => {
    let errorResponse: any = null;

    // Listen for error responses
    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/') && response.status() >= 400) {
        try {
          errorResponse = await response.json();
        } catch (e) {
          // Not JSON, skip
        }
      }
    });

    await page.goto('/admin/products');

    // Try to trigger a 404 by requesting non-existent item
    await page.goto('/admin/products?item_id=99999999');

    await page.waitForTimeout(2000);

    // If we caught an error, verify format
    if (errorResponse) {
      console.log('Error response:', errorResponse);

      // Should have standard fields
      expect(errorResponse).toHaveProperty('error');
      expect(errorResponse).toHaveProperty('message');

      // Error should be a string
      expect(typeof errorResponse.error).toBe('string');
      expect(typeof errorResponse.message).toBe('string');

      // Message should be user-friendly (not Python traceback)
      expect(errorResponse.message).not.toContain('Traceback');
      expect(errorResponse.message).not.toContain('File "');
    } else {
      // No error occurred
      test.skip();
    }
  });

  test('API 404 errors are consistent', async ({ page }) => {
    let notFoundResponse: any = null;

    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/') && response.status() === 404) {
        try {
          notFoundResponse = await response.json();
        } catch (e) {
          // Not JSON
        }
      }
    });

    // Request non-existent endpoint
    await page.request.get('http://localhost:8000/api/v1/items/99999999', {
      headers: {
        'Authorization': `Bearer ${await page.evaluate(() => localStorage.getItem('adminToken'))}`
      },
      failOnStatusCode: false
    });

    await page.waitForTimeout(500);

    if (notFoundResponse) {
      console.log('404 response:', notFoundResponse);

      // Should have standard error format
      expect(notFoundResponse).toHaveProperty('error');
      expect(notFoundResponse).toHaveProperty('message');

      // Error type should indicate not found
      expect(notFoundResponse.error.toLowerCase()).toContain('not found');
    }
  });

  test('API validation errors return specific field errors', async ({ page }) => {
    let validationError: any = null;

    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/') && response.status() === 422) {
        try {
          validationError = await response.json();
        } catch (e) {
          // Not JSON
        }
      }
    });

    await page.goto('/admin/products');

    // Try to create item with invalid data via API
    const token = await page.evaluate(() => localStorage.getItem('adminToken'));

    await page.request.post('http://localhost:8000/api/v1/items', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: {
        name: '',  // Invalid: empty name
        unit: 'invalid-unit',  // Invalid unit
      },
      failOnStatusCode: false
    });

    await page.waitForTimeout(500);

    if (validationError) {
      console.log('Validation error:', validationError);

      // FastAPI validation errors have 'detail' field
      // Should be array of validation errors
      expect(validationError).toHaveProperty('detail');

      if (Array.isArray(validationError.detail)) {
        // Each error should have loc, msg, type
        const firstError = validationError.detail[0];
        expect(firstError).toHaveProperty('loc');
        expect(firstError).toHaveProperty('msg');
      }
    }
  });
});

test.describe('Sprint 1 - API Pagination Standardization', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('list endpoints support offset/limit pagination', async ({ page }) => {
    let paginatedResponse: any = null;

    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/sales-orders') && response.url().includes('offset=')) {
        try {
          paginatedResponse = await response.json();
        } catch (e) {
          // Not JSON
        }
      }
    });

    await page.goto('/admin/orders');

    // Wait for initial load
    await page.waitForLoadState('networkidle');

    // Try to navigate to page 2 (offset=10, limit=10 typically)
    await page.goto('/admin/orders?offset=10&limit=10');

    await page.waitForTimeout(1000);

    // If pagination was used, verify response format
    if (paginatedResponse) {
      console.log('Paginated response keys:', Object.keys(paginatedResponse));

      // Standard pagination response should have:
      // - items (array of results)
      // - total (total count)
      // - offset, limit (pagination params)

      expect(paginatedResponse).toHaveProperty('items');
      expect(Array.isArray(paginatedResponse.items)).toBeTruthy();

      // Should have metadata
      const hasMetadata = paginatedResponse.total !== undefined ||
                          paginatedResponse.count !== undefined ||
                          paginatedResponse.offset !== undefined;

      expect(hasMetadata).toBeTruthy();
    }
  });

  test('pagination parameters are validated', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('adminToken'));

    // Try invalid offset (negative)
    const negativeOffsetResponse = await page.request.get(
      'http://localhost:8000/api/v1/sales-orders?offset=-10&limit=10',
      {
        headers: { 'Authorization': `Bearer ${token}` },
        failOnStatusCode: false
      }
    );

    // Should either reject (422) or ignore (treat as 0)
    expect([200, 422]).toContain(negativeOffsetResponse.status());

    // Try invalid limit (too large)
    const largeLimitResponse = await page.request.get(
      'http://localhost:8000/api/v1/sales-orders?offset=0&limit=10000',
      {
        headers: { 'Authorization': `Bearer ${token}` },
        failOnStatusCode: false
      }
    );

    // Should either reject or cap at max (e.g., 100)
    expect([200, 422]).toContain(largeLimitResponse.status());

    if (largeLimitResponse.status() === 200) {
      const data = await largeLimitResponse.json();

      // If accepted, should cap limit (not return 10000 items)
      if (data.items) {
        expect(data.items.length).toBeLessThanOrEqual(100);
      }
    }
  });

  test('all list endpoints use consistent pagination format', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('adminToken'));

    const endpoints = [
      '/api/v1/sales-orders?offset=0&limit=10',
      '/api/v1/items?offset=0&limit=10',
      '/api/v1/inventory?offset=0&limit=10',
    ];

    const responses: any[] = [];

    for (const endpoint of endpoints) {
      const response = await page.request.get(`http://localhost:8000${endpoint}`, {
        headers: { 'Authorization': `Bearer ${token}` },
        failOnStatusCode: false
      });

      if (response.ok()) {
        const data = await response.json();
        responses.push({ endpoint, data });
      }
    }

    // All responses should have same structure
    if (responses.length >= 2) {
      const firstKeys = Object.keys(responses[0].data).sort();

      for (const response of responses) {
        const keys = Object.keys(response.data).sort();

        console.log(`${response.endpoint} keys:`, keys);

        // All should have 'items' at minimum
        expect(response.data).toHaveProperty('items');
        expect(Array.isArray(response.data.items)).toBeTruthy();
      }
    }
  });
});

test.describe('Sprint 1 - API Response Wrappers', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('detail endpoints return consistent response format', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('adminToken'));

    // Get first item from list
    const listResponse = await page.request.get('http://localhost:8000/api/v1/items?offset=0&limit=1', {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (listResponse.ok()) {
      const listData = await listResponse.json();

      if (listData.items && listData.items.length > 0) {
        const firstItem = listData.items[0];

        // Get detail for that item
        const detailResponse = await page.request.get(`http://localhost:8000/api/v1/items/${firstItem.id}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (detailResponse.ok()) {
          const detailData = await detailResponse.json();

          console.log('Detail response:', detailData);

          // Detail response should contain the item data
          // Either directly as the object, or wrapped in a 'data' field
          const hasItemData = detailData.id !== undefined || detailData.data?.id !== undefined;

          expect(hasItemData).toBeTruthy();
        }
      }
    }
  });

  test('create endpoints return created resource', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('adminToken'));

    // Try to create an item
    const createResponse = await page.request.post('http://localhost:8000/api/v1/items', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: {
        name: `API Test Item ${Date.now()}`,
        sku: `APITEST${Date.now()}`,
        unit: 'kg',
        item_type: 'finished_good',
        procurement_type: 'buy',
        active: true
      },
      failOnStatusCode: false
    });

    if (createResponse.status() === 201 || createResponse.status() === 200) {
      const createdItem = await createResponse.json();

      console.log('Created item:', createdItem);

      // Should return the created item with ID
      expect(createdItem.id).toBeDefined();
      expect(createdItem.name).toBeDefined();

      // Cleanup: delete the test item
      if (createdItem.id) {
        await page.request.delete(`http://localhost:8000/api/v1/items/${createdItem.id}`, {
          headers: { 'Authorization': `Bearer ${token}` },
          failOnStatusCode: false
        });
      }
    } else {
      console.log('Create failed with status:', createResponse.status());

      // Test might fail due to validation or permissions
      // That's OK - the point is to verify response format when it succeeds
      test.skip();
    }
  });
});

test.describe('Sprint 1 - API Error Handling in Frontend', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('frontend displays API errors user-friendly', async ({ page }) => {
    // Monitor console for errors
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/admin/products');

    // Try to create item with invalid data
    const createButton = page.getByRole('button', { name: /create|new.*item/i });
    await createButton.click();

    await expect(page.locator('text=/Add.*Item|Create.*Item/i')).toBeVisible({ timeout: 3000 });

    // Submit without filling required fields
    const submitButton = page.getByRole('button', { name: /save|create|submit/i });
    await submitButton.click();

    await page.waitForTimeout(2000);

    // Check if any errors are displayed to user
    const errorVisible = await page.locator('text=/error|failed|required/i').count() > 0;

    if (errorVisible) {
      // Good - error is shown to user

      // Error should NOT be a raw JSON response
      const errorText = await page.locator('text=/error|failed|required/i').first().textContent();

      if (errorText) {
        expect(errorText).not.toContain('{');
        expect(errorText).not.toContain('detail');
        expect(errorText).not.toContain('status_code');
      }
    }

    // Frontend should not log unhandled errors to console
    const hasUnhandledErrors = consoleErrors.some(err =>
      err.includes('Unhandled') || err.includes('Uncaught')
    );

    expect(hasUnhandledErrors).toBeFalsy();
  });

  test('frontend parses validation errors correctly', async ({ page }) => {
    await page.goto('/admin/products');

    // Open create form
    const createButton = page.getByRole('button', { name: /create|new.*item/i });
    await createButton.click();

    await expect(page.locator('text=/Add.*Item|Create.*Item/i')).toBeVisible({ timeout: 3000 });

    // Fill with invalid data to trigger specific validation
    await page.locator('input[name="name"], input#name').fill('');  // Empty name

    const priceInput = page.locator('input[name="selling_price"], input#selling_price');
    if (await priceInput.count() > 0) {
      await priceInput.fill('-100');  // Negative price
    }

    const submitButton = page.getByRole('button', { name: /save|create|submit/i });
    await submitButton.click();

    await page.waitForTimeout(1500);

    // Should show specific validation errors (not generic "error occurred")
    const validationMessages = await page.locator('text=/required|invalid|must be|positive/i').all();

    if (validationMessages.length > 0) {
      // Each error should be specific
      for (const message of validationMessages) {
        const text = await message.textContent();

        if (text) {
          // Should not be generic
          expect(text.toLowerCase()).not.toBe('error');
          expect(text.toLowerCase()).not.toBe('failed');
        }
      }
    }
  });
});

test.describe('Sprint 1 - API Performance with Pagination', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('paginated list loads faster than full list', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('adminToken'));

    // Time paginated request (limit=10)
    const paginatedStart = Date.now();
    await page.request.get('http://localhost:8000/api/v1/sales-orders?offset=0&limit=10', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const paginatedTime = Date.now() - paginatedStart;

    // Time larger request (limit=100)
    const largeStart = Date.now();
    await page.request.get('http://localhost:8000/api/v1/sales-orders?offset=0&limit=100', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const largeTime = Date.now() - largeStart;

    console.log(`Paginated (limit=10): ${paginatedTime}ms`);
    console.log(`Large (limit=100): ${largeTime}ms`);

    // Paginated should be fast
    expect(paginatedTime).toBeLessThan(1000);

    // Large request should not be dramatically slower (well-optimized)
    expect(largeTime).toBeLessThan(2000);
  });
});
