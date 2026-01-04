# FilaOps Upgrade Guide

**Simple step-by-step instructions to upgrade your FilaOps installation.**

> **📝 Note for Maintainers:** When creating a new release, update version placeholders (`vX.X.X`) in this file with the actual version number. Users will see the latest version in Settings → Version & Updates.

---

## 📌 Finding the Latest Version

**Before upgrading, find the latest version:**

1. **In the app:** Go to Settings → Version & Updates (shows latest available)
2. **On GitHub:** Visit https://github.com/Blb3D/filaops/releases
3. **Via command:** `git fetch --tags && git tag --sort=-v:refname | head -1`

**Replace `vX.X.X` in the commands below with the actual latest version!**

---

## ⚠️ Before You Start

1. **Backup your database** (recommended for production)
   ```bash
   # PostgreSQL backup
   pg_dump -U filaops_user filaops > filaops_backup_$(date +%Y%m%d).sql
   ```
   Or using pgAdmin: Right-click database → Backup

2. **Note your current version**
   - Check in Settings → Version & Updates, or run: `git describe --tags`

3. **Find the latest version** (see above)

4. **Allow 5-10 minutes** for the upgrade process

5. **Stop FilaOps** before upgrading
   - Press `Ctrl+C` in both backend and frontend terminal windows

---

## Quick Upgrade (Native Installation)

### Step 1: Open Terminal/Command Prompt

**Windows:**
- Press `Win + X` → Select "Terminal" or "PowerShell"
- Or search for "PowerShell" in Start Menu

**Mac/Linux:**
- Press `Cmd + Space` (Mac) or `Ctrl + Alt + T` (Linux)
- Type "Terminal" and press Enter

### Step 2: Navigate to Your FilaOps Folder

```bash
# Replace with YOUR actual FilaOps folder location
cd C:\FilaOps
# OR
cd ~/filaops
# OR wherever you installed FilaOps
```

**💡 Tip:** If you're not sure where FilaOps is installed, look for a folder containing `backend/` and `frontend/` subdirectories

### Step 3: Stop FilaOps

**Stop the running services:**
- In Terminal 1 (backend): Press `Ctrl+C`
- In Terminal 2 (frontend): Press `Ctrl+C`

**If running as a system service:**
```bash
# Linux (systemd)
sudo systemctl stop filaops-backend

# Windows (NSSM)
nssm stop FilaOpsBackend

# All platforms (PM2 for frontend)
pm2 stop filaops-frontend
```

### Step 4: Get the Latest Code

```bash
# Get all available versions
git fetch --tags

# Find the latest version
git tag --sort=-v:refname | head -1

# Checkout the latest version (replace vX.X.X with the version from above)
git checkout vX.X.X
```

**💡 Tip:** The latest version is usually the highest number. For example: v1.6.0 is newer than v1.5.0

**❌ If you get "git is not recognized":**
- Install Git: https://git-scm.com/downloads
- Or download the latest release ZIP from GitHub and extract it

**❌ If you get "not a git repository":**
- You installed from ZIP, not git
- Download the latest release ZIP from: https://github.com/Blb3D/filaops/releases
- Extract it to your FilaOps folder (replace old files)

### Step 5: Update Backend Dependencies

```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # Mac/Linux
.\venv\Scripts\activate   # Windows

# Update Python packages
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations (CRITICAL - don't skip!)
alembic upgrade head
```

**✅ Look for:** "Running upgrade..." messages - this means migrations are applying

**❌ If you get migration errors:**
- Check your DATABASE_URL in `backend/.env`
- Make sure PostgreSQL is running
- See "Troubleshooting" section below

### Step 6: Update Frontend Dependencies

**Open a new terminal:**

```bash
cd frontend

# Update Node packages
npm install

# Optional: Rebuild frontend (if not running dev mode)
npm run build
```

**💡 Tip:** If you're running in development mode (`npm run dev`), you don't need to rebuild - hot reload will handle it

