# Quick Start Guide - Running the DEV System

## Prerequisites

1. **PostgreSQL installed** (if not, download from https://www.postgresql.org/download/windows/)
2. **Python 3.9+** installed
3. **Node.js** installed (for frontend)

## Step-by-Step Setup

### 1. Create PostgreSQL Database

Open PostgreSQL (pgAdmin or psql) and run:

```sql
CREATE DATABASE BLB3D_ERP_DEV;
```

### 2. Configure Environment File

```powershell
cd C:\BLB3D_Production_DEV

# Create .env.dev file (copy from example if it exists, or create new)
if (Test-Path ".env.dev.example") {
    Copy-Item .env.dev.example .env.dev
} else {
    # Create basic .env.dev
    @"
ENVIRONMENT=development
DEBUG=True
BLB3D_DEV_MODE=true

DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=BLB3D_ERP_DEV
DB_USER=postgres
DB_PASSWORD=YOUR_POSTGRES_PASSWORD_HERE

SECRET_KEY=dev-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174

FRONTEND_URL=http://localhost:5174
"@ | Out-File -FilePath .env.dev -Encoding utf8
}

# Edit .env.dev and replace YOUR_POSTGRES_PASSWORD_HERE with your actual PostgreSQL password
notepad .env.dev
```

### 3. Install Backend Dependencies

```powershell
cd C:\BLB3D_Production_DEV\backend

# Create virtual environment (if not exists)
if (-not (Test-Path "venv")) {
    python -m venv venv
}

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install PostgreSQL driver
pip install psycopg2-binary
```

### 4. Initialize Database

```powershell
# Still in backend directory with venv activated

# Option 1: Use Alembic migrations (if migrations exist)
python -m alembic upgrade head

# Option 2: Create tables directly (if no migrations yet)
python -c "from app.db.session import engine; from app.db.base import Base; import app.models; Base.metadata.create_all(bind=engine)"
```

### 5. Install Frontend Dependencies

```powershell
cd C:\BLB3D_Production_DEV\frontend
npm install
```

### 6. Start Backend Server

**Open a new PowerShell window:**

```powershell
cd C:\BLB3D_Production_DEV\backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8002
INFO:     Application startup complete.
```

**Keep this window open!**

### 7. Start Frontend Server

**Open another new PowerShell window:**

```powershell
cd C:\BLB3D_Production_DEV\frontend
npm run dev -- --port 5174
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5174/
```

### 8. Access the Application

Open your browser and go to:
- **Frontend**: http://localhost:5174
- **Backend API Docs**: http://localhost:8002/docs

## Using the Startup Scripts (Alternative)

You can also use the provided startup script:

```powershell
cd C:\BLB3D_Production_DEV
.\start-backend-dev.ps1
```

## Troubleshooting

### "Database connection failed"
- Check PostgreSQL is running: `Get-Service postgresql*`
- Verify password in `.env.dev` is correct
- Check database `BLB3D_ERP_DEV` exists

### "Port 8002 already in use"
- Stop any other service using port 8002
- Or change port in `.env.dev` and startup command

### "Module not found" errors
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again

### "Cannot connect to database"
- Verify PostgreSQL service is running
- Check firewall allows port 5432
- Verify credentials in `.env.dev`

## Testing the New Endpoints

Once running, test the new unified production endpoints:

1. **API Docs**: http://localhost:8002/docs
2. **Test Schedule**: `PUT /api/v1/production-orders/{id}/schedule`
3. **Test Start**: `POST /api/v1/production-orders/{id}/start`
4. **Test Lot Requirements**: `GET /api/v1/production-orders/{id}/lot-requirements`

## Next Steps

- Create some test data (products, BOMs, production orders)
- Test the unified production execution flow
- Test lot traceability policies
- Verify FIFO sequencing works

