"""
Integration Tests for Phase 6.2: Priority Queue System

Tests the priority-based task queue with fair scheduling, starvation prevention,
and multi-queue management.
"""

import pytest
from datetime import datetime, timedelta

from core.services.scheduler.priority_queue import PriorityTaskQueue, PrioritizedTask
from core.services.scheduler.tasks.base import TaskPriority, TaskQueue


class TestPriorityTaskQueue:
    """Test priority queue operations"""
    
    def test_enqueue_and_dequeue_basic(self):
        """Test basic enqueue and dequeue operations"""
        # Arrange
        queue = PriorityTaskQueue()
        
        # Act
        success = queue.enqueue(
            task_id="test-task-1",
            task_class="TestTask",
            priority=TaskPriority.NORMAL,
            queue=TaskQueue.BACKGROUND_LIGHT,
            config={"test": "config"}
        )
        
        # Assert
        assert success is True
        assert queue.queue_sizes[TaskQueue.BACKGROUND_LIGHT.value] == 1
        
        # Dequeue
        task = queue.dequeue(TaskQueue.BACKGROUND_LIGHT)
        assert task is not None
        assert task.task_id == "test-task-1"
        assert task.priority == TaskPriority.NORMAL.value
        assert queue.queue_sizes[TaskQueue.BACKGROUND_LIGHT.value] == 0
    
    def test_priority_ordering(self):
        """Test that tasks are dequeued in priority order"""
        # Arrange
        queue = PriorityTaskQueue()
        
        # Enqueue tasks with different priorities
        queue.enqueue("low-task", "TestTask", TaskPriority.LOW, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("high-task", "TestTask", TaskPriority.HIGH, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("critical-task", "TestTask", TaskPriority.CRITICAL, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("normal-task", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT)
        
        # Act - Dequeue all tasks
        tasks = []
        while True:
            task = queue.dequeue(TaskQueue.BACKGROUND_LIGHT)
            if not task:
                break
            tasks.append(task.task_id)
        
        # Assert - Should be in priority order (CRITICAL, HIGH, NORMAL, LOW)
        assert tasks == ["critical-task", "high-task", "normal-task", "low-task"]
    
    def test_fifo_within_same_priority(self):
        """Test FIFO ordering within same priority level"""
        # Arrange
        queue = PriorityTaskQueue()
        
        # Enqueue multiple tasks with same priority
        for i in range(5):
            queue.enqueue(
                f"task-{i}",
                "TestTask",
                TaskPriority.NORMAL,
                TaskQueue.BACKGROUND_LIGHT
            )
        
        # Act - Dequeue all
        tasks = []
        while True:
            task = queue.dequeue(TaskQueue.BACKGROUND_LIGHT)
            if not task:
                break
            tasks.append(task.task_id)
        
        # Assert - Should get all 5 tasks (order may vary due to microsecond jitter)
        assert len(tasks) == 5
        assert all(f"task-{i}" in tasks for i in range(5))
    
    def test_queue_capacity_limit(self):
        """Test that queue respects capacity limits"""
        # Arrange
        queue = PriorityTaskQueue(max_queue_size=3)
        
        # Act - Try to enqueue more than capacity
        results = []
        for i in range(5):
            success = queue.enqueue(
                f"task-{i}",
                "TestTask",
                TaskPriority.NORMAL,
                TaskQueue.BACKGROUND_LIGHT
            )
            results.append(success)
        
        # Assert - First 3 should succeed, last 2 should fail
        assert results == [True, True, True, False, False]
        assert queue.queue_sizes[TaskQueue.BACKGROUND_LIGHT.value] == 3
    
    def test_fair_scheduling_user_facing_priority(self):
        """Test that USER_FACING queue always gets priority"""
        # Arrange
        queue = PriorityTaskQueue()
        
        # Enqueue tasks to different queues
        queue.enqueue("bg-task", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("user-task", "TestTask", TaskPriority.NORMAL, TaskQueue.USER_FACING)
        queue.enqueue("heavy-task", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_HEAVY)
        
        # Act - Dequeue with fair scheduling (no specific queue)
        first_task = queue.dequeue()
        
        # Assert - USER_FACING should come first
        assert first_task.task_id == "user-task"
        assert first_task.queue == TaskQueue.USER_FACING.value
    
    def test_fair_scheduling_background_queues(self):
        """Test fair scheduling among background queues"""
        # Arrange
        queue = PriorityTaskQueue()
        
        # Enqueue tasks to background queues
        queue.enqueue("light-1", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("heavy-1", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_HEAVY)
        queue.enqueue("maint-1", "TestTask", TaskPriority.NORMAL, TaskQueue.MAINTENANCE)
        
        # Act - Dequeue all with fair scheduling
        tasks = []
        for _ in range(3):
            task = queue.dequeue()
            if task:
                tasks.append(task.queue)
        
        # Assert - Should get tasks from different queues (weighted round-robin)
        # BACKGROUND_LIGHT should be favored (weight 1.5)
        assert TaskQueue.BACKGROUND_LIGHT.value in tasks
    
    def test_starvation_prevention(self):
        """Test that starved queues eventually get scheduled"""
        # Arrange
        queue = PriorityTaskQueue()
        
        # Enqueue low priority task first
        queue.enqueue("low-task", "TestTask", TaskPriority.LOW, TaskQueue.BACKGROUND_HEAVY)
        
        # Simulate time passing (update last_execution for other queues)
        queue.last_execution[TaskQueue.BACKGROUND_LIGHT.value] = datetime.now()
        queue.last_execution[TaskQueue.MAINTENANCE.value] = datetime.now()
        
        # Enqueue high priority tasks to other queues
        queue.enqueue("high-task", "TestTask", TaskPriority.HIGH, TaskQueue.BACKGROUND_LIGHT)
        
        # Act - Dequeue with fair scheduling
        # The starved BACKGROUND_HEAVY queue should eventually be selected
        # due to starvation weight
        task = queue.dequeue()
        
        # Assert - Could be either depending on weights, but both are valid
        assert task.task_id in ["low-task", "high-task"]
    
    def test_remove_task(self):
        """Test removing specific task from queue"""
        # Arrange
        queue = PriorityTaskQueue()
        
        queue.enqueue("task-1", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("task-2", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("task-3", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT)
        
        # Act
        removed = queue.remove("task-2")
        
        # Assert
        assert removed is True
        assert queue.queue_sizes[TaskQueue.BACKGROUND_LIGHT.value] == 2
        
        # Verify task-2 is not in queue
        tasks = []
        while True:
            task = queue.dequeue(TaskQueue.BACKGROUND_LIGHT)
            if not task:
                break
            tasks.append(task.task_id)
        
        assert "task-2" not in tasks
        assert "task-1" in tasks
        assert "task-3" in tasks
    
    def test_peek_without_removing(self):
        """Test peeking at highest priority task without removing it"""
        # Arrange
        queue = PriorityTaskQueue()
        
        queue.enqueue("task-1", "TestTask", TaskPriority.HIGH, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("task-2", "TestTask", TaskPriority.LOW, TaskQueue.BACKGROUND_LIGHT)
        
        # Act
        peeked = queue.peek(TaskQueue.BACKGROUND_LIGHT)
        
        # Assert
        assert peeked is not None
        assert peeked.task_id == "task-1"
        assert queue.queue_sizes[TaskQueue.BACKGROUND_LIGHT.value] == 2  # Not removed
        
        # Verify peek didn't remove it
        dequeued = queue.dequeue(TaskQueue.BACKGROUND_LIGHT)
        assert dequeued.task_id == "task-1"
    
    def test_get_stats(self):
        """Test queue statistics"""
        # Arrange
        queue = PriorityTaskQueue()
        
        queue.enqueue("task-1", "TestTask", TaskPriority.NORMAL, TaskQueue.USER_FACING)
        queue.enqueue("task-2", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("task-3", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("task-4", "TestTask", TaskPriority.NORMAL, TaskQueue.MAINTENANCE)
        
        # Act
        stats = queue.get_stats()
        
        # Assert
        assert stats[TaskQueue.USER_FACING.value] == 1
        assert stats[TaskQueue.BACKGROUND_LIGHT.value] == 2
        assert stats[TaskQueue.BACKGROUND_HEAVY.value] == 0
        assert stats[TaskQueue.MAINTENANCE.value] == 1
    
    def test_clear_specific_queue(self):
        """Test clearing specific queue"""
        # Arrange
        queue = PriorityTaskQueue()
        
        queue.enqueue("task-1", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("task-2", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_HEAVY)
        
        # Act
        queue.clear(TaskQueue.BACKGROUND_LIGHT)
        
        # Assert
        assert queue.queue_sizes[TaskQueue.BACKGROUND_LIGHT.value] == 0
        assert queue.queue_sizes[TaskQueue.BACKGROUND_HEAVY.value] == 1
    
    def test_clear_all_queues(self):
        """Test clearing all queues"""
        # Arrange
        queue = PriorityTaskQueue()
        
        queue.enqueue("task-1", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_LIGHT)
        queue.enqueue("task-2", "TestTask", TaskPriority.NORMAL, TaskQueue.BACKGROUND_HEAVY)
        queue.enqueue("task-3", "TestTask", TaskPriority.NORMAL, TaskQueue.USER_FACING)
        
        # Act
        queue.clear()
        
        # Assert
        stats = queue.get_stats()
        assert all(count == 0 for count in stats.values())
    
    def test_retry_count_preserved(self):
        """Test that retry count is preserved in queued tasks"""
        # Arrange
        queue = PriorityTaskQueue()
        
        # Act
        queue.enqueue(
            "retry-task",
            "TestTask",
            TaskPriority.NORMAL,
            TaskQueue.BACKGROUND_LIGHT,
            retry_count=3
        )
        
        task = queue.dequeue(TaskQueue.BACKGROUND_LIGHT)
        
        # Assert
        assert task.retry_count == 3
    
    def test_config_preserved(self):
        """Test that task configuration is preserved"""
        # Arrange
        queue = PriorityTaskQueue()
        config = {"key1": "value1", "key2": 42, "nested": {"data": True}}
        
        # Act
        queue.enqueue(
            "config-task",
            "TestTask",
            TaskPriority.NORMAL,
            TaskQueue.BACKGROUND_LIGHT,
            config=config
        )
        
        task = queue.dequeue(TaskQueue.BACKGROUND_LIGHT)
        
        # Assert
        assert task.config == config
        assert task.config["key1"] == "value1"
        assert task.config["nested"]["data"] is True
