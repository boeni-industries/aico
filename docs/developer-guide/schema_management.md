---
title: Schema Management Developer Guide
---

# Schema Management Developer Guide

This guide provides developers with practical instructions for implementing database schemas using AICO's decorator-based schema registry system.

## Quick Start

### Basic Schema Registration

```python
# 1. Register your schema with a decorator
from aico.data import register_schema, SchemaVersion

@register_schema("my_module", "core", priority=5)
MY_MODULE_SCHEMA = {
    1: SchemaVersion(
        version=1,
        name="My Module Schema",
        description="Core tables for my module functionality",
        sql_statements=[
            """
            CREATE TABLE my_module_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                data_field TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX idx_my_module_user_id ON my_module_data(user_id)"
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_my_module_user_id",
            "DROP TABLE IF EXISTS my_module_data"
        ]
    )
}

# 2. Schema is automatically applied during startup - no manual intervention needed!
# Just import the module containing the decorated schema
```

## Schema Registration Patterns

### Core Module Schema

Core AICO modules register schemas with priority ordering:

```python
# aico/core/conversations/schema.py
from aico.data import register_schema, SchemaVersion

@register_schema("conversations", "core", priority=1)
CONVERSATION_SCHEMA = {
    1: SchemaVersion(
        version=1,
        name="Conversation System",
        description="Core conversation storage and retrieval",
        sql_statements=[
            """
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                is_ai_response BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context_id TEXT,
                metadata JSON
            )
            """,
            """
            CREATE TABLE conversation_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                thread_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX idx_conversations_user_id ON conversations(user_id)",
            "CREATE INDEX idx_conversations_timestamp ON conversations(timestamp)",
            "CREATE INDEX idx_conversations_context ON conversations(context_id)",
            "CREATE INDEX idx_threads_user_id ON conversation_threads(user_id)"
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_threads_user_id",
            "DROP INDEX IF EXISTS idx_conversations_context",
            "DROP INDEX IF EXISTS idx_conversations_timestamp",
            "DROP INDEX IF EXISTS idx_conversations_user_id",
            "DROP TABLE IF EXISTS conversation_threads",
            "DROP TABLE IF EXISTS conversations"
        ]
    ),
    
    2: SchemaVersion(
        version=2,
        name="Add Conversation Analytics",
        description="Add analytics and metrics tracking",
        sql_statements=[
            """
            CREATE TABLE conversation_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                response_time_ms INTEGER,
                user_satisfaction INTEGER CHECK(user_satisfaction BETWEEN 1 AND 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
            """,
            "CREATE INDEX idx_metrics_conversation_id ON conversation_metrics(conversation_id)"
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_metrics_conversation_id",
            "DROP TABLE IF EXISTS conversation_metrics"
        ]
    )
}
```

### Plugin Schema Pattern

Plugins register schemas that are automatically managed during plugin lifecycle:

```python
# aico/plugins/calendar/schema.py
from aico.data import register_schema, SchemaVersion

@register_schema("calendar", "plugin")
CALENDAR_SCHEMA = {
    1: SchemaVersion(
        version=1,
        name="Calendar Plugin",
        description="Calendar events and scheduling",
        sql_statements=[
            "CREATE TABLE calendar_events (...)",
            "CREATE TABLE calendar_reminders (...)",
            "CREATE INDEX idx_calendar_events_user_id ON calendar_events(user_id)"
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_calendar_events_user_id",
            "DROP TABLE IF EXISTS calendar_reminders",
            "DROP TABLE IF EXISTS calendar_events"
        ]
    )
}

# No manual activation/deactivation code needed!
# Plugin system automatically handles schema application
```

## Schema Evolution

### Adding New Versions

When evolving your schema, always add new versions incrementally:

