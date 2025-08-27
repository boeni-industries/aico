"""
Plugin Registry and Interface for AICO API Gateway

Provides plugin management, loading, and lifecycle coordination
following modern plugin architecture patterns.
"""

import asyncio
import importlib
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Callable
from dataclasses import dataclass
from enum import Enum

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager


class PluginPriority(Enum):
    """Plugin execution priority levels"""
    INFRASTRUCTURE = 0  # Infrastructure plugins (logging, monitoring)
    HIGHEST = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    LOWEST = 5


@dataclass
class PluginMetadata:
    """Plugin metadata and configuration"""
    name: str
    version: str
    description: str
    priority: PluginPriority
    dependencies: List[str]
    config_schema: Dict[str, Any]


class PluginInterface(ABC):
    """
    Base interface for all API Gateway plugins
    
    Plugins implement specific middleware functionality in a modular,
    reusable way following the chain of responsibility pattern.
    """
    
    def __init__(self, config: Dict[str, Any], logger):
        self.config = config
        self.logger = logger
        self.enabled = config.get("enabled", True)
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata"""
        pass
    
    @abstractmethod
    async def initialize(self, dependencies: Dict[str, Any]) -> None:
        """Initialize plugin with dependencies"""
        pass
    
    @abstractmethod
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming request
        
        Args:
            context: Request context containing:
                - protocol: Protocol name (rest, websocket, etc.)
                - request_data: Raw request data
                - client_info: Client information
                - gateway: Gateway core instance
                - plugins: Other loaded plugins
        
        Returns:
            Updated context with any modifications
        """
        pass
    
    async def process_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process outgoing response (optional)
        
        Default implementation passes through unchanged.
        """
        return context
    
    async def shutdown(self) -> None:
        """Cleanup plugin resources"""
        pass
    
    def is_enabled(self) -> bool:
        """Check if plugin is enabled"""
        return self.enabled


class PluginRegistry:
    """
    Plugin registry for managing plugin lifecycle and dependencies
    
    Handles plugin registration, loading, dependency resolution,
    and execution order management.
    """
    
    def __init__(self, config: ConfigurationManager, logger):
        self.config = config
        self.logger = logger
        
        # Plugin storage
        self.registered_plugins: Dict[str, Type[PluginInterface]] = {}
        self.loaded_plugins: Dict[str, PluginInterface] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        
        # Dependency graph
        self.dependency_graph: Dict[str, List[str]] = {}
        self.execution_order: List[str] = []
        
        self.logger.info("Plugin registry initialized")
    
    def register_plugin(self, name: str, plugin_instance: PluginInterface) -> None:
        """Register a plugin instance"""
        if not isinstance(plugin_instance, PluginInterface):
            raise ValueError(f"Plugin {name} must implement PluginInterface")
        
        self.registered_plugins[name] = plugin_instance
        self.logger.debug(f"Registered plugin: {name}")
    
    async def load_plugin(self, name: str, config: Dict[str, Any]) -> Optional[PluginInterface]:
        """Load and initialize a plugin"""
        try:
            if name not in self.registered_plugins:
                self.logger.error(f"Plugin not registered: {name}")
                return None
            
            # Create plugin instance
            plugin_class = self.registered_plugins[name]
            plugin = plugin_class(config, self.logger)
            
            # Store configuration
            self.plugin_configs[name] = config
            
            # Check if plugin is enabled
            if not plugin.is_enabled():
                self.logger.info(f"Plugin {name} is disabled, skipping load")
                return None
            
            # Initialize plugin
            dependencies = self._get_plugin_dependencies(name)
            await plugin.initialize(dependencies)
            
            # Store loaded plugin
            self.loaded_plugins[name] = plugin
            
            # Update dependency graph
            self._update_dependency_graph(name, plugin.metadata.dependencies)
            
            self.logger.info(f"Loaded plugin: {name} v{plugin.metadata.version}")
            return plugin
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin {name}: {e}")
            return None
    
    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin"""
        try:
            if name in self.loaded_plugins:
                plugin = self.loaded_plugins[name]
                asyncio.create_task(plugin.shutdown())
                del self.loaded_plugins[name]
                
                # Remove from dependency graph
                if name in self.dependency_graph:
                    del self.dependency_graph[name]
                
                self.logger.info(f"Unloaded plugin: {name}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to unload plugin {name}: {e}")
            return False
    
    def get_plugin(self, name: str) -> Optional[PluginInterface]:
        """Get a registered plugin by name"""
        return self.registered_plugins.get(name)
    
    def get_loaded_plugins(self) -> Dict[str, PluginInterface]:
        """Get all loaded plugins"""
        return self.loaded_plugins.copy()
    
    def get_execution_order(self) -> List[str]:
        """Get plugin execution order based on priorities and dependencies"""
        if not self.execution_order:
            self._calculate_execution_order()
        return self.execution_order.copy()
    
    def _get_plugin_dependencies(self, name: str) -> Dict[str, Any]:
        """Get dependencies for plugin initialization"""
        dependencies = {
            'config': self.config,
            'logger': self.logger,
            'registry': self
        }
        
        # Add other loaded plugins as dependencies
        for plugin_name, plugin in self.loaded_plugins.items():
            if plugin_name != name:
                dependencies[f'plugin_{plugin_name}'] = plugin
        
        return dependencies
    
    def _update_dependency_graph(self, plugin_name: str, dependencies: List[str]) -> None:
        """Update the plugin dependency graph"""
        self.dependency_graph[plugin_name] = dependencies
        
        # Recalculate execution order
        self._calculate_execution_order()
    
    def _calculate_execution_order(self) -> None:
        """Calculate plugin execution order using topological sort"""
        try:
            # Get all plugins sorted by priority first
            plugins_by_priority = []
            for name, plugin in self.loaded_plugins.items():
                plugins_by_priority.append((plugin.metadata.priority.value, name))
            
            plugins_by_priority.sort(key=lambda x: x[0])  # Sort by priority value
            
            # Simple execution order based on priority
            # In a full implementation, this would use topological sort for dependencies
            self.execution_order = [name for _, name in plugins_by_priority]
            
            self.logger.debug(f"Plugin execution order: {self.execution_order}")
            
        except Exception as e:
            self.logger.error(f"Failed to calculate execution order: {e}")
            # Fallback to simple alphabetical order
            self.execution_order = sorted(self.loaded_plugins.keys())
    
    def _validate_dependencies(self, plugin_name: str, dependencies: List[str]) -> bool:
        """Validate that plugin dependencies are satisfied"""
        for dep in dependencies:
            if dep not in self.loaded_plugins:
                self.logger.error(f"Plugin {plugin_name} depends on {dep} which is not loaded")
                return False
        return True
    
    async def reload_plugin(self, name: str) -> bool:
        """Reload a plugin (unload and load again)"""
        try:
            if name in self.loaded_plugins:
                config = self.plugin_configs.get(name, {})
                self.unload_plugin(name)
                plugin = await self.load_plugin(name, config)
                return plugin is not None
            return False
        except Exception as e:
            self.logger.error(f"Failed to reload plugin {name}: {e}")
            return False
    
    def get_plugin_stats(self) -> Dict[str, Any]:
        """Get plugin registry statistics"""
        return {
            "registered_plugins": len(self.registered_plugins),
            "loaded_plugins": len(self.loaded_plugins),
            "plugin_names": list(self.loaded_plugins.keys()),
            "execution_order": self.get_execution_order()
        }
