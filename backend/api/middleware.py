"""
API Middleware for AICO Backend

Provides request ID tracking and other cross-cutting concerns.
"""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.api.errors import set_request_id
from aico.core.logging import get_logger

logger = get_logger("backend.api.middleware")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject request_id into all requests.
    
    - Reads x-request-id header if provided by client
    - Generates new UUID if not provided
    - Sets request_id in context for error handlers
    - Adds x-request-id to response headers
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate request_id
        request_id = request.headers.get("x-request-id")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Set in context for error handlers and logging
        set_request_id(request_id)
        
        # Store in request state for endpoint access
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request_id to response headers
        response.headers["x-request-id"] = request_id
        
        return response
