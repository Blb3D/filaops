"""
Facade over optional Google Drive integration.

Exports:
- get_drive_service(token: str) -> service client
- upload_file(token: str, file_path: str, mime_type: str, folder_id: Optional[str]) -> str
"""

from __future__ import annotations
from typing import Optional

from app.integrations import google_drive


def get_drive_service(token: str):
    return google_drive.get_service(token)


def upload_file(token: str, *, file_path: str, mime_type: str, folder_id: Optional[str] = None) -> str:
    return google_drive.upload_file(token, file_path=file_path, mime_type=mime_type, folder_id=folder_id)
