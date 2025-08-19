"""
AICO Security Module

Simple, unified security functionality for master password setup and key management.
"""

from .key_manager import AICOKeyManager
from .session_service import SessionService, SessionInfo

__version__ = "0.1.0"
__all__ = ['AICOKeyManager', 'SessionService', 'SessionInfo']
