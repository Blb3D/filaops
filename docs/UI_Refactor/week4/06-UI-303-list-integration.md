# UI-303: SO List with Status Cards

**Ticket:** UI-303  
**Status:** Not Started  
**Depends On:** UI-301, API-302  
**Estimate:** 2-3 hours

---

## Purpose

Replace current SO list table with SalesOrderCard grid, add filtering/sorting controls.

---

## Current State

The current AdminOrders.jsx likely has:
- Table-based list of orders
- Basic columns: Order #, Customer, Date, Status, Total
- Simple pagination

## Target State

- Card-based grid layout
- Fulfillment status visible at a glance
- Filter buttons: All | Ready | In Progress | Blocked
- Sort dropdown: Date | Fulfillment Priority | Customer
- Mobile responsive (1 col → 2 col → 3 col)

---

## Design

```
┌─────────────────────────────────────────────────────────────────┐
│  SALES ORDERS                                                   │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Filter: [All] [Ready ✓] [In Progress] [Blocked]               │
│  Sort:   [Fulfillment Priority ▼]                              │
│                                                                 │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ SalesOrderCard  │ │ SalesOrderCard  │ │ SalesOrderCard  │   │
│  │ ● Ready to Ship │ │ ● Ready to Ship │ │ ● Partially     │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                                                                 │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ SalesOrderCard  │ │ SalesOrderCard  │ │ SalesOrderCard  │   │
│  │ ● Partially     │ │ ● Blocked       │ │ ● Blocked       │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                                                                 │
│  [← Previous]                              [Next →] Page 1 of 5 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Filter Bar Component

```jsx
// frontend/src/components/orders/OrderFilters.jsx

import React from 'react';

const FILTER_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'ready_to_ship', label: 'Ready', color: 'green' },
  { value: 'partially_ready', label: 'In Progress', color: 'yellow' },
  { value: 'blocked', label: 'Blocked', color: 'red' },
];

const SORT_OPTIONS = [
  { value: 'fulfillment_priority:asc', label: 'Most Actionable First' },
  { value: 'order_date:desc', label: 'Newest First' },
  { value: 'order_date:asc', label: 'Oldest First' },
  { value: 'fulfillment_percent:desc', label: 'Most Complete First' },
  { value: 'customer_name:asc', label: 'Customer A-Z' },
];

export default function OrderFilters({ 
  selectedFilter, 
  onFilterChange, 
  selectedSort, 
  onSortChange 
}) {
  return (
    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
      {/* Filter Buttons */}
      <div className="flex flex-wrap gap-2">
        {FILTER_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => onFilterChange(option.value)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              selectedFilter === option.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
      
      {/* Sort Dropdown */}
      <div className="flex items-center gap-2">
        <label htmlFor="sort" className="text-sm text-gray-600">Sort:</label>
        <select
          id="sort"
          value={selectedSort}
          onChange={(e) => onSortChange(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500"
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
```

---

## Modified AdminOrders.jsx

```jsx
// frontend/src/pages/admin/AdminOrders.jsx (modify existing)

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { SalesOrderCard } from '../../components/orders';
import OrderFilters from '../../components/orders/OrderFilters';
import Pagination from '../../components/common/Pagination';

export default function AdminOrders() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // State
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [totalPages, setTotalPages] = useState(1);
  
  // Filters from URL
  const filter = searchParams.get('filter') || '';
  const sort = searchParams.get('sort') || 'fulfillment_priority:asc';
  const page = parseInt(searchParams.get('page') || '1', 10);
  
  // Fetch orders
  useEffect(() => {
    const fetchOrders = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('adminToken');
        
        // Parse sort
        const [sortBy, sortOrder] = sort.split(':');
        
        // Build query
        const params = new URLSearchParams({
          include_fulfillment: 'true',
          sort_by: sortBy,
          sort_order: sortOrder,
          skip: ((page - 1) * 12).toString(),
          limit: '12',
        });
        
        if (filter) {
          params.set('fulfillment_state', filter);
        }
        
        const response = await fetch(`/api/v1/sales-orders/?${params}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        setOrders(data.items);
        setTotalPages(Math.ceil(data.total / 12));
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchOrders();
  }, [filter, sort, page]);
  
  // Handlers
  const handleFilterChange = (newFilter) => {
    setSearchParams({ filter: newFilter, sort, page: '1' });
  };
  
  const handleSortChange = (newSort) => {
    setSearchParams({ filter, sort: newSort, page: '1' });
  };
  
  const handlePageChange = (newPage) => {
    setSearchParams({ filter, sort, page: newPage.toString() });
  };
  
  const handleViewDetails = (orderId) => {
    // Open detail view (could be modal or navigate)
    setSearchParams({ ...Object.fromEntries(searchParams), so_id: orderId.toString() });
  };
  
  const handleShip = (orderId) => {
    // Navigate to shipping flow
    navigate(`/admin/shipping?order_id=${orderId}`);
  };
  
  // Selected order for detail view
  const selectedOrderId = searchParams.get('so_id');
  
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Sales Orders</h1>
      
      {/* Filters */}
      <OrderFilters
        selectedFilter={filter}
        onFilterChange={handleFilterChange}
        selectedSort={sort}
        onSortChange={handleSortChange}
      />
      
      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading orders...</p>
        </div>
      )}
      
      {/* Error State */}
      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-6">
          Error loading orders: {error}
        </div>
      )}
      
      {/* Order Cards Grid */}
      {!loading && !error && (
        <>
          {orders.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No orders found matching your filters.
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {orders.map((order) => (
                <SalesOrderCard
                  key={order.id}
                  order={order}
                  onViewDetails={handleViewDetails}
                  onShip={handleShip}
                />
              ))}
            </div>
          )}
          
          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6">
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                onPageChange={handlePageChange}
              />
            </div>
          )}
        </>
      )}
      
      {/* Detail Slide-over/Modal (if using inline detail) */}
      {selectedOrderId && (
        <OrderDetailModal
          orderId={parseInt(selectedOrderId, 10)}
          onClose={() => {
            const newParams = new URLSearchParams(searchParams);
            newParams.delete('so_id');
            setSearchParams(newParams);
          }}
        />
      )}
    </div>
  );
}
```

---

## Responsive Behavior

| Breakpoint | Grid Columns |
|------------|--------------|
| Mobile (< 768px) | 1 column |
| Tablet (768-1024px) | 2 columns |
| Desktop (> 1024px) | 3 columns |

Tailwind classes: `grid gap-4 md:grid-cols-2 lg:grid-cols-3`

---

## URL State

All filter/sort/page state is stored in URL:
- `/admin/orders?filter=ready_to_ship&sort=fulfillment_priority:asc&page=1`

Benefits:
- Shareable links
- Browser back/forward works
- Refresh preserves state

---

## Definition of Done

- [ ] OrderFilters component created
- [ ] AdminOrders.jsx modified to use card grid
- [ ] Filter buttons working (URL state)
- [ ] Sort dropdown working (URL state)
- [ ] Pagination working
- [ ] API called with correct parameters
- [ ] Responsive layout (1/2/3 columns)
- [ ] Loading and error states
- [ ] Empty state message
- [ ] Detail view still accessible
