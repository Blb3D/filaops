# Upgrade Guide - FilaOps ERP

This guide covers how to upgrade your FilaOps installation to the latest release.

---

## Choose Your Installation Method

- **[Docker Installation](#docker-installation)** (Recommended) - Most users
- **[Manual Installation](#manual-installation-non-docker)** - Advanced users running backend/frontend separately

---

## Docker Installation

### Step 1: Pull Latest Code

```bash
# Navigate to your FilaOps directory
cd filaops  # or C:\BLB3D_Production for production

# Fetch all tags and releases
git fetch --tags

# Checkout the latest release
git checkout v1.5.0
```

### Step 2: Rebuild Docker Containers

**For Development**:
```bash
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

**For Production**:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Step 3: Run Database Migrations

v1.5.0 includes 3 new database migrations. Run them after upgrading:

```bash
# Development
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head

# Production
docker-compose exec backend alembic upgrade head
```

### Step 4: Clear Browser Cache

**Important**: Clear your browser cache to avoid JavaScript errors.

- **Chrome/Edge**: Ctrl + Shift + R (Windows) or Cmd + Shift + R (Mac)
- **Firefox**: Ctrl + Shift + Delete → Clear Cache
- **Or**: Use incognito/private browsing mode

### Step 5: Verify Installation

```bash
# Check backend logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Check that all services are running
docker-compose -f docker-compose.dev.yml ps
```

Visit the application and verify it loads:

- **Development**: <http://localhost:5174>
- **Production**: <http://localhost:10000>

---

## Production Deployment Upgrade

**Production Location**: `C:\BLB3D_Production`
**Ports**: Frontend: 10000, Backend: 7000

### ⚠️ Important: Test in Development First

Before upgrading production, **always test in development**:

```bash
cd c:\Users\brand\OneDrive\Documents\filaops
# Follow Docker Installation steps above
# Test thoroughly before proceeding to production
```

### Production Upgrade Steps

```bash
# 1. Navigate to PRODUCTION directory (CRITICAL!)
cd C:\BLB3D_Production

# 2. (Optional but recommended) Backup database
# Using SQL Server Management Studio: Right-click DB → Tasks → Backup

# 3. Pull latest release
git fetch --tags
git checkout v1.5.0

# 4. Rebuild containers (production config - NO .dev.yml!)
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 5. Run migrations (IMPORTANT!)
docker-compose exec backend alembic upgrade head

# 6. Verify services are running
docker-compose ps
docker-compose logs -f backend
```

### Production Verification

Visit <http://localhost:10000> and verify:

- Application loads successfully
- Can log in
- Orders page displays correctly
- No console errors (F12 Developer Tools)

### Production Ports Reference

| Service | Port | Container |
|---------|------|-----------|
| Frontend | 10000 | filaops-frontend |
| Backend | 7000 | filaops-backend |
| Database | 1433 | filaops-db |
| Redis | 6379 | filaops-redis |

### Production Troubleshooting

**Services won't start**:

```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Verify .env file has ENVIRONMENT=production
cat .env | grep ENVIRONMENT
```

**Port conflicts**:

```bash
# Check what's using ports
netstat -ano | findstr :10000
netstat -ano | findstr :7000
```

---

## What's New in v1.5.0

### 🆕 New Features
- **Activity Timeline** - Order event tracking with visual timeline
- **Work Centers & Machines** - Production resource management
- **Order Status Service** - Automated status transitions
- **Enhanced E2E Tests** - Comprehensive test coverage

### 🐛 Bug Fixes
- Fixed TypeError in low-stock calculation (purchasing page)
- Fixed SECRET_KEY validation for production deployments
- Fixed payment date validation (prevents future dates)
- Improved error logging in production order creation

### 🔧 Code Quality Improvements
- SQL Server boolean compatibility across 66 files
- Type hints added to helper functions
- Security: Removed JWT tokens from git tracking
- Standardized database migration naming (001-016)

### 📚 Documentation
- Reorganized release notes into `docs/releases/`
- Archived historical documentation
- Added AI assistant instructions
- Added production build safeguards

See [docs/releases/RELEASE_NOTES_v1.5.0.md](docs/releases/RELEASE_NOTES_v1.5.0.md) for full details.

---

## Manual Installation (Non-Docker)

If you're running the backend and frontend separately without Docker:

### Step 1: Pull Latest Code (Manual)

```bash
cd filaops
git fetch --tags
git checkout v1.5.0
```

### Step 2: Update Backend (Manual)

```bash
cd backend

# Activate your virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Update Python dependencies
pip install -r requirements.txt

# Run database migrations (IMPORTANT!)
alembic upgrade head

# Restart backend server
# If using uvicorn directly:
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Step 3: Update Frontend (Manual)

```bash
cd frontend

# Install/update Node dependencies
npm install

# Rebuild frontend
npm run build

# For development:
npm run dev

# For production (if serving with nginx/apache):
# The build output will be in frontend/dist/
```

### Step 4: Restart Services (Manual)

If you're using systemd, PM2, or another process manager:

```bash
# systemd example:
sudo systemctl restart filaops-backend
sudo systemctl restart filaops-frontend

# PM2 example:
pm2 restart filaops-backend
pm2 restart filaops-frontend

# Or, manually stop and restart your processes
```

### Step 5: Clear Browser Cache (Manual)

Press Ctrl + Shift + R (Windows/Linux) or Cmd + Shift + R (Mac) to hard refresh.

### Manual Installation Troubleshooting

**Python dependency errors**:
```bash
# Recreate virtual environment if needed
rm -rf venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**Node dependency errors**:
```bash
# Clear npm cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Database connection issues**:

- Verify SQL Server is running
- Check connection string in `.env` file
- Ensure `DB_HOST`, `DB_NAME`, and credentials are correct

---

## Upgrade Paths

### From v1.4.x to v1.5.0
- **Database Migrations**: Yes (3 new migrations)
- **Breaking Changes**: None
- **Config Changes**: None
- **Estimated Downtime**: < 5 minutes

Follow the Quick Upgrade steps above.

### From v1.3.x to v1.5.0
1. Upgrade to v1.4.x first
2. Then upgrade to v1.5.0

### From Earlier Versions
Contact support or see the [migration guide](docs/MIGRATION_GUIDE.md).

---

## Database Migrations in v1.5.0

This release includes the following new migrations:

- **014_add_fulfillment_status.py** - Order fulfillment tracking
- **015_add_work_centers_and_machines.py** - Production scheduling tables
- **016_add_scrap_tracking.py** - Quality control and scrap management

These are **additive only** - no data loss will occur.

---

## Rollback Instructions

If you need to rollback to v1.4.x:

```bash
# Stop containers
docker-compose -f docker-compose.dev.yml down

# Checkout previous release
git checkout v1.4.0  # or your previous version

# Rollback database migrations
docker-compose -f docker-compose.dev.yml exec backend alembic downgrade -1  # Repeat 3 times for v1.5.0

# Rebuild and restart
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d
```

---

## Troubleshooting

### Issue: "Cannot access before initialization" errors

**Cause**: Browser cached old JavaScript files
**Solution**: Hard refresh (Ctrl + Shift + R) or clear browser cache

### Issue: Database migration fails

**Cause**: Database connection issue or migration conflict
**Solution**:
```bash
# Check migration status
docker-compose -f docker-compose.dev.yml exec backend alembic current

# View migration history
docker-compose -f docker-compose.dev.yml exec backend alembic history
```

### Issue: Containers won't start

**Cause**: Port conflicts or corrupt volumes
**Solution**:
```bash
# Check what's using the ports
netstat -ano | findstr :5174  # Windows
lsof -i :5174  # Linux/Mac

# Or, remove and recreate volumes
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

### Issue: "ModuleNotFoundError" in backend

**Cause**: Python dependencies changed
**Solution**:
```bash
# Rebuild with --no-cache flag
docker-compose -f docker-compose.dev.yml build --no-cache backend
docker-compose -f docker-compose.dev.yml up -d
```

---

## Getting Help

- **GitHub Issues**: https://github.com/Blb3D/filaops/issues
- **GitHub Discussions**: https://github.com/Blb3D/filaops/discussions
- **Discord Community**: https://discord.gg/FAhxySnRwa

When reporting upgrade issues, please include:
- Current version (check `git describe --tags`)
- Operating system
- Docker version (`docker --version`)
- Error messages from logs

---

## Version Compatibility

| Component | v1.5.0 |
|-----------|--------|
| Docker Compose | 2.0+ |
| Docker Engine | 20.10+ |
| SQL Server | 2017+ |
| Node.js (dev) | 18+ |
| Python (dev) | 3.10+ |

---

## Next Release

**v1.6.0** (Planned Q1 2026)
- Production build optimizations
- Enhanced error handling
- Performance improvements
- Additional manufacturing features

Subscribe to releases on GitHub to get notified: https://github.com/Blb3D/filaops/releases
