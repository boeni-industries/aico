"""
LibSQL Schema Management

This module provides database schema management capabilities including:
- Schema versioning and migration
- Schema validation and integrity checks
- Test schema support for development
- Automatic schema setup and upgrades

The schema manager works with both basic and encrypted LibSQL connections
and provides a clean separation between test and production schemas.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass

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
                _logger = get_logger("data", "libsql.schema")
            except RuntimeError:
                # Logging not initialized, initialize it
                config = ConfigurationManager()
                initialize_logging(config)
                _logger = get_logger("data", "libsql.schema")
        except Exception:
            # Fallback to standard logging if unified system fails
            import logging
            _logger = logging.getLogger("data.libsql.schema")
    return _logger


@dataclass
class SchemaVersion:
    """Represents a database schema version with metadata."""
    version: int
    name: str
    description: str
    sql_statements: List[str]
    rollback_statements: Optional[List[str]] = None
    created_at: Optional[datetime] = None


class SchemaManager:
    """
    Database schema management for LibSQL databases.
    
    Handles schema versioning, migrations, validation, and provides
    support for both production and test schemas.
    """
    
    # Core metadata table for tracking schema versions
    METADATA_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS _aico_schema_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    
    # Migration history table
    MIGRATION_HISTORY_SQL = """
        CREATE TABLE IF NOT EXISTS _aico_migration_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            rollback_sql TEXT,
            checksum TEXT
        )
    """
    
    def __init__(
        self, 
        connection: Union[LibSQLConnection, EncryptedLibSQLConnection],
        schema_definitions: Optional[Dict[int, SchemaVersion]] = None
    ):
        """
        Initialize schema manager.
        
        Args:
            connection: LibSQL connection (basic or encrypted)
            schema_definitions: Optional schema version definitions
        """
        self.connection = connection
        self.schema_definitions = schema_definitions or {}
        
        # Initialize metadata tables
        self._initialize_metadata_tables()
        
        _get_logger().debug(f"Initialized schema manager with {len(self.schema_definitions)} schema versions")
    
    def _initialize_metadata_tables(self) -> None:
        """Create metadata tables if they don't exist."""
        try:
            with self.connection.transaction():
                self.connection.execute(self.METADATA_TABLE_SQL)
                self.connection.execute(self.MIGRATION_HISTORY_SQL)
                
                # Set initial version if not exists
                current_version = self.get_current_version()
                if current_version is None:
                    self._set_metadata("schema_version", "0")
                    self._set_metadata("schema_initialized", str(datetime.now().isoformat()))
                    _get_logger().info("Initialized schema metadata tables")
                    
        except Exception as e:
            _get_logger().error(f"Failed to initialize metadata tables: {e}")
            raise RuntimeError(f"Schema initialization failed: {e}") from e
    
    def _set_metadata(self, key: str, value: str) -> None:
        """Set metadata key-value pair."""
        self.connection.execute("""
            INSERT OR REPLACE INTO _aico_schema_metadata (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
    
    def _get_metadata(self, key: str) -> Optional[str]:
        """Get metadata value by key."""
        result = self.connection.fetch_one(
            "SELECT value FROM _aico_schema_metadata WHERE key = ?",
            (key,)
        )
        return result['value'] if result else None
    
    def get_current_version(self) -> Optional[int]:
        """
        Get current schema version.
        
        Returns:
            Current schema version number or None if not set
        """
        version_str = self._get_metadata("schema_version")
        return int(version_str) if version_str is not None else None
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Get migration history.
        
        Returns:
            List of applied migrations with metadata
        """
        return self.connection.fetch_all("""
            SELECT version, name, description, applied_at, checksum
            FROM _aico_migration_history
            ORDER BY version ASC
        """)
    
    def add_schema_version(self, schema_version: SchemaVersion) -> None:
        """
        Add a schema version definition.
        
        Args:
            schema_version: Schema version to add
        """
        self.schema_definitions[schema_version.version] = schema_version
        _get_logger().debug(f"Added schema version {schema_version.version}: {schema_version.name}")
    
    def validate_schema(self) -> Dict[str, Any]:
        """
        Validate current database schema.
        
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "valid": True,
            "current_version": self.get_current_version(),
            "issues": [],
            "tables": [],
            "metadata_tables_exist": True
        }
        
        try:
            # Check metadata tables exist
            if not self.connection.table_exists("_aico_schema_metadata"):
                validation_result["valid"] = False
                validation_result["metadata_tables_exist"] = False
                validation_result["issues"].append("Schema metadata table missing")
            
            if not self.connection.table_exists("_aico_migration_history"):
                validation_result["valid"] = False
                validation_result["metadata_tables_exist"] = False
                validation_result["issues"].append("Migration history table missing")
            
            # Get all tables
            tables = self.connection.fetch_all("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            
            validation_result["tables"] = [table["name"] for table in tables]
            
            # Check for orphaned tables (tables not in any schema version)
            current_version = self.get_current_version()
            if current_version and current_version in self.schema_definitions:
                expected_tables = self._get_expected_tables(current_version)
                actual_tables = set(validation_result["tables"])
                expected_tables_set = set(expected_tables)
                
                orphaned = actual_tables - expected_tables_set - {"_aico_schema_metadata", "_aico_migration_history"}
                missing = expected_tables_set - actual_tables
                
                if orphaned:
                    validation_result["issues"].append(f"Orphaned tables: {list(orphaned)}")
                
                if missing:
                    validation_result["valid"] = False
                    validation_result["issues"].append(f"Missing tables: {list(missing)}")
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["issues"].append(f"Validation error: {str(e)}")
            _get_logger().error(f"Schema validation failed: {e}")
        
        return validation_result
    
    def _get_expected_tables(self, version: int) -> List[str]:
        """Extract table names from schema version SQL statements."""
        if version not in self.schema_definitions:
            return []
        
        tables = []
        schema_version = self.schema_definitions[version]
        
        for sql in schema_version.sql_statements:
            # Simple extraction of CREATE TABLE statements
            sql_upper = sql.upper().strip()
            if sql_upper.startswith("CREATE TABLE"):
                # Extract table name (basic parsing)
                parts = sql.split()
                for i, part in enumerate(parts):
                    if part.upper() == "TABLE":
                        if i + 1 < len(parts):
                            table_name = parts[i + 1].strip("(").strip()
                            tables.append(table_name)
                        break
        
        return tables
    
    def apply_schema_version(self, version: int, force: bool = False) -> bool:
        """
        Apply a specific schema version.
        
        Args:
            version: Schema version to apply
            force: Force application even if version is lower than current
            
        Returns:
            True if successful, False otherwise
        """
        if version not in self.schema_definitions:
            _get_logger().error(f"Schema version {version} not found")
            return False
        
        current_version = self.get_current_version() or 0
        
        if version <= current_version and not force:
            _get_logger().warning(f"Schema version {version} is not newer than current {current_version}")
            return False
        
        schema_version = self.schema_definitions[version]
        
        try:
            with self.connection.transaction():
                # Apply SQL statements
                for sql_statement in schema_version.sql_statements:
                    if sql_statement.strip():
                        _get_logger().debug(f"Executing: {sql_statement[:100]}...")
                        self.connection.execute(sql_statement)
                
                # Record migration
                rollback_sql = json.dumps(schema_version.rollback_statements) if schema_version.rollback_statements else None
                checksum = self._calculate_checksum(schema_version.sql_statements)
                
                self.connection.execute("""
                    INSERT INTO _aico_migration_history 
                    (version, name, description, rollback_sql, checksum)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    version,
                    schema_version.name,
                    schema_version.description,
                    rollback_sql,
                    checksum
                ))
                
                # Update current version
                self._set_metadata("schema_version", str(version))
                self._set_metadata("last_migration", str(datetime.now().isoformat()))
                
                _get_logger().info(f"Applied schema version {version}: {schema_version.name}")
                return True
                
        except Exception as e:
            _get_logger().error(f"Failed to apply schema version {version}: {e}")
            return False
    
    def migrate_to_version(self, target_version: int) -> bool:
        """
        Migrate database to target schema version.
        
        Args:
            target_version: Target schema version
            
        Returns:
            True if successful, False otherwise
        """
        current_version = self.get_current_version() or 0
        
        if target_version == current_version:
            _get_logger().info(f"Database already at version {target_version}")
            return True
        
        if target_version < current_version:
            _get_logger().error("Downgrade migrations not yet supported")
            return False
        
        # Apply migrations in sequence
        for version in range(current_version + 1, target_version + 1):
            if not self.apply_schema_version(version):
                _get_logger().error(f"Migration failed at version {version}")
                return False
        
        _get_logger().info(f"Successfully migrated from version {current_version} to {target_version}")
        return True
    
    def migrate_to_latest(self) -> bool:
        """
        Migrate database to latest schema version.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.schema_definitions:
            _get_logger().warning("No schema definitions available")
            return False
        
        latest_version = max(self.schema_definitions.keys())
        return self.migrate_to_version(latest_version)
    
    def rollback_to_version(self, target_version: int) -> bool:
        """
        Rollback database to target schema version.
        
        Args:
            target_version: Target schema version to rollback to
            
        Returns:
            True if successful, False otherwise
        """
        current_version = self.get_current_version() or 0
        
        if target_version >= current_version:
            _get_logger().error(f"Cannot rollback to version {target_version} from {current_version}")
            return False
        
        # Get migrations to rollback (in reverse order)
        migrations_to_rollback = []
        for version in range(current_version, target_version, -1):
            migration = self.connection.fetch_one("""
                SELECT rollback_sql FROM _aico_migration_history 
                WHERE version = ?
            """, (version,))
            
            if migration and migration['rollback_sql']:
                rollback_statements = json.loads(migration['rollback_sql'])
                migrations_to_rollback.append((version, rollback_statements))
            else:
                _get_logger().error(f"No rollback SQL available for version {version}")
                return False
        
        try:
            with self.connection.transaction():
                # Execute rollback statements
                for version, rollback_statements in migrations_to_rollback:
                    for sql_statement in rollback_statements:
                        if sql_statement.strip():
                            _get_logger().debug(f"Rollback executing: {sql_statement[:100]}...")
                            self.connection.execute(sql_statement)
                    
                    # Remove from migration history
                    self.connection.execute("""
                        DELETE FROM _aico_migration_history WHERE version = ?
                    """, (version,))
                
                # Update current version
                self._set_metadata("schema_version", str(target_version))
                self._set_metadata("last_rollback", str(datetime.now().isoformat()))
                
                _get_logger().info(f"Rolled back from version {current_version} to {target_version}")
                return True
                
        except Exception as e:
            _get_logger().error(f"Rollback failed: {e}")
            return False
    
    def _calculate_checksum(self, sql_statements: List[str]) -> str:
        """Calculate checksum for SQL statements."""
        import hashlib
        combined_sql = "\n".join(sql_statements)
        return hashlib.sha256(combined_sql.encode()).hexdigest()[:16]
    
    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get comprehensive schema information.
        
        Returns:
            Dictionary with schema information
        """
        return {
            "current_version": self.get_current_version(),
            "available_versions": list(self.schema_definitions.keys()),
            "migration_history": self.get_migration_history(),
            "validation": self.validate_schema(),
            "metadata": {
                "schema_initialized": self._get_metadata("schema_initialized"),
                "last_migration": self._get_metadata("last_migration"),
                "last_rollback": self._get_metadata("last_rollback")
            }
        }

