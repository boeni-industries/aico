"""
Custom exceptions for AICO security operations.
"""


class SecurityError(Exception):
    """Base exception for all security-related errors."""
    pass


class EncryptionError(SecurityError):
    """Raised when encryption operations fail."""
    pass


class DecryptionError(SecurityError):
    """Raised when decryption operations fail."""
    pass


class InvalidKeyError(SecurityError):
    """Raised when an invalid encryption key is provided."""
    pass


class CorruptedFileError(SecurityError):
    """Raised when an encrypted file is corrupted or tampered with."""
    pass


class InvalidFileFormatError(SecurityError):
    """Raised when a file doesn't match the expected encrypted format."""
    pass


class KeyDerivationError(SecurityError):
    """Raised when key derivation operations fail."""
    pass
