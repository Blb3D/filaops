"""
Security Audit API Endpoints

Provides security audit functionality for the admin dashboard:
- Run security audits
- Export audit reports
- Check security status
"""
import sys
import os
from datetime import datetime
from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User
from app.api.v1.endpoints.auth import get_current_user
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/security", tags=["Security"])


# ============================================================================
# SCHEMAS
# ============================================================================

class CheckStatusEnum(str, Enum):
    """Status of a security check"""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    INFO = "info"


class CheckCategoryEnum(str, Enum):
    """Category/severity of a security check"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class SecurityCheck(BaseModel):
    """Single security check result"""
    id: str
    name: str
    category: str
    status: str
    message: str
    details: Optional[str] = None
    remediation: Optional[str] = None


class SecuritySummary(BaseModel):
    """Summary of security audit"""
    total_checks: int
    passed: int
    failed: int
    warnings: int
    info: int
    overall_status: str  # PASS, WARN, or FAIL


class SystemInfo(BaseModel):
    """System information"""
    os: str
    python_version: str
    database: str
    reverse_proxy: str


class SecurityAuditResponse(BaseModel):
    """Full security audit response"""
    audit_version: str
    generated_at: str
    filaops_version: str
    environment: str
    summary: SecuritySummary
    checks: List[SecurityCheck]
    system_info: SystemInfo


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_security_audit() -> dict:
    """Run the security audit and return results as dict"""
    # Add scripts directory to path if needed
    scripts_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "scripts"
    )
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    try:
        from scripts.security_audit import SecurityAuditor

        auditor = SecurityAuditor()
        auditor.run_all_checks()
        return auditor.to_dict()
    except ImportError as e:
        logger.error(f"Failed to import security_audit module: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Security audit module not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Security audit failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Security audit failed: {str(e)}"
        )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/audit", response_model=SecurityAuditResponse)
async def get_security_audit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Run security audit and return results.

    Requires admin authentication.
    """
    # Require admin role
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )

    logger.info(f"Security audit requested by {current_user.email}")

    result = run_security_audit()

    # Convert to response model
    return SecurityAuditResponse(
        audit_version=result.get("audit_version", "1.0"),
        generated_at=result.get("generated_at", datetime.now().isoformat()),
        filaops_version=result.get("filaops_version", "unknown"),
        environment=result.get("environment", "unknown"),
        summary=SecuritySummary(**result.get("summary", {
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "info": 0,
            "overall_status": "UNKNOWN"
        })),
        checks=[SecurityCheck(**check) for check in result.get("checks", [])],
        system_info=SystemInfo(**result.get("system_info", {
            "os": "unknown",
            "python_version": "unknown",
            "database": "unknown",
            "reverse_proxy": "unknown"
        }))
    )


