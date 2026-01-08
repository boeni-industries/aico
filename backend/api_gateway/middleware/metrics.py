"""
API Gateway Metrics Middleware

Collects real-time HTTP request metrics using OpenTelemetry.
Records request method, path, status code, and latency to database.
"""

import time
from typing import Callable
from starlette.types import ASGIApp, Receive, Send, Scope
from starlette.requests import Request
from starlette.datastructures import Headers

from opentelemetry import metrics
from aico.core.logging import get_logger

logger = get_logger("backend", "api_gateway.metrics")


class MetricsMiddleware:
    """
    ASGI middleware for collecting API Gateway request metrics.
    
    Tracks:
    - Request method and path
    - Response status code
    - Request latency in milliseconds
    - Protocol (REST/WebSocket)
    """
    
    def __init__(self, app: ASGIApp):
        self.app = app
        
        # Get OpenTelemetry meter
        meter = metrics.get_meter("aico.api_gateway")
        
        # Create histogram for request duration
        self.request_duration = meter.create_histogram(
            name="aico.api.request.duration",
            description="HTTP request duration in seconds",
            unit="s"
        )
        
        # Create counter for request count
        self.request_counter = meter.create_counter(
            name="aico.api.request.count",
            description="Total number of HTTP requests",
            unit="1"
        )
        
        logger.info("API Gateway metrics middleware initialized")
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI middleware entry point"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Start timing
        start_time = time.perf_counter()
        
        # Extract request info
        request = Request(scope, receive)
        method = request.method
        path = request.url.path
        
        # Track response status
        status_code = 200  # Default
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)
        
        try:
            # Process request
            await self.app(scope, receive, send_wrapper)
            
        finally:
            # Calculate duration
            duration = time.perf_counter() - start_time
            
            # Record metrics with attributes
            attributes = {
                "http.method": method,
                "http.target": path,
                "http.status_code": status_code,
                "http.scheme": "REST"
            }
            
            # Record duration histogram
            self.request_duration.record(duration, attributes)
            
            # Increment request counter
            self.request_counter.add(1, attributes)
            
            # Log high-latency requests
            if duration > 1.0:  # More than 1 second
                logger.warning(
                    f"Slow request: {method} {path} took {duration*1000:.0f}ms",
                    extra={
                        "method": method,
                        "path": path,
                        "duration_ms": duration * 1000,
                        "status_code": status_code
                    }
                )
