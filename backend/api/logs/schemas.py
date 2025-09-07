"""
Logs API Schemas

Pydantic models for frontend log submission requests and responses.
Following AICO unified logging schema.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class LogLevel(str, Enum):
    """Log levels following AICO unified logging schema"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogSeverity(str, Enum):
    """Log severity levels for prioritization"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LogEntryRequest(BaseModel):
    """Single log entry submission from frontend"""
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    level: LogLevel = Field(..., description="Log level")
    module: str = Field(..., description="Module name (e.g., 'frontend.conversation_ui')")
    function: str = Field(..., description="Function name")
    topic: str = Field(..., description="Log topic (e.g., 'ui.button.click')")
    message: str = Field(..., description="Log message")
    file: Optional[str] = Field(None, description="Source file name")
    line: Optional[int] = Field(None, description="Source line number")
    user_id: Optional[str] = Field(None, description="User ID if available")
    trace_id: Optional[str] = Field(None, description="Trace ID for request correlation")
    extra: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    severity: Optional[LogSeverity] = Field(None, description="Log severity")
    origin: Optional[str] = Field(None, description="Origin system (e.g., 'frontend')")
    environment: Optional[str] = Field(None, description="Environment (dev/staging/production)")
    session_id: Optional[str] = Field(None, description="Session ID")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Error details for error logs")

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate ISO 8601 timestamp format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('Timestamp must be in ISO 8601 format')

    @validator('level')
    def validate_level(cls, v):
        """Validate log level"""
        if isinstance(v, str):
            try:
                return LogLevel(v.upper())
            except ValueError:
                raise ValueError(f'Invalid log level: {v}')
        return v


class LogBatchRequest(BaseModel):
    """Batch log submission from frontend"""
    logs: List[LogEntryRequest] = Field(..., description="List of log entries")

    @validator('logs')
    def validate_logs_not_empty(cls, v):
        """Ensure batch is not empty"""
        if not v:
            raise ValueError('Log batch cannot be empty')
        if len(v) > 10000:  # Reasonable batch size limit
            raise ValueError('Log batch too large (max 10000 entries)')
        return v


class LogSubmissionResponse(BaseModel):
    """Response for log submission"""
    success: bool = Field(..., description="Whether submission was successful")
    message: str = Field(..., description="Response message")
    accepted_count: Optional[int] = Field(None, description="Number of logs accepted (for batch)")
    rejected_count: Optional[int] = Field(None, description="Number of logs rejected (for batch)")
    errors: Optional[List[str]] = Field(None, description="List of validation errors")


class LogHealthResponse(BaseModel):
    """Response for log service health check"""
    status: str = Field(..., description="Service status")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="Health check timestamp")
