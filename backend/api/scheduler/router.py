"""
Scheduler API Router

REST API endpoints for task scheduler management following AICO patterns.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from datetime import datetime

from aico.core.logging import get_logger
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

router = APIRouter()
logger = get_logger("api", "scheduler_router")


@router.get("/status", response_model=SchedulerStatusResponse)
@handle_scheduler_exceptions
async def get_scheduler_status(
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> SchedulerStatusResponse:
    """Get scheduler status and statistics"""
    try:
        status_info = scheduler.get_status()
        return SchedulerStatusResponse(**status_info)
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise SchedulerNotAvailableError()


@router.get("/tasks", response_model=TaskListResponse)
@handle_scheduler_exceptions
async def list_tasks(
    enabled_only: bool = False,
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> TaskListResponse:
    """List all scheduled tasks"""
    try:
        tasks = await scheduler.task_store.list_tasks(enabled_only=enabled_only)
        
        task_responses = [
            TaskConfigResponse(
                task_id=task['task_id'],
                task_class=task['task_class'],
                schedule=task['schedule'],
                config=task['config'],
                enabled=task['enabled'],
                created_at=task['created_at'],
                updated_at=task['updated_at']
            )
            for task in tasks
        ]
        
        return TaskListResponse(
            tasks=task_responses,
            total_count=len(task_responses)
        )
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise SchedulerNotAvailableError()


@router.get("/tasks/{task_id}", response_model=TaskConfigResponse)
@handle_scheduler_exceptions
async def get_task(
    task_id: str = Depends(validate_task_id),
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> TaskConfigResponse:
    """Get a specific task configuration"""
    try:
        task = await scheduler.task_store.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        
        return TaskConfigResponse(
            task_id=task['task_id'],
            task_class=task['task_class'],
            schedule=task['schedule'],
            config=task['config'],
            enabled=task['enabled'],
            created_at=task['created_at'],
            updated_at=task['updated_at']
        )
    except TaskNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.post("/tasks", response_model=TaskConfigResponse, status_code=status.HTTP_201_CREATED)
@handle_scheduler_exceptions
async def create_task(
    task_request: TaskConfigRequest,
    scheduler = Depends(get_task_scheduler),
    cron_parser = Depends(get_cron_parser),
    _auth = Depends(require_admin_access)
) -> TaskConfigResponse:
    """Create a new scheduled task"""
    try:
        # Validate task doesn't already exist
        existing_task = await scheduler.task_store.get_task(task_request.task_id)
        if existing_task:
            raise TaskAlreadyExistsError(task_request.task_id)
        
        # Validate cron expression
        if not cron_parser.validate(task_request.schedule):
            raise InvalidCronExpressionError(task_request.schedule)
        
        # Validate task class exists in registry
        task_class = scheduler.task_registry.get_task_class(task_request.task_id)
        if not task_class and not task_request.task_id.startswith('user.'):
            raise TaskClassNotFoundError(task_request.task_class)
        
        # Validate configuration
        if task_request.config:
            validate_task_config(task_request.config)
        
        # Create task
        await scheduler.task_store.upsert_task(
            task_id=task_request.task_id,
            task_class=task_request.task_class,
            schedule=task_request.schedule,
            config=task_request.config,
            enabled=task_request.enabled
        )
        
        # Get the created task to return
        created_task = await scheduler.task_store.get_task(task_request.task_id)
        
        logger.info(f"Created task: {task_request.task_id}")
        
        return TaskConfigResponse(
            task_id=created_task['task_id'],
            task_class=created_task['task_class'],
            schedule=created_task['schedule'],
            config=created_task['config'],
            enabled=created_task['enabled'],
            created_at=created_task['created_at'],
            updated_at=created_task['updated_at']
        )
        
    except (TaskAlreadyExistsError, InvalidCronExpressionError, TaskClassNotFoundError, TaskValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to create task {task_request.task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.put("/tasks/{task_id}", response_model=TaskConfigResponse)
@handle_scheduler_exceptions
async def update_task(
    task_update: TaskUpdateRequest,
    task_id: str = Depends(validate_task_id),
    scheduler = Depends(get_task_scheduler),
    cron_parser = Depends(get_cron_parser),
    _auth = Depends(require_admin_access)
) -> TaskConfigResponse:
    """Update an existing task configuration"""
    try:
        # Check task exists
        existing_task = await scheduler.task_store.get_task(task_id)
        if not existing_task:
            raise TaskNotFoundError(task_id)
        
        # Validate cron expression if provided
        if task_update.schedule and not cron_parser.validate(task_update.schedule):
            raise InvalidCronExpressionError(task_update.schedule)
        
        # Validate configuration if provided
        if task_update.config:
            validate_task_config(task_update.config)
        
        # Update task with new values
        new_schedule = task_update.schedule or existing_task['schedule']
        new_config = task_update.config if task_update.config is not None else existing_task['config']
        new_enabled = task_update.enabled if task_update.enabled is not None else existing_task['enabled']
        
        await scheduler.task_store.upsert_task(
            task_id=task_id,
            task_class=existing_task['task_class'],
            schedule=new_schedule,
            config=new_config,
            enabled=new_enabled
        )
        
        # Get updated task
        updated_task = await scheduler.task_store.get_task(task_id)
        
        logger.info(f"Updated task: {task_id}")
        
        return TaskConfigResponse(
            task_id=updated_task['task_id'],
            task_class=updated_task['task_class'],
            schedule=updated_task['schedule'],
            config=updated_task['config'],
            enabled=updated_task['enabled'],
            created_at=updated_task['created_at'],
            updated_at=updated_task['updated_at']
        )
        
    except (TaskNotFoundError, InvalidCronExpressionError, TaskValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        raise SchedulerNotAvailableError()


@router.delete("/tasks/{task_id}", response_model=ApiResponse)
@handle_scheduler_exceptions
async def delete_task(
    task_id: str = Depends(validate_task_id),
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Delete a scheduled task"""
    try:
        deleted = await scheduler.task_store.delete_task(task_id)
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
    task_id: str = Depends(validate_task_id),
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Enable a scheduled task"""
    try:
        updated = await scheduler.task_store.set_task_enabled(task_id, True)
        if not updated:
            raise TaskNotFoundError(task_id)
        
        logger.info(f"Enabled task: {task_id}")
        
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
    task_id: str = Depends(validate_task_id),
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> ApiResponse:
    """Disable a scheduled task"""
    try:
        updated = await scheduler.task_store.set_task_enabled(task_id, False)
        if not updated:
            raise TaskNotFoundError(task_id)
        
        logger.info(f"Disabled task: {task_id}")
        
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
    task_id: str = Depends(validate_task_id),
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> TaskStatusResponse:
    """Get current status of a task"""
    try:
        # Get task configuration
        task = await scheduler.task_store.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        
        # Get latest execution
        history = await scheduler.task_store.get_execution_history(task_id, limit=1)
        last_execution = None
        if history:
            exec_data = history[0]
            last_execution = TaskExecutionResponse(
                execution_id=exec_data['execution_id'],
                status=exec_data['status'],
                started_at=exec_data['started_at'],
                completed_at=exec_data['completed_at'],
                result=exec_data['result'],
                error_message=exec_data['error_message'],
                duration_seconds=exec_data['duration_seconds']
            )
        
        # Get next run time
        next_run_time = None
        if task['enabled'] and task_id in scheduler.next_run_times:
            next_run_time = scheduler.next_run_times[task_id].isoformat()
        
        # Check if currently running
        is_running = task_id in scheduler.task_executor.running_tasks
        
        return TaskStatusResponse(
            task_id=task_id,
            enabled=task['enabled'],
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
    task_id: str = Depends(validate_task_id),
    limit: int = 50,
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
) -> TaskExecutionHistoryResponse:
    """Get execution history for a task"""
    try:
        # Validate limit
        if limit < 1 or limit > 1000:
            raise TaskValidationError("Limit must be between 1 and 1000")
        
        # Check task exists
        task = await scheduler.task_store.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        
        # Get execution history
        history = await scheduler.task_store.get_execution_history(task_id, limit=limit)
        
        executions = [
            TaskExecutionResponse(
                execution_id=exec_data['execution_id'],
                status=exec_data['status'],
                started_at=exec_data['started_at'],
                completed_at=exec_data['completed_at'],
                result=exec_data['result'],
                error_message=exec_data['error_message'],
                duration_seconds=exec_data['duration_seconds']
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
