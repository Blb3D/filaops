# Week 5: Operation-Level Production Tracking

## Status: ✅ COMPLETE

> **Updated 2025-12-30:** All backend APIs and UI components implemented.

---

## Epic Overview

Transform FilaOps from single-step production orders to true multi-operation routing execution. This enables real manufacturing workflows like Print → Clean → Assemble → QC → Pack/Ship.

---

## Problem Statement

**Current State:**
- Production orders treated as single task
- Completing PO marks everything done (skips intermediate ops)
- Scheduler books entire PO to one resource
- Material blocking checks ALL BOM items upfront
- Double-booking resources is possible
- No progress visibility during production
- 2-hour hardcoded duration ignores BOM/routing times

**Real World Workflow:**
```
PO: Make Gadget Pro (50 units)
├── Op 10: Print       → Printer-01, 4 hrs, consumes PLA
├── Op 20: Clean       → Finishing, 30 min
├── Op 30: Assemble    → Assembly, 1 hr, consumes hardware kit
├── Op 40: QC Inspect  → QC Station, 15 min
└── Op 50: Pack/Ship   → Shipping, 10 min, consumes boxes
```

**Key Insight:** Shipping boxes not received yet? **Start printing anyway** - they'll arrive by the time we get to Op 50.

---

## Week 5 Deliverables

### Backend (API-401 → API-404) - ALL COMPLETE ✅

| Ticket | File | Status | Description |
|--------|------|--------|-------------|
| **API-401** | `01-API-401-operation-status-transitions.md` | ✅ DONE | Start/complete/skip operations |
| **API-402** | `02-API-402-operation-blocking-check.md` | ✅ DONE | Per-operation material blocking |
| **API-403** | `03-API-403-double-booking-validation.md` | ✅ DONE | Resource scheduling conflicts |
| **API-404** | `04-API-404-copy-routing-operations.md` | ✅ DONE | Auto-create ops from routing |

### Frontend (UI-401 → UI-404) - ALL COMPLETE ✅

| Ticket | File | Status | Description |
|--------|------|--------|-------------|
| **UI-401** | `05-UI-401-operations-list.md` | ✅ DONE | Operations list in PO detail |
| **UI-402** | `06-UI-402-operation-scheduler.md` | ✅ DONE | Scheduler modal with conflicts |
| **UI-403** | `07-UI-403-operation-actions.md` | ✅ DONE | Start/Complete/Skip buttons |
| **UI-404** | `08-UI-404-operations-timeline.md` | ✅ DONE | Visual timeline/progress |

---

## Implementation Order

### Phase 1: Backend Foundation
```
API-401 ✅ → API-402 → API-403 → API-404
```

### Phase 2: Frontend Components
```
UI-401 → UI-402 → UI-403 → UI-404
```

### Phase 3: Integration Testing
```
E2E-401 (manual verification or Playwright)
```

---

## Key Files Created/Modified

### Backend
| Path | Description |
|------|-------------|
| `backend/app/services/operation_status.py` | Status transition logic |
| `backend/app/services/operation_blocking.py` | Material availability check |
| `backend/app/services/resource_scheduling.py` | Conflict detection |
| `backend/app/services/operation_generation.py` | Routing → PO ops copy |
| `backend/app/api/v1/endpoints/operation_status.py` | API endpoints |
| `backend/tests/api/test_operation_*.py` | Test suites |

### Frontend
| Path | Description |
|------|-------------|
| `frontend/src/components/production/OperationsPanel.jsx` | Main operations list |
| `frontend/src/components/production/OperationRow.jsx` | Single operation row |
| `frontend/src/components/production/OperationActions.jsx` | Action buttons |
| `frontend/src/components/production/OperationSchedulerModal.jsx` | Scheduling modal |
| `frontend/src/components/production/OperationsTimeline.jsx` | Visual timeline |
| `frontend/src/hooks/useResources.js` | Resource data hook |

---

## Success Criteria

1. ✅ Operations have status transitions (pending → running → complete)
2. ✅ Can define routing with 5 operations for a product
3. ✅ Releasing PO creates operation records (API-404)
4. ✅ Starting Op 1 sets PO to in_progress
5. ✅ Completing Op 1 auto-advances current to Op 2
6. ✅ Materials for Op 3 don't block starting Op 1 (API-402)
7. ✅ Cannot schedule two operations on same resource at same time (API-403)
8. ⏳ Progress bar shows operation status (UI-404 pending)
9. ✅ PO only complete when final operation complete

---

## Operation Status Flow
```
pending → queued → running → complete
                      ↓
                   skipped (with reason)
```

## PO Status Derived from Operations

| Condition | PO Status |
|-----------|-----------|
| All ops `pending` | `released` |
| Any op `running`, not all done | `in_progress` |
| All ops `complete` or `skipped` | `complete` |

---

## Technical Notes

### Consume Stage Mapping (API-402)
| consume_stage | Operation Codes | Materials |
|---------------|-----------------|-----------|
| `production` | PRINT, EXTRUDE | Filament, raw materials |
| `assembly` | ASSEMBLE, BUILD | Hardware, subassemblies |
| `shipping` | PACK, SHIP | Boxes, labels, packaging |

### Conflict Detection (API-403)
```python
# Two operations conflict if:
# - Same resource_id
# - Time ranges overlap: (start1 < end2) AND (start2 < end1)
# - Neither is in terminal state (complete, skipped, cancelled)
```

---

## Out of Scope (Future)

- Parallel operations (print two parts simultaneously)
- Operation-level labor time tracking
- Automated Bambu status sync to operation progress
- Rework routing (failed QC → back to earlier op)
- Gantt drag-drop rescheduling

---

## Dependencies

- ✅ Routing data exists for test products
- ✅ Work centers configured with resources
- ✅ UOM table seeded (completed Week 4)
