"""
AICO User Management

Provides core user CRUD operations and authentication functionality
that can be used by both CLI and API Gateway components.
"""

from aico.data.user.models import UserProfile
from aico.data.user.proactive_models import UserProactivePreferences
from aico.data.user.feedback_models import UserFeedbackRequest
from aico.data.user.relationship_models import UserRelationship, UserSkillConfidence, UserTimePreference
from .models import AuthenticationData
from .service import UserService

__all__ = [
    "UserProfile",
    "UserProactivePreferences",
    "UserFeedbackRequest",
    "UserRelationship",
    "UserSkillConfidence",
    "UserTimePreference",
    "AuthenticationData", 
    "UserService"
]
