"""
Optional Google Drive integration.
- Lazy-imports Google libs only when used.
- Controlled by env/settings ENABLE_GOOGLE_DRIVE (default False).
"""
from __future__ import annotations
import os
from typing import Optional

_ENABLE_ENV = os.getenv("ENABLE_GOOGLE_DRIVE", "false").strip().lower() in {"1","true","yes","on"}

try:
    from app.core.config import settings  # type: ignore
    ENABLE = bool(getattr(settings, "ENABLE_GOOGLE_DRIVE", _ENABLE_ENV))
except Exception:
    ENABLE = _ENABLE_ENV


class GoogleDriveUnavailable(RuntimeError):
    pass


def _require_enabled():
    if not ENABLE:
        raise GoogleDriveUnavailable("Google Drive integration disabled (ENABLE_GOOGLE_DRIVE=false).")


def _import_google():
    try:
        from googleapiclient.discovery import build  # type: ignore
        from googleapiclient.http import MediaFileUpload  # type: ignore
        from google.oauth2.credentials import Credentials  # type: ignore
        return build, MediaFileUpload, Credentials
    except Exception as e:
        raise GoogleDriveUnavailable(
            "Google client libs not installed. Install: "
            "pip install google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib"
        ) from e


def get_service(token: str):
    """Return a Drive service client. Raises if disabled or deps missing."""
    _require_enabled()
    build, _MediaFileUpload, Credentials = _import_google()
    creds = Credentials(token)
    return build("drive", "v3", credentials=creds)


def upload_file(token: str, *, file_path: str, mime_type: str, folder_id: Optional[str] = None) -> str:
    """Upload a file and return its Drive file ID."""
    _require_enabled()
    build, MediaFileUpload, Credentials = _import_google()

    creds = Credentials(token)
    service = build("drive", "v3", credentials=creds)

    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    metadata = {"name": os.path.basename(file_path)}
    if folder_id:
        metadata["parents"] = [folder_id]

    created = service.files().create(body=metadata, media_body=media, fields="id").execute()
    return created["id"]
