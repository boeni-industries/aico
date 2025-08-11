"""
AICO API Gateway

Unified multi-protocol API Gateway providing REST, WebSocket, ZeroMQ IPC, and gRPC
interfaces to the AICO message bus with adaptive transport and zero-trust security.
"""

from .core.gateway import AICOAPIGateway
from .core.auth import AuthenticationManager, AuthorizationManager
from .core.transport import AdaptiveTransport
from .adapters.rest_adapter import RESTAdapter
from .adapters.websocket_adapter import WebSocketAdapter
from .adapters.zeromq_adapter import ZeroMQAdapter

__all__ = [
    "AICOAPIGateway",
    "AuthenticationManager", 
    "AuthorizationManager",
    "AdaptiveTransport",
    "RESTAdapter",
    "WebSocketAdapter", 
    "ZeroMQAdapter"
]
