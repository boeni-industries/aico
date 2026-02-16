from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgencyExecutionSnapshot(BaseModel):
    snapshot_id: str
    execution_id: str
    snapshot_type: str
    state_data: str
    created_at: datetime


class AgencyPlanExecution(BaseModel):
    execution_id: str
    plan_id: str
    goal_id: str
    user_id: str
    status: str

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    current_step_id: Optional[str] = None

    steps_completed: int = 0
    steps_total: int
    progress_percentage: float = 0.0

    execution_context: Optional[str] = None
    error_message: Optional[str] = None
    cancellation_reason: Optional[str] = None
    retry_count: int = 0

    created_at: datetime
    updated_at: datetime


class AgencyStepExecution(BaseModel):
    step_execution_id: str
    execution_id: str
    step_id: str
    step_order: int
    status: str

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    skill_id: Optional[str] = None
    skill_invocation_id: Optional[str] = None

    input_data: str = "{}"
    output_data: str = "{}"

    error_message: Optional[str] = None
    retry_count: int = 0
    blocked_reason: Optional[str] = None

    created_at: datetime
    updated_at: datetime
