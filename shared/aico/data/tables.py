"""
SQLAlchemy Core Table Definitions

Maps PostgreSQL schema to SQLAlchemy Table objects for type-safe query building.
These tables mirror the schema in shared/aico/data/postgres/schema.sql
"""

from sqlalchemy import (
    Table, Column, MetaData,
    String, Integer, BigInteger, Boolean, Float, Text,
    ForeignKey, Index, JSON, LargeBinary, PrimaryKeyConstraint, UniqueConstraint,
    func
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

# MetaData instance - all tables will be registered here
metadata = MetaData(schema="aico_core")

# ============================================================================
# User & Authentication Tables
# ============================================================================

auth_access_policies = Table(
    'auth_access_policies',
    metadata,
    Column('uuid', String, primary_key=True),
    Column('user_uuid', String, nullable=False),
    Column('resource_type', String, nullable=False),
    Column('resource_uuid', String),
    Column('permission', String, nullable=False),
    Column('is_active', Boolean, default=True),
    Column('created_at', TIMESTAMP(timezone=True)),
    Index('idx_access_policies_resource', 'resource_type', 'resource_uuid'),
    Index('idx_access_policies_user', 'user_uuid'),
)

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

user_feedback_requests = Table(
    'user_feedback_requests',
    metadata,
    Column('request_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('goal_id', String),
    Column('skill_id', String),
    Column('execution_id', String),
    Column('feedback_type', String, nullable=False),
    Column('question', String, nullable=False),
    Column('response', String),
    Column('rating', Float),
    Column('responded_at', String),
    Column('created_at', String, nullable=False),
    Index('idx_feedback_requests_responded', 'responded_at'),
    Index('idx_feedback_requests_user', 'user_id'),
)

user_relationships = Table(
    'user_relationships',
    metadata,
    Column('uuid', String, primary_key=True),
    Column('user_uuid', String, nullable=False),
    Column('related_user_uuid', String, nullable=False),
    Column('relationship_type', String, nullable=False),
    Column('is_active', Boolean, default=True),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
    Index('idx_user_relationships_related', 'related_user_uuid'),
    Index('idx_user_relationships_user', 'user_uuid'),
)

user_skill_confidence = Table(
    'user_skill_confidence',
    metadata,
    Column('user_id', String, nullable=False),
    Column('skill_id', String, nullable=False),
    Column('confidence_score', Float, default=0.5),
    Column('usage_count', Integer, default=0),
    Column('positive_count', Integer, default=0),
    Column('negative_count', Integer, default=0),
    Column('last_used_at', TIMESTAMP(timezone=True)),
    Index('idx_user_skill_confidence', 'user_id', 'confidence_score'),
)

user_time_preferences = Table(
    'user_time_preferences',
    metadata,
    Column('preference_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('time_period', String, nullable=False),
    Column('productivity_score', Float, nullable=False, default=1.0),
    Column('active', Boolean, default=True),
    Column('created_at', String, nullable=False),
    Column('updated_at', String, nullable=False),
    Index('idx_user_time_preferences_user', 'user_id', 'active'),
    Index('idx_user_time_preferences_active', 'active'),
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
# Agency Tables
# ============================================================================

agency_arbiter_adjustments = Table(
    'agency_arbiter_adjustments',
    metadata,
    Column('adjustment_key', String, primary_key=True),
    Column('adjustment_value', Float, nullable=False),
    Column('lesson_id', String, nullable=False),
    Column('user_id', String),
    Column('applied_at', TIMESTAMP(timezone=True), nullable=False),
    Column('confidence', Float, nullable=False),
    Column('active', Boolean, default=True),
    Column('notes', String),
    Index('idx_arbiter_adjustments_active', 'active'),
    Index('idx_arbiter_adjustments_lesson', 'lesson_id'),
    Index('idx_arbiter_adjustments_user', 'user_id', 'active'),
)

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

agency_execution_snapshots = Table(
    'agency_execution_snapshots',
    metadata,
    Column('snapshot_id', String, primary_key=True),
    Column('execution_id', String, nullable=False),
    Column('snapshot_type', String, nullable=False),
    Column('state_data', String, nullable=False),
    Column('created_at', String, nullable=False),
    Index('idx_execution_snapshots_execution', 'execution_id', 'created_at'),
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

agency_goal_dependencies = Table(
    'agency_goal_dependencies',
    metadata,
    Column('dependency_id', String, primary_key=True),
    Column('goal_id', String, nullable=False),
    Column('prerequisite_goal_id', String, nullable=False),
    Column('dependency_type', String, server_default='hard'),
    Column('active', Boolean, server_default='true'),
    Column('created_at', String, nullable=False),
    UniqueConstraint('goal_id', 'prerequisite_goal_id'),
    Index('idx_goal_deps_active', 'active'),
    Index('idx_goal_deps_goal', 'goal_id'),
    Index('idx_goal_deps_prereq', 'prerequisite_goal_id'),
)

agency_goal_outcomes = Table(
    'agency_goal_outcomes',
    metadata,
    Column('outcome_id', String, primary_key=True),
    Column('goal_id', String, nullable=False),
    Column('user_id', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('arm_id', String),
    Column('outcome', String, nullable=False),
    Column('success', Integer, server_default='0'),
    Column('reward', Float),
    Column('completion_time_minutes', Integer),
    Column('user_satisfaction', Float),
    Column('metadata_json', JSONB),
    Column('created_at', String, nullable=False),
    Index('idx_goal_outcomes_arm', 'arm_id'),
    Index('idx_goal_outcomes_created', 'created_at'),
    Index('idx_goal_outcomes_goal', 'goal_id'),
    Index('idx_goal_outcomes_success', 'success'),
    Index('idx_goal_outcomes_user', 'user_id'),
)

agency_goal_skill_executions = Table(
    'agency_goal_skill_executions',
    metadata,
    Column('link_id', String, primary_key=True),
    Column('goal_id', String, nullable=False),
    Column('skill_id', String, nullable=False),
    Column('execution_id', String, nullable=False),
    Column('execution_order', Integer),
    Column('created_at', String, nullable=False),
    Index('idx_agency_goal_skill_executions_execution', 'execution_id'),
    Index('idx_agency_goal_skill_executions_goal', 'goal_id'),
)

agency_reflection_notes = Table(
    'agency_reflection_notes',
    metadata,
    Column('note_id', String, primary_key=True),
    Column('user_id', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('related_goal_id', String),
    Column('related_plan_id', String),
    Column('title', String, nullable=False),
    Column('content', String, nullable=False),
    Column('tags_json', JSONB),
    Column('created_at', TIMESTAMP(timezone=True), server_default=func.now()),
    Column('updated_at', TIMESTAMP(timezone=True), server_default=func.now()),
    Index('idx_agency_reflection_user_time', 'user_id', 'created_at'),
)

agency_reflection_runs = Table(
    'agency_reflection_runs',
    metadata,
    Column('run_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('run_type', String, nullable=False),
    Column('trigger_reason', String),
    Column('analysis_window_start', TIMESTAMP(timezone=True), nullable=False),
    Column('analysis_window_end', TIMESTAMP(timezone=True), nullable=False),
    Column('lessons_generated', Integer, server_default='0'),
    Column('lessons_applied', Integer, server_default='0'),
    Column('started_at', TIMESTAMP(timezone=True), nullable=False),
    Column('completed_at', TIMESTAMP(timezone=True)),
    Column('duration_seconds', Float),
    Column('status', String, nullable=False),
    Column('error_message', String),
    Column('created_at', TIMESTAMP(timezone=True), server_default=func.now()),
    Index('idx_reflection_runs_status', 'status'),
    Index('idx_reflection_runs_user_time', 'user_id', 'started_at'),
)

agency_self_model = Table(
    'agency_self_model',
    metadata,
    Column('model_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('entity_type', String, nullable=False),
    Column('entity_id', String, nullable=False),
    Column('performance_summary', String, nullable=False),
    Column('window_start', TIMESTAMP(timezone=True), nullable=False),
    Column('window_end', TIMESTAMP(timezone=True), nullable=False),
    Column('sample_size', Integer, nullable=False),
    Column('confidence', Float, nullable=False),
    Column('last_updated', TIMESTAMP(timezone=True), server_default=func.now()),
    Column('created_at', TIMESTAMP(timezone=True), server_default=func.now()),
    UniqueConstraint('user_id', 'entity_type', 'entity_id', 'window_start'),
    Index('idx_self_model_freshness', 'last_updated'),
    Index('idx_self_model_user_entity', 'user_id', 'entity_type', 'entity_id'),
    Index('idx_self_model_window', 'window_start', 'window_end'),
)

agency_skill_gaps = Table(
    'agency_skill_gaps',
    metadata,
    Column('gap_id', String, primary_key=True),
    Column('step_description', String, nullable=False),
    Column('llm_suggested_skills', String),
    Column('step_metadata', String),
    Column('pattern_embedding', String),
    Column('frequency_count', Integer, server_default='1'),
    Column('first_seen_at', String, nullable=False),
    Column('last_seen_at', String, nullable=False),
    Column('priority_score', Float, server_default='0.0'),
    Column('suggested_skill_spec', String),
    Column('notes', String),
    Column('created_at', String, nullable=False),
    Column('updated_at', String, nullable=False),
    Index('idx_skill_gaps_priority', 'priority_score'),
    Index('idx_skill_gaps_frequency', 'frequency_count'),
    Index('idx_skill_gaps_last_seen', 'last_seen_at'),
)

agency_skill_executions = Table(
    'agency_skill_executions',
    metadata,
    Column('execution_id', String, primary_key=True),
    Column('skill_id', String, nullable=False),
    Column('user_id', String, nullable=False),
    Column('message_id', String),
    Column('goal_id', String),
    Column('execution_time_ms', Integer),
    Column('outcome', String, nullable=False),
    Column('error_message', String),
    Column('context_json', JSONB),
    Column('created_at', String, nullable=False),
)

agency_skill_learning_data = Table(
    'agency_skill_learning_data',
    metadata,
    Column('skill_id', String, primary_key=True),
    Column('dimension_vector', String, nullable=False),
    Column('created_at', String, nullable=False),
    Column('updated_at', String, nullable=False),
    Index('idx_skill_learning_updated', 'updated_at'),
)

agency_step_executions = Table(
    'agency_step_executions',
    metadata,
    Column('step_execution_id', String, primary_key=True),
    Column('execution_id', String, nullable=False),
    Column('step_id', String, nullable=False),
    Column('step_order', Integer, nullable=False),
    Column('status', String, nullable=False, server_default='pending'),
    Column('started_at', String),
    Column('completed_at', String),
    Column('duration_ms', Integer),
    Column('skill_id', String),
    Column('skill_invocation_id', String),
    Column('input_data', String, server_default='{}'),
    Column('output_data', String, server_default='{}'),
    Column('error_message', String),
    Column('retry_count', Integer, server_default='0'),
    Column('blocked_reason', String),
    Column('created_at', String, nullable=False),
    Column('updated_at', String, nullable=False),
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

agency_intention_set = Table(
    'agency_intention_set',
    metadata,
    Column('intention_id', String, primary_key=True),
    Column('goal_id', String, nullable=False),
    Column('user_id', String, nullable=False),
    Column('status', String, nullable=False, server_default='proposed'),
    Column('arbiter_score', Float, nullable=False),
    Column('priority_band', String, nullable=False),
    Column('reasons_json', JSONB),
    Column('activated_at', TIMESTAMP(timezone=True)),
    Column('deactivated_at', TIMESTAMP(timezone=True)),
    Column('created_at', TIMESTAMP(timezone=True), server_default=func.now()),
    Column('updated_at', TIMESTAMP(timezone=True), server_default=func.now()),
    Index('idx_intention_set_goal', 'goal_id'),
    Index('idx_intention_set_priority', 'priority_band', 'status'),
    Index('idx_intention_set_user_status', 'user_id', 'status'),
)

agency_plans = Table(
    'agency_plans',
    metadata,
    Column('plan_id', String, primary_key=True),
    Column('goal_id', String, nullable=False),
    Column('title', String),
    Column('description', String),
    Column('steps_json', JSONB, nullable=False),
    Column('status', String, nullable=False, server_default='draft'),
    Column('metadata_json', JSONB),
    Column('created_at', TIMESTAMP(timezone=True), server_default=func.now()),
    Column('updated_at', TIMESTAMP(timezone=True), server_default=func.now()),
    Index('idx_agency_plans_goal', 'goal_id'),
    Index('idx_agency_plans_status', 'status'),
)

agency_plan_executions = Table(
    'agency_plan_executions',
    metadata,
    Column('execution_id', String, primary_key=True),
    Column('plan_id', String, nullable=False),
    Column('goal_id', String, nullable=False),
    Column('user_id', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('status', String, nullable=False, server_default='pending'),
    Column('started_at', String),
    Column('completed_at', String),
    Column('paused_at', String),
    Column('cancelled_at', String),
    Column('current_step_id', String),
    Column('steps_completed', Integer, server_default='0'),
    Column('steps_total', Integer, nullable=False),
    Column('progress_percentage', Float, server_default='0.0'),
    Column('execution_context', String),
    Column('error_message', String),
    Column('cancellation_reason', String),
    Column('retry_count', Integer, server_default='0'),
    Column('created_at', String, nullable=False),
    Column('updated_at', String, nullable=False),
    Index('idx_plan_executions_goal', 'goal_id'),
    Index('idx_plan_executions_plan', 'plan_id'),
    Index('idx_plan_executions_status', 'status', 'created_at'),
    Index('idx_plan_executions_user', 'user_id', 'status'),
)

agency_lessons = Table(
    'agency_lessons',
    metadata,
    Column('lesson_id', String, primary_key=True),
    Column('user_id', String, ForeignKey('user_profiles.uuid', ondelete='CASCADE'), nullable=False),
    Column('lesson_type', String, nullable=False),
    Column('target_kind', String, nullable=False),
    Column('target_id', String),
    Column('summary_text', Text, nullable=False),
    Column('proposed_change', Text, nullable=False),
    Column('confidence', Float, nullable=False),
    Column('metrics_basis', Text),
    Column('scope', String, nullable=False),
    Column('status', String, nullable=False),
    Column('superseded_by', String, ForeignKey('agency_lessons.lesson_id', ondelete='SET NULL')),
    Column('applied_at', TIMESTAMP(timezone=True)),
    Column('applied_by', String),
    Column('source_reflection_run_id', String),
    Column('evidence_window_start', TIMESTAMP(timezone=True)),
    Column('evidence_window_end', TIMESTAMP(timezone=True)),
    Column('related_goal_ids', Text),
    Column('related_trajectory_ids', Text),
    Column('related_event_ids', Text),
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
    Column('reason', String),
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
    Column('reason', String),
    Index('idx_kg_edges_user', 'user_id'),
    Index('idx_kg_edges_source', 'source_id'),
    Index('idx_kg_edges_target', 'target_id'),
    Index('idx_kg_edges_relation', 'relation_type'),
    Index('idx_kg_edges_current', 'is_current'),
)

# ============================================================================
# Proactive System Tables
# ============================================================================

proactive_analytics = Table(
    'proactive_analytics',
    metadata,
    Column('id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('event_type', String, nullable=False),
    Column('event_data', String),
    Column('confidence_score', Float),
    Column('triggered_action', String),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_proactive_analytics_user', 'user_id'),
    Index('idx_proactive_analytics_type', 'event_type'),
)

proactive_reminder_clusters = Table(
    'proactive_reminder_clusters',
    metadata,
    Column('cluster_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('cluster_name', String, nullable=False),
    Column('reminder_ids', String),
    Column('pattern_description', String),
    Column('confidence_score', Float),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_proactive_clusters_user', 'user_id'),
)

# ============================================================================
# Workflow Tables
# ============================================================================

workflow_executions = Table(
    'workflow_executions',
    metadata,
    Column('execution_id', String, primary_key=True),
    Column('workflow_type', String, nullable=False),
    Column('user_id', String, nullable=False),
    Column('status', String, nullable=False),
    Column('started_at', String, nullable=False),
    Column('completed_at', String),
    Column('current_stage', String),
    Column('total_stages', Integer),
    Column('metadata', String),
    Column('error_message', String),
    Column('created_at', String, nullable=False),
    Column('updated_at', String, nullable=False),
    Index('idx_workflow_executions_status', 'status'),
    Index('idx_workflow_executions_type', 'workflow_type', 'status'),
    Index('idx_workflow_executions_user', 'user_id'),
)

workflow_stages = Table(
    'workflow_stages',
    metadata,
    Column('stage_id', String, primary_key=True),
    Column('execution_id', String, nullable=False),
    Column('stage_name', String, nullable=False),
    Column('stage_order', Integer, nullable=False),
    Column('status', String, nullable=False),
    Column('started_at', String),
    Column('completed_at', String),
    Column('input_data', String),
    Column('output_data', String),
    Column('error_message', String),
    Column('retry_count', Integer, default=0),
    Column('created_at', String, nullable=False),
    Index('idx_workflow_stages_execution', 'execution_id', 'stage_order'),
)

# ============================================================================
# System Event Metrics Tables
# ============================================================================

system_event_metrics = Table(
    'system_event_metrics',
    metadata,
    Column('metric_id', String, primary_key=True),
    Column('metric_name', String, nullable=False),
    Column('metric_type', String, nullable=False),
    Column('event_type', String),
    Column('event_category', String),
    Column('time_bucket', String, nullable=False),
    Column('bucket_start', String, nullable=False),
    Column('value', Float, nullable=False),
    Column('count', Integer, default=1),
    Column('metadata', String),
    Column('created_at', String, nullable=False),
    Index('idx_event_metrics_bucket', 'time_bucket', 'bucket_start'),
    Index('idx_event_metrics_name', 'metric_name', 'bucket_start'),
    Index('idx_event_metrics_type', 'event_type', 'bucket_start'),
)

system_event_replay_sessions = Table(
    'system_event_replay_sessions',
    metadata,
    Column('session_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('replay_name', String),
    Column('start_time', String, nullable=False),
    Column('end_time', String, nullable=False),
    Column('event_filters', String),
    Column('replay_speed', Float, default=1.0),
    Column('status', String, nullable=False),
    Column('started_at', String, nullable=False),
    Column('events_replayed', Integer, default=0),
    Column('completed_at', String),
    Column('created_at', String, nullable=False),
    Index('idx_replay_sessions_user', 'user_id'),
    Index('idx_replay_sessions_status', 'status'),
)

# ============================================================================
# AMS Tables
# ============================================================================

ams_context_preference_vectors = Table(
    'ams_context_preference_vectors',
    metadata,
    Column('user_id', String, nullable=False),
    Column('context_bucket', Integer, nullable=False),
    Column('dimensions', String, nullable=False),
    Column('last_updated_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_ams_context_preferences_user', 'user_id'),
    Index('idx_ams_context_preferences_updated', 'last_updated_at'),
)

ams_context_skill_stats = Table(
    'ams_context_skill_stats',
    metadata,
    Column('user_id', String, nullable=False),
    Column('context_bucket', Integer, nullable=False),
    Column('skill_id', String, nullable=False),
    Column('alpha', Float, nullable=False, default=1.0),
    Column('beta', Float, nullable=False, default=1.0),
    Column('last_updated_at', TIMESTAMP(timezone=True), nullable=False),
    Index('idx_ams_context_skill_stats_user', 'user_id', 'context_bucket'),
)

ams_consolidation_state = Table(
    'ams_consolidation_state',
    metadata,
    Column('id', String, primary_key=True),
    Column('state_json', JSONB, nullable=False),
    Column('updated_at', TIMESTAMP(timezone=True)),
    Index('idx_consolidation_state_updated', 'updated_at'),
)

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
)

ams_user_memories = Table(
    'ams_user_memories',
    metadata,
    Column('fact_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('fact_type', String, nullable=False),
    Column('category', String, nullable=False),
    Column('confidence', Float, nullable=False),
    Column('is_immutable', Boolean, nullable=False, default=False),
    Column('valid_from', TIMESTAMP(timezone=True), nullable=False),
    Column('valid_until', TIMESTAMP(timezone=True)),
    Column('content', String, nullable=False),
    Column('entities_json', JSONB),
    Column('extraction_method', String, nullable=False),
    Column('source_conversation_id', String, nullable=False),
    Column('source_message_id', String),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
    Column('user_note', String),
    Column('tags_json', JSONB),
    Column('is_favorite', Boolean, default=False),
    Column('revisit_count', Integer, default=0),
    Column('last_revisited', TIMESTAMP(timezone=True)),
    Column('emotional_tone', String),
    Column('memory_type', String),
    Column('content_type', String, default='message'),
    Column('conversation_title', String),
    Column('conversation_summary', String),
    Column('turn_range', String),
    Column('key_moments_json', JSONB),
    Column('temporal_metadata', String),
    Column('language', String),
    Index('idx_facts_category', 'category'),
    Index('idx_facts_confidence', 'confidence'),
    Index('idx_facts_content_type', 'user_id', 'content_type'),
    Index('idx_facts_favorite', 'user_id', 'is_favorite'),
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
    Column('timestamp', TIMESTAMP(timezone=True), nullable=False),
    Column('processed', Integer, default=0),
    Column('outcome', String),
    Column('execution_time_ms', Integer),
    Column('context_json', JSONB),
    Column('user_satisfaction', Float),
    Column('free_text', String),
    Index('idx_behavioral_feedback_processed', 'processed'),
    Index('idx_behavioral_feedback_skill', 'skill_id'),
    Index('idx_behavioral_feedback_user', 'user_id'),
)

# ============================================================================
# Arbiter Tables
# ============================================================================

arbiter_ab_tests = Table(
    'arbiter_ab_tests',
    metadata,
    Column('test_id', String, primary_key=True),
    Column('test_name', String, nullable=False),
    Column('arm_a_id', String, nullable=False),
    Column('arm_b_id', String, nullable=False),
    Column('start_date', String, nullable=False),
    Column('end_date', String, nullable=False),
    Column('status', String, default='active'),
    Column('winner_arm_id', String),
    Column('confidence_score', Float),
    Column('notes', String),
    Column('created_at', String, nullable=False),
    Column('updated_at', String),
    Index('idx_ab_tests_dates', 'start_date', 'end_date'),
    Index('idx_ab_tests_status', 'status'),
)

arbiter_bandit_arms = Table(
    'arbiter_bandit_arms',
    metadata,
    Column('arm_id', String, primary_key=True),
    Column('weights_json', JSONB, nullable=False),
    Column('pulls', Integer, default=0),
    Column('total_reward', Float, default=0.0),
    Column('success_count', Integer, default=0),
    Column('failure_count', Integer, default=0),
    Column('last_pulled', String),
    Column('active', Boolean, default=True),
    Column('created_at', String, nullable=False),
    Column('updated_at', String, nullable=False),
    Index('idx_bandit_arms_active', 'active'),
    Index('idx_bandit_arms_pulls', 'pulls'),
)

# ============================================================================
# Consent Tables
# ============================================================================

consent_user_consents = Table(
    'consent_user_consents',
    metadata,
    Column('consent_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('consent_type', String, nullable=False),
    Column('scope', String, nullable=False),
    Column('scope_identifier', String),
    Column('granted', Integer, nullable=False),
    Column('expires_at', String),
    Column('inherited_from', String),
    Column('granted_at', String, nullable=False),
    Column('revoked_at', String),
    Column('created_at', String, nullable=False),
    Column('updated_at', String, nullable=False),
    Index('idx_consents_scope', 'scope', 'scope_identifier'),
    Index('idx_consents_type', 'consent_type', 'granted'),
    Index('idx_consents_user', 'user_id'),
)

consent_records = Table(
    'consent_records',
    metadata,
    Column('consent_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('consent_scope', String, nullable=False),
    Column('decision', String, nullable=False),
    Column('context_json', JSONB),
    Column('granted_at', TIMESTAMP(timezone=True)),
    Column('expires_at', TIMESTAMP(timezone=True)),
    Index('idx_consents_expires', 'expires_at'),
    Index('idx_consents_user_scope', 'user_id', 'consent_scope'),
)

consent_audit_log = Table(
    'consent_audit_log',
    metadata,
    Column('audit_id', String, primary_key=True),
    Column('consent_id', String, nullable=False),
    Column('user_id', String, nullable=False),
    Column('action', String, nullable=False),
    Column('reason', String),
    Column('metadata', String),
    Column('created_at', String, nullable=False),
    Index('idx_consent_audit_consent', 'consent_id'),
    Index('idx_consent_audit_created', 'created_at'),
    Index('idx_consent_audit_user', 'user_id'),
)

# ============================================================================
# Ethics Tables
# ============================================================================

ethics_decisions_cache = Table(
    'ethics_decisions_cache',
    metadata,
    Column('cache_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('target_type', String, nullable=False),
    Column('target_id', String, nullable=False),
    Column('decision', String, nullable=False),
    Column('reasoning', String),
    Column('policy_rules_applied', String),
    Column('confidence', Float, default=1.0),
    Column('cached_at', String, nullable=False),
    Column('expires_at', String),
    Column('hit_count', Integer, default=0),
    Column('last_hit_at', String),
    Index('idx_ethics_cache_expires', 'expires_at'),
    Index('idx_ethics_cache_target', 'target_type', 'target_id'),
    Index('idx_ethics_cache_user', 'user_id'),
)

ethics_gate_audit = Table(
    'ethics_gate_audit',
    metadata,
    Column('audit_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('target_type', String, nullable=False),
    Column('target_id', String, nullable=False),
    Column('decision', String, nullable=False),
    Column('reasoning', String),
    Column('policy_rules_applied', String),
    Column('check_level', Integer, default=1),
    Column('cached', Integer, default=0),
    Column('processing_time_ms', Integer),
    Column('created_at', String, nullable=False),
    Index('idx_ethics_audit_created', 'created_at'),
    Index('idx_ethics_audit_decision', 'decision'),
    Index('idx_ethics_audit_target', 'target_type'),
    Index('idx_ethics_audit_user', 'user_id'),
)

ethics_policy_rules = Table(
    'ethics_policy_rules',
    metadata,
    Column('rule_id', String, primary_key=True),
    Column('rule_name', String, nullable=False),
    Column('target_type', String, nullable=False),
    Column('conditions_json', JSONB, nullable=False),
    Column('effect', String, nullable=False),
    Column('user_message_template', String),
    Column('priority', Integer, default=100),
    Column('enabled', Boolean, default=True),
    Column('scope', String, default='global'),
    Column('scope_id', String),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
    Index('idx_policy_rules_scope', 'scope', 'scope_id'),
    Index('idx_policy_rules_target', 'target_type', 'enabled'),
)

ethics_value_profiles = Table(
    'ethics_value_profiles',
    metadata,
    Column('profile_id', String, primary_key=True),
    Column('user_id', String, nullable=False, unique=True),
    Column('sensitive_life_areas', String),
    Column('allowed_curiosity_domains', String),
    Column('curiosity_intensity', Float, default=0.5),
    Column('autonomy_level', String, default='balanced'),
    Column('storage_preferences', String),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
    Index('idx_value_profiles_user', 'user_id'),
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
    Column('config', String),
    Column('enabled', Boolean, default=True),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
)

scheduler_task_executions = Table(
    'scheduler_task_executions',
    metadata,
    Column('id', BigInteger, primary_key=True, autoincrement=True),
    Column('task_id', String, nullable=False),
    Column('execution_id', String, nullable=False),
    Column('status', String, nullable=False),
    Column('started_at', TIMESTAMP(timezone=True), nullable=False),
    Column('completed_at', TIMESTAMP(timezone=True)),
    Column('result', String),
    Column('error_message', String),
    Column('duration_seconds', Float),
    Column('acknowledged', Boolean, default=False),
    Index('idx_task_executions_task_id', 'task_id'),
    Index('idx_task_executions_started_at', 'started_at'),
)

# ============================================================================
# Conversation Tables
# ============================================================================

interaction_requests = Table(
    'interaction_requests',
    metadata,
    Column('interaction_id', String, primary_key=True),
    Column('user_id', String, nullable=False),
    Column('correlation_id', String, nullable=False),
    Column('interaction_type', String, nullable=False),
    Column('requirement', String, nullable=False),
    Column('status', String, nullable=False),
    Column('category', String, nullable=False),
    Column('severity', String, nullable=False),
    Column('title', String),
    Column('prompt', String),
    Column('context_json', JSONB),
    Column('allowed_options', JSONB),
    Column('expected_answer_type', String),
    Column('answer_text', String),
    Column('answer_json', JSONB),
    Column('answered_at', TIMESTAMP(timezone=True)),
    Column('expires_at', TIMESTAMP(timezone=True)),
    Column('idempotency_key', String, nullable=False),
    Column('created_at', TIMESTAMP(timezone=True)),
    Column('updated_at', TIMESTAMP(timezone=True)),
    UniqueConstraint('user_id', 'idempotency_key', name='uq_interaction_requests_idempotency_key'),
    Index('idx_interaction_requests_user_status', 'user_id', 'status', 'created_at'),
    Index('idx_interaction_requests_correlation', 'correlation_id'),
    Index('idx_interaction_requests_expires', 'expires_at'),
)

interaction_events = Table(
    'interaction_events',
    metadata,
    Column('event_id', String, primary_key=True),
    Column('interaction_id', String, nullable=False),
    Column('user_id', String, nullable=False),
    Column('correlation_id', String, nullable=False),
    Column('actor', String, nullable=False),
    Column('event_type', String, nullable=False),
    Column('from_status', String),
    Column('to_status', String),
    Column('payload_json', JSONB),
    Column('created_at', TIMESTAMP(timezone=True)),
    Index('idx_interaction_events_interaction', 'interaction_id', 'created_at'),
    Index('idx_interaction_events_user_time', 'user_id', 'created_at'),
    Index('idx_interaction_events_correlation', 'correlation_id', 'created_at'),
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
    'user_feedback_requests',
    'user_relationships',
    'user_skill_confidence',
    'user_time_preferences',
    'auth_devices',
    'auth_sessions',
    'auth_user_credentials',
    'agency_arbiter_adjustments',
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
    'ams_consolidation_state',
    'ams_behavioral_skills',
    'ams_trajectories',
    'ams_user_memories',
    'ams_behavioral_feedback',
    'ams_context_preference_vectors',
    'ams_context_skill_stats',
    'arbiter_ab_tests',
    'arbiter_bandit_arms',
    'consent_user_consents',
    'consent_records',
    'consent_audit_log',
    'ethics_decisions_cache',
    'ethics_gate_audit',
    'ethics_policy_rules',
    'ethics_value_profiles',
    'scheduler_tasks',
    'scheduler_task_executions',
    'workflow_executions',
    'workflow_stages',
    'system_event_metrics',
    'system_event_replay_sessions',
    'interaction_requests',
    'interaction_events',
    'emotion_state',
    'emotion_history',
    'system_events',
]
