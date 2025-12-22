# Issues Fixed - Production Order Workflow

## Summary of Issues and Fixes

### 1. ✅ Work Center Dropdown Empty
**Problem**: Work center dropdown was empty when trying to assign to work center.

**Root Cause**: Test script created work center with `center_type="production"` but frontend filters for `center_type="machine"`.

**Fix**: Changed test script to create work center with `center_type="machine"` so it appears in dropdowns.

**File**: `backend/scripts/test_order_to_ship_workflow.py` line 592

---

### 2. ✅ Start Production Order Error
**Problem**: Clicking "Start Now" on production order got "Failed to update status: Unknown error".

**Root Cause**: 
- Frontend was calling `/api/v1/production-orders/{id}/start` without a request body
- Endpoint expects `StartProductionOrderRequest` (even if empty)
- Also had a bug in `explode_bom_and_reserve_materials` returning `[], []` instead of `[], [], []`

**Fixes**:
1. Fixed return statement in `production_execution.py` to return 3 empty lists
2. Updated frontend to send empty JSON body `{}` for start action

**Files**:
- `backend/app/services/production_execution.py` line 127
- `frontend/src/pages/admin/AdminProduction.jsx` line 185-194

---

### 3. ⚠️ Scrap Function Not Populating
**Problem**: Reason codes are listed, but scrap function will not populate on WO.

**Status**: Investigating - The scrap modal appears to be correctly fetching from `/api/v1/production-orders/scrap-reasons` which returns `{ reasons: [], details: [], descriptions: {} }`. The modal uses `data.details` which should work.

**Possible Issues**:
- API might be returning empty array if no scrap reasons exist
- Frontend might not be handling the response correctly
- Modal might not be opening properly

**Next Steps**: Check browser console for errors when opening scrap modal.

---

### 4. ✅ Remove WO Status Advancement on SO
**Problem**: Need to remove ability to advance WO status from sales order page.

**Status**: Already fixed - The OrderDetail.jsx page only shows production orders with a "View →" button. No status change buttons exist on the sales order page.

**File**: `frontend/src/pages/admin/OrderDetail.jsx` lines 988-1013

---

### 5. ✅ Test Script Improvements
**Fixed Issues**:
- ✅ Customer number generation
- ✅ Customer address (billing & shipping)
- ✅ Payment record creation
- ✅ Shipping address on sales order
- ✅ Work centers and routings (with graceful error handling)
- ✅ BOM UOM changed from KG to G (500g instead of 0.5 KG)
- ✅ Inventory transactions created when receiving PO
- ✅ Scrap reason codes seeded
- ✅ Company settings for tax
- ✅ Only receives latest PO if multiple exist
- ✅ Summary shows transactions and clarifies order hasn't shipped

---

## Remaining Issues to Investigate

1. **Scrap Modal**: Need to verify scrap reasons are loading correctly
2. **Shipping Screen**: Not showing past shipments (separate issue)
3. **Payments Tab**: White screen (separate issue)
4. **Accounting Transactions**: May need separate implementation
5. **PO → WO Link**: Purchase order may not display related work orders (display issue)

---

## Testing Checklist

- [ ] Work center dropdown populates correctly
- [ ] "Start Now" button works without errors
- [ ] Scrap modal opens and populates reason codes
- [ ] Scrap submission works correctly
- [ ] Production orders cannot have status changed from sales order page
- [ ] Test script creates all data correctly

