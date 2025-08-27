"""
Encryption Plugin for AICO API Gateway

Handles transport encryption and key management in the modular plugin architecture.
"""

from typing import Dict, Any
from ..core.plugin_registry import PluginInterface, PluginMetadata, PluginPriority


class EncryptionPlugin(PluginInterface):
    """
    Transport encryption plugin
    
    Manages encryption keys and secure transport channels.
    """
    
    def __init__(self, config: Dict[str, Any], logger):
        super().__init__(config, logger)
        self.key_manager = None
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="encryption",
            version="1.0.0",
            description="Transport encryption and key management plugin",
            priority=PluginPriority.INFRASTRUCTURE,  # Infrastructure level
            dependencies=[],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "key_rotation_hours": {"type": "integer", "default": 24}
            }
        )
    
    async def initialize(self, dependencies: Dict[str, Any]) -> None:
        """Initialize encryption components"""
        try:
            # Get key manager from dependencies if available
            self.key_manager = dependencies.get('key_manager')
            self.logger.info("Encryption plugin initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption plugin: {e}")
            raise
    
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through encryption"""
        if not self.enabled:
            return context
        
        try:
            # Encryption is handled by middleware, this plugin manages keys
            self.logger.debug("Encryption plugin processing completed")
            return context
            
        except Exception as e:
            self.logger.error(f"Encryption plugin error: {e}")
            context['error'] = {
                'status_code': 500,
                'message': 'Encryption processing failed',
                'detail': str(e)
            }
            return context
    
    async def start(self) -> None:
        """Start the encryption plugin"""
        self.logger.info("Encryption plugin started")
    
    async def shutdown(self) -> None:
        """Cleanup encryption plugin resources"""
        self.logger.info("Encryption plugin shutdown")
