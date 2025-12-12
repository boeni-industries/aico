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
                primary_language TEXT,  -- ISO/BCP-47 language code
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
                language TEXT,        -- Optional language tag for content (ISO/BCP-47)
                entities_json TEXT,   -- JSON array of extracted entities
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
    ),
    
    9: SchemaVersion(
        version=9,
        name="Property Graph Foundation",
        description="Add knowledge graph tables for structured entity and relationship storage with automatic property indexing",
        sql_statements=[
            # Nodes table - entities with typed properties
            """CREATE TABLE IF NOT EXISTS kg_nodes (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                label TEXT NOT NULL,
                properties JSON NOT NULL,
                confidence REAL NOT NULL,
                source_text TEXT NOT NULL,
                language TEXT,            -- Optional language of source_text / label
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            
            # Edges table - relationships with typed properties
            """CREATE TABLE IF NOT EXISTS kg_edges (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                properties JSON NOT NULL,
                confidence REAL NOT NULL,
                source_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (source_id) REFERENCES kg_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES kg_nodes(id) ON DELETE CASCADE
            )""",
            
            # Node property index - denormalized for fast property queries
            """CREATE TABLE IF NOT EXISTS kg_node_properties (
                node_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (node_id, key, value),
                FOREIGN KEY (node_id) REFERENCES kg_nodes(id) ON DELETE CASCADE
            )""",
            
            # Edge property index - denormalized for fast property queries
            """CREATE TABLE IF NOT EXISTS kg_edge_properties (
                edge_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (edge_id, key, value),
                FOREIGN KEY (edge_id) REFERENCES kg_edges(id) ON DELETE CASCADE
            )""",
            
            # Indexes for performance
            "CREATE INDEX IF NOT EXISTS idx_kg_nodes_user_label ON kg_nodes(user_id, label)",
            "CREATE INDEX IF NOT EXISTS idx_kg_nodes_user_created ON kg_nodes(user_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON kg_edges(source_id)",
            "CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON kg_edges(target_id)",
            "CREATE INDEX IF NOT EXISTS idx_kg_edges_user_relation ON kg_edges(user_id, relation_type)",
            "CREATE INDEX IF NOT EXISTS idx_kg_node_properties_kv ON kg_node_properties(key, value)",
            "CREATE INDEX IF NOT EXISTS idx_kg_edge_properties_kv ON kg_edge_properties(key, value)",
            
            # Triggers for automatic property index synchronization
            # Node property sync - INSERT
            """CREATE TRIGGER IF NOT EXISTS sync_node_properties_insert
            AFTER INSERT ON kg_nodes
            FOR EACH ROW
            BEGIN
                INSERT INTO kg_node_properties (node_id, key, value)
                SELECT NEW.id, key, value FROM json_each(NEW.properties);
            END""",
            
            # Node property sync - UPDATE
            """CREATE TRIGGER IF NOT EXISTS sync_node_properties_update
            AFTER UPDATE OF properties ON kg_nodes
            FOR EACH ROW
            BEGIN
                DELETE FROM kg_node_properties WHERE node_id = NEW.id;
                INSERT INTO kg_node_properties (node_id, key, value)
                SELECT NEW.id, key, value FROM json_each(NEW.properties);
            END""",
            
            # Node property sync - DELETE
            """CREATE TRIGGER IF NOT EXISTS sync_node_properties_delete
            AFTER DELETE ON kg_nodes
            FOR EACH ROW
            BEGIN
                DELETE FROM kg_node_properties WHERE node_id = OLD.id;
            END""",
            
            # Edge property sync - INSERT
            """CREATE TRIGGER IF NOT EXISTS sync_edge_properties_insert
            AFTER INSERT ON kg_edges
            FOR EACH ROW
            BEGIN
                INSERT INTO kg_edge_properties (edge_id, key, value)
                SELECT NEW.id, key, value FROM json_each(NEW.properties);
            END""",
            
            # Edge property sync - UPDATE
            """CREATE TRIGGER IF NOT EXISTS sync_edge_properties_update
            AFTER UPDATE OF properties ON kg_edges
            FOR EACH ROW
            BEGIN
                DELETE FROM kg_edge_properties WHERE edge_id = NEW.id;
                INSERT INTO kg_edge_properties (edge_id, key, value)
                SELECT NEW.id, key, value FROM json_each(NEW.properties);
            END""",
            
            # Edge property sync - DELETE
            """CREATE TRIGGER IF NOT EXISTS sync_edge_properties_delete
            AFTER DELETE ON kg_edges
            FOR EACH ROW
            BEGIN
                DELETE FROM kg_edge_properties WHERE edge_id = OLD.id;
            END""",
        ],
        rollback_statements=[
            # Drop triggers
            "DROP TRIGGER IF EXISTS sync_edge_properties_delete",
            "DROP TRIGGER IF EXISTS sync_edge_properties_update",
            "DROP TRIGGER IF EXISTS sync_edge_properties_insert",
            "DROP TRIGGER IF EXISTS sync_node_properties_delete",
            "DROP TRIGGER IF EXISTS sync_node_properties_update",
            "DROP TRIGGER IF EXISTS sync_node_properties_insert",
            
            # Drop indexes
            "DROP INDEX IF EXISTS idx_kg_edge_properties_kv",
            "DROP INDEX IF EXISTS idx_kg_node_properties_kv",
            "DROP INDEX IF EXISTS idx_kg_edges_user_relation",
            "DROP INDEX IF EXISTS idx_kg_edges_target",
            "DROP INDEX IF EXISTS idx_kg_edges_source",
            "DROP INDEX IF EXISTS idx_kg_nodes_user_created",
            "DROP INDEX IF EXISTS idx_kg_nodes_user_label",
            
            # Drop tables
            "DROP TABLE IF EXISTS kg_edge_properties",
            "DROP TABLE IF EXISTS kg_node_properties",
            "DROP TABLE IF EXISTS kg_edges",
            "DROP TABLE IF EXISTS kg_nodes",
        ]
    ),
    
    10: SchemaVersion(
        version=10,
        name="Knowledge Graph Phase 1.5 - Temporal Model & Personal Graph Support",
        description="Add bi-temporal tracking, entity disambiguation, and indexes for personal graph and temporal reasoning",
        sql_statements=[
            # Temporal fields for nodes - track when facts are valid (event time) vs recorded (ingestion time)
            "ALTER TABLE kg_nodes ADD COLUMN valid_from TEXT",
            "ALTER TABLE kg_nodes ADD COLUMN valid_until TEXT",
            "ALTER TABLE kg_nodes ADD COLUMN is_current INTEGER DEFAULT 1",
            
            # Temporal fields for edges
            "ALTER TABLE kg_edges ADD COLUMN valid_from TEXT",
            "ALTER TABLE kg_edges ADD COLUMN valid_until TEXT", 
            "ALTER TABLE kg_edges ADD COLUMN is_current INTEGER DEFAULT 1",
            
            # Entity disambiguation fields for nodes
            "ALTER TABLE kg_nodes ADD COLUMN canonical_id TEXT",
            "ALTER TABLE kg_nodes ADD COLUMN aliases_json TEXT",
            
            # Temporal indexes for point-in-time queries and current fact filtering
            "CREATE INDEX IF NOT EXISTS idx_kg_nodes_temporal ON kg_nodes(user_id, is_current, valid_from)",
            "CREATE INDEX IF NOT EXISTS idx_kg_edges_temporal ON kg_edges(user_id, is_current, valid_from)",
            
            # Canonical ID index for entity disambiguation
            "CREATE INDEX IF NOT EXISTS idx_kg_nodes_canonical ON kg_nodes(canonical_id)",
            
            # Label-specific indexes for personal graph queries
            # These enable fast queries like "Get all user's active projects" or "Find all goals"
            "CREATE INDEX IF NOT EXISTS idx_kg_nodes_label_user ON kg_nodes(user_id, label, is_current)",
            
            # Relation type index for personal graph traversal
            # Enables fast queries like "Find all WORKING_ON relationships" or "Get task dependencies"
            "CREATE INDEX IF NOT EXISTS idx_kg_edges_relation_user ON kg_edges(user_id, relation_type, is_current)",
        ],
        rollback_statements=[
            # Drop indexes
            "DROP INDEX IF EXISTS idx_kg_edges_relation_user",
            "DROP INDEX IF EXISTS idx_kg_nodes_label_user",
            "DROP INDEX IF EXISTS idx_kg_nodes_canonical",
            "DROP INDEX IF EXISTS idx_kg_edges_temporal",
            "DROP INDEX IF EXISTS idx_kg_nodes_temporal",
            
            # Note: SQLite doesn't support DROP COLUMN
            # Columns added to kg_nodes and kg_edges will remain after rollback
            # This is acceptable as they will be NULL and unused
        ]
    ),
    
    11: SchemaVersion(
        version=11,
        name="Rename facts_metadata to user_memories",
        description="Rename facts_metadata table to user_memories for clarity (Memory Album feature)",
        sql_statements=[
            # Rename table
            "ALTER TABLE facts_metadata RENAME TO user_memories",
            
            # Rename indexes to match new table name
            "DROP INDEX IF EXISTS idx_facts_user_type",
            "DROP INDEX IF EXISTS idx_facts_category",
            "DROP INDEX IF EXISTS idx_facts_confidence",
            "DROP INDEX IF EXISTS idx_facts_immutable",
            "DROP INDEX IF EXISTS idx_facts_validity",
            "DROP INDEX IF EXISTS idx_facts_source",
            "DROP INDEX IF EXISTS idx_facts_user_curated",
            "DROP INDEX IF EXISTS idx_facts_favorite",
            "DROP INDEX IF EXISTS idx_facts_content_type",
            
            "CREATE INDEX IF NOT EXISTS idx_user_memories_user_type ON user_memories(user_id, fact_type)",
            "CREATE INDEX IF NOT EXISTS idx_user_memories_category ON user_memories(category)",
            "CREATE INDEX IF NOT EXISTS idx_user_memories_confidence ON user_memories(confidence)",
            "CREATE INDEX IF NOT EXISTS idx_user_memories_immutable ON user_memories(is_immutable)",
            "CREATE INDEX IF NOT EXISTS idx_user_memories_validity ON user_memories(valid_from, valid_until)",
            "CREATE INDEX IF NOT EXISTS idx_user_memories_source ON user_memories(source_conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_memories_user_curated ON user_memories(user_id, extraction_method) WHERE extraction_method = 'user_curated'",
            "CREATE INDEX IF NOT EXISTS idx_user_memories_favorite ON user_memories(user_id, is_favorite) WHERE is_favorite = 1",
            "CREATE INDEX IF NOT EXISTS idx_user_memories_content_type ON user_memories(user_id, content_type) WHERE extraction_method = 'user_curated'",
        ],
        rollback_statements=[
            # Rename back
            "ALTER TABLE user_memories RENAME TO facts_metadata",
            
            # Restore original index names
            "DROP INDEX IF EXISTS idx_user_memories_user_type",
            "DROP INDEX IF EXISTS idx_user_memories_category",
            "DROP INDEX IF EXISTS idx_user_memories_confidence",
            "DROP INDEX IF EXISTS idx_user_memories_immutable",
            "DROP INDEX IF EXISTS idx_user_memories_validity",
            "DROP INDEX IF EXISTS idx_user_memories_source",
            "DROP INDEX IF EXISTS idx_user_memories_user_curated",
            "DROP INDEX IF EXISTS idx_user_memories_favorite",
            "DROP INDEX IF EXISTS idx_user_memories_content_type",
            
            "CREATE INDEX IF NOT EXISTS idx_facts_user_type ON facts_metadata(user_id, fact_type)",
            "CREATE INDEX IF NOT EXISTS idx_facts_category ON facts_metadata(category)",
            "CREATE INDEX IF NOT EXISTS idx_facts_confidence ON facts_metadata(confidence)",
            "CREATE INDEX IF NOT EXISTS idx_facts_immutable ON facts_metadata(is_immutable)",
            "CREATE INDEX IF NOT EXISTS idx_facts_validity ON facts_metadata(valid_from, valid_until)",
            "CREATE INDEX IF NOT EXISTS idx_facts_source ON facts_metadata(source_conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_facts_user_curated ON facts_metadata(user_id, extraction_method) WHERE extraction_method = 'user_curated'",
            "CREATE INDEX IF NOT EXISTS idx_facts_favorite ON facts_metadata(user_id, is_favorite) WHERE is_favorite = 1",
            "CREATE INDEX IF NOT EXISTS idx_facts_content_type ON facts_metadata(user_id, content_type) WHERE extraction_method = 'user_curated'",
        ]
    ),
    
    12: SchemaVersion(
        version=12,
        name="AMS Phase 1 - Temporal Metadata Support",
        description="Add temporal metadata column to user_memories for Adaptive Memory System temporal intelligence",
        sql_statements=[
            # Add temporal_metadata column to user_memories (formerly facts_metadata)
            # Stores TemporalMetadata as JSON for flexibility
            "ALTER TABLE user_memories ADD COLUMN temporal_metadata TEXT DEFAULT NULL",
            
            # Add indexes for temporal queries
            "CREATE INDEX IF NOT EXISTS idx_user_memories_temporal ON user_memories(json_extract(temporal_metadata, '$.last_accessed'), json_extract(temporal_metadata, '$.confidence'))",
            "CREATE INDEX IF NOT EXISTS idx_user_memories_superseded ON user_memories(json_extract(temporal_metadata, '$.superseded_by'))",
        ],
        rollback_statements=[
            # Drop indexes
            "DROP INDEX IF EXISTS idx_user_memories_superseded",
            "DROP INDEX IF EXISTS idx_user_memories_temporal",
            
            # Note: SQLite doesn't support DROP COLUMN
            # temporal_metadata column will remain after rollback but will be NULL and unused
        ]
    ),
    
    13: SchemaVersion(
        version=13,
        name="AMS Phase 1 - Consolidation State Tracking",
        description="Add consolidation_state table for tracking memory consolidation progress",
        sql_statements=[
            """CREATE TABLE IF NOT EXISTS consolidation_state (
                user_id TEXT NOT NULL,
                last_consolidation_at TIMESTAMP,
                messages_consolidated INTEGER DEFAULT 0,
                memories_created INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id),
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_consolidation_status ON consolidation_state(status)",
            "CREATE INDEX IF NOT EXISTS idx_consolidation_last_run ON consolidation_state(last_consolidation_at)"
        ],
        rollback_statements=[
            # Drop index and table
            "DROP INDEX IF EXISTS idx_consolidation_status",
            "DROP INDEX IF EXISTS idx_consolidation_last_run",
            "DROP TABLE IF EXISTS consolidation_state",
        ]
    ),
    
    14: SchemaVersion(
        version=14,
        name="AMS Phase 3 - Behavioral Learning System",
        description="Add tables for skill-based interaction learning with RLHF and Thompson Sampling",
        sql_statements=[
            # Skills table - user-agnostic templates
            """CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                skill_type TEXT NOT NULL CHECK(skill_type IN ('base', 'user_created')),
                trigger_context TEXT NOT NULL,
                procedure_template TEXT NOT NULL,
                dimension_vector TEXT NOT NULL,
                supported_languages TEXT,  -- JSON array of supported language codes
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_skills_type ON skills(skill_type)",
            
            # User-skill confidence mapping
            """CREATE TABLE IF NOT EXISTS user_skill_confidence (
                user_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.5 CHECK(confidence_score BETWEEN 0.0 AND 1.0),
                usage_count INTEGER DEFAULT 0,
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                last_used_at TIMESTAMP,
                PRIMARY KEY (user_id, skill_id),
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_user_skill_confidence ON user_skill_confidence(user_id, confidence_score DESC)",
            
            # Feedback events table
            """CREATE TABLE IF NOT EXISTS feedback_events (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                skill_id TEXT,
                reward INTEGER NOT NULL CHECK(reward IN (-1, 0, 1)),
                reason TEXT,
                free_text TEXT,
                classified_categories TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback_events(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_skill ON feedback_events(skill_id)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_processed ON feedback_events(processed)",
            
            # Trajectories table with retention policy
            """CREATE TABLE IF NOT EXISTS trajectories (
                trajectory_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                user_input TEXT NOT NULL,
                selected_skill_id TEXT,
                ai_response TEXT NOT NULL,
                feedback_reward INTEGER CHECK(feedback_reward IN (-1, 0, 1)),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                archived BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (selected_skill_id) REFERENCES skills(skill_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_trajectories_user_feedback ON trajectories(user_id, feedback_reward)",
            "CREATE INDEX IF NOT EXISTS idx_trajectories_timestamp ON trajectories(timestamp)",
            
            # Thompson Sampling context-skill statistics
            """CREATE TABLE IF NOT EXISTS context_skill_stats (
                user_id TEXT NOT NULL,
                context_bucket INTEGER NOT NULL CHECK(context_bucket BETWEEN 0 AND 99),
                skill_id TEXT NOT NULL,
                alpha REAL DEFAULT 1.0 CHECK(alpha >= 0.0),
                beta REAL DEFAULT 1.0 CHECK(beta >= 0.0),
                last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, context_bucket, skill_id),
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_context_stats_user_context ON context_skill_stats(user_id, context_bucket)",
            
            # Context-aware preference vectors (16 explicit dimensions)
            """CREATE TABLE IF NOT EXISTS context_preference_vectors (
                user_id TEXT NOT NULL,
                context_bucket INTEGER NOT NULL CHECK(context_bucket BETWEEN 0 AND 99),
                dimensions TEXT NOT NULL,
                last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, context_bucket),
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_preference_vectors_user ON context_preference_vectors(user_id)"
        ],
        rollback_statements=[
            # Drop indexes
            "DROP INDEX IF EXISTS idx_skills_type",
            "DROP INDEX IF EXISTS idx_user_skill_confidence",
            "DROP INDEX IF EXISTS idx_feedback_user",
            "DROP INDEX IF EXISTS idx_feedback_skill",
            "DROP INDEX IF EXISTS idx_feedback_processed",
            "DROP INDEX IF EXISTS idx_trajectories_user_feedback",
            "DROP INDEX IF EXISTS idx_trajectories_timestamp",
            "DROP INDEX IF EXISTS idx_context_stats_user_context",
            "DROP INDEX IF EXISTS idx_preference_vectors_user",
            
            # Drop tables
            "DROP TABLE IF EXISTS context_preference_vectors",
            "DROP TABLE IF EXISTS context_skill_stats",
            "DROP TABLE IF EXISTS trajectories",
            "DROP TABLE IF EXISTS feedback_events",
            "DROP TABLE IF EXISTS user_skill_confidence",
            "DROP TABLE IF EXISTS skills",
        ]
    ),
    
    15: SchemaVersion(
        version=15,
        name="AMS Phase 3 - Skill Tracking",
        description="Add message_id to trajectories table for linking feedback to skills",
        sql_statements=[
            # Add message_id column to trajectories
            "ALTER TABLE trajectories ADD COLUMN message_id TEXT",
            
            # Create index for message_id lookups
            "CREATE INDEX IF NOT EXISTS idx_trajectories_message ON trajectories(message_id)",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_trajectories_message",
            # Note: SQLite doesn't support DROP COLUMN, so we can't easily rollback
            # In production, would need to recreate table without message_id
        ]
    ),
    
    16: SchemaVersion(
        version=16,
        name="Reconcile Feedback Events Schema Conflict",
        description="Rename AMS feedback_events to ams_feedback_events and restore Memory Album feedback_events table",
        sql_statements=[
            # Rename AMS feedback_events table to avoid conflict
            "ALTER TABLE feedback_events RENAME TO ams_feedback_events",
            
            # Recreate Memory Album feedback_events table (v6 schema)
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
            
            # Recreate Memory Album indexes
            "CREATE INDEX IF NOT EXISTS idx_feedback_user_time ON feedback_events(user_uuid, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_conversation ON feedback_events(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback_events(event_type, event_category)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback_events(message_id) WHERE message_id IS NOT NULL",
        ],
        rollback_statements=[
            # Drop Memory Album feedback_events
            "DROP INDEX IF EXISTS idx_feedback_message",
            "DROP INDEX IF EXISTS idx_feedback_type",
            "DROP INDEX IF EXISTS idx_feedback_conversation",
            "DROP INDEX IF EXISTS idx_feedback_user_time",
            "DROP TABLE IF EXISTS feedback_events",
            
            # Restore AMS feedback_events
            "ALTER TABLE ams_feedback_events RENAME TO feedback_events",
        ]
    ),
    
    17: SchemaVersion(
        version=17,
        name="Emotion Simulation State Persistence",
        description="Add tables for persisting AICO's emotional state and history across restarts",
        sql_statements=[
            # Emotion state table - current emotional state
            """CREATE TABLE IF NOT EXISTS emotion_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                user_id TEXT NOT NULL DEFAULT 'system',
                timestamp TEXT NOT NULL,
                subjective_feeling TEXT NOT NULL,
                mood_valence REAL NOT NULL,
                mood_arousal REAL NOT NULL,
                intensity REAL NOT NULL,
                warmth REAL NOT NULL,
                directness REAL NOT NULL,
                formality REAL NOT NULL,
                engagement REAL NOT NULL,
                closeness REAL NOT NULL,
                care_focus REAL NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Emotion history table - mood arc over time
            """CREATE TABLE IF NOT EXISTS emotion_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'system',
                timestamp TEXT NOT NULL,
                feeling TEXT NOT NULL,
                valence REAL NOT NULL,
                arousal REAL NOT NULL,
                intensity REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Indexes for efficient queries
            "CREATE INDEX IF NOT EXISTS idx_emotion_history_user_time ON emotion_history(user_id, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_emotion_history_feeling ON emotion_history(feeling)",
            
            # Insert default neutral state
            """INSERT OR IGNORE INTO emotion_state (id, user_id, timestamp, subjective_feeling, 
                mood_valence, mood_arousal, intensity, warmth, directness, formality, 
                engagement, closeness, care_focus)
            VALUES (1, 'system', datetime('now'), 'neutral', 0.0, 0.5, 0.5, 0.6, 0.5, 0.3, 0.6, 0.5, 0.7)""",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_emotion_history_feeling",
            "DROP INDEX IF EXISTS idx_emotion_history_user_time",
            "DROP TABLE IF EXISTS emotion_history",
            "DROP TABLE IF EXISTS emotion_state",
        ]
    ),
    
    18: SchemaVersion(
        version=18,
        name="Fix Schema v16 Mistake - Correct AMS Behavioral Feedback Table",
        description="Fix v16 error: Rename misnamed ams_feedback_events, create proper ams_behavioral_feedback table",
        sql_statements=[
            # Rename the incorrectly named table from v16
            "ALTER TABLE ams_feedback_events RENAME TO temp_memory_album_feedback",
            
            # Create the CORRECT AMS Behavioral Learning feedback table
            """CREATE TABLE IF NOT EXISTS ams_behavioral_feedback (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                skill_id TEXT,
                reward INTEGER NOT NULL CHECK (reward IN (-1, 0, 1)),
                reason TEXT,
                free_text TEXT,
                timestamp TEXT NOT NULL,
                processed INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_ams_behavioral_feedback_user ON ams_behavioral_feedback(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_ams_behavioral_feedback_skill ON ams_behavioral_feedback(skill_id)",
            "CREATE INDEX IF NOT EXISTS idx_ams_behavioral_feedback_processed ON ams_behavioral_feedback(processed)",
            
            # Note: DROP temp table removed - causes lock issues, will be cleaned in v19
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_ams_behavioral_feedback_processed",
            "DROP INDEX IF EXISTS idx_ams_behavioral_feedback_skill",
            "DROP INDEX IF EXISTS idx_ams_behavioral_feedback_user",
            "DROP TABLE IF EXISTS ams_behavioral_feedback",
            "ALTER TABLE temp_memory_album_feedback RENAME TO ams_feedback_events",
        ]
    )
    ,
    19: SchemaVersion(
        version=19,
        name="Historical Placeholder - Pre-agency schema",
        description="Placeholder for existing dev schema state prior to agency tables. No-op for fresh installs.",
        sql_statements=[],
        rollback_statements=[]
    ),

    20: SchemaVersion(
        version=20,
        name="Agency Phase 0 - Goals & Telemetry Prereqs",
        description="Add foundational tables for agency goals, plans, events, and self-reflection notes.",
        sql_statements=[
            # Core goals table - generic across future agency phases
            """CREATE TABLE IF NOT EXISTS agency_goals (
                goal_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                origin TEXT NOT NULL,              -- user, curiosity, hobby, maintenance, system
                goal_type TEXT NOT NULL,          -- high-level type label (e.g. project, habit, maintenance)
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, active, paused, completed, retired
                priority TEXT DEFAULT 'normal',          -- low, normal, high
                metadata_json TEXT,                      -- JSON blob for future extensions
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_agency_goals_user_status ON agency_goals(user_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_agency_goals_origin ON agency_goals(origin)",

            # Plans table - per-goal plan skeleton with JSON steps
            """CREATE TABLE IF NOT EXISTS agency_plans (
                plan_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',    -- draft, active, completed, abandoned
                steps_json TEXT NOT NULL,                -- JSON array of steps for early phases
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_agency_plans_goal_status ON agency_plans(goal_id, status)",

            # Agency events / logs - telemetry for agency decisions and actions
            """CREATE TABLE IF NOT EXISTS agency_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                goal_id TEXT,
                plan_id TEXT,
                event_type TEXT NOT NULL,              -- decision, plan_update, trigger, error, metric
                source TEXT NOT NULL,                  -- which component emitted this event (engine, planner, arbiter, etc.)
                payload_json TEXT NOT NULL,            -- JSON payload with structured details
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL,
                FOREIGN KEY (plan_id) REFERENCES agency_plans(plan_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_agency_events_user_time ON agency_events(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_agency_events_goal ON agency_events(goal_id)",
            "CREATE INDEX IF NOT EXISTS idx_agency_events_type ON agency_events(event_type)",

            # Self-reflection and lessons learned - for later phases but safe to log against now
            """CREATE TABLE IF NOT EXISTS agency_reflection_notes (
                note_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                related_goal_id TEXT,
                related_plan_id TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (related_goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL,
                FOREIGN KEY (related_plan_id) REFERENCES agency_plans(plan_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_agency_reflection_user_time ON agency_reflection_notes(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_agency_reflection_goal ON agency_reflection_notes(related_goal_id)",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_agency_reflection_goal",
            "DROP INDEX IF EXISTS idx_agency_reflection_user_time",
            "DROP TABLE IF EXISTS agency_reflection_notes",
            "DROP INDEX IF EXISTS idx_agency_events_type",
            "DROP INDEX IF EXISTS idx_agency_events_goal",
            "DROP INDEX IF EXISTS idx_agency_events_user_time",
            "DROP TABLE IF EXISTS agency_events",
            "DROP INDEX IF EXISTS idx_agency_plans_goal_status",
            "DROP TABLE IF EXISTS agency_plans",
            "DROP INDEX IF EXISTS idx_agency_goals_origin",
            "DROP INDEX IF EXISTS idx_agency_goals_user_status",
            "DROP TABLE IF EXISTS agency_goals",
        ]
    ),
    
    # Phase 4: Values & Ethics, Goal Arbiter, and Intention Set
    21: SchemaVersion(
        version=21,
        name="Agency Phase 4 - Values & Ethics and Goal Arbiter",
        description="Add tables for values/ethics policies, goal arbiter scoring, and active intention set tracking.",
        sql_statements=[
            # Value profiles - per-user value preferences and boundaries
            """CREATE TABLE IF NOT EXISTS value_profiles (
                profile_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                sensitive_life_areas TEXT,         -- JSON array of LifeArea IDs
                allowed_curiosity_domains TEXT,    -- JSON array of allowed domains
                curiosity_intensity REAL DEFAULT 0.5,  -- 0.0-1.0 scale
                proactive_behavior_level TEXT DEFAULT 'balanced',  -- quiet, balanced, proactive
                storage_preferences TEXT,          -- JSON object with storage rules
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_value_profiles_user ON value_profiles(user_id)",
            
            # Policy rules - structured ethics/safety rules
            """CREATE TABLE IF NOT EXISTS policy_rules (
                rule_id TEXT PRIMARY KEY,
                rule_name TEXT NOT NULL,
                target_type TEXT NOT NULL,         -- goal, plan, skill, curiosity_signal, world_model_update
                conditions_json TEXT NOT NULL,     -- JSON object with predicates
                effect TEXT NOT NULL,              -- allow, allow_with_warning, needs_consent, block
                user_message_template TEXT,        -- Optional NL explanation
                priority INTEGER DEFAULT 100,      -- Lower = higher priority
                enabled BOOLEAN DEFAULT 1,
                scope TEXT DEFAULT 'global',       -- global, deployment, user
                scope_id TEXT,                     -- NULL for global, user_id for user-specific
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_policy_rules_target ON policy_rules(target_type, enabled)",
            "CREATE INDEX IF NOT EXISTS idx_policy_rules_scope ON policy_rules(scope, scope_id)",
            
            # Consents - explicit user consent records
            """CREATE TABLE IF NOT EXISTS consents (
                consent_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                consent_scope TEXT NOT NULL,       -- JSON object describing what was consented to
                decision TEXT NOT NULL,            -- granted, denied
                context_json TEXT,                 -- Optional context (goal_id, plan_id, etc.)
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,              -- NULL = permanent
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_consents_user_scope ON consents(user_id, consent_scope)",
            "CREATE INDEX IF NOT EXISTS idx_consents_expires ON consents(expires_at)",
            
            # Intention set - active goals being pursued by arbiter
            """CREATE TABLE IF NOT EXISTS intention_set (
                intention_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'proposed',  -- proposed, active, paused, dropped, completed
                arbiter_score REAL NOT NULL,       -- Computed score from arbiter
                priority_band TEXT NOT NULL,       -- urgent, normal, background
                reasons_json TEXT,                 -- JSON array of reason codes/explanations
                activated_at TIMESTAMP,
                deactivated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_intention_set_user_status ON intention_set(user_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_intention_set_goal ON intention_set(goal_id)",
            "CREATE INDEX IF NOT EXISTS idx_intention_set_priority ON intention_set(priority_band, status)",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_intention_set_priority",
            "DROP INDEX IF EXISTS idx_intention_set_goal",
            "DROP INDEX IF EXISTS idx_intention_set_user_status",
            "DROP TABLE IF EXISTS intention_set",
            "DROP INDEX IF EXISTS idx_consents_expires",
            "DROP INDEX IF EXISTS idx_consents_user_scope",
            "DROP TABLE IF EXISTS consents",
            "DROP INDEX IF EXISTS idx_policy_rules_scope",
            "DROP INDEX IF EXISTS idx_policy_rules_target",
            "DROP TABLE IF EXISTS policy_rules",
            "DROP INDEX IF EXISTS idx_value_profiles_user",
            "DROP TABLE IF EXISTS value_profiles",
        ]
    ),
    
    # Fix skills table column order
    22: SchemaVersion(
        version=22,
        name="Fix skills table column order",
        description="Recreate skills table with correct column order (supported_languages before timestamps)",
        run_outside_transaction=True,  # Must run outside transaction to drop tables with foreign keys
        sql_statements=[
            # Disable foreign key checks temporarily
            "PRAGMA foreign_keys = OFF",
            
            # Drop dependent tables (in correct order to avoid FK violations)
            "DROP TABLE IF EXISTS context_skill_stats",
            "DROP TABLE IF EXISTS trajectories", 
            "DROP TABLE IF EXISTS feedback_events",
            "DROP TABLE IF EXISTS user_skill_confidence",
            "DROP TABLE IF EXISTS ams_behavioral_feedback",
            
            # Drop and recreate skills table with correct column order
            "DROP TABLE IF EXISTS skills",
            """CREATE TABLE skills (
                skill_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                skill_type TEXT NOT NULL CHECK(skill_type IN ('base', 'user_created')),
                trigger_context TEXT NOT NULL,
                procedure_template TEXT NOT NULL,
                dimension_vector TEXT NOT NULL,
                supported_languages TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX idx_skills_type ON skills(skill_type)",
            
            # Recreate dependent tables
            """CREATE TABLE user_skill_confidence (
                user_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.5 CHECK(confidence_score BETWEEN 0.0 AND 1.0),
                usage_count INTEGER DEFAULT 0,
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                last_used_at TIMESTAMP,
                PRIMARY KEY (user_id, skill_id),
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX idx_user_skill_confidence ON user_skill_confidence(user_id, confidence_score DESC)",
            
            """CREATE TABLE feedback_events (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                skill_id TEXT,
                reward INTEGER NOT NULL CHECK(reward IN (-1, 0, 1)),
                reason TEXT,
                free_text TEXT,
                classified_categories TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX idx_feedback_user ON feedback_events(user_id)",
            "CREATE INDEX idx_feedback_skill ON feedback_events(skill_id)",
            "CREATE INDEX idx_feedback_processed ON feedback_events(processed, timestamp)",
            
            """CREATE TABLE trajectories (
                trajectory_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                selected_skill_id TEXT,
                context_bucket TEXT NOT NULL,
                feedback_reward INTEGER CHECK(feedback_reward IN (-1, 0, 1)),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                archived BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (selected_skill_id) REFERENCES skills(skill_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX idx_trajectories_user_feedback ON trajectories(user_id, feedback_reward)",
            "CREATE INDEX idx_trajectories_timestamp ON trajectories(timestamp)",
            
            """CREATE TABLE context_skill_stats (
                user_id TEXT NOT NULL,
                context_bucket TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                alpha REAL DEFAULT 1.0,
                beta REAL DEFAULT 1.0,
                last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, context_bucket, skill_id),
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX idx_context_stats_user_context ON context_skill_stats(user_id, context_bucket)",
            
            """CREATE TABLE IF NOT EXISTS ams_behavioral_feedback (
                feedback_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                skill_id TEXT,
                reward INTEGER NOT NULL CHECK(reward IN (-1, 0, 1)),
                reason TEXT,
                timestamp TEXT NOT NULL,
                processed INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_ams_behavioral_feedback_user ON ams_behavioral_feedback(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_ams_behavioral_feedback_skill ON ams_behavioral_feedback(skill_id)",
            "CREATE INDEX IF NOT EXISTS idx_ams_behavioral_feedback_processed ON ams_behavioral_feedback(processed, timestamp)",
            
            # Re-enable foreign key checks
            "PRAGMA foreign_keys = ON",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_skills_type",
            "DROP TABLE IF EXISTS context_skill_stats",
            "DROP TABLE IF EXISTS trajectories",
            "DROP TABLE IF EXISTS feedback_events",
            "DROP TABLE IF EXISTS user_skill_confidence",
            "DROP TABLE IF EXISTS ams_behavioral_feedback",
            "DROP TABLE IF EXISTS skills",
        ]
    ),
    
    # Add agency_context to trajectories
    23: SchemaVersion(
        version=23,
        name="Add agency context to trajectories",
        description="Add agency_context column to trajectories table for storing agency decisions (intentions, ethics evaluations, etc.)",
        sql_statements=[
            # Add agency_context column to trajectories
            "ALTER TABLE trajectories ADD COLUMN agency_context TEXT",
            
            # Create index for agency context queries
            "CREATE INDEX IF NOT EXISTS idx_trajectories_agency ON trajectories(user_id, agency_context) WHERE agency_context IS NOT NULL",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_trajectories_agency",
            # Note: SQLite doesn't support DROP COLUMN easily
            # In production, would need to recreate table without agency_context
        ]
    ),
    
    # Phase 5: Self-Reflection & Behavioral Learning
    24: SchemaVersion(
        version=24,
        name="Agency Phase 5 - Self-Reflection Lessons",
        description="Add agency_lessons table for structured self-reflection and behavioral learning (Phase 5)",
        sql_statements=[
            """CREATE TABLE IF NOT EXISTS agency_lessons (
                lesson_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                
                -- Lesson classification
                lesson_type TEXT NOT NULL,  -- skill_tuning, planner_heuristic, curiosity_focus, persona_style, policy_suggestion
                target_kind TEXT NOT NULL,  -- skill, planner_template, arbiter_weight, curiosity_policy, persona_trait, policy_rule
                target_id TEXT,             -- ID of the target entity (skill_id, policy_rule_id, etc.)
                
                -- Human-readable summary
                summary_text TEXT NOT NULL,
                
                -- Structured change proposal (JSON)
                proposed_change TEXT NOT NULL,  -- JSON: {change_type, field, old, new, notes}
                
                -- Evidence and confidence
                confidence REAL NOT NULL,       -- 0.0 to 1.0
                metrics_basis TEXT,             -- JSON: {time_span, sample_size, outcome_counts, etc.}
                
                -- Scope and status
                scope TEXT NOT NULL,            -- this_user, global_default
                status TEXT NOT NULL,           -- active, superseded, rejected
                superseded_by TEXT,             -- lesson_id that replaced this one
                
                -- Application tracking
                applied_at TIMESTAMP,           -- When the lesson was applied
                applied_by TEXT,                -- Component that applied it (e.g., "self_reflection_engine")
                
                -- Provenance (what led to this lesson)
                source_reflection_run_id TEXT, -- ID of the reflection job that created this
                evidence_window_start TIMESTAMP,
                evidence_window_end TIMESTAMP,
                
                -- Links to related entities
                related_goal_ids TEXT,         -- JSON array of goal_ids
                related_trajectory_ids TEXT,   -- JSON array of trajectory_ids
                related_event_ids TEXT,        -- JSON array of agency_event_ids
                
                -- Audit trail
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Foreign keys
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (superseded_by) REFERENCES agency_lessons(lesson_id) ON DELETE SET NULL
            )""",
            
            # Indexes for efficient querying
            "CREATE INDEX IF NOT EXISTS idx_agency_lessons_user_type ON agency_lessons(user_id, lesson_type)",
            "CREATE INDEX IF NOT EXISTS idx_agency_lessons_target ON agency_lessons(target_kind, target_id)",
            "CREATE INDEX IF NOT EXISTS idx_agency_lessons_status ON agency_lessons(user_id, status) WHERE status = 'active'",
            "CREATE INDEX IF NOT EXISTS idx_agency_lessons_applied ON agency_lessons(applied_at) WHERE applied_at IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_agency_lessons_superseded ON agency_lessons(superseded_by)",
            "CREATE INDEX IF NOT EXISTS idx_agency_lessons_time ON agency_lessons(user_id, created_at DESC)",
            
            # Self-model performance tracking table
            """CREATE TABLE IF NOT EXISTS agency_self_model (
                model_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                
                -- What this tracks
                entity_type TEXT NOT NULL,     -- skill, goal_type, interaction_pattern
                entity_id TEXT NOT NULL,       -- Specific skill_id, goal type name, etc.
                
                -- Performance metrics (JSON)
                performance_summary TEXT NOT NULL,  -- JSON: {success_rate, avg_duration, user_satisfaction, etc.}
                
                -- Temporal scope
                window_start TIMESTAMP NOT NULL,
                window_end TIMESTAMP NOT NULL,
                sample_size INTEGER NOT NULL,
                
                -- Confidence and freshness
                confidence REAL NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Foreign keys
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                UNIQUE(user_id, entity_type, entity_id, window_start)
            )""",
            
            # Indexes for self-model queries
            "CREATE INDEX IF NOT EXISTS idx_self_model_user_entity ON agency_self_model(user_id, entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_self_model_freshness ON agency_self_model(last_updated DESC)",
            "CREATE INDEX IF NOT EXISTS idx_self_model_window ON agency_self_model(window_start, window_end)",
            
            # Reflection run tracking (for audit and scheduling)
            """CREATE TABLE IF NOT EXISTS agency_reflection_runs (
                run_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                
                -- Run metadata
                run_type TEXT NOT NULL,        -- scheduled, triggered, manual
                trigger_reason TEXT,           -- sleep_phase, goal_completion, user_request, etc.
                
                -- Analysis scope
                analysis_window_start TIMESTAMP NOT NULL,
                analysis_window_end TIMESTAMP NOT NULL,
                
                -- Results
                lessons_generated INTEGER DEFAULT 0,
                lessons_applied INTEGER DEFAULT 0,
                
                -- Timing
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                
                -- Status
                status TEXT NOT NULL,          -- running, completed, failed
                error_message TEXT,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Foreign keys
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            
            # Indexes for reflection run queries
            "CREATE INDEX IF NOT EXISTS idx_reflection_runs_user_time ON agency_reflection_runs(user_id, started_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_reflection_runs_status ON agency_reflection_runs(status) WHERE status = 'running'",
        ],
        rollback_statements=[
            # Drop indexes
            "DROP INDEX IF EXISTS idx_reflection_runs_status",
            "DROP INDEX IF EXISTS idx_reflection_runs_user_time",
            "DROP INDEX IF EXISTS idx_self_model_window",
            "DROP INDEX IF EXISTS idx_self_model_freshness",
            "DROP INDEX IF EXISTS idx_self_model_user_entity",
            "DROP INDEX IF EXISTS idx_agency_lessons_time",
            "DROP INDEX IF EXISTS idx_agency_lessons_superseded",
            "DROP INDEX IF EXISTS idx_agency_lessons_applied",
            "DROP INDEX IF EXISTS idx_agency_lessons_status",
            "DROP INDEX IF EXISTS idx_agency_lessons_target",
            "DROP INDEX IF EXISTS idx_agency_lessons_user_type",
            
            # Drop tables
            "DROP TABLE IF EXISTS agency_reflection_runs",
            "DROP TABLE IF EXISTS agency_self_model",
            "DROP TABLE IF EXISTS agency_lessons",
        ]
    ),
    
    # Schema Version 25: Goal Arbiter Adjustments
    25: SchemaVersion(
        version=25,
        name="Agency Phase 5 - Arbiter Adjustments",
        description="Add agency_arbiter_adjustments table for runtime lesson application",
        sql_statements=[
            # Goal Arbiter adjustments table
            """CREATE TABLE IF NOT EXISTS agency_arbiter_adjustments (
                adjustment_key TEXT PRIMARY KEY,     -- e.g., "goal_type_learning", "priority_weight"
                adjustment_value REAL NOT NULL,      -- The adjusted value
                lesson_id TEXT NOT NULL,             -- Which lesson caused this adjustment
                user_id TEXT,                        -- NULL for global adjustments
                applied_at TIMESTAMP NOT NULL,       -- When adjustment was applied
                confidence REAL NOT NULL,            -- Lesson confidence score
                active INTEGER DEFAULT 1,            -- 1=active, 0=disabled
                notes TEXT,                          -- Optional explanation
                
                FOREIGN KEY (lesson_id) REFERENCES agency_lessons(lesson_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            
            # Indexes for efficient querying
            "CREATE INDEX IF NOT EXISTS idx_arbiter_adjustments_active ON agency_arbiter_adjustments(active) WHERE active = 1",
            "CREATE INDEX IF NOT EXISTS idx_arbiter_adjustments_user ON agency_arbiter_adjustments(user_id, active)",
            "CREATE INDEX IF NOT EXISTS idx_arbiter_adjustments_lesson ON agency_arbiter_adjustments(lesson_id)",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_arbiter_adjustments_lesson",
            "DROP INDEX IF EXISTS idx_arbiter_adjustments_user",
            "DROP INDEX IF EXISTS idx_arbiter_adjustments_active",
            "DROP TABLE IF EXISTS agency_arbiter_adjustments",
        ]
    ),
    
    # Schema Version 26: Phase 6.5 - Goal Arbiter Advanced
    26: SchemaVersion(
        version=26,
        name="Agency Phase 6.5 - Arbiter Advanced (Adaptive Scoring & Context-Aware)",
        description="Add tables for multi-armed bandit adaptive scoring, A/B testing, context-aware prioritization, and goal outcomes tracking",
        sql_statements=[
            # Multi-Armed Bandit arms (weight configurations)
            """CREATE TABLE IF NOT EXISTS arbiter_bandit_arms (
                arm_id TEXT PRIMARY KEY,
                weights_json TEXT NOT NULL,          -- JSON of weight configuration
                pulls INTEGER DEFAULT 0,             -- Number of times this arm was selected
                total_reward REAL DEFAULT 0.0,       -- Cumulative reward
                success_count INTEGER DEFAULT 0,     -- Number of successful outcomes
                failure_count INTEGER DEFAULT 0,     -- Number of failed outcomes
                last_pulled TEXT,                    -- ISO timestamp of last use
                active INTEGER DEFAULT 1,            -- 1=active, 0=disabled
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_bandit_arms_active ON arbiter_bandit_arms(active)",
            "CREATE INDEX IF NOT EXISTS idx_bandit_arms_pulls ON arbiter_bandit_arms(pulls)",
            
            # A/B Testing framework
            """CREATE TABLE IF NOT EXISTS arbiter_ab_tests (
                test_id TEXT PRIMARY KEY,
                test_name TEXT NOT NULL,
                arm_a_id TEXT NOT NULL,
                arm_b_id TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT DEFAULT 'active',        -- active, completed, cancelled
                winner_arm_id TEXT,
                confidence_score REAL,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (arm_a_id) REFERENCES arbiter_bandit_arms(arm_id),
                FOREIGN KEY (arm_b_id) REFERENCES arbiter_bandit_arms(arm_id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_ab_tests_status ON arbiter_ab_tests(status)",
            "CREATE INDEX IF NOT EXISTS idx_ab_tests_dates ON arbiter_ab_tests(start_date, end_date)",
            
            # Goal outcomes (for reward calculation and learning)
            """CREATE TABLE IF NOT EXISTS goal_outcomes (
                outcome_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                arm_id TEXT,                         -- Which bandit arm was used
                outcome TEXT NOT NULL,               -- completed, abandoned, failed, timeout
                success INTEGER DEFAULT 0,           -- 1=success, 0=failure
                reward REAL,                         -- Calculated reward (0.0-1.0)
                completion_time_minutes INTEGER,
                user_satisfaction REAL,              -- Optional user feedback (0.0-1.0)
                metadata_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id),
                FOREIGN KEY (arm_id) REFERENCES arbiter_bandit_arms(arm_id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_goal_outcomes_goal ON goal_outcomes(goal_id)",
            "CREATE INDEX IF NOT EXISTS idx_goal_outcomes_user ON goal_outcomes(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_goal_outcomes_arm ON goal_outcomes(arm_id)",
            "CREATE INDEX IF NOT EXISTS idx_goal_outcomes_success ON goal_outcomes(success)",
            "CREATE INDEX IF NOT EXISTS idx_goal_outcomes_created ON goal_outcomes(created_at)",
            
            # Time-of-day preferences (learned from outcomes)
            """CREATE TABLE IF NOT EXISTS user_time_preferences (
                preference_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                time_period TEXT NOT NULL,           -- early_morning, morning, afternoon, evening, night
                productivity_score REAL DEFAULT 1.0, -- 0.0-2.0, learned multiplier
                sample_count INTEGER DEFAULT 0,      -- Number of observations
                last_updated TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                UNIQUE(user_id, time_period)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_time_prefs_user ON user_time_preferences(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_time_prefs_active ON user_time_preferences(active)",
            
            # Goal dependencies (for dependency-aware scheduling)
            """CREATE TABLE IF NOT EXISTS goal_dependencies (
                dependency_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,               -- Goal that has the dependency
                prerequisite_goal_id TEXT NOT NULL,  -- Goal that must be completed first
                dependency_type TEXT DEFAULT 'hard', -- hard, soft, suggested
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id),
                FOREIGN KEY (prerequisite_goal_id) REFERENCES agency_goals(goal_id),
                UNIQUE(goal_id, prerequisite_goal_id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_goal_deps_goal ON goal_dependencies(goal_id)",
            "CREATE INDEX IF NOT EXISTS idx_goal_deps_prereq ON goal_dependencies(prerequisite_goal_id)",
            "CREATE INDEX IF NOT EXISTS idx_goal_deps_active ON goal_dependencies(active)",
            
            # Context snapshots (for analysis and debugging)
            """CREATE TABLE IF NOT EXISTS arbiter_context_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                goal_id TEXT,
                time_of_day TEXT,                    -- early_morning, morning, etc.
                user_state TEXT,                     -- busy, focused, relaxed, etc.
                day_of_week TEXT,
                is_weekend INTEGER,
                current_load REAL,
                emotion_valence REAL,
                emotion_arousal REAL,
                emotion_stress REAL,
                location TEXT,
                context_json TEXT,                   -- Full context as JSON
                created_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_context_snapshots_user ON arbiter_context_snapshots(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_context_snapshots_goal ON arbiter_context_snapshots(goal_id)",
            "CREATE INDEX IF NOT EXISTS idx_context_snapshots_created ON arbiter_context_snapshots(created_at)",
            
            # Scoring history (for analysis and debugging)
            """CREATE TABLE IF NOT EXISTS arbiter_scoring_history (
                history_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                arm_id TEXT,
                base_score REAL NOT NULL,
                final_score REAL NOT NULL,
                adjustments_json TEXT,               -- JSON of all adjustments applied
                context_snapshot_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id),
                FOREIGN KEY (arm_id) REFERENCES arbiter_bandit_arms(arm_id),
                FOREIGN KEY (context_snapshot_id) REFERENCES arbiter_context_snapshots(snapshot_id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_scoring_history_goal ON arbiter_scoring_history(goal_id)",
            "CREATE INDEX IF NOT EXISTS idx_scoring_history_user ON arbiter_scoring_history(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_scoring_history_created ON arbiter_scoring_history(created_at)",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_scoring_history_created",
            "DROP INDEX IF EXISTS idx_scoring_history_user",
            "DROP INDEX IF EXISTS idx_scoring_history_goal",
            "DROP TABLE IF EXISTS arbiter_scoring_history",
            "DROP INDEX IF EXISTS idx_context_snapshots_created",
            "DROP INDEX IF EXISTS idx_context_snapshots_goal",
            "DROP INDEX IF EXISTS idx_context_snapshots_user",
            "DROP TABLE IF EXISTS arbiter_context_snapshots",
            "DROP INDEX IF EXISTS idx_goal_deps_active",
            "DROP INDEX IF EXISTS idx_goal_deps_prereq",
            "DROP INDEX IF EXISTS idx_goal_deps_goal",
            "DROP TABLE IF EXISTS goal_dependencies",
            "DROP INDEX IF EXISTS idx_time_prefs_active",
            "DROP INDEX IF EXISTS idx_time_prefs_user",
            "DROP TABLE IF EXISTS user_time_preferences",
            "DROP INDEX IF EXISTS idx_goal_outcomes_created",
            "DROP INDEX IF EXISTS idx_goal_outcomes_success",
            "DROP INDEX IF EXISTS idx_goal_outcomes_arm",
            "DROP INDEX IF EXISTS idx_goal_outcomes_user",
            "DROP INDEX IF EXISTS idx_goal_outcomes_goal",
            "DROP TABLE IF EXISTS goal_outcomes",
            "DROP INDEX IF EXISTS idx_ab_tests_dates",
            "DROP INDEX IF EXISTS idx_ab_tests_status",
            "DROP TABLE IF EXISTS arbiter_ab_tests",
            "DROP INDEX IF EXISTS idx_bandit_arms_pulls",
            "DROP INDEX IF EXISTS idx_bandit_arms_active",
            "DROP TABLE IF EXISTS arbiter_bandit_arms",
        ]
    ),
    
    # Schema Version 27: Phase 6.6 - Behavioral Feedback Integration
    27: SchemaVersion(
        version=27,
        name="Agency Phase 6.6 - Behavioral Feedback Integration",
        description="Add outcome tracking, skill execution tracking, and complete feedback loop for behavioral learning",
        sql_statements=[
            # Add outcome column to ams_behavioral_feedback
            """ALTER TABLE ams_behavioral_feedback ADD COLUMN outcome TEXT""",
            
            # Add execution metadata columns
            """ALTER TABLE ams_behavioral_feedback ADD COLUMN execution_time_ms INTEGER""",
            """ALTER TABLE ams_behavioral_feedback ADD COLUMN context_json TEXT""",
            """ALTER TABLE ams_behavioral_feedback ADD COLUMN user_satisfaction REAL""",
            
            # Create skill execution tracking table
            """CREATE TABLE IF NOT EXISTS skill_executions (
                execution_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                message_id TEXT,
                goal_id TEXT,
                execution_time_ms INTEGER,
                outcome TEXT NOT NULL,  -- success, failure, timeout, error
                error_message TEXT,
                context_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_skill_executions_skill ON skill_executions(skill_id)",
            "CREATE INDEX IF NOT EXISTS idx_skill_executions_user ON skill_executions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_skill_executions_outcome ON skill_executions(outcome)",
            "CREATE INDEX IF NOT EXISTS idx_skill_executions_created ON skill_executions(created_at)",
            
            # Create goal-skill linkage table
            """CREATE TABLE IF NOT EXISTS goal_skill_executions (
                link_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                execution_order INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE,
                FOREIGN KEY (execution_id) REFERENCES skill_executions(execution_id) ON DELETE CASCADE,
                UNIQUE(goal_id, execution_id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_goal_skill_exec_goal ON goal_skill_executions(goal_id)",
            "CREATE INDEX IF NOT EXISTS idx_goal_skill_exec_skill ON goal_skill_executions(skill_id)",
            
            # Create user feedback collection table
            """CREATE TABLE IF NOT EXISTS user_feedback_requests (
                request_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                goal_id TEXT,
                skill_id TEXT,
                execution_id TEXT,
                feedback_type TEXT NOT NULL,  -- satisfaction, quality, helpfulness
                question TEXT NOT NULL,
                response TEXT,
                rating REAL,
                responded_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE SET NULL,
                FOREIGN KEY (execution_id) REFERENCES skill_executions(execution_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_feedback_requests_user ON user_feedback_requests(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_requests_responded ON user_feedback_requests(responded_at)",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_feedback_requests_responded",
            "DROP INDEX IF EXISTS idx_feedback_requests_user",
            "DROP TABLE IF EXISTS user_feedback_requests",
            "DROP INDEX IF EXISTS idx_goal_skill_exec_skill",
            "DROP INDEX IF EXISTS idx_goal_skill_exec_goal",
            "DROP TABLE IF EXISTS goal_skill_executions",
            "DROP INDEX IF EXISTS idx_skill_executions_created",
            "DROP INDEX IF EXISTS idx_skill_executions_outcome",
            "DROP INDEX IF EXISTS idx_skill_executions_user",
            "DROP INDEX IF EXISTS idx_skill_executions_skill",
            "DROP TABLE IF EXISTS skill_executions",
            # Note: Cannot rollback ALTER TABLE ADD COLUMN in SQLite
            # New columns will remain but be unused if rolled back
        ]
    ),
    
    # Schema Version 28: Phase 6.7 - Proactive Behaviors
    28: SchemaVersion(
        version=28,
        name="Agency Phase 6.7 - Proactive Behaviors (Follow-ups & Reminders)",
        description="Add tables for policy-aware follow-ups and smart reminder scheduling",
        sql_statements=[
            # Follow-ups table
            """CREATE TABLE IF NOT EXISTS agency_followups (
                followup_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                goal_id TEXT,
                related_message_id TEXT,
                followup_type TEXT NOT NULL,  -- check_in, progress_update, completion_prompt, clarification
                content TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                delivered_at TEXT,
                user_response TEXT,
                response_sentiment REAL,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, delivered, responded, dismissed, expired
                priority INTEGER DEFAULT 50,
                policy_approved INTEGER DEFAULT 1,
                relationship_context TEXT,  -- JSON: relationship strength, interaction history
                values_alignment REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_followups_user ON agency_followups(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_followups_scheduled ON agency_followups(scheduled_at, status)",
            "CREATE INDEX IF NOT EXISTS idx_followups_goal ON agency_followups(goal_id)",
            "CREATE INDEX IF NOT EXISTS idx_followups_status ON agency_followups(status)",
            
            # Reminders table
            """CREATE TABLE IF NOT EXISTS agency_reminders (
                reminder_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                goal_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                scheduled_at TEXT NOT NULL,
                delivered_at TEXT,
                snoozed_until TEXT,
                snooze_count INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, delivered, snoozed, completed, dismissed
                priority TEXT NOT NULL DEFAULT 'normal',  -- low, normal, high, urgent
                urgency_score REAL DEFAULT 0.5,
                recurrence_rule TEXT,  -- JSON: frequency, interval, end_date
                cluster_id TEXT,  -- For grouping related reminders
                adaptation_data TEXT,  -- JSON: user response patterns, optimal timing
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_reminders_user ON agency_reminders(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_reminders_scheduled ON agency_reminders(scheduled_at, status)",
            "CREATE INDEX IF NOT EXISTS idx_reminders_goal ON agency_reminders(goal_id)",
            "CREATE INDEX IF NOT EXISTS idx_reminders_cluster ON agency_reminders(cluster_id)",
            "CREATE INDEX IF NOT EXISTS idx_reminders_status ON agency_reminders(status)",
            "CREATE INDEX IF NOT EXISTS idx_reminders_priority ON agency_reminders(priority, urgency_score)",
            
            # Reminder clusters table (for batching)
            """CREATE TABLE IF NOT EXISTS reminder_clusters (
                cluster_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                cluster_name TEXT,
                scheduled_delivery TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, delivered, dismissed
                reminder_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_reminder_clusters_user ON reminder_clusters(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_reminder_clusters_delivery ON reminder_clusters(scheduled_delivery, status)",
            
            # User proactive preferences table
            """CREATE TABLE IF NOT EXISTS user_proactive_preferences (
                user_id TEXT PRIMARY KEY,
                followup_enabled INTEGER DEFAULT 1,
                reminder_enabled INTEGER DEFAULT 1,
                preferred_followup_times TEXT,  -- JSON: array of preferred hours
                preferred_reminder_times TEXT,  -- JSON: array of preferred hours
                max_followups_per_day INTEGER DEFAULT 3,
                max_reminders_per_day INTEGER DEFAULT 5,
                min_hours_between_followups INTEGER DEFAULT 4,
                min_hours_between_reminders INTEGER DEFAULT 2,
                cluster_reminders INTEGER DEFAULT 1,
                auto_snooze_duration_minutes INTEGER DEFAULT 60,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            
            # Proactive behavior analytics table
            """CREATE TABLE IF NOT EXISTS proactive_analytics (
                analytics_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                behavior_type TEXT NOT NULL,  -- followup, reminder
                item_id TEXT NOT NULL,
                delivered_at TEXT NOT NULL,
                user_action TEXT,  -- responded, dismissed, snoozed, ignored
                response_time_minutes INTEGER,
                sentiment_score REAL,
                effectiveness_score REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_proactive_analytics_user ON proactive_analytics(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_proactive_analytics_type ON proactive_analytics(behavior_type)",
            "CREATE INDEX IF NOT EXISTS idx_proactive_analytics_delivered ON proactive_analytics(delivered_at)",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_proactive_analytics_delivered",
            "DROP INDEX IF EXISTS idx_proactive_analytics_type",
            "DROP INDEX IF EXISTS idx_proactive_analytics_user",
            "DROP TABLE IF EXISTS proactive_analytics",
            "DROP TABLE IF EXISTS user_proactive_preferences",
            "DROP INDEX IF EXISTS idx_reminder_clusters_delivery",
            "DROP INDEX IF EXISTS idx_reminder_clusters_user",
            "DROP TABLE IF EXISTS reminder_clusters",
            "DROP INDEX IF EXISTS idx_reminders_priority",
            "DROP INDEX IF EXISTS idx_reminders_status",
            "DROP INDEX IF EXISTS idx_reminders_cluster",
            "DROP INDEX IF EXISTS idx_reminders_goal",
            "DROP INDEX IF EXISTS idx_reminders_scheduled",
            "DROP INDEX IF EXISTS idx_reminders_user",
            "DROP TABLE IF EXISTS agency_reminders",
            "DROP INDEX IF EXISTS idx_followups_status",
            "DROP INDEX IF EXISTS idx_followups_goal",
            "DROP INDEX IF EXISTS idx_followups_scheduled",
            "DROP INDEX IF EXISTS idx_followups_user",
            "DROP TABLE IF EXISTS agency_followups",
        ]
    ),
    
    # Schema Version 29: Phase 6.8 - Policy & Ethics Depth
    29: SchemaVersion(
        version=29,
        name="Agency Phase 6.8 - Policy & Ethics Depth (Dynamic Policies & Consent)",
        description="Add tables for database-driven policy management, consent tracking, and enhanced ethics gates",
        sql_statements=[
            # Policy rules table (replaces hardcoded DEFAULT_POLICIES)
            """CREATE TABLE IF NOT EXISTS agency_policy_rules (
                rule_id TEXT PRIMARY KEY,
                rule_name TEXT NOT NULL,
                user_id TEXT,  -- NULL for global policies
                target_type TEXT NOT NULL,  -- goal, curiosity_signal, plan, world_model_update
                conditions TEXT NOT NULL,  -- JSON: conditions to match
                effect TEXT NOT NULL,  -- allow, block, needs_consent, allow_with_warning
                user_message_template TEXT,
                priority INTEGER DEFAULT 50,
                scope TEXT NOT NULL,  -- global, user, deployment
                version INTEGER DEFAULT 1,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_policy_rules_user ON agency_policy_rules(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_policy_rules_target ON agency_policy_rules(target_type, active)",
            "CREATE INDEX IF NOT EXISTS idx_policy_rules_scope ON agency_policy_rules(scope, active)",
            
            # Policy versions table (for migration and rollback)
            """CREATE TABLE IF NOT EXISTS policy_versions (
                version_id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                conditions TEXT NOT NULL,
                effect TEXT NOT NULL,
                user_message_template TEXT,
                priority INTEGER,
                created_at TEXT NOT NULL,
                created_by TEXT,
                FOREIGN KEY (rule_id) REFERENCES agency_policy_rules(rule_id) ON DELETE CASCADE,
                UNIQUE(rule_id, version_number)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_policy_versions_rule ON policy_versions(rule_id)",
            
            # Consent tracking table
            """CREATE TABLE IF NOT EXISTS user_consents (
                consent_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                consent_type TEXT NOT NULL,  -- curiosity_exploration, data_collection, proactive_contact, etc.
                scope TEXT NOT NULL,  -- specific_goal, life_area, feature, global
                scope_identifier TEXT,  -- goal_id, life_area name, feature name, etc.
                granted INTEGER NOT NULL,  -- 1 = granted, 0 = denied
                expires_at TEXT,  -- NULL for permanent consent
                inherited_from TEXT,  -- consent_id if inherited
                granted_at TEXT NOT NULL,
                revoked_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (inherited_from) REFERENCES user_consents(consent_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_consents_user ON user_consents(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_consents_type ON user_consents(consent_type, granted)",
            "CREATE INDEX IF NOT EXISTS idx_consents_scope ON user_consents(scope, scope_identifier)",
            "CREATE INDEX IF NOT EXISTS idx_consents_expires ON user_consents(expires_at)",
            
            # Consent audit log
            """CREATE TABLE IF NOT EXISTS consent_audit_log (
                audit_id TEXT PRIMARY KEY,
                consent_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,  -- granted, revoked, expired, inherited
                reason TEXT,
                metadata TEXT,  -- JSON: additional context
                created_at TEXT NOT NULL,
                FOREIGN KEY (consent_id) REFERENCES user_consents(consent_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_consent_audit_consent ON consent_audit_log(consent_id)",
            "CREATE INDEX IF NOT EXISTS idx_consent_audit_user ON consent_audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_consent_audit_created ON consent_audit_log(created_at)",
            
            # Ethics gate decisions cache
            """CREATE TABLE IF NOT EXISTS ethics_decisions_cache (
                cache_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                decision TEXT NOT NULL,  -- approved, blocked, needs_review
                reasoning TEXT,
                policy_rules_applied TEXT,  -- JSON: list of rule_ids applied
                confidence REAL DEFAULT 1.0,
                cached_at TEXT NOT NULL,
                expires_at TEXT,
                hit_count INTEGER DEFAULT 0,
                last_hit_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_ethics_cache_user ON ethics_decisions_cache(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_ethics_cache_target ON ethics_decisions_cache(target_type, target_id)",
            "CREATE INDEX IF NOT EXISTS idx_ethics_cache_expires ON ethics_decisions_cache(expires_at)",
            
            # Ethics gate audit trail
            """CREATE TABLE IF NOT EXISTS ethics_gate_audit (
                audit_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                reasoning TEXT,
                policy_rules_applied TEXT,  -- JSON
                check_level INTEGER DEFAULT 1,  -- 1 = basic, 2 = detailed, 3 = comprehensive
                cached INTEGER DEFAULT 0,
                processing_time_ms INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_ethics_audit_user ON ethics_gate_audit(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_ethics_audit_target ON ethics_gate_audit(target_type)",
            "CREATE INDEX IF NOT EXISTS idx_ethics_audit_decision ON ethics_gate_audit(decision)",
            "CREATE INDEX IF NOT EXISTS idx_ethics_audit_created ON ethics_gate_audit(created_at)",
            
            # Policy conflict resolution log
            """CREATE TABLE IF NOT EXISTS policy_conflicts (
                conflict_id TEXT PRIMARY KEY,
                user_id TEXT,
                rule_id_a TEXT NOT NULL,
                rule_id_b TEXT NOT NULL,
                target_type TEXT NOT NULL,
                resolution TEXT NOT NULL,  -- priority_based, user_choice, most_restrictive
                resolved_by TEXT,  -- system, user, admin
                resolution_metadata TEXT,  -- JSON
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (rule_id_a) REFERENCES agency_policy_rules(rule_id) ON DELETE CASCADE,
                FOREIGN KEY (rule_id_b) REFERENCES agency_policy_rules(rule_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_policy_conflicts_user ON policy_conflicts(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_policy_conflicts_rules ON policy_conflicts(rule_id_a, rule_id_b)",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_policy_conflicts_rules",
            "DROP INDEX IF EXISTS idx_policy_conflicts_user",
            "DROP TABLE IF EXISTS policy_conflicts",
            "DROP INDEX IF EXISTS idx_ethics_audit_created",
            "DROP INDEX IF EXISTS idx_ethics_audit_decision",
            "DROP INDEX IF EXISTS idx_ethics_audit_target",
            "DROP INDEX IF EXISTS idx_ethics_audit_user",
            "DROP TABLE IF EXISTS ethics_gate_audit",
            "DROP INDEX IF EXISTS idx_ethics_cache_expires",
            "DROP INDEX IF EXISTS idx_ethics_cache_target",
            "DROP INDEX IF EXISTS idx_ethics_cache_user",
            "DROP TABLE IF EXISTS ethics_decisions_cache",
            "DROP INDEX IF EXISTS idx_consent_audit_created",
            "DROP INDEX IF EXISTS idx_consent_audit_user",
            "DROP INDEX IF EXISTS idx_consent_audit_consent",
            "DROP TABLE IF EXISTS consent_audit_log",
            "DROP INDEX IF EXISTS idx_consents_expires",
            "DROP INDEX IF EXISTS idx_consents_scope",
            "DROP INDEX IF EXISTS idx_consents_type",
            "DROP INDEX IF EXISTS idx_consents_user",
            "DROP TABLE IF EXISTS user_consents",
            "DROP INDEX IF EXISTS idx_policy_versions_rule",
            "DROP TABLE IF EXISTS policy_versions",
            "DROP INDEX IF EXISTS idx_policy_rules_scope",
            "DROP INDEX IF EXISTS idx_policy_rules_target",
            "DROP INDEX IF EXISTS idx_policy_rules_user",
            "DROP TABLE IF EXISTS agency_policy_rules",
        ]
    ),
    
    # Schema Version 30: Phase 6.9 - Integration & Data Flow
    30: SchemaVersion(
        version=30,
        name="Agency Phase 6.9 - Integration & Data Flow (Workflows & Events)",
        description="Add tables for end-to-end workflow tracking, comprehensive event logging, and event-driven triggers",
        sql_statements=[
            # Workflow executions table
            """CREATE TABLE IF NOT EXISTS workflow_executions (
                execution_id TEXT PRIMARY KEY,
                workflow_type TEXT NOT NULL,  -- goal_lifecycle, curiosity_to_goal, reflection_cycle, world_model_update
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',  -- running, completed, failed, paused
                started_at TEXT NOT NULL,
                completed_at TEXT,
                current_stage TEXT,
                total_stages INTEGER,
                metadata TEXT,  -- JSON: workflow-specific data
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_workflow_executions_user ON workflow_executions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_workflow_executions_type ON workflow_executions(workflow_type, status)",
            "CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status)",
            
            # Workflow stages table
            """CREATE TABLE IF NOT EXISTS workflow_stages (
                stage_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                stage_order INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, skipped
                started_at TEXT,
                completed_at TEXT,
                input_data TEXT,  -- JSON
                output_data TEXT,  -- JSON
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (execution_id) REFERENCES workflow_executions(execution_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_workflow_stages_execution ON workflow_stages(execution_id, stage_order)",
            "CREATE INDEX IF NOT EXISTS idx_workflow_stages_status ON workflow_stages(status)",
            
            # Agency events table (comprehensive event log)
            """CREATE TABLE IF NOT EXISTS agency_events_log (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- goal_created, plan_generated, skill_executed, feedback_received, etc.
                event_category TEXT NOT NULL,  -- goal, plan, execution, feedback, curiosity, reflection, policy
                source_component TEXT NOT NULL,  -- planner, arbiter, curiosity_engine, reflection_engine, etc.
                entity_type TEXT,  -- goal, plan, skill, lesson, policy, etc.
                entity_id TEXT,
                event_data TEXT NOT NULL,  -- JSON: event-specific data
                workflow_trace_id TEXT,  -- For tracking related events in a workflow (distinct from conversation correlation_id)
                parent_event_id TEXT,  -- For event hierarchies
                severity TEXT DEFAULT 'info',  -- debug, info, warning, error, critical
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
                FOREIGN KEY (parent_event_id) REFERENCES agency_events_log(event_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_events_log_user ON agency_events_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_log_type ON agency_events_log(event_type, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_events_log_category ON agency_events_log(event_category)",
            "CREATE INDEX IF NOT EXISTS idx_events_log_entity ON agency_events_log(entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_log_trace ON agency_events_log(workflow_trace_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_log_created ON agency_events_log(created_at)",
            
            # Event triggers table
            """CREATE TABLE IF NOT EXISTS event_triggers (
                trigger_id TEXT PRIMARY KEY,
                trigger_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_category TEXT,
                conditions TEXT,  -- JSON: conditions to match
                action_type TEXT NOT NULL,  -- execute_workflow, send_notification, update_state, etc.
                action_config TEXT NOT NULL,  -- JSON: action configuration
                priority INTEGER DEFAULT 50,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_event_triggers_type ON event_triggers(event_type, active)",
            "CREATE INDEX IF NOT EXISTS idx_event_triggers_category ON event_triggers(event_category, active)",
            
            # Event replay sessions table
            """CREATE TABLE IF NOT EXISTS event_replay_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                replay_name TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                event_filters TEXT,  -- JSON: filters applied
                replay_speed REAL DEFAULT 1.0,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
                events_replayed INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_replay_sessions_user ON event_replay_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_replay_sessions_status ON event_replay_sessions(status)",
            
            # Event metrics table
            """CREATE TABLE IF NOT EXISTS event_metrics (
                metric_id TEXT PRIMARY KEY,
                metric_name TEXT NOT NULL,
                metric_type TEXT NOT NULL,  -- counter, gauge, histogram, summary
                event_type TEXT,
                event_category TEXT,
                time_bucket TEXT NOT NULL,  -- hourly, daily, weekly
                bucket_start TEXT NOT NULL,
                value REAL NOT NULL,
                count INTEGER DEFAULT 1,
                metadata TEXT,  -- JSON
                created_at TEXT NOT NULL,
                UNIQUE(metric_name, event_type, time_bucket, bucket_start)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_event_metrics_name ON event_metrics(metric_name, bucket_start)",
            "CREATE INDEX IF NOT EXISTS idx_event_metrics_type ON event_metrics(event_type, bucket_start)",
            "CREATE INDEX IF NOT EXISTS idx_event_metrics_bucket ON event_metrics(time_bucket, bucket_start)",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_event_metrics_bucket",
            "DROP INDEX IF EXISTS idx_event_metrics_type",
            "DROP INDEX IF EXISTS idx_event_metrics_name",
            "DROP TABLE IF EXISTS event_metrics",
            "DROP INDEX IF EXISTS idx_replay_sessions_status",
            "DROP INDEX IF EXISTS idx_replay_sessions_user",
            "DROP TABLE IF EXISTS event_replay_sessions",
            "DROP INDEX IF EXISTS idx_event_triggers_category",
            "DROP INDEX IF EXISTS idx_event_triggers_type",
            "DROP TABLE IF EXISTS event_triggers",
            "DROP INDEX IF EXISTS idx_events_log_created",
            "DROP INDEX IF EXISTS idx_events_log_trace",
            "DROP INDEX IF EXISTS idx_events_log_entity",
            "DROP INDEX IF EXISTS idx_events_log_category",
            "DROP INDEX IF EXISTS idx_events_log_type",
            "DROP INDEX IF EXISTS idx_events_log_user",
            "DROP TABLE IF EXISTS agency_events_log",
            "DROP INDEX IF EXISTS idx_workflow_stages_status",
            "DROP INDEX IF EXISTS idx_workflow_stages_execution",
            "DROP TABLE IF EXISTS workflow_stages",
            "DROP INDEX IF EXISTS idx_workflow_executions_status",
            "DROP INDEX IF EXISTS idx_workflow_executions_type",
            "DROP INDEX IF EXISTS idx_workflow_executions_user",
            "DROP TABLE IF EXISTS workflow_executions"
        ]
    ),
    
    # Schema Version 31: Fix Missing arbiter_bandit_arms Table
    31: SchemaVersion(
        version=31,
        name="Fix Missing arbiter_bandit_arms Table",
        description="Recreate arbiter_bandit_arms table that was missing from Schema v26 migration. Required for adaptive scoring in Goal Arbiter (multi-armed bandit algorithms).",
        sql_statements=[
            """CREATE TABLE IF NOT EXISTS arbiter_bandit_arms (
                arm_id TEXT PRIMARY KEY,
                weights_json TEXT NOT NULL,
                pulls INTEGER DEFAULT 0,
                total_reward REAL DEFAULT 0.0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_pulled TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_bandit_arms_active ON arbiter_bandit_arms(active)",
            "CREATE INDEX IF NOT EXISTS idx_bandit_arms_pulls ON arbiter_bandit_arms(pulls)",
        ],
        rollback_statements=[
            "DROP INDEX IF EXISTS idx_bandit_arms_pulls",
            "DROP INDEX IF EXISTS idx_bandit_arms_active",
            "DROP TABLE IF EXISTS arbiter_bandit_arms",
        ]
    )
})
