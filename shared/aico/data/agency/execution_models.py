"""
Agency Execution Data Models

Dataclasses for execution tracking entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AgencyExecutionSnapshot:
    """Agency execution snapshot model - matches agency_execution_snapshots table."""
    snapshot_id: str
    execution_id: str
    snapshot_type: str
    state_data: str
    created_at: str


@dataclass
class AgencyPlanExecution:
    """Agency plan execution model - matches agency_plan_executions table."""
    execution_id: str
    plan_id: str
    goal_id: str
    user_id: str
    status: str
    steps_total: int
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    paused_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    current_step_id: Optional[str] = None
    steps_completed: int = 0
    progress_percentage: float = 0.0
    execution_context: Optional[str] = None
    error_message: Optional[str] = None
    cancellation_reason: Optional[str] = None
    retry_count: int = 0


@dataclass
class AgencyStepExecution:
    """Agency step execution model - matches agency_step_executions table."""
    step_execution_id: str
    execution_id: str
    step_id: str
    step_order: int
    status: str
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    skill_id: Optional[str] = None
    skill_invocation_id: Optional[str] = None
    input_data: str = '{}'
    output_data: str = '{}'
    error_message: Optional[str] = None
    retry_count: int = 0
    blocked_reason: Optional[str] = None
