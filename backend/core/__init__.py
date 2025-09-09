"""
AICO Backend Core - Clean Architecture Components

Provides the foundational components for AICO's backend architecture:
- Service container with dependency injection
- Plugin base classes and registry
- Lifecycle management for FastAPI integration
"""

from .service_container import ServiceContainer, BaseService, ServiceState, ServiceError
from .plugin_base import BasePlugin, PluginMetadata, PluginPriority, get_plugin_registry
from .lifecycle_manager import BackendLifecycleManager, get_service_container, get_user_service, get_auth_manager

__all__ = [
    "ServiceContainer",
    "BaseService", 
    "ServiceState",
    "ServiceError",
    "BasePlugin",
    "PluginMetadata",
    "PluginPriority",
    "get_plugin_registry",
    "BackendLifecycleManager",
    "get_service_container",
    "get_user_service", 
    "get_auth_manager"
]
