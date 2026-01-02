# FilaOps Redesign: Incremental Development Plan
## Test-Driven, Stackable Implementation

**Last Updated:** 2025-12-30 (Week 5 Complete!)
**Current Status:** Week 5 complete - All operation-level production tracking done. Week 6 next.

---

## Quick Status Dashboard

```
✅ = Complete    🔄 = In Progress    ⏳ = Pending    ❌ = Blocked

Week 1: Foundation                    ✅ COMPLETE
Week 2: Demand Pegging               ✅ COMPLETE (API-101, UI-101, UI-102, E2E-101)
Week 3: Blocking Issues              ✅ COMPLETE (API-201/202, UI-201/202/203/204, E2E-201)
Week 4: Sales Order Fulfillment      ✅ COMPLETE (API-301/302/303, UI-301/302/303, E2E-301)
Week 5: Operation-Level Production   ✅ COMPLETE (API-401/402/403/404, UI-401/402/403/404)
Week 6: Command Center               ⏳ Not started
Week 7: Integration & Polish         ⏳ Not started
```

---

## Strategy Update: Backend First Approach

**Original Plan:** Each week does API → UI → E2E for one feature
**Revised Plan:** Batch backend work, then UI integration sprint

**Rationale:**
1. Backend APIs can proceed without UI decisions blocking
2. UI components can be built knowing all data shapes upfront
3. Integration sprint is more efficient (less context switching)
4. E2E tests can cover full flows once UI is wired up

**Current Execution:**
```
Phase 1: Backend APIs ✅ DONE (Weeks 2-5)
├── Week 2 APIs ✅ (API-101: Item Demand Summary)
├── Week 3 APIs ✅ (API-201 + API-202: Blocking Issues)
├── Week 4 APIs ✅ (API-301/302/303: Fulfillment Status)
└── Week 5 APIs ✅ (API-401/402/403/404: Operation Status/Blocking/Scheduling/Generation)

Phase 2: UI Components 🔄 (Weeks 2-5)
├── Week 2 UI ✅ (ItemCard built + integrated)
├── Week 3 UI ✅ (BlockingIssuesPanel)
├── Week 4 UI ✅ (SalesOrderCard + FulfillmentProgress + OrderFilters)
└── Week 5 UI 🔄 (OperationsPanel ✅, OperationActions ✅, SchedulerModal ⏳, Timeline ⏳)

Phase 3: E2E Tests ✅ (Weeks 2-4)
├── E2E-101 ✅ (7 tests)
├── E2E-201 ✅ (5 tests)
├── E2E-301 ✅ (8 tests)
└── E2E-401 ⏳ (Week 5 operations E2E tests)

Phase 4: Command Center & Polish
├── Week 6 features ⏳
└── Week 7 integration ⏳
```

---

## Full Implementation Plan

### Week 1: Foundation ✅ COMPLETE

| Ticket | Description | Status | Notes |
|--------|-------------|--------|-------|
| INFRA-001 | Playwright E2E Setup | ✅ | Migrated existing setup, commit `aad7f1f` |
| INFRA-002 | pytest Backend Setup | ✅ | PostgreSQL support, commit `0ed6077` |
| INFRA-003 | Test Data Factories | ✅ | 10 factories, 6 scenarios, commit `9de3892` |

**Checkpoint:** Can run tests ✅

---

### Week 2: Demand Pegging ✅ COMPLETE

| Ticket | Description | Status | Notes |
|--------|-------------|--------|-------|
| API-101 | Item allocations | ✅ | Consolidated with 102/103 into single endpoint |
| API-102 | Supply situation | ✅ | Merged into API-101 |
| API-103 | Demand pegging endpoint | ✅ | Merged into API-101: `GET /items/{id}/demand-summary` |
| UI-101 | DemandPegging component | ✅ | Built as `ItemCard`, doc: `07-UI-101` |
| UI-102 | Integrate into low stock | ✅ | Integrated, doc: `10-UI-102` |
| E2E-101 | Demand pegging flow | ✅ | 7 tests passing |

