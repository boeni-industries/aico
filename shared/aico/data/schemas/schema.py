"""
AICO Database Schema - v1 Clean

This is the ACTUAL production database schema.
Extracted directly from the production database.
DO NOT manually edit this file - regenerate from production DB.
"""

# Single source of truth for database schema
V1_SCHEMA = [
    """CREATE TABLE agency_arbiter_adjustments (
                adjustment_key TEXT PRIMARY KEY,     -- e.g., "goal_type_learning", "priority_weight"
                adjustment_value REAL NOT NULL,      -- The adjusted value
                lesson_id TEXT NOT NULL,             -- Which lesson caused this adjustment
                user_id TEXT,                        -- NULL for global adjustments
                applied_at TIMESTAMP NOT NULL,       -- When adjustment was applied
                confidence REAL NOT NULL,            -- Lesson confidence score
                active INTEGER DEFAULT 1,            -- 1=active, 0=disabled
                notes TEXT,                          -- Optional explanation
                
                FOREIGN KEY (lesson_id) REFERENCES agency_lessons(lesson_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_arbiter_adjustments_active ON agency_arbiter_adjustments(active) WHERE active = 1""",
    """CREATE INDEX idx_arbiter_adjustments_lesson ON agency_arbiter_adjustments(lesson_id)""",
    """CREATE INDEX idx_arbiter_adjustments_user ON agency_arbiter_adjustments(user_id, active)""",

    """CREATE TABLE agency_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                goal_id TEXT,
                plan_id TEXT,
                event_type TEXT NOT NULL,              -- decision, plan_update, trigger, error, metric
                source TEXT NOT NULL,                  -- which component emitted this event (engine, planner, arbiter, etc.)
                payload_json TEXT NOT NULL,            -- JSON payload with structured details
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL,
                FOREIGN KEY (plan_id) REFERENCES agency_plans(plan_id) ON DELETE SET NULL
            )""",

    """CREATE INDEX idx_agency_events_goal ON agency_events(goal_id)""",
    """CREATE INDEX idx_agency_events_type ON agency_events(event_type)""",
    """CREATE INDEX idx_agency_events_user_time ON agency_events(user_id, created_at DESC)""",

    """CREATE TABLE agency_events_log (
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
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (parent_event_id) REFERENCES agency_events_log(event_id) ON DELETE SET NULL
            )""",

    """CREATE INDEX idx_events_log_category ON agency_events_log(event_category)""",
    """CREATE INDEX idx_events_log_created ON agency_events_log(created_at)""",
    """CREATE INDEX idx_events_log_entity ON agency_events_log(entity_type, entity_id)""",
    """CREATE INDEX idx_events_log_type ON agency_events_log(event_type, created_at)""",
    """CREATE INDEX idx_events_log_user ON agency_events_log(user_id)""",

    """CREATE TABLE "agency_execution_snapshots" (
                snapshot_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                snapshot_type TEXT NOT NULL,  -- pause, checkpoint, error
                state_data TEXT NOT NULL,  -- JSON: complete execution state
                created_at TEXT NOT NULL,
                FOREIGN KEY (execution_id) REFERENCES "agency_plan_executions"(execution_id) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_execution_snapshots_execution ON "agency_execution_snapshots"(execution_id, created_at)""",

    """CREATE TABLE agency_followups (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL
            )""",

    """CREATE INDEX idx_followups_goal ON agency_followups(goal_id)""",
    """CREATE INDEX idx_followups_scheduled ON agency_followups(scheduled_at, status)""",
    """CREATE INDEX idx_followups_status ON agency_followups(status)""",
    """CREATE INDEX idx_followups_user ON agency_followups(user_id)""",

    """CREATE TABLE "agency_goal_dependencies" (
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

    """CREATE INDEX idx_goal_deps_active ON "agency_goal_dependencies"(active)""",
    """CREATE INDEX idx_goal_deps_goal ON "agency_goal_dependencies"(goal_id)""",
    """CREATE INDEX idx_goal_deps_prereq ON "agency_goal_dependencies"(prerequisite_goal_id)""",

    """CREATE TABLE "agency_goal_outcomes" (
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

    """CREATE INDEX idx_goal_outcomes_arm ON "agency_goal_outcomes"(arm_id)""",
    """CREATE INDEX idx_goal_outcomes_created ON "agency_goal_outcomes"(created_at)""",
    """CREATE INDEX idx_goal_outcomes_goal ON "agency_goal_outcomes"(goal_id)""",
    """CREATE INDEX idx_goal_outcomes_success ON "agency_goal_outcomes"(success)""",
    """CREATE INDEX idx_goal_outcomes_user ON "agency_goal_outcomes"(user_id)""",

    """CREATE TABLE "agency_goal_skill_executions" (
            link_id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            execution_id TEXT NOT NULL,
            execution_order INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE CASCADE
        )""",

    """CREATE INDEX idx_agency_goal_skill_executions_execution ON agency_goal_skill_executions(execution_id)""",
    """CREATE INDEX idx_agency_goal_skill_executions_goal ON agency_goal_skill_executions(goal_id)""",

    """CREATE TABLE agency_goals (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_agency_goals_origin ON agency_goals(origin)""",
    """CREATE INDEX idx_agency_goals_user_status ON agency_goals(user_id, status)""",

    """CREATE TABLE "agency_intention_set" (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_intention_set_goal ON "agency_intention_set"(goal_id)""",
    """CREATE INDEX idx_intention_set_priority ON "agency_intention_set"(priority_band, status)""",
    """CREATE INDEX idx_intention_set_user_status ON "agency_intention_set"(user_id, status)""",

    """CREATE TABLE agency_lessons (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (superseded_by) REFERENCES agency_lessons(lesson_id) ON DELETE SET NULL
            )""",

    """CREATE INDEX idx_agency_lessons_applied ON agency_lessons(applied_at) WHERE applied_at IS NOT NULL""",
    """CREATE INDEX idx_agency_lessons_status ON agency_lessons(user_id, status) WHERE status = 'active'""",
    """CREATE INDEX idx_agency_lessons_superseded ON agency_lessons(superseded_by)""",
    """CREATE INDEX idx_agency_lessons_target ON agency_lessons(target_kind, target_id)""",
    """CREATE INDEX idx_agency_lessons_time ON agency_lessons(user_id, created_at DESC)""",
    """CREATE INDEX idx_agency_lessons_user_type ON agency_lessons(user_id, lesson_type)""",

    """CREATE TABLE "agency_plan_executions" (
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
                progress_percentage REAL DEFAULT 0.0,
                execution_context TEXT,
                error_message TEXT,
                cancellation_reason TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",

    """CREATE INDEX idx_plan_executions_goal ON "agency_plan_executions"(goal_id)""",
    """CREATE INDEX idx_plan_executions_plan ON "agency_plan_executions"(plan_id)""",
    """CREATE INDEX idx_plan_executions_status ON "agency_plan_executions"(status, created_at)""",
    """CREATE INDEX idx_plan_executions_user ON "agency_plan_executions"(user_id, status)""",

    """CREATE TABLE agency_plans (
                plan_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',    -- draft, active, completed, abandoned
                steps_json TEXT NOT NULL,                -- JSON array of steps for early phases
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_agency_plans_goal_status ON agency_plans(goal_id, status)""",

    """CREATE TABLE agency_policy_rules (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_policy_rules_user ON agency_policy_rules(user_id)""",

    """CREATE TABLE agency_reflection_notes (
                note_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                related_goal_id TEXT,
                related_plan_id TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (related_goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL,
                FOREIGN KEY (related_plan_id) REFERENCES agency_plans(plan_id) ON DELETE SET NULL
            )""",

    """CREATE INDEX idx_agency_reflection_goal ON agency_reflection_notes(related_goal_id)""",
    """CREATE INDEX idx_agency_reflection_user_time ON agency_reflection_notes(user_id, created_at DESC)""",

    """CREATE TABLE agency_reflection_runs (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_reflection_runs_status ON agency_reflection_runs(status) WHERE status = 'running'""",
    """CREATE INDEX idx_reflection_runs_user_time ON agency_reflection_runs(user_id, started_at DESC)""",

    """CREATE TABLE agency_reminders (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL
            )""",

    """CREATE INDEX idx_reminders_cluster ON agency_reminders(cluster_id)""",
    """CREATE INDEX idx_reminders_goal ON agency_reminders(goal_id)""",
    """CREATE INDEX idx_reminders_priority ON agency_reminders(priority, urgency_score)""",
    """CREATE INDEX idx_reminders_scheduled ON agency_reminders(scheduled_at, status)""",
    """CREATE INDEX idx_reminders_status ON agency_reminders(status)""",
    """CREATE INDEX idx_reminders_user ON agency_reminders(user_id)""",

    """CREATE TABLE agency_self_model (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                UNIQUE(user_id, entity_type, entity_id, window_start)
            )""",

    """CREATE INDEX idx_self_model_freshness ON agency_self_model(last_updated DESC)""",
    """CREATE INDEX idx_self_model_user_entity ON agency_self_model(user_id, entity_type, entity_id)""",
    """CREATE INDEX idx_self_model_window ON agency_self_model(window_start, window_end)""",

    """CREATE TABLE "agency_skill_executions" (
                execution_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                message_id TEXT,
                goal_id TEXT,
                execution_time_ms INTEGER,
                outcome TEXT NOT NULL,
                error_message TEXT,
                context_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL
            )""",

    """CREATE TABLE "agency_skill_learning_data" (
                skill_id TEXT PRIMARY KEY,
                dimension_vector TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",

    """CREATE INDEX idx_skill_learning_updated ON "agency_skill_learning_data"(updated_at)""",

    """CREATE TABLE "agency_step_executions" (
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
                updated_at TEXT NOT NULL,
                FOREIGN KEY (execution_id) REFERENCES "agency_plan_executions"(execution_id) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_step_executions_execution ON "agency_step_executions"(execution_id, step_order)""",
    """CREATE INDEX idx_step_executions_skill ON "agency_step_executions"(skill_id)""",
    """CREATE INDEX idx_step_executions_status ON "agency_step_executions"(status)""",

    """CREATE TABLE "ams_behavioral_feedback" (
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
            context_json TEXT,
            user_satisfaction REAL,
            free_text TEXT,
            FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE
        )""",

    """CREATE INDEX idx_behavioral_feedback_processed ON ams_behavioral_feedback(processed)""",
    """CREATE INDEX idx_behavioral_feedback_skill ON ams_behavioral_feedback(skill_id)""",
    """CREATE INDEX idx_behavioral_feedback_user ON ams_behavioral_feedback(user_id)""",

    """CREATE TABLE "ams_behavioral_skills" (skill_id TEXT PRIMARY KEY, skill_name TEXT NOT NULL, skill_type TEXT NOT NULL, trigger_context TEXT NOT NULL, procedure_template TEXT NOT NULL, dimension_vector TEXT NOT NULL, supported_languages TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'active')""",

    """CREATE INDEX idx_behavioral_skills_status ON "ams_behavioral_skills"(status)""",
    """CREATE INDEX idx_behavioral_skills_type ON "ams_behavioral_skills"(skill_type)""",

    """CREATE TABLE "ams_consolidation_state" (
                id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",

    """CREATE INDEX idx_consolidation_state_updated ON "ams_consolidation_state"(updated_at DESC)""",

    """CREATE TABLE "ams_trajectories" (
            trajectory_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            conversation_id TEXT,
            selected_skill_id TEXT,
            context_bucket TEXT,
            feedback_reward INTEGER,
            timestamp TIMESTAMP NOT NULL,
            archived BOOLEAN DEFAULT 0,
            agency_context TEXT,
            message_id TEXT,
            turn_number INTEGER,
            user_input TEXT,
            ai_response TEXT,
            FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE
        )""",

    """CREATE INDEX idx_trajectories_archived ON ams_trajectories(archived)""",
    """CREATE INDEX idx_trajectories_conversation ON ams_trajectories(conversation_id)""",
    """CREATE INDEX idx_trajectories_user ON ams_trajectories(user_id)""",

    """CREATE TABLE "ams_user_memories" (
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_note TEXT, tags_json TEXT, is_favorite INTEGER DEFAULT 0, revisit_count INTEGER DEFAULT 0, last_revisited TIMESTAMP, emotional_tone TEXT, memory_type TEXT, content_type TEXT DEFAULT 'message', conversation_title TEXT, conversation_summary TEXT, turn_range TEXT, key_moments_json TEXT, temporal_metadata TEXT DEFAULT NULL, language TEXT,
                
                -- Foreign key
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_facts_category ON "ams_user_memories"(category)""",
    """CREATE INDEX idx_facts_confidence ON "ams_user_memories"(confidence)""",
    """CREATE INDEX idx_facts_content_type ON "ams_user_memories"(user_id, content_type) WHERE extraction_method = 'user_curated'""",
    """CREATE INDEX idx_facts_favorite ON "ams_user_memories"(user_id, is_favorite) WHERE is_favorite = 1""",
    """CREATE INDEX idx_facts_immutable ON "ams_user_memories"(is_immutable)""",
    """CREATE INDEX idx_facts_source ON "ams_user_memories"(source_conversation_id)""",
    """CREATE INDEX idx_facts_user_curated ON "ams_user_memories"(user_id, extraction_method) WHERE extraction_method = 'user_curated'""",
    """CREATE INDEX idx_facts_user_type ON "ams_user_memories"(user_id, fact_type)""",
    """CREATE INDEX idx_facts_validity ON "ams_user_memories"(valid_from, valid_until)""",
    """CREATE INDEX idx_user_memories_superseded ON "ams_user_memories"(json_extract(temporal_metadata, '$.superseded_by'))""",
    """CREATE INDEX idx_user_memories_temporal ON "ams_user_memories"(json_extract(temporal_metadata, '$.last_accessed'), json_extract(temporal_metadata, '$.confidence'))""",

    """CREATE TABLE arbiter_ab_tests (
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

    """CREATE INDEX idx_ab_tests_dates ON arbiter_ab_tests(start_date, end_date)""",
    """CREATE INDEX idx_ab_tests_status ON arbiter_ab_tests(status)""",

    """CREATE TABLE arbiter_bandit_arms (
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

    """CREATE INDEX idx_bandit_arms_active ON arbiter_bandit_arms(active)""",
    """CREATE INDEX idx_bandit_arms_pulls ON arbiter_bandit_arms(pulls)""",

    """CREATE TABLE "auth_access_policies" (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_uuid TEXT,
                permission TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uuid) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_access_policies_resource ON "auth_access_policies"(resource_type, resource_uuid)""",
    """CREATE INDEX idx_access_policies_user ON "auth_access_policies"(user_uuid)""",

    """CREATE TABLE "auth_devices" (
                uuid TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                device_type TEXT NOT NULL,
                platform TEXT NOT NULL,
                last_seen TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",

    """CREATE INDEX idx_devices_active ON "auth_devices"(is_active)""",

    """CREATE TABLE auth_sessions (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                device_uuid TEXT NOT NULL,
                jwt_token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE, session_type TEXT DEFAULT 'unified',
                FOREIGN KEY (user_uuid) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_auth_sessions_active ON auth_sessions(is_active, expires_at)""",
    """CREATE INDEX idx_auth_sessions_user ON auth_sessions(user_uuid)""",

    """CREATE TABLE "auth_user_credentials" (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                pin_hash TEXT NOT NULL,
                failed_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uuid) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_user_authentication_locked_until ON "auth_user_credentials"(locked_until)""",
    """CREATE INDEX idx_user_authentication_pin_hash ON "auth_user_credentials"(pin_hash)""",
    """CREATE INDEX idx_user_authentication_user ON "auth_user_credentials"(user_uuid)""",

    """CREATE TABLE consent_audit_log (
                audit_id TEXT PRIMARY KEY,
                consent_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,  -- granted, revoked, expired, inherited
                reason TEXT,
                metadata TEXT,  -- JSON: additional context
                created_at TEXT NOT NULL,
                FOREIGN KEY (consent_id) REFERENCES "consent_user_consents"(consent_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_consent_audit_consent ON consent_audit_log(consent_id)""",
    """CREATE INDEX idx_consent_audit_created ON consent_audit_log(created_at)""",
    """CREATE INDEX idx_consent_audit_user ON consent_audit_log(user_id)""",

    """CREATE TABLE "consent_records" (
                consent_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                consent_scope TEXT NOT NULL,       -- JSON object describing what was consented to
                decision TEXT NOT NULL,            -- granted, denied
                context_json TEXT,                 -- Optional context (goal_id, plan_id, etc.)
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,              -- NULL = permanent
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_consents_expires ON "consent_records"(expires_at)""",
    """CREATE INDEX idx_consents_user_scope ON "consent_records"(user_id, consent_scope)""",

    """CREATE TABLE "consent_user_consents" (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (inherited_from) REFERENCES "consent_user_consents"(consent_id) ON DELETE SET NULL
            )""",

    """CREATE INDEX idx_consents_scope ON "consent_user_consents"(scope, scope_identifier)""",
    """CREATE INDEX idx_consents_type ON "consent_user_consents"(consent_type, granted)""",
    """CREATE INDEX idx_consents_user ON "consent_user_consents"(user_id)""",

    """CREATE TABLE "conversation_initiations" (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_initiations_conversation_id ON "conversation_initiations"(conversation_id)""",
    """CREATE INDEX idx_initiations_initiated_at ON "conversation_initiations"(initiated_at)""",
    """CREATE INDEX idx_initiations_status ON "conversation_initiations"(resolution_status)""",
    """CREATE INDEX idx_initiations_user_id ON "conversation_initiations"(user_id)""",

    """CREATE TABLE emotion_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'system',
                timestamp TEXT NOT NULL,
                feeling TEXT NOT NULL,
                valence REAL NOT NULL,
                arousal REAL NOT NULL,
                intensity REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""",

    """CREATE INDEX idx_emotion_history_feeling ON emotion_history(feeling)""",
    """CREATE INDEX idx_emotion_history_user_time ON emotion_history(user_id, timestamp DESC)""",

    """CREATE TABLE emotion_state (
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

    """CREATE TABLE ethics_decisions_cache (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_ethics_cache_expires ON ethics_decisions_cache(expires_at)""",
    """CREATE INDEX idx_ethics_cache_target ON ethics_decisions_cache(target_type, target_id)""",
    """CREATE INDEX idx_ethics_cache_user ON ethics_decisions_cache(user_id)""",

    """CREATE TABLE ethics_gate_audit (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_ethics_audit_created ON ethics_gate_audit(created_at)""",
    """CREATE INDEX idx_ethics_audit_decision ON ethics_gate_audit(decision)""",
    """CREATE INDEX idx_ethics_audit_target ON ethics_gate_audit(target_type)""",
    """CREATE INDEX idx_ethics_audit_user ON ethics_gate_audit(user_id)""",

    """CREATE TABLE "ethics_policy_rules" (
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

    """CREATE INDEX idx_policy_rules_scope ON "ethics_policy_rules"(scope, scope_id)""",
    """CREATE INDEX idx_policy_rules_target ON "ethics_policy_rules"(target_type, enabled)""",

    """CREATE TABLE "ethics_value_profiles" (
                profile_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                sensitive_life_areas TEXT,         -- JSON array of LifeArea IDs
                allowed_curiosity_domains TEXT,    -- JSON array of allowed domains
                curiosity_intensity REAL DEFAULT 0.5,  -- 0.0-1.0 scale
                proactive_behavior_level TEXT DEFAULT 'balanced',  -- quiet, balanced, proactive
                storage_preferences TEXT,          -- JSON object with storage rules
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_value_profiles_user ON "ethics_value_profiles"(user_id)""",

    """CREATE TABLE kg_edge_properties (
                edge_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (edge_id, key, value),
                FOREIGN KEY (edge_id) REFERENCES kg_edges(id) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_kg_edge_properties_kv ON kg_edge_properties(key, value)""",

    """CREATE TABLE kg_edges (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                properties JSON NOT NULL,
                confidence REAL NOT NULL,
                source_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, valid_from TEXT, valid_until TEXT, is_current INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (source_id) REFERENCES kg_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES kg_nodes(id) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_kg_edges_relation_user ON kg_edges(user_id, relation_type, is_current)""",
    """CREATE INDEX idx_kg_edges_source ON kg_edges(source_id)""",
    """CREATE INDEX idx_kg_edges_target ON kg_edges(target_id)""",
    """CREATE INDEX idx_kg_edges_temporal ON kg_edges(user_id, is_current, valid_from)""",
    """CREATE INDEX idx_kg_edges_user_relation ON kg_edges(user_id, relation_type)""",

    """CREATE TABLE kg_node_properties (
                node_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (node_id, key, value),
                FOREIGN KEY (node_id) REFERENCES kg_nodes(id) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_kg_node_properties_kv ON kg_node_properties(key, value)""",

    """CREATE TABLE kg_nodes (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                label TEXT NOT NULL,
                properties JSON NOT NULL,
                confidence REAL NOT NULL,
                source_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, valid_from TEXT, valid_until TEXT, is_current INTEGER DEFAULT 1, canonical_id TEXT, aliases_json TEXT, language TEXT,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_kg_nodes_canonical ON kg_nodes(canonical_id)""",
    """CREATE INDEX idx_kg_nodes_label_user ON kg_nodes(user_id, label, is_current)""",
    """CREATE INDEX idx_kg_nodes_temporal ON kg_nodes(user_id, is_current, valid_from)""",
    """CREATE INDEX idx_kg_nodes_user_created ON kg_nodes(user_id, created_at)""",
    """CREATE INDEX idx_kg_nodes_user_label ON kg_nodes(user_id, label)""",

    """CREATE TABLE proactive_analytics (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_proactive_analytics_delivered ON proactive_analytics(delivered_at)""",
    """CREATE INDEX idx_proactive_analytics_type ON proactive_analytics(behavior_type)""",
    """CREATE INDEX idx_proactive_analytics_user ON proactive_analytics(user_id)""",

    """CREATE TABLE "proactive_reminder_clusters" (
                cluster_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                cluster_name TEXT,
                scheduled_delivery TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, delivered, dismissed
                reminder_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_reminder_clusters_delivery ON "proactive_reminder_clusters"(scheduled_delivery, status)""",
    """CREATE INDEX idx_reminder_clusters_user ON "proactive_reminder_clusters"(user_id)""",

    """CREATE TABLE "scheduler_task_executions" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                result TEXT,  -- JSON TaskResult
                error_message TEXT,
                duration_seconds REAL,
                FOREIGN KEY (task_id) REFERENCES "scheduler_tasks" (task_id)
            )""",

    """CREATE INDEX idx_task_executions_started_at ON "scheduler_task_executions" (started_at)""",
    """CREATE INDEX idx_task_executions_task_id ON "scheduler_task_executions" (task_id)""",

    """CREATE TABLE "scheduler_task_locks" (
                task_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (task_id) REFERENCES "scheduler_tasks" (task_id)
            )""",

    """CREATE INDEX idx_task_locks_expires_at ON "scheduler_task_locks" (expires_at)""",

    """CREATE TABLE "scheduler_tasks" (
                task_id TEXT PRIMARY KEY,
                task_class TEXT NOT NULL,
                schedule TEXT NOT NULL,
                config TEXT,  -- JSON configuration
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",

    """CREATE TABLE skill_executions_new (
                execution_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                message_id TEXT,
                goal_id TEXT,
                execution_time_ms INTEGER,
                outcome TEXT NOT NULL,
                error_message TEXT,
                context_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL
            )""",

    """CREATE TABLE "system_event_metrics" (
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

    """CREATE INDEX idx_event_metrics_bucket ON "system_event_metrics"(time_bucket, bucket_start)""",
    """CREATE INDEX idx_event_metrics_name ON "system_event_metrics"(metric_name, bucket_start)""",
    """CREATE INDEX idx_event_metrics_type ON "system_event_metrics"(event_type, bucket_start)""",

    """CREATE TABLE "system_event_replay_sessions" (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_replay_sessions_status ON "system_event_replay_sessions"(status)""",
    """CREATE INDEX idx_replay_sessions_user ON "system_event_replay_sessions"(user_id)""",

    """CREATE TABLE "system_events" (
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

    """CREATE INDEX idx_events_correlation ON "system_events"(correlation_id) WHERE correlation_id IS NOT NULL""",
    """CREATE INDEX idx_events_message_id ON "system_events"(message_id)""",
    """CREATE INDEX idx_events_source ON "system_events"(source)""",
    """CREATE INDEX idx_events_topic_timestamp ON "system_events"(topic, timestamp)""",

    """CREATE TABLE "system_logs" (
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
                user_uuid TEXT,
                session_id TEXT,
                trace_id TEXT,
                extra TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""",

    """CREATE INDEX idx_logs_level ON "system_logs"(level)""",
    """CREATE INDEX idx_logs_module ON "system_logs"(module)""",
    """CREATE INDEX idx_logs_session_id ON "system_logs"(session_id)""",
    """CREATE INDEX idx_logs_subsystem ON "system_logs"(subsystem)""",
    """CREATE INDEX idx_logs_timestamp ON "system_logs"(timestamp)""",
    """CREATE INDEX idx_logs_trace_id ON "system_logs"(trace_id)""",
    """CREATE INDEX idx_logs_user_timestamp ON "system_logs"(user_uuid, timestamp)""",

    """CREATE TABLE "user_feedback_requests" (
            request_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            goal_id TEXT,
            skill_id TEXT,
            execution_id TEXT,
            feedback_type TEXT NOT NULL,
            question TEXT NOT NULL,
            response TEXT,
            rating REAL,
            responded_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE,
            FOREIGN KEY (goal_id) REFERENCES agency_goals(goal_id) ON DELETE SET NULL
        )""",

    """CREATE INDEX idx_feedback_requests_responded ON user_feedback_requests(responded_at)""",
    """CREATE INDEX idx_feedback_requests_user ON user_feedback_requests(user_id)""",

    """CREATE TABLE user_proactive_preferences (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE TABLE "user_profiles" (
                uuid TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                nickname TEXT,
                user_type TEXT DEFAULT 'person',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            , primary_language TEXT)""",

    """CREATE INDEX idx_users_active ON "user_profiles"(is_active)""",
    """CREATE INDEX idx_users_user_type ON "user_profiles"(user_type)""",

    """CREATE TABLE user_relationships (
                uuid TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                related_user_uuid TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uuid) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                FOREIGN KEY (related_user_uuid) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE,
                UNIQUE(user_uuid, related_user_uuid, relationship_type)
            )""",

    """CREATE INDEX idx_user_relationships_related ON user_relationships(related_user_uuid)""",
    """CREATE INDEX idx_user_relationships_user ON user_relationships(user_uuid)""",

    """CREATE TABLE "user_skill_confidence" (
            user_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            confidence_score REAL DEFAULT 0.5 CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            usage_count INTEGER DEFAULT 0,
            positive_count INTEGER DEFAULT 0,
            negative_count INTEGER DEFAULT 0,
            last_used_at TIMESTAMP,
            PRIMARY KEY (user_id, skill_id),
            FOREIGN KEY (user_id) REFERENCES user_profiles(uuid) ON DELETE CASCADE
        )""",

    """CREATE INDEX idx_user_skill_confidence ON user_skill_confidence(user_id, confidence_score DESC)""",

    """CREATE TABLE workflow_executions (
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
                FOREIGN KEY (user_id) REFERENCES "user_profiles"(uuid) ON DELETE CASCADE
            )""",

    """CREATE INDEX idx_workflow_executions_status ON workflow_executions(status)""",
    """CREATE INDEX idx_workflow_executions_type ON workflow_executions(workflow_type, status)""",
    """CREATE INDEX idx_workflow_executions_user ON workflow_executions(user_id)""",

    """CREATE TABLE workflow_stages (
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

    """CREATE INDEX idx_workflow_stages_execution ON workflow_stages(execution_id, stage_order)""",
    """CREATE INDEX idx_workflow_stages_status ON workflow_stages(status)""",

]

# Alias for compatibility
SCHEMA_STATEMENTS = V1_SCHEMA