# Changelog

All notable changes to FilaOps will be documented in this file.

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
  - Organized scripts by purpose (github/, database/, tools/)
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