```python
# Original schema
MY_SCHEMA = {
    1: SchemaVersion(
        version=1,
        name="Initial Schema",
        sql_statements=["CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"],
        rollback_statements=["DROP TABLE IF EXISTS users"]
    )
}

# Evolution - add new version, don't modify existing ones
MY_SCHEMA = {
    1: SchemaVersion(
        version=1,
        name="Initial Schema",
        sql_statements=["CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"],
        rollback_statements=["DROP TABLE IF EXISTS users"]
    ),
    
    2: SchemaVersion(  # New version
        version=2,
        name="Add User Email",
        description="Add email field to users table",
        sql_statements=[
            "ALTER TABLE users ADD COLUMN email TEXT",
            "CREATE INDEX idx_users_email ON users(email)"
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_users_email",
            # Note: SQLite doesn't support DROP COLUMN
            # Consider table recreation for complex rollbacks
        ]
    )
}
```

### Complex Schema Changes

For complex changes that require data migration:

```python
COMPLEX_SCHEMA = {
    3: SchemaVersion(
        version=3,
        name="Restructure User Data",
        description="Split user data into separate tables",
        sql_statements=[
            # Create new table
            """
            CREATE TABLE user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """,
            
            # Migrate existing data
            """
            INSERT INTO user_profiles (user_id, first_name, last_name)
            SELECT id, 
                   SUBSTR(name, 1, INSTR(name || ' ', ' ') - 1) as first_name,
                   SUBSTR(name, INSTR(name || ' ', ' ') + 1) as last_name
            FROM users 
            WHERE name IS NOT NULL
            """,
            
            # Create indexes
            "CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id)"
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_user_profiles_user_id",
            "DROP TABLE IF EXISTS user_profiles"
        ]
    )
}
```

## Automated Integration

### Application Startup

```python
# backend/main.py - Fully automated schema application
from aico.data import EncryptedLibSQLConnection, SchemaRegistry

# Import all modules with registered schemas
import aico.core.conversations.schema  # Registers conversation schema
import aico.core.users.schema         # Registers user schema  
import aico.core.memory.schema        # Registers memory schema

def initialize_database():
    connection = EncryptedLibSQLConnection(
        db_path="~/.aico/user.db",
        master_password=get_master_password()
    )
    
    # Automatically applies all registered core schemas in priority order
    applied_versions = SchemaRegistry.apply_core_schemas(connection)
    
    logger.info(f"Applied {len(applied_versions)} core schemas: {applied_versions}")
    return connection
```

### Plugin System Integration

```python
# aico/plugins/manager.py - Automated plugin schema management
from aico.data import SchemaRegistry

class PluginManager:
    def __init__(self, connection):
        self.connection = connection
        self.active_plugins = set()
    
    def activate_plugin(self, plugin_name: str):
        """Activate a plugin - schema is automatically applied"""
        # Import plugin module to register its schema
        __import__(f"aico.plugins.{plugin_name}.schema")
        
        # Automatically apply registered plugin schema
        version = SchemaRegistry.apply_plugin_schema(plugin_name, self.connection)
        
        self.active_plugins.add(plugin_name)
        logger.info(f"Plugin {plugin_name} activated at schema version {version}")
    
    def deactivate_plugin(self, plugin_name: str, remove_data: bool = False):
        """Deactivate a plugin - schema automatically removed if requested"""
        if remove_data:
            SchemaRegistry.remove_plugin_schema(plugin_name, self.connection)
            logger.info(f"Plugin {plugin_name} schema removed")
        
        self.active_plugins.discard(plugin_name)
        logger.info(f"Plugin {plugin_name} deactivated")
    
    def get_plugin_info(self, plugin_name: str) -> dict:
        """Get plugin schema information"""
        schema_info = SchemaRegistry.get_schema_info(self.connection)
        return schema_info.get("plugin_schemas", {}).get(plugin_name, {"status": "inactive"})
```

## Testing Schema Changes

### Unit Testing

