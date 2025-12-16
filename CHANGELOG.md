# Changelog

All notable changes to FilaOps will be documented in this file.

## [1.5.0] - 2025-12-16

### Added

- **Scrap Order Workflow**: Comprehensive print failure tracking and recovery system
  - New scrap modal with quantity selection for partial or full scrap
  - Configurable scrap reasons with admin management page (`/admin/scrap-reasons`)
  - 14 pre-seeded scrap reasons common to 3D printing (adhesion failure, layer shift, spaghetti, warping, etc.)
  - Automatic remake order creation for scrapped prints
  - Material cost tracking for scrapped units (proper UOM conversion from g→kg)
  - Order stays in-progress for partial scraps, allowing work to continue on remaining units
- **MTS Overrun Support**: Record more completed parts than ordered quantity
  - Complete Order modal with quantity input field
  - Extra units automatically added to inventory as Make-to-Stock
  - Blue "MTS Overrun" indicator showing how many extra units produced
- **Scrap Reasons Admin Page**: Full CRUD management for failure codes
  - Add/edit/delete scrap reasons
  - Code, name, and description fields
  - Sequence ordering and active/inactive toggle
  - Used by scrap modal dropdown
- New migrations: `010_merge_heads.py`, `011_add_scrap_reasons.py`
- New model: `ScrapReason` with code, name, description, active, sequence fields
- New components: `ScrapOrderModal.jsx`, `CompleteOrderModal.jsx`, `AdminScrapReasons.jsx`
- Updated `production_orders.py` with scrap reasons CRUD and partial scrap logic
- Added `quantity_scrapped` parameter to scrap endpoint with validation

### Changed

- **Production Order Completion**: Now uses dedicated modal with quantity input instead of single-click status change
- **Scrap Modal**: Shows order details (ordered, completed, remaining quantities) with partial scrap support

### Fixed

- **Route Ordering**: Fixed scrap-reasons endpoint being matched by `/{order_id}` route (moved static routes before path parameters)
- **UOM Conversion in Scrap**: Fixed material cost calculation for scrap transactions (was showing raw grams cost instead of converting to kilograms)

## [1.4.0] - 2025-12-15

### Added

- **Enhanced MRP System**: Major improvements to Material Requirements Planning
  - Full BOM explosion with multi-level component requirements
  - Unit of Measure (UOM) conversion support for mixed-unit BOMs (e.g., G to KG)
  - Sub-assembly due date cascading (configurable via `MRP_ENABLE_SUB_ASSEMBLY_CASCADING`)
  - MRP trigger service for automatic recalculation on order events
  - New MRP tracking fields on sales orders
- **Dashboard Reorganization**: Improved admin dashboard layout
  - Grouped metrics into Sales, Inventory, and Operations sections
  - Clickable StatCards that navigate to relevant pages
  - "View all →" quick links on section headers
- **Locations Management**: New admin page for inventory locations (`/admin/locations`)
  - CRUD operations for warehouse locations
  - Location hierarchy support
- **Production Order Improvements**:
  - Unique constraint on production order codes (prevents duplicates)
  - Auto-transition sales orders to "ready_to_ship" when production completes
  - Material availability checking with UOM awareness

### Fixed

