"""
SQLAlchemy Core Table Definitions

Maps PostgreSQL schema to SQLAlchemy Table objects for type-safe query building.
These tables mirror the schema in shared/aico/data/postgres/schema.sql
"""

from sqlalchemy import (
    Table, Column, MetaData,
    String, Integer, BigInteger, Boolean, Float, DateTime, Text,
    ForeignKey, Index, JSON, LargeBinary
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

# MetaData instance - all tables will be registered here
metadata = MetaData(schema="aico_core")

# ============================================================================
# User & Authentication Tables
# ============================================================================

user_profiles = Table(
    'user_profiles',
    metadata,
    Column('uuid', String, primary_key=True),
    Column('full_name', String, nullable=False),
    Column('nickname', String),
    Column('user_type', String, nullable=False),
    Column('is_active', Boolean, nullable=False, default=True),
    Column('primary_language', String, nullable=False, default='en'),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False),
)

user_proactive_preferences = Table(
    'user_proactive_preferences',
    metadata,
    Column('user_id', String, primary_key=True),
    Column('followup_enabled', Boolean, default=True),
    Column('reminder_enabled', Boolean, default=True),
    Column('preferred_followup_times', String),
    Column('preferred_reminder_times', String),
    Column('max_followups_per_day', Integer, default=3),
    Column('max_reminders_per_day', Integer, default=5),
    Column('min_hours_between_followups', Integer, default=4),
    Column('min_hours_between_reminders', Integer, default=2),
    Column('cluster_reminders', Integer, default=1),
    Column('auto_snooze_duration_minutes', Integer, default=60),
    Column('updated_at', String, nullable=False),
)

auth_devices = Table(
    'auth_devices',
    metadata,
    Column('uuid', String, primary_key=True),
    Column('device_name', String, nullable=False),
    Column('device_type', String, nullable=False),
    Column('platform', String, nullable=False),
    Column('last_seen', TIMESTAMP(timezone=True)),
    Column('is_active', Boolean, default=True),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
    Index('idx_devices_active', 'is_active'),
)