```python
# tests/test_schema.py
import pytest
import tempfile
from pathlib import Path
from aico.data import EncryptedLibSQLConnection, SchemaManager

@pytest.fixture
def temp_db():
    """Create a temporary encrypted database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    connection = EncryptedLibSQLConnection(
        db_path=db_path,
        master_password="test_password"
    )
    
    yield connection
    
    # Cleanup
    connection.disconnect()
    db_path.unlink(missing_ok=True)
    db_path.with_suffix('.db.salt').unlink(missing_ok=True)

def test_schema_migration(temp_db):
    """Test basic schema migration"""
    test_schema = {
        1: SchemaVersion(
            version=1,
            name="Test Schema",
            sql_statements=["CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)"],
            rollback_statements=["DROP TABLE IF EXISTS test_table"]
        )
    }
    
    # Apply schema
    schema_manager = SchemaManager(temp_db, test_schema)
    schema_manager.migrate_to_latest()
    
    # Verify schema applied
    assert schema_manager.get_current_version() == 1
    assert temp_db.table_exists("test_table")
    
    # Test rollback
    schema_manager.rollback_to_version(0)
    assert schema_manager.get_current_version() == 0
    assert not temp_db.table_exists("test_table")

def test_schema_evolution(temp_db):
    """Test schema evolution with multiple versions"""
    evolving_schema = {
        1: SchemaVersion(
            version=1,
            name="Initial",
            sql_statements=["CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"],
            rollback_statements=["DROP TABLE IF EXISTS users"]
        ),
        2: SchemaVersion(
            version=2,
            name="Add Email",
            sql_statements=[
                "ALTER TABLE users ADD COLUMN email TEXT",
                "CREATE INDEX idx_users_email ON users(email)"
            ],
            rollback_statements=[
                "DROP INDEX IF EXISTS idx_users_email"
                # Note: Can't drop column in SQLite
            ]
        )
    }
    
    schema_manager = SchemaManager(temp_db, evolving_schema)
    
    # Apply version 1
    schema_manager.migrate_to_version(1)
    assert schema_manager.get_current_version() == 1
    
    # Apply version 2
    schema_manager.migrate_to_version(2)
    assert schema_manager.get_current_version() == 2
    
    # Verify table structure
    table_info = temp_db.get_table_info("users")
    column_names = [col['name'] for col in table_info]
    assert 'email' in column_names

@pytest.mark.asyncio
async def test_plugin_schema_isolation(temp_db):
    """Test that plugin schemas are properly isolated"""
    plugin_a_schema = {
        1: SchemaVersion(
            version=1,
            name="Plugin A Schema",
            sql_statements=["CREATE TABLE plugin_a_data (id INTEGER PRIMARY KEY, data TEXT)"],
            rollback_statements=["DROP TABLE IF EXISTS plugin_a_data"]
        )
    }
    
    plugin_b_schema = {
        1: SchemaVersion(
            version=1,
            name="Plugin B Schema", 
            sql_statements=["CREATE TABLE plugin_b_data (id INTEGER PRIMARY KEY, info TEXT)"],
            rollback_statements=["DROP TABLE IF EXISTS plugin_b_data"]
        )
    }
    
    # Apply both plugin schemas
    manager_a = SchemaManager(temp_db, plugin_a_schema)
    manager_b = SchemaManager(temp_db, plugin_b_schema)
    
    manager_a.migrate_to_latest()
    manager_b.migrate_to_latest()
    
    # Verify both tables exist
    assert temp_db.table_exists("plugin_a_data")
    assert temp_db.table_exists("plugin_b_data")
    
    # Remove plugin A schema
    manager_a.rollback_to_version(0)
    
    # Verify plugin A table removed, plugin B table remains
    assert not temp_db.table_exists("plugin_a_data")
    assert temp_db.table_exists("plugin_b_data")
```

### Integration Testing

```python
# tests/integration/test_schema_integration.py
import pytest
from aico.plugins.manager import PluginSchemaManager

@pytest.mark.asyncio
async def test_full_plugin_lifecycle(temp_db):
    """Test complete plugin activation/deactivation lifecycle"""
    plugin_manager = PluginSchemaManager(temp_db)
    
    # Activate plugin
    await plugin_manager.activate_plugin("calendar")
    
    # Verify plugin is active
    info = await plugin_manager.get_plugin_info("calendar")
    assert info["status"] == "active"
    assert info["schema_info"]["current_version"] > 0
    
    # Deactivate plugin without removing data
    await plugin_manager.deactivate_plugin("calendar", remove_data=False)
    
    # Verify plugin is inactive but tables still exist
    info = await plugin_manager.get_plugin_info("calendar")
    assert info["status"] == "inactive"
    assert temp_db.table_exists("calendar_events")
    
    # Reactivate and then deactivate with data removal
    await plugin_manager.activate_plugin("calendar")
    await plugin_manager.deactivate_plugin("calendar", remove_data=True)
    
    # Verify tables are removed
    assert not temp_db.table_exists("calendar_events")
```

