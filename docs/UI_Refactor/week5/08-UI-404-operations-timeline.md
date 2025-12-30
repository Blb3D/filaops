# UI-404: Operations Timeline View

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
- Over-engineer the timeline (keep it simple)
- "Optimize" or refactor unrelated code
- Skip visual verification

---

## Overview

**Goal:** Visual timeline showing operation progress for a production order  
**Outcome:** At-a-glance view of what's done, what's running, and what's ahead

---

## Design Reference

```
Operations Progress
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ●───────────●───────────○───────────○───────────○                  │
│  PRINT       CLEAN       ASSEMBLE    QC          PACK               │
│  ✓ 4h 12m    ● 0:23      ○ Est 1h    ○ Est 15m   ○ Est 10m         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Legend:
● = Complete (solid filled)
● = Running (pulsing)
○ = Pending (outline)
⊘ = Skipped (strikethrough)
```

---

## Alternative: Horizontal Bar View

```
┌─────────────────────────────────────────────────────────────────────┐
│ Operations Progress                                         60%     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ PRINT ✓        CLEAN ●         ASSEMBLE ○   QC ○   PACK ○          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

```
OperationsTimeline.jsx (new)
├── TimelineNode (step indicator)
├── TimelineConnector (line between nodes)
└── TimelineLabel (operation name and timing)
```

---

## Step-by-Step Execution

---

### Step 1 of 4: Create OperationsTimeline Component

**Agent:** Frontend Agent  
**Time:** 30 minutes  
**Directory:** `frontend/src/components/production/`

**File to Create:** `frontend/src/components/production/OperationsTimeline.jsx`
```jsx
/**
 * OperationsTimeline - Visual timeline of operation progress
 *
 * Shows operations as connected nodes with status indicators.
 * Provides quick visual reference for production progress.
 */
import { formatDuration } from '../../utils/formatting';

/**
 * Status configuration for visual styling
 */
