"""
AICO Plugin Base Classes - Standardized Plugin Architecture

Provides base classes and interfaces for all AICO plugins with consistent lifecycle
management, dependency injection, and error handling following AICO principles.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from aico.core.logging import get_logger
from .service_container import BaseService, ServiceContainer, ServiceState

class PluginPriority(Enum):
    """Plugin priority levels for startup ordering"""
    INFRASTRUCTURE = 10    # Core infrastructure (message bus, logging)
    SECURITY = 20         # Security and encryption
    MIDDLEWARE = 30       # Request/response middleware
    BUSINESS = 40         # Business logic plugins
    INTEGRATION = 50      # External integrations

@dataclass
class PluginMetadata:
    """Plugin metadata and configuration"""
    name: str
    version: str
    description: str
    priority: PluginPriority
    dependencies: List[str] = None
    enabled: bool = True

class PluginError(Exception):
    """Plugin-specific errors"""
    pass

class PluginInitializationError(PluginError):
    """Plugin initialization failed"""
    pass

class BasePlugin(BaseService):
    """
    Standardized base class for all AICO plugins
    
    Provides consistent lifecycle management, configuration access,
    and dependency injection following AICO architectural principles.
    """
    
    def __init__(self, name: str, container: ServiceContainer):
        super().__init__(name, container)
        
        # Plugin-specific configuration
        self.plugin_config = self.get_config(f"core.api_gateway.plugins.{name}", {})
        self.enabled = self.plugin_config.get("enabled", False)
        
        # Plugin metadata (must be implemented by subclasses)
        self._metadata: Optional[PluginMetadata] = None
        
        self.logger.debug(f"Plugin {name} initialized (enabled: {self.enabled})")
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize plugin resources
        
        Called once during startup after all dependencies are available.
        Should set up any required resources, connections, or state.
        """
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """
        Start plugin operations
        
        Called after initialization to begin active plugin operations.
        Should start any background tasks or active processing.
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """
        Stop plugin operations
        
        Called during shutdown to cleanly stop all plugin operations.
        Should cleanup resources and stop background tasks.
        """
        pass
    
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming request (optional override)
        
        Args:
            context: Request context with protocol, data, client_info
            
        Returns:
            Modified context or original context if no processing needed
        """
        return context
    
    async def process_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process outgoing response (optional override)
        
        Args:
            context: Response context with protocol, data, client_info
            
        Returns:
            Modified context or original context if no processing needed
        """
        return context
    
    async def health_check(self) -> Dict[str, Any]:
        """Plugin health check with standard format"""
        base_health = await super().health_check()
        
        plugin_health = {
            **base_health,
            "metadata": {
                "version": self.metadata.version,
                "description": self.metadata.description,
                "priority": self.metadata.priority.value,
                "dependencies": self.metadata.dependencies or []
            },
            "enabled": self.enabled,
            "configuration": {
                "has_config": bool(self.plugin_config),
                "config_keys": list(self.plugin_config.keys()) if self.plugin_config else []
            }
        }
        
        return plugin_health
    
    def require_enabled(self) -> None:
        """Ensure plugin is enabled, raise error if not"""
        if not self.enabled:
            raise PluginError(f"Plugin '{self.name}' is disabled but required operation attempted")
    
    async def _safe_initialize(self) -> None:
        """Safe initialization wrapper with error handling"""
        if not self.enabled:
            self.logger.info(f"Plugin {self.name} disabled, skipping initialization")
            self.state = ServiceState.STOPPED
            return
        
        try:
            self.state = ServiceState.INITIALIZING
            self.logger.info(f"Initializing plugin: {self.name}")
            
            await self.initialize()
            
            self.state = ServiceState.INITIALIZED
            self.logger.info(f"Plugin initialized successfully: {self.name}")
            
        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Plugin initialization failed for '{self.name}': {e}")
            raise PluginInitializationError(f"Failed to initialize plugin '{self.name}': {e}")
    
    async def _safe_start(self) -> None:
        """Safe start wrapper with error handling"""
        if not self.enabled or self.state != ServiceState.INITIALIZED:
            return
        
        try:
            self.state = ServiceState.STARTING
            self.logger.info(f"Starting plugin: {self.name}")
            
            await self.start()
            
            self.state = ServiceState.RUNNING
            self.logger.info(f"Plugin started successfully: {self.name}")
            
        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Plugin start failed for '{self.name}': {e}")
            raise PluginError(f"Failed to start plugin '{self.name}': {e}")
    
    async def _safe_stop(self) -> None:
        """Safe stop wrapper with error handling"""
        if self.state not in [ServiceState.RUNNING, ServiceState.ERROR]:
            return
        
        try:
            self.state = ServiceState.STOPPING
            self.logger.info(f"Stopping plugin: {self.name}")
            
            await self.stop()
            
            self.state = ServiceState.STOPPED
            self.logger.info(f"Plugin stopped successfully: {self.name}")
            
        except Exception as e:
            self.logger.error(f"Plugin stop failed for '{self.name}': {e}")
            # Don't raise during shutdown - log and continue
            self.state = ServiceState.ERROR

class InfrastructurePlugin(BasePlugin):
    """Base class for infrastructure plugins (message bus, logging, etc.)"""
    
    def __init__(self, name: str, container: ServiceContainer):
        super().__init__(name, container)
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.name,
            version="1.0.0",
            description=f"Infrastructure plugin: {self.name}",
            priority=PluginPriority.INFRASTRUCTURE,
            dependencies=[]
        )

class SecurityPlugin(BasePlugin):
    """Base class for security plugins (auth, encryption, etc.)"""
    
    def __init__(self, name: str, container: ServiceContainer):
        super().__init__(name, container)
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.name,
            version="1.0.0",
            description=f"Security plugin: {self.name}",
            priority=PluginPriority.SECURITY,
            dependencies=[]
        )

class MiddlewarePlugin(BasePlugin):
    """Base class for middleware plugins (rate limiting, validation, etc.)"""
    
    def __init__(self, name: str, container: ServiceContainer):
        super().__init__(name, container)
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.name,
            version="1.0.0",
            description=f"Middleware plugin: {self.name}",
            priority=PluginPriority.MIDDLEWARE,
            dependencies=[]
        )

class PluginRegistry:
    """
    Plugin registry for managing plugin classes and instances
    
    Provides centralized plugin registration and discovery.
    """
    
    def __init__(self):
        self._plugin_classes: Dict[str, type] = {}
        self.logger = get_logger("backend", "core.plugin_registry")
    
    def register_plugin_class(self, name: str, plugin_class: type) -> None:
        """Register a plugin class"""
        # Validate plugin inheritance
        
        if not issubclass(plugin_class, BasePlugin):
            raise PluginError(f"Plugin class {plugin_class} must inherit from BasePlugin")
        
        if name in self._plugin_classes:
            raise PluginError(f"Plugin class '{name}' already registered")
        
        self._plugin_classes[name] = plugin_class
        self.logger.debug(f"Plugin class registered: {name}")
    
    def get_plugin_class(self, name: str) -> Optional[type]:
        """Get plugin class by name"""
        return self._plugin_classes.get(name)
    
    def list_plugin_classes(self) -> List[str]:
        """List all registered plugin class names"""
        return list(self._plugin_classes.keys())
    
    def create_plugin_factory(self, name: str) -> callable:
        """Create a factory function for service container registration"""
        plugin_class = self.get_plugin_class(name)
        if not plugin_class:
            raise PluginError(f"Plugin class '{name}' not found")
        
        def factory(container: ServiceContainer, **kwargs) -> BasePlugin:
            # Ignore extra dependencies - plugins only need name and container
            return plugin_class(name, container)
        
        return factory

# Global plugin registry instance - initialized lazily to avoid logging dependency
plugin_registry = None

def get_plugin_registry():
    """Get or create the global plugin registry"""
    global plugin_registry
    if plugin_registry is None:
        # Plugin registry created
        plugin_registry = PluginRegistry()
    return plugin_registry
