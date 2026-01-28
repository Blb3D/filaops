# FilaOps Feature Traceability Matrix

> Complete feature-to-layer mapping for DB -> Migration -> API -> Service -> UI.
> Use this to identify unfinished features and understand system architecture.
>
> **Note**: This document covers **Core (Open Source)** features only.

## Overview

This document maps each feature across all implementation layers:

- **DATABASE**: Tables, columns, relationships
- **MIGRATIONS**: Alembic migrations that created/modified the feature
- **API**: REST endpoints for the feature
- **SERVICE**: Backend service files
- **UI**: Frontend pages, components, forms

### Status Legend

- ✅ **Complete** - All layers implemented and functional
- ⚠️ **Backend Only** - API exists, no UI implementation
- 🚧 **Partial** - Some UI exists but incomplete
- ❌ **Disabled** - Feature code exists but is disabled

---

## Feature Matrix

### 1. Authentication & Users

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `users`, `refresh_tokens`, `password_reset_requests` |
| **MIGRATIONS** | `001_initial`, `043_add_customer_name_fields` |
| **API** | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`, `POST /auth/password-reset/*` |
| **SERVICE** | `app/core/security.py`, `app/services/email_service.py` |
| **UI** | `AdminLogin.jsx`, `ForgotPassword.jsx`, `ResetPassword.jsx` |

**Forms**: Email, Password, First Name, Last Name

---

### 2. Sales Orders

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `sales_orders`, `sales_order_lines` |
| **MIGRATIONS** | `001_initial`, `038_add_missing_sales_order_columns` |
| **API** | `GET/POST /sales-orders/`, `GET/PATCH/DELETE /sales-orders/{id}`, `POST /sales-orders/{id}/open`, `POST /sales-orders/{id}/ship`, `POST /sales-orders/{id}/complete` |
| **SERVICE** | `app/services/sales_order_service.py`, `app/services/fulfillment_service.py` |
| **UI** | `AdminOrders.jsx`, `OrderDetail.jsx`, `SalesOrderCard.jsx`, `SalesOrderWizard.jsx`, `CompleteOrderModal.jsx`, `SplitOrderModal.jsx` |

**Forms**: Customer, Products, Quantities, Shipping Address, Due Date, Notes

---

### 3. Quotes

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `quotes`, `quote_lines` |
| **MIGRATIONS** | `001_initial` |
| **API** | `GET/POST /quotes/`, `GET/PATCH/DELETE /quotes/{id}`, `POST /quotes/{id}/send`, `POST /quotes/{id}/approve`, `POST /quotes/{id}/convert` |
| **SERVICE** | `app/services/quote_service.py` |
| **UI** | `AdminQuotes.jsx` |

**Forms**: Customer, Products, Quantities, Expiry Date, Notes

---

### 4. Production Orders

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `production_orders`, `production_order_operations`, `production_order_operation_materials` |
| **MIGRATIONS** | `001_initial`, `033_add_operation_materials`, `054_add_printer_id_to_operations` |
| **API** | `GET/POST /production-orders/`, `GET/PATCH/DELETE /production-orders/{id}`, `POST /production-orders/{id}/release`, `POST /production-orders/{id}/start`, `POST /production-orders/{id}/complete`, operations endpoints |
| **SERVICE** | `app/services/production_service.py`, `app/services/operation_service.py` |
| **UI** | `AdminProduction.jsx`, `ProductionOrderDetail.jsx`, `ProductionOrderModal.jsx`, `OperationsPanel.jsx`, `OperationCard.jsx`, `OperationsTimeline.jsx`, `ScrapEntryModal.jsx` |

**Forms**: Product, Quantity, Due Date, Priority, Operations Schedule

---

### 5. Items/Products

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `products`, `item_categories` |
| **MIGRATIONS** | `001_initial`, `023_sprint3_cleanup_product`, `031_add_stocking_policy`, `035_add_purchase_uom`, `055_add_product_image_url` |
| **API** | `GET/POST /items/`, `GET/PATCH/DELETE /items/{id}`, `GET/POST /items/categories`, `GET /items/low-stock`, bulk endpoints |
| **SERVICE** | `app/services/product_service.py` |
| **UI** | `AdminItems.jsx`, `ItemForm.jsx`, `ItemCard.jsx`, `ItemWizard.jsx`, `MaterialForm.jsx` |

**Forms**: SKU, Name, Description, Category, Item Type, Procurement Type, UOM, Costs, Reorder Point, Lead Time, Has BOM, UPC

---

### 6. Bill of Materials (BOM)

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `boms`, `bom_lines` |
| **MIGRATIONS** | `001_initial`, `056_migrate_bom_to_operations` |
| **API** | `GET/POST /admin/bom/`, `GET/PATCH/DELETE /admin/bom/{id}`, `POST /admin/bom/{id}/lines`, `GET /admin/bom/{id}/explode`, `GET /admin/bom/{id}/cost-rollup`, `GET /admin/bom/where-used/{product_id}` |
| **SERVICE** | `app/services/bom_service.py` |
| **UI** | `AdminBOM.jsx`, `BOMEditor.jsx` |

**Forms**: Product, Components (SKU, Quantity, Unit, Scrap Factor, Notes)

---

### 7. Routings & Manufacturing

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `routings`, `routing_operations`, `routing_operation_materials`, `work_centers`, `resources` |
| **MIGRATIONS** | `001_initial`, `022_sprint3_cleanup_work_center`, `033_add_operation_materials` |
| **API** | `GET/POST /routings/`, `GET/PATCH/DELETE /routings/{id}`, operations endpoints, materials endpoints, `GET/POST /work-centers/`, `GET/POST /resources/` |
| **SERVICE** | `app/services/routing_service.py`, `app/services/work_center_service.py` |
| **UI** | `AdminManufacturing.jsx`, `RoutingEditor.jsx`, `ManufacturingBOMEditor.jsx` |

**Forms**: Operations (Name, Work Center, Setup Time, Run Time, Materials)

---

### 8. Inventory

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `inventory`, `inventory_transactions`, `inventory_locations` |
| **MIGRATIONS** | `001_initial`, `018_add_negative_inventory_approval`, `021_add_performance_indexes`, `029_add_transaction_date` |
| **API** | `POST /inventory/adjust-quantity`, `POST /inventory/transactions/{id}/approve-negative`, `GET /inventory/negative-inventory-report`, `POST /inventory/validate-consistency` |
| **SERVICE** | `app/services/inventory_service.py`, `app/services/inventory_helpers.py` |
| **UI** | `AdminInventoryTransactions.jsx`, `AdminLocations.jsx`, `AdminCycleCount.jsx` (adjustment integrated in AdminItems) |

**Forms**: Product, Location, Quantity, Adjustment Reason, Unit, Notes

---

### 9. Material Spools

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `material_spools`, `production_order_spools` |
| **MIGRATIONS** | `017_add_material_spool_tracking` |
| **API** | `GET/POST /spools/`, `GET/PATCH /spools/{id}`, `POST /spools/{id}/consume`, `POST /spools/{id}/transfer` |
| **SERVICE** | `app/services/spool_service.py` |
| **UI** | `AdminSpools.jsx` |

**Forms**: Spool Number, Product, Initial Weight, Location, Supplier Lot, Expiry Date

---

### 10. Vendors

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `vendors` |
| **MIGRATIONS** | `001_initial` |
| **API** | `GET/POST /vendors/`, `GET/PATCH/DELETE /vendors/{id}` |
| **SERVICE** | N/A (CRUD only) |
| **UI** | `AdminPurchasing.jsx` (integrated), `VendorModal.jsx`, `VendorDetailPanel.jsx` |

**Forms**: Name, Contact, Email, Phone, Address, Payment Terms, Lead Time, Notes

---

### 11. Purchase Orders

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `purchase_orders`, `purchase_order_lines`, `po_documents` |
| **MIGRATIONS** | `001_initial`, `019_add_purchase_unit`, `027_backfill_po_received_date`, `036_add_po_documents_table` |
| **API** | `GET/POST /purchase-orders/`, `GET/PATCH/DELETE /purchase-orders/{id}`, `POST /purchase-orders/{id}/submit`, `POST /purchase-orders/{id}/receive`, documents endpoints, vendor-items endpoints, low-stock endpoints |
| **SERVICE** | `app/services/purchase_order_service.py`, `app/services/receiving_service.py` |
| **UI** | `AdminPurchasing.jsx`, `POCreateModal.jsx`, `PODetailModal.jsx`, `ReceiveModal.jsx`, `DocumentUploadPanel.jsx` |

**Forms**: Vendor, Items (Product, Qty, Unit Price, Unit), Expected Date, Notes

---

### 12. MRP (Material Requirements Planning)

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `mrp_runs`, `planned_orders` |
| **MIGRATIONS** | N/A (tables in initial schema) |
| **API** | `POST /mrp/run`, `GET /mrp/runs`, `GET /mrp/planned-orders`, `POST /mrp/planned-orders/{id}/firm`, `POST /mrp/planned-orders/{id}/release`, `GET /mrp/requirements`, `GET /mrp/supply-demand/{product_id}`, `GET /mrp/explode-bom/{product_id}` |
| **SERVICE** | `app/services/mrp.py` (1200+ lines) |
| **UI** | Integrated in `OrderDetail.jsx` (Material Requirements table), `AdminProduction.jsx` |

**No dedicated MRP UI page** - accessed through Order Detail and Production

---

### 13. Payments

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `payments` |
| **MIGRATIONS** | `001_initial` |
| **API** | `GET/POST /payments/`, `GET/PATCH/DELETE /payments/{id}`, `POST /payments/{id}/apply`, `GET /payments/by-order/{order_id}` |
| **SERVICE** | `app/services/payment_service.py` |
| **UI** | `AdminPayments.jsx`, `RecordPaymentModal.jsx` |

**Forms**: Order, Amount, Payment Method, Reference, Date, Notes

---

### 14. Negative Inventory Approval

**STATUS**: ⚠️ Backend Only | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `inventory_transactions.requires_approval`, `approved_by`, `approved_at`, `approval_reason` |
| **MIGRATIONS** | `018_add_negative_inventory_approval_columns` |
| **API** | `POST /inventory/transactions/{id}/approve-negative`, `GET /inventory/negative-inventory-report` |
| **SERVICE** | `app/services/inventory_service.py` |
| **UI** | **MISSING** - No approval modal or report page |

**Gap**: API exists for approving negative inventory transactions, but no UI to:

1. View pending approvals
2. Approve/deny with reason
3. View negative inventory report

**Remediation**: Add `NegativeInventoryApprovalModal.jsx` and integrate into inventory transactions page

---

### 15. Printers / Equipment

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `printers` (was `machines`) |
| **MIGRATIONS** | `001_initial`, `032_cleanup_machines_table` |
| **API** | `GET/POST /printers/`, `GET/PATCH/DELETE /printers/{id}`, `GET /printers/{id}/status`, `POST /printers/{id}/test-connection`, `POST /printers/discover` |
| **SERVICE** | `app/services/printer_service.py` |
| **UI** | `AdminPrinters.jsx` |

**Forms**: Name, Type, IP Address, Port, Status, Notes

---

### 16. Maintenance Logs

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `maintenance_logs` |
| **MIGRATIONS** | `025_add_maintenance_logs_table`, `026_add_maintenance_tracking_fields` |
| **API** | `GET/POST /maintenance/logs`, `GET/PATCH/DELETE /maintenance/logs/{id}`, `GET /maintenance/upcoming`, `GET /maintenance/overdue` |
| **SERVICE** | N/A (CRUD only) |
| **UI** | Integrated in `AdminPrinters.jsx` |

---

### 17. Traceability (Lots/Serials)

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | Tracked via `material_spools.supplier_lot_number`, `inventory_transactions` |
| **MIGRATIONS** | `017_add_material_spool_tracking` |
| **API** | `GET /traceability/forward/{serial}`, `GET /traceability/backward/{serial}`, `GET /traceability/lot/{lot_number}`, `GET /traceability/recall-impact`, admin traceability endpoints |
| **SERVICE** | `app/services/traceability_service.py` |
| **UI** | `MaterialTraceability.jsx` |

---

### 18. Scrap Tracking

**STATUS**: ✅ Complete | **TIER**: Core

| Layer | Implementation |
| ----- | -------------- |
| **DATABASE** | `scrap_reasons`, `scrap_records`, `production_order_operations.scrap_reason_id` |
| **MIGRATIONS** | `034_add_operation_scrap_reason`, `053_create_scrap_records_table`, `057_seed_scrap_reasons` |
| **API** | Integrated in production order operations endpoints |
| **SERVICE** | `app/services/scrap_service.py` |
| **UI** | `AdminScrapReasons.jsx`, `ScrapEntryModal.jsx` |

---

## Gap Summary

### ⚠️ Backend Only (API exists, no UI)

| Feature | API Endpoint | Missing UI |
| ------- | ------------ | ---------- |
| Negative Inventory Approval | `POST /inventory/transactions/{id}/approve-negative` | Approval modal/workflow |
| Negative Inventory Report | `GET /inventory/negative-inventory-report` | Report page/tab |

### 🚧 Partial Implementation

| Feature | Issue |
| ------- | ----- |
| MRP | No dedicated page - embedded in Order Detail |

---

## Cross-Reference Quick Lookup

### By Database Table

| Table | Feature | API Prefix |
| ----- | ------- | ---------- |
| `users` | Authentication | `/auth` |
| `sales_orders` | Sales Orders | `/sales-orders` |
| `quotes` | Quotes | `/quotes` |
| `production_orders` | Production | `/production-orders` |
| `products` | Items | `/items` |
| `boms` | BOM | `/admin/bom` |
| `routings` | Manufacturing | `/routings` |
| `inventory` | Inventory | `/inventory` |
| `material_spools` | Spools | `/spools` |
| `vendors` | Vendors | `/vendors` |
| `purchase_orders` | Purchasing | `/purchase-orders` |
| `planned_orders` | MRP | `/mrp` |
| `payments` | Payments | `/payments` |
| `printers` | Equipment | `/printers` |
| `maintenance_logs` | Maintenance | `/maintenance` |

### By UI Page

| Page | Features Included |
| ---- | ----------------- |
| `AdminDashboard.jsx` | KPIs, Recent Orders, Alerts |
| `AdminOrders.jsx` | Sales Orders |
| `OrderDetail.jsx` | Order, MRP, Payments, Fulfillment |
| `AdminItems.jsx` | Products, Categories, Inventory Adjustment |
| `AdminBOM.jsx` | BOM Management |
| `AdminProduction.jsx` | Production Orders |
| `ProductionOrderDetail.jsx` | Operations, Scrap, Materials |
| `AdminPurchasing.jsx` | POs, Vendors, Documents |
| `AdminPrinters.jsx` | Printers, Maintenance |
| `AdminSpools.jsx` | Material Spools |
| `AdminSettings.jsx` | Configuration |

---

*Last updated: 2026-01-28*
*Generated for FilaOps Core (Open Source)*
