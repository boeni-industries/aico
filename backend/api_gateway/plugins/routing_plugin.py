"""
Routing Plugin for AICO API Gateway

Handles message routing to the message bus in the modular plugin architecture.
"""

from typing import Dict, Any
from backend.core.plugin_base import BasePlugin, PluginMetadata, PluginPriority
from ..models.core.message_router import MessageRouter
from aico.core.logging import get_logger


class RoutingPlugin(BasePlugin):
    """
    Message routing plugin
    
    Routes validated messages to the AICO message bus system.
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        self.message_router: MessageRouter = None
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="routing",
            version="1.0.0",
            description="Message routing to message bus plugin",
            priority=PluginPriority.LOW,  # Routing runs last in the pipeline
            dependencies=["security", "rate_limiting", "validation", "message_bus"],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "timeout_seconds": {"type": "integer", "default": 30}
            }
        )
    
    async def initialize(self) -> None:
        """Initialize message router"""
        try:
            config_manager = self.require_service('config')
            
            # Get routing config from the config object
            core_config = config_manager.get('core', {})
            api_gateway_config = core_config.get('api_gateway', {})
            router_config = api_gateway_config.get('routing', {})
            
            # Create router without message bus (will be set in start())
            self.message_router = MessageRouter(router_config)
            
            # Message bus will be available during start phase

            self.logger.info("Routing plugin initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize routing plugin: {e}")
            raise
    
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through routing"""
        if not self.enabled:
            return context
        
        try:
            request_data = context.get('request_data')
            
            # Route message to message bus
            response = await self.message_router.route_message(request_data)
            context['response'] = response
            
            self.logger.debug("Message routing completed")
            return context
            
        except Exception as e:
            self.logger.error(f"Routing plugin error: {e}")
            context['error'] = {
                'status_code': 500,
                'message': 'Message routing failed',
                'detail': str(e)
            }
            return context
    
    async def start(self) -> None:
        """Start the routing plugin"""
        try:
            # Get message bus service from container
            message_bus_plugin = self.require_service('message_bus_plugin')
            
            # Register as a module to get a MessageBusClient (not the host)
            message_bus_client = await message_bus_plugin.message_bus_host.register_module(
                "api_gateway", 
                ["api.response.*", "system.error.*"]
            )
            
            await self.message_router.set_message_bus(message_bus_client)
            self.logger.info("Routing plugin started with message bus")
        except Exception as e:
            self.logger.error(f"Failed to start routing plugin: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the routing plugin"""
        if self.message_router:
            await self.message_router.cleanup()
        self.logger.info("Routing plugin stopped")
