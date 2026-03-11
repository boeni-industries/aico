"""
AICO Business Logic Services

Service layer containing business logic separated from API endpoints.
"""

# Services will be imported as they are created
# from .user_service import UserBusinessService
# from .admin_service import AdminBusinessService
# from .auth_service import AuthBusinessService
from .modelservice_client import ModelServiceClient, get_modelservice_client

__all__ = ["ModelServiceClient", "get_modelservice_client"]
