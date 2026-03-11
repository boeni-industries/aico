"""
Retry Manager for Task Execution

Implements retry logic with various backoff strategies including exponential,
linear, and fibonacci backoff with jitter support.

Phase 6.2: Production Scheduler
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from aico.core.logging import get_logger
from .tasks.base import RetryConfig, RetryStrategy


logger = get_logger("backend.scheduler.retry_manager")


class RetryManager:
    """Manages task retry logic with configurable backoff strategies"""
    
    @staticmethod
    def should_retry(retry_count: int, retry_config: RetryConfig) -> bool:
        """Determine if task should be retried
        
        Args:
            retry_count: Current retry attempt count
            retry_config: Retry configuration
            
        Returns:
            True if task should be retried
        """
        if retry_config.strategy == RetryStrategy.NONE:
            return False
        
        return retry_count < retry_config.max_retries
    
    @staticmethod
    def calculate_delay(retry_count: int, retry_config: RetryConfig) -> int:
        """Calculate retry delay in seconds
        
        Args:
            retry_count: Current retry attempt count (0-indexed)
            retry_config: Retry configuration
            
        Returns:
            Delay in seconds before next retry
        """
        if retry_config.strategy == RetryStrategy.NONE:
            return 0
        
        if retry_config.strategy == RetryStrategy.IMMEDIATE:
            delay = 0
        
        elif retry_config.strategy == RetryStrategy.LINEAR:
            # Linear: delay = base_delay * (retry_count + 1)
            delay = retry_config.base_delay_seconds * (retry_count + 1)
        
        elif retry_config.strategy == RetryStrategy.EXPONENTIAL:
            # Exponential: delay = base_delay * (2 ^ retry_count)
            delay = retry_config.base_delay_seconds * (2 ** retry_count)
        
        elif retry_config.strategy == RetryStrategy.FIBONACCI:
            # Fibonacci: delay = base_delay * fib(retry_count + 2)
            fib_value = RetryManager._fibonacci(retry_count + 2)
            delay = retry_config.base_delay_seconds * fib_value
        
        else:
            # Default to exponential
            delay = retry_config.base_delay_seconds * (2 ** retry_count)
        
        # Cap at max_delay
        delay = min(delay, retry_config.max_delay_seconds)
        
        # Add jitter if enabled (±25% random variation)
        if retry_config.jitter and delay > 0:
            jitter_range = delay * 0.25
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = int(delay + jitter)
        
        # Ensure non-negative
        delay = max(0, delay)
        
        logger.debug(
            f"Calculated retry delay: {delay}s "
            f"(strategy={retry_config.strategy.value}, attempt={retry_count})"
        )
        
        return delay
    
    @staticmethod
    def _fibonacci(n: int) -> int:
        """Calculate nth Fibonacci number
        
        Args:
            n: Position in Fibonacci sequence
            
        Returns:
            Fibonacci number at position n
        """
        if n <= 1:
            return n
        
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        
        return b
    
    @staticmethod
    def get_next_retry_time(retry_count: int, retry_config: RetryConfig) -> Optional[datetime]:
        """Calculate next retry time
        
        Args:
            retry_count: Current retry attempt count
            retry_config: Retry configuration
            
        Returns:
            Datetime for next retry, or None if no retry
        """
        if not RetryManager.should_retry(retry_count, retry_config):
            return None
        
        delay_seconds = RetryManager.calculate_delay(retry_count, retry_config)
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        
        logger.info(
            f"Next retry scheduled for {next_retry.isoformat()} "
            f"(in {delay_seconds}s, attempt {retry_count + 1}/{retry_config.max_retries})"
        )
        
        return next_retry
    
    @staticmethod
    def format_retry_info(retry_count: int, retry_config: RetryConfig) -> str:
        """Format retry information for logging
        
        Args:
            retry_count: Current retry attempt count
            retry_config: Retry configuration
            
        Returns:
            Human-readable retry information
        """
        if retry_count == 0:
            return "First attempt"
        
        delay = RetryManager.calculate_delay(retry_count - 1, retry_config)
        return (
            f"Retry {retry_count}/{retry_config.max_retries} "
            f"(after {delay}s {retry_config.strategy.value} backoff)"
        )


class RetryTracker:
    """Tracks retry attempts for tasks"""
    
    def __init__(self):
        """Initialize retry tracker"""
        self.retry_counts: dict[str, int] = {}
        self.last_failure: dict[str, datetime] = {}
        self.failure_reasons: dict[str, list[str]] = {}
    
    def record_failure(self, task_id: str, reason: str):
        """Record task failure
        
        Args:
            task_id: Task identifier
            reason: Failure reason
        """
        self.retry_counts[task_id] = self.retry_counts.get(task_id, 0) + 1
        self.last_failure[task_id] = datetime.now(timezone.utc)
        
        if task_id not in self.failure_reasons:
            self.failure_reasons[task_id] = []
        self.failure_reasons[task_id].append(reason)
        
        # Keep only last 10 failure reasons
        if len(self.failure_reasons[task_id]) > 10:
            self.failure_reasons[task_id] = self.failure_reasons[task_id][-10:]
        
        logger.debug(
            f"Recorded failure for {task_id}: {reason} "
            f"(total failures: {self.retry_counts[task_id]})"
        )
    
    def record_success(self, task_id: str):
        """Record task success (clears retry history)
        
        Args:
            task_id: Task identifier
        """
        if task_id in self.retry_counts:
            del self.retry_counts[task_id]
        if task_id in self.last_failure:
            del self.last_failure[task_id]
        if task_id in self.failure_reasons:
            del self.failure_reasons[task_id]
        
        logger.debug(f"Cleared retry history for {task_id} (success)")
    
    def get_retry_count(self, task_id: str) -> int:
        """Get current retry count for task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Number of retry attempts
        """
        return self.retry_counts.get(task_id, 0)
    
    def get_failure_history(self, task_id: str) -> list[str]:
        """Get failure history for task
        
        Args:
            task_id: Task identifier
            
        Returns:
            List of failure reasons
        """
        return self.failure_reasons.get(task_id, [])
    
    def is_recently_failed(self, task_id: str, within_seconds: int = 60) -> bool:
        """Check if task failed recently
        
        Args:
            task_id: Task identifier
            within_seconds: Time window in seconds
            
        Returns:
            True if task failed within time window
        """
        if task_id not in self.last_failure:
            return False
        
        time_since_failure = (datetime.now(timezone.utc) - self.last_failure[task_id]).total_seconds()
        return time_since_failure < within_seconds
    
    def clear(self, task_id: Optional[str] = None):
        """Clear retry history
        
        Args:
            task_id: Specific task to clear, or None to clear all
        """
        if task_id:
            if task_id in self.retry_counts:
                del self.retry_counts[task_id]
            if task_id in self.last_failure:
                del self.last_failure[task_id]
            if task_id in self.failure_reasons:
                del self.failure_reasons[task_id]
            logger.debug(f"Cleared retry history for {task_id}")
        else:
            self.retry_counts.clear()
            self.last_failure.clear()
            self.failure_reasons.clear()
            logger.info("Cleared all retry history")
