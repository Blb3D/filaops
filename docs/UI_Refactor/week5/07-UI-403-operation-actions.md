# UI-403: Operation Action Buttons

## Status: ✅ IMPLEMENTED (2025-12-30)

---

## Agent Instructions

- Execute steps IN ORDER - do not skip ahead
- Create ONLY the files listed - no extras
- Use EXACT code provided - do not "improve" it
- Match existing button patterns exactly
- Run the app and verify visually after each step
- Commit with the EXACT message provided

⚠️ DO NOT:
- Modify files outside the explicit list
- Add new npm dependencies without approval
- Change button styling from existing patterns
- "Optimize" or refactor unrelated code
- Skip visual verification

---

## Overview

**Goal:** Start, Complete, and Skip buttons for individual operations  
**Outcome:** Users can transition operations through their lifecycle with proper validation

---

## Design Reference

```
Operation Row with Actions:
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ● 10: PRINT - 3D Print                    🔵 Pending              │
│    └─ Printer P1S-01 │ Est: 4h 15m                                 │
│                                                                     │
│    [ ▶ Start ]  [ ⊘ Skip ]                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Running Operation:
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ● 10: PRINT - 3D Print                    🟣 Running   2h 15m     │
│    └─ Printer P1S-01 │ Started: 9:00 AM                            │
│                                                                     │
│    [ ✓ Complete ]                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Action Matrix

| Current Status | Available Actions | API Endpoint |
|----------------|-------------------|--------------|
| `pending` | Start, Skip | POST `/start`, POST `/skip` |
| `queued` | Start, Skip | POST `/start`, POST `/skip` |
| `running` | Complete | POST `/complete` |
| `complete` | None | - |
| `skipped` | None | - |

---

## Validation Before Start

Before starting an operation, check:

1. **Previous operation complete** (via API-401)
2. **Materials available** (via API-402)
3. **Resource not busy** (via API-403)

The Start button should show a loading state while checking, then either proceed or show an error modal.

---

## Skip Reason Modal

When skipping an operation, prompt for a reason:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Skip Operation                                                  ✕   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Are you sure you want to skip this operation?                      │
│                                                                     │
│  Operation: 20 - CLEAN (Post-Print Clean)                          │
│                                                                     │
│  Reason for skipping: *                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Customer requested rush delivery                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ⚠️ Skipped operations cannot be undone.                            │
│                                                                     │
│                                      [ Cancel ]  [ Skip ]           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Execution

---

### Step 1 of 5: Create OperationActions Component

**Agent:** Frontend Agent  
**Time:** 25 minutes  
**Directory:** `frontend/src/components/production/`

**File to Create:** `frontend/src/components/production/OperationActions.jsx`
```jsx
/**
 * OperationActions - Action buttons for an operation
 *
 * Shows Start/Complete/Skip buttons based on operation status.
 * Handles API calls and validation.
 */
import { useState } from 'react';
import { API_URL } from '../../config/api';

/**
 * Start button with blocking check
 */
function StartButton({ operation, productionOrderId, onSuccess, onError }) {
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem('adminToken');

  const handleStart = async () => {
    setLoading(true);
    try {
      // First check if operation can start (blocking issues)
      const checkRes = await fetch(
        `${API_URL}/api/v1/production-orders/${productionOrderId}/operations/${operation.id}/can-start`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (checkRes.ok) {
        const checkData = await checkRes.json();
        if (!checkData.can_start) {
          // Show blocking issues
          const issues = checkData.blocking_issues || [];
          const issueText = issues.map(i => `${i.product_sku}: need ${i.quantity_short} more`).join(', ');
          onError?.(`Cannot start: ${issueText || 'Materials not available'}`);
          setLoading(false);
          return;
        }
      }

      // Proceed with start
      const res = await fetch(
        `${API_URL}/api/v1/production-orders/${productionOrderId}/operations/${operation.id}/start`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            resource_id: operation.resource_id || null
          })
        }
      );

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to start operation');
      }

      onSuccess?.('Operation started');
    } catch (err) {
      onError?.(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleStart}
      disabled={loading}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-600/30 disabled:opacity-50 transition-colors"
    >
      {loading ? (
        <>
          <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-blue-400"></div>
          Checking...
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M6.3 2.841A1.5 1.5 0 004 4.11v11.78a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
          </svg>
          Start
        </>
      )}
    </button>
  );
}

/**
 * Complete button
 */
