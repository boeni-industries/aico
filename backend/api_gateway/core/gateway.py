"""
Core API Gateway Implementation

Main orchestrator for the unified multi-protocol API Gateway following AICO patterns.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.core.bus import AICOMessageBus

# Initialize logger
logger = get_logger("api_gateway", "core")

from .auth import AuthenticationManager, AuthorizationManager
from .transport import AdaptiveTransport
from .message_router import MessageRouter
from ..adapters.rest_adapter import RESTAdapter
from ..adapters.websocket_adapter import WebSocketAdapter
from ..adapters.zeromq_adapter import ZeroMQAdapter
from ..middleware.rate_limiter import RateLimiter
from ..middleware.validator import MessageValidator
from ..middleware.security import SecurityMiddleware


@dataclass
class GatewayConfig:
    """Gateway configuration data class"""
    enabled: bool
    host: str
    protocols: Dict[str, Any]
    admin: Dict[str, Any]
    transport: Dict[str, Any]
    routing: Dict[str, Any]
    security: Dict[str, Any]
    performance: Dict[str, Any]
    monitoring: Dict[str, Any]


class AICOAPIGateway:
    """
    Unified API Gateway for AICO
    
    Provides multi-protocol access to the AICO message bus with:
    - REST, WebSocket, ZeroMQ IPC, and optional gRPC protocols
    - Adaptive transport layer with automatic fallback
    - Zero-trust authentication and authorization
    - Message routing and validation
    - Rate limiting and security enforcement
    - Admin endpoint separation
    """
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        # Logger already initialized at module level
        
        # Configuration
        self.config_manager = config_manager or ConfigurationManager()
        self.config_manager.initialize(lightweight=False)
        self.config = self.config_manager.get("api_gateway", {})
        
        # Check if API Gateway is enabled
        if not self.config.get("enabled", True):
            self.logger.warning("API Gateway is disabled in configuration")
            self.enabled = False
            return
        else:
            self.enabled = True
        
        # Core components
        self.message_bus_client: Optional[MessageBusClient] = None
        self.auth_manager = AuthenticationManager(self.config_manager.get_all())
        self.authz_manager = AuthorizationManager(self.config.get("security", {}))
        self.adaptive_transport = AdaptiveTransport(self.config.get("transport", {}))
        self.message_router = MessageRouter(self.config.get("routing", {}))
        
        # Middleware
        self.rate_limiter = RateLimiter(self.config.get("rate_limiting", {}))
        self.validator = MessageValidator()
        self.security_middleware = SecurityMiddleware(self.config.security)
        
        # Protocol adapters
        self.adapters: Dict[str, Any] = {}
        self.running = False
        
        self.logger.info("API Gateway initialized", extra={
            "protocols": list(self.config.protocols.keys()),
            "admin_enabled": self.config.admin["enabled"]
        })
    
    def _load_config(self) -> GatewayConfig:
        """Load and validate gateway configuration"""
        try:
            # Initialize config manager if needed
            if not hasattr(self.config_manager, '_instance_initialized'):
                self.config_manager.initialize(lightweight=False)
            
            # Load gateway configuration
            gateway_config = self.config_manager.get("api_gateway", {})
            
            if not gateway_config:
                raise ValueError("API Gateway configuration not found")
            
            # Validate configuration against schema
            self.config_manager.validate("api_gateway", {"api_gateway": gateway_config})
            
            return GatewayConfig(
                enabled=gateway_config.get("enabled", True),
                host=gateway_config.get("host", "127.0.0.1"),
                protocols=gateway_config.get("protocols", {}),
                admin=gateway_config.get("admin", {}),
                transport=gateway_config.get("transport", {}),
                routing=gateway_config.get("routing", {}),
                security=gateway_config.get("security", {}),
                performance=gateway_config.get("performance", {}),
                monitoring=gateway_config.get("monitoring", {})
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load gateway configuration: {e}")
            raise
    
    async def start(self, message_bus_address: str = "tcp://localhost:5555"):
        """Start the API Gateway"""
        if not self.config.enabled:
            self.logger.info("API Gateway is disabled in configuration")
            return
        
        try:
            # Connect to message bus
            self.message_bus_client = MessageBusClient(
                "api_gateway", 
                message_bus_address
            )
            await self.message_bus_client.connect()
            self.logger.info(f"Connected to message bus at {message_bus_address}")
            
            # Initialize message router with bus client
            self.message_router.set_message_bus(self.message_bus_client)
            
            # Start protocol adapters
            await self._start_adapters()
            
            # Start admin interface if enabled
            if self.config.admin["enabled"]:
                await self._start_admin_interface()
            self.running = True
            self.logger.info("API Gateway started successfully", extra={
                "adapters": list(self.adapters.keys()),
                "host": self.config.get("host", "127.0.0.1")
            })
            
        except Exception as e:
            self.logger.error(f"Failed to start API Gateway: {e}")
            raise
    
    async def stop(self):
        """Stop the API Gateway"""
        self.running = False
        
        try:
            # Stop all adapters
            for name, adapter in self.adapters.items():
                try:
                    await adapter.stop()
                    self.logger.info(f"Stopped {name} adapter")
                except Exception as e:
                    self.logger.error(f"Error stopping {name} adapter: {e}")
            
            # Disconnect from message bus
            if self.message_bus_client:
                await self.message_bus_client.publish(
                    "system.gateway.stopped",
                    {"timestamp": "now"}
                )
                await self.message_bus_client.disconnect()
                
            self.logger.info("API Gateway stopped")
            
        except Exception as e:
            self.logger.error(f"Error during gateway shutdown: {e}")
    
    async def _start_adapters(self):
        """Start enabled protocol adapters"""
        protocols = self.config.protocols
        
        # REST Adapter
        if protocols.get("rest", {}).get("enabled", False):
            rest_adapter = RESTAdapter(
                config=protocols["rest"],
                auth_manager=self.auth_manager,
                authz_manager=self.authz_manager,
                message_router=self.message_router,
                rate_limiter=self.rate_limiter,
                validator=self.validator,
                security_middleware=self.security_middleware
            )
            await rest_adapter.start(self.config.host)
            self.adapters["rest"] = rest_adapter
            self.logger.info(f"REST adapter started on {self.config.host}:{protocols['rest']['port']}")
        
        # WebSocket Adapter
        if protocols.get("websocket", {}).get("enabled", False):
            ws_adapter = WebSocketAdapter(
                config=protocols["websocket"],
                auth_manager=self.auth_manager,
                authz_manager=self.authz_manager,
                message_router=self.message_router,
                rate_limiter=self.rate_limiter,
                validator=self.validator
            )
            await ws_adapter.start(self.config.host)
            self.adapters["websocket"] = ws_adapter
            self.logger.info(f"WebSocket adapter started on {self.config.host}:{protocols['websocket']['port']}")
        
        # ZeroMQ IPC Adapter
        if protocols.get("zeromq_ipc", {}).get("enabled", False):
            zmq_adapter = ZeroMQAdapter(
                config=protocols["zeromq_ipc"],
                auth_manager=self.auth_manager,
                authz_manager=self.authz_manager,
                message_router=self.message_router,
                adaptive_transport=self.adaptive_transport
            )
            await zmq_adapter.start()
            self.adapters["zeromq_ipc"] = zmq_adapter
            self.logger.info("ZeroMQ IPC adapter started")
        
        # gRPC Adapter (optional)
        if protocols.get("grpc", {}).get("enabled", False):
            try:
                from ..adapters.grpc_adapter import GRPCAdapter
                grpc_adapter = GRPCAdapter(
                    config=protocols["grpc"],
                    auth_manager=self.auth_manager,
                    authz_manager=self.authz_manager,
                    message_router=self.message_router
                )
                await grpc_adapter.start(self.config.host)
                self.adapters["grpc"] = grpc_adapter
                self.logger.info(f"gRPC adapter started on {self.config.host}:{protocols['grpc']['port']}")
            except ImportError:
                self.logger.warning("gRPC adapter requested but gRPC dependencies not available")
    
    async def _start_admin_interface(self):
        """Start admin interface on separate port"""
        from ..admin.endpoints import create_admin_app
        
        admin_config = self.config.admin
        admin_app = create_admin_app(
            auth_manager=self.auth_manager,
            authz_manager=self.authz_manager,
            message_router=self.message_router,
            gateway=self
        )
        
        # Start admin server (implementation depends on chosen framework)
        # This will be implemented in the admin module
        self.logger.info(f"Admin interface started on {admin_config['bind_host']}:{admin_config['port']}")
    
    async def handle_request(self, protocol: str, request_data: Any, client_info: Dict[str, Any]) -> Any:
        """
        Unified request handler for all protocols
        
        This is the main entry point that all protocol adapters use.
        Implements the complete request pipeline with middleware.
        """
        try:
            # 1. Security middleware
            await self.security_middleware.process_request(request_data, client_info)
            
            # 2. Authentication
            auth_result = await self.auth_manager.authenticate(request_data, client_info)
            if not auth_result.success:
                raise AuthenticationError(auth_result.error)
            
            # 3. Rate limiting
            await self.rate_limiter.check_rate_limit(client_info["client_id"])
            
            # 4. Message validation
            message = await self.validator.validate_and_convert(request_data)
            
            # 5. Authorization
            authz_result = await self.authz_manager.authorize(
                auth_result.user, 
                message.metadata.message_type,
                message
            )
            if not authz_result.success:
                raise AuthorizationError(authz_result.error)
            
            # 6. Route to message bus
            response = await self.message_router.route_message(message)
            
            # 7. Return response
            return response
            
        except Exception as e:
            self.logger.error(f"Request handling error: {e}", extra={
                "protocol": protocol,
                "client": client_info.get("client_id", "unknown")
            })
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get gateway health status"""
        return {
            "status": "healthy" if self.running else "stopped",
            "adapters": {
                name: "running" for name in self.adapters.keys()
            },
            "message_bus": "connected" if self.message_bus_client and self.message_bus_client.running else "disconnected",
            "config": {
                "protocols_enabled": [name for name, proto in self.config.protocols.items() if proto.get("enabled")],
                "admin_enabled": self.config.admin["enabled"]
            }
        }


class AuthenticationError(Exception):
    """Authentication failed"""
    pass


class AuthorizationError(Exception):
    """Authorization failed"""
    pass
