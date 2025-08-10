"""
Schema Registry for AICO's automated schema discovery and management.

This module provides a decorator-based system for registering database schemas
that are automatically discovered and applied during application startup and
plugin lifecycle management.
"""

from typing import Dict, List, Optional, Any, Type, Union
from dataclasses import dataclass
from pathlib import Path

from .schema import SchemaManager, SchemaVersion
from .connection import LibSQLConnection
from .encrypted import EncryptedLibSQLConnection

# Lazy logger initialization to avoid circular imports
_logger = None

def _get_logger():
    global _logger
    if _logger is None:
        try:
            from aico.core.logging import get_logger, initialize_logging
            from aico.core.config import ConfigurationManager
            
            # Try to initialize logging if not already done
            try:
                _logger = get_logger("data", "libsql.registry")
            except RuntimeError:
                # Logging not initialized, initialize it
                config = ConfigurationManager()
                initialize_logging(config)
                _logger = get_logger("data", "libsql.registry")
        except Exception:
            # Fallback to standard logging if unified system fails
            import logging
            _logger = logging.getLogger("data.libsql.registry")
    return _logger


@dataclass
class RegisteredSchema:
    """Represents a registered schema with metadata."""
    name: str
    schema_type: str  # "core" or "plugin"
    definitions: Dict[int, SchemaVersion]
    priority: int = 0  # For ordering core schemas


