# SQL Server → PostgreSQL Migration Runbook

> **Upgrading from v1.x?** See [UPGRADE_v1_to_v2.md](UPGRADE_v1_to_v2.md) for the complete upgrade guide.

## Overview

This runbook describes the big-bang cutover process for migrating from SQL Server to PostgreSQL.

## Prerequisites

1. **PostgreSQL installed and running** (local or remote)
2. **DEV database created**: `BLB3D_ERP_DEV` (or your target DB name)
3. **Migration script ready**: `backend/scripts/migrate_sqlserver_to_postgres.py`
4. **Backup of production SQL Server database** (safety)
5. **Maintenance window scheduled** (for production cutover)

## Pre-Migration Checklist

- [ ] Backup production SQL Server database
- [ ] Verify PostgreSQL is accessible
- [ ] Create target PostgreSQL database
- [ ] Run schema migrations on PostgreSQL (create tables)
- [ ] Test migration script on a copy of production data
- [ ] Verify reconciliation report shows 100% match
- [ ] Schedule maintenance window
- [ ] Notify users of downtime

## Migration Steps

### Step 1: Freeze Production System

**Stop all writes to production database:**

1. Stop backend API server
2. Stop frontend (or redirect to maintenance page)
3. Verify no active connections to database

```powershell
# Check active connections (SQL Server)
sqlcmd -S localhost\SQLEXPRESS -d BLB3D_ERP -Q "SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE database_id = DB_ID()"
```

### Step 2: Final Data Export

**Run migration script in DRY-RUN mode first:**

```powershell
cd <YOUR_FILAOPS_PATH>\backend
python scripts\migrate_sqlserver_to_postgres.py `
    --source-conn "mssql+pyodbc://localhost\SQLEXPRESS/<YOUR_SQLSERVER_DB>?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes" `
    --target-conn "postgresql+psycopg://postgres:<PASSWORD>@localhost:5432/<YOUR_POSTGRES_DB>" `
    --dry-run `
    --output migration_report_dryrun.json
```

**Review the reconciliation report** - all counts should match.

### Step 3: Actual Migration

**Run migration script (no dry-run):**

```powershell
python scripts\migrate_sqlserver_to_postgres.py `
    --source-conn "mssql+pyodbc://localhost\SQLEXPRESS/<YOUR_SQLSERVER_DB>?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes" `
    --target-conn "postgresql+psycopg://postgres:<PASSWORD>@localhost:5432/<YOUR_POSTGRES_DB>" `
    --output migration_report.json
```

**Expected output:**
- Tables migrated: ~30-40
- Rows migrated: varies by data volume
- Errors: 0
- Reconciliation: all key totals match

### Step 4: Verify Data Integrity

**Check reconciliation report:**

```json
{
  "key_totals": {
    "inventory": {
      "source_count": 150,
      "target_count": 150,
      "match": true
    },
    "production_orders": {
      "source_count": 45,
      "target_count": 45,
      "match": true
    },
    ...
  }
}
```

**Manual verification queries:**

```sql
-- PostgreSQL
SELECT COUNT(*) FROM inventory;
SELECT COUNT(*) FROM production_orders WHERE status = 'in_progress';
SELECT SUM(on_hand_quantity) FROM inventory;
```

Compare with SQL Server:

```sql
-- SQL Server
SELECT COUNT(*) FROM inventory;
SELECT COUNT(*) FROM production_orders WHERE status = 'in_progress';
SELECT SUM(on_hand_quantity) FROM inventory;
```

### Step 5: Update Application Configuration

**Update `.env` or environment variables:**

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=<YOUR_POSTGRES_DB>
DB_USER=postgres
DB_PASSWORD=<YOUR_PASSWORD>
```

### Step 6: Smoke Test

**Start backend:**

```powershell
cd <YOUR_FILAOPS_PATH>\backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Test key workflows:**
1. Login
2. View production orders
3. View inventory
4. Create a test production order
5. Check material availability

### Step 7: Cutover

**If smoke tests pass:**

1. **Rename production directory** (backup):

   ```powershell
   Rename-Item <YOUR_PRODUCTION_PATH> <YOUR_PRODUCTION_PATH>_BACKUP_$(Get-Date -Format 'yyyyMMdd_HHmmss')
   ```

2. **Rename DEV to production**:

   ```powershell
   Rename-Item <YOUR_DEV_PATH> <YOUR_PRODUCTION_PATH>
   ```

3. **Update production `.env`** with PostgreSQL connection

4. **Start production servers**

5. **Monitor for errors**

## Rollback Plan

**If issues occur:**

1. Stop new system
2. Rename directories back:

   ```powershell
   Rename-Item <YOUR_PRODUCTION_PATH> <YOUR_PRODUCTION_PATH>_FAILED
   Rename-Item <YOUR_PRODUCTION_PATH>_BACKUP_* <YOUR_PRODUCTION_PATH>
   ```

3. Restart old system (SQL Server)
4. Investigate issues in DEV environment

## Post-Migration

- [ ] Monitor application logs for 24 hours
- [ ] Verify all workflows function correctly
- [ ] Update documentation
- [ ] Archive SQL Server backup
- [ ] Update backup procedures for PostgreSQL

## Troubleshooting

### Connection Errors

**PostgreSQL connection refused:**
- Check PostgreSQL service is running
- Verify firewall allows port 5432
- Check `pg_hba.conf` allows connections

### Data Type Mismatches

**Decimal/Numeric precision:**
- SQL Server uses different precision defaults
- Migration script converts to float, then Postgres stores as NUMERIC
- Verify critical financial data manually

### Foreign Key Violations

**If FK violations occur:**
- Check table migration order
- Verify all parent tables migrated before children
- May need to disable FK checks temporarily

## Common Mistakes

### Trying to run Alembic migrations against SQL Server

**Symptom**: Error about column already existing, or PostgreSQL-specific syntax errors.

**Cause**: You're running PostgreSQL migrations against a SQL Server database, or vice versa.

**Solution**: Alembic migrations are for PostgreSQL only. Use the migration script to copy data from SQL Server to PostgreSQL first.

### Using wrong port (8001 vs 8000)

**Symptom**: Frontend can't connect to backend, or API calls fail.

**Cause**: v1.x used port 8001, v2.x uses port 8000.

**Solution**: Update all references to use port 8000.

### Running migration without creating schema first

**Symptom**: "relation does not exist" errors during migration.

**Cause**: PostgreSQL tables don't exist yet.

**Solution**: Run `alembic upgrade head` before running the migration script.

### Not backing up before migration

**Symptom**: Data loss if something goes wrong.

**Solution**: ALWAYS back up your SQL Server database before starting. See Step 1 of the upgrade guide.

## Notes

- Migration is **one-way** - no sync back to SQL Server
- All timestamps are preserved (UTC)
- IDs are preserved (no renumbering)
- Migration script is **read-only** on source (safe)
