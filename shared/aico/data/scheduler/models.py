from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SchedulerTask(BaseModel):
    task_id: str
    task_class: str
    schedule: str
    config: Optional[str] = None
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SchedulerTaskRun(BaseModel):
    id: int | None = None
    task_id: str
    run_key: str
    tenant_id: str | None = None
    scheduled_for: datetime
    planned_at: datetime | None = None
    state: str
    enqueued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    execution_id: str | None = None
    reason_code: str | None = None
    reason_detail: str | None = None


class TaskExecution(BaseModel):
    id: int | None = None
    task_id: str
    execution_id: str
    run_key: str | None = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    acknowledged: bool = False


class SchedulerTaskLock(BaseModel):
    task_id: str
    execution_id: str
    locked_at: Optional[datetime] = None
    expires_at: datetime
