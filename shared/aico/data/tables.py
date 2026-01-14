"""
SQLAlchemy Core Table Definitions

Maps PostgreSQL schema to SQLAlchemy Table objects for type-safe query building.
These tables mirror the schema in shared/aico/data/postgres/schema.sql
"""

from sqlalchemy import (
    Table, Column, MetaData,
    String, Integer, BigInteger, Boolean, Float, DateTime, Text,
    ForeignKey, Index, JSON
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
# Agency System Tables (Core)
# ============================================================================

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
# Export all tables for easy import
# ============================================================================

__all__ = [
    'metadata',
    'user_profiles',
    'auth_sessions',
    'auth_user_credentials',
    'agency_goals',
    'agency_plans',
    'agency_lessons',
    'agency_policy_rules',
    'kg_nodes',
    'kg_edges',
    'ams_trajectories',
    'ams_behavioral_feedback',
    'scheduler_tasks',
    'scheduler_task_executions',
]
