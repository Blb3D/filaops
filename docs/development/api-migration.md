# API Standardization Migration Guide

## Overview

This guide documents the API standardization changes implemented in Sprint 1-2 for production readiness. All changes maintain backward compatibility where possible while providing a clear path forward for new implementations.

**Date**: 2025-12-23
**Version**: 1.0
**Status**: In Progress

---

## Table of Contents

1. [Error Response Standardization](#error-response-standardization)
2. [Pagination Standardization](#pagination-standardization)
3. [Updated Endpoints](#updated-endpoints)
4. [Frontend Migration](#frontend-migration)
5. [Testing Changes](#testing-changes)
6. [Breaking Changes](#breaking-changes)

---

## Error Response Standardization

### New Error Response Format

All API errors now follow this standardized format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "optional_field_name",
    "additional": "context"
  },
  "timestamp": "2025-12-23T10:30:00Z"
}
```

### Error Codes Reference

| HTTP Status | Error Code | Description | Details Fields |
|------------|------------|-------------|----------------|
| 400 | VALIDATION_ERROR | Request validation failed | `errors[]` with field/message/type |
| 400 | INVALID_STATE | Operation invalid for current state | `current_state`, `allowed_states` |
| 400 | DUPLICATE_ERROR | Duplicate resource | `resource`, `field`, `value` |
| 401 | AUTHENTICATION_ERROR | Authentication required | - |
| 401 | INVALID_CREDENTIALS | Invalid email/password | - |
| 401 | TOKEN_EXPIRED | JWT token expired | - |
| 401 | INVALID_TOKEN | Invalid JWT token | - |
| 403 | PERMISSION_DENIED | User lacks permission | `action`, `resource` |
| 404 | NOT_FOUND | Resource not found | `resource`, `resource_id` |
| 409 | CONFLICT | Resource conflict | - |
| 409 | DUPLICATE_ERROR | Duplicate detected | `resource`, `field`, `value` |
| 409 | CONCURRENCY_ERROR | Concurrent modification | - |
| 422 | BUSINESS_RULE_ERROR | Business rule violation | `rule` |
| 422 | INSUFFICIENT_INVENTORY | Not enough inventory | `product`, `requested`, `available` |
| 422 | QUOTE_EXPIRED | Quote has expired | `quote_number` |
| 422 | PRODUCTION_NOT_READY | Production cannot proceed | `reason` |
| 500 | DATABASE_ERROR | Database operation failed | - |
| 500 | INTEGRATION_ERROR | External service error | `service` |
| 500 | INTERNAL_ERROR | Unexpected internal error | - |
| 503 | SERVICE_UNAVAILABLE | Service temporarily unavailable | `service`, `retry_after_seconds` |

### Validation Error Example

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": {
    "errors": [
      {
        "field": "email",
        "message": "Invalid email format",
        "type": "value_error.email"
      },
      {
        "field": "quantity",
        "message": "Must be greater than 0",
        "type": "value_error.number.not_gt"
      }
    ]
  },
  "timestamp": "2025-12-23T10:30:00Z"
}
```

### Business Error Example

```json
{
  "error": "NOT_FOUND",
  "message": "Product with ID 123 not found",
  "details": {
    "resource": "Product",
    "resource_id": "123"
  },
  "timestamp": "2025-12-23T10:30:00Z"
}
```

---

## Pagination Standardization

### New Pagination Parameters

All list endpoints now use standardized pagination:

**Query Parameters**:
- `offset` (integer, default: 0, min: 0): Number of records to skip
- `limit` (integer, default: 50, min: 1, max: 500): Maximum records to return

**Previous Parameters** (now deprecated):
- `skip` - Use `offset` instead
- Variable `limit` defaults - Now consistently 50

### New Response Format

List endpoints now return this structure:

```json
{
  "items": [
    { "id": 1, "name": "Item 1" },
    { "id": 2, "name": "Item 2" }
  ],
  "pagination": {
    "total": 150,
    "offset": 0,
    "limit": 50,
    "returned": 50
  }
}
```

**Pagination Metadata Fields**:
- `total`: Total records matching the query (before pagination)
- `offset`: Current offset used in the request
- `limit`: Maximum records per page
- `returned`: Actual number of records in this response

### Example Request

```bash
GET /api/v1/vendors?offset=50&limit=25&search=acme&active_only=true

Response:
{
  "items": [...],
  "pagination": {
    "total": 100,
    "offset": 50,
    "limit": 25,
    "returned": 25
  }
}
```

### Calculating Page Numbers

```javascript
// From offset/limit to page numbers
const currentPage = Math.floor(offset / limit) + 1;
const totalPages = Math.ceil(total / limit);

// From page number to offset
const offset = (pageNumber - 1) * limit;
```

---

## Updated Endpoints

### ✅ Fully Migrated Endpoints

These endpoints have been fully updated with standardized pagination:

#### 1. Vendors List
**Endpoint**: `GET /api/v1/vendors`

**Old**:
```typescript
GET /api/v1/vendors?skip=0&limit=100
Response: VendorListResponse[]
```

**New**:
```typescript
GET /api/v1/vendors?offset=0&limit=50
Response: {
  items: VendorListResponse[],
  pagination: PaginationMeta
}
```

#### 2. Purchase Orders List
**Endpoint**: `GET /api/v1/purchase-orders`

**Old**:
```typescript
GET /api/v1/purchase-orders?skip=0&limit=100
Response: PurchaseOrderListResponse[]
```

**New**:
```typescript
GET /api/v1/purchase-orders?offset=0&limit=50
Response: {
  items: PurchaseOrderListResponse[],
  pagination: PaginationMeta
}
```

#### 3. Production Orders List (Parameters Only)
**Endpoint**: `GET /api/v1/production-orders`

**Note**: This endpoint currently returns `List[ProductionOrderListResponse]` directly. The response wrapper will be added in v2.0 to avoid breaking existing clients.

**Updated**:
- Parameter: `skip` → `offset`
- Default limit: 50 (was 50, max changed from 200 to 500)
- Added query parameter descriptions

---

### 🚧 Pending Migration

The following endpoints still need standardization:

#### High Priority (User-facing)
- `GET /api/v1/items` - List items
- `GET /api/v1/sales-orders` - List sales orders
- `GET /api/v1/quotes` - List quotes
- `GET /api/v1/printers` - List printers
- `GET /api/v1/work-centers` - List work centers
- `GET /api/v1/routings` - List routings

#### Medium Priority (Admin features)
- `GET /api/v1/admin/customers` - List customers
- `GET /api/v1/admin/bom` - List BOMs
- `GET /api/v1/admin/users` - List users
- `GET /api/v1/admin/inventory-transactions` - List transactions

#### Low Priority (Specialized)
- `GET /api/v1/items/categories` - List categories
- `GET /api/v1/scheduling/capacity/available-slots` - Get available slots
- `GET /api/v1/scheduling/capacity/machine-availability` - Get machine availability
- `GET /api/v1/admin/traceability/profiles` - List profiles
- `GET /api/v1/admin/uom` - List UOMs

---

## Frontend Migration

### 1. Update API Client

#### Error Handling

**Before**:
```typescript
try {
  await api.get('/vendors');
} catch (error) {
  // Error structure was inconsistent
  console.error(error.message);
}
```

**After**:
```typescript
interface ApiError {
  error: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

try {
  await api.get('/vendors');
} catch (error) {
  const apiError = error.response?.data as ApiError;

  // Machine-readable error code
  if (apiError.error === 'NOT_FOUND') {
    // Handle not found
  }

  // Human-readable message for display
  showNotification(apiError.message);

  // Detailed context for debugging
  console.error('Error details:', apiError.details);
  console.error('Occurred at:', apiError.timestamp);
}
```

#### Validation Errors

```typescript
interface ValidationError {
  field: string;
  message: string;
  type: string;
}

try {
  await api.post('/items', data);
} catch (error) {
  const apiError = error.response?.data as ApiError;

  if (apiError.error === 'VALIDATION_ERROR') {
    const errors = apiError.details?.errors as ValidationError[];

    errors.forEach(err => {
      // Set form field errors
      form.setError(err.field, {
        type: err.type,
        message: err.message
      });
    });
  }
}
```

### 2. Update List Components

#### Pagination State

**Before**:
```typescript
const [skip, setSkip] = useState(0);
const [limit] = useState(100);
const [vendors, setVendors] = useState<Vendor[]>([]);

const response = await api.get(`/vendors?skip=${skip}&limit=${limit}`);
setVendors(response.data);
```

**After**:
```typescript
interface ListResponse<T> {
  items: T[];
  pagination: {
    total: number;
    offset: number;
    limit: number;
    returned: number;
  };
}

const [offset, setOffset] = useState(0);
const [limit] = useState(50);
const [vendors, setVendors] = useState<Vendor[]>([]);
const [totalCount, setTotalCount] = useState(0);

const response = await api.get<ListResponse<Vendor>>(
  `/vendors?offset=${offset}&limit=${limit}`
);

setVendors(response.data.items);
setTotalCount(response.data.pagination.total);
```

#### Pagination Controls

```typescript
interface PaginationControlsProps {
  pagination: PaginationMeta;
  onPageChange: (newOffset: number) => void;
}

function PaginationControls({ pagination, onPageChange }: PaginationControlsProps) {
  const { total, offset, limit, returned } = pagination;

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);
  const hasNext = offset + returned < total;
  const hasPrev = offset > 0;

  return (
    <div className="flex items-center justify-between">
      <div className="text-sm text-gray-400">
        Showing {offset + 1} to {offset + returned} of {total} results
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(offset - limit)}
          disabled={!hasPrev}
          className="px-3 py-1 bg-gray-800 rounded disabled:opacity-50"
        >
          Previous
        </button>

        <span className="px-3 py-1">
          Page {currentPage} of {totalPages}
        </span>

        <button
          onClick={() => onPageChange(offset + limit)}
          disabled={!hasNext}
          className="px-3 py-1 bg-gray-800 rounded disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
```

### 3. Type Definitions

Create shared types for consistent usage:

```typescript
// types/api.ts

export interface PaginationMeta {
  total: number;
  offset: number;
  limit: number;
  returned: number;
}

export interface ListResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

export interface ValidationError {
  field: string;
  message: string;
  type: string;
}

// Query parameters for list endpoints
export interface ListQueryParams {
  offset?: number;
  limit?: number;
  search?: string;
  [key: string]: any; // Allow endpoint-specific filters
}
```

### 4. Reusable Hooks

```typescript
// hooks/useListQuery.ts
import { useState, useEffect } from 'react';
import { ListResponse, ListQueryParams } from '../types/api';

export function useListQuery<T>(
  endpoint: string,
  initialParams: ListQueryParams = {}
) {
  const [data, setData] = useState<T[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [params, setParams] = useState<ListQueryParams>({
    offset: 0,
    limit: 50,
    ...initialParams
  });

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const queryString = new URLSearchParams(
          Object.entries(params)
            .filter(([_, v]) => v !== undefined && v !== null)
            .map(([k, v]) => [k, String(v)])
        ).toString();

        const response = await api.get<ListResponse<T>>(
          `${endpoint}?${queryString}`
        );

        setData(response.data.items);
        setPagination(response.data.pagination);
      } catch (err: any) {
        setError(err.response?.data);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [endpoint, params]);

  const goToPage = (page: number) => {
    setParams(prev => ({
      ...prev,
      offset: (page - 1) * (prev.limit || 50)
    }));
  };

  const nextPage = () => {
    if (pagination && params.offset! + pagination.returned < pagination.total) {
      setParams(prev => ({
        ...prev,
        offset: prev.offset! + prev.limit!
      }));
    }
  };

  const prevPage = () => {
    if (params.offset! > 0) {
      setParams(prev => ({
        ...prev,
        offset: Math.max(0, prev.offset! - prev.limit!)
      }));
    }
  };

  const updateFilters = (newFilters: Partial<ListQueryParams>) => {
    setParams(prev => ({
      ...prev,
      ...newFilters,
      offset: 0 // Reset to first page when filters change
    }));
  };

  return {
    data,
    pagination,
    loading,
    error,
    params,
    goToPage,
    nextPage,
    prevPage,
    updateFilters,
    refresh: () => setParams({ ...params })
  };
}
```

### 5. Usage Example

```typescript
// components/VendorsList.tsx
import { useListQuery } from '../hooks/useListQuery';
import { Vendor } from '../types/vendor';

export function VendorsList() {
  const {
    data: vendors,
    pagination,
    loading,
    error,
    nextPage,
    prevPage,
    updateFilters
  } = useListQuery<Vendor>('/api/v1/vendors', {
    active_only: true
  });

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!pagination) return null;

  return (
    <div>
      <SearchBar onSearch={(search) => updateFilters({ search })} />

      <div className="grid gap-4">
        {vendors.map(vendor => (
          <VendorCard key={vendor.id} vendor={vendor} />
        ))}
      </div>

      <PaginationControls
        pagination={pagination}
        onNext={nextPage}
        onPrev={prevPage}
      />
    </div>
  );
}
```

---

## Testing Changes

### Backend Tests

Update test expectations for new response formats:

```python
def test_list_vendors_pagination(client, auth_headers):
    """Test vendor list returns paginated response"""
    response = client.get(
        "/api/v1/vendors?offset=0&limit=10",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "items" in data
    assert "pagination" in data

    # Check pagination metadata
    pagination = data["pagination"]
    assert "total" in pagination
    assert "offset" in pagination
    assert "limit" in pagination
    assert "returned" in pagination

    # Verify pagination values
    assert pagination["offset"] == 0
    assert pagination["limit"] == 10
    assert pagination["returned"] <= 10
    assert len(data["items"]) == pagination["returned"]


def test_error_response_format(client):
    """Test error responses include timestamp"""
    response = client.get("/api/v1/vendors/99999")

    assert response.status_code == 404
    data = response.json()

    # Check error structure
    assert "error" in data
    assert "message" in data
    assert "timestamp" in data

    # Verify error code
    assert data["error"] == "NOT_FOUND"

    # Verify timestamp format
    assert "T" in data["timestamp"]
    assert data["timestamp"].endswith("Z")
```

### Frontend Tests

```typescript
describe('VendorsList', () => {
  it('handles paginated response', async () => {
    const mockResponse = {
      items: [
        { id: 1, name: 'Vendor 1' },
        { id: 2, name: 'Vendor 2' }
      ],
      pagination: {
        total: 100,
        offset: 0,
        limit: 50,
        returned: 2
      }
    };

    api.get.mockResolvedValue({ data: mockResponse });

    const { getByText } = render(<VendorsList />);

    await waitFor(() => {
      expect(getByText('Vendor 1')).toBeInTheDocument();
      expect(getByText('Showing 1 to 2 of 100')).toBeInTheDocument();
    });
  });

  it('handles error response', async () => {
    const mockError = {
      response: {
        data: {
          error: 'NOT_FOUND',
          message: 'Resource not found',
          timestamp: '2025-12-23T10:30:00Z'
        }
      }
    };

    api.get.mockRejectedValue(mockError);

    const { getByText } = render(<VendorsList />);

    await waitFor(() => {
      expect(getByText('Resource not found')).toBeInTheDocument();
    });
  });
});
```

---

## Breaking Changes

### API Breaking Changes

1. **Response Structure Change** (vendors, purchase_orders):
   - Response is now wrapped in `{ items: [], pagination: {} }`
   - Direct array responses no longer supported

2. **Parameter Renaming**:
   - `skip` parameter renamed to `offset`
   - Affects: production_orders, and other endpoints being migrated

3. **Default Limit Change**:
   - Default changed from 100 to 50 for most endpoints
   - Maximum limit enforced at 500

### Migration Timeline

- **Phase 1** (Current): Core endpoints updated (vendors, purchase_orders, production_orders parameters)
- **Phase 2** (Next sprint): User-facing endpoints (items, sales_orders, quotes, printers)
- **Phase 3** (Following sprint): Admin endpoints
- **Phase 4** (Final): Specialized/low-traffic endpoints

### Backward Compatibility

To maintain compatibility during migration:

1. **Frontend**: Update list component wrappers to handle both formats:
   ```typescript
   const getData = (response: any) => {
     // New format
     if (response.items && response.pagination) {
       return response.items;
     }
     // Old format (array)
     return Array.isArray(response) ? response : [];
   };
   ```

2. **Backend**: Consider supporting both `skip` and `offset` temporarily (not implemented yet)

---

## Support and Questions

For questions or issues with the migration:
1. Check this guide first
2. Review the Sprint 1 Agent 3 progress document
3. Consult the API documentation (OpenAPI/Swagger)
4. Reach out to the backend team

---

## Changelog

### 2025-12-23
- Initial migration guide created
- Error response standardization completed
- Pagination models and dependency created
- Vendors endpoint fully migrated
- Purchase orders endpoint fully migrated
- Production orders parameters updated
