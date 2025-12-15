"""
Additional coverage tests for agency/workflows.py - targeting uncovered lines.

Focuses on error handling, edge cases, and conditional branches in workflows.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch
import json

from aico.ai.agency.workflows import (
    EventSystem,
    WorkflowOrchestrator,
    WorkflowType,
    WorkflowStatus,
    StageStatus,
    EventCategory,
    EventSeverity,
)


class TestEventSystemErrorHandling:
    """Tests for EventSystem error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_log_event_basic(self, test_db, test_user):
        """Test basic event logging."""
        event_system = EventSystem(test_db)
        
        event_id = event_system.log_event(
            user_id=test_user,
            event_type="test_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={"key": "value"}
        )
        
        assert event_id is not None
        assert len(event_id) > 0
    
    @pytest.mark.asyncio
    async def test_log_event_with_all_fields(self, test_db, test_user):
        """Test event logging with all optional fields."""
        event_system = EventSystem(test_db)
        
        # First create parent event to satisfy FK
        parent_id = event_system.log_event(
            user_id=test_user,
            event_type="parent_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        # Now create child event with all fields
        event_id = event_system.log_event(
            user_id=test_user,
            event_type="test_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={"key": "value"},
            entity_type="goal",
            entity_id="goal-123",
            workflow_trace_id="trace-123",
            parent_event_id=parent_id,
            severity=EventSeverity.WARNING
        )
        
        assert event_id is not None
    
    @pytest.mark.asyncio
    async def test_log_event_error_handling(self, test_db, test_user):
        """Test event logging handles database errors."""
        event_system = EventSystem(test_db)
        
        # Mock database to fail
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                event_system.log_event(
                    user_id=test_user,
                    event_type="test_event",
                    event_category=EventCategory.GOAL,
                    source_component="test",
                    event_data={}
                )
    
    @pytest.mark.asyncio
    async def test_get_events_no_filters(self, test_db, test_user):
        """Test getting events without filters."""
        event_system = EventSystem(test_db)
        
        # Log some events
        event_system.log_event(
            user_id=test_user,
            event_type="event1",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        events = event_system.get_events(user_id=test_user)
        
        assert isinstance(events, list)
        assert len(events) >= 1
    
    @pytest.mark.asyncio
    async def test_get_events_with_event_type_filter(self, test_db, test_user):
        """Test getting events filtered by event_type."""
        event_system = EventSystem(test_db)
        
        event_system.log_event(
            user_id=test_user,
            event_type="specific_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        events = event_system.get_events(
            user_id=test_user,
            event_type="specific_event"
        )
        
        assert len(events) >= 1
        assert all(e["event_type"] == "specific_event" for e in events)
    
    @pytest.mark.asyncio
    async def test_get_events_with_category_filter(self, test_db, test_user):
        """Test getting events filtered by category."""
        event_system = EventSystem(test_db)
        
        event_system.log_event(
            user_id=test_user,
            event_type="test",
            event_category=EventCategory.PLAN,
            source_component="test",
            event_data={}
        )
        
        events = event_system.get_events(
            user_id=test_user,
            event_category=EventCategory.PLAN
        )
        
        assert len(events) >= 1
    
    @pytest.mark.asyncio
    async def test_get_events_with_entity_id_filter(self, test_db, test_user):
        """Test getting events filtered by entity_id."""
        event_system = EventSystem(test_db)
        
        event_system.log_event(
            user_id=test_user,
            event_type="test",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={},
            entity_id="entity-123"
        )
        
        events = event_system.get_events(
            user_id=test_user,
            entity_id="entity-123"
        )
        
        assert len(events) >= 1
    
    @pytest.mark.asyncio
    async def test_get_events_with_workflow_trace_filter(self, test_db, test_user):
        """Test getting events filtered by workflow_trace_id."""
        event_system = EventSystem(test_db)
        
        event_system.log_event(
            user_id=test_user,
            event_type="test",
            event_category=EventCategory.WORKFLOW,
            source_component="test",
            event_data={},
            workflow_trace_id="trace-123"
        )
        
        events = event_system.get_events(
            user_id=test_user,
            workflow_trace_id="trace-123"
        )
        
        assert len(events) >= 1
    
    @pytest.mark.asyncio
    async def test_get_events_with_time_filters(self, test_db, test_user):
        """Test getting events filtered by time range."""
        event_system = EventSystem(test_db)
        
        event_system.log_event(
            user_id=test_user,
            event_type="test",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        start_time = datetime.now(UTC) - timedelta(hours=1)
        end_time = datetime.now(UTC) + timedelta(hours=1)
        
        events = event_system.get_events(
            user_id=test_user,
            start_time=start_time,
            end_time=end_time
        )
        
        assert len(events) >= 1
    
    @pytest.mark.asyncio
    async def test_get_events_error_handling(self, test_db, test_user):
        """Test get_events handles database errors gracefully."""
        event_system = EventSystem(test_db)
        
        # Mock database to fail
        with patch.object(test_db, 'fetch_all', side_effect=Exception("DB error")):
            events = event_system.get_events(user_id=test_user)
            
            # Should return empty list on error
            assert events == []
    
    @pytest.mark.asyncio
    async def test_register_trigger(self, test_db):
        """Test registering event trigger."""
        event_system = EventSystem(test_db)
        
        handler_called = []
        
        def test_handler(event_data):
            handler_called.append(event_data)
        
        event_system.register_trigger("test_event", test_handler)
        
        assert "test_event" in event_system._triggers
        assert len(event_system._triggers["test_event"]) == 1
    
    @pytest.mark.asyncio
    async def test_trigger_handlers_called(self, test_db, test_user):
        """Test that registered handlers are called on event."""
        event_system = EventSystem(test_db)
        
        handler_called = []
        
        def test_handler(event_data):
            handler_called.append(event_data)
        
        event_system.register_trigger("test_event", test_handler)
        
        event_system.log_event(
            user_id=test_user,
            event_type="test_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={"test": "data"}
        )
        
        assert len(handler_called) == 1
        assert handler_called[0]["test"] == "data"
    
    @pytest.mark.asyncio
    async def test_trigger_handler_error_handling(self, test_db, test_user):
        """Test that handler errors don't crash event logging."""
        event_system = EventSystem(test_db)
        
        def failing_handler(event_data):
            raise Exception("Handler error")
        
        event_system.register_trigger("test_event", failing_handler)
        
        # Should not raise exception
        event_id = event_system.log_event(
            user_id=test_user,
            event_type="test_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        assert event_id is not None
    
    @pytest.mark.asyncio
    async def test_update_metrics_called(self, test_db, test_user):
        """Test that metrics update is called during event logging."""
        event_system = EventSystem(test_db)
        
        # Track if metrics update was called
        metrics_called = []
        original_update = event_system._update_metrics
        
        def tracking_update(*args, **kwargs):
            metrics_called.append(True)
            # Call original but catch any errors
            try:
                original_update(*args, **kwargs)
            except:
                pass
        
        event_system._update_metrics = tracking_update
        
        event_system.log_event(
            user_id=test_user,
            event_type="test_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        assert len(metrics_called) == 1
        
        # Restore original
        event_system._update_metrics = original_update


class TestWorkflowOrchestratorErrorHandling:
    """Tests for WorkflowOrchestrator error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_start_workflow_goal_lifecycle(self, test_db, test_user):
        """Test starting goal lifecycle workflow."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user,
            metadata={"goal_id": "test-goal"}
        )
        
        assert execution_id is not None
        assert len(execution_id) > 0
    
    @pytest.mark.asyncio
    async def test_start_workflow_curiosity_to_goal(self, test_db, test_user):
        """Test starting curiosity to goal workflow."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.CURIOSITY_TO_GOAL,
            user_id=test_user
        )
        
        assert execution_id is not None
    
    @pytest.mark.asyncio
    async def test_start_workflow_reflection_cycle(self, test_db, test_user):
        """Test starting reflection cycle workflow."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.REFLECTION_CYCLE,
            user_id=test_user
        )
        
        assert execution_id is not None
    
    @pytest.mark.asyncio
    async def test_start_workflow_world_model_update(self, test_db, test_user):
        """Test starting world model update workflow."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.WORLD_MODEL_UPDATE,
            user_id=test_user
        )
        
        assert execution_id is not None
    
    @pytest.mark.asyncio
    async def test_start_workflow_error_handling(self, test_db, test_user):
        """Test workflow start handles database errors."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        # Mock database to fail
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                orchestrator.start_workflow(
                    workflow_type=WorkflowType.GOAL_LIFECYCLE,
                    user_id=test_user
                )
    
    @pytest.mark.asyncio
    async def test_complete_stage(self, test_db, test_user):
        """Test completing a workflow stage."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user
        )
        
        # Complete first stage
        orchestrator.complete_stage(
            execution_id=execution_id,
            stage_name="create_goal",
            output_data={"goal_id": "test-goal"}
        )
        
        # Verify stage completed
        row = test_db.fetch_one(
            "SELECT status FROM workflow_stages WHERE execution_id = ? AND stage_name = ?",
            (execution_id, "create_goal")
        )
        
        assert row["status"] == StageStatus.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_complete_all_stages_completes_workflow(self, test_db, test_user):
        """Test that completing all stages completes the workflow."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user
        )
        
        # Get all stages
        stages = test_db.fetch_all(
            "SELECT stage_name FROM workflow_stages WHERE execution_id = ? ORDER BY stage_order",
            (execution_id,)
        )
        
        # Complete all stages
        for stage in stages:
            orchestrator.complete_stage(execution_id, stage["stage_name"])
        
        # Verify workflow completed
        row = test_db.fetch_one(
            "SELECT status FROM workflow_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        assert row["status"] == WorkflowStatus.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_fail_workflow(self, test_db, test_user):
        """Test failing a workflow."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user
        )
        
        orchestrator.fail_workflow(execution_id, "Test error")
        
        # Verify workflow failed
        row = test_db.fetch_one(
            "SELECT status, error_message FROM workflow_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        assert row["status"] == WorkflowStatus.FAILED.value
        assert row["error_message"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_get_workflow_status(self, test_db, test_user):
        """Test getting workflow status."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user
        )
        
        status = orchestrator.get_workflow_status(execution_id)
        
        assert status is not None
        assert status["execution_id"] == execution_id
        assert status["status"] == WorkflowStatus.RUNNING.value
    
    @pytest.mark.asyncio
    async def test_get_workflow_status_nonexistent(self, test_db):
        """Test getting status of nonexistent workflow."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        status = orchestrator.get_workflow_status("nonexistent-id")
        
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_workflow_stages(self, test_db, test_user):
        """Test getting workflow stages."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user
        )
        
        stages = orchestrator._get_workflow_stages(WorkflowType.GOAL_LIFECYCLE)
        
        assert isinstance(stages, list)
        assert len(stages) > 0
    
    @pytest.mark.asyncio
    async def test_workflow_with_metadata(self, test_db, test_user):
        """Test workflow with custom metadata."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        metadata = {
            "custom_field": "value",
            "goal_id": "test-goal-123"
        }
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user,
            metadata=metadata
        )
        
        # Verify metadata stored
        row = test_db.fetch_one(
            "SELECT metadata FROM workflow_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        stored_metadata = json.loads(row["metadata"])
        assert stored_metadata["custom_field"] == "value"


class TestWorkflowIntegration:
    """Integration tests for complete workflow execution."""
    
    @pytest.mark.asyncio
    async def test_complete_goal_lifecycle_workflow(self, test_db, test_user):
        """Test complete goal lifecycle workflow execution."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        # Start workflow
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user,
            metadata={"goal_id": "test-goal"}
        )
        
        # Get stages
        stages = test_db.fetch_all(
            "SELECT stage_name FROM workflow_stages WHERE execution_id = ? ORDER BY stage_order",
            (execution_id,)
        )
        
        # Complete each stage
        for stage in stages:
            orchestrator.complete_stage(
                execution_id,
                stage["stage_name"],
                {"completed": True}
            )
        
        # Verify workflow completed
        status = orchestrator.get_workflow_status(execution_id)
        assert status["status"] == WorkflowStatus.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_workflow_with_event_tracking(self, test_db, test_user):
        """Test workflow with event tracking."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user
        )
        
        # Check that workflow_started event was logged
        events = event_system.get_events(
            user_id=test_user,
            event_type="workflow_started"
        )
        
        assert len(events) >= 1
        assert any(e["entity_id"] == execution_id for e in events)
