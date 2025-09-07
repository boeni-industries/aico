"""
Logs API Dependencies

Dependencies and utilities for log submission endpoints.
"""

from typing import Optional
from fastapi import HTTPException
from aico.core.logging import get_logger
from .schemas import LogLevel, LogSeverity


logger = get_logger("api", "logs_dependencies")


def validate_log_level(level: str) -> LogLevel:
    """Validate and normalize log level"""
    try:
        return LogLevel(level.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid log level: {level}. Must be one of: DEBUG, INFO, WARNING, ERROR"
        )


def validate_log_severity(severity: str) -> LogSeverity:
    """Validate and normalize log severity"""
    try:
        return LogSeverity(severity.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid log severity: {severity}. Must be one of: low, medium, high"
        )


def validate_module_name(module: str) -> str:
    """Validate module name format"""
    if not module or len(module.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="Module name cannot be empty"
        )
    
    # Basic validation - should follow dot notation
    if not all(part.isidentifier() or part.replace('_', '').replace('-', '').isalnum() 
              for part in module.split('.')):
        raise HTTPException(
            status_code=400,
            detail="Module name must follow dot notation (e.g., 'frontend.conversation_ui')"
        )
    
    return module.strip()


def validate_topic(topic: str) -> str:
    """Validate topic format"""
    if not topic or len(topic.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="Topic cannot be empty"
        )
    
    # Basic validation - should follow slash notation
    if not all(part.replace('_', '').replace('-', '').isalnum() 
              for part in topic.split('/')):
        raise HTTPException(
            status_code=400,
            detail="Topic must follow slash notation (e.g., 'auth/login/attempt/v1')"
        )
    
    return topic.strip()


def validate_message(message: str) -> str:
    """Validate log message"""
    if not message or len(message.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="Log message cannot be empty"
        )
    
    # Reasonable message length limit
    if len(message) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Log message too long (max 10000 characters)"
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
