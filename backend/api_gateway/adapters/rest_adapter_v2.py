"""
REST Protocol Adapter V2 for AICO API Gateway

Refactored REST adapter integrating with the modular plugin architecture.
"""

from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from .base import BaseProtocolAdapter


class RESTAdapterV2(BaseProtocolAdapter):
    """
    REST protocol adapter for the modular API Gateway
    
    Integrates with FastAPI and the plugin pipeline for unified
    request processing across all protocols.
    """
    
    def __init__(self, config: Dict[str, Any], dependencies: Dict[str, Any]):
        super().__init__(config, dependencies)
        self.app: Optional[FastAPI] = None
        self.server = None
    
    @property
    def protocol_name(self) -> str:
        return "rest"
    
    async def initialize(self, dependencies: Dict[str, Any]) -> None:
        """Initialize REST adapter with dependencies"""
        self.config = dependencies.get('config')
        self.logger = dependencies.get('logger')
        self.gateway = dependencies.get('gateway')
        self.log_consumer = dependencies.get('log_consumer')  # ZMQ log consumer
        
        if not all([self.config, self.logger, self.gateway]):
            raise ValueError("Missing required dependencies: config, logger, gateway")
        
        # Don't create separate FastAPI app - will use main app
        self.app = None
        
        # Log consumer integration status
        if self.log_consumer:
            self.logger.info("REST adapter initialized with ZMQ log consumer")
        else:
            self.logger.warning("REST adapter initialized without log consumer")
            
        self.logger.info("REST adapter initialized")
    
    async def start(self) -> None:
        """Start REST adapter (handled by main FastAPI app)"""
        try:
            # REST adapter is integrated with the main FastAPI app
            # No separate server startup needed
            self.running = True
            self.logger.info(f"REST adapter started on {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start REST adapter: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop REST adapter"""
        try:
            self.running = False
            self.logger.info("REST adapter stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop REST adapter: {e}")
    
    def _setup_middleware_on_app(self, app: FastAPI) -> None:
        """Setup FastAPI middleware including encryption on the main app"""
        # Setup encryption middleware if available
        encryption_middleware = self._setup_encryption_middleware()
        if encryption_middleware:
            from ..middleware.encryption import EncryptionMiddleware
            app.add_middleware(EncryptionMiddleware, 
                     key_manager=self.gateway.key_manager)
            print(f"[REST ADAPTER] Added encryption middleware to main app")
            self.logger.info("Added encryption middleware to main app")
        
        # Log current middleware stack for debugging
        middleware_stack = []
        for middleware in app.user_middleware:
            # Try to get the actual middleware name from dispatch function
            if hasattr(middleware, 'kwargs') and 'dispatch' in middleware.kwargs:
                dispatch_func = middleware.kwargs['dispatch']
                if hasattr(dispatch_func, '__self__'):
                    actual_name = dispatch_func.__self__.__class__.__name__
                    middleware_stack.append(f"{middleware.cls.__name__}({actual_name})")
                else:
                    middleware_stack.append(f"{middleware.cls.__name__}(dispatch)")
            else:
                middleware_stack.append(middleware.cls.__name__)
        print(f"[REST ADAPTER] Current middleware stack: {middleware_stack}")
        self.logger.info(f"Current middleware stack: {middleware_stack}")
        
        # Also log what encryption middleware we actually added
        if encryption_middleware:
            print(f"[REST ADAPTER] Encryption middleware type: {type(encryption_middleware).__name__}")
            self.logger.info(f"Encryption middleware type: {type(encryption_middleware).__name__}")
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes_on_app(self, app: FastAPI) -> None:
        """Setup REST routes on the main app"""
        # Handshake endpoint is now handled by encryption middleware
        
        # Mount all API routers
        self._mount_api_routers(app)
    
    def _mount_api_routers(self, app: FastAPI) -> None:
        """Mount all domain API routers with proper prefixes"""
        routers_to_mount = [
            ("api.users.router", "router", "/api/v1/users", ["users"]),
            ("api.health.router", "router", "/api/v1/health", ["health"]),
            ("api.logs.router", "router", "/api/v1/logs", ["logs"]),
            ("api.echo.router", "router", "/api/v1/echo", ["echo"])
        ]
        
        # Mount admin routers separately (has two routers: health_router and router)
        try:
            from api.admin.router import router as admin_router, health_router as admin_health_router
            app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
            app.include_router(admin_health_router, prefix="/api/v1/admin", tags=["admin"])
            self.logger.info("Admin API routers mounted at /api/v1/admin")
        except ImportError as e:
            self.logger.warning(f"Admin API routers not available: {e}")
        except AttributeError as e:
            self.logger.warning(f"Admin router attributes not found: {e}")
        
        # Add gateway health endpoint (separate from domain health router)
        @app.get("/api/v1/gateway/health")
        async def gateway_health_check():
            """API Gateway health check endpoint"""
            return await self.gateway.health_check()
        
        for module_path, router_name, prefix, tags in routers_to_mount:
            try:
                module = __import__(module_path, fromlist=[router_name])
                router = getattr(module, router_name)
                app.include_router(router, prefix=prefix, tags=tags)
                self.logger.info(f"API router mounted: {module_path} at {prefix}")
            except ImportError as e:
                self.logger.warning(f"API router not available: {module_path} - {e}")
            except AttributeError as e:
                self.logger.warning(f"Router attribute not found in {module_path}: {e}")
    
    def setup_routes(self, app: FastAPI) -> None:
        """Setup REST routes on the FastAPI app"""
        self.app = app
        
        # Add middleware
        self._setup_middleware_on_app(app)
        
        # Add routes
        self._setup_routes_on_app(app)
    
    def mount_router(self, router, prefix: str = "", **kwargs):
        """Mount a FastAPI router to the REST adapter app"""
        self.app.include_router(router, prefix=prefix, **kwargs)
        
        @self.app.middleware("http")
        async def gateway_middleware(request: Request, call_next):
            """REST gateway middleware for plugin processing"""
            try:
                # Skip middleware for certain paths
                if request.url.path.startswith('/docs') or request.url.path.startswith('/openapi'):
                    return await call_next(request)
                
                # Extract client info
                client_info = self.get_client_info(request)
                
                # Get request body for processing
                body = await request.body()
                request_data = {
                    'method': request.method,
                    'path': str(request.url.path),
                    'headers': dict(request.headers),
                    'body': body,
                    'query_params': dict(request.query_params)
                }
                
                # Process through plugins if this is an API request
                if request.url.path.startswith('/api/'):
                    try:
                        result = await self.handle_request(request_data, client_info)
                        
                        # Check for errors from plugin processing
                        if isinstance(result, dict) and result.get('error'):
                            error = result['error']
                            return JSONResponse(
                                status_code=error.get('status_code', 500),
                                content={
                                    'error': error.get('message', 'Internal error'),
                                    'detail': error.get('detail')
                                }
                            )
                    except Exception as e:
                        self.logger.error(f"REST middleware error: {e}")
                        return JSONResponse(
                            status_code=500,
                            content={'error': 'Internal server error'}
                        )
                
                # Continue with normal processing
                return await call_next(request)
                
            except Exception as e:
                self.logger.error(f"REST middleware error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={'error': 'Internal server error'}
                )
    
    def _extract_client_info(self, request: Request) -> Dict[str, Any]:
        """Extract client information from FastAPI request"""
        return {
            'ip': request.client.host if request.client else 'unknown',
            'user_agent': request.headers.get('user-agent', 'unknown'),
            'protocol': 'rest',
            'timestamp': request.headers.get('x-timestamp'),
            'headers': dict(request.headers)
        }
    
    async def handle_request(self, request_data: Any, client_info: Dict[str, Any]) -> Any:
        """Handle REST request through plugin pipeline"""
        return await self.process_through_plugins(request_data, client_info)
    
    def _setup_encryption_middleware(self):
        """Setup encryption middleware"""
        # Check if encryption is enabled in config
        security_config = self.gateway.config.get("security", {})
        transport_encryption = security_config.get("transport_encryption", {})
        
        if transport_encryption.get("enabled", False):
            from ..middleware.encryption import EncryptionMiddleware
            return EncryptionMiddleware(
                app=None,  # Will be set by FastAPI
                key_manager=self.gateway.key_manager
            )
        return None

    async def health_check(self) -> Dict[str, Any]:
        """REST adapter health check"""
        base_health = await super().health_check()
        base_health.update({
            'fastapi_app': self.app is not None,
            'routes_setup': hasattr(self, 'app') and self.app is not None
        })
        return base_health
