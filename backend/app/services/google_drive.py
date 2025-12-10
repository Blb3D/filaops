"""
Google Drive Service for file uploads

Setup Instructions:
1. Go to Google Cloud Console (console.cloud.google.com)
2. Create a new project or select existing
3. Enable the Google Drive API
4. Create a Service Account (IAM & Admin > Service Accounts)
5. Create a JSON key for the service account
6. Save the JSON file and set GDRIVE_CREDENTIALS_PATH to its path
7. Share your target Google Drive folder with the service account email
8. Set GDRIVE_FOLDER_ID to the folder ID (from the URL)
9. Set GDRIVE_ENABLED=true

Environment Variables:
- GDRIVE_ENABLED: true/false
- GDRIVE_CREDENTIALS_PATH: path to service account JSON
- GDRIVE_FOLDER_ID: Google Drive folder ID to upload to
"""
import os
from app.logging_config import get_logger
from typing import Optional, Tuple

from app.core.config import settings

logger = get_logger(__name__)

# Google Drive API imports (optional)
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False
    logger.warning("Google Drive libraries not installed. Run: pip install google-api-python-client google-auth")


class GoogleDriveService:
    """Service for uploading files to Google Drive"""

    def __init__(self):
        self.enabled = settings.GDRIVE_ENABLED and GDRIVE_AVAILABLE
        self.service = None
        self.folder_id = settings.GDRIVE_FOLDER_ID

        if self.enabled:
            self._initialize()

    def _initialize(self):
        """Initialize the Google Drive API client"""
        try:
            creds_path = settings.GDRIVE_CREDENTIALS_PATH
            if not creds_path or not os.path.exists(creds_path):
                logger.error(f"Google Drive credentials not found at: {creds_path}")
                self.enabled = False
                return

            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Google Drive service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")
            self.enabled = False

    def upload_file(
        self,
        file_path: str,
        filename: str,
        mime_type: str = "application/octet-stream",
        subfolder: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Upload a file to Google Drive

        Args:
            file_path: Local path to the file
            filename: Name to save as in Google Drive
            mime_type: MIME type of the file
            subfolder: Optional subfolder name (will create if doesn't exist)

        Returns:
            Tuple of (success, url_or_error)
        """
        if not self.enabled:
            return False, "Google Drive not configured"

        try:
            # Determine parent folder
            parent_id = self.folder_id
            if subfolder:
                parent_id = self._get_or_create_folder(subfolder, self.folder_id)

            # Upload file
            file_metadata = {
                'name': filename,
                'parents': [parent_id] if parent_id else []
            }

            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            # Make file viewable by anyone with link
            self.service.permissions().create(
                fileId=file['id'],
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()

            logger.info(f"Uploaded to Google Drive: {filename} -> {file['webViewLink']}")
            return True, file['webViewLink']

        except Exception as e:
            logger.error(f"Failed to upload to Google Drive: {e}")
            return False, str(e)

    def upload_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str = "application/octet-stream",
        subfolder: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Upload bytes directly to Google Drive

        Args:
            file_bytes: File content as bytes
            filename: Name to save as in Google Drive
            mime_type: MIME type of the file
            subfolder: Optional subfolder name

        Returns:
            Tuple of (success, url_or_error)
        """
        if not self.enabled:
            return False, "Google Drive not configured"

        try:
            import io

            # Determine parent folder
            parent_id = self.folder_id
            if subfolder:
                parent_id = self._get_or_create_folder(subfolder, self.folder_id)

            # Upload file
            file_metadata = {
                'name': filename,
                'parents': [parent_id] if parent_id else []
            }

            media = MediaIoBaseUpload(
                io.BytesIO(file_bytes),
                mimetype=mime_type,
                resumable=True
            )
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            # Make file viewable by anyone with link
            self.service.permissions().create(
                fileId=file['id'],
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()

            logger.info(f"Uploaded to Google Drive: {filename} -> {file['webViewLink']}")
            return True, file['webViewLink']

        except Exception as e:
            logger.error(f"Failed to upload to Google Drive: {e}")
            return False, str(e)

    def _get_or_create_folder(self, folder_name: str, parent_id: str) -> str:
        """Get existing folder or create new one"""
        try:
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])
            if files:
                return files[0]['id']

            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            logger.info(f"Created Google Drive folder: {folder_name}")
            return folder['id']

        except Exception as e:
            logger.error(f"Failed to get/create folder: {e}")
            return parent_id


# Singleton instance
_drive_service: Optional[GoogleDriveService] = None


def get_drive_service() -> GoogleDriveService:
    """Get the Google Drive service singleton"""
    global _drive_service
    if _drive_service is None:
        _drive_service = GoogleDriveService()
    return _drive_service
