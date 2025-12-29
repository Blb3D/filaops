# E2E-301: Fulfillment Flow Tests

**Ticket:** E2E-301  
**Status:** Not Started  
**Depends On:** All Week 4 tickets  
**Estimate:** 2-3 hours

---

## Purpose

End-to-end tests validating the fulfillment status feature works correctly in the browser.

---

## CRITICAL: Lessons from E2E-201

Before writing these tests, review what we learned:

### 1. Rate Limiting on Login

**Problem:** Backend limits `/api/v1/auth/login` to **5 requests per minute**.

**Solution:** 
- Seed ONCE in `beforeAll`
- Login ONCE per test (not multiple times)
- For API-only tests, use direct API auth (no browser)
- Combine related API tests into single test

### 2. Test Data Seeding

**Problem:** `cleanupTestData()` silently swallows errors. Repeated cleanup/seed cycles cause inconsistent state.

**Solution:**
```typescript
test.describe.serial('Suite Name', () => {
  test.beforeAll(async () => {
    await cleanupTestData();
    await seedTestScenario('scenario-name');
  });
  
  // All tests share the seeded data
});
```

### 3. Don't Use Shared Auth

Our tests seed their own users, so the global auth setup doesn't work.

```typescript
// At top of file
test.use({ storageState: { cookies: [], origins: [] } });
```

### 4. URL Patterns

- SO detail: `/admin/orders?so_id=123` (query param, not path)
- PO detail: `/admin/purchasing?po_id=123`
- Always check actual app behavior before asserting

### 5. Strict Mode

Playwright fails if selector matches multiple elements. Use:
- `.first()` for first match
- `{ name: 'View', exact: true }` for exact text
- More specific selectors

### 6. API Port

Backend runs on port **8000**, not 8001.

```typescript
// CORRECT
await request.get('http://127.0.0.1:8000/api/v1/...')

// WRONG
await request.get('http://127.0.0.1:8001/api/v1/...')
```

---

## Test File Structure

```typescript
// frontend/tests/e2e/flows/fulfillment.spec.ts

import { test, expect } from '@playwright/test';
import { seedTestScenario, cleanupTestData } from '../fixtures/test-utils';

// Don't use shared auth
test.use({ storageState: { cookies: [], origins: [] } });

test.describe.serial('E2E-301: Fulfillment Flow', () => {

  // Seed once before all tests
  test.beforeAll(async () => {
    await cleanupTestData();
    await seedTestScenario('low-stock-with-allocations');
  });

  // Helper: login via UI
  async function loginAsAdmin(page: any) {
    await page.goto('http://localhost:5173/admin/login');
    await page.getByRole('textbox', { name: 'Email Address' }).fill('admin@filaops.test');
    await page.getByRole('textbox', { name: 'Password' }).fill('TestPass123!');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/admin(?!\/login)/);
  }

  // Helper: get token via API
  async function getApiToken(request: any): Promise<string> {
    const response = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      form: {
        username: 'admin@filaops.test',
        password: 'TestPass123!',
      },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    return data.access_token;
  }

  // ====================
  // UI TESTS
  // ====================

  test('SO list shows fulfillment status cards', async ({ page }) => {
    // TODO: Implement after UI-303
  });

  test('filter buttons filter by fulfillment state', async ({ page }) => {
    // TODO: Implement after UI-303
  });

  test('sort dropdown changes order', async ({ page }) => {
    // TODO: Implement after UI-303
  });

  test('SO detail shows fulfillment progress', async ({ page }) => {
    // TODO: Implement after UI-302
  });

  test('ready order shows Ship Now button', async ({ page }) => {
    // TODO: Implement after UI-302
  });

  // ====================
  // API TESTS
  // ====================

  test('API-301 & API-302 & API-303: fulfillment endpoints work correctly', async ({ request }) => {
    const token = await getApiToken(request);

    // --- API-301: Single order fulfillment status ---
    const listResponse = await request.get('http://127.0.0.1:8000/api/v1/sales-orders/', {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    expect(listResponse.ok()).toBeTruthy();
    
    const orders = await listResponse.json();
    const soId = orders.items?.[0]?.id || orders[0]?.id;
    expect(soId).toBeTruthy();

    const statusResponse = await request.get(
      `http://127.0.0.1:8000/api/v1/sales-orders/${soId}/fulfillment-status`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    expect(statusResponse.ok()).toBeTruthy();

    const statusData = await statusResponse.json();
    expect(statusData).toHaveProperty('summary');
    expect(statusData.summary).toHaveProperty('state');
    expect(statusData.summary).toHaveProperty('lines_total');
    expect(statusData.summary).toHaveProperty('lines_ready');
    expect(statusData.summary).toHaveProperty('fulfillment_percent');
    expect(statusData).toHaveProperty('lines');
    expect(Array.isArray(statusData.lines)).toBe(true);

    // --- API-302: Bulk fulfillment in list ---
    const bulkResponse = await request.get(
      'http://127.0.0.1:8000/api/v1/sales-orders/?include_fulfillment=true',
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    expect(bulkResponse.ok()).toBeTruthy();

    const bulkData = await bulkResponse.json();
    expect(bulkData.items[0]).toHaveProperty('fulfillment');
    expect(bulkData.items[0].fulfillment).toHaveProperty('state');

    // --- API-303: Filtering by state ---
    const filteredResponse = await request.get(
      'http://127.0.0.1:8000/api/v1/sales-orders/?include_fulfillment=true&fulfillment_state=blocked',
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    expect(filteredResponse.ok()).toBeTruthy();

    const filteredData = await filteredResponse.json();
    // All returned items should be blocked (or empty if none match)
    for (const item of filteredData.items) {
      expect(item.fulfillment.state).toBe('blocked');
    }

    // --- API-303: Sorting by priority ---
    const sortedResponse = await request.get(
      'http://127.0.0.1:8000/api/v1/sales-orders/?include_fulfillment=true&sort_by=fulfillment_priority&sort_order=asc',
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    expect(sortedResponse.ok()).toBeTruthy();
    // First item should be most actionable (ready_to_ship or partially_ready)
  });

});
```

---

## Test Scenarios Needed

The existing `low-stock-with-allocations` scenario should work, but verify it creates:

1. At least one SO with ALL lines allocated (ready_to_ship)
2. At least one SO with SOME lines allocated (partially_ready)
3. At least one SO with NO allocations (blocked)

If not, create a new scenario:

```typescript
// Add to backend/tests/scenarios.py