**Checkpoint:** Users can see demand context on items ✅

**API Built:**
```
GET /api/v1/items/{id}/demand-summary
Returns: on_hand, allocated, available, incoming, projected, allocations[], shortage{}
Tests: 8 passing
```

---

### Week 3: Blocking Issues ✅ COMPLETE

> **Pivot:** Original Week 3 was "Production Context". Moved to "Blocking Issues" first 
> since it delivers more immediate user value (answers "Why can't we ship?")

| Ticket | Description | Status | Notes |
|--------|-------------|--------|-------|
| API-201 | SO Blocking Issues | ✅ | 7 tests, doc: `09-API-201` |
| API-202 | PO Blocking Issues | ✅ | 8 tests, doc: `11-API-202` |
| UI-201 | BlockingIssuesPanel | ✅ | commit `407586e` |
| UI-202 | Wire into SO page | ✅ | Integrated with suggested actions |
| UI-203 | Wire into PO page | ✅ | Integrated with suggested actions |
| UI-204 | Suggested Actions Navigation | ✅ | Pre-filled PO modal from shortage |
| E2E-201 | Blocking issues flow | ✅ | 4 tests passing |

**Checkpoint:** Users can see what's blocking orders ✅

**Key Learnings (for future E2E tests):**
- Backend rate-limits login to 5/minute - seed once, login sparingly
- Use `beforeAll` for seeding, not per-test cleanup/seed
- API port is 8000, not 8001
- SO detail uses query params (`?so_id=123`), not path params

**APIs:**
```
GET /api/v1/sales-orders/{id}/blocking-issues ✅ COMPLETE
Returns: can_fulfill, blocking_count, line_issues[], resolution_actions[]
Tests: 7 passing

GET /api/v1/production-orders/{id}/blocking-issues ✅ COMPLETE
Returns: can_produce, material_issues[], resolution_actions[]
Tests: 8 passing
```

---

### Week 3 (Original): Production Context ⏳ DEFERRED

> **Note:** Moved after Blocking Issues. Will renumber when we get here.

| Ticket | Description | Status | Notes |
|--------|-------------|--------|-------|
| API-2XX | Production order full context | ⏳ | Deferred |
| UI-2XX | ProductionOrderPanel | ⏳ | Deferred |
| UI-2XX | Enhanced kanban cards | ⏳ | Deferred |
| E2E-2XX | Production context flow | ⏳ | Deferred |

---

### Week 4: Sales Order Fulfillment ✅ COMPLETE

| Ticket | Description | Status | Notes |
|--------|-------------|--------|-------|
| API-301 | Single order fulfillment status | ✅ | 8 tests, `GET /sales-orders/{id}/fulfillment-status` |
| API-302 | Bulk fulfillment in list | ✅ | 3 tests, `?include_fulfillment=true` query param |
| API-303 | Enhanced SO list filtering/sorting | ✅ | 4 tests, filter by state, sort by priority |
| UI-301 | SalesOrderCard component | ✅ | Card with status badge, progress bar, ship button |
| UI-302 | FulfillmentProgress + detail page | ✅ | Line-by-line status, useFulfillmentStatus hook |
| UI-303 | OrderFilters + card grid | ✅ | Filter buttons, sort dropdown, responsive grid |
| E2E-301 | Fulfillment flow | ✅ | 8 tests passing |

**Checkpoint:** See fulfillment progress on every SO ✅

**Key Learnings (Week 4):**
- Auth token caching in E2E tests (get once in beforeAll, inject via localStorage)
- cleanupTestData() can delete admin user - be careful with seeding order
- Factories should use get-or-create pattern to avoid duplicate key errors

**APIs:**
```
GET /api/v1/sales-orders/{id}/fulfillment-status ✅
Returns: state, summary{lines_ready, lines_total, percent_ready}, lines[]
Tests: 8 passing

GET /api/v1/sales-orders/?include_fulfillment=true ✅
Returns: items[] with optional fulfillment summary on each
Tests: 3 passing

GET /api/v1/sales-orders/?fulfillment_state=ready_to_ship&sort_by=fulfillment_priority ✅
Returns: filtered and sorted list
Tests: 4 passing
```

