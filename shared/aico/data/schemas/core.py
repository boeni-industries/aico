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
    )
})
