"""
Security Plugin for AICO API Gateway

Handles authentication, authorization, and security middleware
in the modular plugin architecture.
"""

from typing import Dict, Any
from backend.core.plugin_base import BasePlugin, PluginMetadata, PluginPriority
from ..models.core.auth import AuthenticationManager, AuthorizationManager
from aico.core.logging import get_logger


class SecurityPlugin(BasePlugin):
    """
    Security plugin handling authentication and authorization
    
    Integrates existing AICO security infrastructure into the
    modular plugin system.
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        self.auth_manager: AuthenticationManager = None
        self.authz_manager: AuthorizationManager = None
        
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="security",
            version="1.0.0",
            description="Authentication and authorization security plugin",
            priority=PluginPriority.SECURITY,
            dependencies=[],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "auth": {"type": "object"},
                "authz": {"type": "object"}
            }
        )
    
    def get_auth_manager(self) -> AuthenticationManager:
        """Get the authentication manager instance"""
        return self.auth_manager
    
    def get_authz_manager(self) -> AuthorizationManager:
        """Get the authorization manager instance"""
        return self.authz_manager
    
    async def initialize(self) -> None:
        """Initialize security managers"""
        try:
            config_manager = self.require_service('config')
            database = self.require_service('database')
            
            # Create authentication manager instance
            self.auth_manager = AuthenticationManager(config_manager, db_connection=database)
            print("[✓] Authentication manager ready")
            
            # Create authorization manager instance  
            security_config = config_manager.get("security", {})
            self.authz_manager = AuthorizationManager(security_config)
            print("[✓] Authorization manager ready")
            
            print("[✓] Security middleware active")
            self.logger.info("Security plugin initialized successfully")
            
        except Exception as e:
            print("[✗] Security middleware initialization failed")
            self.logger.error(f"Failed to initialize security plugin: {e}")
            raise
    
    async def start(self) -> None:
        """Start the security plugin"""
        await super().start()
        self.logger.info("Security plugin started")
    
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through security pipeline"""
        if not self.enabled:
            return context
        
        try:
            request_data = context.get('request_data')
            client_info = context.get('client_info', {})
            
            # 1. Authentication
            auth_result = await self.auth_manager.authenticate(request_data, client_info)
            if not auth_result.success:
                context['error'] = {
                    'status_code': 401,
                    'message': 'Authentication failed',
                    'detail': auth_result.error
                }
                return context
            
            # Store authenticated user in context
            context['user'] = auth_result.user
            context['auth_method'] = auth_result.method
            
            # 2. Authorization (if message type is available)
            message_type = getattr(request_data, 'message_type', None) or context.get('message_type')
            if message_type:
                authz_result = await self.authz_manager.authorize(
                    auth_result.user,
                    message_type,
                    request_data
                )
                
                if not authz_result.success:
                    context['error'] = {
                        'status_code': 403,
                        'message': 'Authorization failed',
                        'detail': authz_result.error
                    }
                    return context
            
            self.logger.debug("Security check passed", extra={
                "user": auth_result.user.user_uuid,
                "method": auth_result.method.value if auth_result.method else "unknown"
            })
            
            return context
            
        except Exception as e:
            self.logger.error(f"Security plugin error: {e}")
            context['error'] = {
                'status_code': 500,
                'message': 'Security processing error',
                'detail': str(e)
            }
            return context
    
    def configure_middleware(self, app) -> None:
        """Configure security middleware on FastAPI app"""
        if not self.enabled:
            return
        
        # NOTE: Security middleware disabled to prevent bypassing ASGI encryption middleware
        # The FastAPI HTTP middleware intercepts requests before ASGI middleware can process them
        # Security features should be implemented at the ASGI level if needed
        self.logger.info("Security middleware skipped - would bypass ASGI encryption middleware")
    
    async def stop(self) -> None:
        """Stop the security plugin"""
        await super().stop()
        self.logger.info("Security plugin stopped")
    
    async def shutdown(self) -> None:
        """Legacy compatibility method"""
        await self.stop()