async function seed_fulfillment_test_scenario(db):
    """
    Creates orders in various fulfillment states for testing.
    """
    # Create products
    product_a = create_product(db, sku="FIL-FULFILL-A")
    product_b = create_product(db, sku="FIL-FULFILL-B")
    
    # Create inventory
    inv_a = create_inventory(db, product_id=product_a.id, quantity=100)
    inv_b = create_inventory(db, product_id=product_b.id, quantity=5)  # Low stock
    
    customer = create_customer(db)
    
    # Order 1: Fully allocated (ready_to_ship)
    order1 = create_sales_order(db, customer_id=customer.id)
    line1 = create_so_line(db, order_id=order1.id, product_id=product_a.id, quantity=10)
    create_allocation(db, inventory_id=inv_a.id, so_line_id=line1.id, quantity=10)
    
    # Order 2: Partially allocated (partially_ready)
    order2 = create_sales_order(db, customer_id=customer.id)
    line2a = create_so_line(db, order_id=order2.id, product_id=product_a.id, quantity=10)
    line2b = create_so_line(db, order_id=order2.id, product_id=product_b.id, quantity=10)  # Not enough
    create_allocation(db, inventory_id=inv_a.id, so_line_id=line2a.id, quantity=10)
    create_allocation(db, inventory_id=inv_b.id, so_line_id=line2b.id, quantity=5)  # Only 5 of 10
    
    # Order 3: No allocations (blocked)
    order3 = create_sales_order(db, customer_id=customer.id)
    create_so_line(db, order_id=order3.id, product_id=product_b.id, quantity=50)  # Way more than available
```

---

## Running the Tests

```bash
cd frontend

# Run just fulfillment tests
npx playwright test fulfillment --retries=0

# Run with UI for debugging
npx playwright test fulfillment --ui

# Run specific test
npx playwright test -g "SO list shows fulfillment status cards"
```

---

## Common Failures and Solutions

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `Login failed` after 5th test | Rate limiting | Combine tests or seed once |
| `404` on API call | Wrong port OR wrong ID | Check port 8000, get ID from list first |
| `Strict mode violation` | Multiple matches | Use `.first()` or exact selector |
| `Timeout waiting for URL` | Page didn't navigate | Check if action is modal vs navigation |
| `Element not found` | Timing issue | Add `await expect(...).toBeVisible()` first |

---

## Definition of Done

- [ ] Test file created at `frontend/tests/e2e/flows/fulfillment.spec.ts`
- [ ] Uses `beforeAll` seeding pattern
- [ ] Uses `test.describe.serial`
- [ ] Doesn't exceed 5 logins per minute
- [ ] API tests use direct auth (no browser)
- [ ] UI tests validate card display
- [ ] UI tests validate filtering
- [ ] UI tests validate sorting
- [ ] UI tests validate detail view
- [ ] All tests passing locally
- [ ] No regressions in other E2E tests
