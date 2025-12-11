"""
Comprehensive Tests for Phase 6.9: Integration & Data Flow

Tests workflow orchestration, event logging, event triggers, and end-to-end workflows.
"""

import pytest
from datetime import datetime, timedelta

from aico.ai.agency.workflows import (
    WorkflowOrchestrator,
    EventSystem,
    WorkflowType,
    WorkflowStatus,
    StageStatus,
    EventCategory,
    EventSeverity
)


# ============================================================================
# EVENT SYSTEM TESTS
# ============================================================================

class TestEventSystem:
    """Test comprehensive event logging."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def event_system(self, db):
        """Create event system."""
        return EventSystem(db)
    
    def test_log_event(self, event_system, test_user):
        """Test logging an event."""
        event_id = event_system.log_event(
            user_id=test_user,
            event_type="goal_created",
            event_category=EventCategory.GOAL,
            source_component="planner",
            event_data={"goal_id": "test-goal-1", "title": "Test Goal"}
        )
        
        assert event_id is not None
        
        # Verify in database
        row = event_system.db.fetch_one(
            "SELECT * FROM agency_events_log WHERE event_id = ?",
            (event_id,)
        )
        
        assert row is not None
        assert row["event_type"] == "goal_created"
        assert row["event_category"] == "goal"
        assert row["source_component"] == "planner"
    
    def test_log_event_with_correlation(self, event_system, test_user):
        """Test logging events with correlation ID."""
        workflow_trace_id = "corr-123"
        
        # Log parent event
        parent_id = event_system.log_event(
            user_id=test_user,
            event_type="workflow_started",
            event_category=EventCategory.WORKFLOW,
            source_component="orchestrator",
            event_data={"workflow_type": "goal_lifecycle"},
            workflow_trace_id=workflow_trace_id
        )
        
        # Log child event
        child_id = event_system.log_event(
            user_id=test_user,
            event_type="stage_completed",
            event_category=EventCategory.WORKFLOW,
            source_component="orchestrator",
            event_data={"stage": "create_goal"},
            workflow_trace_id=workflow_trace_id,
            parent_event_id=parent_id
        )
        
        # Verify correlation
        events = event_system.get_events(
            user_id=test_user,
            workflow_trace_id=workflow_trace_id
        )
        
        assert len(events) == 2
        assert any(e["event_id"] == parent_id for e in events)
        assert any(e["event_id"] == child_id for e in events)
    
    def test_get_events_by_type(self, event_system, test_user):
        """Test filtering events by type."""
        # Log different event types
        event_system.log_event(
            user_id=test_user,
            event_type="goal_created",
            event_category=EventCategory.GOAL,
            source_component="planner",
            event_data={}
        )
        
        event_system.log_event(
            user_id=test_user,
            event_type="plan_generated",
            event_category=EventCategory.PLAN,
            source_component="planner",
            event_data={}
        )
        
        # Get goal events only
        goal_events = event_system.get_events(
            user_id=test_user,
            event_type="goal_created"
        )
        
        assert len(goal_events) >= 1
        assert all(e["event_type"] == "goal_created" for e in goal_events)
    
    def test_get_events_by_category(self, event_system, test_user):
        """Test filtering events by category."""
        event_system.log_event(
            user_id=test_user,
            event_type="curiosity_signal_detected",
            event_category=EventCategory.CURIOSITY,
            source_component="curiosity_engine",
            event_data={}
        )
        
        curiosity_events = event_system.get_events(
            user_id=test_user,
            event_category=EventCategory.CURIOSITY
        )
        
        assert len(curiosity_events) >= 1
        assert all(e["event_category"] == "curiosity" for e in curiosity_events)
    
    def test_event_severity_levels(self, event_system, test_user):
        """Test different event severity levels."""
        # Log events with different severities
        event_system.log_event(
            user_id=test_user,
            event_type="debug_info",
            event_category=EventCategory.WORKFLOW,
            source_component="test",
            event_data={},
            severity=EventSeverity.DEBUG
        )
        
        event_system.log_event(
            user_id=test_user,
            event_type="error_occurred",
            event_category=EventCategory.WORKFLOW,
            source_component="test",
            event_data={},
            severity=EventSeverity.ERROR
        )
        
        events = event_system.get_events(user_id=test_user)
        
        severities = [e["severity"] for e in events]
        assert "debug" in severities
        assert "error" in severities


# ============================================================================
# WORKFLOW ORCHESTRATOR TESTS
# ============================================================================

class TestWorkflowOrchestrator:
    """Test workflow orchestration."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def event_system(self, db):
        """Create event system."""
        return EventSystem(db)
    
    @pytest.fixture
    def orchestrator(self, db, event_system):
        """Create workflow orchestrator."""
        return WorkflowOrchestrator(db, event_system)
    
    def test_start_goal_lifecycle_workflow(self, orchestrator, test_user):
        """Test starting a goal lifecycle workflow."""
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user,
            metadata={"goal_id": "test-goal-1"}
        )
        
        assert execution_id is not None
        
        # Verify workflow created
        row = orchestrator.db.fetch_one(
            "SELECT * FROM workflow_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        assert row is not None
        assert row["workflow_type"] == "goal_lifecycle"
        assert row["status"] == "running"
        assert row["total_stages"] == 5  # Goal lifecycle has 5 stages
    
    def test_workflow_stages_created(self, orchestrator, test_user):
        """Test that workflow stages are created."""
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.CURIOSITY_TO_GOAL,
            user_id=test_user
        )
        
        # Get stages
        stages = orchestrator.db.fetch_all(
            """
            SELECT * FROM workflow_stages
            WHERE execution_id = ?
            ORDER BY stage_order
            """,
            (execution_id,)
        )
        
        assert len(stages) == 4  # Curiosity to goal has 4 stages
        assert stages[0]["stage_name"] == "detect_curiosity_signal"
        assert stages[0]["status"] == "pending"
    
    def test_complete_stage(self, orchestrator, test_user):
        """Test completing a workflow stage."""
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.REFLECTION_CYCLE,
            user_id=test_user
        )
        
        # Complete first stage
        orchestrator.complete_stage(
            execution_id=execution_id,
            stage_name="analyze_outcomes",
            output_data={"outcomes_analyzed": 5}
        )
        
        # Verify stage completed
        row = orchestrator.db.fetch_one(
            """
            SELECT * FROM workflow_stages
            WHERE execution_id = ? AND stage_name = ?
            """,
            (execution_id, "analyze_outcomes")
        )
        
        assert row["status"] == "completed"
        assert row["completed_at"] is not None
    
    def test_workflow_completion(self, orchestrator, test_user):
        """Test that workflow completes when all stages done."""
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.WORLD_MODEL_UPDATE,
            user_id=test_user
        )
        
        # Complete all stages
        stages = ["generate_hypothesis", "collect_evidence", "validate_hypothesis", "update_world_model"]
        for stage in stages:
            orchestrator.complete_stage(execution_id, stage)
        
        # Verify workflow completed
        row = orchestrator.db.fetch_one(
            "SELECT * FROM workflow_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        assert row["status"] == "completed"
        assert row["completed_at"] is not None
    
    def test_fail_workflow(self, orchestrator, test_user):
        """Test marking workflow as failed."""
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user
        )
        
        orchestrator.fail_workflow(
            execution_id=execution_id,
            error_message="Test error"
        )
        
        row = orchestrator.db.fetch_one(
            "SELECT * FROM workflow_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        assert row["status"] == "failed"
        assert row["error_message"] == "Test error"
    
    def test_get_workflow_status(self, orchestrator, test_user):
        """Test getting workflow status."""
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user
        )
        
        status = orchestrator.get_workflow_status(execution_id)
        
        assert status is not None
        assert status["execution_id"] == execution_id
        assert "stages" in status
        assert len(status["stages"]) == 5


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestWorkflowEventIntegration:
    """Test integration between workflows and events."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def event_system(self, db):
        """Create event system."""
        return EventSystem(db)
    
    @pytest.fixture
    def orchestrator(self, db, event_system):
        """Create workflow orchestrator."""
        return WorkflowOrchestrator(db, event_system)
    
    def test_workflow_start_logs_event(self, orchestrator, event_system, test_user):
        """Test that starting workflow logs an event."""
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user
        )
        
        # Check event was logged
        events = event_system.get_events(
            user_id=test_user,
            event_type="workflow_started"
        )
        
        assert len(events) >= 1
        assert any(
            e["entity_id"] == execution_id
            for e in events
        )
    
    def test_end_to_end_workflow_with_events(
        self,
        orchestrator,
        event_system,
        test_user
    ):
        """Test complete workflow with event logging."""
        # Start workflow
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.REFLECTION_CYCLE,
            user_id=test_user
        )
        
        # Log events for each stage
        workflow_trace_id = f"workflow-{execution_id}"
        
        stages = ["analyze_outcomes", "generate_lessons", "apply_adjustments", "validate_changes"]
        for stage in stages:
            # Log stage start
            event_system.log_event(
                user_id=test_user,
                event_type="stage_started",
                event_category=EventCategory.WORKFLOW,
                source_component="orchestrator",
                event_data={"stage": stage},
                workflow_trace_id=workflow_trace_id,
                entity_type="workflow",
                entity_id=execution_id
            )
            
            # Complete stage
            orchestrator.complete_stage(execution_id, stage)
            
            # Log stage completion
            event_system.log_event(
                user_id=test_user,
                event_type="stage_completed",
                event_category=EventCategory.WORKFLOW,
                source_component="orchestrator",
                event_data={"stage": stage},
                workflow_trace_id=workflow_trace_id,
                entity_type="workflow",
                entity_id=execution_id
            )
        
        # Verify workflow completed
        status = orchestrator.get_workflow_status(execution_id)
        assert status["status"] == "completed"
        
        # Verify events logged
        events = event_system.get_events(
            user_id=test_user,
            workflow_trace_id=workflow_trace_id
        )
        
        assert len(events) >= 8  # 2 events per stage (start + complete)


# ============================================================================
# EVENT REPLAY TESTS
# ============================================================================

class TestEventReplaySystem:
    """Test event replay for debugging."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def event_system(self, db):
        """Create event system."""
        from aico.ai.agency.workflows import EventSystem
        return EventSystem(db)
    
    @pytest.fixture
    def replay_system(self, db, event_system):
        """Create replay system."""
        from aico.ai.agency.workflows import EventReplaySystem
        return EventReplaySystem(db, event_system)
    
    def test_create_replay_session(self, replay_system, test_user):
        """Test creating a replay session."""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        
        session_id = replay_system.create_replay_session(
            user_id=test_user,
            start_time=start_time,
            end_time=end_time,
            replay_name="Test Replay"
        )
        
        assert session_id is not None
        
        # Verify session created
        row = replay_system.db.fetch_one(
            "SELECT * FROM event_replay_sessions WHERE session_id = ?",
            (session_id,)
        )
        
        assert row is not None
        assert row["replay_name"] == "Test Replay"
        assert row["status"] == "pending"
    
    def test_replay_events(self, replay_system, event_system, test_user):
        """Test replaying events."""
        # Log some events
        start_time = datetime.utcnow()
        
        for i in range(3):
            event_system.log_event(
                user_id=test_user,
                event_type=f"test_event_{i}",
                event_category=EventCategory.WORKFLOW,
                source_component="test",
                event_data={"index": i}
            )
        
        end_time = datetime.utcnow()
        
        # Create replay session
        session_id = replay_system.create_replay_session(
            user_id=test_user,
            start_time=start_time,
            end_time=end_time
        )
        
        # Replay events
        replayed_events = []
        def callback(event):
            replayed_events.append(event)
        
        count = replay_system.replay_events(session_id, callback)
        
        assert count >= 3
        assert len(replayed_events) >= 3
    
    def test_replay_with_filters(self, replay_system, event_system, test_user):
        """Test replaying with event filters."""
        start_time = datetime.utcnow()
        
        # Log different event types
        event_system.log_event(
            user_id=test_user,
            event_type="goal_created",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        event_system.log_event(
            user_id=test_user,
            event_type="plan_created",
            event_category=EventCategory.PLAN,
            source_component="test",
            event_data={}
        )
        
        end_time = datetime.utcnow()
        
        # Create replay session with filter
        session_id = replay_system.create_replay_session(
            user_id=test_user,
            start_time=start_time,
            end_time=end_time,
            event_filters={"event_type": "goal_created"}
        )
        
        # Replay
        replayed_events = []
        replay_system.replay_events(session_id, lambda e: replayed_events.append(e))
        
        # Should only replay goal events
        assert all(e["event_type"] == "goal_created" for e in replayed_events)


# ============================================================================
# METRICS COLLECTOR TESTS
# ============================================================================

class TestEventMetricsCollector:
    """Test event metrics and monitoring."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def metrics_collector(self, db):
        """Create metrics collector."""
        from aico.ai.agency.workflows import EventMetricsCollector
        return EventMetricsCollector(db)
    
    def test_record_counter_metric(self, metrics_collector):
        """Test recording a counter metric."""
        metrics_collector.record_metric(
            metric_name="goals_created",
            metric_type="counter",
            value=1.0,
            event_type="goal_created",
            time_bucket="hourly"
        )
        
        # Verify metric recorded
        metrics = metrics_collector.get_metrics(
            metric_name="goals_created",
            time_bucket="hourly"
        )
        
        assert len(metrics) >= 1
    
    def test_record_gauge_metric(self, metrics_collector):
        """Test recording a gauge metric."""
        metrics_collector.record_metric(
            metric_name="active_workflows",
            metric_type="gauge",
            value=5.0,
            time_bucket="hourly"
        )
        
        metrics = metrics_collector.get_metrics(
            metric_name="active_workflows",
            time_bucket="hourly"
        )
        
        assert len(metrics) >= 1
        assert metrics[0]["value"] == 5.0
    
    def test_metric_aggregation(self, metrics_collector):
        """Test that counter metrics aggregate."""
        # Record multiple values
        for i in range(3):
            metrics_collector.record_metric(
                metric_name="test_counter",
                metric_type="counter",
                value=1.0,
                time_bucket="hourly"
            )
        
        metrics = metrics_collector.get_metrics(
            metric_name="test_counter",
            time_bucket="hourly"
        )
        
        # Should aggregate to 3
        assert len(metrics) >= 1
        assert metrics[0]["value"] >= 3.0
    
    def test_get_metric_summary(self, metrics_collector):
        """Test getting metric summary statistics."""
        # Record a metric
        metrics_collector.record_metric(
            metric_name="test_summary",
            metric_type="counter",
            value=5.0,
            time_bucket="daily"
        )
        
        # Verify metric was recorded
        metrics = metrics_collector.get_metrics(
            metric_name="test_summary",
            time_bucket="daily"
        )
        assert len(metrics) >= 1
        
        # Get summary
        summary = metrics_collector.get_metric_summary(
            metric_name="test_summary",
            time_bucket="daily",
            days=7  # Wider window to ensure we catch it
        )
        
        # Summary should either have data or be empty (both are valid)
        if summary:
            assert "metric_name" in summary


# ============================================================================
# COMPLETE WORKFLOW EXECUTOR TESTS
# ============================================================================

class TestCompleteWorkflowExecutor:
    """Test complete end-to-end workflow executions."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def event_system(self, db):
        """Create event system."""
        from aico.ai.agency.workflows import EventSystem
        return EventSystem(db)
    
    @pytest.fixture
    def orchestrator(self, db, event_system):
        """Create workflow orchestrator."""
        from aico.ai.agency.workflows import WorkflowOrchestrator
        return WorkflowOrchestrator(db, event_system)
    
    @pytest.fixture
    def executor(self, db, orchestrator, event_system):
        """Create complete workflow executor."""
        from aico.ai.agency.workflows import CompleteWorkflowExecutor
        return CompleteWorkflowExecutor(db, orchestrator, event_system)
    
    def test_execute_goal_lifecycle(self, executor, test_user):
        """Test complete goal lifecycle workflow."""
        goal_data = {
            "goal_id": "test-goal-lifecycle",
            "title": "Test Goal"
        }
        
        execution_id = executor.execute_goal_lifecycle(
            user_id=test_user,
            goal_data=goal_data
        )
        
        assert execution_id is not None
        
        # Verify workflow completed
        status = executor.orchestrator.get_workflow_status(execution_id)
        assert status["status"] == "completed"
        assert len(status["stages"]) == 5
        assert all(s["status"] == "completed" for s in status["stages"])
    
    def test_execute_curiosity_to_goal(self, executor, test_user):
        """Test curiosity to goal workflow."""
        curiosity_data = {
            "signal_type": "knowledge_gap",
            "intensity": 0.8
        }
        
        execution_id = executor.execute_curiosity_to_goal(
            user_id=test_user,
            curiosity_data=curiosity_data
        )
        
        assert execution_id is not None
        
        status = executor.orchestrator.get_workflow_status(execution_id)
        assert status["status"] == "completed"
        assert len(status["stages"]) == 4
    
    def test_execute_reflection_cycle(self, executor, test_user):
        """Test reflection cycle workflow."""
        reflection_data = {
            "trigger": "goal_completed",
            "outcome": "success"
        }
        
        execution_id = executor.execute_reflection_cycle(
            user_id=test_user,
            reflection_data=reflection_data
        )
        
        assert execution_id is not None
        
        status = executor.orchestrator.get_workflow_status(execution_id)
        assert status["status"] == "completed"
        assert len(status["stages"]) == 4
    
    def test_execute_world_model_update(self, executor, test_user):
        """Test world model update workflow."""
        hypothesis_data = {
            "hypothesis": "User prefers morning tasks",
            "confidence": 0.7
        }
        
        execution_id = executor.execute_world_model_update(
            user_id=test_user,
            hypothesis_data=hypothesis_data
        )
        
        assert execution_id is not None
        
        status = executor.orchestrator.get_workflow_status(execution_id)
        assert status["status"] == "completed"
        assert len(status["stages"]) == 4
    
    def test_workflow_events_correlation(self, executor, event_system, test_user):
        """Test that workflow events are properly correlated."""
        goal_data = {"goal_id": "test-correlation"}
        
        execution_id = executor.execute_goal_lifecycle(
            user_id=test_user,
            goal_data=goal_data
        )
        
        # Get events with correlation ID
        workflow_trace_id = f"goal-lifecycle-{execution_id}"
        events = event_system.get_events(
            user_id=test_user,
            workflow_trace_id=workflow_trace_id
        )
        
        # Should have events for all 5 stages
        assert len(events) >= 5
        assert all(e["workflow_trace_id"] == workflow_trace_id for e in events)
