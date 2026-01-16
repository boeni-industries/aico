-- AICO Postgres Core Schema
--
-- Auto-generated from shared/aico/data/schemas/schema.py
-- DO NOT EDIT MANUALLY - regenerate using generate_postgres_schema.py
--
-- Database: aico
-- Schema:   aico_core

CREATE SCHEMA IF NOT EXISTS aico_core;
SET search_path TO aico_core, public;

-- Tables created without foreign key constraints to avoid dependency ordering issues

CREATE TABLE IF NOT EXISTS agency_arbiter_adjustments (
                adjustment_key TEXT PRIMARY KEY,     -- e.g., "goal_type_learning", "priority_weight"
                adjustment_value DOUBLE PRECISION NOT NULL,      -- The adjusted value
                lesson_id TEXT NOT NULL,             -- Which lesson caused this adjustment
                user_id TEXT,                        -- NULL for global adjustments
                applied_at TIMESTAMPTZ NOT NULL,       -- When adjustment was applied
                confidence DOUBLE PRECISION NOT NULL,            -- Lesson confidence score
                active BOOLEAN DEFAULT TRUE,            -- 1=active, 0=disabled
                notes TEXT                          -- Optional explanation
            );

CREATE INDEX IF NOT EXISTS idx_arbiter_adjustments_active ON agency_arbiter_adjustments(active) WHERE active = TRUE;

CREATE INDEX IF NOT EXISTS idx_arbiter_adjustments_lesson ON agency_arbiter_adjustments(lesson_id);

CREATE INDEX IF NOT EXISTS idx_arbiter_adjustments_user ON agency_arbiter_adjustments(user_id, active);

