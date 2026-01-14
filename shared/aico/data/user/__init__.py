"""
AICO User Management

Provides core user CRUD operations and authentication functionality
that can be used by both CLI and API Gateway components.
"""

from aico.data.user.models import UserProfile
from aico.data.user.proactive_models import UserProactivePreferences
from .models import AuthenticationData
from .service import UserService

__all__ = [
    "UserProfile",
    "UserProactivePreferences",
    "AuthenticationData", 
    "UserService"
]
