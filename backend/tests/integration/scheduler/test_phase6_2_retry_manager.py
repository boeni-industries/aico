"""
Integration Tests for Phase 6.2: Retry Manager

Tests retry logic with various backoff strategies, jitter, and retry tracking.
"""

import pytest
from datetime import datetime, timedelta

from backend.scheduler.retry_manager import RetryManager, RetryTracker
from backend.scheduler.tasks.base import RetryConfig, RetryStrategy


class TestRetryManager:
    """Test retry manager calculations"""
    
    def test_should_retry_within_limit(self):
        """Test that retry is allowed within max_retries"""
        # Arrange
        config = RetryConfig(max_retries=3)
        
        # Act & Assert
        assert RetryManager.should_retry(0, config) is True
        assert RetryManager.should_retry(1, config) is True
        assert RetryManager.should_retry(2, config) is True
        assert RetryManager.should_retry(3, config) is False  # Exceeded
    
    def test_should_retry_none_strategy(self):
        """Test that NONE strategy never retries"""
        # Arrange
        config = RetryConfig(strategy=RetryStrategy.NONE, max_retries=5)
        
        # Act & Assert
        assert RetryManager.should_retry(0, config) is False
        assert RetryManager.should_retry(1, config) is False
    
    def test_immediate_retry_delay(self):
        """Test IMMEDIATE strategy has zero delay"""
        # Arrange
        config = RetryConfig(strategy=RetryStrategy.IMMEDIATE, jitter=False)
        
        # Act
        delay = RetryManager.calculate_delay(0, config)
        
        # Assert
        assert delay == 0
    
    def test_linear_backoff(self):
        """Test LINEAR backoff strategy"""
        # Arrange
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR,
            base_delay_seconds=10,
            jitter=False
        )
        
        # Act & Assert
        assert RetryManager.calculate_delay(0, config) == 10  # 10 * 1
        assert RetryManager.calculate_delay(1, config) == 20  # 10 * 2
        assert RetryManager.calculate_delay(2, config) == 30  # 10 * 3
        assert RetryManager.calculate_delay(3, config) == 40  # 10 * 4
    
    def test_exponential_backoff(self):
        """Test EXPONENTIAL backoff strategy"""
        # Arrange
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay_seconds=10,
            jitter=False
        )
        
        # Act & Assert
        assert RetryManager.calculate_delay(0, config) == 10   # 10 * 2^0
        assert RetryManager.calculate_delay(1, config) == 20   # 10 * 2^1
        assert RetryManager.calculate_delay(2, config) == 40   # 10 * 2^2
        assert RetryManager.calculate_delay(3, config) == 80   # 10 * 2^3
        assert RetryManager.calculate_delay(4, config) == 160  # 10 * 2^4
    
    def test_fibonacci_backoff(self):
        """Test FIBONACCI backoff strategy"""
        # Arrange
        config = RetryConfig(
            strategy=RetryStrategy.FIBONACCI,
            base_delay_seconds=10,
            jitter=False
        )
        
        # Act & Assert
        # Fibonacci: 1, 1, 2, 3, 5, 8, 13, 21...
        assert RetryManager.calculate_delay(0, config) == 10   # 10 * fib(2) = 10 * 1
        assert RetryManager.calculate_delay(1, config) == 20   # 10 * fib(3) = 10 * 2
        assert RetryManager.calculate_delay(2, config) == 30   # 10 * fib(4) = 10 * 3
        assert RetryManager.calculate_delay(3, config) == 50   # 10 * fib(5) = 10 * 5
        assert RetryManager.calculate_delay(4, config) == 80   # 10 * fib(6) = 10 * 8
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay_seconds"""
        # Arrange
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay_seconds=100,
            max_delay_seconds=500,
            jitter=False
        )
        
        # Act
        delay = RetryManager.calculate_delay(10, config)  # Would be 100 * 2^10 = 102400
        
        # Assert
        assert delay == 500  # Capped at max_delay
    
    def test_jitter_adds_variation(self):
        """Test that jitter adds random variation"""
        # Arrange
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay_seconds=100,
            jitter=True
        )
        
        # Act - Calculate delay multiple times
        delays = [RetryManager.calculate_delay(2, config) for _ in range(10)]
        
        # Assert - Should have variation (not all the same)
        # Base delay would be 400 (100 * 2^2)
        # With ±25% jitter, range is 300-500
        assert len(set(delays)) > 1  # Not all the same
        assert all(300 <= d <= 500 for d in delays)  # Within jitter range
    
    def test_get_next_retry_time(self):
        """Test next retry time calculation"""
        from datetime import timezone
        # Arrange
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR,
            base_delay_seconds=60,
            jitter=False
        )
        
        # Act
        before = datetime.now(timezone.utc)
        next_retry = RetryManager.get_next_retry_time(1, config)
        after = datetime.now(timezone.utc)
        
        # Assert
        assert next_retry is not None
        # Should be approximately 120 seconds from now (60 * 2)
        expected_time = before + timedelta(seconds=120)
        time_diff = abs((next_retry - expected_time).total_seconds())
        assert time_diff < 1  # Within 1 second tolerance
    
    def test_get_next_retry_time_max_retries_exceeded(self):
        """Test that next retry time is None when max retries exceeded"""
        # Arrange
        config = RetryConfig(max_retries=3)
        
        # Act
        next_retry = RetryManager.get_next_retry_time(3, config)
        
        # Assert
        assert next_retry is None
    
    def test_format_retry_info_first_attempt(self):
        """Test retry info formatting for first attempt"""
        # Arrange
        config = RetryConfig()
        
        # Act
        info = RetryManager.format_retry_info(0, config)
        
        # Assert
        assert info == "First attempt"
    
    def test_format_retry_info_retry_attempt(self):
        """Test retry info formatting for retry attempts"""
        # Arrange
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL,
            max_retries=5,
            base_delay_seconds=60,
            jitter=False
        )
        
        # Act
        info = RetryManager.format_retry_info(2, config)
        
        # Assert
        assert "Retry 2/5" in info
        assert "120s" in info  # Delay from previous attempt (60 * 2^1)
        assert "exponential" in info


class TestRetryTracker:
    """Test retry tracking functionality"""
    
    def test_record_failure(self):
        """Test recording task failure"""
        # Arrange
        tracker = RetryTracker()
        
        # Act
        tracker.record_failure("task-1", "Connection timeout")
        
        # Assert
        assert tracker.get_retry_count("task-1") == 1
        assert "Connection timeout" in tracker.get_failure_history("task-1")
    
    def test_record_multiple_failures(self):
        """Test recording multiple failures"""
        # Arrange
        tracker = RetryTracker()
        
        # Act
        tracker.record_failure("task-1", "Error 1")
        tracker.record_failure("task-1", "Error 2")
        tracker.record_failure("task-1", "Error 3")
        
        # Assert
        assert tracker.get_retry_count("task-1") == 3
        history = tracker.get_failure_history("task-1")
        assert len(history) == 3
        assert "Error 1" in history
        assert "Error 2" in history
        assert "Error 3" in history
    
    def test_record_success_clears_history(self):
        """Test that recording success clears retry history"""
        # Arrange
        tracker = RetryTracker()
        tracker.record_failure("task-1", "Error 1")
        tracker.record_failure("task-1", "Error 2")
        
        # Act
        tracker.record_success("task-1")
        
        # Assert
        assert tracker.get_retry_count("task-1") == 0
        assert tracker.get_failure_history("task-1") == []
    
    def test_failure_history_limited_to_10(self):
        """Test that failure history is limited to last 10 entries"""
        # Arrange
        tracker = RetryTracker()
        
        # Act - Record 15 failures
        for i in range(15):
            tracker.record_failure("task-1", f"Error {i}")
        
        # Assert
        history = tracker.get_failure_history("task-1")
        assert len(history) == 10
        # Should have last 10 (errors 5-14)
        assert "Error 5" in history
        assert "Error 14" in history
        assert "Error 0" not in history
    
    def test_is_recently_failed(self):
        """Test checking if task failed recently"""
        # Arrange
        tracker = RetryTracker()
        
        # Act
        tracker.record_failure("task-1", "Error")
        
        # Assert
        assert tracker.is_recently_failed("task-1", within_seconds=60) is True
        assert tracker.is_recently_failed("task-2", within_seconds=60) is False
    
    def test_clear_specific_task(self):
        """Test clearing specific task history"""
        # Arrange
        tracker = RetryTracker()
        tracker.record_failure("task-1", "Error 1")
        tracker.record_failure("task-2", "Error 2")
        
        # Act
        tracker.clear("task-1")
        
        # Assert
        assert tracker.get_retry_count("task-1") == 0
        assert tracker.get_retry_count("task-2") == 1
    
    def test_clear_all_tasks(self):
        """Test clearing all task history"""
        # Arrange
        tracker = RetryTracker()
        tracker.record_failure("task-1", "Error 1")
        tracker.record_failure("task-2", "Error 2")
        tracker.record_failure("task-3", "Error 3")
        
        # Act
        tracker.clear()
        
        # Assert
        assert tracker.get_retry_count("task-1") == 0
        assert tracker.get_retry_count("task-2") == 0
        assert tracker.get_retry_count("task-3") == 0
    
    def test_multiple_tasks_independent(self):
        """Test that different tasks have independent retry tracking"""
        # Arrange
        tracker = RetryTracker()
        
        # Act
        tracker.record_failure("task-1", "Error A")
        tracker.record_failure("task-1", "Error B")
        tracker.record_failure("task-2", "Error C")
        
        # Assert
        assert tracker.get_retry_count("task-1") == 2
        assert tracker.get_retry_count("task-2") == 1
        assert len(tracker.get_failure_history("task-1")) == 2
        assert len(tracker.get_failure_history("task-2")) == 1
