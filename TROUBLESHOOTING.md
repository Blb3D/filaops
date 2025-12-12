# Troubleshooting Guide

Common issues and solutions for FilaOps installation and operation.

---

## Docker Issues

### "Cannot connect to Docker daemon"

**Problem:** Docker Desktop isn't running or Docker service isn't started.

**Solutions:**
1. **Windows/macOS:** 
   - Make sure Docker Desktop is running (look for whale icon in system tray/menu bar)
   - If not running, open Docker Desktop and wait for it to start
   
2. **Windows (PowerShell):**
   - Try running PowerShell as Administrator
   - Restart Docker Desktop service

3. **Linux:**
   ```bash
   # Start Docker service
   sudo systemctl start docker
   
   # Enable Docker to start on boot
   sudo systemctl enable docker
   ```

4. **Verify Docker is working:**
   ```bash
   docker --version
   docker ps
   ```

---

### "Port 5173 already in use" or "Port 8000 already in use"

**Problem:** Another application is using the port FilaOps needs.

**Solutions:**

**Option 1: Stop the conflicting application**
1. Find what's using the port:
   - **Windows:** `netstat -ano | findstr :5173`
   - **Mac/Linux:** `lsof -i :5173`
2. Stop that application or change its port

**Option 2: Change FilaOps port**
1. Edit `docker-compose.yml`
2. Change the port mapping:
   ```yaml
   # Change from:
   ports:
     - "5173:80"
   # To:
   ports:
     - "8080:80"
   ```
3. Restart: `docker-compose down && docker-compose up -d`
4. Access at: `http://localhost:8080`

---

### "Database connection failed"

**Problem:** Database container isn't ready or connection string is wrong.

**Solutions:**

1. **Wait 30 seconds** - Database takes time to initialize on first startup
   ```bash
   # Check if database is ready
   docker-compose logs db
   # Look for: "SQL Server is now ready for client connections"
   ```

2. **Check database container status:**
   ```bash
   docker-compose ps
   # Should show "Up" for filaops-db
   ```

3. **Check database logs:**
   ```bash
   docker-compose logs db
   # Look for errors or connection issues
   ```

4. **Verify connection string in `.env`:**
   ```
   DB_HOST=filaops-db
   DB_NAME=FilaOps
   DB_USER=sa
   DB_PASSWORD=YourStrong@Password123
   ```

5. **Restart database:**
   ```bash
   docker-compose restart db
   # Wait 30 seconds, then try again
   ```

---

### "Container keeps restarting"

**Problem:** Container crashes immediately after starting.

**Solutions:**

1. **Check container logs:**
   ```bash
   # Backend issues
   docker-compose logs backend
   
   # Frontend issues
   docker-compose logs frontend
   
   # Database issues
   docker-compose logs db
   ```

2. **Common causes:**
   - **Backend:** Database not ready, missing environment variables
   - **Frontend:** Build failed, port conflict
   - **Database:** Insufficient memory, disk space

3. **Check system resources:**
   ```bash
   # Check Docker resources
   docker stats
   # Make sure you have enough RAM/CPU
   ```

4. **Rebuild containers:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

---

### "filaops-db-init exited" (Normal!)

**This is normal!** The `filaops-db-init` container is a one-time initialization script. It:
1. Creates the database
2. Runs initialization scripts
3. Exits (this is expected)

**You can ignore this.** The database container (`filaops-db`) should still be running.

---

### Docker containers won't start after update

**Problem:** After pulling latest code, containers fail to start.

**Solutions:**

1. **Rebuild containers:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

2. **Check for breaking changes:**
   - Review [CHANGELOG.md](CHANGELOG.md) or commit history
   - Check if `.env` variables changed

3. **Reset everything (⚠️ deletes all data):**
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

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
   python -m uvicorn app.main:app --reload --port 8001
   ```

3. **Update frontend `.env`:**
   ```
   VITE_API_URL=http://localhost:8001
   ```

---

### "Can't connect to database" (Manual Installation)

**Problem:** SQL Server isn't running or connection string is wrong.

**Solutions:**

1. **Check SQL Server is running:**
   - **Windows:** Open Services (search "Services" in Start menu)
   - Find "SQL Server (SQLEXPRESS)" or "SQL Server (MSSQLSERVER)"
   - Make sure it's "Running"
   - If not, right-click → Start

2. **Verify connection string in `.env`:**
   ```
   DB_HOST=localhost\SQLEXPRESS
   DB_NAME=FilaOps
   DB_TRUSTED_CONNECTION=true
   # OR
   DB_USER=sa
   DB_PASSWORD=YourPassword
   ```

3. **Test connection:**
   ```bash
   # Windows
   sqlcmd -S localhost\SQLEXPRESS -E -Q "SELECT @@VERSION"
   ```

4. **Check firewall:** SQL Server might be blocked by Windows Firewall

---

## Application Issues

### Dashboard shows "Failed to fetch"

**Problem:** Frontend can't connect to backend API.

**Solutions:**

1. **Check backend is running:**
   - **Docker:** `docker-compose ps` (backend should be "Up")
   - **Manual:** Check terminal running `uvicorn`

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

**Problem:** On a fresh Docker install, you see the login screen instead of the setup wizard.

**Cause:** The database has existing user data, likely from:

- A previous installation with persisted volumes
- Incomplete database cleanup

**Solution - Fresh Start:**

```bash
# Stop containers and remove all data volumes
docker-compose down -v

# Start fresh
docker-compose up -d
```

This removes the database volume and starts fresh. The setup wizard will appear.

---

### Login doesn't work / "Invalid credentials"

**Problem:** Can't log in - admin user doesn't exist or password is wrong.

**Solutions:**

1. **Docker (fresh install):**
   - FilaOps doesn't have default credentials
   - You create your admin account via the Setup Wizard on first run
   - If you missed setup, run `docker-compose down -v && docker-compose up -d` for fresh start

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
   docker-compose build --no-cache
   docker-compose up -d
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
   # Docker
   docker-compose logs db
   
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

## Still Need Help?

1. **Check logs:**
   - **Docker:** `docker-compose logs -f`
   - **Manual:** Check terminal output

2. **Search existing issues:**
   - [GitHub Issues](https://github.com/Blb3D/filaops/issues)
   - [GitHub Discussions](https://github.com/Blb3D/filaops/discussions)

3. **Create a new issue:**
   - Include error messages
   - Include logs
   - Describe what you were doing
   - Include your setup (Docker/manual, OS, etc.)

---

*Last updated: December 2025*