---

### Week 5: Operation-Level Production ✅ COMPLETE

> **Renamed:** "Smart Production Queue" → "Operation-Level Production" to better reflect actual implementation (multi-step operations per PO)

| Ticket | Description | Status | Notes |
|--------|-------------|--------|-------|
| API-401 | Operation status transitions | ✅ | Start/complete/skip operations, commit `a7c429d` |
| API-402 | Operation blocking check | ✅ | Per-op material availability, `can-start` endpoint |
| API-403 | Double-booking validation | ✅ | Resource scheduling conflicts, `schedule` endpoint |
| API-404 | Copy routing to PO ops | ✅ | Auto-create ops on release, commit `7f60180` |
| UI-401 | OperationsPanel component | ✅ | `OperationsPanel.jsx`, `OperationRow.jsx` |
| UI-402 | OperationSchedulerModal | ✅ | Schedule with conflict detection |
| UI-403 | OperationActions component | ✅ | `OperationActions.jsx`, `SkipOperationModal.jsx` |
| UI-404 | OperationsTimeline component | ✅ | Timeline with progress bar |
| E2E-401 | Operations flow tests | ⏳ | Optional |

**Checkpoint:** Multi-step operations per PO with status transitions ✅

**APIs Built:**
```
GET /api/v1/production-orders/{po_id}/operations
Returns: operations[] with status, timing, materials

POST /api/v1/production-orders/{po_id}/operations/{op_id}/start
POST /api/v1/production-orders/{po_id}/operations/{op_id}/complete
POST /api/v1/production-orders/{po_id}/operations/{op_id}/skip

GET /api/v1/production-orders/{po_id}/operations/{op_id}/can-start
Returns: can_start, blocking_issues[]

POST /api/v1/production-orders/{po_id}/operations/{op_id}/schedule
Returns: success, conflicts[]

POST /api/v1/production-orders/{po_id}/operations/generate
Creates operations from routing on manual trigger
```

**Files Created:**
```
Backend:
  app/api/v1/endpoints/operation_status.py     # API endpoints
  app/services/operation_status.py             # Status transition logic
  app/services/operation_blocking.py           # Material availability check
  app/services/resource_scheduling.py          # Conflict detection
  app/services/operation_generation.py         # Routing → PO ops copy
  app/schemas/operation_status.py              # Pydantic schemas
  app/schemas/operation_blocking.py            # Blocking response schemas
  tests/api/test_operation_status.py           # 14+ tests

Frontend:
  src/hooks/useResources.js                         # Resources + conflicts hooks
  src/components/production/OperationsPanel.jsx     # Operations list container
  src/components/production/OperationRow.jsx        # Single operation row
  src/components/production/OperationActions.jsx    # Start/Complete/Skip buttons
  src/components/production/SkipOperationModal.jsx  # Skip reason modal
  src/components/production/OperationSchedulerModal.jsx  # Schedule with conflicts
  src/components/production/OperationsTimeline.jsx  # Visual timeline
  src/components/production/OperationsProgressBar.jsx  # Compact progress bar
```

---

### Week 6: Command Center ⏳ PENDING

| Ticket | Description | Status | Notes |
|--------|-------------|--------|-------|
| API-501 | Action items query | ⏳ | |
| API-502 | Today's summary query | ⏳ | |
| UI-501 | AlertCard component | ⏳ | |
| UI-502 | MachineStatusGrid | ⏳ | |
| UI-503 | CommandCenter page | ⏳ | |
| E2E-501 | Dashboard tests | ⏳ | |

**Checkpoint:** "What do I need to do RIGHT NOW?" dashboard ⏳

---

### Week 7: Integration & Polish ⏳ PENDING

