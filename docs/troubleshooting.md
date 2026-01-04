# Troubleshooting Guide

Common issues and solutions for FilaOps installation and operation.

---

## Docker Issues

### "Port already in use" when starting containers

**Problem:** Docker can't bind to port 5173, 8000, or 5432.

**Solutions:**

1. **Find what's using the port:**
   - **Windows:** `netstat -ano | findstr :8000`
   - **Mac/Linux:** `lsof -i :8000`

2. **Stop the conflicting application** or change ports in `docker-compose.yml`:
   ```yaml
   ports:
     - "8001:8000"  # Change left number (host port)
   ```

---

### "Cannot connect to Docker daemon"

**Problem:** Docker Desktop isn't running.

**Solution:** Start Docker Desktop, wait for it to fully initialize (whale icon stops animating), then retry.

---

### Backend container keeps restarting

**Problem:** Backend exits immediately after starting.

**Check logs:**
```bash
docker-compose logs backend
```

**Common causes:**
1. Database not ready (wait 30 seconds, containers have health checks)
2. Wrong `DB_PASSWORD` in `.env` file
3. Database container failed - check `docker-compose logs db`

**Solution:**
```bash
# Restart everything
docker-compose down
docker-compose up --build
```

---

### "FATAL: password authentication failed" in Docker

**Problem:** PostgreSQL was initialized with a different password than what's in `.env`.

**Solution (fresh start - deletes all data):**
```bash
docker-compose down -v
docker-compose up --build
```

> ⚠️ The `-v` flag removes volumes including your database. Only use for fresh installs.

---

### Docker build fails with "no space left on device"

**Problem:** Docker has run out of disk space.

**Solution:**
```bash
# Clean up unused Docker resources
docker system prune -a

# Also remove unused volumes (careful!)
docker volume prune
```

---

### Changes to code aren't reflected in Docker

**Problem:** Docker cached the old image.

**Solution:**
```bash
docker-compose build --no-cache
docker-compose up
```

---

### How to backup Docker database

```bash
# Create backup
docker-compose exec db pg_dump -U postgres filaops > backup_$(date +%Y%m%d).sql

# Restore from backup
docker-compose exec -T db psql -U postgres filaops < backup_20251226.sql
```

---

## PostgreSQL Database Issues

### "Database connection failed"

**Problem:** PostgreSQL isn't running or connection string is wrong.

**Solutions:**

1. **Check PostgreSQL is running:**
   - **Windows:** Check Services (search "Services" in Start menu, look for "postgresql")
   - **macOS:** `brew services list | grep postgresql`
   - **Linux:** `sudo systemctl status postgresql`

2. **Start PostgreSQL if not running:**
   - **Windows:** Start the PostgreSQL service from Services
   - **macOS:** `brew services start postgresql@16`
   - **Linux:** `sudo systemctl start postgresql`

