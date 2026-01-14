from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class WorkflowExecution(BaseModel):
    execution_id: str
    workflow_type: str
    user_id: str

    status: str
    current_stage: Optional[str] = None
    total_stages: int = 0

    started_at: str
    completed_at: Optional[str] = None

    metadata: Optional[str] = None
    error_message: Optional[str] = None

    created_at: str
    updated_at: str


class WorkflowStage(BaseModel):
    stage_id: str
    execution_id: str
    stage_name: str
    stage_order: int

    status: str

    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    input_data: Optional[str] = None
    output_data: Optional[str] = None
    error_message: Optional[str] = None

    retry_count: int = 0

    created_at: str
