from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SchedulerTaskLock(BaseModel):
    task_id: str
    execution_id: str
    locked_at: datetime | None = None
    expires_at: datetime