class SchemaRegistry:
    """
    Global registry for database schemas with automatic discovery and application.
    
    Provides decorator-based registration and automatic schema management
    for core modules and plugins.
    """
    
    _schemas: Dict[str, RegisteredSchema] = {}
    _initialized: bool = False
    
    @classmethod
    def register(
        cls, 
        name: str, 
        schema_type: str = "core", 
        priority: int = 0
    ):
        """
        Decorator to register a schema for automatic discovery.
        
        Args:
            name: Unique schema name (e.g., "conversations", "calendar")
            schema_type: Either "core" or "plugin"
            priority: Priority for core schemas (lower = applied first)
            
        Returns:
            Decorator function
            
        Example:
            @SchemaRegistry.register("conversations", "core", priority=1)
            CONVERSATION_SCHEMA = {
                1: SchemaVersion(...)
            }
        """
        def decorator(schema_definitions: Dict[int, SchemaVersion]):
            if name in cls._schemas:
                _get_logger().warning(f"Schema '{name}' already registered, overriding")
            
            cls._schemas[name] = RegisteredSchema(
                name=name,
                schema_type=schema_type,
                definitions=schema_definitions,
                priority=priority
            )
            
            _get_logger().debug(f"Registered {schema_type} schema: {name}")
            return schema_definitions
        
        return decorator
    
    @classmethod
    def get_core_schemas(cls) -> List[RegisteredSchema]:
        """Get all core schemas ordered by priority."""
        core_schemas = [
            schema for schema in cls._schemas.values() 
            if schema.schema_type == "core"
        ]
        return sorted(core_schemas, key=lambda s: s.priority)
    
    @classmethod
    def get_plugin_schemas(cls) -> List[RegisteredSchema]:
        """Get all plugin schemas."""
        return [
            schema for schema in cls._schemas.values() 
            if schema.schema_type == "plugin"
        ]
    
    @classmethod
    def get_schema(cls, name: str) -> Optional[RegisteredSchema]:
        """Get a specific schema by name."""
        return cls._schemas.get(name)
    
    @classmethod
    def list_schemas(cls) -> Dict[str, str]:
        """List all registered schemas with their types."""
        return {
            name: schema.schema_type 
            for name, schema in cls._schemas.items()
        }
    
    @classmethod
    def apply_core_schemas(
        cls, 
        connection: Union[LibSQLConnection, EncryptedLibSQLConnection]
    ) -> Dict[str, int]:
        """
        Apply all core schemas in priority order.
        
        Args:
            connection: Database connection
            
        Returns:
            Dictionary mapping schema names to applied versions
        """
        applied_versions = {}
        core_schemas = cls.get_core_schemas()
        
        _get_logger().info(f"Applying {len(core_schemas)} core schemas")
        
        for schema in core_schemas:
            try:
                manager = SchemaManager(connection, schema.definitions)
                manager.migrate_to_latest()
                
                version = manager.get_current_version()
                applied_versions[schema.name] = version
                
                _get_logger().info(f"Applied core schema '{schema.name}' at version {version}")
                
            except Exception as e:
                _get_logger().error(f"Failed to apply core schema '{schema.name}': {e}")
                raise
        
        cls._initialized = True
        return applied_versions
    
    @classmethod
    def apply_plugin_schema(
        cls,
        plugin_name: str,
        connection: Union[LibSQLConnection, EncryptedLibSQLConnection]
    ) -> int:
        """
        Apply a specific plugin schema.
        
        Args:
            plugin_name: Name of the plugin schema
            connection: Database connection
            
        Returns:
            Applied schema version
            
        Raises:
            ValueError: If plugin schema not found
        """
        schema = cls.get_schema(plugin_name)
        if not schema:
            raise ValueError(f"Plugin schema '{plugin_name}' not registered")
        
        if schema.schema_type != "plugin":
            raise ValueError(f"Schema '{plugin_name}' is not a plugin schema")
        
        try:
            manager = SchemaManager(connection, schema.definitions)
            manager.migrate_to_latest()
            
            version = manager.get_current_version()
            _get_logger().info(f"Applied plugin schema '{plugin_name}' at version {version}")
            
            return version
            
        except Exception as e:
            _get_logger().error(f"Failed to apply plugin schema '{plugin_name}': {e}")
            raise
    
    @classmethod
    def remove_plugin_schema(
        cls,
        plugin_name: str,
        connection: Union[LibSQLConnection, EncryptedLibSQLConnection]
    ) -> bool:
        """
        Remove a plugin schema (rollback to version 0).
        
        Args:
            plugin_name: Name of the plugin schema
            connection: Database connection
            
        Returns:
            True if successfully removed, False if schema not found
        """
        schema = cls.get_schema(plugin_name)
        if not schema:
            _get_logger().warning(f"Plugin schema '{plugin_name}' not registered")
            return False
        
        if schema.schema_type != "plugin":
            _get_logger().warning(f"Schema '{plugin_name}' is not a plugin schema")
            return False
        
        try:
            manager = SchemaManager(connection, schema.definitions)
            manager.rollback_to_version(0)
            
            _get_logger().info(f"Removed plugin schema '{plugin_name}'")
            return True
            
        except Exception as e:
            _get_logger().error(f"Failed to remove plugin schema '{plugin_name}': {e}")
            raise
    
    @classmethod
    def get_schema_info(
        cls,
        connection: Union[LibSQLConnection, EncryptedLibSQLConnection]
    ) -> Dict[str, Dict]:
        """
        Get information about all applied schemas.
        
        Args:
            connection: Database connection
            
        Returns:
            Dictionary with schema information
        """
        info = {
            "core_schemas": {},
            "plugin_schemas": {},
            "registry_stats": {
                "total_registered": len(cls._schemas),
                "core_count": len(cls.get_core_schemas()),
                "plugin_count": len(cls.get_plugin_schemas()),
                "initialized": cls._initialized
            }
        }
        
        # Get info for each registered schema
        for name, schema in cls._schemas.items():
            try:
                manager = SchemaManager(connection, schema.definitions)
                schema_info = manager.get_schema_info()
                
                if schema.schema_type == "core":
                    info["core_schemas"][name] = schema_info
                else:
                    info["plugin_schemas"][name] = schema_info
                    
            except Exception as e:
                _get_logger().warning(f"Could not get info for schema '{name}': {e}")
        
        return info
    
    @classmethod
    def clear_registry(cls):
        """Clear all registered schemas (for testing)."""
        cls._schemas.clear()
        cls._initialized = False
        _get_logger().debug("Schema registry cleared")


# Convenience function for registration
def register_schema(name: str, schema_type: str = "core", priority: int = 0):
    """
    Convenience function for schema registration.
    
    Args:
        name: Unique schema name
        schema_type: Either "core" or "plugin"  
        priority: Priority for core schemas (lower = applied first)
        
    Returns:
        Decorator function
    """
    return SchemaRegistry.register(name, schema_type, priority)
