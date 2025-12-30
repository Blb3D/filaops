# UI-401: PO Detail Operations List

## Status: NOT STARTED

---

## Agent Instructions

- Execute steps IN ORDER - do not skip ahead
- Create ONLY the files listed - no extras
- Use EXACT code provided - do not "improve" it
- Match existing component patterns exactly
- Run the app and verify visually after each step
- Commit with the EXACT message provided

⚠️ DO NOT:
- Modify files outside the explicit list
- Add new npm dependencies without approval
- Change the existing ProductionOrderDetail layout structure
- "Optimize" or refactor unrelated code
- Skip visual verification

---

## Overview

**Goal:** Display operation sequence on the PO detail page  
**Outcome:** Users see all operations (PRINT → CLEAN → QC → PACK) with status, progress, and timing

---

## Design Reference

```
┌─────────────────────────────────────────────────────────────────────┐
│ Operations                                                    ↻     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ● 10: PRINT - 3D Print                    🟢 Complete    4h 12m   │
│    └─ Printer P1S-01 │ Setup: 5m │ Run: 4h 7m                      │
│                                                                     │
│  ○ 20: CLEAN - Post-Print Clean            🔵 Running     0:23     │
│    └─ Finishing Station │ Est: 30m                                  │
│                                                                     │
│  ○ 30: QC - Quality Check                  ⚪ Pending     -        │
│    └─ QC Station │ Est: 15m                                         │
│                                                                     │
│  ○ 40: PACK - Package & Ship               ⚪ Pending     -        │
│    └─ Shipping │ Est: 10m                                           │
│                                                                     │
│  ────────────────────────────────────────────────────────────────   │
│  Total: 4h 35m elapsed │ ~55m remaining                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

```
ProductionOrderDetail.jsx (existing)
└── OperationsPanel.jsx (new)
    ├── OperationRow.jsx (new)
    │   ├── StatusBadge
    │   ├── TimingInfo
    │   └── ActionButtons (→ UI-403)
    └── OperationsSummary.jsx (new)
```

---

## Step-by-Step Execution

---

### Step 1 of 5: Create OperationRow Component

**Agent:** Frontend Agent  
**Time:** 20 minutes  
**Directory:** `frontend/src/components/production/`

**File to Create:** `frontend/src/components/production/OperationRow.jsx`
```jsx
/**
 * OperationRow - Single operation in the operations list
 *
 * Shows operation sequence, name, status, timing, and assignment.
 * Handles visual states for pending, running, complete, skipped.
 */
import { formatDuration, formatTime } from '../../utils/formatting';

/**
 * Status indicator with icon and color
 */
