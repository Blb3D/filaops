# Week 4: Sales Order Fulfillment - Overview

**Status:** Not Started  
**Prerequisites:** Week 3 complete, merged to main, tagged v2.1.0-demand-pegging  
**Branch:** `feat/week4-fulfillment`

---

## Goal

Answer the question: **"What's the status of this order and what do I need to do to ship it?"**

Week 3 told us what's BLOCKING an order. Week 4 tells us what's the OVERALL STATUS and PROGRESS toward fulfillment.

---

## User Stories

1. **As an operator**, I want to see at a glance which orders are ready to ship, which are in progress, and which are blocked.

2. **As an operator**, I want to see fulfillment progress (e.g., "3 of 5 lines ready") without opening each order.

3. **As an operator**, I want the SO list sorted by actionability - orders I can act on NOW at the top.

---

## Tickets

| Ticket | Description | Depends On | Deliverables |
|--------|-------------|------------|--------------|
| API-301 | Fulfillment status endpoint | None | Endpoint + schema + tests |
| API-302 | Bulk fulfillment status | API-301 | Endpoint for list view |
| API-303 | Enhanced SO list endpoint | API-302 | Sorting/filtering by status |
| UI-301 | SalesOrderCard component | API-302 | React component |
| UI-302 | SO detail status display | API-301 | Integrate into detail page |
| UI-303 | SO list with status cards | UI-301 | Replace current list |
| E2E-301 | Fulfillment flow tests | All above | Playwright tests |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     SO List Page                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │
│  │ SalesOrderCard  │ │ SalesOrderCard  │ │ SalesOrderCard│ │
│  │ ● Ready to Ship │ │ ● In Progress   │ │ ● Blocked     │ │
│  │ 5/5 lines ready │ │ 3/5 lines ready │ │ 0/5 lines     │ │
│  │ [Ship Now]      │ │ [View Details]  │ │ [View Issues] │ │
│  └─────────────────┘ └─────────────────┘ └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    API-302: GET /sales-orders/
                    ?include_fulfillment=true
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   SO Detail Page                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Fulfillment Status: IN PROGRESS (3/5 lines ready)      ││
│  │ ═══════════════════════════░░░░░░░░░░ 60%              ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Blocking Issues Panel (from Week 3)                    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    API-301: GET /sales-orders/{id}/fulfillment-status
```

---

## Fulfillment Status States

| Status | Meaning | Color | Priority |
|--------|---------|-------|----------|
| `ready_to_ship` | All lines have sufficient inventory allocated | Green | 1 (top) |
| `partially_ready` | Some lines ready, some blocked | Yellow | 2 |
| `blocked` | No lines can be fulfilled | Red | 3 |
| `shipped` | Already shipped | Gray | 4 (bottom) |
| `cancelled` | Order cancelled | Gray | 5 |

---

## Key Metrics Per Order

1. **lines_total** - Total line items on order
2. **lines_ready** - Lines with sufficient allocated inventory
3. **lines_blocked** - Lines with shortages
4. **fulfillment_percent** - (lines_ready / lines_total) * 100
5. **estimated_ship_date** - Based on incoming supply (if blocked)
6. **blocking_reasons** - Summary of what's blocking (links to Week 3 API)

---

## File Locations

```
Backend:
  app/schemas/fulfillment_status.py      # New - Pydantic models
  app/services/fulfillment_status.py     # New - Business logic
  app/api/v1/endpoints/sales_orders.py   # Modify - Add endpoints
  tests/api/test_fulfillment_status.py   # New - pytest tests

Frontend:
  src/components/orders/SalesOrderCard.jsx        # New
  src/components/orders/FulfillmentProgress.jsx   # New  
  src/hooks/useFulfillmentStatus.js               # New
  src/pages/admin/AdminOrders.jsx                 # Modify
  src/pages/admin/OrderDetail.jsx                 # Modify
  tests/e2e/flows/fulfillment.spec.ts             # New
```

---

## Known Gotchas

### 1. Rate Limiting on Login
The backend rate-limits `/api/v1/auth/login` to **5 requests per minute**.

**For E2E tests:**
- Do NOT login separately for each test
- Use `beforeAll` to seed once, login once per describe block
- Or use direct API token auth (see E2E-201 for example)

### 2. Test Data Seeding
- Always call `cleanupTestData()` before `seedTestScenario()`
- Cleanup silently swallows errors - don't trust it
- Seed ONCE in `beforeAll`, not per-test
- Use `test.describe.serial` if tests share state

### 3. URL Patterns
- SO detail uses query params: `/admin/orders?so_id=123`
- NOT path params: `/admin/orders/123`
- Check actual app behavior before writing URL assertions

### 4. Strict Mode Violations
- Playwright fails if selector matches multiple elements
- Use `.first()`, `.nth(0)`, or more specific selectors
- Common culprits: "View" buttons, status badges, "short" text

---

## Execution Order

1. API-301 first (single order endpoint)
2. API-302 second (bulk endpoint, uses 301 logic)
3. API-303 third (list filtering, uses 302)
4. UI-301 (component, needs 302 response shape)
5. UI-302 (detail page, needs 301)
6. UI-303 (list page, needs 301 + UI-301)
7. E2E-301 last (needs everything)

---

## Definition of Done

Each ticket must have:
- [ ] Implementation complete
- [ ] Unit/integration tests passing
- [ ] No regressions in existing tests
- [ ] Documentation in this folder
- [ ] Dev plan updated with status

Week 4 complete when:
- [ ] All 7 tickets done
- [ ] Full CI suite passes
- [ ] User can see fulfillment status on SO list and detail pages
- [ ] Ready to merge to main

---

## Documents in This Folder

| File | Content |
|------|---------|
| `00-week4-overview.md` | This file |
| `01-API-301-fulfillment-status.md` | Single order endpoint spec |
| `02-API-302-bulk-fulfillment.md` | Bulk endpoint spec |
| `03-API-303-enhanced-so-list.md` | List filtering spec |
| `04-UI-301-salesordercard.md` | Component spec |
| `05-UI-302-detail-status.md` | Detail page integration |
| `06-UI-303-list-integration.md` | List page integration |
| `07-E2E-301-fulfillment-tests.md` | E2E test spec |