@router.get("/audit/export")
async def export_security_audit(
    format: str = "json",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export security audit report.

    Formats: json (default)
    Future: pdf

    Requires admin authentication.
    """
    # Require admin role
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )

    if format not in ["json"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported format. Available: json"
        )

    logger.info(f"Security audit export ({format}) requested by {current_user.email}")

    result = run_security_audit()

    if format == "json":
        # Add export metadata
        result["exported_at"] = datetime.now().isoformat()
        result["exported_by"] = current_user.email

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"filaops_security_audit_{timestamp}.json"
        return JSONResponse(
            content=result,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    # Future: PDF export
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="PDF export not yet implemented"
    )


@router.get("/status")
async def get_security_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get quick security status overview.

    Returns a simplified status for display in navigation/header.
    Requires authentication.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )

    try:
        result = run_security_audit()
        summary = result.get("summary", {})

        overall = summary.get("overall_status", "UNKNOWN")
        critical_fails = summary.get("failed", 0)
        warnings = summary.get("warnings", 0)

        # Determine status level for UI
        if overall == "FAIL":
            status_level = "critical"
            status_message = f"{critical_fails} critical issue(s) require attention"
        elif overall == "WARN":
            status_level = "warning"
            status_message = f"{warnings} warning(s) should be reviewed"
        elif overall == "PASS":
            status_level = "healthy"
            status_message = "All security checks passed"
        else:
            status_level = "unknown"
            status_message = "Security status unknown"

        return {
            "status": status_level,
            "message": status_message,
            "summary": summary,
            "checked_at": result.get("generated_at", datetime.now().isoformat())
        }

    except Exception as e:
        logger.error(f"Failed to get security status: {e}")
        return {
            "status": "error",
            "message": f"Could not check security status: {str(e)}",
            "summary": None,
            "checked_at": datetime.now().isoformat()
        }


# ============================================================================
# REMEDIATION HELPERS
# ============================================================================

@router.post("/remediate/generate-secret-key")
async def generate_secret_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a secure SECRET_KEY for the user to copy.

    Does NOT automatically update the .env file - user must do that manually.
    This is intentional for security (we don't want to auto-modify config files).
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )

    import secrets
    new_key = secrets.token_urlsafe(64)

    logger.info(f"SECRET_KEY generated for remediation by {current_user.email}")

    return {
        "secret_key": new_key,
        "length": len(new_key),
        "instructions": [
            "Copy the generated key above",
            "Open your backend/.env file",
            "Find the line: SECRET_KEY=...",
            "Replace the value with the new key",
            "Save the file and restart the backend"
        ]
    }


@router.get("/remediate/{check_id}")
async def get_remediation_steps(
    check_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed remediation steps for a specific check.

    Returns step-by-step instructions, code snippets, and file paths.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )

    # Remediation guides for each check
    remediation_guides = {
        "secret_key_not_default": {
            "title": "Fix: Weak SECRET_KEY",
            "severity": "critical",
            "estimated_time": "2 minutes",
            "can_auto_generate": True,
            "steps": [
                {
                    "step": 1,
                    "title": "Generate a Secure Key",
                    "description": "Click the button below to generate a cryptographically secure key.",
                    "action": "generate_key"
                },
                {
                    "step": 2,
                    "title": "Update Your .env File",
                    "description": "Open your backend configuration file and replace the SECRET_KEY value.",
                    "file_path": "backend/.env",
                    "code_before": "SECRET_KEY=change-this-to-a-random-secret-key-in-production",
                    "code_after": "SECRET_KEY=<your-generated-key>"
                },
                {
                    "step": 3,
                    "title": "Restart the Backend",
                    "description": "The new key takes effect after restarting the server.",
                    "command": "Ctrl+C then run start-backend.ps1 again"
                }
            ]
        },
        "secret_key_entropy": {
            "title": "Fix: SECRET_KEY Too Short",
            "severity": "warning",
            "estimated_time": "2 minutes",
            "can_auto_generate": True,
            "steps": [
                {
                    "step": 1,
                    "title": "Generate a Longer Key",
                    "description": "Generate a new key with at least 64 characters.",
                    "action": "generate_key"
                },
                {
                    "step": 2,
                    "title": "Update Your .env File",
                    "description": "Replace the existing SECRET_KEY with the longer one.",
                    "file_path": "backend/.env"
                },
                {
                    "step": 3,
                    "title": "Restart the Backend",
                    "description": "Restart to apply the new key."
                }
            ]
        },
        "https_enabled": {
            "title": "Fix: Enable HTTPS",
            "severity": "warning",
            "estimated_time": "15 minutes",
            "can_auto_generate": False,
            "steps": [
                {
                    "step": 1,
                    "title": "Install Caddy (Recommended)",
                    "description": "Caddy automatically handles HTTPS certificates.",
                    "command": "Download from https://caddyserver.com/download",
                    "docs_url": "https://caddyserver.com/docs/quick-starts/https"
                },
                {
                    "step": 2,
                    "title": "Create a Caddyfile",
                    "description": "Create a file named 'Caddyfile' in your project root:",
                    "code_snippet": """yourdomain.com {
    reverse_proxy localhost:8000

    # Block sensitive files
    @blocked path /.env /.git/* /.*
    respond @blocked 404
}"""
                },
                {
                    "step": 3,
                    "title": "Update FRONTEND_URL",
                    "description": "Update your .env to use HTTPS URLs:",
                    "file_path": "backend/.env",
                    "code_snippet": "FRONTEND_URL=https://yourdomain.com"
                },
                {
                    "step": 4,
                    "title": "Start Caddy",
                    "description": "Run Caddy to start serving with HTTPS.",
                    "command": "caddy run"
                }
            ]
        },
        "cors_not_wildcard": {
            "title": "Fix: CORS Configuration",
            "severity": "warning",
            "estimated_time": "5 minutes",
            "can_auto_generate": False,
            "steps": [
                {
                    "step": 1,
                    "title": "Open Your .env File",
                    "description": "Find the ALLOWED_ORIGINS setting.",
                    "file_path": "backend/.env"
                },
                {
                    "step": 2,
                    "title": "Update Allowed Origins",
                    "description": "Replace localhost with your production domain(s):",
                    "code_before": 'ALLOWED_ORIGINS=["http://localhost:5173"]',
                    "code_after": 'ALLOWED_ORIGINS=["https://yourdomain.com"]'
                },
                {
                    "step": 3,
                    "title": "Restart the Backend",
                    "description": "Restart to apply the new CORS settings."
                }
            ]
        },
        "admin_password_changed": {
            "title": "Fix: Change Admin Password",
            "severity": "critical",
            "estimated_time": "1 minute",
            "can_auto_generate": False,
            "steps": [
                {
                    "step": 1,
                    "title": "Go to Team Members",
                    "description": "Navigate to Admin > Team Members in the sidebar.",
                    "action": "navigate",
                    "navigate_to": "/admin/users"
                },
                {
                    "step": 2,
                    "title": "Edit Admin User",
                    "description": "Find the admin user and click Edit."
                },
                {
                    "step": 3,
                    "title": "Set a Strong Password",
                    "description": "Use a password with at least 12 characters, including uppercase, lowercase, numbers, and symbols."
                }
            ]
        },
        "dependencies_secure": {
            "title": "Fix: Check Dependencies for Vulnerabilities",
            "severity": "warning",
            "estimated_time": "5 minutes",
            "can_auto_generate": False,
            "steps": [
                {
                    "step": 1,
                    "title": "Install pip-audit",
                    "description": "Install the vulnerability scanner:",
                    "command": "pip install pip-audit"
                },
                {
                    "step": 2,
                    "title": "Run Security Audit",
                    "description": "Scan your dependencies for known CVEs:",
                    "command": "pip-audit"
                },
                {
                    "step": 3,
                    "title": "Fix Vulnerabilities",
                    "description": "Update vulnerable packages:",
                    "command": "pip-audit --fix"
                }
            ]
        },
        "rate_limiting_enabled": {
            "title": "Fix: Enable Rate Limiting",
            "severity": "warning",
            "estimated_time": "2 minutes",
            "can_auto_generate": False,
            "steps": [
                {
                    "step": 1,
                    "title": "Install SlowAPI",
                    "description": "Install the rate limiting library:",
                    "command": "pip install slowapi"
                },
                {
                    "step": 2,
                    "title": "Restart the Backend",
                    "description": "FilaOps will automatically detect and enable rate limiting."
                }
            ]
        },
        "backup_configured": {
            "title": "Fix: Configure Database Backups",
            "severity": "warning",
            "estimated_time": "10 minutes",
            "can_auto_generate": False,
            "steps": [
                {
                    "step": 1,
                    "title": "Create Backup Script",
                    "description": "Create a script to backup your PostgreSQL database:",
                    "code_snippet": """@echo off
set BACKUP_DIR=C:\\backups\\filaops
set TIMESTAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%
pg_dump -U postgres -d filaops > "%BACKUP_DIR%\\filaops_%TIMESTAMP%.sql"
"""
                },
                {
                    "step": 2,
                    "title": "Schedule Daily Backups",
                    "description": "Use Windows Task Scheduler to run the script daily.",
                    "docs_url": "https://www.postgresql.org/docs/current/backup-dump.html"
                }
            ]
        }
    }

    if check_id not in remediation_guides:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No remediation guide found for check: {check_id}"
        )

    return remediation_guides[check_id]
