"""
LibSQL Database Integration for AICO

This module provides LibSQL database connectivity with encryption support.
LibSQL is a modern SQLite-compatible database that supports both local
and distributed deployments.

Key Features:
- SQLite-compatible API for easy migration
- Built-in encryption support via PRAGMA statements
- Local-first storage with optional sync capabilities
- Cross-platform compatibility
- Modern async/sync interfaces

Components:
- connection.py: Basic LibSQL connection management
- encrypted.py: Encrypted LibSQL connections with key management
- schema.py: Database schema setup and migrations
"""

from .connection import LibSQLConnection
from .encrypted import EncryptedLibSQLConnection, create_encrypted_database
from .schema import SchemaManager, SchemaVersion
from .registry import SchemaRegistry, register_schema

__all__ = [
    "LibSQLConnection", 
    "EncryptedLibSQLConnection",
    "create_encrypted_database",
    "SchemaManager",
    "SchemaVersion",
    "SchemaRegistry",
    "register_schema",
]
