"""
Integration Tests for Phase 6.2: Scheduler Integration

Tests the complete scheduler with priority queue, retry logic, and resource monitoring.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.scheduler.core import TaskScheduler
from backend.scheduler.tasks.base import (
    BaseTask, TaskContext, TaskResult, TaskStatus,
    TaskPriority, TaskQueue, RetryConfig, RetryStrategy
)


class MockSuccessTask(BaseTask):
    """Mock task that always succeeds"""
    task_id = "test.success"
    priority = TaskPriority.NORMAL
    queue = TaskQueue.BACKGROUND_LIGHT
    
    async def execute(self, context: TaskContext) -> TaskResult:
        return TaskResult(success=True, message="Success")


class MockFailureTask(BaseTask):
    """Mock task that always fails"""
    task_id = "test.failure"
    priority = TaskPriority.NORMAL
    queue = TaskQueue.BACKGROUND_LIGHT
    retry_config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        max_retries=3,
        base_delay_seconds=1,
        jitter=False
    )
    
    async def execute(self, context: TaskContext) -> TaskResult:
        return TaskResult(success=False, error="Simulated failure")


class MockHighPriorityTask(BaseTask):
    """Mock high priority task"""
    task_id = "test.high_priority"
    priority = TaskPriority.HIGH
    queue = TaskQueue.USER_FACING
    
    async def execute(self, context: TaskContext) -> TaskResult:
        return TaskResult(success=True, message="High priority success")


class MockRetrySuccessTask(BaseTask):
    """Mock task that fails first time, succeeds on retry"""
    task_id = "test.retry_success"
    priority = TaskPriority.NORMAL
    queue = TaskQueue.BACKGROUND_LIGHT
    retry_config = RetryConfig(
        strategy=RetryStrategy.LINEAR,
        max_retries=3,
        base_delay_seconds=1,
        jitter=False
    )
    
    async def execute(self, context: TaskContext) -> TaskResult:
        if context.retry_count == 0:
            return TaskResult(success=False, error="First attempt failed")
        else:
            return TaskResult(success=True, message=f"Succeeded on retry {context.retry_count}")


@pytest.mark.asyncio
class TestSchedulerPriorityQueue:
    """Test scheduler with priority queue"""
    
    async def test_priority_queue_initialization(self):
        """Test that scheduler initializes priority queue"""
        # Arrange
        container = MagicMock()
        container.config = MagicMock()
        container.config.get = MagicMock(return_value={})
        
        scheduler = TaskScheduler("test_scheduler", container)
        
        # Mock database service
        mock_db = MagicMock()
        mock_db.execute = MagicMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))
        mock_db.commit = MagicMock()
        container.get_service = MagicMock(return_value=mock_db)
        
        # Act
        await scheduler.initialize()
        
        # Assert
        assert scheduler.priority_queue is not None
        assert scheduler.retry_manager is not None
        assert scheduler.retry_tracker is not None
    
    async def test_high_priority_task_executes_first(self):
        """Test that high priority tasks execute before low priority"""
        # Arrange
        container = MagicMock()
        container.config = MagicMock()
        container.config.get = MagicMock(return_value={"max_concurrent_tasks": 1})
        
        scheduler = TaskScheduler("test_scheduler", container)
        
        mock_db = MagicMock()
        mock_db.execute = MagicMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))
        container.get_service = MagicMock(return_value=mock_db)
        
        await scheduler.initialize()
        
        # Register tasks
        scheduler.task_registry.tasks["test.success"] = MockSuccessTask
        scheduler.task_registry.tasks["test.high_priority"] = MockHighPriorityTask
        
        # Enqueue low priority first, then high priority
        scheduler.priority_queue.enqueue(
            "test.success",
            "MockSuccessTask",
            TaskPriority.NORMAL,
            TaskQueue.BACKGROUND_LIGHT
        )
        scheduler.priority_queue.enqueue(
            "test.high_priority",
            "MockHighPriorityTask",
            TaskPriority.HIGH,
            TaskQueue.USER_FACING
        )
        
        # Act - Dequeue with fair scheduling
        first_task = scheduler.priority_queue.dequeue()
        
        # Assert - High priority USER_FACING task should come first
        assert first_task.task_id == "test.high_priority"


@pytest.mark.asyncio
class TestSchedulerRetryLogic:
    """Test scheduler retry logic"""
    
    async def test_retry_tracker_records_failures(self):
        """Test that retry tracker records task failures"""
        # Arrange
        container = MagicMock()
        container.config = MagicMock()
        container.config.get = MagicMock(return_value={})
        
        scheduler = TaskScheduler("test_scheduler", container)
        
        mock_db = MagicMock()
        mock_db.execute = MagicMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))
        container.get_service = MagicMock(return_value=mock_db)
        
        await scheduler.initialize()
        
        # Act
        scheduler.retry_tracker.record_failure("test.task", "Connection timeout")
        scheduler.retry_tracker.record_failure("test.task", "Database error")
        
        # Assert
        assert scheduler.retry_tracker.get_retry_count("test.task") == 2
        history = scheduler.retry_tracker.get_failure_history("test.task")
        assert len(history) == 2
        assert "Connection timeout" in history
    
    async def test_retry_tracker_clears_on_success(self):
        """Test that retry tracker clears history on success"""
        # Arrange
        container = MagicMock()
        container.config = MagicMock()
        container.config.get = MagicMock(return_value={})
        
        scheduler = TaskScheduler("test_scheduler", container)
        
        mock_db = MagicMock()
        mock_db.execute = MagicMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))
        container.get_service = MagicMock(return_value=mock_db)
        
        await scheduler.initialize()
        
        # Record failures
        scheduler.retry_tracker.record_failure("test.task", "Error 1")
        scheduler.retry_tracker.record_failure("test.task", "Error 2")
        
        # Act
        scheduler.retry_tracker.record_success("test.task")
        
        # Assert
        assert scheduler.retry_tracker.get_retry_count("test.task") == 0
        assert scheduler.retry_tracker.get_failure_history("test.task") == []
    
    async def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation"""
        # Arrange
        container = MagicMock()
        container.config = MagicMock()
        container.config.get = MagicMock(return_value={})
        
        scheduler = TaskScheduler("test_scheduler", container)
        
        mock_db = MagicMock()
        mock_db.execute = MagicMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))
        container.get_service = MagicMock(return_value=mock_db)
        
        await scheduler.initialize()
        
        # Create retry config
        from backend.scheduler.tasks.base import RetryConfig, RetryStrategy
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay_seconds=10,
            jitter=False
        )
        
        # Act & Assert
        delay0 = scheduler.retry_manager.calculate_delay(0, config)
        delay1 = scheduler.retry_manager.calculate_delay(1, config)
        delay2 = scheduler.retry_manager.calculate_delay(2, config)
        
        assert delay0 == 10   # 10 * 2^0
        assert delay1 == 20   # 10 * 2^1
        assert delay2 == 40   # 10 * 2^2


