"""
Scheduler API Schemas

Pydantic models for task scheduler REST API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class TaskConfigRequest(BaseModel):
    """Request model for task configuration"""
    task_id: str = Field(..., description="Unique task identifier")
    task_class: str = Field(..., description="Task class name")
    schedule: str = Field(..., description="Cron expression for scheduling")
    config: Optional[Dict[str, Any]] = Field(None, description="Task-specific configuration")
    enabled: bool = Field(True, description="Whether task is enabled")

    @validator('schedule')
    def validate_schedule(cls, v):
        """Validate cron expression format"""
        if not v or not isinstance(v, str):
            raise ValueError("Schedule must be a non-empty string")
        
        # Basic cron validation (5 fields)
        fields = v.strip().split()
        if len(fields) != 5:
            raise ValueError("Schedule must be a valid cron expression with 5 fields")
        
        return v

    @validator('task_id')
    def validate_task_id(cls, v):
        """Validate task ID format"""
        if not v or not isinstance(v, str):
            raise ValueError("Task ID must be a non-empty string")
        
        # Basic format validation
        if not v.replace('.', '').replace('_', '').replace('-', '').isalnum():
            raise ValueError("Task ID can only contain letters, numbers, dots, underscores, and hyphens")
        
        return v


class TaskConfigResponse(BaseModel):
    """Response model for task configuration"""
    task_id: str
    task_class: str
    schedule: str
    config: Optional[Dict[str, Any]]
    enabled: bool
    created_at: str
    updated_at: str


class TaskExecutionResponse(BaseModel):
    """Response model for task execution history"""
    execution_id: str
    status: str
    started_at: str
    completed_at: Optional[str]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    duration_seconds: Optional[float]


class TaskStatusResponse(BaseModel):
    """Response model for task status"""
    task_id: str
    enabled: bool
    last_execution: Optional[TaskExecutionResponse]
    next_run_time: Optional[str]
    is_running: bool


class TaskListResponse(BaseModel):
    """Response model for task list"""
    tasks: List[TaskConfigResponse]
    total_count: int


class TaskExecutionHistoryResponse(BaseModel):
    """Response model for task execution history"""
    task_id: str
    executions: List[TaskExecutionResponse]
    total_count: int


class TaskTriggerRequest(BaseModel):
    """Request model for manual task triggering"""
    task_id: str = Field(..., description="Task ID to trigger")


class TaskTriggerResponse(BaseModel):
    """Response model for task trigger"""
    success: bool
    message: str
    execution_id: Optional[str]
    data: Optional[Dict[str, Any]]


class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status"""
    running: bool
    registered_tasks: int
    scheduled_tasks: int
    running_tasks: int
    next_run_times: Dict[str, str]


class TaskUpdateRequest(BaseModel):
    """Request model for task updates"""
    schedule: Optional[str] = Field(None, description="New cron schedule")
    config: Optional[Dict[str, Any]] = Field(None, description="Updated configuration")
    enabled: Optional[bool] = Field(None, description="Enable/disable task")

    @validator('schedule')
    def validate_schedule(cls, v):
        """Validate cron expression format if provided"""
        if v is not None:
            if not isinstance(v, str) or not v.strip():
                raise ValueError("Schedule must be a non-empty string")
            
            # Basic cron validation (5 fields)
            fields = v.strip().split()
            if len(fields) != 5:
                raise ValueError("Schedule must be a valid cron expression with 5 fields")
        
        return v


class ApiResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Response model for validation errors"""
    success: bool = False
    message: str
    errors: List[Dict[str, Any]]
