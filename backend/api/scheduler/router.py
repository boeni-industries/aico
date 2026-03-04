"""
Scheduler API Router

REST API endpoints for task scheduler management following AICO patterns.
"""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, WebSocket
from datetime import datetime, UTC
import json
import time

from aico.core.logging import get_logger
from backend.api_gateway.core.nats_client import get_gateway_nats_client
from .schemas import (
    TaskConfigRequest,
    TaskConfigResponse,
    TaskExecutionResponse,
    TaskStatusResponse,
    TaskListResponse,
    TaskExecutionHistoryResponse,
    TaskTriggerRequest,
    TaskTriggerResponse,
    SchedulerStatusResponse,
    TaskUpdateRequest,
    ApiResponse,
    ValidationErrorResponse
)
from .dependencies import (
    get_cron_parser,
    validate_cron_expression,
    validate_task_id,
    require_admin_access,
    validate_task_config,
    validate_task_class_name,
)
from .exceptions import (
    TaskNotFoundError,
    TaskAlreadyExistsError,
    TaskValidationError,
    TaskExecutionError,
    SchedulerNotAvailableError,
    InvalidCronExpressionError,
    TaskClassNotFoundError,
    handle_scheduler_exceptions
)

from backend.api.errors import raise_api_error

router = APIRouter()
logger = get_logger("api.scheduler_router")

# Cache for tasks list to prevent expensive queries on every poll
_tasks_cache = {"data": None, "timestamp": 0}
_CACHE_TTL = 15  # 15 seconds cache