function CompleteButton({ operation, productionOrderId, onSuccess, onError }) {
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem('adminToken');

  const handleComplete = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/production-orders/${productionOrderId}/operations/${operation.id}/complete`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({})
        }
      );

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to complete operation');
      }

      onSuccess?.('Operation completed');
    } catch (err) {
      onError?.(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleComplete}
      disabled={loading}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-green-600/20 text-green-400 border border-green-500/30 rounded-lg hover:bg-green-600/30 disabled:opacity-50 transition-colors"
    >
      {loading ? (
        <>
          <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-green-400"></div>
          Saving...
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Complete
        </>
      )}
    </button>
  );
}

/**
 * Skip button (opens modal)
 */
function SkipButton({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-yellow-600/20 text-yellow-400 border border-yellow-500/30 rounded-lg hover:bg-yellow-600/30 transition-colors"
    >
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
      </svg>
      Skip
    </button>
  );
}

/**
 * Main component - shows appropriate buttons based on status
 */
export default function OperationActions({
  operation,
  productionOrderId,
  onSuccess,
  onError,
  onSkipClick
}) {
  if (!operation) return null;

  const { status } = operation;

  // No actions for completed or skipped
  if (['complete', 'skipped'].includes(status)) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 mt-2">
      {/* Pending/Queued: Start and Skip */}
      {['pending', 'queued'].includes(status) && (
        <>
          <StartButton
            operation={operation}
            productionOrderId={productionOrderId}
            onSuccess={onSuccess}
            onError={onError}
          />
          <SkipButton onClick={() => onSkipClick?.(operation)} />
        </>
      )}

      {/* Running: Complete only */}
      {status === 'running' && (
        <CompleteButton
          operation={operation}
          productionOrderId={productionOrderId}
          onSuccess={onSuccess}
          onError={onError}
        />
      )}
    </div>
  );
}
```

**Verification:**
- [ ] File created
- [ ] No import errors

**Commit Message:** `feat(UI-403): add OperationActions component`

---

### Step 2 of 5: Create SkipOperationModal

**Agent:** Frontend Agent  
**Time:** 20 minutes  
**Directory:** `frontend/src/components/production/`

**File to Create:** `frontend/src/components/production/SkipOperationModal.jsx`
```jsx
/**
 * SkipOperationModal - Confirmation modal for skipping an operation
 *
 * Requires a reason before skipping.
 */
import { useState } from 'react';
import { API_URL } from '../../config/api';

export default function SkipOperationModal({
  isOpen,
  onClose,
  operation,
  productionOrderId,
  onSkipped
}) {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const token = localStorage.getItem('adminToken');

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!reason.trim()) {
      setError('Please provide a reason for skipping');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_URL}/api/v1/production-orders/${productionOrderId}/operations/${operation.id}/skip`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ reason: reason.trim() })
        }
      );

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to skip operation');
      }

      onSkipped?.();
      handleClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setReason('');
    setError(null);
    onClose();
  };

  if (!isOpen || !operation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md mx-4 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <h2 className="text-xl font-semibold text-white">Skip Operation</h2>
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
          <p className="text-gray-300">
            Are you sure you want to skip this operation?
          </p>

          {/* Operation info */}
          <div className="bg-gray-800/50 rounded-lg p-4">
            <div className="text-white font-medium">
              {operation.sequence}: {operation.operation_code}
            </div>
            {operation.operation_name && (
              <div className="text-gray-400 text-sm">{operation.operation_name}</div>
            )}
          </div>

          {/* Reason input */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Reason for skipping <span className="text-red-400">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder="e.g., Customer requested rush delivery, Operation not needed for this order..."
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:ring-2 focus:ring-yellow-500 focus:border-transparent resize-none"
            />
          </div>

          {/* Warning */}
          <div className="flex items-start gap-2 text-yellow-400/70 text-sm">
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>Skipped operations cannot be undone.</span>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !reason.trim()}
              className="px-6 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? 'Skipping...' : 'Skip Operation'}
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

**Commit Message:** `feat(UI-403): add SkipOperationModal component`

---

### Step 3 of 5: Update OperationRow to Include Actions

**Agent:** Frontend Agent  
**Time:** 15 minutes  
**File to Modify:** `frontend/src/components/production/OperationRow.jsx`

**Add import at top:**
```jsx
import OperationActions from './OperationActions';
```

**Update the component to accept and pass action handlers:**

Update the component signature:
```jsx
export default function OperationRow({
  operation,
  isActive,
  productionOrderId,
  onActionSuccess,
  onActionError,
  onSkipClick,
  onClick
}) {
```

Add OperationActions inside the component, after the expanded details section:
```jsx
      {/* Action buttons */}
      {productionOrderId && (
        <OperationActions
          operation={operation}
          productionOrderId={productionOrderId}
          onSuccess={onActionSuccess}
          onError={onActionError}
          onSkipClick={onSkipClick}
        />
      )}
```

**Full updated return statement:**
```jsx
  return (
    <div
      className={`
        group p-3 rounded-lg border transition-all
        ${isActive ? 'border-purple-500/50 bg-purple-500/5' : 'border-gray-800 bg-gray-900/50'}
        ${isClickable ? 'cursor-pointer hover:border-gray-700 hover:bg-gray-800/50' : ''}
        ${operation.status === 'complete' ? 'opacity-75' : ''}
        ${operation.status === 'skipped' ? 'opacity-50' : ''}
      `}
      onClick={isClickable ? () => onClick(operation) : undefined}
    >
      <div className="flex items-center justify-between">
        {/* ... existing left/right content ... */}
      </div>

      {/* Expanded details for running operation */}
      {operation.status === 'running' && (
        <div className="mt-3 pt-3 border-t border-gray-800 flex items-center justify-between">
          <div className="text-xs text-gray-500">
            Started: {operation.actual_start ? formatTime(operation.actual_start) : 'Just now'}
          </div>
          <div className="text-xs text-purple-400">
            ● In Progress
          </div>
        </div>
      )}

      {/* Show skip reason if skipped */}
      {operation.status === 'skipped' && operation.notes && (
        <div className="mt-2 text-xs text-yellow-400/70 italic">
          Skipped: {operation.notes}
        </div>
      )}

      {/* Action buttons */}
      {productionOrderId && (
        <OperationActions
          operation={operation}
          productionOrderId={productionOrderId}
          onSuccess={onActionSuccess}
          onError={onActionError}
          onSkipClick={onSkipClick}
        />
      )}
    </div>
  );
```

**Verification:**
- [ ] Import added
- [ ] Props passed correctly
- [ ] Actions render in row

**Commit Message:** `feat(UI-403): integrate OperationActions into OperationRow`

---

### Step 4 of 5: Update OperationsPanel with Action Handling

**Agent:** Frontend Agent  
**Time:** 15 minutes  
**File to Modify:** `frontend/src/components/production/OperationsPanel.jsx`

**Add import:**
```jsx
import SkipOperationModal from './SkipOperationModal';
```

**Add state for skip modal (after existing useState declarations):**
```jsx
  const [skipModalOpen, setSkipModalOpen] = useState(false);
  const [operationToSkip, setOperationToSkip] = useState(null);
```

**Add handlers (after fetchOperations function):**
```jsx
  const handleActionSuccess = (message) => {
    // Refresh operations after action
    fetchOperations();
    // Toast handled by parent
  };

  const handleActionError = (message) => {
    // Could show inline error or let parent handle
    console.error('Operation action error:', message);
  };

  const handleSkipClick = (operation) => {
    setOperationToSkip(operation);
    setSkipModalOpen(true);
  };
```

**Update OperationRow rendering to pass new props:**
```jsx
            <OperationRow
              key={operation.id}
              operation={operation}
              isActive={activeOperation?.id === operation.id}
              productionOrderId={productionOrderId}
              onActionSuccess={handleActionSuccess}
              onActionError={handleActionError}
              onSkipClick={handleSkipClick}
              onClick={onOperationClick}
            />
```

**Add SkipOperationModal at end of component (before final closing div):**
```jsx
      {/* Skip Operation Modal */}
      <SkipOperationModal
        isOpen={skipModalOpen}
        onClose={() => {
          setSkipModalOpen(false);
          setOperationToSkip(null);
        }}
        operation={operationToSkip}
        productionOrderId={productionOrderId}
        onSkipped={() => {
          fetchOperations();
        }}
      />
```

**Verification:**
- [ ] Import added
- [ ] State added
- [ ] Handlers implemented
- [ ] Props passed to OperationRow
- [ ] Modal rendered

**Commit Message:** `feat(UI-403): add skip modal and action handling to OperationsPanel`

---

### Step 5 of 5: Update Index Exports

**Agent:** Frontend Agent  
**Time:** 5 minutes  
**File to Modify:** `frontend/src/components/production/index.js`

**Update exports:**
```javascript
/**
 * Production components exports
 */
export { default as OperationRow } from './OperationRow';
export { default as OperationsPanel } from './OperationsPanel';
export { default as OperationSchedulerModal } from './OperationSchedulerModal';
export { default as OperationActions } from './OperationActions';
export { default as SkipOperationModal } from './SkipOperationModal';
```

**Verification:**
- [ ] Exports updated
- [ ] No import errors from other files

**Commit Message:** `chore(UI-403): export action components`

---

## Final Checklist

- [ ] All 5 steps executed in order
- [ ] Start button appears for pending operations
- [ ] Start checks materials before proceeding
- [ ] Complete button appears for running operations
- [ ] Skip button opens modal with reason input
- [ ] Actions refresh the operations list
- [ ] Error messages display properly

---

## Visual Verification

1. Navigate to a PO with operations
2. Verify Start button shows on pending operations
3. Click Start - verify loading state shows
4. If blocked, verify error message displays
5. If successful, verify operation transitions to running
6. Verify Complete button shows on running operation
7. Click Skip on pending - verify modal opens
8. Submit skip - verify operation shows as skipped

---

## Handoff to Next Ticket

**UI-404: Operations Timeline View**
- Visual timeline/Gantt of operations
- Shows scheduled vs actual times
- Color-coded by status
- Drag to reschedule (optional)
