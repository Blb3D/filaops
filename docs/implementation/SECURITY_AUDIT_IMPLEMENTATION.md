# FilaOps Security Audit System - Implementation Specification

**Version:** 1.0  
**Date:** 2026-01-04  
**Status:** Ready for Implementation  
**Priority:** High - Required for Enterprise/Regulated Industry Customers

---

## Executive Summary

FilaOps needs a comprehensive security audit system that allows users to:
1. Verify their installation is secure post-deployment
2. Monitor ongoing security posture via admin dashboard
3. Generate exportable compliance reports for auditors
4. Prove data privacy (especially for local AI with Ollama)

This document provides complete specifications for implementation.

---

## Part 1: Security Audit CLI Script

### Purpose
A standalone Python script users run after installation to verify security configuration.

### Location
`backend/scripts/security_audit.py`

### Usage
```bash
cd backend
python scripts/security_audit.py

# Or with options
python scripts/security_audit.py --json --output report.json
python scripts/security_audit.py --format pdf --output security_report.pdf
```

### Checks to Implement

```python
SECURITY_CHECKS = [
    {
        "id": "secret_key_not_default",
        "name": "SECRET_KEY Strength",
        "category": "critical",
        "description": "SECRET_KEY must not be a default/known value",
        "remediation": "Generate a secure key: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    },
    {
        "id": "secret_key_entropy",
        "name": "SECRET_KEY Entropy",
        "category": "critical", 
        "description": "SECRET_KEY must be at least 64 characters of random data",
        "remediation": "Generate a longer key with high entropy"
    },
    {
        "id": "environment_production",
        "name": "Production Environment",
        "category": "critical",
        "description": "ENVIRONMENT must be set to 'production'",
        "remediation": "Set ENVIRONMENT=production in .env"
    },
    {
        "id": "debug_disabled",
        "name": "Debug Mode Disabled",
        "category": "critical",
        "description": "DEBUG must be false in production",
        "remediation": "Set DEBUG=false in .env"
    },
    {
        "id": "https_enabled",
        "name": "HTTPS Enabled",
        "category": "critical",
        "description": "Application should be served over HTTPS",
        "remediation": "Configure Caddy or another reverse proxy with TLS"
    },
    {
        "id": "cors_not_wildcard",
        "name": "CORS Configuration",
        "category": "warning",
        "description": "CORS should not allow wildcard (*) origins",
        "remediation": "Set specific origins in ALLOWED_ORIGINS"
    },
    {
        "id": "admin_password_changed",
        "name": "Admin Password Changed",
        "category": "critical",
        "description": "Default admin password must be changed",
        "remediation": "Change admin password via Settings > Users"
    },
    {
        "id": "rate_limiting_enabled",
        "name": "Rate Limiting",
        "category": "warning",
        "description": "Rate limiting should be enabled on auth endpoints",
        "remediation": "Verify rate_limit.py middleware is active"
    },
    {
        "id": "database_ssl",
        "name": "Database SSL",
        "category": "warning",
        "description": "Database connection should use SSL",
        "remediation": "Add ?sslmode=require to DATABASE_URL"
    },
    {
        "id": "env_file_not_exposed",
        "name": ".env Not Accessible",
        "category": "critical",
        "description": ".env file should not be web-accessible",
        "remediation": "Ensure reverse proxy blocks dotfiles"
    },
    {
        "id": "dependencies_secure",
        "name": "Dependencies Secure",
        "category": "warning",
        "description": "No known vulnerabilities in dependencies",
        "remediation": "Run: pip install pip-audit && pip-audit"
    },
    {
        "id": "external_ai_blocked",
        "name": "External AI Blocked (Optional)",
        "category": "info",
        "description": "External AI services are blocked for data privacy",
        "remediation": "Enable in Settings > AI Configuration if required"
    },
    {
        "id": "backup_configured",
        "name": "Backup Configured",
        "category": "warning",
        "description": "Database backup should be configured",
        "remediation": "Set up pg_dump cron job or backup service"
    }
]
```

### Output Format

