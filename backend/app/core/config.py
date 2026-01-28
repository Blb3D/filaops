"""
Configuration settings for FilaOps ERP

This module provides backward compatibility with the original config.py interface.
The actual settings implementation is in settings.py using pydantic-settings.

Usage:
    from app.core.config import settings
    # or
    from app.core.settings import get_settings
    settings = get_settings()
"""

from app.core.settings import Settings, get_settings, settings

# Re-export for backward compatibility
__all__ = ["Settings", "get_settings", "settings"]
