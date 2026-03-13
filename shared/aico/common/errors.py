from __future__ import annotations

import traceback
from typing import Any, Optional
from contextvars import ContextVar

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from aico.core.logging import get_logger

logger = get_logger("gateway.api.errors")

# Context variable to store request_id across async contexts
request_id_context: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class APIErrorResponse(BaseModel):
    """Standardized error response schema for all non-2xx responses."""
    error_code: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Any] = None


def set_request_id(request_id: str) -> None:
    """Set request_id in context for current async context."""
    request_id_context.set(request_id)


def get_request_id() -> Optional[str]:
    """Get request_id from context."""
    return request_id_context.get()


def raise_api_error(
    *,
    status_code: int,
    error_code: str,
    message: str,
    details: Any | None = None,
    request_id: Optional[str] = None
) -> None:
    """Raise standardized API error with optional request_id."""
    detail: dict[str, Any] = {
        "error_code": error_code,
        "message": message,
        "request_id": request_id or get_request_id(),
    }
    if details is not None:
        detail["details"] = details
    raise HTTPException(status_code=status_code, detail=detail)


def error_responses(*status_codes: int) -> dict[int, dict[str, object]]:
    """Generate OpenAPI error response schemas."""
    return {
        int(code): {"model": APIErrorResponse}
        for code in status_codes
    }


# ============================================================================
# Global Exception Handlers
# ============================================================================

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global handler for HTTPException to enforce standardized error envelope.
    
    Converts all HTTPException instances to APIErrorResponse format.
    """
    request_id = get_request_id() or request.headers.get("x-request-id")
    
    # If detail is already a dict with error_code, use it
    if isinstance(exc.detail, dict) and "error_code" in exc.detail:
        error_response = APIErrorResponse(
            error_code=exc.detail.get("error_code", "http_error"),
            message=exc.detail.get("message", str(exc.detail)),
            request_id=exc.detail.get("request_id") or request_id,
            details=exc.detail.get("details"),
        )
    else:
        # Convert plain string detail to standardized format
        error_response = APIErrorResponse(
            error_code=f"http_{exc.status_code}",
            message=str(exc.detail) if exc.detail else "An error occurred",
            request_id=request_id,
        )
    
    logger.warning(
        f"HTTP {exc.status_code}: {error_response.error_code}",
        extra={
            "status_code": exc.status_code,
            "error_code": error_response.error_code,
            "request_id": request_id,
            "path": request.url.path,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Global handler for request validation errors.
    
    Converts Pydantic validation errors to standardized error format.
    """
    request_id = get_request_id() or request.headers.get("x-request-id")
    
    error_response = APIErrorResponse(
        error_code="validation_error",
        message="Request validation failed",
        request_id=request_id,
        details={"errors": exc.errors()},
    )
    
    logger.warning(
        f"Validation error: {len(exc.errors())} errors",
        extra={
            "error_code": "validation_error",
            "request_id": request_id,
            "path": request.url.path,
            "errors": exc.errors(),
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(exclude_none=True),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global handler for unhandled exceptions.
    
    Catches all other exceptions and returns standardized 500 error.
    """
    request_id = get_request_id() or request.headers.get("x-request-id")
    
    error_response = APIErrorResponse(
        error_code="internal_server_error",
        message="An internal server error occurred",
        request_id=request_id,
    )
    
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "error_code": "internal_server_error",
            "request_id": request_id,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True),
    )
