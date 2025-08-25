"""
Encryption Middleware for AICO API Gateway

Provides transparent libsodium encryption for HTTP/WebSocket communication
while maintaining JSON API compatibility.
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Send, Scope

from aico.core.logging import get_logger
from aico.security.key_manager import AICOKeyManager
from aico.security.transport import TransportIdentityManager, SecureTransportChannel
from aico.security.exceptions import EncryptionError, DecryptionError


class EncryptionMiddleware:
    """
    Pure ASGI middleware for transparent JSON payload encryption
    
    Handles handshake negotiation and encrypts/decrypts JSON payloads
    while maintaining standard HTTP semantics. Uses pure ASGI to avoid
    BaseHTTPMiddleware Content-Length calculation bugs.
    """
    
    def __init__(self, app: ASGIApp, key_manager: AICOKeyManager):
        self.app = app
        self.key_manager = key_manager
        self.logger = get_logger("api_gateway", "encryption")
        
        # Load transport encryption configuration
        from aico.core.config import ConfigurationManager
        config_manager = ConfigurationManager()
        config_manager.initialize()
        config = config_manager.get("security", {}).get("transport_encryption", {})
        self.config = config
        self.enabled = config.get("enabled", True)
        
        if not self.enabled:
            self.logger.info("Transport encryption disabled in configuration")
            return
        
        # Initialize transport security components
        self.identity_manager = TransportIdentityManager(key_manager)
        # Create secure channel using the identity manager's method
        self.secure_channel = self.identity_manager.create_secure_channel("api_gateway")
        
        # Session management from configuration
        session_config = config.get("session", {})
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = session_config.get("timeout_seconds", 3600)
        self.handshake_timeout = session_config.get("handshake_timeout_seconds", 30)
        self.max_sessions_per_client = session_config.get("max_sessions_per_client", 5)
        
        # Message settings
        message_config = config.get("message", {})
        self.max_payload_size = message_config.get("max_payload_size", 1048576)
        self.compression_enabled = message_config.get("compression_enabled", True)
        self.compression_threshold = message_config.get("compression_threshold", 1024)
        
        # Configuration
        self.require_encryption = True
        self.handshake_path = "/api/v1/handshake"
        
        # Initialize channels dictionary for session management
        self.channels: Dict[str, Any] = {}
        
        self.logger.info("Encryption middleware initialized")
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI middleware entry point"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Skip encryption if disabled
        if not self.enabled:
            await self.app(scope, receive, send)
            return
        
        # Create request object for processing
        request = Request(scope, receive)
        
        # Skip encryption for health checks and handshake endpoint
        if self._should_skip_encryption(request):
            await self.app(scope, receive, send)
            return
        
        # Handle handshake requests
        if request.url.path == self.handshake_path:
            response = await self._handle_handshake(request)
            await response(scope, receive, send)
            return
        
        # Handle encrypted requests
        await self._handle_encrypted_request(scope, receive, send)
    
    async def _handle_encrypted_request(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle encrypted request by decrypting and forwarding"""
        try:
            # Get client channel
            request = Request(scope, receive)
            client_id = self._get_client_id(request)
            channel = self.channels.get(client_id)
            
            if not channel or not channel.is_session_valid():
                if self.require_encryption:
                    response = JSONResponse(
                        status_code=401,
                        content={
                            "error": "Encryption required",
                            "message": "Perform handshake at /api/v1/handshake first"
                        }
                    )
                    await response(scope, receive, send)
                    return
                else:
                    # Allow unencrypted requests - pass through
                    await self.app(scope, receive, send)
                    return
            
            # Read and check if request is encrypted
            body = await request.body()
            if body:
                try:
                    request_data = json.loads(body)
                    if request_data.get("encrypted") and "payload" in request_data:
                        # Use client_id from request if provided, otherwise generate one
                        if "client_id" in request_data:
                            client_id = request_data["client_id"]
                            self.logger.debug(f"Looking for client_id: {client_id}")
                            self.logger.debug(f"Available channels: {list(self.channels.keys())}")
                            channel = self.channels.get(client_id)
                            if not channel or not channel.is_session_valid():
                                self.logger.error(f"Invalid session for client_id: {client_id}, available: {list(self.channels.keys())}")
                                raise DecryptionError("Invalid or expired session for provided client_id")
                        
                        # Decrypt the payload
                        encrypted_payload = request_data["payload"]
                        self.logger.info(f"Attempting to decrypt payload for client_id: {client_id}")
                        self.logger.info(f"Channel session valid: {channel.is_session_valid()}")
                        self.logger.info(f"Encrypted payload length: {len(encrypted_payload)}")
                        
                        try:
                            decrypted_data = channel.decrypt_json_payload(encrypted_payload)
                            self.logger.info(f"Successfully decrypted payload: {decrypted_data}")
                        except Exception as e:
                            self.logger.error(f"Decryption failed with error: {e}")
                            # Let's also check if the channel has the right session info
                            self.logger.error(f"Channel session_established: {getattr(channel, 'session_established', 'N/A')}")
                            self.logger.error(f"Channel session_box exists: {hasattr(channel, 'session_box') and channel.session_box is not None}")
                            raise
                        
                        # Create new receive callable with decrypted data
                        decrypted_body = json.dumps(decrypted_data).encode()
                        
                        async def new_receive():
                            return {
                                "type": "http.request",
                                "body": decrypted_body,
                                "more_body": False
                            }
                        
                        # Forward to app with decrypted body
                        await self.app(scope, new_receive, send)
                        return
                except json.JSONDecodeError:
                    # Not JSON, pass through
                    pass
            
            # Pass through unencrypted requests
            await self.app(scope, receive, send)
            
        except (EncryptionError, DecryptionError) as e:
            self.logger.error(f"Encryption middleware error: {e}")
            response = JSONResponse(
                status_code=400,
                content={"error": "Encryption error", "detail": str(e)}
            )
            await response(scope, receive, send)
        except Exception as e:
            self.logger.error(f"Middleware error: {e}")
            response = JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )
            await response(scope, receive, send)
    
    def _should_skip_encryption(self, request: Request) -> bool:
        """Check if request should skip encryption"""
        skip_paths = [
            "/api/v1/health",
            "/api/v1/gateway/status",
            "/api/v1/gateway/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Use combination of IP and User-Agent for client identification
        # In production, this could be enhanced with client certificates
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "unknown")
        return f"{client_ip}:{hash(user_agent)}"
    
    async def _handle_handshake(self, request: Request) -> Response:
        """Handle encryption handshake"""
        try:
            if request.method != "POST":
                return JSONResponse(
                    status_code=405,
                    content={"error": "Method not allowed"}
                )
            
            # Parse handshake request
            body = await request.body()
            handshake_data = json.loads(body)
            
            # Get or create channel for client
            client_id = self._get_client_id(request)
            
            if "handshake_request" in handshake_data:
                # Initial handshake request
                channel = self.identity_manager.create_secure_channel("backend")
                response_data = channel.process_handshake_request(
                    handshake_data["handshake_request"]
                )
                
                # Store channel with both server-generated and client-provided IDs
                self.channels[client_id] = channel
                
                # Also store with client identity for encrypted requests
                handshake_request = handshake_data["handshake_request"]
                
                # Store with identity_key (Ed25519) if provided - this is what client uses for client_id
                if "identity_key" in handshake_request:
                    import base64
                    identity_key_b64 = handshake_request["identity_key"]
                    identity_key_bytes = base64.b64decode(identity_key_b64)
                    client_verify_key_id = identity_key_bytes.hex()[:16]
                    self.channels[client_verify_key_id] = channel
                    self.logger.info(f"Stored channel with client_verify_key_id: {client_verify_key_id}")
                
                # Fallback: store with public_key if no identity_key (for backward compatibility)
                elif "public_key" in handshake_request:
                    import base64
                    public_key_b64 = handshake_request["public_key"]
                    public_key_bytes = base64.b64decode(public_key_b64)
                    client_verify_key_id = public_key_bytes.hex()[:16]
                    self.channels[client_verify_key_id] = channel
                    self.logger.info(f"Stored channel with client_verify_key_id (fallback): {client_verify_key_id}")
                
                # Also store with component name as fallback
                if "component" in handshake_request:
                    component_id = handshake_request.get("component", "unknown")
                    self.channels[component_id] = channel
                    self.logger.info(f"Stored channel with component_id: {component_id}")
                
                self.logger.info("Handshake initiated", extra={
                    "client_id": client_id,
                    "peer_component": handshake_data["handshake_request"].get("component")
                })
                
                self.logger.info("Handshake completed successfully", extra={
                    "client_id": client_id,
                    "peer_component": handshake_data["handshake_request"].get("component"),
                    "session_status": "established"
                })
                
                return JSONResponse({
                    "handshake_response": response_data,
                    "status": "session_established"
                })
                
            elif "handshake_response" in handshake_data:
                # Handshake response (for client-initiated handshakes)
                channel = self.channels.get(client_id)
                if not channel:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "No active handshake"}
                    )
                
                success = channel.process_handshake_response(
                    handshake_data["handshake_response"]
                )
                
                if success:
                    return JSONResponse({"status": "handshake_complete"})
                else:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Handshake failed"}
                    )
            
            else:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid handshake format"}
                )
                
        except Exception as e:
            self.logger.error(f"Handshake error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Handshake failed", "detail": str(e)}
            )
    
    async def _decrypt_request(self, request: Request, channel: SecureTransportChannel) -> Request:
        """Decrypt request body"""
        try:
            body = await request.body()
            if not body:
                return request
            
            # Check if body is encrypted (base64 encoded)
            try:
                request_data = json.loads(body)
                if "encrypted_payload" in request_data:
                    # Decrypt payload
                    decrypted_data = channel.decrypt_json_payload(
                        request_data["encrypted_payload"]
                    )
                    
                    # Replace request body with decrypted data
                    new_body = json.dumps(decrypted_data).encode()
                    
                    # Create new request with decrypted body
                    scope = request.scope.copy()
                    scope["body"] = new_body
                    
                    # Update content-length header
                    headers = dict(request.headers)
                    headers["content-length"] = str(len(new_body))
                    scope["headers"] = [(k.encode(), v.encode()) for k, v in headers.items()]
                    
                    return Request(scope)
                
            except json.JSONDecodeError:
                # Not JSON, return as-is
                pass
            
            return request
            
        except Exception as e:
            self.logger.error(f"Request decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt request: {e}")
    
    async def _encrypt_response(self, response: Response, channel: SecureTransportChannel) -> Response:
        """Encrypt response body"""
        try:
            # Get response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            if not body:
                return response
            
            # Parse JSON response
            try:
                response_data = json.loads(body)
                
                # Encrypt the response data
                encrypted_payload = channel.encrypt_json_payload(response_data)
                
                # Create encrypted response
                encrypted_response = {
                    "encrypted_payload": encrypted_payload,
                    "encryption": "xchacha20poly1305"
                }
                
                # Create new response
                new_body = json.dumps(encrypted_response).encode()
                
                return Response(
                    content=new_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json"
                )
                
            except json.JSONDecodeError:
                # Not JSON, return as-is
                return response
            
        except Exception as e:
            self.logger.error(f"Response encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt response: {e}")
    
    def _is_json_response(self, response: Response) -> bool:
        """Check if response is JSON"""
        content_type = response.headers.get("content-type", "")
        return "application/json" in content_type
    
    def cleanup_expired_channels(self):
        """Clean up expired channels"""
        expired_clients = [
            client_id for client_id, channel in self.channels.items()
            if not channel.is_session_valid()
        ]
        
        for client_id in expired_clients:
            del self.channels[client_id]
            self.logger.debug(f"Cleaned up expired channel for {client_id}")


