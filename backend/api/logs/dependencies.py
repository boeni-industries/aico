"""
Logs API Dependencies

Dependencies and utilities for log submission endpoints.
"""

from typing import Optional
from fastapi import HTTPException
from aico.core.logging import get_logger
from .schemas import LogLevel, LogSeverity

from backend.api.errors import raise_api_error


logger = get_logger("api.logs_dependencies")


def validate_log_level(level: str) -> LogLevel:
    """Validate and normalize log level"""
    try:
        return LogLevel(level.upper())
    except ValueError:
        raise_api_error(
            status_code=400,
            error_code="LOG_LEVEL_INVALID",
            message=f"Invalid log level: {level}. Must be one of: DEBUG, INFO, WARNING, ERROR",
        )


def validate_log_severity(severity: str) -> LogSeverity:
    """Validate and normalize log severity"""
    try:
        return LogSeverity(severity.lower())
    except ValueError:
        raise_api_error(
            status_code=400,
            error_code="LOG_SEVERITY_INVALID",
            message=f"Invalid log severity: {severity}. Must be one of: low, medium, high",
        )


def validate_module_name(module: str) -> str:
    """Validate module name format"""
    if not module or len(module.strip()) == 0:
        raise_api_error(status_code=400, error_code="LOG_MODULE_EMPTY", message="Module name cannot be empty")
    
    # Basic validation - should follow dot notation
    if not all(part.isidentifier() or part.replace('_', '').replace('-', '').isalnum() 
              for part in module.split('.')):
        raise_api_error(
            status_code=400,
            error_code="LOG_MODULE_INVALID",
            message="Module name must follow dot notation (e.g., 'frontend.conversation_ui')",
        )
    
    return module.strip()


def validate_topic(topic: str) -> str:
    """Validate topic format"""
    if not topic or len(topic.strip()) == 0:
        raise_api_error(status_code=400, error_code="LOG_TOPIC_EMPTY", message="Topic cannot be empty")
    
    # Split by slash and filter out empty parts (handles trailing/leading slashes)
    parts = [part.strip() for part in topic.split('/') if part.strip()]
    
    if not parts:
        raise_api_error(
            status_code=400,
            error_code="LOG_TOPIC_INVALID",
            message="Topic must contain at least one valid part",
        )
    
    # Validate each part - should be alphanumeric (allowing underscores and hyphens)
    for part in parts:
        # Remove underscores and hyphens, check if remaining is alphanumeric
        cleaned = part.replace('_', '').replace('-', '')
        if not cleaned or not cleaned.isalnum():
            raise_api_error(
                status_code=400,
                error_code="LOG_TOPIC_INVALID",
                message=f"Topic part '{part}' is invalid. Topic must follow slash notation (e.g., 'auth/login/attempt/v1')",
            )
    
    # Return normalized topic (removes trailing/leading slashes and extra spaces)
    return '/'.join(parts)


def validate_message(message: str) -> str:
    """Validate log message"""
    if not message or len(message.strip()) == 0:
        raise_api_error(status_code=400, error_code="LOG_MESSAGE_EMPTY", message="Log message cannot be empty")
    
    # Reasonable message length limit
    if len(message) > 10000:
        raise_api_error(
            status_code=400,
            error_code="LOG_MESSAGE_TOO_LONG",
            message="Log message too long (max 10000 characters)",
        )
    
    return message.strip()


def sanitize_log_entry(log_data: dict) -> dict:
    """Sanitize log entry data for security"""
    # Remove any potentially sensitive fields that shouldn't be logged
    sensitive_fields = ['password', 'token', 'secret', 'key', 'auth']
    
    def sanitize_dict(data):
        if isinstance(data, dict):
            return {
                k: sanitize_dict(v) if k.lower() not in sensitive_fields else "[REDACTED]"
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [sanitize_dict(item) for item in data]
        else:
            return data
    
    return sanitize_dict(log_data)
