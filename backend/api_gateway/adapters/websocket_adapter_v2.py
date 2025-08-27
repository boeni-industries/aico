"""
WebSocket Protocol Adapter V2 for AICO API Gateway

Refactored WebSocket adapter integrating with the modular plugin architecture.
"""

import asyncio
import json
import websockets
from typing import Dict, Any, Set, Optional
from dataclasses import dataclass
from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from .base import BaseProtocolAdapter
from aico.core.logging import get_logger
from aico.core.version import get_backend_version
from aico.core.bus import MessageBusClient
from aico.core import AicoMessage, MessageMetadata
from aico.security import SessionService


@dataclass
class WebSocketConnection:
    """WebSocket connection state"""
    websocket: websockets.WebSocketServerProtocol
    client_id: str
    user: Optional[Any] = None
    user_uuid: Optional[str] = None
    device_uuid: Optional[str] = None
    session_id: Optional[str] = None
    subscriptions: Set[str] = None
    last_heartbeat: float = 0
    authenticated: bool = False
    
    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = set()


class WebSocketAdapterV2(BaseProtocolAdapter):
    """
    WebSocket protocol adapter for the modular API Gateway
    
    Manages WebSocket connections and integrates with the plugin pipeline
    for unified request processing.
    """
    
    def __init__(self, config: Dict[str, Any], dependencies: Dict[str, Any]):
        super().__init__(config, dependencies)
        self.connections: Dict[str, WebSocketConnection] = {}
        self.server = None
        self.heartbeat_task = None
    
    async def initialize(self, dependencies: Dict[str, Any]) -> None:
        """Initialize WebSocket adapter with dependencies"""
        self.config = dependencies.get('config')
        self.logger = dependencies.get('logger')
        self.gateway = dependencies.get('gateway')
        self.log_consumer = dependencies.get('log_consumer')  # ZMQ log consumer
        
        if not all([self.config, self.logger, self.gateway]):
            raise ValueError("Missing required dependencies: config, logger, gateway")
        
        # WebSocket configuration
        ws_config = self.config.get('protocols', {}).get('websocket', {})
        self.host = ws_config.get('host', '127.0.0.1')
        self.port = ws_config.get('port', 8772)
        self.path = ws_config.get('path', '/ws')
        self.heartbeat_interval = ws_config.get('heartbeat_interval', 30)
        self.max_connections = ws_config.get('max_connections', 1000)
        
        # Get auth managers from gateway
        self.auth_manager = getattr(self.gateway, 'auth_manager', None)
        self.authz_manager = getattr(self.gateway, 'authz_manager', None)
        self.message_router = getattr(self.gateway, 'message_router', None)
        self.rate_limiter = getattr(self.gateway, 'rate_limiter', None)
        self.validator = getattr(self.gateway, 'validator', None)
        
        # Session service for database-backed WebSocket sessions
        self.session_service = self.auth_manager.session_service if self.auth_manager and hasattr(self.auth_manager, 'session_service') else None
        
        # Log consumer integration status
        if self.log_consumer:
            self.logger.info("WebSocket adapter initialized with ZMQ log consumer")
        else:
            self.logger.warning("WebSocket adapter initialized without log consumer")
        
        self.logger.info("WebSocket adapter initialized", extra={
            "host": self.host,
            "port": self.port,
            "path": self.path,
            "heartbeat_interval": self.heartbeat_interval
        })
    
    @property
    def protocol_name(self) -> str:
        return "websocket"
    
    async def start(self) -> None:
        """Start WebSocket server"""
        try:
            # Start WebSocket server
            self.server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port,
                max_size=10 * 1024 * 1024,  # 10MB max message size
                max_queue=100,  # Max queued messages per connection
                compression=None,  # Disable compression for lower latency
                ping_interval=self.heartbeat_interval,
                ping_timeout=self.heartbeat_interval * 2
            )
            
            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            self.running = True
            self.logger.info(f"WebSocket server running on ws://{self.host}:{self.port}{self.path}")
            
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket adapter: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop WebSocket server"""
        try:
            self.running = False
            
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
    
    async def handle_request(self, request_data: Any, client_info: Dict[str, Any]) -> Any:
        """Handle WebSocket message through plugin pipeline"""
        return await self.process_through_plugins(request_data, client_info)
    
    async def _handle_connection(self, websocket):
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
                "version": "2.0"
            })
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(connection, message)
                
        except Exception as e:
            self.logger.error(f"WebSocket connection error for {client_id}: {e}")
        finally:
            # Clean up connection
            if client_id in self.connections:
                await self._close_connection(self.connections[client_id], "Connection ended")
    
    async def _handle_message(self, connection, raw_message: str):
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
            elif message_type == "heartbeat":
                await self._handle_heartbeat_message(connection, message_data)
            else:
                await self._send_error(connection, f"Unknown message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
            await self._send_error(connection, "Internal server error", str(e))
    
    async def _handle_auth_message(self, connection, message_data: Dict[str, Any]):
        """Handle authentication message"""
        try:
            # Extract client info
            client_info = {
                "client_id": connection.client_id,
                "protocol": "websocket",
                "headers": {},
                "cookies": {},
                "user_agent": "",
                "remote_addr": connection.websocket.remote_address[0]
            }
            
            # Add auth token to headers if provided
            token = message_data.get("token")
            device_uuid = message_data.get("device_uuid", "websocket_client")
            
            if token:
                client_info["headers"]["authorization"] = f"Bearer {token}"
            
            # Authenticate if auth manager available
            if self.auth_manager:
                auth_result = await self.auth_manager.authenticate(message_data, client_info)
                
                if auth_result.success:
                    connection.user = auth_result.user
                    connection.user_uuid = auth_result.user.user_uuid
                    connection.device_uuid = device_uuid
                    connection.token = token
                    connection.authenticated = True
                    
                    await self._send_message(connection, {
                        "type": "auth_success",
                        "user_uuid": auth_result.user.user_uuid,
                        "roles": auth_result.user.roles,
                        "session_id": connection.session_id
                    })
                else:
                    await self._send_error(connection, "Authentication failed", auth_result.error)
            else:
                await self._send_error(connection, "Authentication not available")
                
        except Exception as e:
            await self._send_error(connection, "Authentication error", str(e))
    
    async def _handle_heartbeat_message(self, connection, message_data: Dict[str, Any]):
        """Handle heartbeat/ping message"""
        connection.last_heartbeat = asyncio.get_event_loop().time()
        
        await self._send_message(connection, {
            "type": "heartbeat_ack",
            "timestamp": connection.last_heartbeat
        })
    
    async def _send_message(self, connection, message: Dict[str, Any]):
        """Send message to WebSocket connection"""
        try:
            message_json = json.dumps(message)
            await connection.websocket.send(message_json)
        except Exception as e:
            self.logger.error(f"Error sending WebSocket message: {e}")
    
    async def _send_error(self, connection, error: str, detail: str = None):
        """Send error message to WebSocket connection"""
        error_message = {
            "type": "error",
            "error": error
        }
        if detail:
            error_message["detail"] = detail
        
        await self._send_message(connection, error_message)
    
    async def _close_connection(self, connection, reason: str = "Unknown"):
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
    
    async def accept_connection(self, websocket: WebSocket) -> None:
        """Accept and manage a WebSocket connection"""
        try:
            await websocket.accept()
            # Note: This is for FastAPI WebSocket, main server uses websockets library
            
            self.logger.info(f"WebSocket connection accepted: {websocket.client.host}")
            
        except Exception as e:
            self.logger.error(f"Failed to accept WebSocket connection: {e}")
            try:
                await websocket.close()
            except Exception:
                pass
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        authenticated_count = sum(1 for conn in self.connections.values() if conn.authenticated)
        
        return {
            "total_connections": len(self.connections),
            "authenticated_connections": authenticated_count,
            "max_connections": self.max_connections,
            "heartbeat_interval": self.heartbeat_interval
        }
    
    async def _handle_connection(self, websocket: WebSocket) -> None:
        """Handle messages from a WebSocket connection"""
        try:
            while self.running:
                try:
                    # Receive message
                    data = await websocket.receive_text()
                    
                    # Parse JSON message
                    try:
                        message = json.loads(data)
                    except json.JSONDecodeError as e:
                        await self._send_error(websocket, "Invalid JSON format", str(e))
                        continue
                    
                    # Extract client info
                    client_info = self.get_client_info(websocket)
                    
                    # Process through plugin pipeline
                    result = await self.handle_request(message, client_info)
                    
                    # Send response
                    if isinstance(result, dict) and result.get('error'):
                        error = result['error']
                        await self._send_error(
                            websocket,
                            error.get('message', 'Processing error'),
                            error.get('detail')
                        )
                    else:
                        await self._send_response(websocket, result)
                
                except WebSocketDisconnect:
                    break
                except ConnectionClosed:
                    break
                except Exception as e:
                    self.logger.error(f"WebSocket message handling error: {e}")
                    await self._send_error(websocket, "Internal error", str(e))
        
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
        
        finally:
            await self._cleanup_connection(websocket)
    
    async def _send_response(self, websocket: WebSocket, response: Any) -> None:
        """Send response to WebSocket client"""
        try:
            if isinstance(response, dict):
                await websocket.send_text(json.dumps(response))
            else:
                await websocket.send_text(json.dumps({"result": response}))
        except Exception as e:
            self.logger.error(f"Failed to send WebSocket response: {e}")
    
    async def _send_error(self, websocket: WebSocket, message: str, detail: str = None) -> None:
        """Send error response to WebSocket client"""
        try:
            error_response = {
                "error": message,
                "detail": detail
            }
            await websocket.send_text(json.dumps(error_response))
        except Exception as e:
            self.logger.error(f"Failed to send WebSocket error: {e}")
    
    async def _cleanup_connection(self, websocket: WebSocket) -> None:
        """Clean up WebSocket connection resources"""
        try:
            # Remove from active connections
            self.active_connections.discard(websocket)
            
            # Cancel and remove connection task
            if websocket in self.connection_tasks:
                task = self.connection_tasks[websocket]
                if not task.done():
                    task.cancel()
                del self.connection_tasks[websocket]
            
            # Close connection if still open
            try:
                await websocket.close()
            except Exception:
                pass
            
            self.logger.debug(f"WebSocket connection cleaned up")
            
        except Exception as e:
            self.logger.error(f"WebSocket cleanup error: {e}")
    
    def get_client_info(self, websocket: WebSocket) -> Dict[str, Any]:
        """Extract client information from WebSocket"""
        return {
            'client_id': f"ws_{websocket.client.host}_{websocket.client.port}" if websocket.client else 'unknown',
            'protocol': self.protocol_name,
            'remote_addr': websocket.client.host if websocket.client else 'unknown',
            'user_agent': websocket.headers.get('user-agent', 'unknown'),
            'headers': dict(websocket.headers)
        }
    
    async def broadcast_message(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all active connections"""
        if not self.active_connections:
            return
        
        message_text = json.dumps(message)
        disconnected = set()
        
        for websocket in self.active_connections:
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                self.logger.warning(f"Failed to broadcast to connection: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected:
            await self._cleanup_connection(websocket)
    
    async def health_check(self) -> Dict[str, Any]:
        """WebSocket adapter health check"""
        base_health = await super().health_check()
        base_health.update({
            'active_connections': len(self.active_connections),
            'connection_tasks': len(self.connection_tasks)
        })
        return base_health
