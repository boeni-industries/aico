"""
Validation Plugin for AICO API Gateway

Handles message validation and conversion in the modular plugin architecture.
"""

from typing import Dict, Any
from backend.core.plugin_base import BasePlugin, PluginMetadata, PluginPriority
from ..middleware.validator import MessageValidator, ValidationError
from aico.core.logging import get_logger


class ValidationPlugin(BasePlugin):
    """
    Message validation plugin
    
    Wraps existing MessageValidator middleware into the plugin system.
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        self.validator: MessageValidator = None
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="validation",
            version="1.0.0",
            description="Message validation and conversion plugin",
            priority=PluginPriority.MEDIUM,  # Validation runs after rate limiting
            dependencies=["security", "rate_limiting"],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "strict_validation": {"type": "boolean", "default": False}
            }
        )
    
    async def initialize(self) -> None:
        """Initialize message validator"""
        try:
            self.validator = MessageValidator()
            self.logger.info("Validation plugin initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize validation plugin: {e}")
            raise
    
    async def start(self) -> None:
        """Start the validation plugin"""
        self.logger.info("Validation plugin started")
    
    async def stop(self) -> None:
        """Stop the validation plugin"""
        self.logger.info("Validation plugin stopped")
    
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through validation"""
        if not self.enabled:
            return context
        
        try:
            request_data = context.get('request_data')
            
            # Only validate if we have an AicoMessage
            if hasattr(request_data, 'metadata') and hasattr(request_data, 'payload'):
                validated_message = await self.validator.validate_and_convert(request_data)
                context['request_data'] = validated_message
                context['message_type'] = validated_message.metadata.message_type
            
            self.logger.debug("Message validation passed")
            return context
            
        except ValidationError as e:
            self.logger.warning(f"Message validation failed: {e}")
            context['error'] = {
                'status_code': 400,
                'message': 'Message validation failed',
                'detail': str(e)
            }
            return context
        except Exception as e:
            self.logger.error(f"Validation plugin error: {e}")
            # On error, continue processing if not strict validation
            if not self.config_manager.get("core.api_gateway.validation.strict_validation", False):
                return context
            
            context['error'] = {
                'status_code': 500,
                'message': 'Validation processing error',
                'detail': str(e)
            }
            return context
    
    async def shutdown(self) -> None:
        """Cleanup validation plugin resources"""
        self.logger.info("Validation plugin shutdown")