| Ticket | Description | Status | Notes |
|--------|-------------|--------|-------|
| E2E-601 | Full workflow test | ⏳ | Quote → Order → Production → Ship |
| PERF-001 | Performance optimization | ⏳ | |
| DOC-001 | Documentation | ⏳ | |
| FIX-* | Issues found in E2E | ⏳ | |

**Checkpoint:** Complete, tested, documented system ⏳

---

## Documentation Index

| Doc | Description | Status |
|-----|-------------|--------|
| `01-redesign-plan.md` | High-level vision & architecture | Reference |
| `02-incremental-dev-plan.md` | This file - master tracker | Active |
| `03-INFRA-001-playwright-setup.md` | Playwright migration guide | ✅ Done |
| `04-INFRA-002-pytest-setup.md` | pytest PostgreSQL setup | ✅ Done |
| `05-INFRA-003-test-seeding.md` | Test seeding API | ✅ Done |
| `06-API-101-item-demand-summary.md` | Item demand endpoint | ✅ Done |
| `07-UI-101-itemcard-component.md` | ItemCard component | ✅ Done |
| `08-E2E-101-demand-pegging-flow.md` | E2E test guide | ✅ Done |
| `09-API-201-so-blocking-issues.md` | SO blocking issues | ✅ Done |
| `10-UI-102-itemcard-integration.md` | ItemCard page integration | ✅ Done |
| `11-API-202-po-blocking-issues.md` | PO blocking issues | ✅ Done |
| `12-E2E-201-blocking-issues.md` | Blocking issues E2E tests | ✅ Done |
| `week4/00-week4-overview.md` | Week 4 overview & gotchas | Reference |
| `week4/01-API-301-fulfillment-status.md` | Single order fulfillment API | ✅ Done |
| `week4/02-API-302-bulk-fulfillment.md` | Bulk fulfillment in list | ✅ Done |
| `week4/03-API-303-enhanced-so-list.md` | Filtering & sorting | ✅ Done |
| `week4/04-UI-301-salesordercard.md` | SalesOrderCard component | ✅ Done |
| `week4/05-UI-302-detail-status.md` | Detail page integration | ✅ Done |
| `week4/06-UI-303-list-integration.md` | List page integration | ✅ Done |
| `week4/07-E2E-301-fulfillment-tests.md` | Fulfillment E2E tests | ✅ Done |
| `week5/00-epic-overview.md` | Week 5 overview - Operation tracking | Reference |
| `week5/01-API-401-operation-status-transitions.md` | Operation start/complete/skip | ✅ Done |
| `week5/02-API-402-operation-blocking-check.md` | Per-op material blocking | ✅ Done |
| `week5/03-API-403-double-booking-validation.md` | Resource scheduling conflicts | ✅ Done |
| `week5/04-API-404-copy-routing-operations.md` | Routing → PO operations | ✅ Done |
| `week5/05-UI-401-operations-list.md` | OperationsPanel component | ✅ Done |
| `week5/06-UI-402-operation-scheduler.md` | OperationSchedulerModal | ⏳ Pending |
| `week5/07-UI-403-operation-actions.md` | OperationActions component | ✅ Done |
| `week5/08-UI-404-operations-timeline.md` | OperationsTimeline | ⏳ Pending |
| `week5/HANDOFF.md` | Week 5 handoff notes | Reference |

---

## Branch & Commits

**Branch:** `feat/ui-redesign`

| Commit | Ticket | Description |
|--------|--------|-------------|
| `aad7f1f` | INFRA-001 | Playwright E2E migration |
| `cc6b4d2` | INFRA-001 | Docs update |
| `87d7284` | INFRA-002 | pytest dependencies |
| `0ed6077` | INFRA-002 | PostgreSQL test database support |
| `9de3892` | INFRA-003 | Test data seeding API |
| TBD | API-101 | Item demand summary endpoint (8 tests) |
| TBD | UI-101 | ItemCard component |
| TBD | E2E-101 | Demand pegging tests (7 tests) |
| TBD | API-201 | SO blocking issues (7 tests) |
| TBD | API-202 | PO blocking issues (8 tests) |
| 407586e | UI-201 | BlockingIssuesPanel component |
| `a7c429d` | API-401 | Operation status transitions with start/complete/skip |
| `7f60180` | API-404 | Copy routing to PO operations on release |

