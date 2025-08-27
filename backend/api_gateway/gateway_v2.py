"""
AICO API Gateway V2 - Modular Architecture

Refactored API Gateway with plugin-based architecture for improved
extensibility, maintainability, and testability.
"""

import signal
import asyncio
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from .core.gateway_core import GatewayCore, GatewayStatus


class AICOAPIGatewayV2:
    """
    AICO API Gateway V2 - Modular Plugin-Based Architecture
    
    Provides a clean, extensible API Gateway implementation using a plugin-based
    architecture with protocol adapters for REST, WebSocket, and ZeroMQ.
    """
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None, db_connection=None):
        self.config_manager = config_manager or ConfigurationManager()
        self.db_connection = db_connection
        self.logger = get_logger("api_gateway", "gateway_v2")
        self.shutdown_event = asyncio.Event()
        
        # Initialize gateway core with database connection
        self.gateway_core = GatewayCore(
            self.config_manager, 
            self.logger,
            db_connection=db_connection
        )
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        self.logger.info("AICO API Gateway V2 initialized")
    
    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.shutdown_event.set()
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def start(self, message_bus_address: str = "tcp://localhost:5555") -> None:
        """Start the API Gateway"""
        await self.gateway_core.start()
        self.logger.info("AICO API Gateway V2 started")
    
    async def stop(self) -> None:
        """Stop the API Gateway"""
        await self.gateway_core.stop()
        self.logger.info("AICO API Gateway V2 stopped")
    
    def setup_fastapi_integration(self, app: FastAPI) -> None:
        """Setup FastAPI integration with REST adapter"""
        print("[DEBUG] setup_fastapi_integration() called")
        rest_adapter = self.gateway_core.protocol_manager.get_adapter('rest')
        print(f"[DEBUG] REST adapter found: {rest_adapter}")
        print(f"[DEBUG] REST adapter type: {type(rest_adapter)}")
        print(f"[DEBUG] Has setup_routes: {hasattr(rest_adapter, 'setup_routes') if rest_adapter else 'No adapter'}")
        
        if rest_adapter and hasattr(rest_adapter, 'setup_routes'):
            # Instead of mounting, let the REST adapter setup routes on the main app
            print("[DEBUG] About to call rest_adapter.setup_routes()")
            rest_adapter.setup_routes(app)
            print("[DEBUG] rest_adapter.setup_routes() completed")
            self.logger.info("FastAPI integration setup complete")
        else:
            self.logger.warning("REST adapter not available for FastAPI integration")
    
    @asynccontextmanager
    async def lifespan_context(self, app: FastAPI):
        """FastAPI lifespan context manager for startup/shutdown"""
        try:
            # Startup
            await self.start()
            self.logger.info("Gateway lifespan startup complete")
            yield
        finally:
            # Shutdown
            await self.stop()
            self.logger.info("Gateway lifespan shutdown complete")
    
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal"""
        await self.shutdown_event.wait()
    
    async def handle_request(self, protocol: str, request_data: Any, client_info: Dict[str, Any]) -> Any:
        """Handle request through the gateway core"""
        return await self.gateway_core.handle_request(protocol, request_data, client_info)
    
    def get_status(self) -> GatewayStatus:
        """Get gateway status"""
        return self.gateway_core.get_status()
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        return await self.gateway_core.health_check()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get gateway statistics"""
        return self.gateway_core.get_statistics()
    
    def get_plugin(self, plugin_name: str):
        """Get a loaded plugin"""
        return self.gateway_core.get_plugin(plugin_name)
    
    def get_protocol_adapter(self, protocol_name: str):
        """Get a protocol adapter"""
        return self.gateway_core.get_protocol_adapter(protocol_name)
    
    def create_rest_adapter(self):
        """Get REST adapter for FastAPI integration"""
        return self.gateway_core.protocol_manager.active_adapters.get('rest')
    
    def configure_main_app(self, app: FastAPI):
        """Configure main FastAPI app with plugin-based middleware and infrastructure"""
        # Let plugins configure their middleware through the plugin system
        # This ensures proper architecture compliance
        
        # Add basic infrastructure endpoints
        @app.get("/api/v1/health")
        async def health_check():
            return {"status": "healthy", "service": "aico-api-gateway"}
        
        @app.get("/api/v1/gateway/status")
        async def gateway_status():
            return {
                "status": "healthy",
                "service": "aico-api-gateway",
                "adapters": ["rest", "websocket", "zeromq"],
                "version": "1.0.0"
            }
        
        @app.get("/api/v1/gateway/metrics")
        async def gateway_metrics():
            return {
                "requests_processed": getattr(self, '_requests_processed', 0),
                "active_connections": getattr(self, '_active_connections', 0),
                "uptime": getattr(self, '_uptime', 0)
            }
        
        # Configure plugins to set up their middleware on the main app
        self.gateway_core.configure_fastapi_app(app)
        
        self.logger.info("Main FastAPI app configured with API Gateway middleware and infrastructure")
    
    @property
    def auth_manager(self):
        """Get authentication manager for main.py integration"""
        return self.gateway_core.auth_manager
    
    @property
    def authz_manager(self):
        """Get authorization manager for main.py integration"""
        return self.gateway_core.authz_manager
    
    @property
    def message_router(self):
        """Get message router for main.py integration"""
        return self.gateway_core.message_router


# Backward compatibility alias
AICOAPIGateway = AICOAPIGatewayV2
