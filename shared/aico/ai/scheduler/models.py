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
    """Scheduler task execution domain model matching PostgreSQL schema.

    Backed by scheduler_task_executions table:
      - id BIGSERIAL PRIMARY KEY
      - task_id TEXT NOT NULL
      - execution_id TEXT NOT NULL
      - status TEXT NOT NULL
      - started_at TIMESTAMPTZ NOT NULL
      - completed_at TIMESTAMPTZ
      - result TEXT
      - error_message TEXT
      - duration_seconds DOUBLE PRECISION
    """

    # Database primary key (autoincrement). Optional because it is assigned
    # by the database on insert and populated by the repository layer.
    id: Optional[int] = None

    execution_id: str
    task_id: str
    status: TaskStatus
    # Allow partial update payloads by making started_at optional
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    # Represent result as a JSON-serializable dictionary; repository is
    # responsible for serializing it to TEXT/JSON in the database layer.
    result: Optional[dict] = None
    duration_seconds: Optional[float] = None
