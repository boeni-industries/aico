"""
API Gateway Metrics Middleware

Collects real-time HTTP request metrics using OpenTelemetry.
Records request method, path, status code, and latency to database.
Classifies requests by service and category for drill-down analysis.
"""

import time
from typing import Callable
from starlette.types import ASGIApp, Receive, Send, Scope
from starlette.requests import Request
from starlette.datastructures import Headers

from opentelemetry import metrics
from aico.core.logging import get_logger

logger = get_logger("backend.api_gateway.metrics")


def classify_service(path: str) -> str:
    """Classify request by service based on path pattern.
    
    All API paths follow the pattern: /api/v1/{service}/...
    """
    if not path or not path.startswith('/api/v1/'):
        return 'unknown'
    
    # Extract service from path: /api/v1/{service}/...
    parts = path.split('/')
    if len(parts) >= 4:
        service = parts[3]
    else:
        return 'unknown'
    
    # Map to standardized service names
    service_map = {
        'conversation': 'Conversation',
        'agency': 'Agency',
        'memory': 'Memory',
        'operations': 'Operations',
        'system': 'System',
        'admin': 'Admin',
        'security': 'Security',
        'auth': 'Authentication',
        'modelservice': 'Modelservice',
        'metrics': 'Metrics',
        'users': 'Users',
        'goals': 'Agency',
        'tasks': 'Operations',
        'health': 'System',
        'echo': 'System',
        'logs': 'System',
        'handshake': 'System',
    }
    
    return service_map.get(service.lower(), service.capitalize())


def classify_category(path: str) -> str:
    """Classify request by functional category."""
    if not path:
        return 'other'
    
    path_lower = path.lower()
    
    # User-facing chat/conversation endpoints
    if any(p in path_lower for p in ['/conversation/send', '/conversation/stream', '/conversation/chat', '/conversation/messages', '/conversation/proactive/']):
        return 'user_chat'
    
    # Admin/operations endpoints
    if any(p in path_lower for p in ['/admin/', '/operations/', '/system/admin']):
        return 'admin'
    
    # Security/auth endpoints (includes user management and sessions)
    if any(p in path_lower for p in ['/security/', '/auth/', '/login', '/logout', '/token', '/handshake', '/users/', '/users-sessions/']):
        return 'security'
    
    # System/monitoring endpoints
    if any(p in path_lower for p in ['/system/', '/metrics/', '/health', '/logs']):
        return 'system'
    
    # Memory operations
    if '/memory/' in path_lower or '/kg/' in path_lower:
        return 'memory'
    
    # Agency operations
    if '/agency/' in path_lower or '/goals/' in path_lower:
        return 'agency'
    
    # Speech services (TTS/STT)
    if '/tts/' in path_lower or '/stt/' in path_lower:
        return 'speech'
    
    # Model/AI operations
    if '/modelservice/' in path_lower or '/inference/' in path_lower:
        return 'ai'
    
    # Emotion/behavioral endpoints
    if '/emotion/' in path_lower or '/behavioral/' in path_lower:
        return 'emotion'
    
    return 'other'


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
            
            # Classify request
            service = classify_service(path)
            category = classify_category(path)
            
            # Record metrics with attributes
            attributes = {
                "http.method": method,
                "http.target": path,
                "http.status_code": status_code,
                "http.scheme": "REST",
                "service": service,
                "category": category
            }
            
            # Record duration histogram
            self.request_duration.record(duration, attributes)
            
            # Increment request counter
            self.request_counter.add(1, attributes)
            
            # Log high-latency requests with category-based thresholds
            # Different categories have different performance expectations
            thresholds = {
                'user_chat': 1.0,      # User-facing chat - keep strict (1s)
                'security': 1.0,       # Auth/security - keep strict (1s)
                'system': 1.5,         # Health checks/monitoring - relaxed (1.5s)
                'agency': 1.5,         # Complex aggregations - relaxed (1.5s)
                'memory': 1.5,         # Complex queries - relaxed (1.5s)
                'admin': 2.0,          # Admin operations - very relaxed (2s)
                'operations': 1.5,     # Operations - relaxed (1.5s)
                'other': 1.0,          # Default - strict (1s)
            }
            
            threshold = thresholds.get(category, 1.0)
            
            if duration > threshold:
                logger.warning(
                    f"Slow request: {method} {path} took {duration*1000:.0f}ms (threshold: {threshold*1000:.0f}ms for {category})",
                    extra={
                        "method": method,
                        "path": path,
                        "duration_ms": duration * 1000,
                        "status_code": status_code,
                        "category": category,
                        "threshold_ms": threshold * 1000
                    }
                )
