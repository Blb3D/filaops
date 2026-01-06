# Upgrading from FilaOps v1.x to v2.x

> **Important**: FilaOps v2.0 switched from SQL Server to PostgreSQL. This guide walks you through migrating your data safely.

## What Changed?

FilaOps v2.0 introduced a major architecture change: **the database engine switched from SQL Server to PostgreSQL**. This is not a simple version upgrade - it requires migrating your data to a new database system.

**Your data is NOT lost!** We provide tools to migrate everything.

### Summary of Changes

| Component | v1.x | v2.x |
|-----------|------|------|
| Database | SQL Server Express | PostgreSQL 15+ |
| Backend Port | 8001 | 8000 |
| Deployment | Docker optional | Native install (no Docker) |
| Driver | pyodbc | psycopg |

### New Features in v2.x

- **Command Center Dashboard** - Prioritized action items and blocking issues
- **Production Scheduling** - Drag-and-drop Gantt chart scheduler
- **AI Invoice Parsing** - Upload vendor invoices, auto-populate PO data
- **Operation Tracking** - Start/complete/skip individual operations
- **Fulfillment Status** - Track sales order completion status

---

## Prerequisites

Before starting, ensure you have:

1. **PostgreSQL 15+ installed** (12+ minimum, 15+ recommended)
   - Download: https://www.postgresql.org/download/
   - Windows users: Use the installer, include pgAdmin

2. **Access to your v1.x SQL Server database**
   - Either SQL Server is still running, OR
   - You have a database backup (.bak file)

3. **ODBC Driver 17 for SQL Server** (for migration script)
   - Download: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

4. **Python 3.10+** with pip

5. **FilaOps v2.x code** cloned/downloaded

---

## Upgrade Steps

### Step 1: Back Up Your SQL Server Database

**CRITICAL**: Before doing anything else, back up your production database.

```sql
-- In SQL Server Management Studio or sqlcmd:
BACKUP DATABASE [YourDatabaseName]
TO DISK = 'C:\Backups\filaops_v1_backup.bak'
WITH FORMAT, COMPRESSION;
```

Or use SQL Server Management Studio: Right-click database → Tasks → Back Up...

### Step 2: Install PostgreSQL

1. Download PostgreSQL 15+ from https://www.postgresql.org/download/
2. Run the installer
3. Remember the password you set for the `postgres` user
4. Ensure the PostgreSQL service is running

### Step 3: Create the PostgreSQL Database

```bash
# Using psql (PostgreSQL command line)
psql -U postgres

# Create the database
CREATE DATABASE filaops;

# Verify it was created
\l
```

Or use pgAdmin: Right-click "Databases" → Create → Database...

### Step 4: Set Up FilaOps v2.x

```bash
# Clone or download v2.x code
cd C:\repos  # or your preferred location
git clone https://github.com/Blb3D/filaops.git
cd filaops

# Set up Python virtual environment
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Configure Environment

Create or update `backend/.env`:

```env
# Database Configuration (PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=filaops
DB_USER=postgres
DB_PASSWORD=your_postgres_password

# Security
SECRET_KEY=generate-a-random-string-here

# Environment
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO

# CORS (adjust ports if needed)
CORS_ORIGINS=["http://localhost:5173","http://localhost:5174"]
```

### Step 6: Create Database Schema

```bash
cd backend
.\venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Linux/Mac

# Run Alembic migrations to create all tables
alembic upgrade head

# Verify tables were created
alembic current
```

### Step 7: Migrate Your Data

**IMPORTANT**: Test on a copy first! If possible, restore your SQL Server backup to a test instance.

#### Option A: Use the Migration Script (Recommended)

```bash
cd backend

# First, do a DRY RUN to verify connectivity and see what will be migrated
python scripts/migrate_sqlserver_to_postgres.py \
    --source-conn "mssql+pyodbc://localhost\SQLEXPRESS/YourDB?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes" \
    --target-conn "postgresql://postgres:yourpassword@localhost:5432/filaops" \
    --dry-run \
    --output migration_dryrun.json
