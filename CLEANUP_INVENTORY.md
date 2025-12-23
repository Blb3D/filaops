# FilaOps - Codebase Cleanup Inventory

**Date**: December 23, 2025
**Status**: 🔍 IN PROGRESS - Agents scanning codebase
**Purpose**: Identify and clean up outdated Docker/SQL Server references and personal info

---

## 🎯 Cleanup Objectives

The FilaOps project has transitioned to:
- ✅ **Native PostgreSQL** (no SQL Server)
- ✅ **Native Python/Node** (no Docker)
- ⚠️ **Need to sanitize**: BLB3D company-specific references

### What Needs Cleanup

1. **Docker References** - Project no longer uses Docker
2. **SQL Server References** - Fully migrated to PostgreSQL
3. **Personal/Company Info** - BLB3D, ML Dashboard, paths, etc.
4. **Outdated Documentation** - Installation guides reference old setup

---

## 📊 Quick Scan Results

### Docker References Found
**Total Files**: 28 files with docker-compose/Dockerfile mentions

Critical files to review:
- `CLAUDE.md` - Contains Docker setup instructions
- `INSTALL.md` - References docker-compose commands
- `.github/workflows/test.yml` - CI/CD uses Docker
- `frontend/playwright.config.ts` - Test config mentions Docker
- Backend `.dockerignore` files exist

### SQL Server References Found
**Total Files**: 61 files with SQL Server/MSSQL mentions

Critical categories:
- Migration scripts (retired migrations with SQL Server code)
- Documentation (CHANGELOG, announcements mentioning SQL Server)
- Old database scripts with SQL Server syntax
- Some code comments referencing SQL Server

### Personal/Company Info Found
**Total Files**: 78 files with BLB3D references

Critical categories:
- Company name "BLB3D" throughout code
- Production paths: `C:\BLB3D_Production`
- ML Dashboard references
- Company-specific configuration

---

## 🚨 HIGH PRIORITY - Immediate Action Required

### Category 1: Documentation with False Instructions

These files contain **incorrect setup instructions** that will confuse users:

| File | Issue | Risk | Action |
|------|-------|------|--------|
| `CLAUDE.md` | Docker-compose commands, SQL Server ports | HIGH | Rewrite entire file |
| `INSTALL.md` | Docker installation steps | HIGH | Update to native install |
| `.github/workflows/test.yml` | CI/CD assumes Docker | HIGH | Rewrite for native |
| `RUN_SPRINT1_TESTS.md` | Docker compose commands | HIGH | Update server startup |
| `SPRINT1_TESTING_COMPLETE.md` | References docker-compose.dev.yml | HIGH | Fix startup instructions |

**Impact**: Users following these docs will fail to set up the project!

---

### Category 2: Code Files with SQL Server Syntax

These may contain **SQL Server specific code** that doesn't work on PostgreSQL:

| Location | Issue | Risk | Action |
|----------|-------|------|--------|
| `backend/migrations/retired/*.py` | Old SQL Server migrations | MEDIUM | Archive or delete |
| `scripts/database/*.sql` | May have MSSQL syntax (GETDATE, ISNULL) | MEDIUM | Audit and convert |
| `backend/scripts/migrate_sqlserver_to_postgres.py` | Migration tool (historical) | LOW | Keep for reference |

---

### Category 3: Personal/Company Information

Files containing **BLB3D or personal references**:

| Type | Count | Examples | Action |
|------|-------|----------|--------|
| Company name "BLB3D" | 78 files | Settings, docs, comments | Replace with "FilaOps" or "Company" |
| Production paths | Multiple | `C:\BLB3D_Production` | Remove or genericize |
| ML Dashboard | Unknown | To be determined | Remove if not generic |
| License/proprietary | 2+ files | PROPRIETARY.md, LICENSE | Review for open source |

---

## 📋 Detailed Agent Reports

### Agent 1: Docker References (RUNNING)
**Status**: Scanning all files for Docker mentions
**Progress**: Found 28 files, analyzing details...

**Initial Findings**:
- `.dockerignore` files in backend/ and frontend/
- Multiple documentation files with docker-compose instructions
- CI/CD workflows assume Docker environment
- Test configurations reference Docker services

**Waiting for complete report...**

---

### Agent 2: SQL Server References (RUNNING)
**Status**: Scanning for SQL Server code and docs
**Progress**: Found 61 files, checking for active vs retired code...