3. **Verify connection string in `.env`:**
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=filaops
   DB_USER=postgres
   DB_PASSWORD=your_password_here
   ```

4. **Test database connection:**
   ```bash
   # Test connection
   psql -h localhost -U postgres -d filaops -c "SELECT 1;"
   ```

5. **Check if database exists:**
   ```bash
   psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname='filaops';"
   # If empty, create it:
   createdb -U postgres filaops
   ```

---

### "Port 5173 already in use" or "Port 8000 already in use"

**Problem:** Another application is using the port FilaOps needs.

**Solutions:**

**Option 1: Stop the conflicting application**
1. Find what's using the port:
   - **Windows:** `netstat -ano | findstr :5173` or `netstat -ano | findstr :8000`
   - **Mac/Linux:** `lsof -i :5173` or `lsof -i :8000`
2. Stop that application or change its port

**Option 2: Change FilaOps ports**
1. Edit `.env` file (backend) or frontend config
2. Change backend port: Update `start-backend.ps1` or uvicorn command to use different port
3. Change frontend port: Update `package.json` scripts or vite config
4. Restart both backend and frontend

---

### "psql: command not found"

**Problem:** PostgreSQL command-line tools aren't in your PATH.

**Solutions:**

1. **Windows:** Add PostgreSQL bin directory to PATH:
   - Usually: `C:\Program Files\PostgreSQL\16\bin`
   - Add to System PATH in Environment Variables

2. **macOS/Linux:** PostgreSQL should be in PATH if installed via package manager
   - Verify: `which psql`
   - If missing, reinstall PostgreSQL or add to PATH manually

---

## Manual Installation Issues

### "python is not recognized"

**Problem:** Python isn't in your system PATH.

**Solutions:**

1. **Reinstall Python:**
   - Download from https://www.python.org/downloads/
   - **Important:** Check "Add Python to PATH" during installation
   - Restart your terminal/command prompt

2. **Add Python to PATH manually (Windows):**
   - Find Python installation (usually `C:\Python3xx` or `C:\Users\YourName\AppData\Local\Programs\Python\Python3xx`)
   - Add to System PATH:
     - Right-click "This PC" → Properties → Advanced System Settings
     - Environment Variables → System Variables → Path → Edit
     - Add Python folder and `Scripts` folder
   - Restart terminal

3. **Verify:**
   ```bash
   python --version
   pip --version
   ```

---

### "npm is not recognized"

**Problem:** Node.js isn't installed or not in PATH.

**Solutions:**

1. **Install Node.js:**
   - Download from https://nodejs.org/ (LTS version)
   - Run installer with default settings
   - Restart terminal

2. **Verify:**
   ```bash
   node --version
   npm --version
   ```

---

### "pip install" fails with errors

**Problem:** Python packages can't be installed.

**Solutions:**

1. **Upgrade pip:**
   ```bash
   python -m pip install --upgrade pip
   ```

2. **Use virtual environment (recommended):**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate (Windows)
   venv\Scripts\activate
   
   # Activate (Mac/Linux)
   source venv/bin/activate
   
   # Install packages
   pip install -r requirements.txt
   ```

3. **Check Python version:**
   - FilaOps requires Python 3.11+
   - `python --version` should show 3.11.x or higher

---

### Backend won't start / "Address already in use"

**Problem:** Port 8000 is already in use.

**Solutions:**

1. **Find what's using port 8000:**
   - **Windows:** `netstat -ano | findstr :8000`
   - **Mac/Linux:** `lsof -i :8000`

2. **Stop the conflicting application** or use a different port:
   ```bash
   python -m uvicorn app.main:app --reload --port 8010
   ```

3. **Update frontend `.env`:**
   ```
   VITE_API_URL=http://localhost:8010
   ```

---

### "Can't connect to database" (Manual Installation)

**Problem:** PostgreSQL isn't running or connection string is wrong.

**Solutions:**

1. **Check PostgreSQL is running:**
   - **Windows:** Open Services (search "Services" in Start menu)
   - Find "postgresql" service
   - Make sure it's "Running"
   - If not, right-click → Start
   - **macOS:** `brew services list | grep postgresql`
   - **Linux:** `sudo systemctl status postgresql`

2. **Verify connection string in `.env`:**
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=filaops
   DB_USER=postgres
   DB_PASSWORD=your_password_here
   ```

3. **Test connection:**
   ```bash
   psql -h localhost -U postgres -d filaops -c "SELECT version();"
   ```

4. **Check firewall:** PostgreSQL might be blocked by firewall (default port 5432)

---

## Application Issues

### Dashboard shows "Failed to fetch"

**Problem:** Frontend can't connect to backend API.

**Solutions:**

1. **Check backend is running:**
   - Check terminal running `uvicorn` (should show "Uvicorn running on http://...")
   - Verify backend is accessible: `curl http://localhost:8000/health`

2. **Check API URL:**
   - Open browser console (F12)
   - Look for network errors
   - Verify `VITE_API_URL` in frontend `.env` matches backend URL

3. **Test backend directly:**
   - Open http://localhost:8000/docs
   - Should see FastAPI documentation
   - If not, backend isn't running