function StatusIndicator({ status }) {
  const configs = {
    pending: {
      color: 'text-gray-400',
      bgColor: 'bg-gray-500/20',
      icon: '○',
      label: 'Pending'
    },
    queued: {
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/20',
      icon: '◐',
      label: 'Queued'
    },
    running: {
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/20',
      icon: '●',
      label: 'Running',
      pulse: true
    },
    complete: {
      color: 'text-green-400',
      bgColor: 'bg-green-500/20',
      icon: '●',
      label: 'Complete'
    },
    skipped: {
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/20',
      icon: '⊘',
      label: 'Skipped'
    }
  };

  const config = configs[status] || configs.pending;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.color}`}
    >
      <span className={config.pulse ? 'animate-pulse' : ''}>{config.icon}</span>
      {config.label}
    </span>
  );
}

/**
 * Format elapsed or estimated time
 */
function TimingDisplay({ operation }) {
  if (operation.status === 'complete') {
    // Show actual time
    const actualMinutes = (operation.actual_setup_minutes || 0) + (operation.actual_run_minutes || 0);
    return (
      <span className="text-green-400 text-sm">
        {formatDuration(actualMinutes)}
      </span>
    );
  }

  if (operation.status === 'running') {
    // Show elapsed time (calculate from actual_start)
    if (operation.actual_start) {
      const start = new Date(operation.actual_start);
      const elapsed = Math.floor((Date.now() - start.getTime()) / 60000);
      return (
        <span className="text-purple-400 text-sm font-mono">
          {formatDuration(elapsed)}
        </span>
      );
    }
    return <span className="text-purple-400 text-sm">Starting...</span>;
  }

  if (operation.status === 'skipped') {
    return <span className="text-yellow-400 text-sm">—</span>;
  }

  // Pending - show estimate
  const planned = (operation.planned_setup_minutes || 0) + (operation.planned_run_minutes || 0);
  if (planned > 0) {
    return (
      <span className="text-gray-500 text-sm">
        Est: {formatDuration(planned)}
      </span>
    );
  }

  return <span className="text-gray-600 text-sm">—</span>;
}

/**
 * Main OperationRow component
 */
export default function OperationRow({ operation, isActive, onClick }) {
  const isClickable = onClick && ['pending', 'running'].includes(operation.status);

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
        {/* Left: Sequence, Code, Name */}
        <div className="flex items-center gap-3">
          {/* Sequence number */}
          <span className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-800 text-gray-400 text-sm font-mono">
            {operation.sequence}
          </span>

          {/* Operation info */}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white font-medium">
                {operation.operation_code || `Op ${operation.sequence}`}
              </span>
              {operation.operation_name && (
                <>
                  <span className="text-gray-600">—</span>
                  <span className="text-gray-400">{operation.operation_name}</span>
                </>
              )}
            </div>

            {/* Work center / resource */}
            <div className="text-xs text-gray-500 mt-0.5">
              {operation.work_center_name || operation.work_center_code || 'Unassigned'}
              {operation.resource_name && (
                <span className="text-gray-600"> → {operation.resource_name}</span>
              )}
            </div>
          </div>
        </div>

        {/* Right: Status and Timing */}
        <div className="flex items-center gap-4">
          <TimingDisplay operation={operation} />
          <StatusIndicator status={operation.status} />
        </div>
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
    </div>
  );
}
```

**Verification:**
- [ ] File created
- [ ] No import errors

**Commit Message:** `feat(UI-401): add OperationRow component`

---

### Step 2 of 5: Create OperationsPanel Component

**Agent:** Frontend Agent  
**Time:** 25 minutes  
**Directory:** `frontend/src/components/production/`