- **BOM Issues** (Issue #55): Multiple BOM-related bugs resolved
  - Units now display correctly (G, KG, M) instead of defaulting to "EA"
  - BOM line updates work properly (fixed 405 Method Not Allowed error)
  - Scrap factor calculation now correct in cost display
  - UOM conversion for cost when BOM line unit differs from component unit
- **Lint Errors**: Fixed E402 import ordering and removed redundant logger recreation

### Security

- Removed hardcoded printer credentials from codebase
- Replaced personal email with business contact email

### Technical

- New migrations: `006_add_mrp_tracking_to_sales_orders.py`, `007_ensure_production_order_code_unique.py`
- Added `mrp_trigger_service.py` for automatic MRP recalculation
- Enhanced `uom_service.py` with database-backed conversion
- Added `qty_needed` field to BOM response showing effective quantity with scrap

## [1.3.1] - 2025-12-12

### Fixed

- **Remote Access Login Issue** (Issue #50): Fixed "Failed to fetch" error for network access
  - Login page shows warning with instructions to set `VITE_API_URL`
- **No Colors Available** (Issue #44): Seed data now includes 15 basic colors
  - BambuLab-style materials linked to common colors
- **Setup Wizard UX**: Clearer messaging about seed data
- **CI/Test Fixes**: Resolved ruff lint errors, fixed test database setup

## [1.3.0] - 2025-12-11

### Added

- **Split Production Orders**: Split large production runs across multiple machines or batches
  - Split released orders into 2+ child orders with custom quantity allocation
  - Child orders track independently (PO-2025-001-A, PO-2025-001-B, etc.)
  - Parent order shows "split" status with links to children
  - Kanban board shows split orders grouped under parent
- **Production Kanban View**: Visual drag-and-drop production board
  - Columns: Released, Queued, In Progress, QC, Complete
  - Drag orders between stages to update status
  - Color-coded priority indicators
  - Click to view order details
- **Inventory Allocation**: Reserve materials when production starts
  - Items page shows Reserved and Available quantities
  - Reserved qty deducted from available for planning
  - Visual indicators for allocation status
- **Complete Shipping Workflow**: Full order-to-ship flow
  - Shipping address capture on Order Detail page
  - Edit address inline with validation
  - Ship modal with carrier selection (USPS, FedEx, UPS)
  - Manual tracking number entry
  - Quick links to carrier websites for label creation
- **Purchasing Module Refactor**: Extracted components for maintainability
  - VendorModal, POCreateModal, PODetailModal components
  - ReceiveModal with improved UX
  - ProductSearchSelect reusable component
  - VendorDetailPanel with metrics

### Changed

- **Items Page**: Added Reserved/Available columns, hidden prices for materials/supplies
- **Production Orders**: Default quantity_completed to quantity_ordered on completion
- **Work Order Navigation**: Fixed deep linking with search params

### Fixed

- **Shipping Address Display**: Address fields now correctly parsed and displayed
- **Production Completion**: Fixed 0% completion bug (quantity_completed now defaults properly)
- **Work Order Detail**: Fixed white screen when clicking "View" on work orders
- **Ship Endpoint**: Created proper `/ship` endpoint with carrier and tracking support

### Technical

- New migrations: `003_add_sales_order_product_id.py`, `004_add_production_order_split.py`
- Added `SalesOrderUpdateAddress` schema for address PATCH endpoint
- Added `ProductionOrderSplitRequest/Response` schemas
- Split order status added to production order state machine

## [1.2.0] - 2025-12-11

### Added

- **Company Settings**: New admin settings page (`/admin/settings`) for business configuration
  - Company information (name, address, contact details)
  - Logo upload with image storage in database
  - Tax configuration (rate, name, registration number, enable/disable)
  - Quote defaults (validity days, terms, footer)
- **Quote Management**: Full quoting system with professional PDF generation
  - Create and manage quotes linked to customers
  - Per-quote product image upload
  - Tax calculation based on company settings
  - Professional PDF export with company logo, product image, and formatted layout
  - Compact single-page PDF layout with two-column design
- **Toast Notification System**: Global toast notifications across all admin pages
  - Success/error/warning/info notification types
  - Auto-dismiss with configurable duration
  - Manual dismiss capability
  - Consistent feedback for all CRUD operations

### Changed

- **Admin Navigation**: Added Settings menu item for company configuration
- **Quote PDFs**: Redesigned to professional single-page layout with image beside quote details

### Technical

- New database migration for company_settings table and quote enhancements
- ReportLab PDF generation with dynamic layouts
- Authenticated image endpoints with blob URL handling in React

## [1.1.0] - 2025-12-10

### Added

- **Multi-User Management**: Full team management for admin and operator accounts
  - Admin users API with CRUD operations, password reset, and user activation/deactivation
  - Team Members UI (`/admin/users`) with stats dashboard, filtering, and search
  - Role-based navigation - operators see limited menu (no imports, analytics, transactions)
  - Staff login supporting both admin and operator account types
- **Operator Role**: New account type with restricted access to core operations
  - Can access: Dashboard, Orders, Production, Manufacturing, Inventory, Shipping
  - Cannot access: User management, Analytics, Imports, Inventory Transactions
- **Filament Filter**: Added "Filament" option to Items page filter dropdown
  - Filters items with material_type_id (supplies that are filament materials)
  - Orange badge styling for filament items

### Changed

- **Login Page**: Renamed to "Staff Login" to reflect multi-user support
- **README**: Updated tier structure - Multi-user now in Community (free) tier
- **Item Type Colors**: Supply items now use yellow badges (filaments use orange)

### Fixed

- **Critical: Frontend Build Failure** (Issue #40): Fixed missing `frontend/index.html`
  - Root cause: `.gitignore` had `*.html` which excluded the Vite entry point
  - Docker builds now work correctly for new installations
- **AdminManufacturing Crash**: Fixed undefined state variables when opening routing modal
  - Added missing `editingRouting` and `routingProductId` useState declarations
- **SQL Server Boolean Comparisons**: Changed `.is_(True)` to `== True` across 23 files
- **Customer Number Index**: Fixed unique constraint to allow multiple NULLs for non-customers
- **Import Order Issues**: Created shared limiter module to fix circular import problems
- **Pydantic Schema**: Use correct schema for locations in InventoryCheckResponse

### Improved

- **Order Workflow UX**: "Advance" button now shows target status (e.g., "→ Confirmed")
- **Shipping Address Validation**: Clear error message with link to edit order when address missing
- **Security**: Password hashing, refresh token revocation on password reset
- **Authorization**: Protection against self-deactivation and last-admin removal

## [1.0.1] - 2025-12-09

### Changed

- **Repository Organization**: Reorganized documentation structure for better collaboration
  - Moved 75+ markdown files into organized `docs/` subdirectories (architecture, planning, history, development, sessions)
  - Organized scripts by purpose (GitHub/, database/, tools/)
  - Cleaned root directory to only essential user-facing documentation
  - Added documentation index and organization guide

### Technical

- **Type Checking**: Added mypy type checking infrastructure
  - Configured mypy in `pyproject.toml` with SQLAlchemy plugin support
  - Integrated type checking into CI pipeline
  - Documented SQLAlchemy ORM type inference limitations
- **Code Quality**: Completed Issue #27 improvements
  - Standardized logging across 15+ files to use structured logger
  - Removed duplicate logger setups
  - Added type checking dependencies to requirements.txt
- **CI/CD**: Enhanced GitHub Actions workflow
  - Added mypy type checking step (non-blocking)
  - Improved code quality checks

### Fixed

- Removed workspace files from repository
- Updated `.gitignore` to exclude workspace files

## [Unreleased]

### Added

- **Unified Item Master**: Single `Products` table for all item types (finished goods, components, supplies, materials)
- **Inventory Transactions**: Complete transaction system for receipts, issues, transfers, adjustments, consumption, and scrap
- **Order Command Center**: Comprehensive order detail page with MRP explosion, material/capacity requirements, and shortage detection
- **Dashboard Improvements**: Real-time KPIs including overdue orders, low stock items (with MRP integration), and revenue metrics
- **SKU Auto-generation**: Automatic SKU generation based on item type (FG, CP, SP, SV prefixes)
- **BOM Editor**: Standalone BOM editor with material support and explicit unit of measure
- **Routing Editor**: Full routing operation management with work center integration
- **Shipping Enhancements**: Production status validation, multi-carrier support, integration with Order Command Center
- **Low Stock with MRP**: Enhanced low stock alerts to include shortages from active sales orders
- **Customer Management**: Full customer CRUD with navigation from order creation workflow

### Changed

- **Material System**: Materials now use unified `Products` table instead of separate `MaterialInventory` table
- **BOM Lines**: Added explicit `unit` field and `is_cost_only` flag for better cost tracking
- **Order Creation**: Improved workflow with navigation to full customer/item pages instead of inline forms
- **Dashboard**: Enhanced with actionable alerts and improved data accuracy

### Fixed

- **SQL Server Compatibility**: Fixed `created_at` timestamp issues for customer creation and refresh tokens
- **Dashboard Queries**: Corrected column references (`estimated_completion_date` instead of `ship_by_date`)
- **Low Stock Calculation**: Fixed to properly aggregate inventory across locations and include MRP shortages
- **Order Authorization**: Admin users can now view and manage all orders
- **Frontend Theming**: Consistent dark theme across all pages (including RoutingEditor)
- **Ship Order Logic**: Added validation to prevent shipping orders with incomplete production or material shortages

### Technical

- **MRP Refactor**: Completed Phase 5 of MRP refactoring plan
- **Database Schema**: Unified product model with material type and color relationships
- **API Endpoints**: New endpoints for inventory transactions and enhanced dashboard data
- **Frontend Components**: Simplified item creation, separate BOM/Routing editors, Order Command Center

## [Previous Versions]

See git history for earlier changes.
