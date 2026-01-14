"""
Scheduler Data Models

Dataclasses for scheduler entities (tasks, executions).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class SchedulerTask:
    """Scheduler task model."""
    task_id: str
    task_class: str
    schedule: str
    config: Optional[str] = None
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class TaskExecution:
    """Task execution model."""
    id: int
    task_id: str
    execution_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[str] = None
    duration_seconds: Optional[float] = None
