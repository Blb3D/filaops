# FilaOps UI Components Reference

> Complete UI page and component documentation for FilaOps Core ERP system.
> Generated for AI consumption and developer reference.
>
> This document covers **Core (Open Source)** UI components only.

## Overview

| Metric | Count |
| ------ | ----- |
| **Total Pages** | 31 |
| **Total Components** | 65+ |
| **Route Groups** | 6 |
| **Framework** | React 18 + Vite |
| **UI Library** | Tailwind CSS |
| **State** | React Query + Context |

---

## Navigation Structure

From `AdminLayout.jsx`, the sidebar navigation is organized into groups:

### Dashboard (No Header)

- `/admin` → Dashboard (end: true)
- `/admin/command-center` → Command Center

### SALES

- `/admin/orders` → Orders
- `/admin/quotes` → Quotes
- `/admin/payments` → Payments (adminOnly)
- `/admin/customers` → Customers (adminOnly)

### INVENTORY

- `/admin/items` → Items
- `/admin/materials/import` → Import Materials (adminOnly)
- `/admin/bom` → Bill of Materials
- `/admin/locations` → Locations (adminOnly)
- `/admin/inventory/transactions` → Transactions (adminOnly)
- `/admin/inventory/cycle-count` → Cycle Count (adminOnly)
- `/admin/spools` → Material Spools (adminOnly)

### OPERATIONS

- `/admin/production` → Production
- `/admin/manufacturing` → Manufacturing
- `/admin/printers` → Printers
- `/admin/purchasing` → Purchasing
- `/admin/shipping` → Shipping

### QUALITY

- `/admin/quality/traceability` → Material Traceability

### ADMIN (adminOnly group)

- `/admin/accounting` → Accounting
- `/admin/orders/import` → Import Orders
- `/admin/users` → Team Members
- `/admin/scrap-reasons` → Scrap Reasons
- `/admin/settings` → Settings
- `/admin/security` → Security Audit

---

## Route Definitions

From `App.jsx`:

```text
/
├── /setup                                → Setup (initial setup wizard)
├── /onboarding                           → Onboarding (user onboarding flow)
├── /admin/login                          → AdminLogin
├── /forgot-password                      → ForgotPassword
├── /reset-password/:token                → ResetPassword
├── /admin/password-reset/:action/:token  → AdminPasswordResetApproval
│
└── /admin (AdminLayout wrapper - requires auth)
    ├── / (index)                         → AdminDashboard
    ├── /orders                           → AdminOrders
    ├── /orders/:orderId                  → OrderDetail
    ├── /quotes                           → AdminQuotes
    ├── /payments                         → AdminPayments
    ├── /customers                        → AdminCustomers
    ├── /bom                              → AdminBOM
    ├── /products                         → redirects to /items
    ├── /items                            → AdminItems
    ├── /purchasing                       → AdminPurchasing
    ├── /manufacturing                    → AdminManufacturing
    ├── /production                       → AdminProduction
    ├── /production/:orderId              → ProductionOrderDetail
    ├── /shipping                         → AdminShipping
    ├── /materials/import                 → AdminMaterialImport
    ├── /orders/import                    → AdminOrderImport
    ├── /inventory/transactions           → AdminInventoryTransactions
    ├── /inventory/cycle-count            → AdminCycleCount
    ├── /users                            → AdminUsers
    ├── /locations                        → AdminLocations
    ├── /accounting                       → AdminAccounting
    ├── /printers                         → AdminPrinters
    ├── /scrap-reasons                    → AdminScrapReasons
    ├── /spools                           → AdminSpools
    ├── /quality/traceability             → MaterialTraceability
    ├── /command-center                   → CommandCenter
    ├── /settings                         → AdminSettings
    └── /security                         → AdminSecurity
```

---

## Pages Catalog

### Authentication Pages (3)

| Page | File | Route | Purpose |
| ---- | ---- | ----- | ------- |
| Admin Login | `AdminLogin.jsx` | `/admin/login` | Email/password login for admin panel |
| Forgot Password | `ForgotPassword.jsx` | `/forgot-password` | Request password reset (admin-approved) |
| Reset Password | `ResetPassword.jsx` | `/reset-password/:token` | Set new password with approved token |