const STATUS_CONFIG = {
  pending: {
    nodeClass: 'border-2 border-gray-600 bg-gray-900',
    labelClass: 'text-gray-500',
    connectorClass: 'bg-gray-700',
    icon: null
  },
  queued: {
    nodeClass: 'border-2 border-blue-500 bg-gray-900',
    labelClass: 'text-blue-400',
    connectorClass: 'bg-gray-700',
    icon: null
  },
  running: {
    nodeClass: 'border-2 border-purple-500 bg-purple-500/20 animate-pulse',
    labelClass: 'text-purple-400',
    connectorClass: 'bg-purple-500/50',
    icon: (
      <div className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
    )
  },
  complete: {
    nodeClass: 'border-2 border-green-500 bg-green-500',
    labelClass: 'text-green-400',
    connectorClass: 'bg-green-500',
    icon: (
      <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
      </svg>
    )
  },
  skipped: {
    nodeClass: 'border-2 border-yellow-500 bg-yellow-500/20',
    labelClass: 'text-yellow-400 line-through',
    connectorClass: 'bg-yellow-500/30',
    icon: (
      <svg className="w-3 h-3 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    )
  }
};

/**
 * Single timeline node
 */
function TimelineNode({ operation, isFirst, isLast }) {
  const config = STATUS_CONFIG[operation.status] || STATUS_CONFIG.pending;

  // Calculate timing display
  let timingText = '';
  if (operation.status === 'complete') {
    const actual = (operation.actual_setup_minutes || 0) + (operation.actual_run_minutes || 0);
    timingText = `✓ ${formatDuration(actual)}`;
  } else if (operation.status === 'running') {
    if (operation.actual_start) {
      const elapsed = Math.floor((Date.now() - new Date(operation.actual_start).getTime()) / 60000);
      timingText = `● ${formatDuration(elapsed)}`;
    } else {
      timingText = '● Starting...';
    }
  } else if (operation.status === 'skipped') {
    timingText = '⊘ Skipped';
  } else {
    const planned = (operation.planned_setup_minutes || 0) + (operation.planned_run_minutes || 0);
    if (planned > 0) {
      timingText = `Est ${formatDuration(planned)}`;
    }
  }

  return (
    <div className="flex flex-col items-center flex-1 min-w-0">
      {/* Node */}
      <div
        className={`
          w-6 h-6 rounded-full flex items-center justify-center
          ${config.nodeClass}
          transition-all duration-300
        `}
      >
        {config.icon}
      </div>

      {/* Label */}
      <div className="mt-2 text-center">
        <div className={`text-xs font-medium truncate max-w-[80px] ${config.labelClass}`}>
          {operation.operation_code || `Op ${operation.sequence}`}
        </div>
        <div className={`text-[10px] ${config.labelClass} opacity-70`}>
          {timingText}
        </div>
      </div>
    </div>
  );
}

/**
 * Connector line between nodes
 */
function TimelineConnector({ prevStatus, nextStatus }) {
  // Use the "more complete" status for coloring
  const getConnectorClass = () => {
    if (prevStatus === 'complete' || prevStatus === 'skipped') {
      return 'bg-green-500';
    }
    if (prevStatus === 'running') {
      return 'bg-gradient-to-r from-purple-500 to-gray-700';
    }
    return 'bg-gray-700';
  };

  return (
    <div className="flex-1 h-0.5 mt-3 mx-1">
      <div className={`h-full ${getConnectorClass()} transition-all duration-300`} />
    </div>
  );
}

/**
 * Progress percentage display
 */
function ProgressSummary({ operations }) {
  if (!operations || operations.length === 0) return null;

  const completed = operations.filter(op =>
    ['complete', 'skipped'].includes(op.status)
  ).length;
  const percentage = Math.round((completed / operations.length) * 100);

  return (
    <div className="flex items-center justify-between mb-4">
      <span className="text-sm text-gray-400">Operations Progress</span>
      <span className="text-sm font-medium text-white">{percentage}%</span>
    </div>
  );
}

/**
 * Progress bar underneath timeline
 */
function ProgressBar({ operations }) {
  if (!operations || operations.length === 0) return null;

  const completed = operations.filter(op => op.status === 'complete').length;
  const running = operations.filter(op => op.status === 'running').length;
  const skipped = operations.filter(op => op.status === 'skipped').length;
  const total = operations.length;

  const completedPct = (completed / total) * 100;
  const runningPct = (running / total) * 100;
  const skippedPct = (skipped / total) * 100;

  return (
    <div className="mt-4">
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden flex">
        {/* Completed */}
        <div
          className="bg-green-500 transition-all duration-500"
          style={{ width: `${completedPct}%` }}
        />
        {/* Running */}
        <div
          className="bg-purple-500 animate-pulse transition-all duration-500"
          style={{ width: `${runningPct}%` }}
        />
        {/* Skipped */}
        <div
          className="bg-yellow-500/50 transition-all duration-500"
          style={{ width: `${skippedPct}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Main component
 */
export default function OperationsTimeline({ operations }) {
  if (!operations || operations.length === 0) {
    return null;
  }

  // Sort by sequence
  const sortedOps = [...operations].sort((a, b) => a.sequence - b.sequence);

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <ProgressSummary operations={sortedOps} />

      {/* Timeline */}
      <div className="flex items-start">
        {sortedOps.map((operation, index) => (
          <div key={operation.id} className="flex items-start flex-1 min-w-0">
            <TimelineNode
              operation={operation}
              isFirst={index === 0}
              isLast={index === sortedOps.length - 1}
            />
            {index < sortedOps.length - 1 && (
              <TimelineConnector
                prevStatus={operation.status}
                nextStatus={sortedOps[index + 1].status}
              />
            )}
          </div>
        ))}
      </div>

      <ProgressBar operations={sortedOps} />
    </div>
  );
}
```

**Verification:**
- [ ] File created
- [ ] No import errors

**Commit Message:** `feat(UI-404): add OperationsTimeline component`

---

### Step 2 of 4: Create Compact Progress Bar Variant

**Agent:** Frontend Agent  
**Time:** 15 minutes  
**Directory:** `frontend/src/components/production/`

**File to Create:** `frontend/src/components/production/OperationsProgressBar.jsx`
```jsx
/**
 * OperationsProgressBar - Compact progress indicator
 *
 * Shows operation progress in a single horizontal bar.
 * Use when space is limited (e.g., in list views).
 */
import { formatDuration } from '../../utils/formatting';

export default function OperationsProgressBar({ operations, showLabels = true }) {
  if (!operations || operations.length === 0) {
    return (
      <div className="text-xs text-gray-500">No operations</div>
    );
  }

  const sortedOps = [...operations].sort((a, b) => a.sequence - b.sequence);

  const completed = sortedOps.filter(op => op.status === 'complete').length;
  const running = sortedOps.filter(op => op.status === 'running').length;
  const skipped = sortedOps.filter(op => op.status === 'skipped').length;
  const total = sortedOps.length;

  const completedPct = (completed / total) * 100;
  const runningPct = (running / total) * 100;
  const skippedPct = (skipped / total) * 100;

  // Find current operation (first running or first pending)
  const currentOp = sortedOps.find(op => op.status === 'running')
    || sortedOps.find(op => op.status === 'pending' || op.status === 'queued');

  return (
    <div className="space-y-1.5">
      {/* Progress bar */}
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden flex">
        <div
          className="bg-green-500 transition-all duration-500"
          style={{ width: `${completedPct}%` }}
        />
        <div
          className="bg-purple-500 animate-pulse transition-all duration-500"
          style={{ width: `${runningPct}%` }}
        />
        <div
          className="bg-yellow-500/50 transition-all duration-500"
          style={{ width: `${skippedPct}%` }}
        />
      </div>

      {/* Labels */}
      {showLabels && (
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">
            {completed + skipped}/{total} ops
          </span>
          {currentOp && (
            <span className={currentOp.status === 'running' ? 'text-purple-400' : 'text-gray-500'}>
              {currentOp.status === 'running' ? '● ' : ''}
              {currentOp.operation_code || `Op ${currentOp.sequence}`}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
```

**Verification:**
- [ ] File created
- [ ] No import errors

**Commit Message:** `feat(UI-404): add OperationsProgressBar component`

---

### Step 3 of 4: Update Index Exports

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
export { default as OperationsTimeline } from './OperationsTimeline';
export { default as OperationsProgressBar } from './OperationsProgressBar';
```

**Verification:**
- [ ] Exports updated
- [ ] No import errors

**Commit Message:** `chore(UI-404): export timeline components`

---

### Step 4 of 4: Integrate into ProductionOrderDetail

**Agent:** Frontend Agent  
**Time:** 15 minutes  
**File to Modify:** `frontend/src/pages/admin/ProductionOrderDetail.jsx`

**Update import:**
```jsx
import {
  OperationsPanel,
  OperationSchedulerModal,
  OperationsTimeline
} from '../../components/production';
```

**Add state for operations (to share between timeline and panel):**
```jsx
  const [operations, setOperations] = useState([]);
```

**Add operations fetch function (can be lifted from OperationsPanel or duplicated):**

Actually, the simpler approach is to let OperationsPanel handle its own fetching, and add the timeline as a separate visual that also fetches. But for better UX, we can lift state up.

**Simpler approach - add timeline that fetches independently:**

Add OperationsTimeline before the OperationsPanel:
```jsx
      {/* Operations Timeline (visual overview) */}
      {order.status !== 'draft' && (
        <OperationsTimelineWrapper productionOrderId={order.id} />
      )}

      {/* Operations Panel (detailed list) */}
      <OperationsPanel
```

**Create wrapper component inline or in separate file:**

For simplicity, add this above the export in ProductionOrderDetail.jsx:
```jsx
/**
 * Wrapper to fetch operations for timeline
 */
function OperationsTimelineWrapper({ productionOrderId }) {
  const [operations, setOperations] = useState([]);
  const token = localStorage.getItem('adminToken');

  useEffect(() => {
    const fetchOps = async () => {
      if (!token || !productionOrderId) return;
      try {
        const res = await fetch(
          `${API_URL}/api/v1/production-orders/${productionOrderId}/operations`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (res.ok) {
          const data = await res.json();
          setOperations(Array.isArray(data) ? data : data.operations || []);
        }
      } catch (err) {
        console.error('Failed to fetch operations for timeline:', err);
      }
    };
    fetchOps();
  }, [productionOrderId, token]);

  if (operations.length === 0) return null;

  return <OperationsTimeline operations={operations} />;
}
```

Add OperationsTimeline to the imports:
```jsx
import {
  OperationsPanel,
  OperationSchedulerModal,
  OperationsTimeline
} from '../../components/production';
```

**Insert timeline in render (after Order Summary, before OperationsPanel):**
```jsx
      </div>  {/* End of Order Summary */}

      {/* Operations Timeline (visual overview) */}
      {order.status !== 'draft' && (
        <OperationsTimelineWrapper productionOrderId={order.id} />
      )}

      {/* Operations Panel */}
      <OperationsPanel
```

**Verification:**
- [ ] Import updated
- [ ] Wrapper component created
- [ ] Timeline renders above operations list
- [ ] Timeline shows correct status indicators
- [ ] Progress bar animates

**Commit Message:** `feat(UI-404): integrate OperationsTimeline into ProductionOrderDetail`

---

## Final Checklist

- [ ] All 4 steps executed in order
- [ ] Timeline component renders correctly
- [ ] Nodes show correct status colors
- [ ] Running nodes pulse/animate
- [ ] Progress bar shows accurate percentages
- [ ] Connectors change color based on progress
- [ ] Component handles empty operations gracefully

---

## Visual Verification

1. Navigate to a PO with multiple operations in various states
2. Verify timeline shows all operations in sequence order
3. Verify completed operations show green checkmarks
4. Verify running operations pulse purple
5. Verify pending operations show gray outline
6. Verify skipped operations show yellow with line-through
7. Verify progress bar matches operation completion
8. Verify progress percentage is accurate

---

## Week 5 UI Complete

| Ticket | Description | Status |
|--------|-------------|--------|
| UI-401 | Operations List | 📝 Spec ready |
| UI-402 | Operation Scheduler | 📝 Spec ready |
| UI-403 | Operation Actions | 📝 Spec ready |
| UI-404 | Operations Timeline | 📝 Spec ready |

---

## Usage in Other Views

The `OperationsProgressBar` component can be used in list views:

```jsx
// In a PO list card
import { OperationsProgressBar } from '../components/production';

<div className="mt-2">
  <OperationsProgressBar operations={po.operations} showLabels={true} />
</div>
```

This provides a compact way to show production progress without navigating to the detail page.
