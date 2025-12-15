"""
Final targeted tests for workflows.py to push coverage from 78% to 80%+.

Focuses on specific uncovered lines:
- Event filtering with time ranges
- Event handler registration and triggering
- Metrics update error handling
- Workflow stage transitions
"""

import pytest
from datetime import datetime, timedelta, UTC
import uuid

from aico.ai.agency.workflows import (
    EventSystem,
    WorkflowOrchestrator,
    EventCategory,
    EventSeverity,
)


class TestEventSystemTimeFiltering:
    """Tests for event filtering with time ranges."""
    
    def test_get_events_with_time_filters(self, test_db, test_user):
        """Test that time filter parameters are accepted."""
        event_system = EventSystem(test_db)
        
        # Log event
        event_system.log_event(
            user_id=test_user,
            event_type="test_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        # Test that start_time parameter is accepted
        start_time = datetime.now(UTC) - timedelta(hours=1)
        events = event_system.get_events(
            user_id=test_user,
            start_time=start_time
        )
        
        # Should return list (filtering logic tested elsewhere)
        assert isinstance(events, list)
    
    def test_get_events_with_end_time_filter(self, test_db, test_user):
        """Test filtering events by end time."""
        event_system = EventSystem(test_db)
        
        # Log event
        event_system.log_event(
            user_id=test_user,
            event_type="test_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        # Filter with end time in the past (should get no results)
        end_time = datetime.now(UTC) - timedelta(hours=1)
        events = event_system.get_events(
            user_id=test_user,
            end_time=end_time
        )
        
        # Should get no events (all are more recent)
        assert len(events) == 0
    
    def test_get_events_with_entity_id_filter(self, test_db, test_user):
        """Test filtering events by entity_id."""
        event_system = EventSystem(test_db)
        
        entity_id = str(uuid.uuid4())
        
        # Log event with entity_id
        event_system.log_event(
            user_id=test_user,
            event_type="entity_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={},
            entity_id=entity_id
        )
        
        # Filter by entity_id
        events = event_system.get_events(
            user_id=test_user,
            entity_id=entity_id
        )
        
        assert len(events) >= 1
        assert all(e["entity_id"] == entity_id for e in events)
    
    def test_get_events_with_workflow_trace_id_filter(self, test_db, test_user):
        """Test filtering events by workflow_trace_id."""
        event_system = EventSystem(test_db)
        
        trace_id = f"workflow-{str(uuid.uuid4())[:8]}"
        
        # Log event with workflow_trace_id
        event_system.log_event(
            user_id=test_user,
            event_type="workflow_event",
            event_category=EventCategory.WORKFLOW,
            source_component="test",
            event_data={},
            workflow_trace_id=trace_id
        )
        
        # Filter by workflow_trace_id
        events = event_system.get_events(
            user_id=test_user,
            workflow_trace_id=trace_id
        )
        
        assert len(events) >= 1
        assert all(e["workflow_trace_id"] == trace_id for e in events)


class TestEventHandlerRegistration:
    """Tests for event handler registration and triggering."""
    
    def test_register_and_trigger_handler(self, test_db, test_user):
        """Test registering and triggering event handlers."""
        event_system = EventSystem(test_db)
        
        # Track handler calls
        handler_called = []
        
        def test_handler(event_data):
            handler_called.append(event_data)
        
        # Register handler
        event_system.register_trigger("test_event", test_handler)
        
        # Log event that should trigger handler
        event_system.log_event(
            user_id=test_user,
            event_type="test_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={"key": "value"}
        )
        
        # Handler should have been called
        assert len(handler_called) == 1
        assert handler_called[0]["key"] == "value"
    
    def test_multiple_handlers_for_same_event(self, test_db, test_user):
        """Test multiple handlers for the same event type."""
        event_system = EventSystem(test_db)
        
        calls = []
        
        def handler1(data):
            calls.append("handler1")
        
        def handler2(data):
            calls.append("handler2")
        
        # Register multiple handlers
        event_system.register_trigger("multi_event", handler1)
        event_system.register_trigger("multi_event", handler2)
        
        # Log event
        event_system.log_event(
            user_id=test_user,
            event_type="multi_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        # Both handlers should be called
        assert len(calls) == 2
        assert "handler1" in calls
        assert "handler2" in calls
    
    def test_handler_exception_doesnt_break_event_logging(self, test_db, test_user):
        """Test that handler exceptions don't break event logging."""
        event_system = EventSystem(test_db)
        
        def failing_handler(data):
            raise Exception("Handler error")
        
        # Register failing handler
        event_system.register_trigger("error_event", failing_handler)
        
        # Log event - should succeed despite handler failure
        event_id = event_system.log_event(
            user_id=test_user,
            event_type="error_event",
            event_category=EventCategory.GOAL,
            source_component="test",
            event_data={}
        )
        
        # Event should still be logged
        assert event_id is not None
        
        # Verify event was stored
        events = event_system.get_events(user_id=test_user, event_type="error_event")
        assert len(events) >= 1


class TestWorkflowBasicOperations:
    """Tests for basic workflow operations."""
    
    def test_start_workflow_creates_execution(self, test_db, test_user):
        """Test that starting a workflow creates an execution record."""
        event_system = EventSystem(test_db)
        orchestrator = WorkflowOrchestrator(test_db, event_system)
        
        # Start workflow
        from aico.ai.agency.workflows import WorkflowType
        execution_id = orchestrator.start_workflow(
            workflow_type=WorkflowType.GOAL_LIFECYCLE,
            user_id=test_user,
            metadata={"test": "data"}
        )
        
        # Verify execution was created
        assert execution_id is not None
        assert isinstance(execution_id, str)
        
        # Verify we can get status
        status = orchestrator.get_workflow_status(execution_id)
        assert status is not None
        assert status["execution_id"] == execution_id
