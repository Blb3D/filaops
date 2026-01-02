"""
Machine model - DEPRECATED, use Resource from manufacturing.py

This module provides backward compatibility aliases.
The 'machines' table has been consolidated into the 'resources' table.
"""

from .manufacturing import Resource
from .work_center import WorkCenter

# Machine is now an alias for Resource
Machine = Resource

__all__ = ["Machine", "WorkCenter", "Resource"]
