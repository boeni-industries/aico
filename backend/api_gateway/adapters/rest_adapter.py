"""
REST Adapter for AICO API Gateway

FastAPI-based REST interface with:
- OpenAPI documentation
- CORS support
- Request/response validation
- Authentication middleware
- Error handling
"""

import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import sys
from pathlib import Path

# Shared modules now installed via UV editable install

from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.core import AicoMessage, MessageMetadata

from ..core.auth import AuthenticationManager, AuthorizationManager
from ..core.message_router import MessageRouter
from ..middleware.rate_limiter import RateLimiter
from ..middleware.validator import MessageValidator
from ..middleware.security import SecurityMiddleware


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
                 security_middleware: SecurityMiddleware):
        
        self.logger = get_logger("api_gateway", "rest")
        self.config = config
        self.auth_manager = auth_manager
        self.authz_manager = authz_manager
        self.message_router = message_router
        self.rate_limiter = rate_limiter
        self.validator = validator
        self.security_middleware = security_middleware
        
        # FastAPI app
        self.app = FastAPI(
            title="AICO API Gateway",
            description="Unified API Gateway for AICO AI Companion",
            version="1.0.0",
            docs_url=f"{config.get('prefix', '/api/v1')}/docs",
            redoc_url=f"{config.get('prefix', '/api/v1')}/redoc"
        )
        
        # Configure CORS
        self._setup_cors()
        
        # Setup routes
        self._setup_routes()
        
        # Setup middleware
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
        """Setup custom middleware"""
        
        @self.app.middleware("http")
        async def security_middleware(request: Request, call_next):
            """Security middleware for all requests"""
            try:
                # Extract client info
                client_info = {
                    "client_id": request.client.host,
                    "protocol": "rest",
                    "headers": dict(request.headers),
                    "cookies": dict(request.cookies),
                    "user_agent": request.headers.get("user-agent", ""),
                    "remote_addr": request.client.host
                }
                
                # Apply security middleware
                await self.security_middleware.process_request(request, client_info)
                
                # Continue with request
                response = await call_next(request)
                return response
                
            except Exception as e:
                self.logger.error(f"Security middleware error: {e}")
                return JSONResponse(
                    status_code=403,
                    content={"error": "Security check failed", "detail": str(e)}
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
        
        # Authentication endpoints
        @self.app.post(f"{prefix}/auth/login")
        async def login(credentials: Dict[str, Any]):
            """User login endpoint"""
            # This would integrate with user management system
            # For now, return a demo JWT token
            from ..core.auth import User
            
            user = User(
                user_id=credentials.get("username", "demo_user"),
                username=credentials.get("username", "demo_user"),
                roles=["user"],
                permissions={"conversation.*", "personality.read", "memory.read"},
                metadata={"login_time": "now"}
            )
            
            token = self.auth_manager.create_jwt_token(user)
            return {"access_token": token, "token_type": "bearer"}
        
        # Conversation endpoints
        @self.app.post(f"{prefix}/conversation")
        async def start_conversation(request: Request, message: Dict[str, Any]):
            """Start a new conversation"""
            return await self._handle_api_request(request, "api.conversation.start", message)
        
        @self.app.post(f"{prefix}/conversation/{{conversation_id}}/message")
        async def send_message(request: Request, conversation_id: str, message: Dict[str, Any]):
            """Send message to conversation"""
            message["conversation_id"] = conversation_id
            return await self._handle_api_request(request, "api.conversation.message", message)
        
        # Personality endpoints
        @self.app.get(f"{prefix}/personality")
        async def get_personality(request: Request):
            """Get current personality state"""
            return await self._handle_api_request(request, "api.personality.get", {})
        
        @self.app.put(f"{prefix}/personality")
        async def update_personality(request: Request, personality: Dict[str, Any]):
            """Update personality traits"""
            return await self._handle_api_request(request, "api.personality.update", personality)
        
        # Memory endpoints
        @self.app.get(f"{prefix}/memory/search")
        async def search_memory(request: Request, query: str):
            """Search memory"""
            return await self._handle_api_request(request, "api.memory.search", {"query": query})
        
        # System endpoints
        @self.app.get(f"{prefix}/system/status")
        async def system_status(request: Request):
            """Get system status"""
            return await self._handle_api_request(request, "api.system.status", {})
    
    async def _handle_api_request(self, request: Request, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API request through gateway pipeline"""
        try:
            # Extract client info
            client_info = {
                "client_id": request.client.host,
                "protocol": "rest",
                "headers": dict(request.headers),
                "cookies": dict(request.cookies),
                "user_agent": request.headers.get("user-agent", ""),
                "remote_addr": request.client.host
            }
            
            # Authenticate request
            auth_result = await self.auth_manager.authenticate(payload, client_info)
            if not auth_result.success:
                raise HTTPException(status_code=401, detail=auth_result.error)
            
            # Check rate limits
            await self.rate_limiter.check_rate_limit(client_info["client_id"])
            
            # Create AICO message
            import uuid
            from datetime import datetime
            
            message = AicoMessage(
                metadata=MessageMetadata(
                    message_id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    source="rest_api",
                    message_type=message_type,
                    version="1.0",
                    
                ),
                payload=payload
            )
            
            # Validate message
            validated_message = await self.validator.validate_and_convert(message)
            
            # Authorize request
            authz_result = await self.authz_manager.authorize(
                auth_result.user,
                message_type,
                validated_message
            )
            if not authz_result.success:
                raise HTTPException(status_code=403, detail=authz_result.error)
            
            # Route message
            routing_result = await self.message_router.route_message(validated_message)
            if not routing_result.success:
                raise HTTPException(status_code=500, detail=routing_result.error)
            
            return {
                "success": True,
                "data": routing_result.response,
                "correlation_id": routing_result.correlation_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"API request error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def start(self, host: str):
        """Start REST server"""
        try:
            port = self.config.get("port", 8771)
            
            # Configure uvicorn
            config = uvicorn.Config(
                self.app,
                host=host,
                port=port,
                log_level="info",
                access_log=False  # We handle logging in middleware
            )
            
            self.server = uvicorn.Server(config)
            
            # Start server in background
            await self.server.serve()
            
            self.logger.info(f"REST adapter started on {host}:{port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start REST adapter: {e}")
            raise
    
    async def stop(self):
        """Stop REST server"""
        if self.server:
            self.server.should_exit = True
            await self.server.shutdown()
            self.logger.info("REST adapter stopped")
    
    def get_app(self) -> FastAPI:
        """Get FastAPI app instance"""
        return self.app
