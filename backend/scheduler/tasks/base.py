"""
Base Task Classes and Types

Provides abstract base classes and data structures for scheduler tasks.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
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


@dataclass
class TaskResult:
    """Result of task execution"""
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    skipped: bool = False
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "skipped": self.skipped,
            "error": self.error,
            "duration_seconds": self.duration_seconds
        }


class TaskContext:
    """Context provided to tasks during execution"""
    
    def __init__(self, 
                 task_id: str,
                 config_manager,
                 db_connection,
                 instance_config: Optional[Dict[str, Any]] = None,
                 execution_id: Optional[str] = None,
                 service_container = None):
        self.task_id = task_id
        self.config_manager = config_manager
        self.db_connection = db_connection
        self.instance_config = instance_config or {}
        self.execution_id = execution_id
        self.service_container = service_container
        self.logger = get_logger("backend", "scheduler.task_context")
    
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
        """Check if task should be skipped when on battery power"""
        try:
            # TODO: Implement battery status checking
            # For now, assume AC power
            return False
        except Exception as e:
            self.logger.warning(f"Failed to check battery status: {e}")
            return False


class BaseTask(ABC):
    """Abstract base class for all scheduler tasks"""
    
    # Task metadata (must be defined by subclasses)
    task_id: str = None
    default_config: Dict[str, Any] = {}
    
    def __init__(self):
        if not self.task_id:
            raise ValueError(f"Task class {self.__class__.__name__} must define task_id")
        
        self.logger = get_logger("backend", f"scheduler.task.{self.task_id}")
    
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
