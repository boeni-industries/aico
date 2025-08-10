"""
Core AICO Database Schemas

Defines the foundational database schemas for AICO's core functionality.
All schemas use the decorator-based registration system for automatic discovery.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class SchemaVersion:
    """Represents a single version of a database schema"""
    version: int
    name: str
    description: str
    sql_statements: List[str]
    rollback_statements: List[str] = None


# Schema registry (will be populated by decorators)
_SCHEMA_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_schema(schema_name: str, schema_type: str, priority: int = 10):
    """Decorator for registering database schemas"""
    def decorator(schema_dict):
        _SCHEMA_REGISTRY[schema_name] = {
            "schema": schema_dict,
            "type": schema_type,
            "priority": priority
        }
        return schema_dict
    return decorator


# Register logs schema
LOGS_SCHEMA = register_schema("logs", "core", priority=0)({
    1: SchemaVersion(
        version=1,
        name="Unified Logging System",
        description="Single source of truth for all subsystem logs",
        sql_statements=[
            """CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                subsystem TEXT NOT NULL,
                module TEXT NOT NULL,
                function_name TEXT,
                file_path TEXT,
                line_number INTEGER,
                topic TEXT NOT NULL,
                message TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                trace_id TEXT,
                extra TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)",
            "CREATE INDEX IF NOT EXISTS idx_logs_subsystem ON logs(subsystem)",
            "CREATE INDEX IF NOT EXISTS idx_logs_module ON logs(module)",
            "CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id)",
            "CREATE INDEX IF NOT EXISTS idx_logs_session_id ON logs(session_id)"
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_logs_session_id",
            "DROP INDEX IF EXISTS idx_logs_trace_id",
            "DROP INDEX IF EXISTS idx_logs_module",
            "DROP INDEX IF EXISTS idx_logs_subsystem",
            "DROP INDEX IF EXISTS idx_logs_level",
            "DROP INDEX IF EXISTS idx_logs_timestamp",
            "DROP TABLE IF EXISTS logs"
        ]
    )
})


class SchemaRegistry:
    """Manages schema registration and application"""
    
    @classmethod
    def get_core_schemas(cls) -> Dict[str, Dict]:
        """Get all registered core schemas sorted by priority"""
        core_schemas = {
            name: data for name, data in _SCHEMA_REGISTRY.items() 
            if data["type"] == "core"
        }
        return dict(sorted(core_schemas.items(), key=lambda x: x[1]["priority"]))
    
    @classmethod
    def get_plugin_schemas(cls, plugin_name: str = None) -> Dict[str, Dict]:
        """Get plugin schemas, optionally filtered by plugin name"""
        plugin_schemas = {
            name: data for name, data in _SCHEMA_REGISTRY.items() 
            if data["type"] == "plugin"
        }
        if plugin_name:
            plugin_schemas = {
                name: data for name, data in plugin_schemas.items()
                if name.startswith(plugin_name)
            }
        return plugin_schemas
    
    @classmethod
    def apply_core_schemas(cls, connection):
        """Apply all core schemas in priority order"""
        applied_versions = []
        core_schemas = cls.get_core_schemas()
        
        for schema_name, schema_data in core_schemas.items():
            schema_dict = schema_data["schema"]
            # Apply latest version (for now, just version 1)
            latest_version = max(schema_dict.keys())
            schema_version = schema_dict[latest_version]
            
            # Execute SQL statements
            for sql in schema_version.sql_statements:
                connection.execute(sql)
            
            applied_versions.append(f"{schema_name}:v{latest_version}")
        
        return applied_versions
