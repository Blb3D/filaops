# FilaOps Testing Guidelines

> **AI ASSISTANTS: Read this before writing ANY test code.**
> This document defines testing standards. Following these patterns is MANDATORY.

---

## Scope: Core ERP (Open Source)

Tests in this repo cover the **core ERP system**. The quote engine, ML pricing, and BambuStudio integration are in the Pro version (separate repo).

### What to Test (Core ERP)

| Module | Backend Tests | E2E Tests | Priority |
|--------|---------------|-----------|----------|
| Auth (login, tokens) | ✅ `tests/unit/test_auth.py` | ✅ `e2e/fixtures/auth.ts` | DONE |
| Customers | `tests/integration/test_customers.py` | `e2e/tests/customers.spec.ts` | HIGH |
| Orders | `tests/integration/test_orders.py` | `e2e/tests/orders.spec.ts` | HIGH |
| Items/Products | `tests/integration/test_items.py` | `e2e/tests/items.spec.ts` | HIGH |
| BOMs | `tests/integration/test_boms.py` | `e2e/tests/bom.spec.ts` | HIGH |
| Production Orders | `tests/integration/test_production.py` | `e2e/tests/production.spec.ts` | MEDIUM |
| Inventory | `tests/integration/test_inventory.py` | `e2e/tests/inventory.spec.ts` | MEDIUM |
| Vendors | `tests/integration/test_vendors.py` | `e2e/tests/vendors.spec.ts` | MEDIUM |
| Purchase Orders | `tests/integration/test_purchase_orders.py` | `e2e/tests/purchase-orders.spec.ts` | MEDIUM |
| Work Centers | `tests/integration/test_work_centers.py` | - | LOW |
| Routings | `tests/integration/test_routings.py` | - | LOW |
| Traceability | `tests/integration/test_traceability.py` | - | LOW |

### What NOT to Test Here (Pro Version)

- Quote engine / file upload / slicing
- ML pricing algorithms
- BambuStudio CLI integration
- Multi-material color detection
- Stripe payment processing
- Customer quote portal flow

---

## Core Philosophy

### 1. Tests Own Their Data

Every test creates what it needs in `beforeEach` / fixtures and cleans up in `afterEach`.

```python
# ✅ GOOD - test creates what it needs
def test_create_order_with_customer(client, db_session):
    # ARRANGE - create test data
    customer = create_test_customer(db_session)
    product = create_test_product(db_session)
    
    # ACT
    response = client.post("/api/v1/sales-orders/", json={
        "user_id": customer.id,
        "product_id": product.id,
        "quantity": 5
    })
    
    # ASSERT
    assert response.status_code == 201
    assert response.json()["quantity"] == 5
```

```python
# ❌ BAD - checks if data exists, skips if not
def test_create_order(client):
    response = client.get("/api/v1/customers/")
    if len(response.json()) == 0:
        pytest.skip("No customers")  # NEVER DO THIS
    # ...
```

### 2. Fail Loudly

If a precondition isn't met, the test FAILS. No silent skips, no defensive returns.

```typescript
// ✅ GOOD - fail if precondition not met
test('should edit customer', async ({ authenticatedPage: page }) => {
  // Create customer first via API
  const customer = await createTestCustomer();
  
  await page.goto(`/admin/customers/${customer.id}/edit`);
  await page.fill('[name="company"]', 'Updated Company');
  await page.click('button[type="submit"]');
  
  await expect(page.locator('text=Updated Company')).toBeVisible();
});
```

```typescript
// ❌ BAD - silent escape
test('should edit customer', async ({ authenticatedPage: page }) => {
  await page.goto('/admin/customers');
  const editButton = page.locator('button:has-text("Edit")').first();
  
  if (!(await editButton.isVisible())) {
    return;  // NEVER DO THIS - you just passed a test that tested nothing
  }
  // ...
});
```

### 3. Test Behavior, Not Implementation

Test what the user sees and does, not CSS classes or internal state.

```typescript
// ✅ GOOD - tests user-visible behavior
await expect(page.locator('[data-testid="order-status"]')).toHaveText('Confirmed');
await expect(page.locator('text=Order created successfully')).toBeVisible();

// ❌ BAD - tests implementation details
await expect(page.locator('.bg-green-500.text-white.px-4')).toBeVisible();
await expect(page.locator('div.order-card')).toHaveClass(/confirmed/);
```

---

## Backend Tests (pytest)

### File Structure

```
backend/tests/
├── conftest.py              # Shared fixtures (db_session, client, users)
├── unit/
│   ├── test_auth.py         # ✅ EXISTS - password hashing, JWT tokens
│   ├── test_bom_costing.py  # BOM cost calculations
│   └── test_inventory.py    # Inventory math (reservations, consumption)
├── integration/
│   ├── test_customers.py    # Customer CRUD API
│   ├── test_orders.py       # Sales order CRUD API
│   ├── test_items.py        # Product/Item CRUD API
│   ├── test_boms.py         # BOM CRUD API
│   ├── test_production.py   # Production order lifecycle
│   ├── test_inventory.py    # Inventory transactions API
│   ├── test_vendors.py      # Vendor CRUD API
│   ├── test_purchase_orders.py  # PO CRUD API
│   └── test_traceability.py # Lots, serials, recall queries
```

