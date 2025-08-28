"""
Scheduler API Exceptions

Custom exceptions for scheduler API endpoints with proper HTTP status codes.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class SchedulerAPIException(HTTPException):
    """Base exception for scheduler API"""
    def __init__(self, status_code: int, detail: str, headers: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class TaskNotFoundError(SchedulerAPIException):
    """Task not found exception"""
    def __init__(self, task_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}"
        )


class TaskAlreadyExistsError(SchedulerAPIException):
    """Task already exists exception"""
    def __init__(self, task_id: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task already exists: {task_id}"
        )


class TaskValidationError(SchedulerAPIException):
    """Task validation error"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task validation error: {message}"
        )


class TaskExecutionError(SchedulerAPIException):
    """Task execution error"""
    def __init__(self, task_id: str, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed for {task_id}: {message}"
        )


class SchedulerNotAvailableError(SchedulerAPIException):
    """Scheduler service not available"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task scheduler service is not available"
        )


class InvalidCronExpressionError(SchedulerAPIException):
    """Invalid cron expression"""
    def __init__(self, expression: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: {expression}"
        )


class TaskClassNotFoundError(SchedulerAPIException):
    """Task class not found"""
    def __init__(self, task_class: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task class not found: {task_class}"
        )


class UnauthorizedAccessError(SchedulerAPIException):
    """Unauthorized access to scheduler API"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access to scheduler API",
            headers={"WWW-Authenticate": "Bearer"}
        )


class InsufficientPermissionsError(SchedulerAPIException):
    """Insufficient permissions for scheduler operation"""
    def __init__(self, operation: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for operation: {operation}"
        )


def handle_scheduler_exceptions(func):
    """Decorator to handle scheduler API exceptions"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except SchedulerAPIException:
            # Re-raise scheduler API exceptions as-is
            raise
        except Exception as e:
            # Convert unexpected exceptions to internal server error
            raise SchedulerAPIException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal scheduler error: {str(e)}"
            )
    
    return wrapper