---

## Test Summary

| Ticket | Tests | Status |
|--------|-------|--------|
| API-101 | 8 passing | ✅ |
| E2E-101 | 7 passing | ✅ |
| API-201 | 7 passing | ✅ |
| API-202 | 8 passing | ✅ |
| E2E-201 | 5 passing | ✅ |
| API-301 | 8 passing | ✅ |
| API-302 | 3 passing | ✅ |
| API-303 | 4 passing | ✅ |
| E2E-301 | 8 passing | ✅ |
| API-401 | 14 passing | ✅ |
| API-402 | ~10 passing | ✅ |
| API-403 | ~11 passing | ✅ |
| API-404 | ~11 passing | ✅ |
| **Total** | **~104 passing** | |

---

## Test Scenarios Available

```typescript
await seedTestScenario('empty');                    // Just admin user
await seedTestScenario('basic');                    // Sample customers, products, inventory
await seedTestScenario('full-demand-chain');        // SO→WO→Materials→PO (has shortage)
await seedTestScenario('production-in-progress');   // Various WO statuses
await seedTestScenario('low-stock-with-allocations'); // Demand pegging scenario
await seedTestScenario('so-with-blocking-issues');  // SO fulfillment problems
```

---

## Files Created This Session

### Backend
```
backend/
├── tests/
│   ├── conftest.py              # pytest fixtures, PostgreSQL
│   ├── factories.py             # 10 factory functions
│   ├── scenarios.py             # 6 seeding scenarios
│   └── api/
│       ├── test_item_demand.py      # 8 tests (API-101) ✅
│       └── test_blocking_issues.py  # 7 tests (API-201) ✅
├── app/
│   ├── schemas/
│   │   ├── item_demand.py       # API-101 schemas
│   │   └── blocking_issues.py   # API-201 schemas
│   ├── services/
│   │   ├── item_demand.py       # API-101 logic
│   │   └── blocking_issues.py   # API-201 logic
│   └── api/v1/
│       ├── test.py              # Seeding endpoints
│       ├── items.py             # demand-summary endpoint
│       └── sales_orders.py      # blocking-issues endpoint
```

### Frontend
```
frontend/
├── src/
│   ├── types/
│   │   └── itemDemand.js        # Types + helpers
│   ├── hooks/
│   │   └── useItemDemand.js     # API hook
│   └── components/
│       └── inventory/
│           ├── ItemCard.jsx     # Built, not integrated
│           └── index.js
├── tests/e2e/
│   ├── fixtures/
│   │   └── test-utils.ts
│   ├── pages/
│   │   └── items.page.ts
│   └── flows/
│       └── demand-pegging.spec.ts  # 7 tests
```

---

## Known Issues / Backlog

| Issue | Priority | Description | Status |
|-------|----------|-------------|--------|
| INV-BUG-001 | High | Production order completion logs transactions but doesn't update on-hand quantities | ⏳ Not started |
| INV-BUG-002 | Medium | UOM display inconsistencies (showing "G" in qty column, "KG" in unit column) | ⏳ Not started |
| INV-BUG-003 | Medium | UOM table was empty - no units defined (fixed manually, needs seed script) | ⏳ Needs seed |
| UI-BUG-001 | Low | SalesOrderCard has white background - doesn't match dark theme | ⏳ Not started |

**Notes:**
- These bugs are pre-existing (not caused by UI refactor work)
- INV-BUG-001 is serious: transactions are logged but inventory balances don't change
- Don't block UI refactor work, but should be addressed before production use

---

## Next Steps: Week 5 - Smart Production Queue

