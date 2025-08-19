"""
ZeroMQ IPC Adapter for AICO API Gateway

Platform-independent IPC communication with:
- Unix sockets (Linux/macOS)
- Named pipes (Windows)
- TCP fallback
- High-performance local communication
"""

import asyncio
import json
import platform
import os
from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Shared modules now installed via UV editable install

import zmq
import zmq.asyncio
from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.core import AicoMessage, MessageMetadata

from ..models.core.auth import AuthenticationManager, AuthorizationManager
from ..models.core.message_router import MessageRouter
from ..models.core.transport import AdaptiveTransport


class ZeroMQAdapter:
    """
    ZeroMQ IPC adapter for high-performance local communication
    
    Provides:
    - Platform-specific IPC (Unix sockets/Named pipes)
    - TCP fallback for compatibility
    - Request-reply pattern
    - Authentication for local clients
    - Message routing to internal bus
    """
    
    def __init__(self, config: Dict[str, Any], auth_manager: AuthenticationManager,
                 authz_manager: AuthorizationManager, message_router: MessageRouter,
                 adaptive_transport: AdaptiveTransport):
        
        self.logger = get_logger("api_gateway", "zeromq")
        self.config = config
        self.auth_manager = auth_manager
        self.authz_manager = authz_manager
        self.message_router = message_router
        self.adaptive_transport = adaptive_transport
        
        # Platform detection
        self.platform = platform.system().lower()
        self.is_windows = self.platform == "windows"
        
        # ZeroMQ context and socket
        self.context = zmq.asyncio.Context()
        self.socket = None
        self.endpoint = None
        
        # Configuration
        self.unix_socket = config.get("unix_socket", "/tmp/aico_gateway.sock")
        self.windows_pipe = config.get("windows_pipe", "\\\\.\\pipe\\aico_gateway")
        self.fallback_tcp_port = config.get("fallback_tcp_port", 8082)
        
        # Running state
        self.running = False
        self.message_task = None
        
        self.logger.info("ZeroMQ adapter initialized", extra={
            "platform": self.platform,
            "unix_socket": self.unix_socket,
            "windows_pipe": self.windows_pipe,
            "fallback_port": self.fallback_tcp_port
        })
    
    async def start(self):
        """Start ZeroMQ IPC server"""
        try:
            # Create REP socket for request-reply pattern
            self.socket = self.context.socket(zmq.REP)
            
            # Determine endpoint based on platform
            self.endpoint = await self._determine_endpoint()
            
            # Bind to endpoint
            self.socket.bind(self.endpoint)
            
            self.running = True
            
            # Start message handling loop
            self.message_task = asyncio.create_task(self._message_loop())
            
            self.logger.info(f"ZeroMQ adapter started on {self.endpoint}")
            
        except Exception as e:
            self.logger.error(f"Failed to start ZeroMQ adapter: {e}")
            raise
    
    async def stop(self):
        """Stop ZeroMQ IPC server"""
        try:
            self.running = False
            
            # Cancel message task
            if self.message_task:
                self.message_task.cancel()
                try:
                    await self.message_task
                except asyncio.CancelledError:
                    # Expected during shutdown - this is the correct behavior
                    pass
            
            # Close socket
            if self.socket:
                self.socket.close()
            
            # Clean up IPC files
            await self._cleanup_ipc()
            
            # Terminate context
            self.context.term()
            
            self.logger.info("ZeroMQ adapter stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping ZeroMQ adapter: {e}")
    
    async def _determine_endpoint(self) -> str:
        """Determine best IPC endpoint for platform"""
        if self.is_windows:
            # Try Windows named pipe
            try:
                endpoint = self.windows_pipe
                # Test if we can create the pipe
                test_socket = self.context.socket(zmq.REP)
                test_socket.bind(endpoint)
                test_socket.close()
                return endpoint
            except Exception as e:
                self.logger.warning(f"Named pipe not available: {e}, falling back to TCP")
                return f"tcp://127.0.0.1:{self.fallback_tcp_port}"
        else:
            # Try Unix socket
            try:
                endpoint = f"ipc://{self.unix_socket}"
                
                # Remove existing socket file if present
                if os.path.exists(self.unix_socket):
                    os.unlink(self.unix_socket)
                
                # Test if we can create the socket
                test_socket = self.context.socket(zmq.REP)
                test_socket.bind(endpoint)
                test_socket.close()
                
                # Clean up test socket
                if os.path.exists(self.unix_socket):
                    os.unlink(self.unix_socket)
                
                return endpoint
            except Exception as e:
                self.logger.warning(f"Unix socket not available: {e}, falling back to TCP")
                return f"tcp://127.0.0.1:{self.fallback_tcp_port}"
    
    async def _message_loop(self):
        """Main message processing loop"""
        while self.running:
            try:
                # Wait for request
                raw_message = await self.socket.recv_string()
                
                # Process request
                response = await self._handle_request(raw_message)
                
                # Send response
                await self.socket.send_string(response)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Message loop error: {e}")
                # Send error response
                try:
                    error_response = json.dumps({
                        "success": False,
                        "error": str(e)
                    })
                    await self.socket.send_string(error_response)
                except Exception as e:
                    # Log error response send failure - this indicates network issues
                    self.logger.warning(f"Failed to send error response to client: {e}")
    
    async def _handle_request(self, raw_message: str) -> str:
        """Handle incoming request"""
        try:
            # Parse JSON message
            try:
                request_data = json.loads(raw_message)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid JSON: {e}"
                })
            
            # Extract client info (for local IPC, client is trusted)
            client_info = {
                "client_id": "local_ipc",
                "protocol": "zeromq_ipc",
                "headers": {},
                "cookies": {},
                "user_agent": "zeromq_client",
                "remote_addr": "127.0.0.1"
            }
            
            # Authenticate (local IPC is trusted by default)
            auth_result = await self.auth_manager.authenticate(request_data, client_info)
            if not auth_result.success:
                return json.dumps({
                    "success": False,
                    "error": auth_result.error
                })
            
            # Extract message data
            message_type = request_data.get("message_type")
            payload = request_data.get("payload", {})
            
            if not message_type:
                return json.dumps({
                    "success": False,
                    "error": "Missing message_type"
                })
            
            # Create AICO message
            import uuid
            from datetime import datetime
            
            aico_message = AicoMessage(
                metadata=MessageMetadata(
                    message_id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    source="zeromq_ipc",
                    message_type=message_type,
                    version="1.0",
                    
                ),
                payload=payload
            )
            
            # Authorize request
            authz_result = await self.authz_manager.authorize(
                auth_result.user,
                message_type,
                aico_message
            )
            if not authz_result.success:
                return json.dumps({
                    "success": False,
                    "error": authz_result.error
                })
            
            # Route message
            routing_result = await self.message_router.route_message(aico_message)
            
            # Return response
            response_data = {
                "success": routing_result.success,
                "correlation_id": routing_result.correlation_id
            }
            
            if routing_result.success:
                response_data["data"] = routing_result.response
            else:
                response_data["error"] = routing_result.error
            
            return json.dumps(response_data)
            
        except Exception as e:
            self.logger.error(f"Request handling error: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    async def _cleanup_ipc(self):
        """Clean up IPC resources"""
        if not self.is_windows and self.endpoint and self.endpoint.startswith("ipc://"):
            socket_path = self.endpoint[6:]  # Remove "ipc://" prefix
            try:
                if os.path.exists(socket_path):
                    os.unlink(socket_path)
                    self.logger.debug(f"Cleaned up Unix socket: {socket_path}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up Unix socket: {e}")
    
    def get_endpoint_info(self) -> Dict[str, Any]:
        """Get endpoint information"""
        return {
            "endpoint": self.endpoint,
            "platform": self.platform,
            "transport_type": "named_pipe" if self.is_windows and "pipe" in (self.endpoint or "") else 
                            "unix_socket" if not self.is_windows and "ipc://" in (self.endpoint or "") else 
                            "tcp_fallback",
            "running": self.running
        }
