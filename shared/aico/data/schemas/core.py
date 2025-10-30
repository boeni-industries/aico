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
                user_type TEXT DEFAULT 'person',
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
            "CREATE INDEX IF NOT EXISTS idx_events_message_id ON events(message_id)",
            
        ],
        rollback_statements=[
            # Drop other indexes (reverse order)
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
    ),
    
    2: SchemaVersion(
        version=2,
        name="Logs Table User UUID Migration",
        description="Migrate logs table from user_id to user_uuid for consistency",
        sql_statements=[
            # Rename user_id column to user_uuid in logs table
            "ALTER TABLE logs RENAME COLUMN user_id TO user_uuid",
            
            # Drop old index and create new one with correct column name
            "DROP INDEX IF EXISTS idx_logs_user_timestamp",
            "CREATE INDEX IF NOT EXISTS idx_logs_user_timestamp ON logs(user_uuid, timestamp)"
        ],
        rollback_statements=[
            # Rollback: rename back to user_id
            "DROP INDEX IF EXISTS idx_logs_user_timestamp", 
            "ALTER TABLE logs RENAME COLUMN user_uuid TO user_id",
            "CREATE INDEX IF NOT EXISTS idx_logs_user_timestamp ON logs(user_id, timestamp)"
        ]
    ),
    3: SchemaVersion(
        version=3,
        name="Add session_type to auth_sessions",
        description="Add session_type TEXT column to auth_sessions table for differentiating session origin.",
        sql_statements=[
            "ALTER TABLE auth_sessions ADD COLUMN session_type TEXT DEFAULT 'unified'"
        ],
        rollback_statements=[
            # SQLite does not support DROP COLUMN directly; so for rollback, document the steps
            # 1. Create new table without session_type
            # 2. Copy data
            # 3. Drop old table
            # 4. Rename new table
            # For now, log a warning or leave as a no-op if not supported
        ]
    ),
    
    4: SchemaVersion(
        version=4,
        name="Task Scheduler Tables",
        description="Add scheduler tables for task management: scheduled_tasks, task_executions, task_locks",
        sql_statements=[
            # Task Scheduler tables
            """CREATE TABLE IF NOT EXISTS scheduled_tasks (
                task_id TEXT PRIMARY KEY,
                task_class TEXT NOT NULL,
                schedule TEXT NOT NULL,
                config TEXT,  -- JSON configuration
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            """CREATE TABLE IF NOT EXISTS task_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                result TEXT,  -- JSON TaskResult
                error_message TEXT,
                duration_seconds REAL,
                FOREIGN KEY (task_id) REFERENCES scheduled_tasks (task_id)
            )""",
            
            """CREATE TABLE IF NOT EXISTS task_locks (
                task_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (task_id) REFERENCES scheduled_tasks (task_id)
            )""",
            
            # Task Scheduler indexes
            "CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON task_executions (task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_executions_started_at ON task_executions (started_at)",
            "CREATE INDEX IF NOT EXISTS idx_task_locks_expires_at ON task_locks (expires_at)"
        ],
        rollback_statements=[
            # Drop task scheduler indexes and tables
            "DROP INDEX IF EXISTS idx_task_locks_expires_at",
            "DROP INDEX IF EXISTS idx_task_executions_started_at", 
            "DROP INDEX IF EXISTS idx_task_executions_task_id",
            "DROP TABLE IF EXISTS task_locks",
            "DROP TABLE IF EXISTS task_executions",
            "DROP TABLE IF EXISTS scheduled_tasks"
        ]
    ),
    
    5: SchemaVersion(
        version=5,
        name="Fact-Centric Memory System",
        description="Add tables for intelligent fact storage and management",
        sql_statements=[
            # Facts metadata table
            """CREATE TABLE IF NOT EXISTS facts_metadata (
                fact_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                fact_type TEXT NOT NULL,  -- identity, preference, relationship, temporal
                category TEXT NOT NULL,   -- personal_info, preferences, relationships
                confidence REAL NOT NULL,
                is_immutable BOOLEAN NOT NULL DEFAULT FALSE,
                
                -- Temporal validity
                valid_from TIMESTAMP NOT NULL,
                valid_until TIMESTAMP,
                
                -- Content and extraction
                content TEXT NOT NULL,
                entities_json TEXT,  -- JSON array of extracted entities
                extraction_method TEXT NOT NULL,
                
                -- Provenance
                source_conversation_id TEXT NOT NULL,
                source_message_id TEXT,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Foreign key
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            
            # Fact relationships table (for multi-hop reasoning)
            """CREATE TABLE IF NOT EXISTS fact_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_fact_id TEXT NOT NULL,
                target_fact_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,  -- contradicts, supports, relates_to
                confidence REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (source_fact_id) REFERENCES facts_metadata(fact_id) ON DELETE CASCADE,
                FOREIGN KEY (target_fact_id) REFERENCES facts_metadata(fact_id) ON DELETE CASCADE,
                UNIQUE(source_fact_id, target_fact_id, relationship_type)
            )""",
            
            # Session memory metadata (LMDB coordination)
            """CREATE TABLE IF NOT EXISTS session_metadata (
                session_key TEXT PRIMARY KEY,  -- user_id_conversation_id
                user_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                context_summary TEXT,
                
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            
            # Indexes for performance
            "CREATE INDEX IF NOT EXISTS idx_facts_user_type ON facts_metadata(user_id, fact_type)",
            "CREATE INDEX IF NOT EXISTS idx_facts_category ON facts_metadata(category)",
            "CREATE INDEX IF NOT EXISTS idx_facts_confidence ON facts_metadata(confidence)",
            "CREATE INDEX IF NOT EXISTS idx_facts_immutable ON facts_metadata(is_immutable)",
            "CREATE INDEX IF NOT EXISTS idx_facts_validity ON facts_metadata(valid_from, valid_until)",
            "CREATE INDEX IF NOT EXISTS idx_facts_source ON facts_metadata(source_conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_fact_relationships_source ON fact_relationships(source_fact_id)",
            "CREATE INDEX IF NOT EXISTS idx_fact_relationships_target ON fact_relationships(target_fact_id)",
            "CREATE INDEX IF NOT EXISTS idx_session_metadata_user ON session_metadata(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_session_metadata_accessed ON session_metadata(last_accessed)"
        ],
        rollback_statements=[
            # Drop indexes
            "DROP INDEX IF EXISTS idx_session_metadata_accessed",
            "DROP INDEX IF EXISTS idx_session_metadata_user", 
            "DROP INDEX IF EXISTS idx_fact_relationships_target",
            "DROP INDEX IF EXISTS idx_fact_relationships_source",
            "DROP INDEX IF EXISTS idx_facts_source",
            "DROP INDEX IF EXISTS idx_facts_validity",
            "DROP INDEX IF EXISTS idx_facts_immutable",
            "DROP INDEX IF EXISTS idx_facts_confidence",
            "DROP INDEX IF EXISTS idx_facts_category",
            "DROP INDEX IF EXISTS idx_facts_user_type",
            
            # Drop tables
            "DROP TABLE IF EXISTS session_metadata",
            "DROP TABLE IF EXISTS fact_relationships", 
            "DROP TABLE IF EXISTS facts_metadata"
        ]
    ),
    
    6: SchemaVersion(
        version=6,
        name="Feedback & Memory Album System",
        description="Add feedback_events table and extend facts_metadata for Memory Album",
        sql_statements=[
            # Create feedback_events table
            """CREATE TABLE IF NOT EXISTS feedback_events (
                id TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                message_id TEXT,
                event_type TEXT NOT NULL,
                event_category TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                is_sensitive INTEGER DEFAULT 0,
                federated_at INTEGER,
                FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            
            # Indexes for feedback_events
            "CREATE INDEX IF NOT EXISTS idx_feedback_user_time ON feedback_events(user_uuid, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_conversation ON feedback_events(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback_events(event_type, event_category)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback_events(message_id) WHERE message_id IS NOT NULL",
            
            # Extend facts_metadata for Memory Album
            "ALTER TABLE facts_metadata ADD COLUMN user_note TEXT",
            "ALTER TABLE facts_metadata ADD COLUMN tags_json TEXT",
            "ALTER TABLE facts_metadata ADD COLUMN is_favorite INTEGER DEFAULT 0",
            "ALTER TABLE facts_metadata ADD COLUMN revisit_count INTEGER DEFAULT 0",
            "ALTER TABLE facts_metadata ADD COLUMN last_revisited TIMESTAMP",
            "ALTER TABLE facts_metadata ADD COLUMN emotional_tone TEXT",
            "ALTER TABLE facts_metadata ADD COLUMN memory_type TEXT",
            
            # Indexes for Memory Album queries
            "CREATE INDEX IF NOT EXISTS idx_facts_user_curated ON facts_metadata(user_id, extraction_method) WHERE extraction_method = 'user_curated'",
            "CREATE INDEX IF NOT EXISTS idx_facts_favorite ON facts_metadata(user_id, is_favorite) WHERE is_favorite = 1",
        ],
        rollback_statements=[
            # Drop indexes
            "DROP INDEX IF EXISTS idx_facts_favorite",
            "DROP INDEX IF EXISTS idx_facts_user_curated",
            "DROP INDEX IF EXISTS idx_feedback_message",
            "DROP INDEX IF EXISTS idx_feedback_type",
            "DROP INDEX IF EXISTS idx_feedback_conversation",
            "DROP INDEX IF EXISTS idx_feedback_user_time",
            
            # Drop table
            "DROP TABLE IF EXISTS feedback_events",
            
            # Note: SQLite doesn't support DROP COLUMN
            # Columns added to facts_metadata will remain
        ]
    ),
    
    7: SchemaVersion(
        version=7,
        name="Conversation-Level Memory Support",
        description="Extend facts_metadata to support full conversation memories",
        sql_statements=[
            # Add conversation-level memory fields
            "ALTER TABLE facts_metadata ADD COLUMN content_type TEXT DEFAULT 'message'",
            "ALTER TABLE facts_metadata ADD COLUMN conversation_title TEXT",
            "ALTER TABLE facts_metadata ADD COLUMN conversation_summary TEXT",
            "ALTER TABLE facts_metadata ADD COLUMN turn_range TEXT",
            "ALTER TABLE facts_metadata ADD COLUMN key_moments_json TEXT",
            
            # Index for content type filtering
            "CREATE INDEX IF NOT EXISTS idx_facts_content_type ON facts_metadata(user_id, content_type) WHERE extraction_method = 'user_curated'",
        ],
        rollback_statements=[
            # Drop index
            "DROP INDEX IF EXISTS idx_facts_content_type",
            
            # Note: SQLite doesn't support DROP COLUMN
            # Columns added to facts_metadata will remain
        ]
    ),
    
    8: SchemaVersion(
        version=8,
        name="Property Graph Preparation - Cleanup Unused Tables",
        description="Remove unused tables in preparation for property graph implementation. Keep facts_metadata for migration.",
        sql_statements=[
            # Drop unused fact_relationships table (never implemented)
            "DROP INDEX IF EXISTS idx_fact_relationships_target",
            "DROP INDEX IF EXISTS idx_fact_relationships_source",
            "DROP TABLE IF EXISTS fact_relationships",
            
            # Drop unused session_metadata table (LMDB coordination never implemented)
            "DROP INDEX IF EXISTS idx_session_metadata_accessed",
            "DROP INDEX IF EXISTS idx_session_metadata_user",
            "DROP TABLE IF EXISTS session_metadata",
        ],
        rollback_statements=[
            # Recreate session_metadata table
            """CREATE TABLE IF NOT EXISTS session_metadata (
                session_key TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                context_summary TEXT,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_session_metadata_user ON session_metadata(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_session_metadata_accessed ON session_metadata(last_accessed)",
            
            # Recreate fact_relationships table
            """CREATE TABLE IF NOT EXISTS fact_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_fact_id TEXT NOT NULL,
                target_fact_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_fact_id) REFERENCES facts_metadata(fact_id) ON DELETE CASCADE,
                FOREIGN KEY (target_fact_id) REFERENCES facts_metadata(fact_id) ON DELETE CASCADE,
                UNIQUE(source_fact_id, target_fact_id, relationship_type)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_fact_relationships_source ON fact_relationships(source_fact_id)",
            "CREATE INDEX IF NOT EXISTS idx_fact_relationships_target ON fact_relationships(target_fact_id)",
        ]
    )
})



