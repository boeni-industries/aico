"""
AICO User Management

Provides core user CRUD operations and authentication functionality
that can be used by both CLI and API Gateway components.
"""

from .models import UserProfile, AuthenticationData
from .service import UserService

__all__ = [
    "UserProfile",
    "AuthenticationData", 
    "UserService"
]
