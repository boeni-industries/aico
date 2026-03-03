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
from aico.data.uow import UnitOfWork
from aico.services.scheduler_service import SchedulerService
from backend.core.postgres_dependencies import get_uow
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
    get_task_scheduler,
    get_cron_parser,
    validate_cron_expression,
    validate_task_id,
    require_admin_access,
    validate_task_config,
    validate_task_class_name
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
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> TaskConfigResponse:
    """Get a specific task configuration"""
    try:
        scheduler_service = SchedulerService(uow)
        task = await scheduler_service.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        
        return TaskConfigResponse(
            task_id=task.task_id,
            task_class=task.task_class,
            schedule=task.schedule,
            config=json.loads(task.config) if isinstance(task.config, str) else task.config,
            enabled=task.enabled,
            created_at=task.created_at.isoformat() if hasattr(task.created_at, 'isoformat') else task.created_at,
            updated_at=task.updated_at.isoformat() if hasattr(task.updated_at, 'isoformat') else task.updated_at
        )
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get task: {e}", extra={"task_id": task_id})
        raise SchedulerNotAvailableError()


@router.post("/tasks", response_model=TaskConfigResponse, status_code=status.HTTP_201_CREATED)
@handle_scheduler_exceptions
async def create_task(
    task_request: TaskConfigRequest,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    cron_parser = Depends(get_cron_parser),
    _auth = Depends(require_admin_access)
) -> TaskConfigResponse:
    """Create a new scheduled task"""
    try:
        scheduler_service = SchedulerService(uow)
        
        # Validate task doesn't already exist
        existing_task = await scheduler_service.get_task(task_request.task_id)
        if existing_task:
            raise TaskAlreadyExistsError(task_request.task_id)
        
        # Validate cron expression
        if not cron_parser.validate(task_request.schedule):
            raise InvalidCronExpressionError(task_request.schedule)
        
        # Validate task class exists
        validate_task_class_name(task_request.task_class)
        
        # Validate config if provided
        if task_request.config:
            validate_task_config(task_request.config)
        
        # Create task
        task_data = {
            "task_id": task_request.task_id,
            "task_class": task_request.task_class,
            "schedule": task_request.schedule,
            "config": task_request.config or {},
            "enabled": task_request.enabled,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        created_task = await scheduler_service.create_task(task_data)
        
        logger.info(f"Created task: {task_request.task_id}")
        
        return TaskConfigResponse(
            task_id=created_task.task_id,
            task_class=created_task.task_class,
            schedule=created_task.schedule,
            config=json.loads(created_task.config) if isinstance(created_task.config, str) else created_task.config,
            enabled=created_task.enabled,
            created_at=created_task.created_at.isoformat() if hasattr(created_task.created_at, 'isoformat') else created_task.created_at,
            updated_at=created_task.updated_at.isoformat() if hasattr(created_task.updated_at, 'isoformat') else created_task.updated_at
        )
    except (TaskAlreadyExistsError, InvalidCronExpressionError, TaskClassNotFoundError, TaskValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {e}", extra={"task_id": task_request.task_id})
        raise SchedulerNotAvailableError()


@router.put("/tasks/{task_id}", response_model=TaskConfigResponse)
@handle_scheduler_exceptions
async def update_task(
    task_update: TaskUpdateRequest,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    cron_parser = Depends(get_cron_parser),
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> TaskConfigResponse:
    """Update an existing task configuration"""
    try:
        scheduler_service = SchedulerService(uow)
        
        # Check task exists
        existing_task = await scheduler_service.get_task(task_id)
        if not existing_task:
            raise TaskNotFoundError(task_id)
        
        # Validate cron expression if provided
        if task_update.schedule and not cron_parser.validate(task_update.schedule):
            raise InvalidCronExpressionError(task_update.schedule)
        
        # Validate configuration if provided
        if task_update.config:
            validate_task_config(task_update.config)
        
        # Update task with new values
        task_data = {
            "task_id": task_id,
            "task_class": existing_task.task_class,
            "schedule": task_update.schedule or existing_task.schedule,
            "config": task_update.config if task_update.config is not None else existing_task.config,
            "enabled": task_update.enabled if task_update.enabled is not None else existing_task.enabled,
            "created_at": existing_task.created_at,
            "updated_at": datetime.now(UTC)
        }
        updated_task = await scheduler_service.update_task(task_data)
        
        logger.info(f"Updated task: {task_id}")
        
        return TaskConfigResponse(
            task_id=updated_task.task_id,
            task_class=updated_task.task_class,
            schedule=updated_task.schedule,
            config=json.loads(updated_task.config) if isinstance(updated_task.config, str) else updated_task.config,
            enabled=updated_task.enabled,
            created_at=updated_task.created_at.isoformat() if hasattr(updated_task.created_at, 'isoformat') else updated_task.created_at,
            updated_at=updated_task.updated_at.isoformat() if hasattr(updated_task.updated_at, 'isoformat') else updated_task.updated_at
        )
        
    except (TaskNotFoundError, InvalidCronExpressionError, TaskValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.delete("/tasks/{task_id}", response_model=ApiResponse)
@handle_scheduler_exceptions
async def delete_task(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Delete a scheduled task"""
    try:
        scheduler_service = SchedulerService(uow)
        deleted = await scheduler_service.delete_task(task_id)
        if not deleted:
            raise TaskNotFoundError(task_id)
        
        logger.info(f"Deleted task: {task_id}")
        
        return ApiResponse(
            success=True,
            message=f"Task {task_id} deleted successfully"
        )
        
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.post("/tasks/{task_id}/enable", response_model=ApiResponse)
@handle_scheduler_exceptions
async def enable_task(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    task_id: str = Depends(validate_task_id),
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Enable a scheduled task"""
    try:
        scheduler_service = SchedulerService(uow)
        updated = await scheduler_service.enable_task(task_id)
        if not updated:
            raise TaskNotFoundError(task_id)
        
        # Recalculate next run time for this task immediately
        task = await scheduler_service.get_task(task_id)
        if task and task.schedule:
            next_run = scheduler.cron_parser.next_run_time(task.schedule, datetime.now(UTC))
            if next_run:
                scheduler.next_run_times[task_id] = next_run
                logger.info(f"Enabled task: {task_id}, next run: {next_run}")
        
        return ApiResponse(
            success=True,
            message=f"Task {task_id} enabled successfully"
        )
        
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to enable task {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.post("/tasks/{task_id}/disable", response_model=ApiResponse)
@handle_scheduler_exceptions
async def disable_task(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    task_id: str = Depends(validate_task_id),
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Disable a scheduled task"""
    try:
        scheduler_service = SchedulerService(uow)
        updated = await scheduler_service.disable_task(task_id)
        if not updated:
            raise TaskNotFoundError(task_id)
        
        # Remove from next_run_times to prevent execution
        if task_id in scheduler.next_run_times:
            del scheduler.next_run_times[task_id]
            logger.info(f"Disabled task: {task_id}, removed from schedule")
        
        return ApiResponse(
            success=True,
            message=f"Task {task_id} disabled successfully"
        )
        
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to disable task {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.post("/tasks/{task_id}/trigger", response_model=TaskTriggerResponse)
@handle_scheduler_exceptions
async def trigger_task(
    task_id: str = Depends(validate_task_id),
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> TaskTriggerResponse:
    """Manually trigger a task execution"""
    try:
        result = await scheduler.trigger_task(task_id)
        
        logger.info(f"Triggered task: {task_id}")
        
        return TaskTriggerResponse(
            success=result.success,
            message=result.message,
            execution_id=None,  # TODO: Add execution ID to TaskResult
            data=result.data
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger task {task_id}: {e}")
        raise TaskExecutionError(task_id, str(e))


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
@handle_scheduler_exceptions
async def get_task_status(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    task_id: str = Depends(validate_task_id),
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> TaskStatusResponse:
    """Get current status of a task"""
    try:
        scheduler_service = SchedulerService(uow)
        
        # Get task configuration
        task = await scheduler_service.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        
        # Get latest execution
        history = await scheduler_service.get_task_executions(task_id, limit=1)
        last_execution = None
        if history:
            exec_data = history[0]
            last_execution = TaskExecutionResponse(
                execution_id=exec_data.execution_id,
                status=exec_data.status,
                started_at=exec_data.started_at,
                completed_at=exec_data.completed_at,
                result=exec_data.result,
                error_message=exec_data.error_message,
                duration_seconds=exec_data.duration_seconds
            )
        
        # Get next run time
        next_run_time = None
        if task.enabled and task_id in scheduler.next_run_times:
            next_run_time = scheduler.next_run_times[task_id].isoformat()
        
        # Check if currently running
        is_running = task_id in scheduler.task_executor.running_tasks
        
        return TaskStatusResponse(
            task_id=task_id,
            enabled=task.enabled,
            last_execution=last_execution,
            next_run_time=next_run_time,
            is_running=is_running
        )
        
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.get("/tasks/{task_id}/history", response_model=TaskExecutionHistoryResponse)
@handle_scheduler_exceptions
async def get_task_history(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: int = 50,
    task_id: str = Depends(validate_task_id),
    _auth = Depends(require_admin_access)
) -> TaskExecutionHistoryResponse:
    """Get execution history for a task"""
    try:
        scheduler_service = SchedulerService(uow)
        
        # Validate limit
        if limit < 1 or limit > 1000:
            raise TaskValidationError("Limit must be between 1 and 1000")
        
        # Check task exists
        task = await scheduler_service.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        
        # Get execution history
        history = await scheduler_service.get_task_executions(task_id, limit=limit)
        
        executions = [
            TaskExecutionResponse(
                execution_id=exec_data.execution_id,
                status=exec_data.status,
                started_at=exec_data.started_at,
                completed_at=exec_data.completed_at,
                result=exec_data.result,
                error_message=exec_data.error_message,
                duration_seconds=exec_data.duration_seconds
            )
            for exec_data in history
        ]
        
        return TaskExecutionHistoryResponse(
            task_id=task_id,
            executions=executions,
            total_count=len(executions)
        )
        
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
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    _auth = Depends(require_admin_access)
) -> dict:
    """Get all task executions within a time range"""
    try:
        # Validate datetime strings
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError as e:
            raise TaskValidationError(f"Invalid datetime format: {e}")
        
        scheduler_service = SchedulerService(uow)
        # Get all executions and filter by time range
        all_executions = await scheduler_service.get_recent_executions(limit=10000)
        executions = [e for e in all_executions if e.started_at and start_dt <= e.started_at <= end_dt]
        
        executions_response = [
            {
                'task_id': exec_data.task_id,
                'execution_id': exec_data.execution_id,
                'status': exec_data.status,
                'started_at': exec_data.started_at.isoformat() if exec_data.started_at else None,
                'completed_at': exec_data.completed_at.isoformat() if exec_data.completed_at else None,
                'result': exec_data.result,
                'error_message': exec_data.error_message,
                'duration_seconds': exec_data.duration_seconds
            }
            for exec_data in executions
        ]
        
        return {
            'executions': executions_response,
            'total_count': len(executions_response),
            'start_time': start_time,
            'end_time': end_time
        }
        
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
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Mark a single failed execution as acknowledged (hide from UI)."""
    try:
        scheduler_service = SchedulerService(uow)
        success = await scheduler_service.acknowledge_execution(execution_id)
        
        if not success:
            raise_api_error(
                status_code=404,
                error_code="SCHEDULER_EXECUTION_NOT_FOUND",
                message=f"Execution {execution_id} not found",
            )
        
        logger.info(f"Acknowledged execution: {execution_id}")
        
        return ApiResponse(
            success=True,
            message=f"Execution {execution_id} acknowledged successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge execution {execution_id}: {e}")
        raise SchedulerNotAvailableError()


@router.post("/executions/acknowledge-all", response_model=ApiResponse)
@handle_scheduler_exceptions
async def acknowledge_all_failed(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    task_id: Optional[str] = None,
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Mark all failed executions as acknowledged.
    
    Query Parameters:
        task_id: Optional task ID to limit acknowledgement to specific task
    """
    try:
        scheduler_service = SchedulerService(uow)
        count = await scheduler_service.acknowledge_all_failed(task_id=task_id)
        
        if task_id:
            message = f"Acknowledged {count} failed executions for task {task_id}"
        else:
            message = f"Acknowledged {count} failed executions across all tasks"
        
        logger.info(message)
        
        return ApiResponse(
            success=True,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Failed to acknowledge all failed executions: {e}")
        raise SchedulerNotAvailableError()


@router.get("/executions/unacknowledged-failures", response_model=dict)
@handle_scheduler_exceptions
async def get_unacknowledged_failures(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
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
        scheduler_service = SchedulerService(uow)
        executions = await scheduler_service.get_unacknowledged_failures(task_id=task_id, limit=limit)
        
        executions_response = [
            {
                'execution_id': exec_data.execution_id,
                'task_id': exec_data.task_id,
                'status': exec_data.status,
                'started_at': exec_data.started_at.isoformat() if exec_data.started_at else None,
                'completed_at': exec_data.completed_at.isoformat() if exec_data.completed_at else None,
                'error_message': exec_data.error_message,
                'duration_seconds': exec_data.duration_seconds
            }
            for exec_data in executions
        ]
        
        return {
            'executions': executions_response,
            'total_count': len(executions_response),
            'task_id': task_id
        }
        
    except Exception as e:
        logger.error(f"Failed to get unacknowledged failures: {e}")
        raise SchedulerNotAvailableError()


# WebSocket endpoint for real-time scheduler events
@router.websocket("/ws/events")
async def scheduler_events_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time scheduler event notifications.
    
    Provides live updates for:
    - Stuck tasks (exceeded timeout + buffer)
    - Long-running tasks (approaching timeout)
    - Task failures
    - Critical scheduler errors
    
    Follows the same pattern as conversation WebSocket endpoint.
    """
    from .events import scheduler_events_websocket as handle_ws
    await handle_ws(websocket)