4. **Check CORS errors:**
   - Backend must allow frontend origin
   - Check `CORS_ORIGINS` in backend `.env`

---

### Stuck at Login Screen (Expected Setup Wizard)

**Problem:** On a fresh install, you see the login screen instead of the setup wizard.

**Cause:** The database has existing user data, likely from:

- A previous installation
- Incomplete database cleanup

**Solution - Fresh Start:**

```bash
# Drop and recreate database
psql -U postgres -c "DROP DATABASE IF EXISTS filaops;"
createdb -U postgres filaops

# Run migrations
cd backend
alembic upgrade head
```

This removes the database and starts fresh. The setup wizard will appear.

---

### Login doesn't work / "Invalid credentials"

**Problem:** Can't log in - admin user doesn't exist or password is wrong.

**Solutions:**

1. **Fresh install:**
   - FilaOps doesn't have default credentials
   - You create your admin account via the Setup Wizard on first run
   - If you missed setup, drop and recreate the database (see above)

2. **Manual (local development):**
   - Default: `admin@localhost` / `admin123`
   - These are created by `scripts/tools/fresh_database_setup.py`
   - Create admin user:
     ```bash
     python scripts/tools/create_admin.py
     ```

3. **Reset password (if you forgot it):**
   - Currently requires database access
   - See below for manual reset

---

### CSV import fails with errors

**Problem:** CSV format doesn't match or has invalid data.

**Solutions:**

1. **Check CSV format:**
   - See [docs/MARKETPLACE_IMPORT_GUIDE.md](docs/MARKETPLACE_IMPORT_GUIDE.md)
   - Verify column names match expected format
   - Download template if available

2. **Common issues:**
   - **Missing required fields:** SKU, Name, or Price
   - **Invalid data:** Special characters, empty rows
   - **Wrong encoding:** Save as UTF-8
   - **Currency symbols:** FilaOps auto-removes, but check format

3. **Check import errors:**
   - Import results show which rows failed
   - Fix those rows and re-import
   - Or import in smaller batches

4. **Test with template:**
   - Download CSV template
   - Fill with sample data
   - Import to verify format works

---

### "Low stock" count doesn't match

**Problem:** Dashboard shows different low stock count than items page.

**Solutions:**

1. **This was fixed in recent updates** - Make sure you're on latest version:
   ```bash
   git pull
   # Restart backend and frontend
   ```

2. **Check inventory locations:**
   - Low stock aggregates across all locations
   - Verify inventory is in correct location

3. **Check MRP shortages:**
   - Dashboard includes MRP-calculated shortages
   - Items page shows only current inventory

---

### Bulk update reverts changes

**Problem:** Category/item type changes revert after another bulk update.

**Solutions:**

1. **This was fixed in recent updates** - Update to latest version

2. **Workaround:**
   - Update one category at a time
   - Wait for update to complete before next update
   - Refresh page after each update

---

## Performance Issues

### Dashboard loads slowly

**Problem:** Too much data or slow database queries.

**Solutions:**

1. **Check database performance:**
   ```bash
   # Check PostgreSQL logs
   # Windows: Check PostgreSQL log files
   # macOS/Linux: tail -f /var/log/postgresql/postgresql-*.log
   
   # Look for slow queries
   ```

2. **Reduce data:**
   - Archive old orders
   - Limit dashboard date range (if available)

3. **Check system resources:**
   - Make sure you have enough RAM
   - Close other applications

---

### Import takes too long

**Problem:** Large CSV files take forever to import.

**Solutions:**

1. **Import in smaller batches:**
   - Split CSV into 100-200 row chunks
   - Import one at a time

2. **Check for errors:**
   - Errors slow down import
   - Fix CSV issues first

3. **Use bulk import API** (if available):
   - More efficient than web UI
   - See API documentation

---

## Data Issues

### Seeded example data is confusing

**Problem:** Example products show as "Finished Goods" with selling prices.

**Solutions:**

