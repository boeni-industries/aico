"""
AICO API Gateway

Unified multi-protocol API Gateway providing REST, WebSocket, ZeroMQ IPC, and gRPC
interfaces to the AICO message bus with adaptive transport and zero-trust security.
"""

# New Architecture - Plugin-based API Gateway V2
from .gateway_v2 import AICOAPIGatewayV2, AICOAPIGateway
from .core.gateway_core import GatewayCore
from .core.plugin_registry import PluginRegistry, PluginInterface, PluginMetadata, PluginPriority
from .core.protocol_manager import ProtocolAdapterManager

# Legacy compatibility (deprecated - use AICOAPIGatewayV2)
from .models.core.auth import AuthenticationManager, AuthorizationManager
from .models.core.transport import AdaptiveTransport

__all__ = [
    # New Architecture (Recommended)
    "AICOAPIGatewayV2",
    "AICOAPIGateway",  # Alias for V2
    "GatewayCore",
    "PluginRegistry",
    "PluginInterface", 
    "PluginMetadata",
    "PluginPriority",
    "ProtocolAdapterManager",
    
    # Legacy compatibility (deprecated)
    "AuthenticationManager", 
    "AuthorizationManager",
    "AdaptiveTransport"
]