### Step 7: Start FilaOps

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # Mac/Linux
.\venv\Scripts\activate   # Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Or restart services if running as a system service:**
```bash
# Linux (systemd)
sudo systemctl start filaops-backend

# Windows (NSSM)
nssm start FilaOpsBackend

# All platforms (PM2 for frontend)
pm2 restart filaops-frontend
```

### Step 8: Verify Upgrade

1. Open your browser to http://localhost:5174
2. Go to **Settings → Version & Updates**
3. Confirm the version matches what you installed
4. Test basic functionality:
   - View orders list
   - Check dashboard loads
   - Verify inventory displays

**✅ Success!** Your FilaOps is now upgraded!

---

## Upgrade for Production Deployments

### Additional Steps for Production

1. **Test in staging first** (if you have a staging environment)

2. **Announce downtime** to users

3. **Run backup:**
   ```bash
   pg_dump -U filaops_user filaops > filaops_backup_$(date +%Y%m%d_%H%M%S).sql
   ```

4. **Stop services:**
   ```bash
   # Linux
   sudo systemctl stop filaops-backend
   pm2 stop filaops-frontend

   # Windows
   nssm stop FilaOpsBackend
   pm2 stop filaops-frontend
   ```

5. **Get latest code and update dependencies** (Steps 4-6 above)

6. **Build production frontend:**
   ```bash
   cd frontend
   npm run build
   ```

7. **Restart services:**
   ```bash
   # Linux
   sudo systemctl start filaops-backend
   pm2 restart filaops-frontend

   # Windows
   nssm start FilaOpsBackend
   pm2 restart filaops-frontend
   ```

8. **Monitor logs for errors:**
   ```bash
   # Linux backend logs
   sudo journalctl -u filaops-backend -f

   # PM2 frontend logs
   pm2 logs filaops-frontend

   # Or check backend logs directly
   cd backend
   tail -f logs/filaops.log
   ```

9. **Verify all features** before announcing service is back

---

## Downgrading (If Needed)

If the new version has issues, you can rollback:

### Step 1: Stop FilaOps

```bash
# Stop backend and frontend (Ctrl+C in terminals, or stop services)
```

### Step 2: Checkout Previous Version

```bash
# See all versions
git tag --sort=-v:refname

# Checkout your previous version (replace vX.Y.Z)
git checkout vX.Y.Z
```

### Step 3: Rollback Database (IMPORTANT!)

```bash
cd backend
source venv/bin/activate

# Find the migration revision for your previous version
alembic history

# Downgrade to that revision (replace abc123)
alembic downgrade abc123
```

**⚠️ WARNING:** Downgrading may cause data loss if the new version added tables/columns!

### Step 4: Reinstall Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Step 5: Restart FilaOps

Follow Step 7 from the upgrade guide above.

---

## Troubleshooting

### Issue: "Migration failed" or "alembic.util.exc.CommandError"

**Cause:** Database migration issue

**Solution:**
```bash
cd backend
source venv/bin/activate

# Check current revision
alembic current

# Show migration history
alembic history

# Try upgrading one migration at a time
alembic upgrade +1

# If stuck, check backend logs for specific error
```

### Issue: "Module not found" errors

**Cause:** Python packages not installed or virtual environment not activated

**Solution:**
```bash
cd backend
source venv/bin/activate  # IMPORTANT!
pip install -r requirements.txt
```

### Issue: Frontend won't start after upgrade

**Cause:** Node modules need updating or cache issues

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Issue: Database connection failed after upgrade

**Cause:** DATABASE_URL might be incorrect or PostgreSQL not running

**Solution:**
```bash
# Check PostgreSQL is running
# Windows: Check Services app
# Mac: brew services list
# Linux: sudo systemctl status postgresql

# Verify DATABASE_URL in backend/.env
cat backend/.env | grep DATABASE_URL

# Test connection manually
psql -U filaops_user -d filaops
```

### Issue: "Could not find migration" errors