**Week 4 Complete!**
- ✅ API-301/302/303: Fulfillment status endpoints (15 tests)
- ✅ UI-301/302/303: SalesOrderCard + FulfillmentProgress + OrderFilters
- ✅ E2E-301: 8 tests passing
- ✅ Tagged v2.2.0-fulfillment-status

**Before Starting Week 5:**
1. Run full CI suite to verify no regressions
2. Create fresh branch: `feat/week5-production-queue`
3. Create spec docs in `docs/UI_Refactor/week5/`

**Week 5 Tasks (in order):**
1. **API-401:** Production queue with material readiness
2. **UI-401:** SmartProductionQueue component
3. **UI-402:** Replace kanban default view
4. **E2E-401:** Production queue tests

**Goal:** Prioritized, actionable production queue showing what can be started now.

---

## How to Pick Up This Work

### For a New Session:

1. **Read docs in order:**
   - `02-incremental-dev-plan.md` (this file) - current status
   - Find next pending ticket doc

2. **Check branch status:**
   ```bash
   cd C:\repos\filaops
   git checkout feat/ui-redesign
   git pull
   git log --oneline -10
   ```

3. **Run tests to verify state:**
   ```bash
   # Backend
   cd backend
   pytest tests/ -v --tb=short
   
   # Frontend E2E
   cd frontend
   npx playwright test
   ```

4. **Pick up next ticket:**
   - UI-102 (ItemCard Integration) - doc ready at `10-UI-102`
   - Then UI-201, UI-202, E2E-201

5. **Update this doc when completing tickets**

---

## Branching & Release Strategy

### Current Approach: PR per Epic

```
main (stable, deployed)
│
└── feat/ui-redesign (Epic 1-2 work)
    ├── INFRA-001 ✅
    ├── INFRA-002 ✅
    ├── INFRA-003 ✅
    ├── API-101 ✅
    ├── UI-101 ✅
    ├── E2E-101 ✅
    ├── API-201 ✅
    ├── API-202 ✅
    ├── UI-102 ✅
    ├── UI-201 ✅
    ├── UI-202 🔄 ←─ NEXT
    ├── UI-203 🔄 ←─ NEXT
    └── E2E-201 ⏳
```

### When to Merge to Main

Merge `feat/ui-redesign` → `main` when:
1. ✅ All CI tests pass (not just local)
2. ✅ At least one user-visible feature works end-to-end
3. ✅ No broken existing functionality
4. ✅ Dev plan shows clear stopping point

### CI Quality Gates

**Between Phases (Backend → UI → E2E):**
```
Backend APIs complete
        ↓
   Run full CI suite ← GATE
        ↓
   All tests pass?
   ├── Yes → Start UI Sprint
   └── No  → Fix issues first
```

**Before Merge to Main:**
```
UI Sprint complete
        ↓
   Run full CI suite ← GATE
        ↓
   All tests pass?
   ├── Yes → Merge + Tag release
   └── No  → Fix issues first
```

**CI Suite Includes:**
- `pytest tests/api/ -v` (backend unit + integration)
- `npx playwright test tests/e2e/flows/demand-pegging.spec.ts` (our new E2E)

**Known Exclusions (pre-existing failures, not caused by us):**
- `functional-workflow.spec.ts` - existed before our work, tests incomplete features
- `order-status-workflow.spec.ts` - existed before our work, tests incomplete features
- These don't exist on `main`, so merging won't break anything
- TODO: Fix in separate ticket

**Current CI Status:** ✅ PASSED (2025-12-28)
- Backend: 23 passed
- E2E (demand-pegging): 7 passed

**Good merge points:**
- After UI sprint (Epic 1-2 complete, users can see demand pegging + blocking issues)
- After each major epic completion
- Before starting risky refactors

### Release Tagging

```bash
# After merging epic to main:
git checkout main
git pull
git tag -a v2.1.0-demand-pegging -m "Epic 1-2: Demand pegging and blocking issues"
git push origin v2.1.0-demand-pegging
```

