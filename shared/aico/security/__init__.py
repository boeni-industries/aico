"""
AICO Security Module

This module provides security functionality for AICO including:
- Key management and derivation
- Encrypted database connections
- Transparent file encryption
- Authentication and authorization
"""

from .key_manager import AICOKeyManager
from .encrypted_file import EncryptedFile, open_encrypted
from .async_session_service import AsyncSessionService
from .device_service import DeviceService, DeviceInfo
from .exceptions import (
    SecurityError,
    EncryptionError,
    DecryptionError,
    InvalidKeyError,
    CorruptedFileError,
    InvalidFileFormatError,
    KeyDerivationError,
)
__all__ = [
    "AICOKeyManager",
    "EncryptedFile",
    "open_encrypted",
    "AsyncSessionService",
    "DeviceService",
    "DeviceInfo",
    "SecurityError",
    "EncryptionError",
    "DecryptionError",
    "InvalidKeyError",
    "CorruptedFileError",
    "InvalidFileFormatError",
    "KeyDerivationError",
]
