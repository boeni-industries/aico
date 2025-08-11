"""
WebSocket Adapter for AICO API Gateway

Real-time bidirectional communication with:
- Connection management
- Heartbeat/keepalive
- Message framing
- Authentication
- Subscription management
"""

import asyncio
import json
import websockets
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
import sys
from pathlib import Path

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.logging import get_logger
from aico.core.bus import AICOMessage, MessageMetadata, MessagePriority

from ..core.auth import AuthenticationManager, AuthorizationManager
from ..core.message_router import MessageRouter
from ..middleware.rate_limiter import RateLimiter
from ..middleware.validator import MessageValidator


@dataclass
class WebSocketConnection:
    """WebSocket connection state"""
    websocket: websockets.WebSocketServerProtocol
    client_id: str
    user: Optional[Any] = None
    subscriptions: Set[str] = None
    last_heartbeat: float = 0
    authenticated: bool = False
    
    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = set()


class WebSocketAdapter:
    """
    WebSocket adapter for real-time communication
    
    Provides:
    - Bidirectional real-time messaging
    - Connection lifecycle management
    - Heartbeat/keepalive mechanism
    - Topic subscriptions
    - Authentication and authorization
    """
    
    def __init__(self, config: Dict[str, Any], auth_manager: AuthenticationManager,
                 authz_manager: AuthorizationManager, message_router: MessageRouter,
                 rate_limiter: RateLimiter, validator: MessageValidator):
        
        self.logger = get_logger("api_gateway.websocket")
        self.config = config
        self.auth_manager = auth_manager
        self.authz_manager = authz_manager
        self.message_router = message_router
        self.rate_limiter = rate_limiter
        self.validator = validator
        
        # Connection management
        self.connections: Dict[str, WebSocketConnection] = {}
        self.server = None
        
        # Configuration
        self.port = config.get("port", 8081)
        self.path = config.get("path", "/ws")
        self.heartbeat_interval = config.get("heartbeat_interval", 30)
        self.max_connections = config.get("max_connections", 1000)
        
        # Heartbeat task
        self.heartbeat_task = None
        
        self.logger.info("WebSocket adapter initialized", extra={
            "port": self.port,
            "path": self.path,
            "heartbeat_interval": self.heartbeat_interval
        })
    
    async def start(self, host: str):
        """Start WebSocket server"""
        try:
            # Start WebSocket server
            self.server = await websockets.serve(
                self._handle_connection,
                host,
                self.port,
                path=self.path,
                max_size=10 * 1024 * 1024,  # 10MB max message size
                max_queue=100,  # Max queued messages per connection
                compression=None,  # Disable compression for lower latency
                ping_interval=self.heartbeat_interval,
                ping_timeout=self.heartbeat_interval * 2
            )
            
            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            self.logger.info(f"WebSocket adapter started on {host}:{self.port}{self.path}")
            
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket adapter: {e}")
            raise
    
    async def stop(self):
        """Stop WebSocket server"""
        try:
            # Stop heartbeat task
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # Close all connections
            for connection in list(self.connections.values()):
                await self._close_connection(connection, "Server shutdown")
            
            # Stop server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.logger.info("WebSocket adapter stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping WebSocket adapter: {e}")
    
    async def _handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        try:
            # Check connection limits
            if len(self.connections) >= self.max_connections:
                await websocket.close(code=1013, reason="Server overloaded")
                return
            
            # Create connection object
            connection = WebSocketConnection(
                websocket=websocket,
                client_id=client_id,
                last_heartbeat=asyncio.get_event_loop().time()
            )
            
            self.connections[client_id] = connection
            
            self.logger.info(f"WebSocket connection established: {client_id}")
            
            # Send welcome message
            await self._send_message(connection, {
                "type": "welcome",
                "client_id": client_id,
                "server": "aico-api-gateway",
                "version": "1.0.0"
            })
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(connection, message)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.debug(f"WebSocket connection closed: {client_id}")
        except Exception as e:
            self.logger.error(f"WebSocket connection error for {client_id}: {e}")
        finally:
            # Clean up connection
            if client_id in self.connections:
                await self._close_connection(self.connections[client_id], "Connection ended")
    
    async def _handle_message(self, connection: WebSocketConnection, raw_message: str):
        """Handle incoming WebSocket message"""
        try:
            # Parse JSON message
            try:
                message_data = json.loads(raw_message)
            except json.JSONDecodeError as e:
                await self._send_error(connection, "Invalid JSON", str(e))
                return
            
            # Extract message type
            message_type = message_data.get("type")
            if not message_type:
                await self._send_error(connection, "Missing message type")
                return
            
            # Handle different message types
            if message_type == "auth":
                await self._handle_auth_message(connection, message_data)
            elif message_type == "subscribe":
                await self._handle_subscribe_message(connection, message_data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe_message(connection, message_data)
            elif message_type == "request":
                await self._handle_request_message(connection, message_data)
            elif message_type == "heartbeat":
                await self._handle_heartbeat_message(connection, message_data)
            else:
                await self._send_error(connection, f"Unknown message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
            await self._send_error(connection, "Internal server error", str(e))
    
    async def _handle_auth_message(self, connection: WebSocketConnection, message_data: Dict[str, Any]):
        """Handle authentication message"""
        try:
            # Extract client info
            client_info = {
                "client_id": connection.client_id,
                "protocol": "websocket",
                "headers": {},  # WebSocket headers not easily accessible
                "cookies": {},
                "user_agent": "",
                "remote_addr": connection.websocket.remote_address[0]
            }
            
            # Add auth token to headers if provided
            token = message_data.get("token")
            if token:
                client_info["headers"]["authorization"] = f"Bearer {token}"
            
            # Authenticate
            auth_result = await self.auth_manager.authenticate(message_data, client_info)
            
            if auth_result.success:
                connection.user = auth_result.user
                connection.authenticated = True
                
                await self._send_message(connection, {
                    "type": "auth_success",
                    "user_id": auth_result.user.user_id,
                    "roles": auth_result.user.roles
                })
                
                self.logger.info(f"WebSocket authentication successful: {connection.client_id}")
            else:
                await self._send_error(connection, "Authentication failed", auth_result.error)
                
        except Exception as e:
            await self._send_error(connection, "Authentication error", str(e))
    
    async def _handle_subscribe_message(self, connection: WebSocketConnection, message_data: Dict[str, Any]):
        """Handle topic subscription"""
        try:
            if not connection.authenticated:
                await self._send_error(connection, "Authentication required for subscriptions")
                return
            
            topic = message_data.get("topic")
            if not topic:
                await self._send_error(connection, "Missing topic for subscription")
                return
            
            # Check authorization for topic
            authz_result = await self.authz_manager.authorize(
                connection.user,
                f"subscribe.{topic}",
                None
            )
            
            if not authz_result.success:
                await self._send_error(connection, "Subscription not authorized", authz_result.error)
                return
            
            # Add subscription
            connection.subscriptions.add(topic)
            
            await self._send_message(connection, {
                "type": "subscribed",
                "topic": topic
            })
            
            self.logger.debug(f"WebSocket subscribed to topic: {topic} by {connection.client_id}")
            
        except Exception as e:
            await self._send_error(connection, "Subscription error", str(e))
    
    async def _handle_unsubscribe_message(self, connection: WebSocketConnection, message_data: Dict[str, Any]):
        """Handle topic unsubscription"""
        try:
            topic = message_data.get("topic")
            if not topic:
                await self._send_error(connection, "Missing topic for unsubscription")
                return
            
            # Remove subscription
            connection.subscriptions.discard(topic)
            
            await self._send_message(connection, {
                "type": "unsubscribed",
                "topic": topic
            })
            
            self.logger.debug(f"WebSocket unsubscribed from topic: {topic} by {connection.client_id}")
            
        except Exception as e:
            await self._send_error(connection, "Unsubscription error", str(e))
    
    async def _handle_request_message(self, connection: WebSocketConnection, message_data: Dict[str, Any]):
        """Handle API request message"""
        try:
            if not connection.authenticated:
                await self._send_error(connection, "Authentication required for requests")
                return
            
            # Check rate limits
            await self.rate_limiter.check_rate_limit(connection.client_id)
            
            # Extract request data
            request_id = message_data.get("id")
            message_type = message_data.get("message_type")
            payload = message_data.get("payload", {})
            
            if not message_type:
                await self._send_error(connection, "Missing message_type for request")
                return
            
            # Create AICO message
            import uuid
            from datetime import datetime
            
            aico_message = AICOMessage(
                metadata=MessageMetadata(
                    message_id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    source="websocket_api",
                    message_type=message_type,
                    version="1.0",
                    priority=MessagePriority.NORMAL
                ),
                payload=payload
            )
            
            # Validate message
            validated_message = await self.validator.validate_and_convert(aico_message)
            
            # Authorize request
            authz_result = await self.authz_manager.authorize(
                connection.user,
                message_type,
                validated_message
            )
            if not authz_result.success:
                await self._send_error(connection, "Request not authorized", authz_result.error)
                return
            
            # Route message
            routing_result = await self.message_router.route_message(validated_message)
            
            # Send response
            response_data = {
                "type": "response",
                "id": request_id,
                "success": routing_result.success,
                "correlation_id": routing_result.correlation_id
            }
            
            if routing_result.success:
                response_data["data"] = routing_result.response
            else:
                response_data["error"] = routing_result.error
            
            await self._send_message(connection, response_data)
            
        except Exception as e:
            await self._send_error(connection, "Request error", str(e))
    
    async def _handle_heartbeat_message(self, connection: WebSocketConnection, message_data: Dict[str, Any]):
        """Handle heartbeat/ping message"""
        connection.last_heartbeat = asyncio.get_event_loop().time()
        
        await self._send_message(connection, {
            "type": "heartbeat_ack",
            "timestamp": connection.last_heartbeat
        })
    
    async def _send_message(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """Send message to WebSocket connection"""
        try:
            message_json = json.dumps(message)
            await connection.websocket.send(message_json)
        except websockets.exceptions.ConnectionClosed:
            # Connection already closed
            pass
        except Exception as e:
            self.logger.error(f"Error sending WebSocket message: {e}")
    
    async def _send_error(self, connection: WebSocketConnection, error: str, detail: str = None):
        """Send error message to WebSocket connection"""
        error_message = {
            "type": "error",
            "error": error
        }
        if detail:
            error_message["detail"] = detail
        
        await self._send_message(connection, error_message)
    
    async def _close_connection(self, connection: WebSocketConnection, reason: str = "Unknown"):
        """Close WebSocket connection"""
        try:
            if connection.client_id in self.connections:
                del self.connections[connection.client_id]
            
            if not connection.websocket.closed:
                await connection.websocket.close(code=1000, reason=reason)
            
            self.logger.debug(f"WebSocket connection closed: {connection.client_id} - {reason}")
            
        except Exception as e:
            self.logger.error(f"Error closing WebSocket connection: {e}")
    
    async def _heartbeat_loop(self):
        """Heartbeat loop to check connection health"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                current_time = asyncio.get_event_loop().time()
                timeout_threshold = current_time - (self.heartbeat_interval * 3)
                
                # Check for stale connections
                stale_connections = []
                for connection in self.connections.values():
                    if connection.last_heartbeat < timeout_threshold:
                        stale_connections.append(connection)
                
                # Close stale connections
                for connection in stale_connections:
                    await self._close_connection(connection, "Heartbeat timeout")
                
                if stale_connections:
                    self.logger.info(f"Closed {len(stale_connections)} stale WebSocket connections")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat loop error: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        authenticated_count = sum(1 for conn in self.connections.values() if conn.authenticated)
        
        return {
            "total_connections": len(self.connections),
            "authenticated_connections": authenticated_count,
            "max_connections": self.max_connections,
            "heartbeat_interval": self.heartbeat_interval
        }
    
    async def broadcast_to_subscribers(self, topic: str, message: Dict[str, Any]):
        """Broadcast message to all subscribers of a topic"""
        subscribers = [
            conn for conn in self.connections.values()
            if topic in conn.subscriptions and conn.authenticated
        ]
        
        if subscribers:
            broadcast_message = {
                "type": "broadcast",
                "topic": topic,
                "data": message
            }
            
            # Send to all subscribers
            for connection in subscribers:
                await self._send_message(connection, broadcast_message)
            
            self.logger.debug(f"Broadcasted to {len(subscribers)} subscribers on topic: {topic}")