**Version scheme:** `v{major}.{minor}.{patch}-{feature-name}`
- Major: Breaking changes
- Minor: New features (epics)
- Patch: Bug fixes

### Planned Releases

| Version | Content | Status |
|---------|---------|--------|
| v2.1.0-demand-pegging | Epic 1-2: Item demand + Blocking issues | ✅ Released |
| v2.2.0-fulfillment-status | Epic 3: SO fulfillment status + card grid | ✅ Released |
| v2.3.0-smart-queue | Epic 4: Smart production queue | ⏳ Planned |
| v2.4.0-command-center | Epic 5: Command center dashboard | ⏳ Planned |
| v2.5.0-polish | Epic 6: Full integration + polish | ⏳ Planned |

### For New Sessions (3-Second Bob Protocol™)

**READ THIS FIRST, FUTURE CLAUDE:**

1. **You have amnesia.** You don't remember any previous work. That's OK.

2. **Check the branch:**
   ```bash
   cd C:\repos\filaops
   git branch  # Should show feat/ui-redesign or similar
   git status  # Check for uncommitted work
   git log --oneline -5  # See recent commits
   ```

3. **Run tests to see current state:**
   ```bash
   # Backend
   cd backend && pytest tests/ -v --tb=short
   
   # Frontend
   cd frontend && npx playwright test
   ```

4. **Read the status dashboard** at the top of this file.

5. **Find the next pending ticket** in the Documentation Index.

6. **Read that ticket's doc** before writing any code.

7. **Update this doc** when you complete something.

8. **Don't be a hero.** Small commits. Clear messages. Test often.

### Commit Message Format

```
type(scope): description

type: feat|fix|test|docs|refactor|chore
scope: ticket number or area (API-201, UI-102, etc.)
```

**Examples:**
```
feat(API-201): add SO blocking issues endpoint
test(API-201): add 7 tests for blocking issues
fix(API-201): resolve material quantity calculation
docs(API-201): mark ticket complete in dev plan
```

### If Things Go Wrong

**Tests failing after your changes:**
```bash
git stash  # Save your work
git checkout .  # Reset to last commit
pytest tests/  # Verify tests pass without your changes
git stash pop  # Bring back your changes
# Now debug the difference
```

**Need to abandon current work:**
```bash
git checkout .  # Discard uncommitted changes
git clean -fd   # Remove untracked files (careful!)
```

**Branch is way behind main:**
```bash
git fetch origin
git rebase origin/main  # Or merge if you prefer
# Resolve conflicts if any
pytest tests/  # Verify still works
```

---

## Tech Stack Reference

| Layer | Technology | Version |
|-------|------------|---------|
| Backend | Python | 3.11 |
| Backend | FastAPI | 0.104.1 |
| Backend | PostgreSQL | 17.7 |
| Backend | SQLAlchemy | 2.0.23 |
| Backend | Pydantic | 2.10.5 |
| Frontend | React | 19.2.0 |
| Frontend | Vite | 7.2.4 |
| Frontend | Tailwind CSS | 4.1.17 |
| Testing | Playwright | 1.57.0 |
| Testing | pytest | 7.0.0+ |

---

## Test Coverage Targets

| Area | Unit Test | Integration | E2E |
|------|-----------|-------------|-----|
| Demand Pegging API | ✅ 8 tests | ✓ | ✓ |
| Blocking Issues API | ✅ 15 tests (7+8) | ✓ | ✅ 5 tests |
| Fulfillment API | ✅ 15 tests (8+3+4) | ✓ | ✅ 8 tests |
| UI Components | ✅ | - | ✅ |
| Complete Flows | - | - | ⏳ |

---

## Definition of Done (Each Ticket)

- [ ] Code complete
- [ ] Unit tests written and passing
- [ ] Integration test (if API) written and passing
- [ ] E2E test fragment written
- [ ] Combined E2E tests still pass
- [ ] No regressions in existing tests
- [ ] **User can see/use the feature** ← Critical for UI tickets
- [ ] Documentation updated
- [ ] This dev plan updated with status