1. **This is intentional** - Examples show finished products, not raw filament
2. **You can delete examples:**
   - Go to Products page
   - Delete items with `SEED-EXAMPLE-` prefix
3. **Or skip seeding:**
   - Don't select "Load Example Data" during onboarding

---

### Inventory shows wrong quantities

**Problem:** On-hand quantities don't match reality.

**Solutions:**

1. **Check inventory transactions:**
   - Go to Inventory Transactions page
   - Look for recent receipts, issues, adjustments

2. **Verify production consumption:**
   - Production orders consume materials
   - Check if production was completed correctly

3. **Manual adjustment:**
   - Create inventory adjustment transaction
   - Correct the quantity

---

## Remote Access Issues

### "Cannot connect to API" when accessing from another machine

**Problem:** Frontend loads but shows "Cannot connect to API" error when accessing FilaOps from a different computer on your network.

**Cause:** By default, FilaOps is configured for localhost access. The frontend has the API URL baked in at build time.

**Solution:**

1. **Find your server's IP address:**
   ```bash
   # Windows
   ipconfig
   # Look for "IPv4 Address" (e.g., 192.168.1.100)
   
   # Linux/Mac
   ip addr
   # or
   hostname -I
   ```

2. **Update your `.env` file:**
   ```
   VITE_API_URL=http://192.168.1.100:8000
   FRONTEND_URL=http://192.168.1.100:5173
   ```
   Replace `192.168.1.100` with your actual server IP.

3. **Rebuild the frontend (required!):**
   ```bash
   cd frontend
   npm run build
   ```

   ⚠️ **Important:** The `VITE_API_URL` is compiled into the JavaScript at build time - you need to rebuild the frontend after changing environment variables.

4. **Access from other machines:**
   - Open `http://192.168.1.100:5173` in your browser
   - Use your server's IP, not `localhost`

**Why is rebuild required?**

Vite (the frontend build tool) bakes environment variables starting with `VITE_` into the JavaScript bundle at compile time. This is different from backend environment variables which are read at runtime. Changing `.env` and restarting only affects the backend - the frontend needs a full rebuild.

---

### API works in browser but frontend can't connect

**Problem:** You can open `http://192.168.1.100:8000` directly and see the API response, but the frontend shows connection errors.

**Cause:** CORS (Cross-Origin Resource Sharing) is blocking the frontend.

**Solution:**

Make sure `FRONTEND_URL` in your `.env` matches exactly how you access the frontend:

```
# If you access via http://192.168.1.100:5173
FRONTEND_URL=http://192.168.1.100:5173
```

Then restart the backend:
```bash
# Stop the backend (Ctrl+C) and restart
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

### Firewall blocking access

**Problem:** Can't reach FilaOps from other machines at all.

**Solution:**

**Windows:**
```powershell
# Allow ports through Windows Firewall
netsh advfirewall firewall add rule name="FilaOps Frontend" dir=in action=allow protocol=tcp localport=5173
netsh advfirewall firewall add rule name="FilaOps Backend" dir=in action=allow protocol=tcp localport=8000
```

**Linux (UFW):**
```bash
sudo ufw allow 5173/tcp
sudo ufw allow 8000/tcp
```

**Linux (firewalld):**
```bash
sudo firewall-cmd --permanent --add-port=5173/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

---

## Still Need Help?

1. **Check logs:**
   - Check backend terminal output
   - Check frontend terminal output
   - Check PostgreSQL logs if database issues

2. **Join Discord for quick help:**
   - [Discord Server](https://discord.gg/FAhxySnRwa)
   - Best for installation issues and quick questions

3. **Search existing issues:**
   - [GitHub Issues](https://github.com/Blb3D/filaops/issues)
   - [GitHub Discussions](https://github.com/Blb3D/filaops/discussions)

4. **Create a new issue:**
   - Include error messages
   - Include logs
   - Describe what you were doing
   - Include your setup (OS, PostgreSQL version, Python version, etc.)

---

*Last updated: December 2025*