**File to Create:** `frontend/src/components/production/OperationsPanel.jsx`
```jsx
/**
 * OperationsPanel - List of operations for a production order
 *
 * Displays all operations with status, provides click interaction,
 * and shows overall progress summary.
 */
import { useState, useEffect } from 'react';
import { API_URL } from '../../config/api';
import OperationRow from './OperationRow';
import { formatDuration } from '../../utils/formatting';

/**
 * Operations summary bar
 */
function OperationsSummary({ operations }) {
  if (!operations || operations.length === 0) return null;

  const completed = operations.filter(op => op.status === 'complete').length;
  const skipped = operations.filter(op => op.status === 'skipped').length;
  const running = operations.filter(op => op.status === 'running').length;
  const pending = operations.filter(op => op.status === 'pending').length;

  // Calculate time
  const elapsedMinutes = operations.reduce((sum, op) => {
    if (op.status === 'complete') {
      return sum + (op.actual_setup_minutes || 0) + (op.actual_run_minutes || 0);
    }
    if (op.status === 'running' && op.actual_start) {
      const elapsed = Math.floor((Date.now() - new Date(op.actual_start).getTime()) / 60000);
      return sum + elapsed;
    }
    return sum;
  }, 0);

  const remainingMinutes = operations.reduce((sum, op) => {
    if (['pending', 'queued'].includes(op.status)) {
      return sum + (op.planned_setup_minutes || 0) + (op.planned_run_minutes || 0);
    }
    return sum;
  }, 0);

  return (
    <div className="flex items-center justify-between text-sm border-t border-gray-800 pt-3 mt-3">
      <div className="flex items-center gap-4">
        <span className="text-gray-500">
          {completed + skipped}/{operations.length} complete
        </span>
        {running > 0 && (
          <span className="text-purple-400">
            ● {running} running
          </span>
        )}
      </div>
      <div className="flex items-center gap-4 text-gray-500">
        {elapsedMinutes > 0 && (
          <span>{formatDuration(elapsedMinutes)} elapsed</span>
        )}
        {remainingMinutes > 0 && (
          <span>~{formatDuration(remainingMinutes)} remaining</span>
        )}
      </div>
    </div>
  );
}

/**
 * Empty state when no operations
 */
function EmptyOperations({ orderStatus }) {
  if (orderStatus === 'draft') {
    return (
      <div className="text-center py-8">
        <div className="text-gray-500 mb-2">No operations yet</div>
        <div className="text-sm text-gray-600">
          Operations will be generated when the order is released
        </div>
      </div>
    );
  }

  return (
    <div className="text-center py-8">
      <div className="text-gray-500 mb-2">No operations defined</div>
      <div className="text-sm text-gray-600">
        This product may not have a routing configured
      </div>
    </div>
  );
}

/**
 * Main OperationsPanel component
 */
export default function OperationsPanel({ productionOrderId, orderStatus, onOperationClick }) {
  const [operations, setOperations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const token = localStorage.getItem('adminToken');

  useEffect(() => {
    fetchOperations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productionOrderId]);

  // Auto-refresh while any operation is running
  useEffect(() => {
    const hasRunning = operations.some(op => op.status === 'running');
    if (!hasRunning) return;

    const interval = setInterval(fetchOperations, 30000); // Refresh every 30s
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [operations]);

  const fetchOperations = async () => {
    if (!token || !productionOrderId) return;

    try {
      const res = await fetch(
        `${API_URL}/api/v1/production-orders/${productionOrderId}/operations`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (!res.ok) throw new Error('Failed to fetch operations');

      const data = await res.json();
      // Handle both array response and object with operations array
      setOperations(Array.isArray(data) ? data : data.operations || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    setLoading(true);
    fetchOperations();
  };

  // Find the active (running) operation
  const activeOperation = operations.find(op => op.status === 'running');

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Operations</h2>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="text-gray-400 hover:text-white transition-colors disabled:opacity-50"
          title="Refresh"
        >
          <svg
            className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Loading state */}
      {loading && operations.length === 0 && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        </div>
      )}

      {/* Operations list */}
      {!loading && operations.length === 0 ? (
        <EmptyOperations orderStatus={orderStatus} />
      ) : (
        <div className="space-y-2">
          {operations
            .sort((a, b) => a.sequence - b.sequence)
            .map(operation => (
              <OperationRow
                key={operation.id}
                operation={operation}
                isActive={activeOperation?.id === operation.id}
                onClick={onOperationClick}
              />
            ))}

          <OperationsSummary operations={operations} />
        </div>
      )}
    </div>
  );
}
```

**Verification:**
- [ ] File created
- [ ] No import errors

**Commit Message:** `feat(UI-401): add OperationsPanel component`

---

### Step 3 of 5: Add Formatting Utilities

**Agent:** Frontend Agent  
**Time:** 10 minutes  
**Directory:** `frontend/src/utils/`

**File to Create (or Modify):** `frontend/src/utils/formatting.js`
```javascript
/**
 * Formatting utilities for display
 */

/**
 * Format duration in minutes to human-readable string
 * @param {number} minutes - Duration in minutes
 * @returns {string} Formatted duration (e.g., "2h 30m", "45m", "1h")
 */
export function formatDuration(minutes) {
  if (!minutes || minutes <= 0) return '0m';

  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);

  if (hours === 0) return `${mins}m`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}m`;
}

/**
 * Format datetime to time string
 * @param {string|Date} datetime - ISO datetime string or Date object
 * @returns {string} Formatted time (e.g., "2:30 PM")
 */