## Best Practices

### Schema Design Guidelines

1. **Use Incremental Versions**: Each version should represent a single logical change
2. **Provide Complete Rollbacks**: Always include rollback statements for every change
3. **Index Strategy**: Create indexes for commonly queried columns
4. **Foreign Key Constraints**: Use foreign keys to maintain referential integrity
5. **Data Types**: Use appropriate SQLite data types (INTEGER, TEXT, REAL, BLOB)

### Security Considerations

1. **No User Data in Schema**: Schema definitions should contain structure only
2. **Validate SQL**: Validate SQL statements don't contain malicious code
3. **Plugin Isolation**: Use table prefixes to isolate plugin data
4. **Encryption Integration**: Always use encrypted connections for sensitive data

### Performance Optimization

1. **Index Planning**: Create indexes for WHERE, ORDER BY, and JOIN columns
2. **Query Optimization**: Design schema to support efficient queries
3. **Batch Operations**: Use transactions for multiple schema operations
4. **Connection Reuse**: Reuse database connections across schema operations

### Error Handling

```python
def safe_schema_migration(connection, schema_definitions):
    """Safely apply schema migration with proper error handling"""
    schema_manager = SchemaManager(connection, schema_definitions)
    
    try:
        # Backup current state
        backup_info = schema_manager.get_schema_info()
        
        # Apply migration
        schema_manager.migrate_to_latest()
        
        # Validate result
        validation = schema_manager.validate_schema()
        if not validation['valid']:
            raise SchemaValidationError(f"Schema validation failed: {validation}")
        
        logger.info("Schema migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Schema migration failed: {e}")
        
        # Attempt rollback
        try:
            if backup_info['current_version'] > 0:
                schema_manager.rollback_to_version(backup_info['current_version'])
                logger.info("Successfully rolled back to previous schema version")
        except Exception as rollback_error:
            logger.critical(f"Rollback failed: {rollback_error}")
            raise SchemaRollbackError("Migration failed and rollback unsuccessful")
        
        raise
```

## Troubleshooting

### Common Issues

1. **Migration Already Applied**: Check migration history before applying
2. **Rollback Limitations**: SQLite doesn't support DROP COLUMN - plan accordingly
3. **Foreign Key Violations**: Ensure proper order when creating/dropping tables
4. **Index Conflicts**: Use IF NOT EXISTS for index creation
5. **Transaction Deadlocks**: Keep transactions short and avoid nested transactions

### Debugging Tools

```python
def debug_schema_state(connection, schema_definitions):
    """Debug current schema state"""
    schema_manager = SchemaManager(connection, schema_definitions)
    
    print("=== Schema Debug Information ===")
    print(f"Current Version: {schema_manager.get_current_version()}")
    print(f"Available Versions: {list(schema_definitions.keys())}")
    
    # Migration history
    history = schema_manager.get_migration_history()
    print(f"Migration History: {len(history)} entries")
    for entry in history[-5:]:  # Last 5 migrations
        print(f"  - Version {entry['version']} applied at {entry['applied_at']}")
    
    # Schema validation
    validation = schema_manager.validate_schema()
    print(f"Schema Valid: {validation['valid']}")
    if not validation['valid']:
        print(f"Validation Issues: {validation}")
    
    # Table information
    tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"Tables: {[t[0] for t in tables]}")
```

This developer guide provides comprehensive coverage of AICO's schema management system, enabling developers to effectively implement and maintain database schemas in the local-first, plugin-extensible architecture.
