# UI-402: Operation Scheduler Modal

## Status: ✅ IMPLEMENTED (2025-12-30)

---

## Agent Instructions

- Execute steps IN ORDER - do not skip ahead
- Create ONLY the files listed - no extras
- Use EXACT code provided - do not "improve" it
- Match existing modal patterns exactly
- Run the app and verify visually after each step
- Commit with the EXACT message provided

⚠️ DO NOT:
- Modify files outside the explicit list
- Add new npm dependencies without approval
- Change modal behavior patterns from existing modals
- "Optimize" or refactor unrelated code
- Skip visual verification

---

## Overview

**Goal:** Modal for scheduling an operation on a specific resource and time slot  
**Outcome:** Users can assign operations to printers/machines with conflict detection

---

## Design Reference

```
┌─────────────────────────────────────────────────────────────────────┐
│ Schedule Operation                                              ✕   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Operation: 10 - PRINT (3D Print)                                   │
│  Production Order: PO-2025-0089                                     │
│  Estimated Duration: 4h 15m                                         │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Resource *                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Select a printer...                                     ▼   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Start Time *                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 2025-01-15T09:00                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  End Time (auto-calculated)                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 2025-01-15T13:15                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ⚠️ CONFLICT DETECTED                                        │   │
│  │                                                              │   │
│  │ This time slot overlaps with:                                │   │
│  │ • PO-2025-0087 - PRINT (9:00 - 12:30)                       │   │
│  │                                                              │   │
│  │ Adjust the start time or select a different resource.       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│                                      [ Cancel ]  [ Schedule ]       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

```
OperationSchedulerModal.jsx (new)
├── ResourceSelector (dropdown of available resources)
├── DateTimePicker (start time)
├── ConflictAlert (shows overlapping operations)
└── ScheduleButton (disabled when conflicts exist)
```

---

## API Dependencies

| Endpoint | Purpose |
|----------|---------|
| GET `/resources` | Load available resources/machines |
| GET `/resources/{id}/conflicts?start=&end=` | Check for conflicts |
| POST `/production-orders/{po_id}/operations/{op_id}/schedule` | Submit schedule |

---

## Step-by-Step Execution

---

### Step 1 of 4: Create useResources Hook

**Agent:** Frontend Agent  
**Time:** 15 minutes  
**Directory:** `frontend/src/hooks/`

**File to Create:** `frontend/src/hooks/useResources.js`
```javascript
/**
 * Hook for fetching available resources/machines
 */
import { useState, useEffect } from 'react';
import { API_URL } from '../config/api';

