"""
REST Adapter for AICO API Gateway

Infrastructure-focused FastAPI adapter providing:
- Protocol-level HTTP/REST interface
- CORS middleware
- Security middleware
- Request logging
- Gateway status and metrics endpoints
- Domain router mounting capabilities

Business logic endpoints are handled by domain-specific routers in backend/api/
"""

import asyncio
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, Response, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import sys
from pathlib import Path

# Shared modules now installed via UV editable install

from aico.core.logging import get_logger

# Import version from VERSIONS file
from aico.core.version import get_backend_version
__version__ = get_backend_version()
from aico.core.bus import MessageBusClient
from aico.core import AicoMessage, MessageMetadata
from aico.security.key_manager import AICOKeyManager

from ..models.core.auth import AuthenticationManager, AuthorizationManager
from ..models.core.message_router import MessageRouter
from ..middleware.rate_limiter import RateLimiter
from ..middleware.validator import MessageValidator
from ..middleware.security import SecurityMiddleware
from ..middleware.encryption import EncryptionMiddleware


class RESTAdapter:
    """
    REST API adapter using FastAPI
    
    Provides HTTP/JSON interface to AICO message bus with:
    - RESTful endpoints
    - OpenAPI documentation
    - CORS support
    - Authentication/authorization
    - Rate limiting
    """
    
    def __init__(self, config: Dict[str, Any], auth_manager: AuthenticationManager,
                 authz_manager: AuthorizationManager, message_router: MessageRouter,
                 rate_limiter: RateLimiter, validator: MessageValidator,
                 security_middleware: SecurityMiddleware, key_manager: AICOKeyManager):
        
        self.logger = get_logger("api_gateway", "rest")
        self.config = config
        self.auth_manager = auth_manager
        self.authz_manager = authz_manager
        self.message_router = message_router
        self.rate_limiter = rate_limiter
        self.validator = validator
        self.security_middleware = security_middleware
        self.key_manager = key_manager
        
        # Initialize encryption middleware
        self.encryption_middleware = EncryptionMiddleware(None, key_manager)
        
        # FastAPI app
        self.app = FastAPI(
            title="AICO API Gateway",
            description="Unified API Gateway for AICO AI Companion",
            version=__version__,
            docs_url=f"{config.get('prefix', '/api/v1')}/docs",
            redoc_url=f"{config.get('prefix', '/api/v1')}/redoc"
        )
        
        # Configure CORS
        self._setup_cors()
        
        # Setup routes
        self._setup_routes()
        
        # Setup middleware (including encryption)
        self._setup_middleware()
        
        # Server instance
        self.server = None
        
        self.logger.info("REST adapter initialized", extra={
            "port": config.get("port", 8771),
            "prefix": config.get("prefix", "/api/v1")
        })
    
    def _setup_cors(self):
        """Configure CORS middleware"""
        # CORS is always enabled for Studio React app - following AICO security paradigm
        cors_origins = self.config.get("cors_origins", ["http://localhost:3000", "http://127.0.0.1:3000"])
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"]
        )
    
    def _setup_middleware(self):
        """Setup middleware stack"""
        
        # Add encryption middleware (first in chain for request processing)
        # Using pure ASGI middleware to avoid Content-Length calculation bugs
        self.app.add_middleware(self.encryption_middleware.__class__, key_manager=self.key_manager)
        
        # Add security middleware
        self.app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=self.security_middleware.dispatch
        )
        
        # Add rate limiting middleware
        self.app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=self.rate_limiter.dispatch
        )
        
        @self.app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            """Request logging middleware"""
            import time
            start_time = time.time()
            
            response = await call_next(request)
            
            process_time = time.time() - start_time
            self.logger.info("REST request processed", extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": process_time,
                "client_ip": request.client.host
            })
            
            return response
    
    def _setup_routes(self):
        """Setup API routes"""
        prefix = self.config.get("prefix", "/api/v1")
        
        # Health check
        @self.app.get(f"{prefix}/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "service": "aico-api-gateway"}
        
        # Gateway infrastructure endpoints only
        @self.app.get(f"{prefix}/gateway/status")
        async def gateway_status():
            """Gateway infrastructure status"""
            return {
                "status": "healthy",
                "service": "aico-api-gateway",
                "adapters": ["rest", "websocket", "zeromq"],
                "version": __version__
            }
        
        @self.app.get(f"{prefix}/gateway/metrics")
        async def gateway_metrics():
            """Gateway performance metrics"""
            return {
                "requests_processed": getattr(self, '_requests_processed', 0),
                "active_connections": getattr(self, '_active_connections', 0),
                "uptime": getattr(self, '_uptime', 0)
            }
    
    def mount_router(self, router: APIRouter, prefix: str = "", tags: Optional[list] = None):
        """Mount a domain router to the FastAPI app"""
        self.app.include_router(router, prefix=prefix, tags=tags)
        self.logger.info("Router mounted", extra={
            "prefix": prefix,
            "tags": tags or []
        })
    
    async def start(self, host: str):
        """Initialize REST adapter (no separate server - uses main FastAPI app)"""
        try:
            port = self.config.get("port", 8771)
            
            # REST adapter now integrates with main FastAPI app - no separate server needed
            # The main FastAPI server handles all REST endpoints
            self.logger.info(f"REST adapter initialized for {host}:{port} (using main FastAPI app)")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize REST adapter: {e}")
            raise
    
    async def stop(self):
        """Stop REST adapter (no separate server to stop)"""
        # REST adapter now integrates with main FastAPI app - no separate server to stop
        self.logger.info("REST adapter stopped")
    
    def get_app(self) -> FastAPI:
        """Get FastAPI app instance"""
        return self.app


def create_rest_adapter(config_manager) -> FastAPI:
    """Create and configure REST adapter app"""
    from aico.core.bus import MessageBusBroker
    from aico.security.key_manager import AICOKeyManager
    from ..models.core.auth import AuthenticationManager, AuthorizationManager
    from ..models.core.message_router import MessageRouter
    from ..middleware.rate_limiter import RateLimiter
    from ..middleware.validator import MessageValidator
    from ..middleware.security import SecurityMiddleware
    
    # Get configuration
    config = config_manager.config_cache.get('core', {})
    api_gateway_config = config.get('api_gateway', {})
    
    # Create required components
    key_manager = AICOKeyManager(config_manager)
    auth_manager = AuthenticationManager(config_manager)
    authz_manager = AuthorizationManager(config_manager)
    message_router = MessageRouter(api_gateway_config)
    rate_limiter = RateLimiter(config_manager)
    validator = MessageValidator()
    security_middleware = SecurityMiddleware(config_manager)
    
    # Create REST adapter with all dependencies
    rest_adapter = RESTAdapter(
        config=api_gateway_config,
        auth_manager=auth_manager,
        authz_manager=authz_manager,
        message_router=message_router,
        rate_limiter=rate_limiter,
        validator=validator,
        security_middleware=security_middleware,
        key_manager=key_manager
    )
    
    return rest_adapter.get_app()