#### Console Output (default)
```
╔══════════════════════════════════════════════════════════════════════╗
║                    FilaOps Security Audit v1.0                       ║
║                    Generated: 2026-01-04 15:30:00                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  CRITICAL CHECKS                                                     ║
║  ───────────────                                                     ║
║  ✅ SECRET_KEY Strength         Strong key configured                ║
║  ✅ SECRET_KEY Entropy          72 characters (good)                 ║
║  ✅ Production Environment      ENVIRONMENT=production               ║
║  ✅ Debug Mode Disabled         DEBUG=false                          ║
║  ✅ HTTPS Enabled               TLS detected via Caddy               ║
║  ❌ Admin Password Changed      Default password still in use!       ║
║  ✅ .env Not Accessible         Blocked by reverse proxy             ║
║                                                                      ║
║  WARNINGS                                                            ║
║  ────────                                                            ║
║  ⚠️  CORS Configuration          Wildcard origin detected            ║
║  ✅ Rate Limiting               Enabled on /api/v1/auth/*            ║
║  ⚠️  Database SSL                SSL not enabled                      ║
║  ⚠️  Dependencies Secure         2 packages have known CVEs          ║
║  ✅ Backup Configured           pg_dump scheduled daily              ║
║                                                                      ║
║  INFORMATIONAL                                                       ║
║  ─────────────                                                       ║
║  ✅ External AI Blocked         Cloud AI services disabled           ║
║  ℹ️  Data Privacy Mode           Ollama (local) configured           ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  SUMMARY: 9 PASS │ 3 WARN │ 1 FAIL                                   ║
║                                                                      ║
║  ❌ ACTION REQUIRED: 1 critical issue must be resolved               ║
╚══════════════════════════════════════════════════════════════════════╝

FAILED CHECKS - REMEDIATION REQUIRED:
────────────────────────────────────

1. Admin Password Changed [CRITICAL]
   Issue: Default admin password is still in use
   Fix: Navigate to Settings > Users and change the admin password
   
WARNINGS - RECOMMENDED FIXES:
────────────────────────────

1. CORS Configuration
   Issue: ALLOWED_ORIGINS contains wildcard (*)
   Fix: Set specific origins in .env: ALLOWED_ORIGINS=https://filaops.yourdomain.com

2. Database SSL
   Issue: Database connection is not encrypted
   Fix: Add ?sslmode=require to DATABASE_URL in .env

3. Dependencies Secure
   Issue: 2 packages have known vulnerabilities
   Affected: cryptography==41.0.0 (CVE-2024-XXXX), requests==2.28.0 (CVE-2024-YYYY)
   Fix: Run: pip install --upgrade cryptography requests
```

#### JSON Output (--json flag)
```json
{
  "audit_version": "1.0",
  "generated_at": "2026-01-04T15:30:00Z",
  "filaops_version": "2.0.1",
  "environment": "production",
  "summary": {
    "total_checks": 13,
    "passed": 9,
    "warnings": 3,
    "failed": 1,
    "overall_status": "FAIL"
  },
  "checks": [
    {
      "id": "secret_key_not_default",
      "name": "SECRET_KEY Strength",
      "category": "critical",
      "status": "pass",
      "message": "Strong key configured",
      "details": null
    },
    {
      "id": "admin_password_changed",
      "name": "Admin Password Changed", 
      "category": "critical",
      "status": "fail",
      "message": "Default password still in use",
      "remediation": "Navigate to Settings > Users and change the admin password"
    }
  ],
  "system_info": {
    "os": "Windows 10",
    "python_version": "3.11.0",
    "database": "PostgreSQL 16.0",
    "reverse_proxy": "Caddy 2.7.0"
  }
}
```

---

## Part 2: Admin Dashboard Security Page

### Purpose
A real-time security status page in the admin UI.

### Location
- Backend: `backend/app/api/v1/endpoints/security.py`
- Frontend: `frontend/src/pages/admin/SecurityDashboard.jsx`
- Route: `/admin/security`

### API Endpoint

