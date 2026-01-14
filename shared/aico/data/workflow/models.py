"""
Workflow Data Models

Dataclasses for workflow executions and stages.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkflowExecution:
    """Workflow execution model - matches workflow_executions table."""
    execution_id: str
    workflow_type: str
    user_id: str
    status: str
    started_at: str
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    current_stage: Optional[str] = None
    total_stages: Optional[int] = None
    metadata: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class WorkflowStage:
    """Workflow stage model - matches workflow_stages table."""
    stage_id: str
    execution_id: str
    stage_name: str
    stage_order: int
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