@pytest.mark.asyncio
class TestSchedulerTaskCancellation:
    """Test task cancellation functionality"""
    
    async def test_cancel_queued_task(self):
        """Test cancelling a task in the queue"""
        # Arrange
        container = MagicMock()
        container.config = MagicMock()
        container.config.get = MagicMock(return_value={})
        
        scheduler = TaskScheduler("test_scheduler", container)
        
        mock_db = MagicMock()
        mock_db.execute = MagicMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))
        container.get_service = MagicMock(return_value=mock_db)
        
        await scheduler.initialize()
        
        # Enqueue a task
        scheduler.priority_queue.enqueue(
            "test.task",
            "TestTask",
            TaskPriority.NORMAL,
            TaskQueue.BACKGROUND_LIGHT
        )
        
        # Act
        cancelled = await scheduler.cancel_task("test.task")
        
        # Assert
        assert cancelled is True
        stats = scheduler.priority_queue.get_stats()
        assert stats[TaskQueue.BACKGROUND_LIGHT.value] == 0
    
    async def test_cancel_nonexistent_task(self):
        """Test cancelling a task that doesn't exist"""
        # Arrange
        container = MagicMock()
        container.config = MagicMock()
        container.config.get = MagicMock(return_value={})
        
        scheduler = TaskScheduler("test_scheduler", container)
        
        mock_db = MagicMock()
        mock_db.execute = MagicMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))
        container.get_service = MagicMock(return_value=mock_db)
        
        await scheduler.initialize()
        
        # Act
        cancelled = await scheduler.cancel_task("nonexistent.task")
        
        # Assert
        assert cancelled is False


@pytest.mark.asyncio
class TestSchedulerQueueStatistics:
    """Test queue statistics and monitoring"""
    
    async def test_get_queue_statistics(self):
        """Test getting queue statistics"""
        # Arrange
        container = MagicMock()
        container.config = MagicMock()
        container.config.get = MagicMock(return_value={})
        
        scheduler = TaskScheduler("test_scheduler", container)
        
        mock_db = MagicMock()
        mock_db.execute = MagicMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))
        container.get_service = MagicMock(return_value=mock_db)
        
        await scheduler.initialize()
        
        # Enqueue tasks to different queues
        scheduler.priority_queue.enqueue(
            "task-1", "TestTask", TaskPriority.NORMAL, TaskQueue.USER_FACING
        )
        scheduler.priority_queue.enqueue(
            "task-2", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT
        )
        scheduler.priority_queue.enqueue(
            "task-3", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT
        )
        scheduler.priority_queue.enqueue(
            "task-4", "TestTask", TaskPriority.NORMAL, TaskQueue.MAINTENANCE
        )
        
        # Act
        stats = scheduler.priority_queue.get_stats()
        
        # Assert
        assert stats[TaskQueue.USER_FACING.value] == 1
        assert stats[TaskQueue.BACKGROUND_LIGHT.value] == 2
        assert stats[TaskQueue.BACKGROUND_HEAVY.value] == 0
        assert stats[TaskQueue.MAINTENANCE.value] == 1
    
    async def test_clear_specific_queue(self):
        """Test clearing a specific queue"""
        # Arrange
        container = MagicMock()
        container.config = MagicMock()
        container.config.get = MagicMock(return_value={})
        
        scheduler = TaskScheduler("test_scheduler", container)
        
        mock_db = MagicMock()
        mock_db.execute = MagicMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))
        container.get_service = MagicMock(return_value=mock_db)
        
        await scheduler.initialize()
        
        # Enqueue tasks
        scheduler.priority_queue.enqueue(
            "task-1", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT
        )
        scheduler.priority_queue.enqueue(
            "task-2", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_HEAVY
        )
        
        # Act
        scheduler.priority_queue.clear(TaskQueue.BACKGROUND_LIGHT)
        
        # Assert
        stats = scheduler.priority_queue.get_stats()
        assert stats[TaskQueue.BACKGROUND_LIGHT.value] == 0
        assert stats[TaskQueue.BACKGROUND_HEAVY.value] == 1
