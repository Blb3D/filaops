# Accounting Module Test Plan

## Prerequisites
- [ ] Run database migration: `009_accounting_enhancements.py`
- [ ] Rebuild containers: `docker-compose build && docker-compose up -d`
- [ ] Have at least a few test orders in different states (pending, paid, shipped, cancelled)
- [ ] Have at least one payment recorded

---

## 1. Navigation & Access

### 1.1 Admin Navigation
- [ ] Login as admin user
- [ ] Verify "Accounting" appears in ADMIN section of sidebar
- [ ] Click Accounting - page loads without errors
- [ ] Verify all 5 tabs are visible: Dashboard, Sales Journal, Payments, COGS & Materials, Tax Center

### 1.2 Operator Access (if multi-user enabled)
- [ ] Login as operator user
- [ ] Verify "Accounting" does NOT appear in sidebar (admin-only feature)

---

## 2. Dashboard Tab

### 2.1 Revenue Cards
- [ ] Revenue MTD shows a dollar amount
- [ ] Revenue MTD shows order count that matches Orders page filter for current month
- [ ] Revenue YTD shows cumulative amount from fiscal year start
- [ ] Revenue YTD order count is >= MTD count

### 2.2 Payments Cards
- [ ] Payments Received MTD matches Payments page totals for current month
- [ ] Outstanding amount shows sum of unpaid/partially paid orders
- [ ] Outstanding orders count matches orders with payment_status = pending or partial

### 2.3 Tax & COGS Cards
- [ ] Tax Collected MTD shows sum of tax_amount from current month orders
- [ ] COGS MTD shows costs from shipped orders this month
- [ ] Gross Profit = Revenue - COGS - Tax (verify calculation)
- [ ] Margin % is calculated correctly: (Gross Profit / Revenue) * 100

### 2.4 Manual Verification
```
Compare Dashboard numbers with:
- Orders page: Filter by date, sum grand_total manually
- Payments page: Filter by date, sum amounts
- Calculate expected values in spreadsheet
```

---

## 3. Sales Journal Tab

### 3.1 Data Display
- [ ] Default shows last 30 days of orders
- [ ] Table shows: Date, Order #, Product, Subtotal, Tax, Total, Status
- [ ] Totals row shows correct sums for all columns
- [ ] Order count matches number of rows

### 3.2 Date Filtering
- [ ] Change start date - table updates
- [ ] Change end date - table updates
- [ ] Set date range with no orders - shows "No sales in this period"
- [ ] Totals update when date range changes

### 3.3 Status Badges
- [ ] Paid orders show green "paid" badge
- [ ] Partial payments show yellow "partial" badge
- [ ] Pending payments show gray "pending" badge

### 3.4 CSV Export (Generic)
- [ ] Click "Export CSV" button
- [ ] File downloads with name like `sales_journal_YYYYMMDD_YYYYMMDD.csv`
- [ ] Open in Excel/Google Sheets
- [ ] Verify columns: Date, Order Number, Status, Payment Status, Source, Product, Quantity, Subtotal, Tax Rate, Tax Amount, Shipping, Grand Total, Paid Date, Shipped Date
- [ ] Spot check 3-5 rows against UI data
- [ ] Verify totals match UI totals

### 3.5 QuickBooks Export
- [ ] Click "Export for QuickBooks" button
- [ ] File downloads
- [ ] Open in text editor, verify IIF format:
  - Header rows: `!TRNS`, `!SPL`, `!ENDTRNS`
  - Each order has TRNS line (debit to A/R)
  - SPL lines for: Sales Income, Sales Tax Payable, Shipping Income
  - ENDTRNS after each order
- [ ] Amounts should balance: TRNS amount = sum of SPL amounts (opposite signs)

---

## 4. Payments Tab

### 4.1 Data Display
- [ ] Default shows last 30 days of payments
- [ ] Table shows: Date, Payment #, Order #, Method, Amount, Type
- [ ] Summary cards show: Payments, Refunds, Net, Transaction count

### 4.2 By Method Breakdown
- [ ] Cards appear for each payment method used (cash, credit_card, etc.)
- [ ] Amounts per method sum to total payments

### 4.3 Date Filtering
- [ ] Change dates - data updates
- [ ] Totals update correctly

### 4.4 Refund Display
- [ ] Refunds show in red with negative amount
- [ ] Refund type badge shows "refund"
- [ ] Refunds counted in Refunds total, not Payments

### 4.5 CSV Export
- [ ] Click "Export CSV"
- [ ] Verify columns: Date, Payment Number, Order Number, Type, Method, Amount, Transaction ID, Notes
- [ ] Spot check data accuracy

---

## 5. COGS & Materials Tab

### 5.1 Period Selection
- [ ] Default shows "Last 30 days"
- [ ] Change to 7 days - data updates
- [ ] Change to 90 days - data updates
- [ ] Change to 365 days - data updates

### 5.2 Summary Cards
- [ ] Orders Shipped count matches shipped orders in period
- [ ] Revenue matches sum of order totals
- [ ] Total COGS shows sum of all cost categories
- [ ] Gross Profit = Revenue - COGS

