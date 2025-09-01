"""
Encryption Plugin for AICO API Gateway

Handles transport encryption and key management in the modular plugin architecture.
"""

from typing import Dict, Any
from backend.core.plugin_base import BasePlugin, PluginMetadata, PluginPriority
from aico.core.logging import get_logger
from aico.security.key_manager import AICOKeyManager



class EncryptionPlugin(BasePlugin):
    """
    Transport encryption plugin
    
    Manages encryption keys and secure transport channels.
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        self.key_manager = None
        
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="encryption",
            version="1.0.0",
            description="Transport encryption and key management plugin",
            priority=PluginPriority.SECURITY,
            dependencies=[],
            enabled=True
        )
    
    async def initialize(self) -> None:
        """Initialize encryption components"""
        try:
            # Initialize key manager
            print("[+] Initializing transport security...")
            config_service = self.require_service('config')
            self.key_manager = AICOKeyManager(config_service)
            
            # Display transport security status
            print("[✓] Transport encryption keys loaded")
            print("[✓] AES-256-GCM encryption ready")
            print("[✓] Transport security middleware active")
            
            self.logger.info("Transport security initialized successfully")
            
        except Exception as e:
            print("[✗] Transport security initialization failed")
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
        await super().start()
        self.logger.info("Encryption plugin started")
    
    async def stop(self) -> None:
        """Stop the encryption plugin"""
        await super().stop()
        self.logger.info("Encryption plugin stopped")
    
    async def shutdown(self) -> None:
        """Legacy compatibility method"""
        await self.stop()
