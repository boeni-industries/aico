"""
Communication Schema

Database schema for AICO-initiated conversation tracking and learning.
"""

from ..libsql.schema import SchemaVersion

# Version 1: Initial communication schema
COMMUNICATION_SCHEMA_V1 = SchemaVersion(
    version=1,
    name="communication_initiations",
    description="Track AICO-initiated conversations for learning and optimization",
    sql_statements=[
        """
        CREATE TABLE IF NOT EXISTS aico_conversation_initiations (
            initiation_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            trigger_source TEXT NOT NULL,
            trigger_reason TEXT,
            question TEXT,
            context TEXT,
            urgency TEXT DEFAULT 'medium',
            expected_answer_type TEXT DEFAULT 'text',
            initiated_at TIMESTAMP NOT NULL,
            resolved_at TIMESTAMP,
            resolution_status TEXT DEFAULT 'pending',
            user_response_time INTEGER,
            engagement_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_uuid) ON DELETE CASCADE
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_initiations_user_id 
        ON aico_conversation_initiations(user_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_initiations_conversation_id 
        ON aico_conversation_initiations(conversation_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_initiations_status 
        ON aico_conversation_initiations(resolution_status)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_initiations_initiated_at 
        ON aico_conversation_initiations(initiated_at)
        """,
    ],
    rollback_statements=[
        "DROP INDEX IF EXISTS idx_initiations_initiated_at",
        "DROP INDEX IF EXISTS idx_initiations_status",
        "DROP INDEX IF EXISTS idx_initiations_conversation_id",
        "DROP INDEX IF EXISTS idx_initiations_user_id",
        "DROP TABLE IF EXISTS aico_conversation_initiations",
    ]
)

# Export schema versions
COMMUNICATION_SCHEMAS = {
    1: COMMUNICATION_SCHEMA_V1,
}
