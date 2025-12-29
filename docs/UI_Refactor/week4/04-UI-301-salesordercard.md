# UI-301: SalesOrderCard Component

**Ticket:** UI-301  
**Status:** Not Started  
**Depends On:** API-302  
**Estimate:** 2-3 hours

---

## Purpose

A card component for displaying sales order summary with fulfillment status in list views.

---

## Design

```
┌─────────────────────────────────────────────────────────────────┐
│  SO-2025-0042                               ● Ready to Ship     │
│  Acme Corp                                                      │
│  ────────────────────────────────────────────────────────────── │
│  5/5 lines ready    ███████████████████████████████ 100%       │
│  ────────────────────────────────────────────────────────────── │
│  Order Date: Jan 15, 2025    Requested: Jan 20, 2025           │
│  Total: $1,500.00                                               │
│  ────────────────────────────────────────────────────────────── │
│  [View Details]                              [Ship Now ▸]       │
└─────────────────────────────────────────────────────────────────┘
```

### Status Badge Colors

| State | Badge Color | Badge Text |
|-------|-------------|------------|
| `ready_to_ship` | Green (bg-green-100 text-green-800) | Ready to Ship |
| `partially_ready` | Yellow (bg-yellow-100 text-yellow-800) | Partially Ready |
| `blocked` | Red (bg-red-100 text-red-800) | Blocked |
| `shipped` | Gray (bg-gray-100 text-gray-600) | Shipped |
| `cancelled` | Gray (bg-gray-100 text-gray-400) | Cancelled |

### Progress Bar Colors

| Percent | Bar Color |
|---------|-----------|
| 100% | Green (bg-green-500) |
| 50-99% | Yellow (bg-yellow-500) |
| 1-49% | Orange (bg-orange-500) |
| 0% | Red (bg-red-500) |

---

## Props

```typescript
interface SalesOrderCardProps {
  order: {
    id: number;
    order_number: string;
    customer_name: string;
    order_date: string;
    requested_date?: string;
    status: string;
    total: number;
    fulfillment?: {
      state: 'ready_to_ship' | 'partially_ready' | 'blocked' | 'shipped' | 'cancelled';
      lines_total: number;
      lines_ready: number;
      fulfillment_percent: number;
      can_ship_partial: boolean;
      can_ship_complete: boolean;
    };
  };
  onViewDetails: (orderId: number) => void;
  onShip?: (orderId: number) => void;  // Only shown if can_ship_complete or can_ship_partial
}
```

---

## Component Implementation

```jsx
// frontend/src/components/orders/SalesOrderCard.jsx

import React from 'react';
import { formatCurrency, formatDate } from '../../utils/formatters';

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

export default function SalesOrderCard({ order, onViewDetails, onShip }) {
  const { fulfillment } = order;
  const state = fulfillment?.state || 'blocked';
  const canShip = fulfillment?.can_ship_complete || fulfillment?.can_ship_partial;
  
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{order.order_number}</h3>
          <p className="text-sm text-gray-600">{order.customer_name}</p>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_STYLES[state]}`}>
          {STATUS_LABELS[state]}
        </span>
      </div>
      
      {/* Fulfillment Progress */}
      {fulfillment && (
        <div className="mb-3">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>{fulfillment.lines_ready}/{fulfillment.lines_total} lines ready</span>
            <span>{fulfillment.fulfillment_percent}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getProgressColor(fulfillment.fulfillment_percent)}`}
              style={{ width: `${fulfillment.fulfillment_percent}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Order Details */}
      <div className="text-sm text-gray-500 mb-3 space-y-1">
        <div className="flex justify-between">
          <span>Order Date:</span>
          <span>{formatDate(order.order_date)}</span>
        </div>
        {order.requested_date && (
          <div className="flex justify-between">
            <span>Requested:</span>
            <span>{formatDate(order.requested_date)}</span>
          </div>
        )}
        <div className="flex justify-between font-medium text-gray-700">
          <span>Total:</span>
          <span>{formatCurrency(order.total)}</span>
        </div>
      </div>
      
      {/* Actions */}
      <div className="flex justify-between items-center pt-3 border-t border-gray-100">
        <button
          onClick={() => onViewDetails(order.id)}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
        >
          View Details
        </button>
        
        {canShip && onShip && state !== 'shipped' && state !== 'cancelled' && (
          <button
            onClick={() => onShip(order.id)}
            className="px-3 py-1.5 bg-green-600 text-white text-sm font-medium rounded hover:bg-green-700"
          >
            {fulfillment.can_ship_complete ? 'Ship Now' : 'Ship Partial'} →
          </button>
        )}
      </div>
    </div>
  );
}
```

---

## Export

```javascript
// frontend/src/components/orders/index.js

