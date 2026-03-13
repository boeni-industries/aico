"""
Base Task Classes and Types

Provides abstract base classes and data structures for scheduler tasks.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass

from aico.core.logging import get_logger


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    DEFERRED = "deferred"  # Phase 6.2: Task deferred due to resources/lifecycle


class TaskPriority(Enum):
    """Task priority levels for queue ordering"""
    CRITICAL = 0   # System-critical tasks (maintenance, safety)
    HIGH = 1       # User-facing, time-sensitive
    NORMAL = 2     # Standard background tasks
    LOW = 3        # Opportunistic, can be deferred
    IDLE = 4       # Only run when system is truly idle


class TaskQueue(Enum):
    """Task queue types for resource governance"""
    USER_FACING = "user_facing"           # Interactive, user-initiated
    BACKGROUND_LIGHT = "background_light" # Light background work
    BACKGROUND_HEAVY = "background_heavy" # Heavy consolidation jobs
    MAINTENANCE = "maintenance"           # System maintenance


class RetryStrategy(Enum):
    """Retry strategies for failed tasks"""
    NONE = "none"                    # No retries
    IMMEDIATE = "immediate"          # Retry immediately
    LINEAR = "linear"                # Linear backoff (fixed delay)
    EXPONENTIAL = "exponential"      # Exponential backoff (2^n * base_delay)
    FIBONACCI = "fibonacci"          # Fibonacci backoff


@dataclass
class TaskResult:
    """Result of task execution"""
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    skipped: bool = False
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    retry_after_seconds: Optional[int] = None  # Phase 6.2: Suggest retry delay
    defer_reason: Optional[str] = None         # Phase 6.2: Why task was deferred
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "skipped": self.skipped,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "retry_after_seconds": self.retry_after_seconds,
            "defer_reason": self.defer_reason
        }


@dataclass
class RetryConfig:
    """Retry configuration for tasks"""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_retries: int = 3
    base_delay_seconds: int = 60  # Base delay for backoff calculations
    max_delay_seconds: int = 3600  # Maximum delay (1 hour)
    jitter: bool = True  # Add random jitter to prevent thundering herd


class TaskContext:
    """Context provided to tasks during execution"""
    
    def __init__(self, 
                 task_id: str,
                 config_manager,
                 db_connection,
                 instance_config: Optional[Dict[str, Any]] = None,
                 execution_id: Optional[str] = None,
                 service_container = None,
                 retry_count: int = 0):
        self.task_id = task_id
        self.config_manager = config_manager
        self.db_connection = db_connection
        self.instance_config = instance_config or {}
        self.execution_id = execution_id
        self.service_container = service_container
        self.retry_count = retry_count  # Phase 6.2: Current retry attempt
        self.logger = get_logger("core.scheduler.task_context")
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback chain:
        1. Instance config (database)
        2. Task defaults (provided by task class)
        3. Default parameter
        """
        # Check instance config first (highest priority)
        if key in self.instance_config:
            return self.instance_config[key]
        
        # Fall back to provided default
        return default
    
    def system_idle(self) -> bool:
        """Check if system is in idle state for resource-intensive tasks"""
        try:
            # Get CPU and memory thresholds from scheduler config
            scheduler_config = self.config_manager.get("scheduler", {})
            cpu_threshold = scheduler_config.get("idle_threshold_cpu", 20)
            memory_threshold = scheduler_config.get("idle_threshold_memory", 70)
            
            # TODO: Implement actual system resource checking
            # For now, return True (assume idle)
            return True
        except Exception as e:
            self.logger.warning(f"Failed to check system idle state: {e}")
            return False
    
    def should_skip_on_battery(self) -> bool:
        """Check if task should be skipped when on battery power.
        
        Returns:
            True if on battery and should skip, False if on AC power or check fails
        """
        try:
            import psutil
            
            # Get battery status
            battery = psutil.sensors_battery()
            
            if battery is None:
                # No battery (desktop) - never skip
                return False
            
            # On battery if not plugged in
            on_battery = not battery.power_plugged
            
            if on_battery:
                # Also check battery percentage - don't skip if battery is high
                if battery.percent > 50:
                    # Battery is healthy, OK to run
                    return False
                else:
                    # Low battery, skip task
                    self.logger.info(
                        f"Skipping task on battery power (battery: {battery.percent}%)"
                    )
                    return True
            
            return False
            
        except ImportError:
            # psutil not available - assume AC power
            self.logger.debug("psutil not available for battery check, assuming AC power")
            return False
        except Exception as e:
            self.logger.warning(f"Failed to check battery status: {e}")
            return False


class BaseTask(ABC):
    """Abstract base class for all scheduler tasks"""
    
    # Task metadata (must be defined by subclasses)
    task_id: str = None
    default_config: Dict[str, Any] = {}
    
    # Phase 6.2: Priority and queue configuration
    priority: TaskPriority = TaskPriority.NORMAL
    queue: TaskQueue = TaskQueue.BACKGROUND_LIGHT
    retry_config: RetryConfig = RetryConfig()
    
    # Phase 6.2: Resource profile (for governance)
    resource_profile: Dict[str, str] = {
        "cpu": "low",
        "memory": "low",
        "battery": "low",
        "duration_hint": "short",
        "io_intensity": "low"
    }
    
    # Phase 6.2: Runtime context
    runtime_context: Dict[str, bool] = {
        "foreground": False,
        "network_required": False,
        "power_required": False
    }
    
    def __init__(self):
        if not self.task_id:
            raise ValueError(f"Task class {self.__class__.__name__} must define task_id")
        
        self.logger = get_logger(f"core.scheduler.task.{self.task_id}")
    
    @abstractmethod
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute the task with given context
        
        Args:
            context: TaskContext with configuration and resources
            
        Returns:
            TaskResult with execution outcome
        """
        pass
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for this task"""
        return self.default_config.copy()
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate task configuration (override in subclasses if needed)"""
        return True
    
    async def cleanup(self):
        """Cleanup resources after task execution (override if needed)"""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.task_id})"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(task_id='{self.task_id}')"
