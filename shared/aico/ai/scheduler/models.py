"""
Scheduler Domain Models

Rich domain models for scheduler entities.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SchedulerTask(BaseModel):
    """Scheduler task domain model matching PostgreSQL schema."""
    task_id: str
    task_class: str  # Python class path for the task
    schedule: str  # Cron expression or schedule string
    config: Optional[str] = None  # JSON configuration
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class SchedulerTaskExecution(BaseModel):
    """Scheduler task execution domain model."""
    execution_id: str
    task_id: str
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[dict] = None
    duration_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
