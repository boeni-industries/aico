"""
Logs API Module

Public logging endpoints for frontend log submissions.
Separate from admin logging endpoints which are for log management.
"""

from .router import router

__all__ = ["router"]