### Existing Fixtures (conftest.py)

Use these - don't recreate them:

```python
# Users
admin_user        # Admin account (account_type="admin")
customer_user     # Customer account with customer_number
admin_headers     # {"Authorization": "Bearer <token>"}
customer_headers  # {"Authorization": "Bearer <token>"}

# Products
sample_product    # Finished good (sku="TEST-PROD-001")
sample_material   # Raw material (sku="MAT-TEST-PLA")
sample_box        # Packaging (sku="PKG-BOX-4X4")

# BOM
sample_bom        # BOM with material + box lines

# Orders
sample_quote      # Pending quote
sample_sales_order # Confirmed order
```

### Integration Test Pattern

```python
# tests/integration/test_customers.py
import pytest
from tests.conftest import testData

class TestCustomerCRUD:
    """Customer API integration tests"""
    
    def test_create_customer(self, client, admin_headers):
        """Admin can create a new customer"""
        response = client.post(
            "/api/v1/customers/",
            json={
                "email": f"test-{testData.unique_id()}@example.com",
                "first_name": "Test",
                "last_name": "Customer",
                "company": "Test Corp"
            },
            headers=admin_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"].startswith("test-")
        assert data["customer_number"].startswith("CUST-")
    
    def test_create_customer_duplicate_email_fails(self, client, admin_headers, customer_user):
        """Creating customer with duplicate email returns 400"""
        response = client.post(
            "/api/v1/customers/",
            json={"email": customer_user.email},
            headers=admin_headers
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    def test_list_customers_requires_auth(self, client):
        """Listing customers without auth returns 401"""
        response = client.get("/api/v1/customers/")
        assert response.status_code == 401
    
    def test_list_customers_as_admin(self, client, admin_headers, customer_user):
        """Admin can list all customers"""
        response = client.get("/api/v1/customers/", headers=admin_headers)
        
        assert response.status_code == 200
        customers = response.json()
        assert len(customers) >= 1
        assert any(c["email"] == customer_user.email for c in customers)
```

### What Makes a Good Backend Test

| ✅ DO | ❌ DON'T |
|-------|----------|
| Use fixtures for test data | Query DB to "find" existing data |
| Assert specific status codes | Assert `response.ok` |
| Check response body content | Only check status code |
| Test error cases explicitly | Only test happy path |
| Use `admin_headers` fixture | Manually create tokens |
| Clean up in fixture teardown | Leave test data behind |

---

## Frontend E2E Tests (Playwright)

### File Structure

```
frontend/e2e/
├── fixtures/
│   ├── auth.ts              # ✅ EXISTS - authenticatedPage fixture
│   ├── api.ts               # API helpers for test data seeding
│   └── testData.ts          # Test data generators
├── tests/
│   ├── customers.spec.ts    # ✅ EXISTS
│   ├── orders.spec.ts       # ✅ EXISTS  
│   ├── items.spec.ts        # Product/Item management
│   ├── bom.spec.ts          # BOM management
│   ├── production.spec.ts   # Production order workflow
│   ├── inventory.spec.ts    # Inventory management
│   ├── vendors.spec.ts      # Vendor management
│   └── purchase-orders.spec.ts  # PO workflow
```

### API Fixture for Data Seeding

Create `frontend/e2e/fixtures/api.ts`:

```typescript
import { APIRequestContext } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';

export class TestAPI {
  constructor(private request: APIRequestContext, private adminToken: string) {}

  async createCustomer(data?: Partial<Customer>): Promise<Customer> {
    const response = await this.request.post(`${API_BASE}/customers/`, {
      headers: { Authorization: `Bearer ${this.adminToken}` },
      data: {
        email: `test-${Date.now()}@example.com`,
        first_name: 'Test',
        last_name: 'Customer',
        ...data
      }
    });
    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  async createProduct(data?: Partial<Product>): Promise<Product> {
    const response = await this.request.post(`${API_BASE}/items/`, {
      headers: { Authorization: `Bearer ${this.adminToken}` },
      data: {
        sku: `TEST-${Date.now()}`,
        name: 'Test Product',
        category: 'Finished Goods',
        selling_price: 29.99,
        ...data
      }
    });
    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  async createOrder(customerId: number, productId: number, quantity = 1): Promise<Order> {
    const response = await this.request.post(`${API_BASE}/sales-orders/`, {
      headers: { Authorization: `Bearer ${this.adminToken}` },
      data: {
        user_id: customerId,
        product_id: productId,
        quantity
      }
    });
    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  async deleteCustomer(id: number): Promise<void> {
    await this.request.delete(`${API_BASE}/customers/${id}`, {
      headers: { Authorization: `Bearer ${this.adminToken}` }
    });
  }
}
```

