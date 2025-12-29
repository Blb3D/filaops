# UI-302: SO Detail Fulfillment Status Display

**Ticket:** UI-302  
**Status:** Not Started  
**Depends On:** API-301, UI-301 (for shared styles)  
**Estimate:** 1-2 hours

---

## Purpose

Add fulfillment progress display to the SO detail page, above the existing BlockingIssuesPanel.

---

## Design

```
┌─────────────────────────────────────────────────────────────────┐
│  SO-2025-0042 - Acme Corp                                       │
│  ═══════════════════════════════════════════════════════════════│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  FULFILLMENT PROGRESS                    ● Partially Ready ││
│  │  ─────────────────────────────────────────────────────────  ││
│  │  3/5 lines ready      ████████████████░░░░░░░░░ 60%        ││
│  │                                                             ││
│  │  ✓ Line 1: FIL-PLA-BLK-1KG (10 units) - Ready              ││
│  │  ✓ Line 2: FIL-PLA-WHT-1KG (5 units) - Ready               ││
│  │  ✓ Line 3: FIL-PLA-RED-1KG (8 units) - Ready               ││
│  │  ✗ Line 4: FIL-PETG-BLK-1KG (10 units) - Short 3           ││
│  │  ✗ Line 5: FIL-PETG-WHT-1KG (5 units) - Short 5            ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  BLOCKING ISSUES (existing component from Week 3)          ││
│  │  ...                                                        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component

```jsx
// frontend/src/components/orders/FulfillmentProgress.jsx

import React from 'react';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/solid';

const STATUS_STYLES = {
  ready_to_ship: 'bg-green-100 text-green-800',
  partially_ready: 'bg-yellow-100 text-yellow-800',
  blocked: 'bg-red-100 text-red-800',
  shipped: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-gray-100 text-gray-400',
};

const STATUS_LABELS = {
  ready_to_ship: 'Ready to Ship',
  partially_ready: 'Partially Ready',
  blocked: 'Blocked',
  shipped: 'Shipped',
  cancelled: 'Cancelled',
};

function getProgressColor(percent) {
  if (percent === 100) return 'bg-green-500';
  if (percent >= 50) return 'bg-yellow-500';
  if (percent > 0) return 'bg-orange-500';
  return 'bg-red-500';
}

export default function FulfillmentProgress({ fulfillmentStatus }) {
  if (!fulfillmentStatus) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <p className="text-gray-500">Loading fulfillment status...</p>
      </div>
    );
  }
  
  const { summary, lines } = fulfillmentStatus;
  
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          Fulfillment Progress
        </h3>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_STYLES[summary.state]}`}>
          {STATUS_LABELS[summary.state]}
        </span>
      </div>
      
      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>{summary.lines_ready}/{summary.lines_total} lines ready</span>
          <span>{summary.fulfillment_percent}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all ${getProgressColor(summary.fulfillment_percent)}`}
            style={{ width: `${summary.fulfillment_percent}%` }}
            role="progressbar"
            aria-valuenow={summary.fulfillment_percent}
            aria-valuemin="0"
            aria-valuemax="100"
          />
        </div>
      </div>
      
      {/* Line Items */}
      <div className="space-y-2">
        {lines.map((line) => (
          <div
            key={line.line_id}
            className={`flex items-center justify-between p-2 rounded ${
              line.is_ready ? 'bg-green-50' : 'bg-red-50'
            }`}
          >
            <div className="flex items-center gap-2">
              {line.is_ready ? (
                <CheckCircleIcon className="w-5 h-5 text-green-600" />
              ) : (
                <XCircleIcon className="w-5 h-5 text-red-600" />
              )}
              <span className="text-sm">
                <span className="font-medium">Line {line.line_number}:</span>{' '}
                {line.product_sku} ({line.quantity_remaining} units)
              </span>
            </div>
            <span className={`text-sm ${line.is_ready ? 'text-green-700' : 'text-red-700'}`}>
              {line.is_ready ? 'Ready' : `Short ${line.shortage}`}
            </span>
          </div>
        ))}
      </div>
      
      {/* Action Buttons */}
      {summary.can_ship_complete && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <button className="w-full px-4 py-2 bg-green-600 text-white font-medium rounded hover:bg-green-700">
            Ship Complete Order →
          </button>
        </div>
      )}
      
      {!summary.can_ship_complete && summary.can_ship_partial && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <button className="w-full px-4 py-2 bg-yellow-600 text-white font-medium rounded hover:bg-yellow-700">
            Ship Partial ({summary.lines_ready} lines) →
          </button>
        </div>
      )}
    </div>
  );
}
```

---

## Hook for Data Fetching

```javascript
// frontend/src/hooks/useFulfillmentStatus.js

import { useState, useEffect } from 'react';

export function useFulfillmentStatus(orderId) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    if (!orderId) {
      setLoading(false);
      return;
    }
    
    const fetchStatus = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('adminToken');
        const response = await fetch(
          `/api/v1/sales-orders/${orderId}/fulfillment-status`,
          {
            headers: { 'Authorization': `Bearer ${token}` },
          }
        );
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        setError(err.message);
        setData(null);
      } finally {
        setLoading(false);
      }
    };
    
    fetchStatus();
  }, [orderId]);
  
  return { data, loading, error, refetch: () => setLoading(true) };
}
```

---

## Integration into OrderDetail.jsx

```jsx
// frontend/src/pages/admin/OrderDetail.jsx (modify existing)

import { FulfillmentProgress } from '../../components/orders';
import { useFulfillmentStatus } from '../../hooks/useFulfillmentStatus';
// ... existing imports

function OrderDetail() {
  const { orderId } = useParams(); // or from URL params
  
  // Existing data fetching...
  const { data: order, loading: orderLoading } = useOrder(orderId);
  
  // NEW: Fetch fulfillment status
  const { data: fulfillmentStatus, loading: fulfillmentLoading } = useFulfillmentStatus(orderId);
  
  return (
    <div>
      {/* Existing order header */}
      <OrderHeader order={order} />
      
      {/* NEW: Fulfillment Progress - ABOVE BlockingIssuesPanel */}
      <FulfillmentProgress fulfillmentStatus={fulfillmentStatus} />
      
      {/* Existing: BlockingIssuesPanel from Week 3 */}
      <BlockingIssuesPanel orderId={orderId} />
      
      {/* Existing: Order lines table, etc. */}
      <OrderLinesTable lines={order?.lines} />
    </div>
  );
}
```

---

## Where to Find OrderDetail.jsx

Check current location:
```
frontend/src/pages/admin/OrderDetail.jsx
# OR
frontend/src/pages/admin/AdminOrders.jsx (might be inline modal)
```

The SO detail might be a modal/slide-over within AdminOrders.jsx rather than a separate page. Check the URL behavior:
- If clicking "View" changes URL to `/admin/orders?so_id=123` → likely inline
- If clicking "View" changes URL to `/admin/orders/123` → likely separate page

---

## Definition of Done

- [ ] `FulfillmentProgress` component created
- [ ] `useFulfillmentStatus` hook created
- [ ] Component integrated into SO detail view
- [ ] Shows above BlockingIssuesPanel
- [ ] Progress bar animates on load
- [ ] Line items display with correct icons
- [ ] Ship button shows conditionally
- [ ] No console errors