**Cause:** Database is ahead of code (happens when downgrading)

**Solution:**
```bash
cd backend
source venv/bin/activate

# Stamp database with current code's revision
alembic stamp head

# Then try upgrading again
alembic upgrade head
```

### Issue: Changes not appearing after upgrade

**Cause:** Browser cache or old build

**Solution:**
1. **Hard refresh:** Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
2. **Clear browser cache** for localhost
3. **Rebuild frontend:**
   ```bash
   cd frontend
   npm run build
   ```

### Issue: Backend won't start - "Port already in use"

**Cause:** Old backend process still running

**Solution:**
```bash
# Find process using port 8000
# Windows:
netstat -ano | findstr :8000

# Mac/Linux:
lsof -i :8000

# Kill the process (replace PID with actual process ID)
# Windows:
taskkill /PID <PID> /F

# Mac/Linux:
kill -9 <PID>
```

---

## Version-Specific Upgrade Notes

### Upgrading to v1.6.0

- **Breaking changes:** None
- **New features:** Material spool tracking, UOM conversion
- **Database changes:** New tables for spools and UOM
- **Action required:** None (migrations handle it)

### Upgrading to v1.5.0

- **Breaking changes:** None
- **New features:** Enhanced purchase order system
- **Database changes:** New fields in purchase_orders table
- **Action required:** None (migrations handle it)

### Upgrading from Docker to Native Installation

If you previously used Docker and want to migrate to native installation:

1. **Export your database:**
   ```bash
   # From Docker
   docker-compose exec db pg_dump -U filaops filaops > database_export.sql
   ```

2. **Install PostgreSQL natively** (see INSTALL.md)

3. **Import your database:**
   ```bash
   psql -U filaops_user -d filaops < database_export.sql
   ```

4. **Follow native installation guide** (INSTALL.md)

5. **Update configuration:**
   - Copy `.env` settings from Docker to `backend/.env`
   - Update DATABASE_URL to point to native PostgreSQL

---

## FAQ

### Q: Do I need to stop FilaOps to upgrade?

**A:** Yes, always stop FilaOps before upgrading to avoid file conflicts and database issues.

### Q: How long does an upgrade take?

**A:** Usually 5-10 minutes. Most time is spent downloading dependencies.

### Q: Can I skip versions?

**A:** Yes! You can upgrade directly from v1.0.0 to v1.6.0. Alembic migrations will run in order automatically.

### Q: Will I lose data when upgrading?

**A:** No, upgrades preserve your data. Database migrations add new tables/columns without deleting existing data. But always backup first!

### Q: Can I upgrade while users are using the system?

**A:** Not recommended. Stop FilaOps first to prevent database corruption. For production, schedule maintenance windows.

### Q: What if the upgrade fails?

**A:** Restore from your database backup and downgrade to the previous version (see "Downgrading" section).

### Q: How do I know which migrations ran?

**A:** Check migration history:
```bash
cd backend
source venv/bin/activate
alembic history
alembic current  # Shows current revision
```

---

## Getting Help

**Still having issues?**

1. Check the [Troubleshooting Guide](./TROUBLESHOOTING.md)
2. Search [GitHub Issues](https://github.com/Blb3D/filaops/issues)
3. Ask in [GitHub Discussions](https://github.com/Blb3D/filaops/discussions)
4. Open a new issue with:
   - Your current version
   - Version you're trying to upgrade to
   - Error messages (copy/paste full error)
   - Output of `alembic current` and `alembic history`

---

## Keeping FilaOps Updated

### Enable Update Notifications

FilaOps checks for updates automatically:

1. Go to **Settings → Version & Updates**
2. Enable **"Check for updates on startup"**
3. You'll see a notification when a new version is available

### Subscribe to Releases

Get notified of new releases:

1. Go to https://github.com/Blb3D/filaops
2. Click **Watch → Custom → Releases**
3. You'll get an email when new versions are released

---

*FilaOps - Keeping Your 3D Print Farm Running Smoothly*
