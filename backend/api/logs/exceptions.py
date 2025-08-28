"""
Logs API Exceptions

Custom exceptions for log submission endpoints.
"""

from fastapi import HTTPException


class LogSubmissionError(HTTPException):
    """Base exception for log submission errors"""
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


class LogValidationError(LogSubmissionError):
    """Exception for log validation errors"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=400)


class LogServiceUnavailableError(LogSubmissionError):
    """Exception when log service is unavailable"""
    def __init__(self, detail: str = "Log service is currently unavailable"):
        super().__init__(detail=detail, status_code=503)


class LogBatchTooLargeError(LogSubmissionError):
    """Exception when log batch is too large"""
    def __init__(self, detail: str = "Log batch size exceeds maximum limit"):
        super().__init__(detail=detail, status_code=413)


class LogRateLimitError(LogSubmissionError):
    """Exception when rate limit is exceeded"""
    def __init__(self, detail: str = "Log submission rate limit exceeded"):
        super().__init__(detail=detail, status_code=429)


def handle_log_service_exceptions(func):
    """Decorator to handle common log service exceptions"""
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except LogSubmissionError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Convert unexpected errors to service unavailable
            raise LogServiceUnavailableError(f"Internal log service error: {str(e)}")
    
    return wrapper