auth_sessions = Table(
    'auth_sessions',
    metadata,
    Column('uuid', String, primary_key=True),
    Column('user_uuid', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('device_uuid', String, nullable=False),
    Column('jwt_token_hash', String, nullable=False),
    Column('expires_at', TIMESTAMP(timezone=True), nullable=False),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('is_active', Boolean, default=True),
    Column('session_type', String, default='unified'),
    Index('idx_auth_sessions_active', 'is_active', 'expires_at'),
    Index('idx_auth_sessions_user', 'user_uuid'),
)

auth_user_credentials = Table(
    'auth_user_credentials',
    metadata,
    Column('uuid', String, primary_key=True),
    Column('user_uuid', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('pin_hash', String, nullable=False),
    Column('failed_attempts', Integer, default=0),
    Column('locked_until', TIMESTAMP(timezone=True)),
    Column('last_login', TIMESTAMP(timezone=True)),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
    Index('idx_user_authentication_locked_until', 'locked_until'),
    Index('idx_user_authentication_pin_hash', 'pin_hash'),
    Index('idx_user_authentication_user', 'user_uuid'),
)

# ============================================================================
# Agency Core Tables
# ============================================================================

agency_events = Table(
    'agency_events',
    metadata,
    Column('id', BigInteger, primary_key=True, autoincrement=True),
    Column('user_id', String, nullable=False),
    Column('goal_id', String),
    Column('plan_id', String),
    Column('event_type', String, nullable=False),
    Column('source', String, nullable=False),
    Column('payload_json', JSONB, nullable=False),
    Column('created_at', TIMESTAMP(timezone=True)),
    Index('idx_agency_events_goal', 'goal_id'),
    Index('idx_agency_events_type', 'event_type'),
    Index('idx_agency_events_user_time', 'user_id', 'created_at'),
)

agency_events_log = Table(
    'agency_events_log',
    metadata,
    Column('event_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('event_type', String, nullable=False),
    Column('event_category', String, nullable=False),
    Column('source_component', String, nullable=False),
    Column('entity_type', String),
    Column('entity_id', String),
    Column('event_data', String, nullable=False),
    Column('workflow_trace_id', String),
    Column('parent_event_id', String),
    Column('severity', String, default='info'),
    Column('created_at', String, nullable=False),
    Index('idx_events_log_category', 'event_category'),
    Index('idx_events_log_created', 'created_at'),
    Index('idx_events_log_entity', 'entity_type', 'entity_id'),
    Index('idx_events_log_type', 'event_type', 'created_at'),
    Index('idx_events_log_user', 'user_id'),
)

agency_followups = Table(
    'agency_followups',
    metadata,
    Column('followup_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('goal_id', String),
    Column('related_message_id', String),
    Column('followup_type', String, nullable=False),
    Column('content', String, nullable=False),
    Column('scheduled_at', String, nullable=False),
    Column('delivered_at', String),
    Column('user_response', String),
    Column('response_sentiment', Float),
    Column('status', String, nullable=False, default='pending'),
    Column('priority', Integer, default=50),
    Column('policy_approved', Integer, default=1),
    Column('relationship_context', String),
    Column('values_alignment', Float),
    Column('created_at', String, nullable=False),
    Column('updated_at', String, nullable=False),
    Index('idx_followups_goal', 'goal_id'),
    Index('idx_followups_scheduled', 'scheduled_at', 'status'),
    Index('idx_followups_status', 'status'),
    Index('idx_followups_user', 'user_id'),
)

agency_reflection_notes = Table(
    'agency_reflection_notes',
    metadata,
    Column('note_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('related_goal_id', String),
    Column('related_plan_id', String),
    Column('title', String, nullable=False),
    Column('content', String, nullable=False),
    Column('tags_json', JSONB),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
    Index('idx_agency_reflection_goal', 'related_goal_id'),
    Index('idx_agency_reflection_user_time', 'user_id', 'created_at'),
)

agency_reminders = Table(
    'agency_reminders',
    metadata,
    Column('reminder_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('goal_id', String),
    Column('title', String, nullable=False),
    Column('description', String),
    Column('scheduled_at', String, nullable=False),
    Column('delivered_at', String),
    Column('snoozed_until', String),
    Column('snooze_count', Integer, default=0),
    Column('status', String, nullable=False, default='pending'),
    Column('priority', String, nullable=False, default='normal'),
    Column('urgency_score', Float, default=0.5),
    Column('recurrence_rule', String),
    Column('cluster_id', String),
    Column('adaptation_data', String),
    Column('created_at', String, nullable=False),
    Column('updated_at', String, nullable=False),
    Index('idx_reminders_cluster', 'cluster_id'),
    Index('idx_reminders_goal', 'goal_id'),
    Index('idx_reminders_priority', 'priority', 'urgency_score'),
    Index('idx_reminders_scheduled', 'scheduled_at', 'status'),
    Index('idx_reminders_status', 'status'),
    Index('idx_reminders_user', 'user_id'),
)

agency_goals = Table(
    'agency_goals',
    metadata,
    Column('goal_id', String, primary_key=True),
    Column('user_id', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('origin', String, nullable=False),
    Column('goal_type', String),
    Column('title', String, nullable=False),
    Column('description', String),
    Column('status', String, nullable=False),
    Column('priority', String, nullable=False),
    Column('metadata_json', JSONB),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_agency_goals_user', 'user_id'),
    Index('idx_agency_goals_status', 'status'),
    Index('idx_agency_goals_user_status', 'user_id', 'status'),
)

agency_plans = Table(
    'agency_plans',
    metadata,
    Column('plan_id', String, primary_key=True),
    Column('goal_id', String, ForeignKey('agency_goals.goal_id', ondelete='CASCADE'), nullable=False),
    Column('status', String, nullable=False),
    Column('steps_json', JSONB, nullable=False),
    Column('metadata_json', JSONB),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_agency_plans_goal', 'goal_id'),
    Index('idx_agency_plans_status', 'status'),
)

agency_lessons = Table(
    'agency_lessons',
    metadata,
    Column('lesson_id', String, primary_key=True),
    Column('user_id', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('lesson_type', String, nullable=False),
    Column('content', Text, nullable=False),
    Column('confidence', Float, nullable=False),
    Column('status', String, nullable=False),
    Column('source_data', JSONB),
    Column('superseded_by', String, ForeignKey('agency_lessons.lesson_id', ondelete='SET NULL')),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_agency_lessons_user', 'user_id'),
    Index('idx_agency_lessons_status', 'status'),
    Index('idx_agency_lessons_type', 'lesson_type'),
)

# ============================================================================
# Knowledge Graph Tables
# ============================================================================

kg_nodes = Table(
    'kg_nodes',
    metadata,
    Column('id', String, primary_key=True),
    Column('user_id', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('label', String, nullable=False),
    Column('properties', JSONB, nullable=False),
    Column('confidence', Float, nullable=False, default=1.0),
    Column('source_text', Text),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False),
    Column('language', String),
    Column('valid_from', TIMESTAMP(timezone=True)),
    Column('valid_until', TIMESTAMP(timezone=True)),
    Column('is_current', Boolean, nullable=False, default=True),
    Column('canonical_id', String),
    Column('aliases_json', JSONB),
    Index('idx_kg_nodes_user', 'user_id'),
    Index('idx_kg_nodes_label', 'label'),
    Index('idx_kg_nodes_current', 'is_current'),
)

kg_edges = Table(
    'kg_edges',
    metadata,
    Column('id', String, primary_key=True),
    Column('user_id', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('source_id', String, ForeignKey('kg_nodes.id', ondelete='CASCADE'), nullable=False),
    Column('target_id', String, ForeignKey('kg_nodes.id', ondelete='CASCADE'), nullable=False),
    Column('relation_type', String, nullable=False),
    Column('properties', JSONB),
    Column('confidence', Float, nullable=False, default=1.0),
    Column('source_text', Text),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False),
    Column('valid_from', TIMESTAMP(timezone=True)),
    Column('valid_until', TIMESTAMP(timezone=True)),
    Column('is_current', Boolean, nullable=False, default=True),
    Index('idx_kg_edges_user', 'user_id'),
    Index('idx_kg_edges_source', 'source_id'),
    Index('idx_kg_edges_target', 'target_id'),
    Index('idx_kg_edges_relation', 'relation_type'),
    Index('idx_kg_edges_current', 'is_current'),
)

# ============================================================================
# AMS/Behavioral Tables
# ============================================================================

ams_behavioral_skills = Table(
    'ams_behavioral_skills',
    metadata,
    Column('skill_id', String, primary_key=True),
    Column('skill_name', String, nullable=False),
    Column('skill_type', String, nullable=False),
    Column('trigger_context', String, nullable=False),
    Column('procedure_template', String, nullable=False),
    Column('dimension_vector', String, nullable=False),
    Column('supported_languages', String),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
    Column('status', String, default='active'),
    Index('idx_behavioral_skills_status', 'status'),
    Index('idx_behavioral_skills_type', 'skill_type'),
)

ams_trajectories = Table(
    'ams_trajectories',
    metadata,
    Column('trajectory_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('conversation_id', String),
    Column('selected_skill_id', String),
    Column('context_bucket', String),
    Column('feedback_reward', Integer),
    Column('timestamp', TIMESTAMP(timezone=True), nullable=False),
    Column('archived', Boolean, default=False),
    Column('agency_context', String),
    Column('message_id', String),
    Column('turn_number', Integer),
    Column('user_input', String),
    Column('ai_response', String),
    Index('idx_trajectories_archived', 'archived'),
    Index('idx_trajectories_conversation', 'conversation_id'),
    Index('idx_trajectories_user', 'user_id'),
)

ams_behavioral_feedback = Table(
    'ams_behavioral_feedback',
    metadata,
    Column('feedback_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('message_id', String),
    Column('skill_id', String),
    Column('reward', Integer),
    Column('reason', String),
    Column('timestamp', String, nullable=False),
    Column('processed', Integer, default=0),
    Column('outcome', String),
    Column('execution_time_ms', Integer),
    Column('context_json', JSONB),
    Column('user_satisfaction', Float),
    Column('free_text', String),
    Index('idx_behavioral_feedback_processed', 'processed'),
    Index('idx_behavioral_feedback_skill', 'skill_id'),
)

# ============================================================================
# Scheduler Tables
# ============================================================================

scheduler_tasks = Table(
    'scheduler_tasks',
    metadata,
    Column('task_id', String, primary_key=True),
    Column('task_class', String, nullable=False),
    Column('schedule', String, nullable=False),
    Column('config', Text),
    Column('enabled', Boolean, default=True),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
)

scheduler_task_executions = Table(
    'scheduler_task_executions',
    metadata,
    Column('execution_id', String, primary_key=True),
    Column('task_id', String, ForeignKey('scheduler_tasks.task_id'), nullable=False),
    Column('status', String, nullable=False),
    Column('started_at', TIMESTAMP(timezone=True), nullable=False),
    Column('completed_at', TIMESTAMP(timezone=True)),
    Column('error_message', Text),
    Column('result_data', JSONB),
    Index('idx_scheduler_executions_task', 'task_id'),
    Index('idx_scheduler_executions_status', 'status'),
)

# ============================================================================
# Conversation Tables
# ============================================================================

conversation_initiations = Table(
    'conversation_initiations',
    metadata,
    Column('initiation_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('conversation_id', String, nullable=False),
    Column('trigger_source', String, nullable=False),
    Column('trigger_reason', String),
    Column('question', String),
    Column('context', String),
    Column('urgency', String, default='medium'),
    Column('expected_answer_type', String, default='text'),
    Column('initiated_at', TIMESTAMP(timezone=True), nullable=False),
    Column('resolved_at', TIMESTAMP(timezone=True)),
    Column('resolution_status', String, default='pending'),
    Column('user_response_time', Integer),
    Column('engagement_score', Float),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
    Index('idx_initiations_conversation_id', 'conversation_id'),
    Index('idx_initiations_initiated_at', 'initiated_at'),
    Index('idx_initiations_status', 'resolution_status'),
    Index('idx_initiations_user_id', 'user_id'),
)

# ============================================================================
# Agency Policy Tables
# ============================================================================

agency_policy_rules = Table(
    'agency_policy_rules',
    metadata,
    Column('rule_id', String, primary_key=True),
    Column('rule_name', String, nullable=False),
    Column('user_id', String),
    Column('target_type', String, nullable=False),
    Column('conditions', Text, nullable=False),
    Column('effect', String, nullable=False),
    Column('user_message_template', Text),
    Column('priority', Integer, default=50),
    Column('scope', String, nullable=False),
    Column('version', Integer, default=1),
    Column('active', Boolean, default=True),
    Column('created_at', Text, nullable=False),
    Column('updated_at', Text, nullable=False),
    Index('idx_policy_rules_user', 'user_id'),
)

# ============================================================================
# Emotion Tables
# ============================================================================

emotion_state = Table(
    'emotion_state',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', String, nullable=False, default='system'),
    Column('timestamp', String, nullable=False),
    Column('subjective_feeling', String, nullable=False),
    Column('mood_valence', Float, nullable=False),
    Column('mood_arousal', Float, nullable=False),
    Column('intensity', Float, nullable=False),
    Column('warmth', Float, nullable=False),
    Column('directness', Float, nullable=False),
    Column('formality', Float, nullable=False),
    Column('engagement', Float, nullable=False),
    Column('closeness', Float, nullable=False),
    Column('care_focus', Float, nullable=False),
    Column('updated_at', String),
)

emotion_history = Table(
    'emotion_history',
    metadata,
    Column('id', BigInteger, primary_key=True, autoincrement=True),
    Column('user_id', String, nullable=False, default='system'),
    Column('timestamp', String, nullable=False),
    Column('feeling', String, nullable=False),
    Column('valence', Float, nullable=False),
    Column('arousal', Float, nullable=False),
    Column('intensity', Float, nullable=False),
    Column('created_at', String),
    Index('idx_emotion_history_feeling', 'feeling'),
    Index('idx_emotion_history_user_time', 'user_id', 'timestamp'),
)

# ============================================================================
# System Tables
# ============================================================================

system_events = Table(
    'system_events',
    metadata,
    Column('id', BigInteger, primary_key=True, autoincrement=True),
    Column('timestamp', String, nullable=False),
    Column('topic', String, nullable=False),
    Column('source', String, nullable=False),
    Column('message_type', String, nullable=False),
    Column('message_id', String, nullable=False, unique=True),
    Column('priority', Integer, default=1),
    Column('correlation_id', String),
    Column('payload', LargeBinary),
    Column('metadata', JSONB),
    Column('created_at', TIMESTAMP(timezone=True)),
    Index('idx_events_correlation', 'correlation_id'),
    Index('idx_events_message_id', 'message_id'),
    Index('idx_events_source', 'source'),
    Index('idx_events_topic_timestamp', 'topic', 'timestamp'),
)

# ============================================================================
# Export all tables for easy import
# ============================================================================

__all__ = [
    'metadata',
    'user_profiles',
    'user_proactive_preferences',
    'auth_devices',
    'auth_sessions',
    'auth_user_credentials',
    'agency_events',
    'agency_events_log',
    'agency_followups',
    'agency_reflection_notes',
    'agency_reminders',
    'agency_goals',
    'agency_plans',
    'agency_lessons',
    'agency_policy_rules',
    'kg_nodes',
    'kg_edges',
    'ams_behavioral_skills',
    'ams_trajectories',
    'ams_behavioral_feedback',
    'scheduler_tasks',
    'scheduler_task_executions',
    'conversation_initiations',
    'emotion_state',
    'emotion_history',
    'system_events',
]
