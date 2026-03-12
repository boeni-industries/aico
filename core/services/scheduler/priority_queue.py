"""
Priority Queue for Task Scheduling

Implements a priority-based task queue with support for multiple queues,
preemption, and fair scheduling across different priority levels.

Phase 6.2: Production Scheduler
"""

import heapq
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from aico.core.logging import get_logger
from .tasks.base import TaskPriority, TaskQueue


logger = get_logger("core.scheduler.priority_queue")


@dataclass(order=True)
class PrioritizedTask:
    """Task wrapper for priority queue ordering"""
    
    # Priority fields (used for ordering)
    priority: int = field(compare=True)  # Lower number = higher priority
    enqueued_at: datetime = field(compare=True)  # FIFO within same priority
    
    # Task data (not used for ordering)
    task_id: str = field(compare=False)
    task_class: str = field(compare=False)
    config: Dict = field(compare=False, default_factory=dict)
    queue: str = field(compare=False, default="background_light")
    retry_count: int = field(compare=False, default=0)
    unique_key: str = field(compare=False, default="")
    run_key: Optional[str] = field(compare=False, default=None)
    scheduled_for: Optional[str] = field(compare=False, default=None)
    tenant_id: Optional[str] = field(compare=False, default=None)
    
    def __post_init__(self):
        """Add small random jitter to prevent ties"""
        # Add microseconds jitter to enqueued_at to break ties
        if isinstance(self.enqueued_at, datetime):
            jitter_us = random.randint(0, 999)
            self.enqueued_at = self.enqueued_at.replace(microsecond=jitter_us)
        if not self.unique_key:
            self.unique_key = self.run_key or self.task_id


