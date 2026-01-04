# Debugging Guide - CORS and API Connection Issues

## Current Issues
1. **Production Start Now Error** - CORS blocking requests
2. **No Work Centers in Schedule Modal** - API calls failing
3. **No Scrap Reason Codes** - API calls failing

## Root Cause
All three issues are caused by **CORS errors** preventing the frontend from calling the backend API.

## Debugging Steps

### 1. Verify Backend is Running
Check if the backend is running on port 8000:
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000
```

If not running, start it:
```powershell
cd C:\repos\filaops\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Check Browser Console
Open browser DevTools (F12) and check:
- **Console tab**: Look for error messages showing the API URL being called
- **Network tab**: Check if requests are being blocked (red/failed)
  - Look for OPTIONS requests (preflight) - these should return 200 OK
  - Check response headers for `Access-Control-Allow-Origin`

### 3. Verify API URL Configuration
The frontend uses `VITE_API_URL` environment variable or defaults to `http://localhost:8000`.

Check `.env` in the project root:
```env
VITE_API_URL=http://localhost:8000
```

If changed, restart the frontend dev server.

### 4. Check CORS Configuration
The backend should log CORS origins at startup:
```
INFO: CORS configured with X allowed origins: [...]
```

Verify `http://localhost:5174` is in the list.

### 5. Test API Directly
Try calling the API directly from browser console:
```javascript
fetch('http://localhost:8000/api/v1/work-centers/?center_type=machine&active_only=true', {
  headers: { 'Authorization': 'Bearer YOUR_TOKEN' }
})
.then(r => r.json())
.then(console.log)
.catch(console.error)
```

### 6. Common Fixes

#### Backend Not Running
- Start backend: `cd backend && .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

#### Wrong Port
- Frontend expects backend on port 8000
- Check `.env` has `VITE_API_URL=http://localhost:8000`
- Restart frontend after changing `.env`

#### CORS Not Allowing Frontend Origin
- Backend defaults include `http://localhost:5173`
- If using a different port, add it to `.env`:
  ```env
  ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
  ```
- Restart backend after changing CORS settings

#### Token Expired
- Log out and log back in to get a fresh token
- Check `localStorage.getItem('adminToken')` in browser console

## Expected Console Output

When working correctly, you should see:
```
Fetching work centers from: http://localhost:8000/api/v1/work-centers/?center_type=machine&active_only=true
Work centers response: 200 OK
Work centers data: [...]
```

When failing, you'll see:
```
Error fetching scrap reasons: TypeError: Failed to fetch
Network error: Failed to fetch. Is the backend running on http://localhost:8000?
```

## Next Steps After Fixing CORS

1. **Work Centers**: Should populate in schedule modal dropdown
2. **Scrap Reasons**: Should load and populate dropdown
3. **Start Production**: Should work without CORS errors

If CORS is fixed but issues persist, check:
- Are work centers actually created? (run test script)
- Are scrap reasons in database? (check Admin → Scrap Reasons)
- Are resources created for work centers? (check Manufacturing → Work Centers)

