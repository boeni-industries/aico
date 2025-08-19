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
    support for both production and test schemas. Supports both single-schema
    and multi-schema version tracking.
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
                
                # Always set initial version if no version exists
                # This ensures metadata row exists for version tracking
                current_version = self.get_current_version()
                if current_version is None:
                    # If we have schema definitions, start at 0 and let migration handle it
                    # If no schema definitions, also start at 0 (empty database)
                    self._set_metadata("schema_version", "0")
                    self._set_metadata("schema_initialized", str(datetime.now().isoformat()))
                    _get_logger().info("Initialized schema metadata tables with version 0")
                    
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
    
    def sync_to_latest_schema(self, target_schemas: Dict[int, SchemaVersion], confirm: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Sync database to match latest schema definitions, resolving conflicts intelligently.
        
        This applies the latest schema definitions to the database, handling conflicts
        like duplicate tables, missing columns, and structural inconsistencies.
        
        Args:
            target_schemas: Schema definitions to sync to
            confirm: Actually perform the sync (safety check)
            dry_run: Preview what would be synced without making changes
            
        Returns:
            Dictionary with sync operation results
        """
        result = {
            "success": False,
            "current_version": self.get_current_version(),
            "target_version": max(target_schemas.keys()) if target_schemas else 0,
            "conflicts_found": [],
            "actions": [],
            "dry_run": dry_run
        }
        
        try:
            # Detect current database state
            current_state = self.detect_current_schema_state()
            result["actions"].append(f"Analyzed current database: {len(current_state['tables'])} tables")
            
            # Analyze what migrations are actually needed based on current state
            current_version = self.get_current_version() or 0
            target_version = result["target_version"]
            
            # Check if we need to handle existing tables that conflict with migration path
            try:
                conflicts = self._analyze_migration_conflicts(current_state, target_schemas, current_version)
                if conflicts:
                    result["actions"].append(f"Found {len(conflicts)} migration conflicts:")
                    for conflict in conflicts:
                        result["actions"].append(f"  • {conflict}")
            except Exception as e:
                result["actions"].append(f"Error analyzing conflicts: {str(e)}")
                conflicts = []
            
            if dry_run:
                result["actions"].extend([
                    f"Would sync to schema version {result['target_version']}",
                    "Would apply all pending migrations sequentially", 
                    "Would preserve existing data during structural changes"
                ])
                if conflicts:
                    result["actions"].append("Would resolve migration conflicts before applying migrations")
                result["success"] = True
                return result
            
            if not confirm:
                raise Exception("Sync requires --confirm flag for safety")
            
            # Perform the sync
            with self.connection.transaction():
                # Resolve migration conflicts first
                if conflicts:
                    self._resolve_migration_conflicts(conflicts, current_state)
                
                # Apply migrations to reach target version
                target_version = result["target_version"]
                if target_version > 0:
                    # Update schema definitions and migrate
                    self.schema_definitions = target_schemas
                    success = self.migrate_to_version(target_version)
                    if not success:
                        raise Exception(f"Failed to migrate to version {target_version}")
                
                result["actions"].extend([
                    f"Synced to schema version {target_version}",
                    "Database now matches latest code definitions"
                ])
                
                result["success"] = True
                _get_logger().info(f"Schema sync completed to version {target_version}")
                
        except Exception as e:
            result["actions"].append(f"Sync failed: {str(e)}")
            _get_logger().error(f"Failed to sync schema: {e}")
        
        return result
    
    def snapshot_current_state(self, confirm: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Capture current database state as new migration baseline, reset history.
        
        This creates a clean baseline from the current database structure,
        useful for compressing complex development migration history.
        
        Args:
            confirm: Actually perform the snapshot (safety check)
            dry_run: Preview what would be snapshotted without making changes
            
        Returns:
            Dictionary with snapshot operation results
        """
        result = {
            "success": False,
            "current_version": self.get_current_version(),
            "tables_found": [],
            "migrations_cleared": 0,
            "dry_run": dry_run,
            "actions": []
        }
        
        try:
            # Detect current database state
            current_state = self.detect_current_schema_state()
            result["tables_found"] = current_state["tables"]
            result["actions"].append(f"Analyzed current database: {len(current_state['tables'])} tables")
            
            # Get current migration history
            migration_history = self.get_migration_history()
            result["migrations_cleared"] = len(migration_history)
            
            if dry_run:
                result["actions"].extend([
                    f"Would clear {len(migration_history)} migration records",
                    "Would create baseline schema from current structure",
                    "Would set schema version to 1 (new baseline)",
                    "Would preserve all existing data and tables"
                ])
                result["success"] = True
                return result
            
            if not confirm:
                result["actions"].append("Snapshot not performed - confirmation required")
                _get_logger().warning("Schema snapshot requires confirmation")
                return result
            
            # Perform the snapshot
            with self.connection.get_connection() as conn:
                # Start transaction
                conn.execute("BEGIN TRANSACTION")
                
                try:
                    # Clear migration history
                    conn.execute("DELETE FROM _aico_migration_history")
                    
                    # Set as version 1 baseline
                    conn.execute("""
                        INSERT OR REPLACE INTO _aico_schema_metadata (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """, ("schema_version", "1"))
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO _aico_schema_metadata (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """, ("schema_snapshot_at", str(datetime.now().isoformat())))
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO _aico_schema_metadata (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """, ("schema_snapshot_reason", "Development snapshot - current state as baseline"))
                    
                    # Record the baseline in migration history
                    conn.execute("""
                        INSERT INTO _aico_migration_history 
                        (version, name, description, rollback_sql, checksum)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        1,
                        "Baseline Snapshot",
                        "Current database structure captured as baseline",
                        None,
                        "snapshot"
                    ))
                    
                    # Commit transaction
                    conn.execute("COMMIT")
                    
                except Exception as e:
                    # Rollback on error
                    conn.execute("ROLLBACK")
                    raise e
                
                result["actions"].extend([
                    f"Cleared {len(migration_history)} migration records",
                    "Created baseline schema from current structure",
                    "Set schema version to 1 (new baseline)",
                    "Future migrations will apply from this snapshot"
                ])
                
                result["success"] = True
                _get_logger().info("Schema snapshot created successfully")
                
        except Exception as e:
            result["actions"].append(f"Snapshot failed: {str(e)}")
            _get_logger().error(f"Failed to create schema snapshot: {e}")
        
        return result
    
    def _analyze_migration_conflicts(self, current_state: Dict[str, Any], target_schemas: Dict[int, SchemaVersion], current_version: int) -> List[str]:
        """Analyze conflicts between current database state and planned migrations."""
        conflicts = []
        current_tables = set(current_state["tables"])
        
        # Analyze each migration step to see if it would conflict with current state
        if not target_schemas:
            return conflicts
            
        for version in range(current_version + 1, max(target_schemas.keys()) + 1):
            if version not in target_schemas:
                continue
                
            schema_version = target_schemas[version]
            for sql in schema_version.sql_statements:
                sql_upper = sql.upper().strip()
                
                # Check for CREATE TABLE conflicts
                if sql_upper.startswith("CREATE TABLE") and "IF NOT EXISTS" not in sql_upper:
                    table_name = self._extract_table_name_from_create(sql)
                    if table_name and table_name in current_tables:
                        conflicts.append(f"Migration v{version} tries to CREATE TABLE {table_name} but it already exists")
                
                # Check for ALTER TABLE RENAME conflicts
                elif "ALTER TABLE" in sql_upper and "RENAME TO" in sql_upper:
                    old_name, new_name = self._extract_rename_tables(sql)
                    if old_name and new_name:
                        if old_name not in current_tables:
                            conflicts.append(f"Migration v{version} tries to rename {old_name} to {new_name} but {old_name} doesn't exist")
                        elif new_name in current_tables:
                            conflicts.append(f"Migration v{version} tries to rename {old_name} to {new_name} but {new_name} already exists")
                
                # Check for ADD COLUMN conflicts
                elif "ALTER TABLE" in sql_upper and "ADD COLUMN" in sql_upper:
                    table_name, column_name = self._extract_add_column_info(sql)
                    if table_name and column_name and table_name in current_tables:
                        # Check if column already exists
                        if table_name in current_state.get("constraints", {}):
                            existing_columns = [col[1] for col in current_state["constraints"][table_name].get("columns", [])]
                            if column_name in existing_columns:
                                conflicts.append(f"Migration v{version} tries to add column {column_name} to {table_name} but it already exists")
                
                # Check for missing columns that migrations expect to exist
                elif "DEFAULT" in sql_upper and "user_type" in sql_upper:
                    # This is likely a CREATE TABLE with user_type column
                    table_name = self._extract_table_name_from_create(sql)
                    if table_name == "family_members" and "family_members" in current_tables:
                        # Check if family_members has user_type column
                        if table_name in current_state.get("constraints", {}):
                            existing_columns = [col[1] for col in current_state["constraints"][table_name].get("columns", [])]
                            if "user_type" not in existing_columns:
                                conflicts.append(f"Migration v{version} expects {table_name} to have user_type column but it's missing")
        
        return conflicts
    
    def _resolve_migration_conflicts(self, conflicts: List[str], current_state: Dict[str, Any]) -> None:
        """Resolve migration conflicts by adjusting database state."""
        for conflict in conflicts:
            if "already exists" in conflict and "CREATE TABLE" in conflict:
                # Extract table name and drop it if it's a legacy table
                table_name = self._extract_conflicting_table_name(conflict)
                if table_name:
                    self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
                    _get_logger().info(f"Resolved conflict: dropped existing table {table_name}")
            
            elif "doesn't exist" in conflict and "rename" in conflict:
                # Skip this migration step - table doesn't exist to rename
                _get_logger().info(f"Conflict noted: {conflict} (will be skipped)")
            
            elif "already exists" in conflict and "rename" in conflict:
                # For rename conflicts like "rename message_log to events but events already exists"
                # We need to drop the target table that's blocking the rename
                if "to events but events already exists" in conflict:
                    self.connection.execute("DROP TABLE IF EXISTS events")
                    _get_logger().info("Resolved conflict: dropped existing events table")
                elif "to users but users already exists" in conflict:
                    self.connection.execute("DROP TABLE IF EXISTS users")
                    _get_logger().info("Resolved conflict: dropped existing users table")
                else:
                    # Generic extraction for other cases
                    parts = conflict.split()
                    target_table = None
                    for i, part in enumerate(parts):
                        if part == "to" and i + 1 < len(parts):
                            target_table = parts[i + 1]
                            break
                    if target_table:
                        self.connection.execute(f"DROP TABLE IF EXISTS {target_table}")
                        _get_logger().info(f"Resolved conflict: dropped existing target table {target_table}")
            
            elif "add column" in conflict and "already exists" in conflict:
                # Column already exists, skip adding it
                _get_logger().info(f"Conflict noted: {conflict} (column add will be skipped)")
            
            elif "user_type column but it's missing" in conflict:
                # Add missing user_type column to family_members
                self.connection.execute("ALTER TABLE family_members ADD COLUMN user_type TEXT DEFAULT 'parent'")
                _get_logger().info("Resolved conflict: added missing user_type column to family_members")
    
    def _extract_table_name_from_create(self, sql: str) -> str:
        """Extract table name from CREATE TABLE statement."""
        parts = sql.split()
        for i, part in enumerate(parts):
            if part.upper() == "TABLE":
                if i + 1 < len(parts):
                    return parts[i + 1].strip("(").strip()
        return ""
    
    def _extract_rename_tables(self, sql: str) -> tuple:
        """Extract old and new table names from ALTER TABLE RENAME statement."""
        parts = sql.split()
        old_name = new_name = ""
        for i, part in enumerate(parts):
            if part.upper() == "TABLE" and i + 1 < len(parts):
                old_name = parts[i + 1]
            elif part.upper() == "TO" and i + 1 < len(parts):
                new_name = parts[i + 1]
        return old_name, new_name
    
    def _extract_add_column_info(self, sql: str) -> tuple:
        """Extract table and column name from ALTER TABLE ADD COLUMN statement."""
        parts = sql.split()
        table_name = column_name = ""
        for i, part in enumerate(parts):
            if part.upper() == "TABLE" and i + 1 < len(parts):
                table_name = parts[i + 1]
            elif part.upper() == "COLUMN" and i + 1 < len(parts):
                column_name = parts[i + 1]
        return table_name, column_name
    
    def _extract_conflicting_table_name(self, conflict: str) -> str:
        """Extract table name from conflict message."""
        parts = conflict.split()
        for i, part in enumerate(parts):
            if part == "TABLE" and i + 1 < len(parts):
                return parts[i + 1]
        return ""
    
    def detect_current_schema_state(self) -> Dict[str, Any]:
        """
        Analyze current database structure to understand existing schema.
        
        Returns:
            Dictionary with current database structure information
        """
        state = {
            "tables": [],
            "indexes": [],
            "triggers": [],
            "views": [],
            "table_schemas": {},
            "foreign_keys": {},
            "constraints": {}
        }
        
        try:
            # Get all tables
            tables = self.connection.fetch_all("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            
            for table in tables:
                table_name = table["name"]
                state["tables"].append(table_name)
                state["table_schemas"][table_name] = table["sql"]
                
                # Get table info (columns, types, constraints)
                try:
                    columns = self.connection.fetch_all(f"PRAGMA table_info({table_name})")
                    foreign_keys = self.connection.fetch_all(f"PRAGMA foreign_key_list({table_name})")
                    
                    state["constraints"][table_name] = {
                        "columns": columns,
                        "foreign_keys": foreign_keys
                    }
                except Exception as e:
                    _get_logger().warning(f"Could not get detailed info for table {table_name}: {e}")
            
            # Get indexes
            indexes = self.connection.fetch_all("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            state["indexes"] = [{"name": idx["name"], "sql": idx["sql"]} for idx in indexes]
            
            # Get triggers
            triggers = self.connection.fetch_all("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='trigger'
                ORDER BY name
            """)
            state["triggers"] = [{"name": trig["name"], "sql": trig["sql"]} for trig in triggers]
            
            # Get views
            views = self.connection.fetch_all("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='view'
                ORDER BY name
            """)
            state["views"] = [{"name": view["name"], "sql": view["sql"]} for view in views]
            
        except Exception as e:
            _get_logger().error(f"Failed to detect current schema state: {e}")
            state["error"] = str(e)
        
        return state

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

