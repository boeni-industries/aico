
"""
Global exception handlers for FastAPI application.

Ensures all exceptions are properly logged at appropriate levels with full context.
"""

import time
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from aico.core.logging import get_logger

logger = get_logger("backend.core.exception_handlers")

_validation_error_log_cache = {}
_VALIDATION_ERROR_LOG_TTL_SECONDS = 10


def _get_request_id(request: Request) -> str | None:
    return request.headers.get("x-request-id")


def _error_payload(*, request: Request, error_code: str, message: str, details: object | None = None) -> dict:
    payload = {
        "error_code": error_code,
        "message": message,
        "request_id": _get_request_id(request),
    }
    if details is not None:
        payload["details"] = details
    return payload


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions with proper logging.
    
    - 4xx errors: Log at WARNING level
    - 5xx errors: Log at ERROR level with full stack trace
    """
    # Determine log level based on status code
    if exc.status_code >= 500:
        # Server errors - log at ERROR level with full details
        # Use exception() method for AICOLogger to include traceback
        logger.exception(
            f"HTTP {exc.status_code} error on {request.method} {request.url.path}",
            extra={
                'status_code': exc.status_code,
                'method': request.method,
                'path': request.url.path,
                'detail': str(exc.detail),
                'client': request.client.host if request.client else None,
            }
        )
    elif exc.status_code >= 400:
        # Client errors - log at WARNING level
        logger.warning(
            f"HTTP {exc.status_code} error on {request.method} {request.url.path}: {exc.detail}",
            extra={
                'status_code': exc.status_code,
                'method': request.method,
                'path': request.url.path,
                'detail': str(exc.detail),
            }
        )
    
    detail = exc.detail
    if isinstance(detail, dict) and "error_code" in detail and "message" in detail:
        content = {
            "error_code": detail.get("error_code"),
            "message": detail.get("message"),
            "request_id": _get_request_id(request),
        }
        if detail.get("details") is not None:
            content["details"] = detail.get("details")
    else:
        content = _error_payload(
            request=request,
            error_code=f"HTTP_{exc.status_code}",
            message=str(detail),
        )

    return JSONResponse(status_code=exc.status_code, content=content)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors.
    
    Log validation errors at WARNING level with details about what failed.
    """
    errors = exc.errors()
    cache_key = (request.method, request.url.path, repr(errors))
    now = time.time()
    last_logged = _validation_error_log_cache.get(cache_key)
    if last_logged is None or (now - last_logged) >= _VALIDATION_ERROR_LOG_TTL_SECONDS:
        _validation_error_log_cache[cache_key] = now
        logger.warning(
            f"Validation error on {request.method} {request.url.path}",
            extra={
                'method': request.method,
                'path': request.url.path,
                'errors': errors,
                'body': exc.body,
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_payload(
            request=request,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": exc.errors()},
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unhandled exceptions.
    
    CRITICAL: All unhandled exceptions are logged at ERROR level with full stack trace.
    This ensures no 500 errors go unlogged.
    """
    # Log the full exception with stack trace using exception() method for AICOLogger
    logger.exception(
        f"UNHANDLED EXCEPTION on {request.method} {request.url.path}",
        extra={
            'method': request.method,
            'path': request.url.path,
            'exception_type': type(exc).__name__,
            'exception_message': str(exc),
            'client': request.client.host if request.client else None,
        }
    )
    
    # Return generic 500 error to client (don't leak internal details)
    message = str(exc) if logger.level <= 10 else "An unexpected error occurred"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_payload(
            request=request,
            error_code="INTERNAL_SERVER_ERROR",
            message=message,
            details={"exception_type": type(exc).__name__} if logger.level <= 10 else None,
        ),
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    from fastapi import HTTPException
    
    # Register handlers
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    
    logger.info("Exception handlers registered")