@router.get("/status", response_model=SchedulerStatusResponse)
@handle_scheduler_exceptions
async def get_scheduler_status(
    _auth: bool = Depends(require_admin_access)
) -> SchedulerStatusResponse:
    """Get scheduler status and statistics (via NATS from core)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        status_info = await nats_client.request_scheduler_status()
        return SchedulerStatusResponse(**status_info)
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise SchedulerNotAvailableError()


@router.get("/tasks", response_model=TaskListResponse)
@handle_scheduler_exceptions
async def list_tasks(
    enabled_only: bool = False,
    _auth = Depends(require_admin_access)
) -> TaskListResponse:
    """List all scheduled tasks (via NATS from core)"""
    # Check cache first (only for unfiltered requests)
    current_time = time.time()
    if not enabled_only and _tasks_cache["data"] is not None and (current_time - _tasks_cache["timestamp"]) < _CACHE_TTL:
        return _tasks_cache["data"]
    
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        response_data = await nats_client.request_scheduler_tasks(enabled_only=enabled_only)
        
        result = TaskListResponse(**response_data)
        
        # Update cache for unfiltered requests
        if not enabled_only:
            _tasks_cache["data"] = result
            _tasks_cache["timestamp"] = current_time
        
        return result
    except Exception as e_outer:
        logger.error(f"Failed to list tasks via NATS: {e_outer}")
        raise SchedulerNotAvailableError()


@router.get("/tasks/{task_id}", response_model=TaskConfigResponse)
@handle_scheduler_exceptions
async def get_task(
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> TaskConfigResponse:
    """Get a specific task configuration"""
    try:
        nats_client = get_gateway_nats_client()
        task = await nats_client.request_scheduler_task(task_id)
        if task.get("error"):
            if task.get("error") == "TASK_NOT_FOUND":
                raise TaskNotFoundError(task_id)
            raise SchedulerNotAvailableError()

        return TaskConfigResponse(**task)
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get task: {e}", extra={"task_id": task_id})
        raise SchedulerNotAvailableError()


@router.post("/tasks", response_model=TaskConfigResponse, status_code=status.HTTP_201_CREATED)
@handle_scheduler_exceptions
async def create_task(
    task_request: TaskConfigRequest,
    cron_parser = Depends(get_cron_parser),
    _auth = Depends(require_admin_access)
) -> TaskConfigResponse:
    """Create a new scheduled task"""
    try:
        # Validate cron expression
        # Validate cron expression
        if not cron_parser.validate(task_request.schedule):
            raise InvalidCronExpressionError(task_request.schedule)
        
        # Validate task class exists
        validate_task_class_name(task_request.task_class)
        
        # Validate config if provided
        if task_request.config:
            validate_task_config(task_request.config)
        
        nats_client = get_gateway_nats_client()
        created = await nats_client.request_scheduler_task_create(task_request.model_dump())
        if created.get("error"):
            if created.get("error") == "TASK_ALREADY_EXISTS":
                raise TaskAlreadyExistsError(task_request.task_id)
            raise SchedulerNotAvailableError()

        logger.info(f"Created task via NATS: {task_request.task_id}")
        return TaskConfigResponse(**created)
    except (TaskAlreadyExistsError, InvalidCronExpressionError, TaskClassNotFoundError, TaskValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {e}", extra={"task_id": task_request.task_id})
        raise SchedulerNotAvailableError()


@router.put("/tasks/{task_id}", response_model=TaskConfigResponse)
@handle_scheduler_exceptions
async def update_task(
    task_update: TaskUpdateRequest,
    cron_parser = Depends(get_cron_parser),
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> TaskConfigResponse:
    """Update an existing task configuration"""
    try:
        # Validate cron expression if provided
        if task_update.schedule and not cron_parser.validate(task_update.schedule):
            raise InvalidCronExpressionError(task_update.schedule)
        
        # Validate configuration if provided
        if task_update.config:
            validate_task_config(task_update.config)
        
        nats_client = get_gateway_nats_client()
        updated = await nats_client.request_scheduler_task_update(task_id, task_update.model_dump(exclude_unset=True))
        if updated.get("error"):
            if updated.get("error") == "TASK_NOT_FOUND":
                raise TaskNotFoundError(task_id)
            raise SchedulerNotAvailableError()

        logger.info(f"Updated task via NATS: {task_id}")
        return TaskConfigResponse(**updated)
        
    except (TaskNotFoundError, InvalidCronExpressionError, TaskValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.delete("/tasks/{task_id}", response_model=ApiResponse)
@handle_scheduler_exceptions
async def delete_task(
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Delete a scheduled task"""
    try:
        nats_client = get_gateway_nats_client()
        resp = await nats_client.request_scheduler_task_delete(task_id)
        if resp.get("error"):
            if resp.get("error") == "TASK_NOT_FOUND":
                raise TaskNotFoundError(task_id)
            raise SchedulerNotAvailableError()

        logger.info(f"Deleted task via NATS: {task_id}")
        return ApiResponse(success=True, message=f"Task {task_id} deleted successfully")
        
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.post("/tasks/{task_id}/enable", response_model=ApiResponse)
@handle_scheduler_exceptions
async def enable_task(
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Enable a scheduled task"""
    try:
        nats_client = get_gateway_nats_client()
        resp = await nats_client.request_scheduler_task_enable(task_id)
        if resp.get("error"):
            if resp.get("error") == "TASK_NOT_FOUND":
                raise TaskNotFoundError(task_id)
            raise SchedulerNotAvailableError()

        return ApiResponse(success=True, message=f"Task {task_id} enabled successfully")
        
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to enable task {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.post("/tasks/{task_id}/disable", response_model=ApiResponse)
@handle_scheduler_exceptions
async def disable_task(
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Disable a scheduled task"""
    try:
        nats_client = get_gateway_nats_client()
        resp = await nats_client.request_scheduler_task_disable(task_id)
        if resp.get("error"):
            if resp.get("error") == "TASK_NOT_FOUND":
                raise TaskNotFoundError(task_id)
            raise SchedulerNotAvailableError()

        return ApiResponse(success=True, message=f"Task {task_id} disabled successfully")
        
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to disable task {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.post("/tasks/{task_id}/trigger", response_model=TaskTriggerResponse)
@handle_scheduler_exceptions
async def trigger_task(
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> TaskTriggerResponse:
    """Manually trigger a task execution"""
    try:
        nats_client = get_gateway_nats_client()
        result = await nats_client.request_scheduler_task_trigger(task_id)
        if result.get("error"):
            raise TaskExecutionError(task_id, result.get("message", "Unknown error"))

        logger.info(f"Triggered task via NATS: {task_id}")
        return TaskTriggerResponse(
            success=bool(result.get("success")),
            message=str(result.get("message") or ""),
            execution_id=result.get("execution_id"),
            data=result.get("data"),
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger task {task_id}: {e}")
        raise TaskExecutionError(task_id, str(e))


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
@handle_scheduler_exceptions
async def get_task_status(
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> TaskStatusResponse:
    """Get current status of a task"""
    try:
        nats_client = get_gateway_nats_client()
        resp = await nats_client.request_scheduler_task_status(task_id)
        if resp.get("error"):
            if resp.get("error") == "TASK_NOT_FOUND":
                raise TaskNotFoundError(task_id)
            raise SchedulerNotAvailableError()

        return TaskStatusResponse(**resp)
        
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.get("/tasks/{task_id}/history", response_model=TaskExecutionHistoryResponse)
@handle_scheduler_exceptions
async def get_task_history(
    limit: int = 50,
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> TaskExecutionHistoryResponse:
    """Get execution history for a task"""
    try:
        # Validate limit
        if limit < 1 or limit > 1000:
            raise TaskValidationError("Limit must be between 1 and 1000")

        nats_client = get_gateway_nats_client()
        resp = await nats_client.request_scheduler_task_history(task_id, limit=limit)
        if resp.get("error"):
            if resp.get("error") == "TASK_NOT_FOUND":
                raise TaskNotFoundError(task_id)
            raise SchedulerNotAvailableError()

        return TaskExecutionHistoryResponse(**resp)
        
    except (TaskNotFoundError, TaskValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to get task history {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.get("/executions/range", response_model=dict)
@handle_scheduler_exceptions
async def get_executions_in_range(
    start_time: str,
    end_time: str,
    _auth = Depends(require_admin_access)
) -> dict:
    """Get all task executions within a time range"""
    try:
        nats_client = get_gateway_nats_client()
        resp = await nats_client.request_scheduler_executions_range(start_time, end_time)
        if resp.get("error"):
            raise SchedulerNotAvailableError()
        return resp
        
    except TaskValidationError:
        raise
    except Exception as e:
        logger.error(f"Failed to get executions in range: {e}")
        raise SchedulerNotAvailableError()


@router.get("/expected-runs-today", response_model=dict)
@handle_scheduler_exceptions
async def get_expected_runs_today(
    _auth = Depends(require_admin_access)
) -> dict:
    """Calculate expected number of job runs today based on cron schedules (via NATS from core)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        response_data = await nats_client.request_scheduler_expected_runs_today()
        return response_data
        
    except Exception as e:
        logger.error(f"Failed to get expected runs today: {e}")
        raise SchedulerNotAvailableError()


@router.post("/executions/{execution_id}/acknowledge", response_model=ApiResponse)
@handle_scheduler_exceptions
async def acknowledge_execution(
    execution_id: str,
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Mark a single failed execution as acknowledged (hide from UI)."""
    try:
        nats_client = get_gateway_nats_client()
        resp = await nats_client.request_scheduler_acknowledge_execution(execution_id)
        if resp.get("error"):
            raise_api_error(
                status_code=404,
                error_code="SCHEDULER_EXECUTION_NOT_FOUND",
                message=f"Execution {execution_id} not found",
            )

        logger.info(f"Acknowledged execution via NATS: {execution_id}")
        return ApiResponse(success=True, message=f"Execution {execution_id} acknowledged successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge execution {execution_id}: {e}")
        raise SchedulerNotAvailableError()


@router.post("/executions/acknowledge-all", response_model=ApiResponse)
@handle_scheduler_exceptions
async def acknowledge_all_failed(
    task_id: Optional[str] = None,
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Mark all failed executions as acknowledged.
    
    Query Parameters:
        task_id: Optional task ID to limit acknowledgement to specific task
    """
    try:
        nats_client = get_gateway_nats_client()
        resp = await nats_client.request_scheduler_acknowledge_all_failed(task_id=task_id)
        if resp.get("error"):
            raise SchedulerNotAvailableError()

        message = resp.get("message") or "Acknowledged failed executions"
        logger.info(message)
        return ApiResponse(success=True, message=message)
        
    except Exception as e:
        logger.error(f"Failed to acknowledge all failed executions: {e}")
        raise SchedulerNotAvailableError()


@router.get("/executions/unacknowledged-failures", response_model=dict)
@handle_scheduler_exceptions
async def get_unacknowledged_failures(
    task_id: Optional[str] = None,
    limit: int = 100,
    _auth = Depends(require_admin_access)
) -> dict:
    """Get unacknowledged failed executions.
    
    Query Parameters:
        task_id: Optional task ID to filter by
        limit: Maximum number of results (default: 100)
    """
    try:
        nats_client = get_gateway_nats_client()
        resp = await nats_client.request_scheduler_unacknowledged_failures(task_id=task_id, limit=limit)
        if resp.get("error"):
            raise SchedulerNotAvailableError()
        return resp
        
    except Exception as e:
        logger.error(f"Failed to get unacknowledged failures: {e}")
        raise SchedulerNotAvailableError()


# WebSocket endpoint removed - now handled by API Gateway WebSocket adapter
# Clients should connect to ws://gateway:8772/ws and subscribe to "scheduler.events"
