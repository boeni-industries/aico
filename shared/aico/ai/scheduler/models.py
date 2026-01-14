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
    """Scheduler task domain model."""
    task_id: str
    task_type: str
    user_id: Optional[str] = None
    schedule: str
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    is_active: bool = True
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    priority: int = 50
    metadata: dict = Field(default_factory=dict)
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


class SchedulerTaskLock(BaseModel):
    """Scheduler task lock domain model."""
    task_id: str
    worker_id: str
    acquired_at: datetime
    expires_at: float
