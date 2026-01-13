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
    Column('session_token', String, nullable=False),
    Column('device_id', String),
    Column('device_name', String),
    Column('ip_address', String),
    Column('user_agent', String),
    Column('is_active', Boolean, nullable=False, default=True),
    Column('expires_at', TIMESTAMP(timezone=True), nullable=False),
    Column('last_activity_at', TIMESTAMP(timezone=True)),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_auth_sessions_token', 'session_token', unique=True),
    Index('idx_auth_sessions_user', 'user_uuid', 'is_active'),
)

auth_user_credentials = Table(
    'auth_user_credentials',
    metadata,
    Column('uuid', String, primary_key=True),
    Column('user_uuid', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('pin_hash', String, nullable=False),
    Column('failed_attempts', Integer, nullable=False, default=0),
    Column('locked_until', TIMESTAMP(timezone=True)),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_auth_credentials_user', 'user_uuid', unique=True),
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
    Column('user_id', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('context_hash', String, nullable=False),
    Column('action_taken', String, nullable=False),
    Column('outcome', String, nullable=False),
    Column('reward', Float, nullable=False),
    Column('context_data', JSONB, nullable=False),
    Column('metadata_json', JSONB),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_ams_trajectories_user', 'user_id'),
    Index('idx_ams_trajectories_context', 'context_hash'),
)

ams_behavioral_feedback = Table(
    'ams_behavioral_feedback',
    metadata,
    Column('feedback_id', String, primary_key=True),
    Column('user_id', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('trajectory_id', String),
    Column('feedback_type', String, nullable=False),
    Column('feedback_value', Float, nullable=False),
    Column('context_data', JSONB),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_ams_feedback_user', 'user_id'),
    Index('idx_ams_feedback_trajectory', 'trajectory_id'),
)

# ============================================================================
# Scheduler Tables
# ============================================================================

scheduler_tasks = Table(
    'scheduler_tasks',
    metadata,
    Column('task_id', String, primary_key=True),
    Column('task_name', String, nullable=False),
    Column('task_type', String, nullable=False),
    Column('schedule_expression', String, nullable=False),
    Column('enabled', Boolean, nullable=False, default=True),
    Column('last_run_at', TIMESTAMP(timezone=True)),
    Column('next_run_at', TIMESTAMP(timezone=True)),
    Column('metadata_json', JSONB),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_scheduler_tasks_enabled', 'enabled'),
    Index('idx_scheduler_tasks_next_run', 'next_run_at'),
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
    'kg_nodes',
    'kg_edges',
    'ams_trajectories',
    'ams_behavioral_feedback',
    'scheduler_tasks',
    'scheduler_task_executions',
]