export { default as SalesOrderCard } from './SalesOrderCard';
```

---

## Usage Example

```jsx
import { SalesOrderCard } from '../components/orders';

function OrdersList({ orders }) {
  const navigate = useNavigate();
  
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {orders.map(order => (
        <SalesOrderCard
          key={order.id}
          order={order}
          onViewDetails={(id) => navigate(`/admin/orders?so_id=${id}`)}
          onShip={(id) => handleShip(id)}
        />
      ))}
    </div>
  );
}
```

---

## Tests

Component tests (optional but recommended):

```jsx
// frontend/src/components/orders/SalesOrderCard.test.jsx

import { render, screen, fireEvent } from '@testing-library/react';
import SalesOrderCard from './SalesOrderCard';

const mockOrder = {
  id: 123,
  order_number: 'SO-2025-0042',
  customer_name: 'Acme Corp',
  order_date: '2025-01-15',
  total: 1500,
  fulfillment: {
    state: 'ready_to_ship',
    lines_total: 5,
    lines_ready: 5,
    fulfillment_percent: 100,
    can_ship_complete: true,
    can_ship_partial: true,
  },
};

test('displays order number and customer', () => {
  render(<SalesOrderCard order={mockOrder} onViewDetails={jest.fn()} />);
  expect(screen.getByText('SO-2025-0042')).toBeInTheDocument();
  expect(screen.getByText('Acme Corp')).toBeInTheDocument();
});

test('shows Ready to Ship badge for ready orders', () => {
  render(<SalesOrderCard order={mockOrder} onViewDetails={jest.fn()} />);
  expect(screen.getByText('Ready to Ship')).toBeInTheDocument();
});

test('shows Ship Now button when can_ship_complete', () => {
  const onShip = jest.fn();
  render(<SalesOrderCard order={mockOrder} onViewDetails={jest.fn()} onShip={onShip} />);
  
  const shipButton = screen.getByText(/Ship Now/);
  fireEvent.click(shipButton);
  expect(onShip).toHaveBeenCalledWith(123);
});

test('hides ship button for shipped orders', () => {
  const shippedOrder = {
    ...mockOrder,
    fulfillment: { ...mockOrder.fulfillment, state: 'shipped' },
  };
  render(<SalesOrderCard order={shippedOrder} onViewDetails={jest.fn()} onShip={jest.fn()} />);
  expect(screen.queryByText(/Ship/)).not.toBeInTheDocument();
});
```

---

## Accessibility

- Use semantic HTML (buttons for actions, not divs)
- Include aria-labels where needed
- Ensure color contrast meets WCAG AA
- Progress bar should have aria-valuenow, aria-valuemin, aria-valuemax

---

## Definition of Done

- [ ] Component created at `frontend/src/components/orders/SalesOrderCard.jsx`
- [ ] Exported from `frontend/src/components/orders/index.js`
- [ ] All status states styled correctly
- [ ] Progress bar working
- [ ] Ship button conditional logic correct
- [ ] No console errors
- [ ] Looks good on mobile (responsive)
