"""
Request Logging Middleware

Logs all incoming HTTP requests to the AICO logging system via ZMQ transport.
"""

import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from aico.core.logging import get_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming HTTP requests"""
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.logger = get_logger("backend", "api_gateway.request_logging")
        print("[REQUEST LOGGING MIDDLEWARE] Initialized successfully")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log the incoming request and response"""
        start_time = time.time()
        
        # Extract comprehensive request details
        method = request.method
        url = str(request.url)
        path = request.url.path
        query_params = str(request.url.query) if request.url.query else None
        client_ip = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else None
        user_agent = request.headers.get("user-agent", "unknown")
        content_type = request.headers.get("content-type", "unknown")
        content_length = request.headers.get("content-length", "0")
        
        # Add debug print to verify middleware is called
        print(f"[REQUEST LOGGING] Processing {method} {path} from {client_ip}")
        
        # Log the incoming request with comprehensive details
        self.logger.info(
            f"REST REQUEST: {method} {path} from {client_ip}",
            extra={
                "event_type": "http_request_received",
                "method": method,
                "url": url,
                "path": path,
                "query_params": query_params,
                "client_ip": client_ip,
                "client_port": client_port,
                "user_agent": user_agent,
                "content_type": content_type,
                "content_length": content_length,
                "request_id": id(request),
                "timestamp": start_time
            }
        )
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log the response with comprehensive details
            response_size = response.headers.get("content-length", "unknown")
            self.logger.info(
                f"REST RESPONSE: {method} {path} -> {response.status_code} ({process_time:.3f}s)",
                extra={
                    "event_type": "http_response_sent",
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "response_size": response_size,
                    "request_id": id(request),
                    "success": 200 <= response.status_code < 400
                }
            )
            
            return response
            
        except Exception as e:
            # Log errors with comprehensive details
            process_time = time.time() - start_time
            self.logger.error(
                f"REST ERROR: {method} {path} -> ERROR: {str(e)} ({process_time:.3f}s)",
                extra={
                    "event_type": "http_request_error",
                    "method": method,
                    "path": path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "process_time": process_time,
                    "request_id": id(request),
                    "client_ip": client_ip
                }
            )
            raise