CREATE TABLE IF NOT EXISTS agency_events (
                id BIGSERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                goal_id TEXT,
                plan_id TEXT,
                event_type TEXT NOT NULL,              -- decision, plan_update, trigger, error, metric
                source TEXT NOT NULL,                  -- which component emitted this event (engine, planner, arbiter, etc.)
                payload_json JSONB NOT NULL,            -- JSONB payload with structured details
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_agency_events_goal ON agency_events(goal_id);

CREATE INDEX IF NOT EXISTS idx_agency_events_type ON agency_events(event_type);

CREATE INDEX IF NOT EXISTS idx_agency_events_user_time ON agency_events(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS agency_events_log (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- goal_created, plan_generated, skill_executed, feedback_received, etc.
                event_category TEXT NOT NULL,  -- goal, plan, execution, feedback, curiosity, reflection, policy
                source_component TEXT NOT NULL,  -- planner, arbiter, curiosity_engine, reflection_engine, etc.
                entity_type TEXT,  -- goal, plan, skill, lesson, policy, etc.
                entity_id TEXT,
                event_data TEXT NOT NULL,  -- JSON: event-specific data
                workflow_trace_id TEXT,  -- For tracking related events
                parent_event_id TEXT,  -- For event hierarchies
                severity TEXT DEFAULT 'info',  -- debug, info, warning, error, critical
                created_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_events_log_category ON agency_events_log(event_category);

CREATE INDEX IF NOT EXISTS idx_events_log_created ON agency_events_log(created_at);

CREATE INDEX IF NOT EXISTS idx_events_log_entity ON agency_events_log(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_events_log_type ON agency_events_log(event_type, created_at);

CREATE INDEX IF NOT EXISTS idx_events_log_user ON agency_events_log(user_id);

CREATE TABLE IF NOT EXISTS "agency_execution_snapshots" (
                snapshot_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                snapshot_type TEXT NOT NULL,  -- pause, checkpoint, error
                state_data TEXT NOT NULL,  -- JSON: complete execution state
                created_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_execution_snapshots_execution ON "agency_execution_snapshots"(execution_id, created_at);

CREATE TABLE IF NOT EXISTS agency_followups (
                followup_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                goal_id TEXT,
                related_message_id TEXT,
                followup_type TEXT NOT NULL,  -- check_in, progress_update, completion_prompt, clarification
                content TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                delivered_at TEXT,
                user_response TEXT,
                response_sentiment DOUBLE PRECISION,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, delivered, responded, dismissed, expired
                priority INTEGER DEFAULT 50,
                policy_approved INTEGER DEFAULT 1,
                relationship_context TEXT,  -- JSON: relationship strength, interaction history
                values_alignment DOUBLE PRECISION,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_followups_goal ON agency_followups(goal_id);

CREATE INDEX IF NOT EXISTS idx_followups_scheduled ON agency_followups(scheduled_at, status);

CREATE INDEX IF NOT EXISTS idx_followups_status ON agency_followups(status);

CREATE INDEX IF NOT EXISTS idx_followups_user ON agency_followups(user_id);

CREATE TABLE IF NOT EXISTS "agency_goal_dependencies" (
                dependency_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,               -- Goal that has the dependency
                prerequisite_goal_id TEXT NOT NULL,  -- Goal that must be completed first
                dependency_type TEXT DEFAULT 'hard', -- hard, soft, suggested
                active BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                UNIQUE(goal_id, prerequisite_goal_id)
            );

CREATE INDEX IF NOT EXISTS idx_goal_deps_active ON "agency_goal_dependencies"(active);

CREATE INDEX IF NOT EXISTS idx_goal_deps_goal ON "agency_goal_dependencies"(goal_id);

CREATE INDEX IF NOT EXISTS idx_goal_deps_prereq ON "agency_goal_dependencies"(prerequisite_goal_id);

CREATE TABLE IF NOT EXISTS "agency_goal_outcomes" (
                outcome_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                arm_id TEXT,                         -- Which bandit arm was used
                outcome TEXT NOT NULL,               -- completed, abandoned, failed, timeout
                success INTEGER DEFAULT 0,           -- 1=success, 0=failure
                reward DOUBLE PRECISION,                         -- Calculated reward (0.0-1.0)
                completion_time_minutes INTEGER,
                user_satisfaction DOUBLE PRECISION,              -- Optional user feedback (0.0-1.0)
                metadata_json JSONB,
                created_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_goal_outcomes_arm ON "agency_goal_outcomes"(arm_id);

CREATE INDEX IF NOT EXISTS idx_goal_outcomes_created ON "agency_goal_outcomes"(created_at);

CREATE INDEX IF NOT EXISTS idx_goal_outcomes_goal ON "agency_goal_outcomes"(goal_id);

CREATE INDEX IF NOT EXISTS idx_goal_outcomes_success ON "agency_goal_outcomes"(success);

CREATE INDEX IF NOT EXISTS idx_goal_outcomes_user ON "agency_goal_outcomes"(user_id);

CREATE TABLE IF NOT EXISTS "agency_goal_skill_executions" (
            link_id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            execution_id TEXT NOT NULL,
            execution_order INTEGER,
            created_at TEXT NOT NULL
        );

CREATE INDEX IF NOT EXISTS idx_agency_goal_skill_executions_execution ON agency_goal_skill_executions(execution_id);

CREATE INDEX IF NOT EXISTS idx_agency_goal_skill_executions_goal ON agency_goal_skill_executions(goal_id);

CREATE TABLE IF NOT EXISTS agency_goals (
                goal_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                origin TEXT NOT NULL,              -- user, curiosity, hobby, maintenance, system
                goal_type TEXT NOT NULL,          -- high-level type label (e.g. project, habit, maintenance)
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, active, paused, completed, retired
                priority TEXT DEFAULT 'normal',          -- low, normal, high
                metadata_json JSONB,                      -- JSONB BYTEA for future extensions
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_agency_goals_origin ON agency_goals(origin);

CREATE INDEX IF NOT EXISTS idx_agency_goals_user_status ON agency_goals(user_id, status);

CREATE TABLE IF NOT EXISTS "agency_intention_set" (
                intention_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'proposed',  -- proposed, active, paused, dropped, completed
                arbiter_score DOUBLE PRECISION NOT NULL,       -- Computed score from arbiter
                priority_band TEXT NOT NULL,       -- urgent, normal, background
                reasons_json JSONB,                 -- JSONB array of reason codes/explanations
                activated_at TIMESTAMPTZ,
                deactivated_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_intention_set_goal ON "agency_intention_set"(goal_id);

CREATE INDEX IF NOT EXISTS idx_intention_set_priority ON "agency_intention_set"(priority_band, status);

CREATE INDEX IF NOT EXISTS idx_intention_set_user_status ON "agency_intention_set"(user_id, status);

CREATE TABLE IF NOT EXISTS agency_lessons (
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
                confidence DOUBLE PRECISION NOT NULL,       -- 0.0 to 1.0
                metrics_basis TEXT,             -- JSON: {time_span, sample_size, outcome_counts, etc.}
                -- Scope and status
                scope TEXT NOT NULL,            -- this_user, global_default
                status TEXT NOT NULL,           -- active, superseded, rejected
                superseded_by TEXT,             -- lesson_id that replaced this one
                -- Application tracking
                applied_at TIMESTAMPTZ,           -- When the lesson was applied
                applied_by TEXT,                -- Component that applied it (e.g., "self_reflection_engine")
                -- Provenance (what led to this lesson)
                source_reflection_run_id TEXT, -- ID of the reflection job that created this
                evidence_window_start TIMESTAMPTZ,
                evidence_window_end TIMESTAMPTZ,
                -- Links to related entities
                related_goal_ids TEXT,         -- JSONB array of goal_ids
                related_trajectory_ids TEXT,   -- JSONB array of trajectory_ids
                related_event_ids TEXT,        -- JSONB array of agency_event_ids
                -- Audit trail
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_agency_lessons_applied ON agency_lessons(applied_at) WHERE applied_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_agency_lessons_status ON agency_lessons(user_id, status) WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_agency_lessons_superseded ON agency_lessons(superseded_by);

CREATE INDEX IF NOT EXISTS idx_agency_lessons_target ON agency_lessons(target_kind, target_id);

CREATE INDEX IF NOT EXISTS idx_agency_lessons_time ON agency_lessons(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agency_lessons_user_type ON agency_lessons(user_id, lesson_type);

CREATE TABLE IF NOT EXISTS "agency_plan_executions" (
                execution_id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                goal_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                paused_at TEXT,
                cancelled_at TEXT,
                current_step_id TEXT,
                steps_completed INTEGER DEFAULT 0,
                steps_total INTEGER NOT NULL,
                progress_percentage DOUBLE PRECISION DEFAULT 0.0,
                execution_context TEXT,
                error_message TEXT,
                cancellation_reason TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_plan_executions_goal ON "agency_plan_executions"(goal_id);

CREATE INDEX IF NOT EXISTS idx_plan_executions_plan ON "agency_plan_executions"(plan_id);

CREATE INDEX IF NOT EXISTS idx_plan_executions_status ON "agency_plan_executions"(status, created_at);

CREATE INDEX IF NOT EXISTS idx_plan_executions_user ON "agency_plan_executions"(user_id, status);

CREATE TABLE IF NOT EXISTS agency_plans (
                plan_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                title TEXT,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'draft',    -- draft, active, completed, abandoned
                steps_json JSONB NOT NULL,
                metadata_json JSONB,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_agency_plans_goal_status ON agency_plans(goal_id, status);

CREATE TABLE IF NOT EXISTS agency_policy_rules (
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
                active BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_policy_rules_user ON agency_policy_rules(user_id);

CREATE TABLE IF NOT EXISTS agency_reflection_notes (
                note_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                related_goal_id TEXT,
                related_plan_id TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags_json JSONB,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_agency_reflection_goal ON agency_reflection_notes(related_goal_id);

CREATE INDEX IF NOT EXISTS idx_agency_reflection_user_time ON agency_reflection_notes(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS agency_reflection_runs (
                run_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                -- Run metadata
                run_type TEXT NOT NULL,        -- scheduled, triggered, manual
                trigger_reason TEXT,           -- sleep_phase, goal_completion, user_request, etc.
                -- Analysis scope
                analysis_window_start TIMESTAMPTZ NOT NULL,
                analysis_window_end TIMESTAMPTZ NOT NULL,
                -- Results
                lessons_generated INTEGER DEFAULT 0,
                lessons_applied INTEGER DEFAULT 0,
                -- Timing
                started_at TIMESTAMPTZ NOT NULL,
                completed_at TIMESTAMPTZ,
                duration_seconds DOUBLE PRECISION,
                -- Status
                status TEXT NOT NULL,          -- running, completed, failed
                error_message TEXT,
                -- Metadata
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_reflection_runs_status ON agency_reflection_runs(status) WHERE status = 'running';

CREATE INDEX IF NOT EXISTS idx_reflection_runs_user_time ON agency_reflection_runs(user_id, started_at DESC);

CREATE TABLE IF NOT EXISTS agency_reminders (
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
                urgency_score DOUBLE PRECISION DEFAULT 0.5,
                recurrence_rule TEXT,  -- JSON: frequency, interval, end_date
                cluster_id TEXT,  -- For grouping related reminders
                adaptation_data TEXT,  -- JSON: user response patterns, optimal timing
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_reminders_cluster ON agency_reminders(cluster_id);

CREATE INDEX IF NOT EXISTS idx_reminders_goal ON agency_reminders(goal_id);

CREATE INDEX IF NOT EXISTS idx_reminders_priority ON agency_reminders(priority, urgency_score);

CREATE INDEX IF NOT EXISTS idx_reminders_scheduled ON agency_reminders(scheduled_at, status);

CREATE INDEX IF NOT EXISTS idx_reminders_status ON agency_reminders(status);

CREATE INDEX IF NOT EXISTS idx_reminders_user ON agency_reminders(user_id);

CREATE TABLE IF NOT EXISTS agency_self_model (
                model_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                -- What this tracks
                entity_type TEXT NOT NULL,     -- skill, goal_type, interaction_pattern
                entity_id TEXT NOT NULL,       -- Specific skill_id, goal type name, etc.
                -- Performance metrics (JSON)
                performance_summary TEXT NOT NULL,  -- JSON: {success_rate, avg_duration, user_satisfaction, etc.}
                -- Temporal scope
                window_start TIMESTAMPTZ NOT NULL,
                window_end TIMESTAMPTZ NOT NULL,
                sample_size INTEGER NOT NULL,
                -- Confidence and freshness
                confidence DOUBLE PRECISION NOT NULL,
                last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                -- Metadata
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, entity_type, entity_id, window_start)
            );

CREATE INDEX IF NOT EXISTS idx_self_model_freshness ON agency_self_model(last_updated DESC);

CREATE INDEX IF NOT EXISTS idx_self_model_user_entity ON agency_self_model(user_id, entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_self_model_window ON agency_self_model(window_start, window_end);

CREATE TABLE IF NOT EXISTS agency_skill_gaps (
                gap_id TEXT PRIMARY KEY,
                step_description TEXT NOT NULL,
                llm_suggested_skills TEXT,           -- JSONB array of skill names suggested by LLM
                step_metadata TEXT,                  -- JSON: full step context (goal_id, plan_id, etc.)
                pattern_embedding TEXT,              -- JSON: 768-dim embedding for similarity matching
                frequency_count INTEGER DEFAULT 1,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                priority_score DOUBLE PRECISION DEFAULT 0.0,     -- frequency * goal_importance
                suggested_skill_spec TEXT,           -- Auto-generated skill requirements
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_skill_gaps_priority ON agency_skill_gaps(priority_score DESC);

CREATE INDEX IF NOT EXISTS idx_skill_gaps_frequency ON agency_skill_gaps(frequency_count DESC);

CREATE INDEX IF NOT EXISTS idx_skill_gaps_last_seen ON agency_skill_gaps(last_seen_at DESC);

CREATE TABLE IF NOT EXISTS "agency_skill_executions" (
                execution_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                message_id TEXT,
                goal_id TEXT,
                execution_time_ms INTEGER,
                outcome TEXT NOT NULL,
                error_message TEXT,
                context_json JSONB,
                created_at TEXT NOT NULL
            );

CREATE TABLE IF NOT EXISTS "agency_skill_learning_data" (
                skill_id TEXT PRIMARY KEY,
                dimension_vector TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_skill_learning_updated ON "agency_skill_learning_data"(updated_at);

CREATE TABLE IF NOT EXISTS "agency_step_executions" (
                step_execution_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                duration_ms INTEGER,
                skill_id TEXT,
                skill_invocation_id TEXT,
                input_data TEXT DEFAULT '{}',
                output_data TEXT DEFAULT '{}',
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                blocked_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_step_executions_execution ON "agency_step_executions"(execution_id, step_order);

CREATE INDEX IF NOT EXISTS idx_step_executions_skill ON "agency_step_executions"(skill_id);

CREATE INDEX IF NOT EXISTS idx_step_executions_status ON "agency_step_executions"(status);

CREATE TABLE IF NOT EXISTS "ams_behavioral_feedback" (
            feedback_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            message_id TEXT,
            skill_id TEXT,
            reward INTEGER,
            reason TEXT,
            timestamp TEXT NOT NULL,
            processed INTEGER DEFAULT 0,
            outcome TEXT,
            execution_time_ms INTEGER,
            context_json JSONB,
            user_satisfaction DOUBLE PRECISION,
            free_text TEXT
        );

CREATE INDEX IF NOT EXISTS idx_behavioral_feedback_processed ON ams_behavioral_feedback(processed);

CREATE INDEX IF NOT EXISTS idx_behavioral_feedback_skill ON ams_behavioral_feedback(skill_id);

CREATE INDEX IF NOT EXISTS idx_behavioral_feedback_user ON ams_behavioral_feedback(user_id);

CREATE TABLE IF NOT EXISTS "ams_behavioral_skills" (skill_id TEXT PRIMARY KEY, skill_name TEXT NOT NULL, skill_type TEXT NOT NULL, trigger_context TEXT NOT NULL, procedure_template TEXT NOT NULL, dimension_vector TEXT NOT NULL, supported_languages TEXT, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'active');

CREATE INDEX IF NOT EXISTS idx_behavioral_skills_status ON "ams_behavioral_skills"(status);

CREATE INDEX IF NOT EXISTS idx_behavioral_skills_type ON "ams_behavioral_skills"(skill_type);

CREATE TABLE IF NOT EXISTS ams_context_preference_vectors (
        user_id TEXT NOT NULL,
        context_bucket INTEGER NOT NULL CHECK(context_bucket BETWEEN 0 AND 99),
        dimensions TEXT NOT NULL,
        last_updated_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (user_id, context_bucket)
    );

CREATE INDEX IF NOT EXISTS idx_ams_context_preferences_user ON ams_context_preference_vectors(user_id);

CREATE INDEX IF NOT EXISTS idx_ams_context_preferences_updated ON ams_context_preference_vectors(last_updated_at DESC);

CREATE TABLE IF NOT EXISTS ams_context_skill_stats (
        user_id TEXT NOT NULL,
        context_bucket INTEGER NOT NULL CHECK(context_bucket BETWEEN 0 AND 99),
        skill_id TEXT NOT NULL,
        alpha DOUBLE PRECISION NOT NULL DEFAULT 1.0 CHECK(alpha >= 0.0),
        beta DOUBLE PRECISION NOT NULL DEFAULT 1.0 CHECK(beta >= 0.0),
        last_updated_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (user_id, context_bucket, skill_id)
    );

CREATE INDEX IF NOT EXISTS idx_ams_context_skill_stats_user ON ams_context_skill_stats(user_id, context_bucket);

CREATE INDEX IF NOT EXISTS idx_ams_context_skill_stats_skill ON ams_context_skill_stats(skill_id);

CREATE TABLE IF NOT EXISTS "ams_consolidation_state" (
                id TEXT PRIMARY KEY,
                state_json JSONB NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_consolidation_state_updated ON "ams_consolidation_state"(updated_at DESC);

CREATE TABLE IF NOT EXISTS "ams_trajectories" (
            trajectory_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            conversation_id TEXT,
            selected_skill_id TEXT,
            context_bucket TEXT,
            feedback_reward INTEGER,
            timestamp TIMESTAMPTZ NOT NULL,
            archived BOOLEAN DEFAULT FALSE,
            agency_context TEXT,
            message_id TEXT,
            turn_number INTEGER,
            user_input TEXT,
            ai_response TEXT
        );

CREATE INDEX IF NOT EXISTS idx_trajectories_archived ON ams_trajectories(archived);

CREATE INDEX IF NOT EXISTS idx_trajectories_conversation ON ams_trajectories(conversation_id);

CREATE INDEX IF NOT EXISTS idx_trajectories_user ON ams_trajectories(user_id);

CREATE TABLE IF NOT EXISTS "ams_user_memories" (
                fact_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                fact_type TEXT NOT NULL,  -- identity, preference, relationship, temporal
                category TEXT NOT NULL,   -- personal_info, preferences, relationships
                confidence DOUBLE PRECISION NOT NULL,
                is_immutable BOOLEAN NOT NULL DEFAULT FALSE,
                -- Temporal validity
                valid_from TIMESTAMPTZ NOT NULL,
                valid_until TIMESTAMPTZ,
                -- Content and extraction
                content TEXT NOT NULL,
                entities_json JSONB,  -- JSONB array of extracted entities
                extraction_method TEXT NOT NULL,
                -- Provenance
                source_conversation_id TEXT NOT NULL,
                source_message_id TEXT,
                -- Timestamps
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, user_note TEXT, tags_json JSONB, is_favorite BOOLEAN DEFAULT FALSE, revisit_count INTEGER DEFAULT 0, last_revisited TIMESTAMPTZ, emotional_tone TEXT, memory_type TEXT, content_type TEXT DEFAULT 'message', conversation_title TEXT, conversation_summary TEXT, turn_range TEXT, key_moments_json JSONB, temporal_metadata TEXT DEFAULT NULL, language TEXT
            );

CREATE INDEX IF NOT EXISTS idx_facts_category ON "ams_user_memories"(category);

CREATE INDEX IF NOT EXISTS idx_facts_confidence ON "ams_user_memories"(confidence);

CREATE INDEX IF NOT EXISTS idx_facts_content_type ON "ams_user_memories"(user_id, content_type) WHERE extraction_method = 'user_curated';

CREATE INDEX IF NOT EXISTS idx_facts_favorite ON "ams_user_memories"(user_id, is_favorite) WHERE is_favorite = TRUE;

CREATE INDEX IF NOT EXISTS idx_facts_immutable ON "ams_user_memories"(is_immutable);

CREATE INDEX IF NOT EXISTS idx_facts_source ON "ams_user_memories"(source_conversation_id);

CREATE INDEX IF NOT EXISTS idx_facts_user_curated ON "ams_user_memories"(user_id, extraction_method) WHERE extraction_method = 'user_curated';

CREATE INDEX IF NOT EXISTS idx_facts_user_type ON "ams_user_memories"(user_id, fact_type);

CREATE INDEX IF NOT EXISTS idx_facts_validity ON "ams_user_memories"(valid_from, valid_until);

CREATE TABLE IF NOT EXISTS arbiter_ab_tests (
                test_id TEXT PRIMARY KEY,
                test_name TEXT NOT NULL,
                arm_a_id TEXT NOT NULL,
                arm_b_id TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT DEFAULT 'active',        -- active, completed, cancelled
                winner_arm_id TEXT,
                confidence_score DOUBLE PRECISION,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            );

CREATE INDEX IF NOT EXISTS idx_ab_tests_dates ON arbiter_ab_tests(start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_ab_tests_status ON arbiter_ab_tests(status);

CREATE TABLE IF NOT EXISTS arbiter_bandit_arms (
    arm_id TEXT PRIMARY KEY,
    weights_json JSONB NOT NULL,
    pulls INTEGER DEFAULT 0,
    total_reward DOUBLE PRECISION DEFAULT 0.0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_pulled TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bandit_arms_active ON arbiter_bandit_arms(active);

CREATE INDEX IF NOT EXISTS idx_bandit_arms_pulls ON arbiter_bandit_arms(pulls);

CREATE TABLE IF NOT EXISTS "auth_access_policies" (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_uuid TEXT,
                permission TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_access_policies_resource ON "auth_access_policies"(resource_type, resource_uuid);

CREATE INDEX IF NOT EXISTS idx_access_policies_user ON "auth_access_policies"(user_uuid);

CREATE TABLE IF NOT EXISTS "auth_devices" (
                uuid TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                device_type TEXT NOT NULL,
                platform TEXT NOT NULL,
                last_seen TIMESTAMPTZ,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_devices_active ON "auth_devices"(is_active);

CREATE TABLE IF NOT EXISTS auth_sessions (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                device_uuid TEXT NOT NULL,
                jwt_token_hash TEXT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE, session_type TEXT DEFAULT 'unified'
            );

CREATE INDEX IF NOT EXISTS idx_auth_sessions_active ON auth_sessions(is_active, expires_at);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_uuid);

CREATE TABLE IF NOT EXISTS "auth_user_credentials" (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                pin_hash TEXT NOT NULL,
                failed_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMPTZ,
                last_login TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_user_authentication_locked_until ON "auth_user_credentials"(locked_until);

CREATE INDEX IF NOT EXISTS idx_user_authentication_pin_hash ON "auth_user_credentials"(pin_hash);

CREATE INDEX IF NOT EXISTS idx_user_authentication_user ON "auth_user_credentials"(user_uuid);

CREATE TABLE IF NOT EXISTS consent_audit_log (
                audit_id TEXT PRIMARY KEY,
                consent_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,  -- granted, revoked, expired, inherited
                reason TEXT,
                metadata TEXT,  -- JSON: additional context
                created_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_consent_audit_consent ON consent_audit_log(consent_id);

CREATE INDEX IF NOT EXISTS idx_consent_audit_created ON consent_audit_log(created_at);

CREATE INDEX IF NOT EXISTS idx_consent_audit_user ON consent_audit_log(user_id);

CREATE TABLE IF NOT EXISTS "consent_records" (
                consent_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                consent_scope TEXT NOT NULL,       -- JSONB object describing what was consented to
                decision TEXT NOT NULL,            -- granted, denied
                context_json JSONB,                 -- Optional context (goal_id, plan_id, etc.)
                granted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMPTZ              -- NULL = permanent
            );

CREATE INDEX IF NOT EXISTS idx_consents_expires ON "consent_records"(expires_at);

CREATE INDEX IF NOT EXISTS idx_consents_user_scope ON "consent_records"(user_id, consent_scope);

CREATE TABLE IF NOT EXISTS "consent_user_consents" (
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
                updated_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_consents_scope ON "consent_user_consents"(scope, scope_identifier);

CREATE INDEX IF NOT EXISTS idx_consents_type ON "consent_user_consents"(consent_type, granted);

CREATE INDEX IF NOT EXISTS idx_consents_user ON "consent_user_consents"(user_id);

CREATE TABLE IF NOT EXISTS "conversation_initiations" (
                initiation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                trigger_source TEXT NOT NULL,
                trigger_reason TEXT,
                question TEXT,
                context TEXT,
                urgency TEXT DEFAULT 'medium',
                expected_answer_type TEXT DEFAULT 'text',
                initiated_at TIMESTAMPTZ NOT NULL,
                resolved_at TIMESTAMPTZ,
                resolution_status TEXT DEFAULT 'pending',
                user_response_time INTEGER,
                engagement_score DOUBLE PRECISION,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_initiations_conversation_id ON "conversation_initiations"(conversation_id);

CREATE INDEX IF NOT EXISTS idx_initiations_initiated_at ON "conversation_initiations"(initiated_at);

CREATE INDEX IF NOT EXISTS idx_initiations_status ON "conversation_initiations"(resolution_status);

CREATE INDEX IF NOT EXISTS idx_initiations_user_id ON "conversation_initiations"(user_id);

CREATE TABLE IF NOT EXISTS emotion_history (
                id BIGSERIAL PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'system',
                timestamp TEXT NOT NULL,
                feeling TEXT NOT NULL,
                valence DOUBLE PRECISION NOT NULL,
                arousal DOUBLE PRECISION NOT NULL,
                intensity DOUBLE PRECISION NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_emotion_history_feeling ON emotion_history(feeling);

CREATE INDEX IF NOT EXISTS idx_emotion_history_user_time ON emotion_history(user_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS emotion_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                user_id TEXT NOT NULL DEFAULT 'system',
                timestamp TEXT NOT NULL,
                subjective_feeling TEXT NOT NULL,
                mood_valence DOUBLE PRECISION NOT NULL,
                mood_arousal DOUBLE PRECISION NOT NULL,
                intensity DOUBLE PRECISION NOT NULL,
                warmth DOUBLE PRECISION NOT NULL,
                directness DOUBLE PRECISION NOT NULL,
                formality DOUBLE PRECISION NOT NULL,
                engagement DOUBLE PRECISION NOT NULL,
                closeness DOUBLE PRECISION NOT NULL,
                care_focus DOUBLE PRECISION NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS ethics_decisions_cache (
                cache_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                decision TEXT NOT NULL,  -- approved, blocked, needs_review
                reasoning TEXT,
                policy_rules_applied TEXT,  -- JSON: list of rule_ids applied
                confidence DOUBLE PRECISION DEFAULT 1.0,
                cached_at TEXT NOT NULL,
                expires_at TEXT,
                hit_count INTEGER DEFAULT 0,
                last_hit_at TEXT
            );

CREATE INDEX IF NOT EXISTS idx_ethics_cache_expires ON ethics_decisions_cache(expires_at);

CREATE INDEX IF NOT EXISTS idx_ethics_cache_target ON ethics_decisions_cache(target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_ethics_cache_user ON ethics_decisions_cache(user_id);

CREATE TABLE IF NOT EXISTS ethics_gate_audit (
                audit_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                reasoning TEXT,
                policy_rules_applied TEXT,  -- JSONB
                check_level INTEGER DEFAULT 1,  -- 1 = basic, 2 = detailed, 3 = comprehensive
                cached INTEGER DEFAULT 0,
                processing_time_ms INTEGER,
                created_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_ethics_audit_created ON ethics_gate_audit(created_at);

CREATE INDEX IF NOT EXISTS idx_ethics_audit_decision ON ethics_gate_audit(decision);

CREATE INDEX IF NOT EXISTS idx_ethics_audit_target ON ethics_gate_audit(target_type);

CREATE INDEX IF NOT EXISTS idx_ethics_audit_user ON ethics_gate_audit(user_id);

CREATE TABLE IF NOT EXISTS "ethics_policy_rules" (
                rule_id TEXT PRIMARY KEY,
                rule_name TEXT NOT NULL,
                target_type TEXT NOT NULL,         -- goal, plan, skill, curiosity_signal, world_model_update
                conditions_json JSONB NOT NULL,     -- JSONB object with predicates
                effect TEXT NOT NULL,              -- allow, allow_with_warning, needs_consent, block
                user_message_template TEXT,        -- Optional NL explanation
                priority INTEGER DEFAULT 100,      -- Lower = higher priority
                enabled BOOLEAN DEFAULT TRUE,
                scope TEXT DEFAULT 'global',       -- global, deployment, user
                scope_id TEXT,                     -- NULL for global, user_id for user-specific
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_policy_rules_scope ON "ethics_policy_rules"(scope, scope_id);

CREATE INDEX IF NOT EXISTS idx_policy_rules_target ON "ethics_policy_rules"(target_type, enabled);

CREATE TABLE IF NOT EXISTS "ethics_value_profiles" (
                profile_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                sensitive_life_areas TEXT,         -- JSONB array of LifeArea IDs
                allowed_curiosity_domains TEXT,    -- JSONB array of allowed domains
                curiosity_intensity DOUBLE PRECISION DEFAULT 0.5,  -- 0.0-1.0 scale
                proactive_behavior_level TEXT DEFAULT 'balanced',  -- quiet, balanced, proactive
                storage_preferences TEXT,          -- JSONB object with storage rules
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_value_profiles_user ON "ethics_value_profiles"(user_id);

CREATE TABLE IF NOT EXISTS kg_edge_properties (
                edge_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (edge_id, key, value)
            );

CREATE INDEX IF NOT EXISTS idx_kg_edge_properties_kv ON kg_edge_properties(key, value);

CREATE TABLE IF NOT EXISTS kg_edges (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                properties TEXT,
                confidence DOUBLE PRECISION,
                source_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                valid_from TEXT,
                valid_until TEXT,
                is_current BOOLEAN DEFAULT TRUE,
                reason TEXT,
                UNIQUE(user_id, source_id, target_id, relation_type, is_current)
            );

CREATE INDEX IF NOT EXISTS idx_kg_edges_relation_user ON kg_edges(user_id, relation_type, is_current);

CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON kg_edges(source_id);

CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON kg_edges(target_id);

CREATE INDEX IF NOT EXISTS idx_kg_edges_temporal ON kg_edges(user_id, is_current, valid_from);

CREATE INDEX IF NOT EXISTS idx_kg_edges_user_relation ON kg_edges(user_id, relation_type);

CREATE INDEX IF NOT EXISTS idx_kg_edges_reason ON kg_edges(reason) WHERE reason IS NOT NULL;

CREATE TABLE IF NOT EXISTS kg_node_properties (
                node_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (node_id, key, value)
            );

CREATE INDEX IF NOT EXISTS idx_kg_node_properties_kv ON kg_node_properties(key, value);

CREATE TABLE IF NOT EXISTS kg_nodes (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                label TEXT NOT NULL,
                properties JSONB NOT NULL,
                confidence DOUBLE PRECISION NOT NULL,
                source_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                valid_from TEXT,
                valid_until TEXT,
                is_current BOOLEAN DEFAULT TRUE,
                canonical_id TEXT,
                aliases_json JSONB,
                language TEXT,
                reason TEXT,
                UNIQUE(user_id, label, properties, is_current)
            );

CREATE INDEX IF NOT EXISTS idx_kg_nodes_canonical ON kg_nodes(canonical_id);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_label_user ON kg_nodes(user_id, label, is_current);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_temporal ON kg_nodes(user_id, is_current, valid_from);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_user_created ON kg_nodes(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_user_label ON kg_nodes(user_id, label);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_reason ON kg_nodes(reason) WHERE reason IS NOT NULL;

CREATE TABLE IF NOT EXISTS proactive_analytics (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                confidence_score DOUBLE PRECISION,
                triggered_action TEXT,
                created_at TIMESTAMPTZ NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_proactive_analytics_user ON proactive_analytics(user_id);

CREATE INDEX IF NOT EXISTS idx_proactive_analytics_type ON proactive_analytics(event_type);

CREATE TABLE IF NOT EXISTS "proactive_reminder_clusters" (
                cluster_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                cluster_name TEXT NOT NULL,
                reminder_ids TEXT,
                pattern_description TEXT,
                confidence_score DOUBLE PRECISION,
                created_at TIMESTAMPTZ NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_reminder_clusters_user ON "proactive_reminder_clusters"(user_id);

CREATE TABLE IF NOT EXISTS "scheduler_task_executions" (
                id BIGSERIAL PRIMARY KEY,
                task_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMPTZ NOT NULL,
                completed_at TIMESTAMPTZ,
                result TEXT,  -- JSONB TaskResult
                error_message TEXT,
                duration_seconds DOUBLE PRECISION,
                acknowledged BOOLEAN DEFAULT FALSE
            );

CREATE INDEX IF NOT EXISTS idx_task_executions_started_at ON "scheduler_task_executions" (started_at);

CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON "scheduler_task_executions" (task_id);

CREATE INDEX IF NOT EXISTS idx_task_executions_acknowledged ON "scheduler_task_executions" (status, acknowledged) WHERE status = 'failed' AND acknowledged = FALSE;

CREATE TABLE IF NOT EXISTS "scheduler_tasks" (
                task_id TEXT PRIMARY KEY,
                task_class TEXT NOT NULL,
                schedule TEXT NOT NULL,
                config TEXT,  -- JSONB configuration
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS "system_event_metrics" (
                metric_id TEXT PRIMARY KEY,
                metric_name TEXT NOT NULL,
                metric_type TEXT NOT NULL,  -- counter, gauge, histogram, summary
                event_type TEXT,
                event_category TEXT,
                time_bucket TEXT NOT NULL,  -- hourly, daily, weekly
                bucket_start TEXT NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                count INTEGER DEFAULT 1,
                metadata TEXT,  -- JSONB
                created_at TEXT NOT NULL,
                UNIQUE(metric_name, event_type, time_bucket, bucket_start)
            );

CREATE INDEX IF NOT EXISTS idx_event_metrics_bucket ON "system_event_metrics"(time_bucket, bucket_start);

CREATE INDEX IF NOT EXISTS idx_event_metrics_name ON "system_event_metrics"(metric_name, bucket_start);

CREATE INDEX IF NOT EXISTS idx_event_metrics_type ON "system_event_metrics"(event_type, bucket_start);

CREATE TABLE IF NOT EXISTS "system_event_replay_sessions" (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                replay_name TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                event_filters TEXT,  -- JSON: filters applied
                replay_speed DOUBLE PRECISION DEFAULT 1.0,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
                events_replayed INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                created_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_replay_sessions_status ON "system_event_replay_sessions"(status);

CREATE INDEX IF NOT EXISTS idx_replay_sessions_user ON "system_event_replay_sessions"(user_id);

CREATE TABLE IF NOT EXISTS "system_events" (
                id BIGSERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                topic TEXT NOT NULL,
                source TEXT NOT NULL,
                message_type TEXT NOT NULL,
                message_id TEXT NOT NULL UNIQUE,
                priority INTEGER DEFAULT 1,
                correlation_id TEXT,
                payload BYTEA,
                metadata JSONB,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE INDEX IF NOT EXISTS idx_events_correlation ON "system_events"(correlation_id) WHERE correlation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_events_message_id ON "system_events"(message_id);

CREATE INDEX IF NOT EXISTS idx_events_source ON "system_events"(source);

CREATE INDEX IF NOT EXISTS idx_events_topic_timestamp ON "system_events"(topic, timestamp);

CREATE TABLE IF NOT EXISTS "user_feedback_requests" (
            request_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            goal_id TEXT,
            skill_id TEXT,
            execution_id TEXT,
            feedback_type TEXT NOT NULL,
            question TEXT NOT NULL,
            response TEXT,
            rating DOUBLE PRECISION,
            responded_at TEXT,
            created_at TEXT NOT NULL
        );

CREATE INDEX IF NOT EXISTS idx_feedback_requests_responded ON user_feedback_requests(responded_at);

CREATE INDEX IF NOT EXISTS idx_feedback_requests_user ON user_feedback_requests(user_id);

CREATE TABLE IF NOT EXISTS user_proactive_preferences (
                user_id TEXT PRIMARY KEY,
                followup_enabled BOOLEAN DEFAULT TRUE,
                reminder_enabled BOOLEAN DEFAULT TRUE,
                preferred_followup_times TEXT,  -- JSON: array of preferred hours
                preferred_reminder_times TEXT,  -- JSON: array of preferred hours
                max_followups_per_day INTEGER DEFAULT 3,
                max_reminders_per_day INTEGER DEFAULT 5,
                min_hours_between_followups INTEGER DEFAULT 4,
                min_hours_between_reminders INTEGER DEFAULT 2,
                cluster_reminders INTEGER DEFAULT 1,
                auto_snooze_duration_minutes INTEGER DEFAULT 60,
                updated_at TEXT NOT NULL
            );

CREATE TABLE IF NOT EXISTS "user_profiles" (
                uuid TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                nickname TEXT,
                user_type TEXT DEFAULT 'person',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            , primary_language TEXT);

CREATE INDEX IF NOT EXISTS idx_users_active ON "user_profiles"(is_active);

CREATE INDEX IF NOT EXISTS idx_users_user_type ON "user_profiles"(user_type);

CREATE TABLE IF NOT EXISTS user_relationships (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                related_user_uuid TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_uuid, related_user_uuid, relationship_type)
            );

CREATE INDEX IF NOT EXISTS idx_user_relationships_related ON user_relationships(related_user_uuid);

CREATE INDEX IF NOT EXISTS idx_user_relationships_user ON user_relationships(user_uuid);

CREATE TABLE IF NOT EXISTS "user_skill_confidence" (
            user_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            confidence_score DOUBLE PRECISION DEFAULT 0.5 CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            usage_count INTEGER DEFAULT 0,
            positive_count INTEGER DEFAULT 0,
            negative_count INTEGER DEFAULT 0,
            last_used_at TIMESTAMPTZ,
            PRIMARY KEY (user_id, skill_id)
        );

CREATE INDEX IF NOT EXISTS idx_user_skill_confidence ON user_skill_confidence(user_id, confidence_score DESC);

CREATE TABLE IF NOT EXISTS workflow_executions (
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
                updated_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status);

CREATE INDEX IF NOT EXISTS idx_workflow_executions_type ON workflow_executions(workflow_type, status);

CREATE INDEX IF NOT EXISTS idx_workflow_executions_user ON workflow_executions(user_id);

CREATE TABLE IF NOT EXISTS workflow_stages (
                stage_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                stage_order INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, skipped
                started_at TEXT,
                completed_at TEXT,
                input_data TEXT,  -- JSONB
                output_data TEXT,  -- JSONB
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

CREATE INDEX IF NOT EXISTS idx_workflow_stages_execution ON workflow_stages(execution_id, stage_order);

CREATE INDEX IF NOT EXISTS idx_workflow_stages_status ON workflow_stages(status);

CREATE TABLE IF NOT EXISTS user_time_preferences (
                preference_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                time_period TEXT NOT NULL,  -- early_morning, morning, afternoon, evening, night
                productivity_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,  -- 0.0-2.0, relative productivity
                active BOOLEAN DEFAULT TRUE,  -- 1=active, 0=disabled
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, time_period)
            );

CREATE INDEX IF NOT EXISTS idx_user_time_preferences_user ON user_time_preferences(user_id, active);

CREATE INDEX IF NOT EXISTS idx_user_time_preferences_active ON user_time_preferences(active) WHERE active = TRUE;


-- Foreign key constraints added after all tables are created

ALTER TABLE agency_arbiter_adjustments
    ADD CONSTRAINT fk_agency_arbiter_adjustments_lesson_id_agency_lessons
    FOREIGN KEY (lesson_id) REFERENCES agency_lessons(lesson_id) ON DELETE CASCADE;
ALTER TABLE agency_events ADD CONSTRAINT fk_agency_events_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_events ADD CONSTRAINT fk_agency_events_goal_id_agency_goals FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL;
ALTER TABLE agency_events ADD CONSTRAINT fk_agency_events_plan_id_agency_plans FOREIGN KEY (plan_id) REFERENCES agency_plans(plan_id) ON DELETE SET NULL;
ALTER TABLE agency_events_log ADD CONSTRAINT fk_agency_events_log_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_events_log ADD CONSTRAINT fk_agency_events_log_parent_event_id_agency_events_log FOREIGN KEY (parent_event_id) REFERENCES agency_events_log(event_id) ON DELETE SET NULL;
ALTER TABLE agency_execution_snapshots ADD CONSTRAINT fk_agency_execution_snapshots_execution_id_agency_plan_executions FOREIGN KEY (execution_id) REFERENCES agency_plan_executions(execution_id) ON DELETE CASCADE;
ALTER TABLE agency_followups ADD CONSTRAINT fk_agency_followups_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_followups ADD CONSTRAINT fk_agency_followups_goal_id_agency_goals FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL;
ALTER TABLE agency_goal_dependencies ADD CONSTRAINT fk_agency_goal_dependencies_goal_id_agency_goals FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id);
ALTER TABLE agency_goal_dependencies ADD CONSTRAINT fk_agency_goal_dependencies_prerequisite_goal_id_agency_goals FOREIGN KEY (prerequisite_goal_id) REFERENCES agency_goals(goal_id);
ALTER TABLE agency_goal_outcomes ADD CONSTRAINT fk_agency_goal_outcomes_goal_id_agency_goals FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id);
ALTER TABLE agency_goal_outcomes ADD CONSTRAINT fk_agency_goal_outcomes_arm_id_arbiter_bandit_arms FOREIGN KEY (arm_id) REFERENCES arbiter_bandit_arms(arm_id);
ALTER TABLE agency_goal_skill_executions ADD CONSTRAINT fk_agency_goal_skill_executions_goal_id_agency_goals FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE CASCADE;
ALTER TABLE agency_goals ADD CONSTRAINT fk_agency_goals_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_intention_set ADD CONSTRAINT fk_agency_intention_set_goal_id_agency_goals FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE CASCADE;
ALTER TABLE agency_intention_set ADD CONSTRAINT fk_agency_intention_set_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_lessons ADD CONSTRAINT fk_agency_lessons_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_lessons ADD CONSTRAINT fk_agency_lessons_superseded_by_agency_lessons FOREIGN KEY (superseded_by) REFERENCES agency_lessons(lesson_id) ON DELETE SET NULL;
ALTER TABLE agency_plans ADD CONSTRAINT fk_agency_plans_goal_id_agency_goals FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE CASCADE;
ALTER TABLE agency_policy_rules ADD CONSTRAINT fk_agency_policy_rules_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_reflection_notes ADD CONSTRAINT fk_agency_reflection_notes_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_reflection_notes ADD CONSTRAINT fk_agency_reflection_notes_related_goal_id_agency_goals FOREIGN KEY (related_goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL;
ALTER TABLE agency_reflection_notes ADD CONSTRAINT fk_agency_reflection_notes_related_plan_id_agency_plans FOREIGN KEY (related_plan_id) REFERENCES agency_plans(plan_id) ON DELETE SET NULL;
ALTER TABLE agency_reflection_runs ADD CONSTRAINT fk_agency_reflection_runs_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_reminders ADD CONSTRAINT fk_agency_reminders_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_reminders ADD CONSTRAINT fk_agency_reminders_goal_id_agency_goals FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL;
ALTER TABLE agency_self_model ADD CONSTRAINT fk_agency_self_model_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_skill_executions ADD CONSTRAINT fk_agency_skill_executions_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE agency_skill_executions ADD CONSTRAINT fk_agency_skill_executions_goal_id_agency_goals FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL;
ALTER TABLE agency_step_executions ADD CONSTRAINT fk_agency_step_executions_execution_id_agency_plan_executions FOREIGN KEY (execution_id) REFERENCES agency_plan_executions(execution_id) ON DELETE CASCADE;
ALTER TABLE ams_behavioral_feedback ADD CONSTRAINT fk_ams_behavioral_feedback_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE ams_context_preference_vectors ADD CONSTRAINT fk_ams_context_preference_vectors_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE ams_context_skill_stats ADD CONSTRAINT fk_ams_context_skill_stats_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE ams_context_skill_stats ADD CONSTRAINT fk_ams_context_skill_stats_skill_id_ams_behavioral_skills FOREIGN KEY (skill_id) REFERENCES ams_behavioral_skills(skill_id) ON DELETE CASCADE;
ALTER TABLE ams_trajectories ADD CONSTRAINT fk_ams_trajectories_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE ams_user_memories ADD CONSTRAINT fk_ams_user_memories_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE arbiter_ab_tests ADD CONSTRAINT fk_arbiter_ab_tests_arm_a_id_arbiter_bandit_arms FOREIGN KEY (arm_a_id) REFERENCES arbiter_bandit_arms(arm_id);
ALTER TABLE arbiter_ab_tests ADD CONSTRAINT fk_arbiter_ab_tests_arm_b_id_arbiter_bandit_arms FOREIGN KEY (arm_b_id) REFERENCES arbiter_bandit_arms(arm_id);
ALTER TABLE auth_access_policies ADD CONSTRAINT fk_auth_access_policies_user_uuid_user_profiles FOREIGN KEY (user_uuid) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE auth_sessions ADD CONSTRAINT fk_auth_sessions_user_uuid_user_profiles FOREIGN KEY (user_uuid) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE auth_user_credentials ADD CONSTRAINT fk_auth_user_credentials_user_uuid_user_profiles FOREIGN KEY (user_uuid) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE consent_audit_log ADD CONSTRAINT fk_consent_audit_log_consent_id_consent_user_consents FOREIGN KEY (consent_id) REFERENCES consent_user_consents(consent_id) ON DELETE CASCADE;
ALTER TABLE consent_audit_log ADD CONSTRAINT fk_consent_audit_log_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE consent_records ADD CONSTRAINT fk_consent_records_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE consent_user_consents ADD CONSTRAINT fk_consent_user_consents_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE consent_user_consents ADD CONSTRAINT fk_consent_user_consents_inherited_from_consent_user_consents FOREIGN KEY (inherited_from) REFERENCES consent_user_consents(consent_id) ON DELETE SET NULL;
ALTER TABLE conversation_initiations ADD CONSTRAINT fk_conversation_initiations_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE ethics_decisions_cache ADD CONSTRAINT fk_ethics_decisions_cache_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE ethics_gate_audit ADD CONSTRAINT fk_ethics_gate_audit_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE ethics_value_profiles ADD CONSTRAINT fk_ethics_value_profiles_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE kg_edge_properties ADD CONSTRAINT fk_kg_edge_properties_edge_id_kg_edges FOREIGN KEY (edge_id) REFERENCES kg_edges(id) ON DELETE CASCADE;
ALTER TABLE kg_edges ADD CONSTRAINT fk_kg_edges_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE kg_edges ADD CONSTRAINT fk_kg_edges_source_id_kg_nodes FOREIGN KEY (source_id) REFERENCES kg_nodes(id) ON DELETE CASCADE;
ALTER TABLE kg_edges ADD CONSTRAINT fk_kg_edges_target_id_kg_nodes FOREIGN KEY (target_id) REFERENCES kg_nodes(id) ON DELETE CASCADE;
ALTER TABLE kg_node_properties ADD CONSTRAINT fk_kg_node_properties_node_id_kg_nodes FOREIGN KEY (node_id) REFERENCES kg_nodes(id) ON DELETE CASCADE;
ALTER TABLE kg_nodes ADD CONSTRAINT fk_kg_nodes_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE proactive_analytics ADD CONSTRAINT fk_proactive_analytics_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE proactive_reminder_clusters ADD CONSTRAINT fk_proactive_reminder_clusters_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE scheduler_task_executions ADD CONSTRAINT fk_scheduler_task_executions_task_id_scheduler_tasks FOREIGN KEY (task_id) REFERENCES scheduler_tasks(task_id);
ALTER TABLE system_event_replay_sessions ADD CONSTRAINT fk_system_event_replay_sessions_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE user_feedback_requests ADD CONSTRAINT fk_user_feedback_requests_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE user_feedback_requests ADD CONSTRAINT fk_user_feedback_requests_goal_id_agency_goals FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL;
ALTER TABLE user_proactive_preferences ADD CONSTRAINT fk_user_proactive_preferences_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE user_relationships ADD CONSTRAINT fk_user_relationships_user_uuid_user_profiles FOREIGN KEY (user_uuid) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE user_relationships ADD CONSTRAINT fk_user_relationships_related_user_uuid_user_profiles FOREIGN KEY (related_user_uuid) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE user_skill_confidence ADD CONSTRAINT fk_user_skill_confidence_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE workflow_executions ADD CONSTRAINT fk_workflow_executions_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
ALTER TABLE workflow_stages ADD CONSTRAINT fk_workflow_stages_execution_id_workflow_executions FOREIGN KEY (execution_id) REFERENCES workflow_executions(execution_id) ON DELETE CASCADE;
ALTER TABLE user_time_preferences ADD CONSTRAINT fk_user_time_preferences_user_id_user_profiles FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE;
-- Immutable wrapper functions for JSONB extraction (required for functional indexes)
CREATE OR REPLACE FUNCTION jsonb_extract_text_immutable(data TEXT, path TEXT)
RETURNS TEXT AS $$
BEGIN
  RETURN (data::jsonb)->>path;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION jsonb_extract_timestamptz_immutable(data TEXT, path TEXT)
RETURNS TIMESTAMPTZ AS $$
BEGIN
  RETURN ((data::jsonb)->>path)::timestamptz;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION jsonb_extract_double_immutable(data TEXT, path TEXT)
RETURNS DOUBLE PRECISION AS $$
BEGIN
  RETURN ((data::jsonb)->>path)::double precision;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- PostgreSQL-compatible indexes for ams_user_memories JSON fields
-- These replace the 2 skipped json_extract() indexes from SQLite

CREATE INDEX IF NOT EXISTS idx_user_memories_superseded 
  ON ams_user_memories(jsonb_extract_text_immutable(temporal_metadata, 'superseded_by'))
  WHERE temporal_metadata IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_memories_temporal 
  ON ams_user_memories(
    jsonb_extract_timestamptz_immutable(temporal_metadata, 'last_accessed'),
    jsonb_extract_double_immutable(temporal_metadata, 'confidence')
  )
  WHERE temporal_metadata IS NOT NULL;
