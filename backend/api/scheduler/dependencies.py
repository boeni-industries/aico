"""
Scheduler API Dependencies

FastAPI dependencies for scheduler endpoints including validation and access control.
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from aico.core.logging import get_logger
from backend.scheduler import TaskScheduler, CronParser
from backend.scheduler.tasks.base import TaskContext

logger = get_logger("api", "scheduler_dependencies")
security = HTTPBearer(auto_error=False)


async def get_task_scheduler(request: Request) -> TaskScheduler:
    """
    Get TaskScheduler instance from FastAPI app state.
    """
    if not hasattr(request.app.state, 'task_scheduler'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task scheduler not available"
        )
    return request.app.state.task_scheduler


async def get_cron_parser() -> CronParser:
    """Dependency to get cron parser instance"""
    return CronParser()


async def validate_cron_expression(schedule: str, cron_parser: CronParser = Depends(get_cron_parser)) -> str:
    """Validate cron expression format"""
    try:
        if not cron_parser.validate(schedule):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {schedule}"
            )
        return schedule
    except Exception as e:
        logger.error(f"Cron validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: {schedule}"
        )


async def validate_task_id(task_id: str) -> str:
    """Validate task ID format and constraints"""
    if not task_id or not isinstance(task_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task ID must be a non-empty string"
        )
    
    # Check length
    if len(task_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task ID must be 100 characters or less"
        )
    
    # Check format
    if not task_id.replace('.', '').replace('_', '').replace('-', '').isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task ID can only contain letters, numbers, dots, underscores, and hyphens"
        )
    
    return task_id


async def require_admin_access(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Require admin access for scheduler operations"""
    # TODO: Implement proper authentication/authorization
    # For now, we'll allow access but log the attempt
    if not credentials:
        logger.warning("Scheduler API access attempted without authentication")
        # In development, we might allow this, but log it
        # In production, this should raise HTTPException
        pass
    else:
        logger.info(f"Scheduler API access with token: {credentials.credentials[:10]}...")
    
    # For now, return True to allow access during development
    return True


def validate_task_config(config: dict) -> dict:
    """Validate task configuration dictionary"""
    if not isinstance(config, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task config must be a valid JSON object"
        )
    
    # Check for reserved keys that shouldn't be in user config
    reserved_keys = {'task_id', 'task_class', 'schedule', 'enabled', 'created_at', 'updated_at'}
    user_keys = set(config.keys())
    
    if user_keys.intersection(reserved_keys):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Config cannot contain reserved keys: {reserved_keys.intersection(user_keys)}"
        )
    
    return config


def validate_task_class_name(task_class: str) -> str:
    """Validate task class name format"""
    if not task_class or not isinstance(task_class, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task class must be a non-empty string"
        )
    
    # Check if it looks like a valid Python class name
    if not task_class.replace('_', '').isalnum() or task_class[0].islower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task class must be a valid Python class name (PascalCase)"
        )
    
    return task_class
