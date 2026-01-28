"""
Admin System Management Endpoints

Handles system-level operations like updates, maintenance, etc.
"""

import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

from app.models.user import User
from app.api.v1.deps import get_current_admin_user
from app.logging_config import get_logger

router = APIRouter(prefix="/system", tags=["Admin - System"])

logger = get_logger(__name__)

# Path to project root (assuming this file is in backend/app/api/v1/endpoints/admin/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent.parent


class UpdateRequest(BaseModel):
    version: Optional[str] = None  # Specific version tag, or None for latest


class UpdateStatus(BaseModel):
    status: str  # "idle", "checking", "updating", "success", "error"
    message: str
    current_version: Optional[str] = None
    target_version: Optional[str] = None
    progress: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime


# Global update status (in production, use Redis or database)
_update_status = {
    "status": "idle",
    "message": "Ready",
    "current_version": None,
    "target_version": None,
    "progress": None,
    "error": None,
    "timestamp": datetime.now(),
}


def _is_running_in_container() -> bool:
    """Check if we're running inside a Docker container"""
    # Check for common container indicators
    if Path("/.dockerenv").exists():
        return True
    # Check cgroup (Linux containers)
    try:
        with open("/proc/self/cgroup", "r") as f:
            return "docker" in f.read() or "containerd" in f.read()
    except (FileNotFoundError, IOError):
        pass
    return False


def _check_docker_available() -> bool:
    """Check if Docker and docker-compose are available"""
    # If running in container, check if Docker socket is accessible
    if _is_running_in_container():
        # Check if Docker socket exists and is accessible
        docker_sock = Path("/var/run/docker.sock")
        if not docker_sock.exists():
            return False
        # Try to access it (may fail due to permissions)
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False

    # Not in container, check if docker/docker-compose are installed
    try:
        subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        # Try docker compose (newer) or docker-compose (older)
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # Fall back to docker-compose
            subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
        return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return False


def _check_git_available() -> bool:
    """Check if git is available"""
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return False


def _get_current_git_version() -> Optional[str]:
    """Get current git version/tag"""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.warning(f"Failed to get git version: {e}")
    return None


def _run_update(version: Optional[str] = None):
    """Run the update process in background (production only)"""
    global _update_status

    try:
        _update_status["status"] = "updating"
        _update_status["message"] = "Starting update..."
        _update_status["timestamp"] = datetime.now()

        # Step 1: Pull latest code
        _update_status["progress"] = "Pulling latest code..."
        logger.info("Pulling latest code from git")
        if version:
            result = subprocess.run(
                ["git", "fetch", "origin", f"tags/{version}"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise Exception(f"Git fetch failed: {result.stderr}")

            result = subprocess.run(
                ["git", "checkout", f"tags/{version}"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise Exception(f"Git checkout failed: {result.stderr}")
        else:
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise Exception(f"Git pull failed: {result.stderr}")

        # Step 2: Determine compose command (docker compose or docker-compose)
        compose_cmd = None
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            compose_cmd = ["docker", "compose"]
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            compose_cmd = ["docker-compose"]

        # Step 3: Rebuild Docker containers
        _update_status["progress"] = "Rebuilding containers..."
        logger.info("Rebuilding Docker containers")
        result = subprocess.run(
            compose_cmd + ["build", "--no-cache"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes for build
        )
        if result.returncode != 0:
            raise Exception(f"Docker build failed: {result.stderr}")

        # Step 4: Run database migrations
        _update_status["progress"] = "Running database migrations..."
        logger.info("Running database migrations")
        result = subprocess.run(
            compose_cmd + ["exec", "-T", "backend", "alembic", "upgrade", "head"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Migration failures are non-fatal (might already be up to date)
        if result.returncode != 0:
            logger.warning(f"Migration warning: {result.stderr}")

        # Step 5: Restart containers
        _update_status["progress"] = "Restarting services..."
        logger.info("Restarting Docker containers")
        result = subprocess.run(
            compose_cmd + ["up", "-d"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise Exception(f"Docker restart failed: {result.stderr}")

        # Success!
        _update_status["status"] = "success"
        _update_status["message"] = "Update completed successfully"
        _update_status["progress"] = None
        _update_status["target_version"] = version or _get_current_git_version()
        _update_status["timestamp"] = datetime.now()
        logger.info("Update completed successfully")

    except subprocess.TimeoutExpired:
        error_msg = "Update timed out - this may indicate a network or system issue"
        _update_status["status"] = "error"
        _update_status["message"] = "Update failed"
        _update_status["error"] = error_msg
        _update_status["timestamp"] = datetime.now()
        logger.error(error_msg)

    except Exception as e:
        error_msg = str(e)
        _update_status["status"] = "error"
        _update_status["message"] = "Update failed"
        _update_status["error"] = error_msg
        _update_status["timestamp"] = datetime.now()
        logger.error(f"Update failed: {error_msg}", exc_info=True)


@router.get("/update/status", response_model=UpdateStatus)
async def get_update_status(
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get current update status

    Returns the current status of any ongoing or completed update operation.
    """
    return UpdateStatus(**_update_status)


@router.post("/update/start")
async def start_update(
    request: UpdateRequest,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Start system update

    This endpoint triggers an update of the FilaOps system:
    1. Pulls latest code from git (or specific version)
    2. Rebuilds Docker containers
    3. Runs database migrations
    4. Restarts services

    **Security:** Admin-only endpoint. Requires admin authentication.

    **Note:** This is a long-running operation. Check status via /update/status.
    """
    global _update_status

    # Check if update is already in progress
    if _update_status["status"] in ["checking", "updating"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Update already in progress")

    # Check prerequisites
    if not _check_docker_available():
        is_container = _is_running_in_container()
        if is_container:
            detail = (
                "Docker is not available inside the container. "
                "To enable one-click updates, you need to:\n"
                "1. Mount the Docker socket: Add '-v /var/run/docker.sock:/var/run/docker.sock' to your docker-compose.yml backend service\n"
                "2. Install Docker CLI in the container (add to Dockerfile)\n"
                "3. Mount the project directory as a volume\n\n"
                "Alternatively, run updates manually from the host using the commands in UPGRADE.md"
            )
        else:
            detail = "Docker is not available. Please install Docker and docker-compose to use this feature."

        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    if not _check_git_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Git is not available. Cannot pull updates."
        )

    # Check if docker-compose.yml exists (production only)
    # Note: We only update production deployments, not dev environments
    docker_compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not docker_compose_file.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="docker-compose.yml not found. This endpoint requires a production Docker deployment.",
        )

    # Initialize update status
    _update_status["status"] = "checking"
    _update_status["message"] = "Preparing update..."
    _update_status["current_version"] = _get_current_git_version()
    _update_status["target_version"] = request.version
    _update_status["progress"] = None
    _update_status["error"] = None
    _update_status["timestamp"] = datetime.now()

    # Start update in background
    background_tasks.add_task(_run_update, request.version)

    logger.info(f"Update started by admin {current_admin.email} (version: {request.version or 'latest'})")

    return {
        "message": "Update started",
        "status": "checking",
        "current_version": _update_status["current_version"],
        "target_version": request.version,
    }


@router.get("/version")
async def get_system_version(
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get current system version

    Returns the current git version/tag of the system.
    """
    version = _get_current_git_version()
    return {
        "version": version,
        "package_version": "1.1.0",  # From package.json or settings
    }