export function useResources(workCenterId = null) {
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const token = localStorage.getItem('adminToken');

  useEffect(() => {
    const fetchResources = async () => {
      if (!token) {
        setError('Not authenticated');
        setLoading(false);
        return;
      }

      try {
        let url = `${API_URL}/api/v1/resources`;
        if (workCenterId) {
          url += `?work_center_id=${workCenterId}`;
        }

        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!res.ok) throw new Error('Failed to fetch resources');

        const data = await res.json();
        // Handle both array and paginated response
        setResources(Array.isArray(data) ? data : data.items || data.resources || []);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchResources();
  }, [token, workCenterId]);

  return { resources, loading, error };
}

/**
 * Hook for checking resource conflicts
 */
export function useResourceConflicts(resourceId, startTime, endTime) {
  const [conflicts, setConflicts] = useState([]);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState(null);

  const token = localStorage.getItem('adminToken');

  useEffect(() => {
    const checkConflicts = async () => {
      if (!resourceId || !startTime || !endTime) {
        setConflicts([]);
        return;
      }

      setChecking(true);
      try {
        const params = new URLSearchParams({
          start: new Date(startTime).toISOString(),
          end: new Date(endTime).toISOString()
        });

        const res = await fetch(
          `${API_URL}/api/v1/resources/${resourceId}/conflicts?${params}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );

        if (!res.ok) throw new Error('Failed to check conflicts');

        const data = await res.json();
        setConflicts(data.conflicts || []);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setChecking(false);
      }
    };

    // Debounce the conflict check
    const timer = setTimeout(checkConflicts, 300);
    return () => clearTimeout(timer);
  }, [token, resourceId, startTime, endTime]);

  return { conflicts, checking, error, hasConflicts: conflicts.length > 0 };
}
```

**Verification:**
- [ ] File created
- [ ] No import errors

**Commit Message:** `feat(UI-402): add useResources and useResourceConflicts hooks`

---

### Step 2 of 4: Create OperationSchedulerModal

**Agent:** Frontend Agent  
**Time:** 30 minutes  
**Directory:** `frontend/src/components/production/`

**File to Create:** `frontend/src/components/production/OperationSchedulerModal.jsx`
```jsx
/**
 * OperationSchedulerModal - Schedule an operation on a resource
 *
 * Allows selecting resource and time slot with conflict detection.
 */
import { useState, useEffect } from 'react';
import { API_URL } from '../../config/api';
import { useResources, useResourceConflicts } from '../../hooks/useResources';
import { formatDuration } from '../../utils/formatting';

/**
 * Conflict alert banner
 */
function ConflictAlert({ conflicts }) {
  if (!conflicts || conflicts.length === 0) return null;

  return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <svg className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div className="flex-1">
          <h4 className="text-red-400 font-medium">Conflict Detected</h4>
          <p className="text-sm text-red-400/70 mt-1">
            This time slot overlaps with:
          </p>
          <ul className="mt-2 space-y-1">
            {conflicts.map((conflict, idx) => (
              <li key={idx} className="text-sm text-red-300">
                • {conflict.production_order_code} - {conflict.operation_code || 'Operation'}
                {conflict.scheduled_start && (
                  <span className="text-red-400/50">
                    {' '}({new Date(conflict.scheduled_start).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} -
                    {' '}{new Date(conflict.scheduled_end).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })})
                  </span>
                )}
              </li>
            ))}
          </ul>
          <p className="text-xs text-red-400/50 mt-2">
            Adjust the start time or select a different resource.
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Main modal component
 */
export default function OperationSchedulerModal({
  isOpen,
  onClose,
  operation,
  productionOrder,
  onScheduled
}) {
  const [resourceId, setResourceId] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const token = localStorage.getItem('adminToken');

  // Get available resources for the operation's work center
  const { resources, loading: loadingResources } = useResources(operation?.work_center_id);

  // Check for conflicts
  const { conflicts, checking, hasConflicts } = useResourceConflicts(
    resourceId ? parseInt(resourceId) : null,
    startTime,
    endTime
  );

  // Calculate estimated duration
  const estimatedMinutes = operation
    ? (operation.planned_setup_minutes || 0) + (operation.planned_run_minutes || 0)
    : 0;

  // Auto-calculate end time when start time changes
  useEffect(() => {
    if (startTime && estimatedMinutes > 0) {
      const start = new Date(startTime);
      const end = new Date(start.getTime() + estimatedMinutes * 60000);
      setEndTime(end.toISOString().slice(0, 16)); // Format for datetime-local input
    }
  }, [startTime, estimatedMinutes]);

  // Set default start time to now (rounded to next 15 min)
  useEffect(() => {
    if (isOpen && !startTime) {
      const now = new Date();
      now.setMinutes(Math.ceil(now.getMinutes() / 15) * 15, 0, 0);
      setStartTime(now.toISOString().slice(0, 16));
    }
  }, [isOpen, startTime]);

  // Pre-select resource if operation already has one
  useEffect(() => {
    if (isOpen && operation?.resource_id) {
      setResourceId(String(operation.resource_id));
    }
  }, [isOpen, operation]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!resourceId || !startTime || !endTime) {
      setError('Please fill in all required fields');
      return;
    }

    if (hasConflicts) {
      setError('Cannot schedule with conflicts. Please resolve conflicts first.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_URL}/api/v1/production-orders/${productionOrder.id}/operations/${operation.id}/schedule`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            resource_id: parseInt(resourceId),
            scheduled_start: new Date(startTime).toISOString(),
            scheduled_end: new Date(endTime).toISOString()
          })
        }
      );

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to schedule operation');
      }

      onScheduled?.();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setResourceId('');
    setStartTime('');
    setEndTime('');
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg mx-4 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <h2 className="text-xl font-semibold text-white">Schedule Operation</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Operation info */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-white">
              <span className="font-medium">{operation?.sequence}:</span>
              <span>{operation?.operation_code}</span>
              {operation?.operation_name && (
                <span className="text-gray-400">({operation.operation_name})</span>
              )}
            </div>
            <div className="text-sm text-gray-500">
              Production Order: {productionOrder?.code}
            </div>
            <div className="text-sm text-gray-500">
              Estimated Duration: {formatDuration(estimatedMinutes)}
            </div>
          </div>

          <hr className="border-gray-800" />

          {/* Resource selector */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Resource <span className="text-red-400">*</span>
            </label>
            <select
              value={resourceId}
              onChange={(e) => setResourceId(e.target.value)}
              disabled={loadingResources}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">
                {loadingResources ? 'Loading...' : 'Select a resource...'}
              </option>
              {resources.map((resource) => (
                <option key={resource.id} value={resource.id}>
                  {resource.code} - {resource.name}
                </option>
              ))}
            </select>
          </div>

          {/* Start time */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Start Time <span className="text-red-400">*</span>
            </label>
            <input
              type="datetime-local"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* End time (auto-calculated) */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              End Time
              <span className="text-gray-600 font-normal ml-2">(auto-calculated)</span>
            </label>
            <input
              type="datetime-local"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Conflict alert */}
          {checking ? (
            <div className="text-sm text-gray-500 flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
              Checking for conflicts...
            </div>
          ) : (
            <ConflictAlert conflicts={conflicts} />
          )}

          {/* Error message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          <hr className="border-gray-800" />

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || hasConflicts || !resourceId || !startTime}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? 'Scheduling...' : 'Schedule'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

**Verification:**
- [ ] File created
- [ ] No import errors

**Commit Message:** `feat(UI-402): add OperationSchedulerModal component`

---

### Step 3 of 4: Export from Index

**Agent:** Frontend Agent  
**Time:** 5 minutes  
**File to Modify:** `frontend/src/components/production/index.js`

**Update to include new component:**
```javascript
/**
 * Production components exports
 */
export { default as OperationRow } from './OperationRow';
export { default as OperationsPanel } from './OperationsPanel';
export { default as OperationSchedulerModal } from './OperationSchedulerModal';
```

**Verification:**
- [ ] Export added
- [ ] No import errors

**Commit Message:** `chore(UI-402): export OperationSchedulerModal`

---

### Step 4 of 4: Integrate into ProductionOrderDetail

**Agent:** Frontend Agent  
**Time:** 15 minutes  
**File to Modify:** `frontend/src/pages/admin/ProductionOrderDetail.jsx`

**Update import:**
```jsx
import { OperationsPanel, OperationSchedulerModal } from '../../components/production';
```

**Add state for modal (after existing useState declarations):**
```jsx
  const [schedulerOpen, setSchedulerOpen] = useState(false);
  const [selectedOperation, setSelectedOperation] = useState(null);
```

**Update OperationsPanel onClick handler:**
```jsx
      <OperationsPanel
        productionOrderId={order.id}
        orderStatus={order.status}
        onOperationClick={(operation) => {
          if (operation.status === 'pending') {
            setSelectedOperation(operation);
            setSchedulerOpen(true);
          }
        }}
      />
```

**Add modal at end of component (before final closing `</div>`):**
```jsx
      {/* Operation Scheduler Modal */}
      <OperationSchedulerModal
        isOpen={schedulerOpen}
        onClose={() => {
          setSchedulerOpen(false);
          setSelectedOperation(null);
        }}
        operation={selectedOperation}
        productionOrder={order}
        onScheduled={() => {
          toast.success('Operation scheduled successfully');
          fetchOrder();
        }}
      />
```

**Verification:**
- [ ] Import updated
- [ ] State added
- [ ] Modal renders
- [ ] Clicking pending operation opens scheduler
- [ ] Scheduling works (if API is implemented)

**Commit Message:** `feat(UI-402): integrate OperationSchedulerModal into ProductionOrderDetail`

---

## Final Checklist

- [ ] All 4 steps executed in order
- [ ] Modal opens when clicking pending operation
- [ ] Resources load in dropdown
- [ ] Start/end time picker works
- [ ] Conflict detection shows warnings
- [ ] Schedule button disabled when conflicts exist
- [ ] Successful scheduling closes modal and refreshes

---

## API Notes

If the resources endpoint returns empty or doesn't exist yet, the modal will still work but show "Select a resource..." with no options. The agent should verify the endpoint exists first.

If `/resources/{id}/conflicts` isn't implemented yet (API-403), the conflict checking will fail silently and no conflicts will show.

---

## Handoff to Next Ticket

**UI-403: Operation Action Buttons**
- Start, Complete, Skip buttons for operations
- Validates material availability before start (API-402)
- Shows confirmation before skip with reason input