class PriorityTaskQueue:
    """Multi-queue priority scheduler with fair scheduling"""
    
    def __init__(self, max_queue_size: int = 1000):
        """Initialize priority queue system
        
        Args:
            max_queue_size: Maximum tasks per queue (prevents unbounded growth)
        """
        self.max_queue_size = max_queue_size
        
        # Separate heaps for each queue type
        self.queues: Dict[str, List[PrioritizedTask]] = {
            TaskQueue.USER_FACING.value: [],
            TaskQueue.BACKGROUND_LIGHT.value: [],
            TaskQueue.BACKGROUND_HEAVY.value: [],
            TaskQueue.MAINTENANCE.value: []
        }
        
        # Track queue sizes for metrics
        self.queue_sizes: Dict[str, int] = {q: 0 for q in self.queues.keys()}

        # Track which task_ids are currently enqueued to prevent duplicates
        self._enqueued_task_ids: set[str] = set()
        
        # Track last execution time per queue for fairness
        self.last_execution: Dict[str, datetime] = {}
        
        logger.info("Priority task queue initialized")
    
    def enqueue(self, 
                task_id: str,
                task_class: str,
                priority: TaskPriority,
                queue: TaskQueue,
                config: Optional[Dict] = None,
                retry_count: int = 0,
                unique_key: Optional[str] = None,
                run_key: Optional[str] = None,
                scheduled_for: Optional[str] = None,
                tenant_id: Optional[str] = None) -> bool:
        """Add task to appropriate priority queue
        
        Args:
            task_id: Unique task identifier
            task_class: Task class name
            priority: Task priority level
            queue: Queue type
            config: Task configuration
            retry_count: Number of previous retry attempts
            
        Returns:
            True if enqueued successfully, False if queue is full
        """
        queue_name = queue.value
        dedupe_key = unique_key or run_key or task_id

        # Prevent duplicate enqueues of the same logical queue item.
        # For deterministic scheduled runs this must be the per-run identity,
        # not only the task_id, otherwise multiple due runs collapse into one.
        if dedupe_key in self._enqueued_task_ids:
            logger.debug(f"Task {task_id} ({dedupe_key}) is already enqueued, skipping duplicate enqueue")
            return False
        
        # Check queue capacity
        if self.queue_sizes[queue_name] >= self.max_queue_size:
            logger.warning(
                f"Queue {queue_name} is full ({self.max_queue_size} tasks), "
                f"rejecting task {task_id}"
            )
            return False
        
        # Create prioritized task
        task = PrioritizedTask(
            priority=priority.value,
            enqueued_at=datetime.now(timezone.utc),
            task_id=task_id,
            task_class=task_class,
            config=config or {},
            queue=queue_name,
            retry_count=retry_count,
            unique_key=dedupe_key,
            run_key=run_key,
            scheduled_for=scheduled_for,
            tenant_id=tenant_id,
        )
        
        # Add to appropriate heap
        heapq.heappush(self.queues[queue_name], task)
        self.queue_sizes[queue_name] += 1
        self._enqueued_task_ids.add(dedupe_key)
        
        logger.debug(
            f"Enqueued task {task_id} to {queue_name} queue "
            f"(priority={priority.name}, size={self.queue_sizes[queue_name]})"
        )
        
        return True

    def has_task(self, key: str) -> bool:
        """Return True if the logical queue item key is currently enqueued."""
        return key in self._enqueued_task_ids
    
    def dequeue(self, queue: Optional[TaskQueue] = None) -> Optional[PrioritizedTask]:
        """Remove and return highest priority task
        
        Args:
            queue: Specific queue to dequeue from, or None for fair scheduling
            
        Returns:
            PrioritizedTask or None if no tasks available
        """
        if queue:
            # Dequeue from specific queue
            return self._dequeue_from_queue(queue.value)
        
        # Fair scheduling across all queues
        return self._fair_dequeue()
    
    def _dequeue_from_queue(self, queue_name: str) -> Optional[PrioritizedTask]:
        """Dequeue from specific queue"""
        if self.queue_sizes[queue_name] == 0:
            return None
        
        task = heapq.heappop(self.queues[queue_name])
        self.queue_sizes[queue_name] -= 1
        self.last_execution[queue_name] = datetime.now(timezone.utc)
        self._enqueued_task_ids.discard(task.unique_key)
        
        logger.debug(
            f"Dequeued task {task.task_id} from {queue_name} "
            f"(priority={task.priority}, remaining={self.queue_sizes[queue_name]})"
        )
        
        return task
    
    def _fair_dequeue(self) -> Optional[PrioritizedTask]:
        """Fair scheduling across queues with priority consideration
        
        Strategy:
        1. USER_FACING queue gets highest priority
        2. Among background queues, use weighted round-robin based on:
           - Task priority
           - Time since last execution
           - Queue type weights
        """
        # Always prioritize user-facing tasks
        if self.queue_sizes[TaskQueue.USER_FACING.value] > 0:
            return self._dequeue_from_queue(TaskQueue.USER_FACING.value)
        
        # Weighted selection for background queues
        candidates = []
        now = datetime.now(timezone.utc)
        
        for queue_name in [
            TaskQueue.BACKGROUND_LIGHT.value,
            TaskQueue.BACKGROUND_HEAVY.value,
            TaskQueue.MAINTENANCE.value
        ]:
            if self.queue_sizes[queue_name] == 0:
                continue
            
            # Peek at highest priority task in this queue
            task = self.queues[queue_name][0]
            
            # Calculate selection weight
            priority_weight = 1.0 / (task.priority + 1)  # Higher priority = higher weight
            
            # Time since last execution (favor starved queues)
            last_exec = self.last_execution.get(queue_name)
            if last_exec:
                # Ensure last_exec is timezone-aware
                if last_exec.tzinfo is None:
                    last_exec = last_exec.replace(tzinfo=timezone.utc)
                seconds_since = (now - last_exec).total_seconds()
                starvation_weight = min(seconds_since / 60.0, 5.0)  # Cap at 5x
            else:
                starvation_weight = 5.0  # Never executed = highest starvation
            
            # Queue type weight (light > heavy > maintenance)
            queue_type_weights = {
                TaskQueue.BACKGROUND_LIGHT.value: 1.5,
                TaskQueue.BACKGROUND_HEAVY.value: 1.0,
                TaskQueue.MAINTENANCE.value: 0.5
            }
            type_weight = queue_type_weights.get(queue_name, 1.0)
            
            total_weight = priority_weight * starvation_weight * type_weight
            candidates.append((total_weight, queue_name))
        
        if not candidates:
            return None
        
        # Select queue with highest weight
        selected_queue = max(candidates, key=lambda x: x[0])[1]
        return self._dequeue_from_queue(selected_queue)
    
    def peek(self, queue: TaskQueue) -> Optional[PrioritizedTask]:
        """View highest priority task without removing it
        
        Args:
            queue: Queue to peek into
            
        Returns:
            PrioritizedTask or None if queue is empty
        """
        queue_name = queue.value
        if self.queue_sizes[queue_name] == 0:
            return None
        
        return self.queues[queue_name][0]
    
    def remove(self, task_id: str) -> bool:
        """Remove specific task from queue (for cancellation)
        
        Args:
            task_id: Task to remove
            
        Returns:
            True if task was found and removed
        """
        for queue_name, heap in self.queues.items():
            for i, task in enumerate(heap):
                if task.task_id == task_id:
                    # Remove from heap and re-heapify
                    heap[i] = heap[-1]
                    heap.pop()
                    if i < len(heap):
                        heapq.heapify(heap)
                    
                    self.queue_sizes[queue_name] -= 1
                    self._enqueued_task_ids.discard(task_id)
                    logger.info(f"Removed task {task_id} from {queue_name} queue")
                    return True
        
        return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics
        
        Returns:
            Dictionary of queue names to task counts
        """
        return self.queue_sizes.copy()
    
    def clear(self, queue: Optional[TaskQueue] = None):
        """Clear all tasks from queue(s)
        
        Args:
            queue: Specific queue to clear, or None to clear all
        """
        if queue:
            queue_name = queue.value
            self.queues[queue_name] = []
            self.queue_sizes[queue_name] = 0
            # Recompute enqueued ids from remaining queues
            remaining: set[str] = set()
            for heap in self.queues.values():
                for task in heap:
                    remaining.add(task.task_id)
            self._enqueued_task_ids = remaining
            logger.info(f"Cleared {queue_name} queue")
        else:
            for queue_name in self.queues.keys():
                self.queues[queue_name] = []
                self.queue_sizes[queue_name] = 0
            self._enqueued_task_ids.clear()
            logger.info("Cleared all queues")