```python
# backend/app/api/v1/endpoints/security.py

from fastapi import APIRouter, Depends
from typing import List
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

router = APIRouter(prefix="/security", tags=["security"])


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    INFO = "info"


class SecurityCheck(BaseModel):
    id: str
    name: str
    category: str  # critical, warning, info
    status: CheckStatus
    message: str
    remediation: str | None = None


class SecurityAuditResponse(BaseModel):
    generated_at: str
    filaops_version: str
    summary: dict
    checks: List[SecurityCheck]


@router.get("/audit", response_model=SecurityAuditResponse)
async def get_security_audit():
    """
    Run security audit and return results.
    Requires admin authentication.
    """
    # Import and run auditor
    from scripts.security_audit import SecurityAuditor
    
    auditor = SecurityAuditor()
    auditor.run_all_checks()
    
    return SecurityAuditResponse(
        generated_at=datetime.now().isoformat(),
        filaops_version="2.0.1",
        summary=auditor.get_summary(),
        checks=[
            SecurityCheck(
                id=r.id,
                name=r.name,
                category=r.category.value,
                status=r.status.value,
                message=r.message,
                remediation=r.remediation
            )
            for r in auditor.results
        ]
    )


@router.get("/audit/export")
async def export_security_audit(format: str = "json"):
    """
    Export security audit report.
    Formats: json, pdf
    """
    # Implementation for exportable reports
    pass
```

### Frontend Component

See full implementation in the complete spec document.

---

## Part 3: Sync Production AI Changes to Dev Repo

### Changes Made in Production (need to sync)

Based on the implementation summary, these files need to be synced from `C:\BLB3D_Production` to `C:\repos\filaops`:

#### Database Migration Required
```sql
-- Add to new migration file
ALTER TABLE company_settings ADD COLUMN ai_provider VARCHAR(50);
ALTER TABLE company_settings ADD COLUMN ai_api_key VARCHAR(500);
ALTER TABLE company_settings ADD COLUMN ai_ollama_url VARCHAR(255);
ALTER TABLE company_settings ADD COLUMN ai_ollama_model VARCHAR(100);
ALTER TABLE company_settings ADD COLUMN external_ai_blocked BOOLEAN DEFAULT FALSE;
```

#### Files to Sync
1. `backend/app/models/company_settings.py` - AI config columns
2. `backend/app/api/v1/endpoints/settings.py` - AI endpoints
3. `frontend/src/components/SecurityBadge.jsx` - NEW
4. `frontend/src/components/AdminLayout.jsx` - SecurityBadge integration
5. `frontend/src/pages/admin/AdminSettings.jsx` - AI configuration UI

### Sync Process
```powershell
# From C:\repos\filaops

# 1. Create feature branch
git checkout -b feature/ai-configuration-ui

# 2. Copy files from production
# (Manual copy or use robocopy)

# 3. Create migration
cd backend
alembic revision --autogenerate -m "add_ai_configuration_columns"

# 4. Test locally
# 5. Commit and push
```

---

## Part 4: Caddy as Standard Installation

### Recommendation: YES

Caddy should be the standard installation method because:

1. **Automatic HTTPS** - Handles TLS certificates automatically
2. **Simple configuration** - Single Caddyfile vs complex nginx config
3. **Secure by default** - HTTP/2, TLS 1.3, security headers built-in
4. **Cross-platform** - Works on Windows, Linux, macOS
5. **No dependencies** - Single binary, no OpenSSL to manage

### Standard Caddyfile Template

```caddyfile
# FilaOps Production Caddyfile
# Save as: Caddyfile (in installation directory)

{
    # Global options
    admin off  # Disable admin API for security
}

# Replace with your domain or use localhost for local deployment
filaops.yourdomain.com {
    # Or for local: filaops.local, localhost:443

    # Security headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        -Server  # Remove server header
    }

    # Block dotfiles
    @dotfiles {
        path .*
    }
    respond @dotfiles 404

    # API routes -> Backend
    handle /api/* {
        reverse_proxy localhost:8000
    }

    # WebSocket for real-time updates
    handle /ws/* {
        reverse_proxy localhost:8000
    }

    # Frontend static files
    handle {
        root * /path/to/frontend/dist
        try_files {path} /index.html
        file_server
    }

    # Logging
    log {
        output file /var/log/caddy/filaops.log
        format json
    }
}
```

