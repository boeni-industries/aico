"""
Scheduler Task Lock Data Models

Dataclasses for scheduler task locks.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SchedulerTaskLock:
    """Scheduler task lock model - matches scheduler_task_locks table."""
    task_id: str
    execution_id: str
    expires_at: datetime
    locked_at: Optional[datetime] = None