---

### Dashboard & Core Pages (4)

| Page | File | Route | Purpose |
| ------ | ------ | ------- | --------- |
| Dashboard | `AdminDashboard.jsx` | `/admin` | Main KPI dashboard |
| Command Center | `CommandCenter.jsx` | `/admin/command-center` | Real-time production floor monitoring |
| Setup | `Setup.jsx` | `/setup` | Initial system setup wizard |
| Onboarding | `Onboarding.jsx` | `/onboarding` | User onboarding flow |

#### AdminDashboard Features

- Sales trend chart (WTD, MTD, QTD, YTD, ALL periods)
- Dual-line cumulative chart (sales vs payments)
- Action Items panel (overdue, low stock, pending quotes, ready orders)
- Production Pipeline horizontal bar chart
- Recent Orders table (clickable to detail)
- Pending Purchase Orders list

**API Endpoints Used:**

- `GET /admin/dashboard/` - Main dashboard data
- `GET /admin/dashboard/sales-trend/` - Sales trend data
- `GET /sales-orders/` - Recent orders
- `GET /purchase-orders/` - Pending POs

---

### Sales Management Pages (5)

| Page | File | Route | Purpose | Key API Endpoints |
| ---- | ---- | ----- | ------- | ----------------- |
| Orders | `AdminOrders.jsx` | `/admin/orders` | Sales order list with filters | `GET /sales-orders/` |
| Order Detail | `OrderDetail.jsx` | `/admin/orders/:orderId` | Full order view | `GET /sales-orders/:id` |
| Quotes | `AdminQuotes.jsx` | `/admin/quotes` | Quotation management | `GET /quotes/` |
| Payments | `AdminPayments.jsx` | `/admin/payments` | Payment tracking | `GET /payments/` |
| Customers | `AdminCustomers.jsx` | `/admin/customers` | Customer database | `GET /admin/customers/` |

#### AdminOrders Features