```

Review the output. If everything looks correct:

```bash
# Run the actual migration
python scripts/migrate_sqlserver_to_postgres.py \
    --source-conn "mssql+pyodbc://localhost\SQLEXPRESS/YourDB?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes" \
    --target-conn "postgresql://postgres:yourpassword@localhost:5432/filaops" \
    --output migration_report.json
```

#### Option B: Manual Export/Import

If the script doesn't work for your setup, you can export data manually:

1. Export each table from SQL Server to CSV
2. Import CSVs into PostgreSQL using pgAdmin or `\copy`

### Step 8: Verify the Migration

Check that your data transferred correctly:

```bash
# Connect to PostgreSQL
psql -U postgres -d filaops

# Check row counts for key tables
SELECT 'products' as table_name, COUNT(*) as count FROM products
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory
UNION ALL SELECT 'production_orders', COUNT(*) FROM production_orders
UNION ALL SELECT 'purchase_orders', COUNT(*) FROM purchase_orders
UNION ALL SELECT 'sales_orders', COUNT(*) FROM sales_orders;
```

Compare these counts with your SQL Server database. They should match.

### Step 9: Update Port References

If you have bookmarks, scripts, or reverse proxy configs pointing to port 8001, update them to port **8000**.

### Step 10: Start the Application

```bash
# Terminal 1 - Backend
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm install  # first time only
npm run dev
```

Open http://localhost:5173 and verify your data is there.

---

## Troubleshooting

### "Connection refused" to SQL Server

- Ensure SQL Server is running
- Check SQL Server Configuration Manager → SQL Server Network Configuration → TCP/IP is enabled
- Verify the ODBC driver is installed

### "relation does not exist" errors

The PostgreSQL schema wasn't created. Run:

```bash
cd backend
alembic upgrade head
```

### Migration script fails mid-way

The script is safe to re-run. However, you may need to:

1. Truncate the partially-migrated tables in PostgreSQL
2. Re-run the migration script

```sql
-- In PostgreSQL, truncate all tables (CAREFUL - deletes all data!)
TRUNCATE TABLE inventory, production_orders, purchase_orders, sales_orders CASCADE;
```

### Row counts don't match

Check the migration report JSON for specific errors. Common issues:

- Foreign key violations (parent record doesn't exist)
- Data type conversion errors
- NULL constraint violations

### Frontend can't connect to backend

1. Verify backend is running on port 8000: http://localhost:8000/docs
2. Check browser console for CORS errors
3. Verify `CORS_ORIGINS` in `.env` includes your frontend URL

---

## FAQ

### Q: Can I run v1.x and v2.x side by side?

Yes, temporarily. Run them on different ports and point them at different databases. This is useful for verification.

### Q: Do I need to keep SQL Server after migrating?

No, but keep your backup! You can uninstall SQL Server after verifying everything works in PostgreSQL.

### Q: What about my custom reports/queries?

SQL Server and PostgreSQL have some syntax differences. You may need to update custom queries:

| SQL Server | PostgreSQL |
|------------|------------|
| `TOP 10` | `LIMIT 10` |
| `GETDATE()` | `NOW()` |
| `ISNULL()` | `COALESCE()` |
| `[column]` | `"column"` |

### Q: How long does migration take?

Depends on data volume:
- Small (<1,000 records): 5-10 minutes
- Medium (1,000-10,000 records): 15-30 minutes
- Large (10,000+ records): 30-60 minutes

### Q: Can I go back to v1.x if something goes wrong?

Yes - that's why we back up first! Restore your SQL Server backup and run the old code.

### Q: I use Docker. What happened to it?

Docker support was removed in v2.0 to simplify deployment. PostgreSQL and the application now run natively. This actually makes development easier - no Docker knowledge required.

---

## Getting Help

If you run into issues:

1. Check the [GitHub Issues](https://github.com/Blb3D/filaops/issues) for similar problems
2. Open a new issue with:
   - Your v1.x version
   - Error messages (full text)
   - Output from migration script
   - Your OS and PostgreSQL version

---

## Linux/Mac Users

The steps above are written for Windows but work on Linux/Mac with minor changes:

- Use `source venv/bin/activate` instead of `.\venv\Scripts\activate`
- Path separators are `/` instead of `\`
- PostgreSQL is often installed via package manager (`apt`, `brew`, etc.)

The migration script and all Python code works identically on all platforms.