export function formatTime(datetime) {
  if (!datetime) return '';

  const date = typeof datetime === 'string' ? new Date(datetime) : datetime;
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

/**
 * Format datetime to date string
 * @param {string|Date} datetime - ISO datetime string or Date object
 * @returns {string} Formatted date (e.g., "Jan 15, 2025")
 */
export function formatDate(datetime) {
  if (!datetime) return '';

  const date = typeof datetime === 'string' ? new Date(datetime) : datetime;
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}

/**
 * Format datetime to relative string
 * @param {string|Date} datetime - ISO datetime string or Date object
 * @returns {string} Relative time (e.g., "5 minutes ago", "in 2 hours")
 */
export function formatRelativeTime(datetime) {
  if (!datetime) return '';

  const date = typeof datetime === 'string' ? new Date(datetime) : datetime;
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffMins = Math.round(diffMs / 60000);

  if (Math.abs(diffMins) < 1) return 'just now';
  if (diffMins < 0) {
    // Past
    const absMins = Math.abs(diffMins);
    if (absMins < 60) return `${absMins}m ago`;
    const hours = Math.floor(absMins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  } else {
    // Future
    if (diffMins < 60) return `in ${diffMins}m`;
    const hours = Math.floor(diffMins / 60);
    if (hours < 24) return `in ${hours}h`;
    const days = Math.floor(hours / 24);
    return `in ${days}d`;
  }
}
```

**Verification:**
- [ ] File created or updated
- [ ] No syntax errors

**Commit Message:** `feat(UI-401): add formatting utilities`

---

### Step 4 of 5: Create Index Export

**Agent:** Frontend Agent  
**Time:** 5 minutes  
**Directory:** `frontend/src/components/production/`

**File to Create:** `frontend/src/components/production/index.js`
```javascript
/**
 * Production components exports
 */
export { default as OperationRow } from './OperationRow';
export { default as OperationsPanel } from './OperationsPanel';
```

**Verification:**
- [ ] File created
- [ ] Exports work correctly

**Commit Message:** `chore(UI-401): add production components index`

---

### Step 5 of 5: Integrate into ProductionOrderDetail

**Agent:** Frontend Agent  
**Time:** 15 minutes  
**File to Modify:** `frontend/src/pages/admin/ProductionOrderDetail.jsx`

**Add import at top:**
```jsx
import { OperationsPanel } from '../../components/production';
```

**Add OperationsPanel after the Order Summary section (around line 180, after the progress bar div):**
```jsx
      {/* Operations Panel */}
      <OperationsPanel
        productionOrderId={order.id}
        orderStatus={order.status}
        onOperationClick={(operation) => {
          // For now, just log - UI-403 will add action modal
          console.log('Operation clicked:', operation);
        }}
      />
```

The full insertion point should be after this block:
```jsx
        {/* Progress Bar */}
        <div className="mt-4">
          ...
        </div>
      </div>

      {/* ADD OPERATIONS PANEL HERE */}
      <OperationsPanel
        productionOrderId={order.id}
        orderStatus={order.status}
        onOperationClick={(operation) => {
          console.log('Operation clicked:', operation);
        }}
      />

      {/* Blocking Issues Panel */}
      <BlockingIssuesPanel
```

**Verification:**
- [ ] Import added
- [ ] OperationsPanel rendered in correct position
- [ ] App runs without errors
- [ ] Operations display for a PO with operations

**Commit Message:** `feat(UI-401): integrate OperationsPanel into ProductionOrderDetail`

---

## Final Checklist

- [ ] All 5 steps executed in order
- [ ] Components render correctly
- [ ] Operations load from API
- [ ] Status badges display properly
- [ ] Time calculations work
- [ ] Clicking operations logs to console (ready for UI-403)

---

## Visual Verification

1. Navigate to a released production order with operations
2. Verify operations list displays
3. Verify status badges are correct
4. Verify timing shows estimates for pending, elapsed for running
5. Verify completed operations are slightly dimmed
6. Verify refresh button works

---

## Handoff to Next Ticket

**UI-402: Operation Scheduler Modal**
- Click on pending operation opens scheduler
- Select resource and time slot
- Shows conflicts if time overlaps with other operations
- Calls POST `/operations/{op_id}/schedule` API