---

## Part 5: Documentation Cleanup Checklist

### Files to Review/Update

| File | Status | Action Required |
|------|--------|-----------------|
| `README.md` | 🔄 Review | Update with Caddy as default |
| `INSTALL.md` | 🔄 Review | Rewrite for Caddy-first approach |
| `GETTING_STARTED.md` | 🔄 Review | Simplify, add security steps |
| `FilaOps_Zero-to-Running_Windows.md` | 🔄 Review | Add Caddy, security audit |
| `FilaOps_Zero-to-Running_macOS_Linux_SSH.md` | 🔄 Review | Add Caddy, security audit |
| `SETUP_GUIDE.md` | ❓ Check | May be redundant |
| `QUICK_START.md` | ❓ Check | May be redundant |
| `TROUBLESHOOTING.md` | 🔄 Review | Add security-related issues |
| `FAQ.md` | 🔄 Review | Add security questions |
| `docker-compose.yml` | 🔄 Review | Add Caddy container |

### Documentation Structure Proposal

```
docs/
├── README.md                    # Overview, quick links
├── getting-started/
│   ├── INSTALLATION.md          # Complete install guide (Caddy default)
│   ├── QUICK_START.md           # 5-minute setup
│   ├── SECURITY_SETUP.md        # Security configuration guide
│   └── UPGRADING.md             # Version upgrade instructions
├── configuration/
│   ├── ENVIRONMENT.md           # .env reference
│   ├── CADDY.md                 # Caddy configuration
│   ├── DATABASE.md              # PostgreSQL setup
│   └── AI_PROVIDERS.md          # Ollama vs Anthropic setup
├── administration/
│   ├── SECURITY_AUDIT.md        # Using security audit tool
│   ├── BACKUP_RESTORE.md        # Database backup procedures
│   └── USER_MANAGEMENT.md       # User/role management
├── development/
│   ├── CONTRIBUTING.md          # Dev setup, PR process
│   ├── API_REFERENCE.md         # API documentation
│   └── ARCHITECTURE.md          # System architecture
└── troubleshooting/
    ├── COMMON_ISSUES.md         # FAQ / common problems
    └── SUPPORT.md               # Getting help
```

---

## Implementation Order

### Phase 1: Core Security (This Week)
1. ✅ Clean dev repo .env (DONE)
2. ✅ Verify production SECRET_KEY (DONE)
3. [ ] Implement `security_audit.py` script
4. [ ] Add `/admin/security` dashboard page
5. [ ] Sync AI configuration from production to dev repo

### Phase 2: Installation Improvements (Next Week)
6. [ ] Create standard Caddyfile template
7. [ ] Add Caddy installation script
8. [ ] Update docker-compose.yml with Caddy

### Phase 3: Documentation (Following Week)
9. [ ] Restructure docs folder
10. [ ] Rewrite INSTALLATION.md with Caddy-first approach
11. [ ] Create SECURITY_SETUP.md guide
12. [ ] Archive/remove redundant docs
13. [ ] Update README.md

---

## GitHub Issues to Create

1. **[SECURITY] Implement security audit CLI tool**
   - Labels: security, enhancement, priority:high
   
2. **[SECURITY] Add admin security dashboard**
   - Labels: security, frontend, enhancement
   
3. **[FEATURE] Sync AI configuration UI from production**
   - Labels: feature, backend, frontend
   
4. **[INFRA] Add Caddy as standard installation**
   - Labels: infrastructure, documentation
   
5. **[DOCS] Documentation restructure and cleanup**
   - Labels: documentation, good-first-issue

---

## Notes for Claude Code / VS Claude

When implementing this specification:

1. **Start with the security_audit.py script** - This is the foundation
2. **Test each check individually** before combining
3. **Use existing patterns** from the codebase (see settings.py for API patterns)
4. **Create database migration** for any new columns
5. **Update requirements.txt** if adding pip-audit dependency
6. **Follow existing UI patterns** in AdminSettings.jsx for consistency

The SecurityBadge component already exists in production - sync it first before building the full dashboard.