class WebSocketEncryptionHandler:
    """
    WebSocket encryption handler for secure real-time communication
    
    Handles WebSocket upgrade with encryption handshake and message encryption.
    """
    
    def __init__(self, key_manager: AICOKeyManager):
        self.key_manager = key_manager
        self.identity_manager = TransportIdentityManager(key_manager)
        self.logger = get_logger("api_gateway", "websocket_encryption")
        
        # Active channels per WebSocket connection
        self.channels: Dict[str, SecureTransportChannel] = {}
    
    async def handle_connection(self, websocket, client_id: str):
        """Handle WebSocket connection with encryption"""
        try:
            # Accept WebSocket connection
            await websocket.accept()
            
            # Perform handshake
            channel = await self._perform_websocket_handshake(websocket, client_id)
            if not channel:
                await websocket.close(code=4000, reason="Handshake failed")
                return
            
            # Store channel
            self.channels[client_id] = channel
            
            self.logger.info("Secure WebSocket connection established", extra={
                "client_id": client_id
            })
            
            # Handle encrypted messages
            await self._handle_encrypted_messages(websocket, channel)
            
        except Exception as e:
            self.logger.error(f"WebSocket encryption error: {e}")
            await websocket.close(code=4001, reason="Encryption error")
        finally:
            # Cleanup
            if client_id in self.channels:
                del self.channels[client_id]
    
    async def _perform_websocket_handshake(self, websocket, client_id: str) -> Optional[SecureTransportChannel]:
        """Perform encryption handshake over WebSocket"""
        try:
            # Create channel
            channel = self.identity_manager.create_secure_channel("backend")
            
            # Wait for handshake request
            handshake_request = await websocket.receive_json()
            
            if "handshake_request" not in handshake_request:
                await websocket.send_json({"error": "Invalid handshake format"})
                return None
            
            # Process handshake
            response_data = channel.process_handshake_request(
                handshake_request["handshake_request"]
            )
            
            # Send response
            await websocket.send_json({
                "handshake_response": response_data,
                "status": "session_established"
            })
            
            return channel
            
        except Exception as e:
            self.logger.error(f"WebSocket handshake failed: {e}")
            return None
    
    async def _handle_encrypted_messages(self, websocket, channel: SecureTransportChannel):
        """Handle encrypted WebSocket messages"""
        try:
            while True:
                # Receive message
                message = await websocket.receive_json()
                
                if "encrypted_payload" in message:
                    # Decrypt message
                    decrypted_data = channel.decrypt_json_payload(
                        message["encrypted_payload"]
                    )
                    
                    # Process decrypted message (this would integrate with message bus)
                    response_data = await self._process_message(decrypted_data)
                    
                    # Encrypt and send response
                    if response_data:
                        encrypted_payload = channel.encrypt_json_payload(response_data)
                        await websocket.send_json({
                            "encrypted_payload": encrypted_payload,
                            "encryption": "xchacha20poly1305"
                        })
                
                else:
                    # Unencrypted message (could be control message)
                    await websocket.send_json({"error": "Encryption required"})
                    
        except Exception as e:
            self.logger.error(f"WebSocket message handling error: {e}")
    
    async def _process_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process decrypted WebSocket message"""
        # This would integrate with the AICO message bus
        # For now, return echo response
        return {
            "type": "response",
            "data": message_data,
            "timestamp": asyncio.get_event_loop().time()
        }
