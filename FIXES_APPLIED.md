# Fixes Applied - Production Order Issues

## Issues Fixed

### 1. ✅ CORS Configuration
**Problem**: CORS errors blocking API requests

**Fix**: 
- Updated `main.py` to ensure `ALLOWED_ORIGINS` is always a list
- Updated `settings.py` validator to handle string/list conversion properly
- Added fallback to allow all origins if empty

**Files**:
- `backend/app/main.py` lines 152-158
- `backend/app/core/settings.py` lines 199-209, 211-221

---

### 2. ✅ Work Center Resources/Machines
**Problem**: No machines in work center dropdown

**Fix**: Updated test script to create a Resource (machine) for the work center

**File**: `backend/scripts/test_order_to_ship_workflow.py` lines 609-625

**Note**: You manually added a printer to the WC, but it needs to be a `Resource` record, not a `Printer` record. The system uses `Resource` model for scheduling.

---

### 3. ✅ Scrap Modal Debug Logging
**Problem**: Scrap reason dropdown not populating

**Fix**: Added console logging to debug API response

**File**: `frontend/src/components/ScrapOrderModal.jsx` lines 24-42

**Next Steps**: 
- Open browser console (F12) when opening scrap modal
- Check what "Scrap reasons API response:" shows
- Verify `data.details` contains the reason objects

---

### 4. ✅ Start Production Order Request Body
**Problem**: Start Now button failing

**Fix**: Updated frontend to send empty JSON body `{}` for start action

**File**: `frontend/src/pages/admin/AdminProduction.jsx` lines 185-197

---

## Testing Steps

1. **Restart Backend** (to apply CORS fixes):
   ```powershell
   cd C:\BLB3D_Production_DEV\backend
   .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
   ```

2. **Check Scrap Reasons**:
   - Open browser console (F12)
   - Open scrap modal on a production order
   - Check console for "Scrap reasons API response:" log
   - Verify `data.details` array has items

3. **Check Work Center Resources**:
   - Go to Manufacturing > Work Centers
   - Expand your work center
   - Verify resources/machines are listed
   - If not, create a Resource via the UI or run test script again

4. **Test Start Production**:
   - Try "Start Now" button again
   - Check browser console for CORS errors
   - If still failing, check Network tab for actual error response

---

## Known Issues

1. **Scrap Reasons**: If dropdown is still empty, check:
   - Are scrap reasons actually in the database? (run test script)
   - Is the API returning data? (check Network tab)
   - Is the response format correct? (check console logs)

2. **Resources**: The work center needs `Resource` records, not `Printer` records. These are different models:
   - `Printer` = Bambu printer integration
   - `Resource` = Scheduling resource (can be linked to Printer)

3. **CORS**: If still getting CORS errors:
   - Verify frontend is running on port 5174
   - Verify backend is running on port 8002
   - Check `.env.dev` has correct `FRONTEND_URL` and `VITE_API_URL`

