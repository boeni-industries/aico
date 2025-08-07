"""
AICO Data Layer

This package provides data storage and management capabilities for AICO,
including database connections, encryption, and schema management.

The data layer is designed to be:
- Local-first: All data stored locally by default
- Privacy-first: Encryption at rest for all sensitive data
- Modular: Support for multiple database backends
- Cross-platform: Works across Windows, macOS, and Linux
"""

__version__ = "0.1.0"

# Re-export main components for convenience
from .libsql import (
    LibSQLConnection, 
    EncryptedLibSQLConnection,
    create_encrypted_database,
    SchemaManager,
    SchemaVersion,
    SchemaRegistry,
    register_schema
)

__all__ = [
    "LibSQLConnection",
    "EncryptedLibSQLConnection",
    "create_encrypted_database",
    "SchemaManager",
    "SchemaVersion",
    "SchemaRegistry",
    "register_schema",
]
