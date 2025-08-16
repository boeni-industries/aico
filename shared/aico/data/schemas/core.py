"""
Core AICO Database Schemas

Defines the foundational database schemas for AICO's core functionality.
All schemas use the decorator-based registration system for automatic discovery.
"""

from ..libsql.schema import SchemaVersion
from ..libsql.registry import register_schema


# Register unified core schema
CORE_SCHEMA = register_schema("core", "core", priority=0)({
    1: SchemaVersion(
        version=1,
        name="AICO Core Database",
        description="All core tables: logging, events, authentication, and user management",
        sql_statements=[
            # Logs table - unified logging system
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
            
            # Events table - message bus persistence
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                topic TEXT NOT NULL,
                source TEXT NOT NULL,
                message_type TEXT NOT NULL,
                message_id TEXT NOT NULL UNIQUE,
                priority INTEGER DEFAULT 1,
                correlation_id TEXT,
                payload BLOB,
                metadata JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Users table - core user profiles
            """CREATE TABLE IF NOT EXISTS users (
                uuid TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                nickname TEXT,
                user_type TEXT DEFAULT 'parent',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # User authentication table - separated authentication concerns
            """CREATE TABLE IF NOT EXISTS user_authentication (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                pin_hash TEXT NOT NULL,
                failed_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            
            # Authentication sessions - JWT token management
            """CREATE TABLE IF NOT EXISTS auth_sessions (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                device_uuid TEXT NOT NULL,
                jwt_token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            
            # Access policies - authorization rules
            """CREATE TABLE IF NOT EXISTS access_policies (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_uuid TEXT,
                permission TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            
            # Devices table for device management
            """CREATE TABLE IF NOT EXISTS devices (
                uuid TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                device_type TEXT NOT NULL,
                platform TEXT NOT NULL,
                last_seen TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # User relationships junction table
            """CREATE TABLE IF NOT EXISTS user_relationships (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                related_user_uuid TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (related_user_uuid) REFERENCES users(uuid) ON DELETE CASCADE,
                UNIQUE(user_uuid, related_user_uuid, relationship_type)
            )""",
            
            # Indexes for performance
            # Logs table indexes
            "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)",
            "CREATE INDEX IF NOT EXISTS idx_logs_subsystem ON logs(subsystem)",
            "CREATE INDEX IF NOT EXISTS idx_logs_module ON logs(module)",
            "CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id)",
            "CREATE INDEX IF NOT EXISTS idx_logs_session_id ON logs(session_id)",
            
            # Events table indexes
            "CREATE INDEX IF NOT EXISTS idx_events_topic_timestamp ON events(topic, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)",
            "CREATE INDEX IF NOT EXISTS idx_events_correlation ON events(correlation_id) WHERE correlation_id IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_events_message_id ON events(message_id)",
            
            # User tables indexes
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type)",
            "CREATE INDEX IF NOT EXISTS idx_user_authentication_user ON user_authentication(user_uuid)",
            "CREATE INDEX IF NOT EXISTS idx_user_authentication_pin_hash ON user_authentication(pin_hash)",
            "CREATE INDEX IF NOT EXISTS idx_user_authentication_locked_until ON user_authentication(locked_until)",
            "CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_uuid)",
            "CREATE INDEX IF NOT EXISTS idx_auth_sessions_active ON auth_sessions(is_active, expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_access_policies_user ON access_policies(user_uuid)",
            "CREATE INDEX IF NOT EXISTS idx_access_policies_resource ON access_policies(resource_type, resource_uuid)",
            "CREATE INDEX IF NOT EXISTS idx_devices_active ON devices(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_user_relationships_user ON user_relationships(user_uuid)",
            "CREATE INDEX IF NOT EXISTS idx_user_relationships_related ON user_relationships(related_user_uuid)",
            "CREATE INDEX IF NOT EXISTS idx_logs_user_timestamp ON logs(user_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_events_message_id ON events(message_id)"
        ],
        rollback_statements=[
            # Drop indexes first (reverse order)
            "DROP INDEX IF EXISTS idx_events_message_id",
            "DROP INDEX IF EXISTS idx_events_correlation",
            "DROP INDEX IF EXISTS idx_events_source",
            "DROP INDEX IF EXISTS idx_events_topic_timestamp",
            "DROP INDEX IF EXISTS idx_logs_session_id",
            "DROP INDEX IF EXISTS idx_logs_trace_id",
            "DROP INDEX IF EXISTS idx_logs_module",
            "DROP INDEX IF EXISTS idx_logs_subsystem",
            "DROP INDEX IF EXISTS idx_logs_level",
            "DROP INDEX IF EXISTS idx_logs_timestamp",
            "DROP INDEX IF EXISTS idx_logs_user_timestamp",
            "DROP INDEX IF EXISTS idx_user_relationships_related",
            "DROP INDEX IF EXISTS idx_user_relationships_user",
            "DROP INDEX IF EXISTS idx_devices_active",
            "DROP INDEX IF EXISTS idx_access_policies_resource",
            "DROP INDEX IF EXISTS idx_access_policies_user", 
            "DROP INDEX IF EXISTS idx_auth_sessions_active",
            "DROP INDEX IF EXISTS idx_auth_sessions_user",
            "DROP INDEX IF EXISTS idx_user_authentication_locked_until",
            "DROP INDEX IF EXISTS idx_user_authentication_pin_hash",
            "DROP INDEX IF EXISTS idx_user_authentication_user",
            "DROP INDEX IF EXISTS idx_users_user_type",
            "DROP INDEX IF EXISTS idx_users_active",
            "DROP TABLE IF EXISTS user_relationships",
            "DROP TABLE IF EXISTS devices",
            "DROP TABLE IF EXISTS access_policies",
            "DROP TABLE IF EXISTS auth_sessions",
            "DROP TABLE IF EXISTS user_authentication",
            "DROP TABLE IF EXISTS users",
            "DROP TABLE IF EXISTS events",
            "DROP TABLE IF EXISTS logs"
        ]
    )
})



