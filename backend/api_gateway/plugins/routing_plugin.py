"""
Routing Plugin for AICO API Gateway

Handles message routing to the message bus in the modular plugin architecture.
"""

from typing import Dict, Any
from ..core.plugin_registry import PluginInterface, PluginMetadata, PluginPriority
from ..models.core.message_router import MessageRouter


class RoutingPlugin(PluginInterface):
    """
    Message routing plugin
    
    Routes validated messages to the AICO message bus system.
    """
    
    def __init__(self, config: Dict[str, Any], logger):
        super().__init__(config, logger)
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
    
    async def initialize(self, dependencies: Dict[str, Any]) -> None:
        """Initialize message router"""
        try:
            config = dependencies.get('config')
            
            if not config:
                raise ValueError("config dependency required")
            
            # Get routing config from the config object
            core_config = config.get('core', {})
            api_gateway_config = core_config.get('api_gateway', {})
            router_config = api_gateway_config.get('routing', {})
            
            # Create router without message bus (will be set in start())
            self.message_router = MessageRouter(router_config)
            
            self.message_bus = dependencies.get('message_bus')
            if not self.message_bus:
                raise ValueError("message_bus dependency not found")

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
            # Set up message bus connection if available
            if self.message_bus and self.message_router:
                await self.message_router.set_message_bus(self.message_bus)
                self.logger.info("Routing plugin started with message bus")
            else:
                self.logger.warning("Routing plugin started without message bus")
        except Exception as e:
            self.logger.error(f"Failed to start routing plugin: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Cleanup routing plugin resources"""
        if self.message_router:
            await self.message_router.cleanup()
        self.logger.info("Routing plugin shutdown")