**Initial Findings**:
- Many references are in `retired/` migrations (safe to ignore)
- Some documentation mentions SQL Server migration
- Database scripts may contain MSSQL-specific syntax
- Requirements files checked (pyodbc removed ✅)

**Waiting for complete report...**

---

### Agent 3: Outdated Documentation (RUNNING)
**Status**: Analyzing markdown docs for incorrect info
**Progress**: Scanning README, INSTALL, setup guides...

**Initial Findings**:
- Multiple installation guides with Docker steps
- Port number references (1433 = SQL Server)
- Container-based deployment instructions
- CLAUDE.md has extensive Docker section

**Waiting for complete report...**

---

### Agent 4: Personal Information (RUNNING)
**Status**: Searching for BLB3D, personal info, credentials
**Progress**: Found 78 BLB3D references, scanning for other info...

**Initial Findings**:
- "BLB3D" appears in:
  - Code (settings, version info)
  - Documentation
  - Database scripts
  - Configuration files
- Production path `C:\BLB3D_Production` in multiple places
- License/proprietary files need review

**Waiting for complete report...**

---

## 🔧 Cleanup Strategy

### Phase 1: Critical Documentation (Today)
Fix documentation that will break user setup:
1. `CLAUDE.md` - Complete rewrite for native PostgreSQL
2. `INSTALL.md` - Update to native installation
3. `README.md` - Verify no Docker references
4. `GETTING_STARTED.md` - Check startup instructions
5. `RUN_SPRINT1_TESTS.md` - Fix test execution steps

**Estimated Time**: 2-3 hours

---

### Phase 2: Code Sanitization (Week 1)
Remove company-specific references:
1. Replace "BLB3D" with generic names
2. Remove production path references
3. Clean up company-specific settings
4. Review and update license files

**Estimated Time**: 4-6 hours

---

### Phase 3: Archive Old Code (Week 1)
Deal with retired/legacy code:
1. Move SQL Server migrations to archive folder
2. Document migration history
3. Delete or clearly mark Docker config as obsolete
4. Update CI/CD for native environment

**Estimated Time**: 2-4 hours

---

### Phase 4: Verification (Week 1)
Ensure cleanup is complete:
1. Re-scan for Docker references
2. Re-scan for SQL Server code
3. Re-scan for personal info
4. Test installation following new docs
5. Run all tests in native environment

**Estimated Time**: 2-3 hours

---

## 📁 Files To Archive

Create `archive/` or `legacy/` folder for:
- Old Docker compose files (if any)
- SQL Server migration scripts
- SQL Server-specific database tools
- Company-specific configurations

---

## 📝 Files To Delete

Candidates for deletion (after review):
- `.dockerignore` files (no longer needed)
- SQL Server connection testing scripts
- Obsolete CI/CD workflows
- Duplicate or outdated documentation

---

## ⚠️ Files Requiring Manual Review

Cannot be automatically cleaned:
- `LICENSE` and `PROPRIETARY.md` - Legal review needed
- Configuration files with company names
- Database scripts with company-specific data
- Any files with customer information

---

## 🎯 Success Criteria

Cleanup is complete when:
- [ ] Zero Docker references in active documentation
- [ ] Zero SQL Server code in active codebase
- [ ] All company-specific info genericized or removed
- [ ] Fresh install works following updated docs
- [ ] All tests pass in native environment
- [ ] No personal/confidential info remains

---

## 📊 Progress Tracking

### Documentation Updates
- [ ] CLAUDE.md rewritten
- [ ] INSTALL.md updated
- [ ] README.md verified
- [ ] GETTING_STARTED.md checked
- [ ] Test documentation fixed
- [ ] CI/CD docs updated

### Code Cleanup
- [ ] BLB3D references replaced
- [ ] Production paths removed
- [ ] SQL Server code archived
- [ ] Docker configs archived
- [ ] Settings sanitized

### Verification
- [ ] Re-scan completed
- [ ] Fresh install tested
- [ ] Tests pass
- [ ] Code review completed

---

## 🚀 Next Steps

**Immediate (Today)**:
1. Wait for all 4 agents to complete their scans
2. Review detailed findings
3. Prioritize files by risk level
4. Create detailed cleanup plan

**This Week**:
1. Execute Phase 1 (critical docs)
2. Execute Phase 2 (code sanitization)
3. Execute Phase 3 (archive legacy)
4. Execute Phase 4 (verification)

---

**Status**: Agents still scanning...
**ETA**: Complete reports in 5-10 minutes
**Next Update**: After agents finish