- Fulfillment Status filter (fulfillment_priority, fulfillment_state)
- Sort by multiple fields (created_at, due_date, total_amount)
- Client-side search (order #, product, customer, email)
- Card layout (3-column grid)
- Create Order modal
- Cancel Order modal (with reason)
- Delete Order confirmation

#### OrderDetail Features

- Full order summary with customer info
- Material Requirements table (BOM explosion, shortages)
- Capacity Requirements (routing operations)
- Production Status (WO progress bars)
- Payment Summary & History
- Fulfillment Progress widget
- Blocking Issues Panel
- Shipping Address editor
- Activity & Shipping Timeline

---

### Inventory Management Pages (7)

| Page | File | Route | Purpose | Key API Endpoints |
|------|------|-------|---------|-------------------|
| Items | `AdminItems.jsx` | `/admin/items` | Product/component catalog | `GET /items/` |
| BOM Management | `AdminBOM.jsx` | `/admin/bom` | Bill of materials editor | `GET /admin/bom/` |
| Inventory Transactions | `AdminInventoryTransactions.jsx` | `/admin/inventory/transactions` | Transaction log | `GET /admin/inventory-transactions/` |
| Cycle Count | `AdminCycleCount.jsx` | `/admin/inventory/cycle-count` | Physical inventory counting | `GET /inventory/cycle-count/` |
| Locations | `AdminLocations.jsx` | `/admin/locations` | Warehouse/location management | `GET /admin/locations/` |
| Spools | `AdminSpools.jsx` | `/admin/spools` | Filament spool tracking | `GET /spools/` |
| Material Import | `AdminMaterialImport.jsx` | `/admin/materials/import` | Bulk material import | `POST /materials/import/` |

#### AdminItems Features

- Hierarchical Category tree (expandable, edit/delete)
- Table AND Card views (sortable)
- Inventory Adjustment with reason codes
- Bulk Update modal (category, type, procurement)
- Quick filter cards (Total, FG, Components, Materials, Supplies, Needs Reorder)
- Search by SKU/name/UPC
- Recost All function
- Pagination (25/50/100/200 per page)
- Item Type filtering
- Active/Inactive toggle

**Form Fields (ItemForm):**

- SKU (required)
- Name (required)
- Description
- Category (dropdown)
- Item Type (finished_good, component, material, consumable)
- Procurement Type (make, buy)
- Unit of Measure
- Standard Cost, Average Cost, Last Cost
- Reorder Point, Reorder Qty
- Lead Time Days
- Active toggle
- Has BOM toggle
- UPC/Barcode

---

### Manufacturing Pages (4)

| Page | File | Route | Purpose | Key API Endpoints |
|------|------|-------|---------|-------------------|
| Production Orders | `AdminProduction.jsx` | `/admin/production` | Work order list/queue | `GET /production-orders/` |
| Production Detail | `ProductionOrderDetail.jsx` | `/admin/production/:orderId` | Single WO with operations | `GET /production-orders/:id` |
| Manufacturing | `AdminManufacturing.jsx` | `/admin/manufacturing` | Shop floor view | `GET /production-orders/` |
| Printers | `AdminPrinters.jsx` | `/admin/printers` | 3D printer management | `GET /printers/` |

#### AdminProduction Features

- Production queue list
- Filter by status (Draft, Released, Scheduled, In Progress, Complete)
- Work order cards with progress
- Quick operation actions
- Production Order creation

#### ProductionOrderDetail Features

- Operation timeline visualization
- Material consumption tracking
- QC pass/fail recording
- Scrap entry modal
- Operation scheduling
- Progress bars per operation

---

### Supply Chain Pages (3)

| Page | File | Route | Purpose | Key API Endpoints |
|------|------|-------|---------|-------------------|
| Purchasing | `AdminPurchasing.jsx` | `/admin/purchasing` | PO management | `GET /purchase-orders/`, `GET /vendors/` |
| Shipping | `AdminShipping.jsx` | `/admin/shipping` | Order fulfillment | `POST /shipments/` |
| Order Import | `AdminOrderImport.jsx` | `/admin/orders/import` | Bulk order import | `POST /orders/import/` |

#### AdminPurchasing Features

- PO list with vendor, status, amount
- Low Stock items tab
- Vendor management
- PO creation wizard
- Receipt/acceptance workflow

---

### Settings & Admin Pages (5)

| Page | File | Route | Purpose | Key API Endpoints |
|------|------|-------|---------|-------------------|
| Users | `AdminUsers.jsx` | `/admin/users` | User accounts/roles | `GET /admin/users/` |
| Settings | `AdminSettings.jsx` | `/admin/settings` | System configuration | `GET /settings/`, `PATCH /settings/` |
| Security | `AdminSecurity.jsx` | `/admin/security` | Security audit | `GET /security/audit-log/` |
| Accounting | `AdminAccounting.jsx` | `/admin/accounting` | GL, tax settings | `GET /accounting/trial-balance` |
| Scrap Reasons | `AdminScrapReasons.jsx` | `/admin/scrap-reasons` | Scrap reason codes | `GET /scrap-reasons/` |

---

### Quality & Reporting Pages (1)

| Page | File | Route | Purpose | Key API Endpoints |
|------|------|-------|---------|-------------------|
| Material Traceability | `MaterialTraceability.jsx` | `/admin/quality/traceability` | Lot/serial traceability | `GET /traceability/forward/:serial` |

---

## Components Catalog

### Layout Components (2)

| Component      | File                 | Purpose                                 | Props                     |
|----------------|----------------------|-----------------------------------------|---------------------------|
| AdminLayout    | `AdminLayout.jsx`    | Main navigation sidebar/layout wrapper  | `children`, `currentPage` |
| ErrorBoundary  | `ErrorBoundary.jsx`  | Error fallback for crash recovery       | `children`                |

---

### Order Management Components (5)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | -------- |
| SalesOrderCard | `SalesOrderCard.jsx` | Card display for sales order | `order`, `onViewDetails`, `onShip` | AdminOrders |
| OrderFilters | `OrderFilters.jsx` | Filter/sort toolbar | `selectedFilter`, `onFilterChange`, `selectedSort`, `onSortChange`, `search`, `onSearchChange` | AdminOrders |
| BlockingIssuesPanel | `BlockingIssuesPanel.jsx` | Shows fulfillment blockers | `orderType`, `orderId`, `onActionClick` | OrderDetail |
| FulfillmentProgress | `FulfillmentProgress.jsx` | Order fulfillment status | `fulfillmentStatus`, `loading`, `error`, `onRefresh`, `onShip` | OrderDetail |
| SplitOrderModal | `SplitOrderModal.jsx` | Split order into multiple sub-orders | `isOpen`, `orderId`, `onClose`, `onSuccess` | AdminOrders |

---

### Production Management Components (11)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| ProductionOrderModal | `ProductionOrderModal.jsx` | Create/edit production order | `isOpen`, `orderId`, `onClose`, `onSuccess` | AdminProduction |
| OperationsPanel | `OperationsPanel.jsx` | Display operations for WO | `productionOrderId`, `operations` | ProductionOrderDetail |
| OperationCard | `OperationCard.jsx` | Single operation status card | `operation`, `onStatusChange` | OperationsPanel |
| OperationRow | `OperationRow.jsx` | Table row for operation | `operation`, `onEdit` | OperationsPanel |
| OperationCompletionModal | `OperationCompletionModal.jsx` | Complete operation with qty/scrap | `isOpen`, `operationId`, `onClose`, `onSuccess` | ProductionOrderDetail |
| OperationSchedulerModal | `OperationSchedulerModal.jsx` | Schedule to work center | `isOpen`, `operationId`, `onClose`, `onSuccess` | OperationsPanel |
| OperationsTimeline | `OperationsTimeline.jsx` | Timeline view of operations | `operations` | ProductionOrderDetail |
| OperationsProgressBar | `OperationsProgressBar.jsx` | Progress indicator | `operations` | OperationsPanel |
| ProductionQueueList | `ProductionQueueList.jsx` | Queue of pending work orders | `workOrders` | AdminProduction |
| ScrapEntryModal | `ScrapEntryModal.jsx` | Record scrap for operation | `isOpen`, `operationId`, `onClose`, `onSuccess` | ProductionOrderDetail |
| ElapsedTimer | `ElapsedTimer.jsx` | Running timer for operation | `startTime`, `isPaused` | OperationsPanel |

---

### Inventory & Items Components (5)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| ItemCard | `ItemCard.jsx` | Card view of item with stock | `itemId`, `onClick` | AdminItems |
| ItemForm | `ItemForm.jsx` | Create/edit item form | `isOpen`, `editingItem`, `onClose`, `onSuccess` | AdminItems |
| MaterialForm | `MaterialForm.jsx` | Create filament/material form | `isOpen`, `onClose`, `onSuccess` | AdminItems |
| ItemWizard | `ItemWizard.jsx` | Step-by-step item creation | `isOpen`, `onClose`, `onSuccess` | AdminItems |
| BOMEditor | `BOMEditor.jsx` | Edit BOM components & quantities | `isOpen`, `productId`, `onClose`, `onSuccess` | AdminItems |

---

### Manufacturing Configuration Components (2)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| RoutingEditor | `RoutingEditor.jsx` | Edit routing operations & work centers | `isOpen`, `productId`, `onClose`, `onSuccess` | AdminItems, AdminBOM |
| ManufacturingBOMEditor | `ManufacturingBOMEditor.jsx` | Edit routing materials | `isOpen`, `productId`, `onClose`, `onSuccess` | AdminBOM |

---

### Purchasing Components (6)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| POCreateModal | `POCreateModal.jsx` | Create purchase order | `isOpen`, `onClose`, `onSuccess`, `defaultVendor`, `defaultItem` | AdminPurchasing |
| PODetailModal | `PODetailModal.jsx` | View/edit PO details | `isOpen`, `poId`, `onClose`, `onSuccess` | AdminPurchasing |
| ReceiveModal | `ReceiveModal.jsx` | Receive PO items | `isOpen`, `poId`, `onClose`, `onSuccess` | AdminPurchasing |
| VendorModal | `VendorModal.jsx` | Create/edit vendor | `isOpen`, `vendor`, `onClose`, `onSuccess` | AdminPurchasing |
| VendorDetailPanel | `VendorDetailPanel.jsx` | Vendor info panel | `vendorId` | AdminPurchasing |
| DocumentUploadPanel | `DocumentUploadPanel.jsx` | Attach PO documents | `poId` | AdminPurchasing |

---

### Payment Components (1)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| RecordPaymentModal | `RecordPaymentModal.jsx` | Record payment/refund | `orderId`, `isRefund`, `onClose`, `onSuccess` | OrderDetail |

---

### Quality Components (2)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| QCInspectionModal | `QCInspectionModal.jsx` | QC pass/fail entry | `isOpen`, `operationId`, `onClose`, `onSuccess` | ProductionOrderDetail |
| RemediationModal | `RemediationModal.jsx` | Record rework/scrap handling | `isOpen`, `defectId`, `onClose`, `onSuccess` | ProductionOrderDetail |

---

### Modal & Dialog Components (7)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| CompleteOrderModal | `CompleteOrderModal.jsx` | Mark order complete | `isOpen`, `orderId`, `onClose`, `onSuccess` | OrderDetail |
| ConfirmDialog | `ConfirmDialog.jsx` | Generic confirmation | `isOpen`, `title`, `message`, `confirmLabel`, `onConfirm`, `onCancel` | Multiple |
| ScrapOrderModal | `ScrapOrderModal.jsx` | Scrap entire production order | `isOpen`, `orderId`, `onClose`, `onSuccess` | ProductionOrderDetail |
| ShortageModal | `ShortageModal.jsx` | Shortage resolution | `isOpen`, `shortages`, `onClose`, `onResolve` | ProductionOrderDetail |
| SkipOperationModal | `SkipOperationModal.jsx` | Skip operation with reason | `isOpen`, `operationId`, `onClose`, `onSuccess` | OperationsPanel |
| QuickCreateItemModal | `QuickCreateItemModal.jsx` | Quick item creation | `isOpen`, `onClose`, `onSuccess` | Purchasing |
| ProductSearchSelect | `ProductSearchSelect.jsx` | Search & select product | `placeholder`, `onSelect` | Various |

---

### Data Display Components (7)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| ActivityTimeline | `ActivityTimeline.jsx` | Event log timeline | `orderId` | OrderDetail |
| POActivityTimeline | `POActivityTimeline.jsx` | PO event timeline | `poId` | AdminPurchasing |
| ShippingTimeline | `ShippingTimeline.jsx` | Shipment tracking timeline | `orderId` | OrderDetail |
| StatCard | `StatCard.jsx` | KPI card with value | `title`, `value`, `subtitle`, `color`, `onClick`, `to`, `active` | Dashboard, AdminItems |
| PaginationControls | `PaginationControls.jsx` | Table pagination | `page`, `pageSize`, `total`, `onPageChange` | Tables |
| EmptyState | `EmptyState.jsx` | No data placeholder | `title`, `description`, `action` | Various |
| RelativeDate | `RelativeDate.jsx` | Human-readable date | `date` | Timelines |

---

### Alert & Feedback Components (4)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| Toast | `Toast.jsx` | Toast notifications provider | `children` | App |
| ApiErrorToaster | `ApiErrorToaster.jsx` | Global API error handler | - | App |
| ErrorMessage | `ErrorMessage.jsx` | Inline error message | `error`, `RequiredIndicator` | Forms |
| UpdateNotification | `UpdateNotification.jsx` | App update available banner | - | App |

---

### Utility Components (4)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| ExportImport | `ExportImport.jsx` | Import/export data | `resourceType`, `onImport`, `onExport` | Admin pages |
| SecurityBadge | `SecurityBadge.jsx` | Security level indicator | `level` | SecuritySettings |
| OperationMaterialModal | `OperationMaterialModal.jsx` | Material assignment | `isOpen`, `operationId`, `onClose`, `onSuccess` | RoutingEditor |
| OperationActions | `OperationActions.jsx` | Action buttons for operation | `operation`, `onStart`, `onPause`, `onComplete` | OperationsPanel |

---

### Command Center Components (3)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| SummaryCard | `SummaryCard.jsx` | KPI card for command center | `title`, `value`, `trend` | CommandCenter |
| MachineStatusGrid | `MachineStatusGrid.jsx` | Work center status grid | `workCenters`, `onSelect` | CommandCenter |
| AlertCard | `AlertCard.jsx` | Alert/issue card | `alert`, `onAcknowledge` | CommandCenter |

---

### Wizard Components (1)

| Component | File | Purpose | Props | Used In |
| --------- | ---- | ------- | ----- | ------- |
| SalesOrderWizard | `SalesOrderWizard.jsx` | Multi-step SO creation | `isOpen`, `onClose`, `onSuccess` | AdminOrders |

---

## Form Fields Reference

### ItemForm Fields

| Field | Type | Required | API Field |
| ------- | ------ | ---------- | ----------- |
| SKU | text | Yes | `sku` |
| Name | text | Yes | `name` |
| Description | textarea | No | `description` |
| Category | select | No | `category_id` |
| Item Type | select | Yes | `item_type` |
| Procurement Type | select | No | `procurement_type` |
| Unit of Measure | select | Yes | `unit` |
| Standard Cost | number | No | `standard_cost` |
| Average Cost | number | No | `average_cost` |
| Last Cost | number | No | `last_cost` |
| Reorder Point | number | No | `reorder_point` |
| Reorder Quantity | number | No | `reorder_qty` |
| Lead Time Days | number | No | `lead_time_days` |
| Active | toggle | No | `is_active` |
| Has BOM | toggle | No | `has_bom` |
| UPC/Barcode | text | No | `upc` |

### VendorModal Fields

| Field | Type | Required | API Field |
|-------|------|----------|-----------|
| Vendor Name | text | Yes | `name` |
| Contact Name | text | No | `contact_name` |
| Email | email | No | `email` |
| Phone | tel | No | `phone` |
| Address | textarea | No | `address` |
| Payment Terms | select | No | `payment_terms` |
| Lead Time Days | number | No | `lead_time_days` |
| Notes | textarea | No | `notes` |
| Active | toggle | No | `is_active` |

### CustomerModal Fields

| Field | Type | Required | API Field |
| ----- | ---- | -------- | --------- |
| Company Name | text | No | `company_name` |
| First Name | text | Yes | `first_name` |
| Last Name | text | Yes | `last_name` |
| Email | email | Yes | `email` |
| Phone | tel | No | `phone` |
| Address Line 1 | text | No | `address_line1` |
| Address Line 2 | text | No | `address_line2` |
| City | text | No | `city` |
| State | text | No | `state` |
| Postal Code | text | No | `postal_code` |
| Country | select | No | `country` |
| Notes | textarea | No | `notes` |

---

## Disabled/Hidden Features

### Navigation Disabled

| Feature | Location | Reason |
|---------|----------|--------|
| Analytics | `AdminLayout.jsx` | TODO: Re-enable when analytics are implemented |

---

## API Call Patterns

All API calls use this pattern:

```javascript
const token = localStorage.getItem("adminToken");
const response = await fetch(`${API_URL}/api/v1/endpoint`, {
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  }
});
```

### Common API Hooks

- `useQuery` - React Query for GET requests
- `useMutation` - React Query for POST/PATCH/DELETE
- `useActivityTokenRefresh` - Auto-refresh JWT tokens

---

## State Management

### Local Storage Keys

| Key | Purpose |
| --- | ------- |
| `adminToken` | JWT access token |
| `adminRefreshToken` | JWT refresh token |
| `adminUser` | User profile JSON |
| `sidebarOpen` | Sidebar collapse state |

### React Context

| Context        | Purpose                  |
|----------------|--------------------------|
| `ToastContext` | Toast notification state |

---

## Styling

### CSS Variables (from theme)

```css
--bg-primary      /* Main background */
--bg-secondary    /* Sidebar background */
--bg-card         /* Card background */
--text-primary    /* Primary text */
--text-secondary  /* Secondary text */
--text-muted      /* Muted/disabled text */
--border-subtle   /* Subtle borders */
```

### Tailwind Classes

- `glass` - Glass morphism effect
- `nav-item` - Navigation item default
- `nav-item-active` - Navigation item active state
- `grid-pattern` - Background grid pattern
- `logo-glow` - Logo glow effect

---

*Last updated: 2026-01-28*
*Generated for FilaOps Core*
