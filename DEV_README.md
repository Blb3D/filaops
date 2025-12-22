# BLB3D Production DEV Environment

This is the **isolated development environment** for the MRP workflow unification and Postgres migration work.

## ⚠️ Safety Features

- **Separate directory**: All changes are in `BLB3D_Production_DEV`, not your production system
- **Separate database**: DEV defaults to PostgreSQL (`BLB3D_ERP_DEV`) - completely isolated from production
- **Safety latch**: DEV mode will **refuse to connect** to production database names unless explicitly allowed
- **Separate ports**: DEV backend runs on port **8002** (production uses 8001)

## Quick Start

### 1. Set up PostgreSQL (if not already installed)

Install PostgreSQL and create a DEV database:

```sql
CREATE DATABASE BLB3D_ERP_DEV;
```

### 2. Configure Environment

Copy the example env file:

```powershell
cd C:\BLB3D_Production_DEV
Copy-Item .env.dev.example .env.dev
```

Edit `.env.dev` and set your PostgreSQL password:

```
DB_PASSWORD=your_postgres_password_here
```

### 3. Install Dependencies

```powershell
# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Install PostgreSQL driver (if not already installed)
pip install psycopg2-binary

# Frontend
cd ..\frontend
npm install
```

### 4. Initialize Database

Run migrations or create tables:

```powershell
cd backend
python -m alembic upgrade head
# OR if starting fresh:
python -c "from app.db.session import engine; from app.db.base import Base; import app.models; Base.metadata.create_all(bind=engine)"
```

### 5. Start DEV Servers

**Backend (port 8002):**
```powershell
cd C:\BLB3D_Production_DEV\backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

**Frontend (port 5174):**
```powershell
cd C:\BLB3D_Production_DEV\frontend
npm run dev -- --port 5174
```

## Safety Checks

The system automatically detects DEV mode by:
1. Checking if the path contains `_DEV`
2. Checking the `BLB3D_DEV_MODE` environment variable

If DEV mode is detected, it will:
- ✅ Default to PostgreSQL
- ✅ Use `.env.dev` file
- ✅ Block connections to production database names (`BLB3D_ERP`, `BLB3D_Production`, `FilaOps`)
- ✅ Use separate ports (8002 backend, 5174 frontend)

## Overriding Safety (NOT RECOMMENDED)

If you absolutely need to test with production data (e.g., for migration testing), you can bypass the safety latch:

```powershell
$env:BLB3D_DEV_ALLOW_PROD_DB="true"
```

**⚠️ WARNING**: This defeats the purpose of isolation. Only use for migration testing with a **read-only** production database connection.

## Development Workflow

1. **Make changes** in `C:\BLB3D_Production_DEV`
2. **Test** in DEV environment (PostgreSQL)
3. **When ready**, migrate production data from SQL Server → Postgres
4. **Cutover** production to new system

## Current Development Focus

- Phase A: ✅ DEV fork + config safety (COMPLETE)
- Phase B: Unify Production Execution (remove fulfillment seam)
- Phase C: Hybrid scheduling rules + operator FIFO
- Phase D: Policy-driven lot traceability
- Phase E: Infor-style workbench UI updates
- Phase F: SQL Server → Postgres migration tooling

## Ports

- **Production Backend**: `http://localhost:8001`
- **Production Frontend**: `http://localhost:5173`
- **DEV Backend**: `http://localhost:8002` ⬅️ Use this
- **DEV Frontend**: `http://localhost:5174` ⬅️ Use this

## Database Connections

- **Production**: SQL Server (`BLB3D_ERP` on `localhost\SQLEXPRESS`)
- **DEV**: PostgreSQL (`BLB3D_ERP_DEV` on `localhost:5432`)

