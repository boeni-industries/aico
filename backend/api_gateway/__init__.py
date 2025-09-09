"""
AICO API Gateway

Unified multi-protocol API Gateway providing REST, WebSocket, ZeroMQ IPC, and gRPC
interfaces to the AICO message bus with adaptive transport and zero-trust security.
"""

# New Architecture - Service Container based API Gateway
from .core.gateway_core import GatewayCore as AICOAPIGateway
from .core.gateway_core import GatewayCore
from .core.plugin_registry import PluginRegistry, PluginInterface, PluginMetadata, PluginPriority
from .core.protocol_manager import ProtocolAdapterManager


__all__ = [
    "AICOAPIGateway",
    "GatewayCore",
    "PluginRegistry",
    "PluginInterface", 
    "PluginMetadata",
    "PluginPriority",
    "ProtocolAdapterManager"
]