### 5.3 COGS Breakdown
- [ ] Materials shows material consumption costs
- [ ] Labor shows labor/service costs (if tracked)
- [ ] Packaging shows packaging material costs
- [ ] Shipping shows shipping costs from orders
- [ ] Total matches sum of all categories

### 5.4 Edge Cases
- [ ] Period with no shipped orders - shows $0 values
- [ ] Order without production order - only shipping cost counted

---

## 6. Tax Center Tab

### 6.1 Period Selection
- [ ] "This Month" shows current month name and year
- [ ] "This Quarter" shows Q1/Q2/Q3/Q4 and year
- [ ] "This Year" shows current year
- [ ] Data updates when period changes

### 6.2 Summary Cards
- [ ] Total Sales = Taxable + Non-Taxable
- [ ] Tax Collected matches sum of tax_amount from orders
- [ ] Order count matches actual orders in period

### 6.3 By Tax Rate Table
- [ ] Shows breakdown by different tax rates used
- [ ] Rate % is displayed correctly (e.g., 8.25% not 0.0825)
- [ ] Per-rate totals sum to overall totals

### 6.4 Monthly Breakdown Table
- [ ] Shows each month in the selected period
- [ ] Monthly totals sum to period totals
- [ ] Order counts per month are correct

### 6.5 Export for Filing
- [ ] Click "Export for Filing"
- [ ] CSV downloads
- [ ] Contains all orders with: Date, Order Number, Taxable (Yes/No), Subtotal, Tax Rate %, Tax Amount, Grand Total, Payment Status
- [ ] TOTALS row at bottom with sums
- [ ] Verify tax amounts match order data

---

## 7. API Direct Testing (Optional - via curl or Postman)

### 7.1 Dashboard Endpoint
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/admin/accounting/dashboard"
```
- [ ] Returns 200 OK
- [ ] JSON has: as_of, fiscal_year_start, revenue, payments, tax, cogs, profit

### 7.2 Sales Journal Endpoint
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/admin/accounting/sales-journal?start_date=2025-01-01T00:00:00&end_date=2025-12-31T23:59:59"
```
- [ ] Returns 200 OK
- [ ] JSON has: period, totals, entries array

### 7.3 Tax Summary Endpoint
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/admin/accounting/tax-summary?period=quarter"
```
- [ ] Returns 200 OK
- [ ] JSON has: period, period_start, period_end, summary, by_rate, monthly_breakdown

### 7.4 Payments Journal Endpoint
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/admin/accounting/payments-journal"
```
- [ ] Returns 200 OK
- [ ] JSON has: period, totals, by_method, entries

---

## 8. Edge Cases & Error Handling

### 8.1 Empty Data
- [ ] New install with no orders - Dashboard shows $0 values, no errors
- [ ] Date range with no data - Tables show empty state message

### 8.2 Null/Missing Data
- [ ] Order with null tax_amount - Treated as $0, no errors
- [ ] Order with null shipping_cost - Treated as $0
- [ ] Payment with null amount - Treated as $0

### 8.3 Cancelled Orders
- [ ] Cancelled orders excluded from all calculations
- [ ] Cancelled orders don't appear in Sales Journal (default)

### 8.4 Large Numbers
- [ ] Currency formatting handles $10,000+ amounts
- [ ] No overflow in UI cards

---

## 9. Database Migration Verification

### 9.1 New Columns Added
```sql
-- Check sales_orders table
SELECT tax_rate, is_taxable FROM sales_orders LIMIT 5;
```
- [ ] tax_rate column exists (NUMERIC 5,4)
- [ ] is_taxable column exists (BOOLEAN)

### 9.2 Existing Data Migration
- [ ] Existing orders with tax_amount > 0 have is_taxable = 1
- [ ] Existing orders with tax_amount = 0 have is_taxable = 0

### 9.3 Company Settings
```sql
SELECT fiscal_year_start_month, accounting_method, currency_code
FROM company_settings;
```
- [ ] fiscal_year_start_month defaults to 1 (January)
- [ ] accounting_method defaults to 'cash'
- [ ] currency_code defaults to 'USD'

---

## 10. Cross-Reference Validation

### Manual Calculation Check
Pick 3-5 orders and manually verify:

| Order # | Subtotal | Tax | Shipping | Grand Total | Calculated Total |
|---------|----------|-----|----------|-------------|------------------|
|         |          |     |          |             | Sub+Tax+Ship     |

- [ ] All grand_totals match calculated totals
- [ ] Sales Journal totals match sum of individual orders
- [ ] Tax Center tax_collected matches sum of tax_amount

---

## Sign-Off

| Test Section | Tester | Date | Pass/Fail | Notes |
|--------------|--------|------|-----------|-------|
| Navigation   |        |      |           |       |
| Dashboard    |        |      |           |       |
| Sales Journal|        |      |           |       |
| Payments     |        |      |           |       |
| COGS         |        |      |           |       |
| Tax Center   |        |      |           |       |
| API Tests    |        |      |           |       |
| Edge Cases   |        |      |           |       |
| Migration    |        |      |           |       |
| Cross-Ref    |        |      |           |       |

**Overall Status:** [ ] PASS / [ ] FAIL

**Notes:**
