# FilaOps Scripts

This directory contains utility scripts organized by purpose.

## 📁 Directory Structure

### `github/`

Scripts for GitHub issue and release management:

- `create-new-issues.ps1` - Create GitHub issues from templates
- `update-completed-issues.ps1` - Update issues with completion comments
- `check-duplicate-issues.ps1` - Check for duplicate issues
- `create-core-issues.ps1` - Create core release issues
- `create-release.ps1` - Create GitHub releases
- `add-github-topics.ps1` - Add topics to repository

**Usage:** Requires GitHub CLI (`gh`) to be installed and authenticated.

### `database/`

SQL scripts for database setup and migration:

- `init-db.sql` - Initial database setup
- `setup_database.sql` - Database initialization
- `create_*.sql` - Table creation scripts
- `*_sync_*.sql` - Data synchronization scripts
- Various migration and fix scripts

**Usage:** Run these scripts against your SQL Server database.

### `tools/`

Utility Python scripts and helpers:

- `material_import.py` - Material data import utilities
- `fresh_database_setup.py` - Fresh database setup script
- `api_helper.py` - API authentication and helper functions
- Various migration and analysis tools

**Usage:** Most can be run directly with Python:

```bash
python scripts/tools/script_name.py
```

**API Scripts Configuration:**
Scripts that use `api_helper.py` require API credentials to be set as environment variables:

```bash
# Set credentials in your shell
export API_USERNAME=admin
export API_PASSWORD=your_secure_password

# Or create a .env file in the project root:
echo "API_USERNAME=admin" >> .env
echo "API_PASSWORD=your_secure_password" >> .env

# Then run the script
python scripts/tools/your_script.py
```

**Security Note:** Never commit credentials to version control. The `.env` file is gitignored.

## 🔧 PowerShell Scripts

### Prerequisites

- PowerShell 7+ (recommended)
- GitHub CLI (`gh`) for GitHub scripts
- Python 3.11+ for Python scripts

### Common Tasks

**Create GitHub Issues:**

```powershell
.\scripts\github\create-new-issues.ps1
```

**Update Completed Issues:**

```powershell
.\scripts\github\update-completed-issues.ps1
```

**Check for Duplicates:**

```powershell
.\scripts\github\check-duplicate-issues.ps1
```

## 📝 Notes

- All scripts include error handling and user-friendly output
- GitHub scripts require authentication: `gh auth login`
- Database scripts should be run with appropriate permissions
- Always review scripts before running in production

---

For more information, see the main [README.md](../README.md) or [CONTRIBUTING.md](../CONTRIBUTING.md).