### E2E Test Pattern

```typescript
// e2e/tests/orders.spec.ts
import { test, expect } from '../fixtures/auth';
import { TestAPI } from '../fixtures/api';

test.describe('Order Management', () => {
  let api: TestAPI;
  let testCustomer: Customer;
  let testProduct: Product;

  test.beforeAll(async ({ request }) => {
    // Get admin token
    const loginResponse = await request.post('http://localhost:8000/api/v1/auth/login', {
      data: { email: 'admin@localhost', password: 'admin123' }
    });
    const { access_token } = await loginResponse.json();
    api = new TestAPI(request, access_token);
  });

  test.beforeEach(async () => {
    // Seed test data via API - NOT UI
    testCustomer = await api.createCustomer();
    testProduct = await api.createProduct();
  });

  test.afterEach(async () => {
    // Cleanup
    if (testCustomer?.id) await api.deleteCustomer(testCustomer.id);
  });

  test('create order with seeded customer and product', async ({ authenticatedPage: page }) => {
    await page.goto('/admin/orders');
    await page.click('button:has-text("Create Order")');
    
    // Select our seeded customer
    await page.selectOption('[data-testid="customer-select"]', { label: testCustomer.email });
    
    // Select our seeded product
    await page.selectOption('[data-testid="product-select"]', { label: testProduct.name });
    
    await page.fill('[data-testid="quantity-input"]', '5');
    await page.click('button[type="submit"]');
    
    // ASSERT - order created successfully
    await expect(page.locator('.fixed')).not.toBeVisible({ timeout: 5000 }); // Modal closed
    await expect(page.locator(`text=${testCustomer.email}`)).toBeVisible();
    await expect(page.locator('text=5')).toBeVisible(); // Quantity
  });
});
```

### Data-Testid Conventions

Add these to UI components for stable selectors:

```
# Customer Management
customer-table
customer-row-{id}
customer-add-btn
customer-edit-btn
customer-delete-btn
customer-email-input
customer-save-btn

# Order Management  
order-table
order-row-{id}
order-create-btn
customer-select
product-select
quantity-input
order-status-badge
order-advance-btn

# Item/Product Management
item-table
item-row-{id}
item-add-btn
sku-input
name-input
category-select
price-input

# BOM Management
bom-table
bom-row-{id}
bom-add-line-btn
component-select
quantity-input
bom-total-cost

# Production
production-queue
production-row-{id}
start-production-btn
printer-select
complete-btn
qty-good-input
qty-bad-input
```

---

## Anti-Patterns (NEVER DO THESE)

| Pattern | Why It's Bad | Do This Instead |
|---------|--------------|-----------------|
| `if (!element) return` | Silent pass on failure | `expect(element).toBeVisible()` |
| `if (count === 0) skip()` | Hides missing test data | Seed data in beforeEach |
| `await page.waitForTimeout(1000)` | Flaky, slow | Use `waitForLoadState` or `expect().toBeVisible()` |
| `test.skip(true, 'no data')` | Test does nothing useful | Seed the data you need |
| Check only page loads | Proves nothing | Assert on content/state |
| `expect(response.ok)` | Doesn't catch wrong status | `expect(response.status).toBe(201)` |
| Hardcoded IDs | Breaks between runs | Use fixture-created data |

---

## Running Tests

### Backend

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific file
pytest tests/integration/test_orders.py

# Run specific test
pytest tests/integration/test_orders.py::TestOrderCRUD::test_create_order

# Verbose output
pytest -v
```

### Frontend E2E

```bash
cd frontend

# Run all E2E tests
npm run test:e2e

# Run specific test file
npm run test:e2e -- --grep "orders"

# Run with UI (debugging)
npm run test:e2e -- --ui

# Run headed (watch browser)
npm run test:e2e -- --headed

# Update snapshots
npm run test:e2e -- --update-snapshots
```

---

## Checklist Before Writing a Test

1. ☐ What user behavior am I testing?
2. ☐ What data does this test need?
3. ☐ How do I seed that data (API fixture, not UI)?
4. ☐ What assertion proves the feature works?
5. ☐ How do I clean up after?
6. ☐ Does this test fail if the feature is broken?

If you can't answer #6 with "yes", the test isn't ready.

---

## When AI Writes Tests

If you're an AI assistant writing tests for FilaOps:

1. **Read this file first** - don't deviate from these patterns
2. **Use existing fixtures** - check `conftest.py` and `fixtures/` before creating new ones
3. **Seed via API** - never rely on existing database state
4. **Assert meaningfully** - if the test passes when the feature is broken, it's useless
5. **No defensive escapes** - if data is missing, FAIL, don't skip
6. **Test error cases** - 400s, 401s, 404s, validation failures
7. **Keep tests focused** - one behavior per test, not mega-tests
