"""
Message Bus Plugin for AICO API Gateway

Integrates the central message bus broker into the modular plugin architecture,
maintaining architectural consistency by treating message bus as a plugin
rather than external dependency injection.
"""

import asyncio
from typing import Dict, Any, Optional

from backend.core.plugin_base import BasePlugin, PluginMetadata, PluginPriority
from aico.core.logging import get_logger


class MessageBusPlugin(BasePlugin):
    """
    Message bus plugin for centralized message broker and module coordination
    
    Provides unified message bus infrastructure as a plugin component,
    maintaining architectural consistency with the modular design.
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        self.message_bus_host: Optional[Any] = None
        self.bind_address = "tcp://*:5555"
        
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="message_bus",
            version="1.0.0",
            description="Central message bus broker for inter-module communication",
            priority=PluginPriority.INFRASTRUCTURE,  # Infrastructure-level plugin
            dependencies=[],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "bind_address": {"type": "string", "default": "tcp://*:5555"},
                "pub_port": {"type": "integer", "default": 5555},
                "sub_port": {"type": "integer", "default": 5556},
                "persistence_enabled": {"type": "boolean", "default": True},
                "topic_permissions": {"type": "object", "default": {}}
            }
        )
    
    async def initialize(self) -> None:
        """Initialize plugin with dependencies"""
        # Get database connection from service container
        self.db_connection = self.require_service('database')
        #print(f"[MESSAGE BUS PLUGIN] initialize() - db_connection: {self.db_connection is not None}")
    
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request - required by PluginInterface"""
        return context
    
    async def start(self) -> None:
        """Start the message bus broker"""
        try:
            #print(f"[MESSAGE BUS PLUGIN] start() called")
            
            # Get message bus configuration
            mb_config = self.get_config("message_bus", {})
            self.bind_address = mb_config.get("bind_address", "tcp://*:5555")
            
            # Import and initialize message bus host
            from backend.message_bus_host import AICOMessageBusHost
            
            self.message_bus_host = AICOMessageBusHost(self.bind_address)
            #print(f"[MESSAGE BUS PLUGIN] Created message bus host on {self.bind_address}")
            
            # Start message bus host directly in current async context
            #print(f"[MESSAGE BUS PLUGIN] Starting message bus host...")
            await self.message_bus_host.start(db_connection=self.db_connection)
            #print(f"[MESSAGE BUS PLUGIN] Message bus host started successfully")
            
            self.logger.info("Message bus plugin started", extra={
                "bind_address": self.bind_address,
                "db_connection": "provided" if self.db_connection else "none",
                "persistence": "enabled" if self.db_connection else "disabled"
            })
            
        except Exception as e:
            self.logger.error(f"Failed to start message bus plugin: {e}")
            print(f"[ERROR]: Failed to start message bus plugin: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            raise
    
    async def stop(self) -> None:
        """Stop the message bus broker"""
        if self.message_bus_host:
            try:
                await self.message_bus_host.stop()
                self.logger.info("Message bus plugin stopped")
            except Exception as e:
                self.logger.error(f"Error stopping message bus plugin: {e}")
    
    
    async def process_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Message bus doesn't process responses - it's infrastructure"""
        return context
    
    def get_message_bus_host(self) -> Optional[Any]:
        """Get the message bus host instance for external access"""
        return self.message_bus_host
    
    async def register_module(self, module_name: str, topic_permissions: list = None) -> Any:
        """Register a module with the message bus"""
        if not self.message_bus_host:
            raise RuntimeError("Message bus not initialized")
        
        return await self.message_bus_host.register_module(module_name, topic_permissions)
    
    async def unregister_module(self, module_name: str) -> None:
        """Unregister a module from the message bus"""
        if not self.message_bus_host:
            return
        
        await self.message_bus_host.unregister_module(module_name)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        if not self.message_bus_host:
            return {"status": "not_initialized"}
        
        try:
            stats = await self.message_bus_host.get_message_stats()
            stats["plugin_status"] = "running" if self.enabled else "disabled"
            return stats
        except Exception as e:
            return {"error": str(e), "plugin_status": "error"}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check message bus health status"""
        if not self.enabled:
            return {"status": "disabled", "message": "Message bus plugin disabled"}
        
        if not self.message_bus_host:
            return {"status": "error", "message": "Message bus not initialized"}
        
        try:
            # Check if message bus is running
            is_running = getattr(self.message_bus_host, 'running', False)
            
            stats = await self.get_stats() if is_running else {}
            
            return {
                "status": "healthy" if is_running else "stopped",
                "message": f"Message bus {'running' if is_running else 'stopped'}",
                "bind_address": self.bind_address,
                "persistence": "enabled" if self.db_connection else "disabled",
                "registered_modules": stats.get("registered_modules", []),
                "total_messages": stats.get("total_messages", 0)
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Health check failed: {e}"
            }
    
    async def shutdown(self) -> None:
        """Cleanup message bus plugin resources"""
        self.logger.info("Shutting down message bus plugin...")
        if self.message_bus_host:
            try:
                await self.message_bus_host.stop()
                self.message_bus_host = None
            except Exception as e:
                self.logger.error(f"Error during message bus shutdown: {e}")
        self.logger.info("Message bus plugin shutdown complete")
