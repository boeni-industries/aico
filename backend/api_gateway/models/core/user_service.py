"""
DEPRECATED: User Service for AICO API Gateway

This file is deprecated. User management functionality has been moved to:
- Core logic: shared/aico/data/user/service.py
- Data models: shared/aico/data/user/models.py

This allows the same user management logic to be used by both CLI and API Gateway.
"""

# Re-export from shared location for backward compatibility
from aico.data.user import UserService, UserProfile, AuthenticationData

__all__ = ["UserService", "UserProfile", "AuthenticationData"]
