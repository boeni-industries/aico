"""
Base Protocol Adapter Interface for AICO API Gateway

Defines the common interface and shared functionality for all protocol adapters
in the modular API Gateway architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..core.protocol_manager import ProtocolAdapter


class BaseProtocolAdapter(ProtocolAdapter):
    """
    Base implementation for protocol adapters with common functionality
    
    Provides shared utilities and patterns for all protocol adapters
    while maintaining the clean interface contract.
    """
    
    def __init__(self, config: Dict[str, Any], dependencies: Dict[str, Any]):
        super().__init__(config, dependencies)
        
        # Extract common dependencies
        self.key_manager = dependencies.get('key_manager')
        self.message_bus = dependencies.get('message_bus')
        self.plugins = dependencies.get('plugins', {})
        self.gateway_config = dependencies.get('config')
        
        # Common configuration
        self.host = config.get('host', '127.0.0.1')
        self.port = config.get('port', 8080)
        self.enabled = config.get('enabled', True)
    
    async def process_through_plugins(self, request_data: Any, client_info: Dict[str, Any]) -> Any:
        """
        Process request through the plugin pipeline
        
        This provides a common way for all protocol adapters to use
        the plugin system for request processing.
        """
        try:
            # Get gateway core from dependencies for plugin processing
            gateway = self.dependencies.get('gateway')
            if gateway:
                return await gateway.handle_request(
                    self.protocol_name, 
                    request_data, 
                    client_info
                )
            else:
                # Fallback: direct plugin processing
                context = {
                    'protocol': self.protocol_name,
                    'request_data': request_data,
                    'client_info': client_info,
                    'plugins': self.plugins
                }
                
                # Simple plugin chain execution
                for plugin_name in ['security', 'rate_limiting', 'validation', 'routing']:
                    plugin = self.plugins.get(plugin_name)
                    if plugin and plugin.is_enabled():
                        context = await plugin.process_request(context)
                        if context.get('error'):
                            return context['error']
                
                return context.get('response', {'success': True})
                
        except Exception as e:
            self.logger.error(f"Plugin processing error: {e}")
            return {'error': 'Internal processing error', 'success': False}
    
    def get_client_info(self, request_context: Any) -> Dict[str, Any]:
        """
        Extract client information from request context
        
        Override this method in specific adapters to extract
        protocol-specific client information.
        """
        return {
            'client_id': 'unknown',
            'protocol': self.protocol_name,
            'remote_addr': 'unknown',
            'user_agent': 'unknown'
        }
    
    def is_enabled(self) -> bool:
        """Check if adapter is enabled"""
        return self.enabled
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the adapter"""
        return {
            'protocol': self.protocol_name,
            'running': self.running,
            'enabled': self.enabled,
            'host': self.host,
            'port': self.port
        }
