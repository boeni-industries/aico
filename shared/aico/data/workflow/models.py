from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WorkflowExecution(BaseModel):
    execution_id: str
    workflow_type: str
    user_id: str

    status: str
    current_stage: Optional[str] = None
    total_stages: int = 0

    started_at: datetime
    completed_at: Optional[datetime] = None

    metadata: Optional[str] = None
    error_message: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class WorkflowStage(BaseModel):
    stage_id: str
    execution_id: str
    stage_name: str
    stage_order: int

    status: str

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    input_data: Optional[str] = None
    output_data: Optional[str] = None
    error_message: Optional[str] = None

    retry_count: int = 0

    created_at: datetime
