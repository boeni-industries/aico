"""
ZeroMQ Protocol Adapter V2 for AICO API Gateway

Refactored ZeroMQ adapter integrating with the modular plugin architecture.
"""

import asyncio
import json
import os
import zmq
import zmq.asyncio
from typing import Dict, Any, Optional
import platform

from .base import BaseProtocolAdapter


class ZeroMQAdapterV2(BaseProtocolAdapter):
    """
    ZeroMQ protocol adapter for the modular API Gateway
    
    Handles IPC communication using Unix sockets, named pipes, or TCP fallback
    and integrates with the plugin pipeline.
    """
    
    def __init__(self, config: Dict[str, Any], dependencies: Dict[str, Any]):
        super().__init__(config, dependencies)
        self.context: Optional[zmq.asyncio.Context] = None
        self.socket: Optional[zmq.asyncio.Socket] = None
        self.server_task: Optional[asyncio.Task] = None
        
        # Platform-specific configuration
        self.transport_type = self._determine_transport()
        self.bind_address = self._get_bind_address()
    
    @property
    def protocol_name(self) -> str:
        return "zeromq_ipc"
    
    def _determine_transport(self) -> str:
        """Determine the best transport for the platform"""
        system = platform.system().lower()
        if system in ['linux', 'darwin']:
            return 'ipc'
        elif system == 'windows':
            return 'tcp'  # Windows doesn't support Unix sockets reliably
        else:
            return 'tcp'
    
    def _get_bind_address(self) -> str:
        """Get the bind address based on transport type"""
        if self.transport_type == 'ipc':
            socket_path = self.config.get('socket_path', '/tmp/aico_gateway.sock')
            return f"ipc://{socket_path}"
        else:
            host = self.config.get('host', '127.0.0.1')
            port = self.config.get('port', 5555)
            return f"tcp://{host}:{port}"
    
    async def start(self) -> None:
        """Start ZeroMQ IPC server"""
        try:
            # Create REP socket for request-reply pattern
            self.context = zmq.asyncio.Context()
            self.socket = None
            self.endpoint = None
            
            # Running state
            self.running = False
            self.message_task = None
            
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
    
    async def initialize(self, dependencies: Dict[str, Any]) -> None:
        """Initialize ZeroMQ adapter with dependencies"""
        self.config = dependencies.get('config')
        self.logger = dependencies.get('logger')
        self.gateway = dependencies.get('gateway')
        self.log_consumer = dependencies.get('log_consumer')  # ZMQ log consumer
        
        if not all([self.config, self.logger, self.gateway]):
            raise ValueError("Missing required dependencies: config, logger, gateway")
        
        # ZeroMQ configuration
        zmq_config = self.config.get('protocols', {}).get('zeromq_ipc', {})
        self.enabled = zmq_config.get('enabled', True)
        
        if not self.enabled:
            self.logger.info("ZeroMQ IPC adapter disabled by configuration")
            return
        
        # Platform detection
        self.platform = platform.system().lower()
        self.is_windows = self.platform == "windows"
        
        # Platform-specific IPC configuration
        self.unix_socket = zmq_config.get("unix_socket", "/tmp/aico_gateway.sock")
        self.windows_pipe = zmq_config.get("windows_pipe", "\\\\.\\pipe\\aico_gateway")
        self.fallback_port = zmq_config.get('fallback_port', 8773)
        
        # Log consumer integration status
        if self.log_consumer:
            self.logger.info("ZeroMQ adapter initialized with ZMQ log consumer")
        else:
            self.logger.warning("ZeroMQ adapter initialized without log consumer")
        
        self.logger.info("ZeroMQ adapter initialized", extra={
            "unix_socket": self.unix_socket,
            "windows_pipe": self.windows_pipe,
            "fallback_port": self.fallback_port,
            "enabled": self.enabled
        })
    
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
                return f"tcp://127.0.0.1:{self.fallback_port}"
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
                return f"tcp://127.0.0.1:{self.fallback_port}"
    
    async def stop(self) -> None:
        """Stop ZeroMQ IPC server"""
        try:
            self.running = False
            
            # Cancel message task
            if self.message_task:
                self.message_task.cancel()
                try:
                    await self.message_task
                except asyncio.CancelledError:
                    pass
            
            # Close socket
            if self.socket:
                self.socket.close()
            
            # Clean up IPC files
            await self._cleanup_ipc()
            
            # Terminate context
            if self.context:
                self.context.term()
            
            self.logger.info("ZeroMQ adapter stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping ZeroMQ adapter: {e}")
    
    async def _cleanup_ipc(self):
        """Clean up IPC files"""
        try:
            if not self.is_windows and "ipc://" in getattr(self, 'endpoint', ''):
                socket_path = self.endpoint.replace("ipc://", "")
                if os.path.exists(socket_path):
                    os.unlink(socket_path)
                    self.logger.debug(f"Cleaned up IPC socket: {socket_path}")
        except Exception as e:
            self.logger.warning(f"Failed to clean up IPC files: {e}")
    
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
                return f"tcp://127.0.0.1:{self.fallback_port}"
        else:
            # Try Unix socket
            try:
                endpoint = f"ipc://{self.unix_socket}"
                # Clean up any existing socket file
                if os.path.exists(self.unix_socket):
                    os.unlink(self.unix_socket)
                
                # Test socket creation
                test_socket = self.context.socket(zmq.REP)
                test_socket.bind(endpoint)
                test_socket.close()
                
                # Clean up test socket
                if os.path.exists(self.unix_socket):
                    os.unlink(self.unix_socket)
                
                return endpoint
            except Exception as e:
                self.logger.warning(f"Unix socket not available: {e}, falling back to TCP")
                return f"tcp://127.0.0.1:{self.fallback_port}"
    
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
                except Exception:
                    pass
    
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
            
            # Create client info for plugin processing
            client_info = {
                "protocol": "zeromq_ipc",
                "endpoint": self.endpoint,
                "transport": "ipc" if "ipc://" in self.endpoint else "tcp"
            }
            
            # Process through plugin pipeline if available
            if hasattr(self, 'handle_request'):
                response = await self.handle_request(request_data, client_info)
                return json.dumps(response or {"success": True, "message": "processed"})
            else:
                # Basic echo response for testing
                return json.dumps({
                    "success": True,
                    "echo": request_data,
                    "server": "aico-api-gateway-v2"
                })
                
        except Exception as e:
            self.logger.error(f"Request handling error: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get ZeroMQ connection statistics"""
        return {
            "protocol": "zeromq_ipc",
            "endpoint": getattr(self, 'endpoint', 'not_started'),
            "running": self.running,
            "platform": self.platform
        }
    
    async def handle_request(self, request_data: Any, client_info: Dict[str, Any]) -> Any:
        """Handle ZeroMQ request through plugin pipeline"""
        return await self.process_through_plugins(request_data, client_info)
    
    def get_client_info(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract client information from ZeroMQ message"""
        return {
            'client_id': message_data.get('client_id', 'zeromq_client'),
            'protocol': self.protocol_name,
            'remote_addr': 'local_ipc',
            'user_agent': message_data.get('user_agent', 'zeromq_client'),
            'transport': self.transport_type,
            'bind_address': self.bind_address
        }
    
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message through ZeroMQ (client mode)"""
        client_socket = None
        try:
            # Create client socket
            client_socket = self.context.socket(zmq.REQ)
            client_socket.connect(self.bind_address)
            
            # Send message
            message_bytes = json.dumps(message).encode('utf-8')
            await client_socket.send(message_bytes)
            
            # Receive response
            response_bytes = await client_socket.recv()
            response = json.loads(response_bytes.decode('utf-8'))
            
            return response
            
        except Exception as e:
            self.logger.error(f"ZeroMQ client send error: {e}")
            return {
                "error": "Failed to send message",
                "detail": str(e)
            }
        finally:
            if client_socket:
                client_socket.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """ZeroMQ adapter health check"""
        base_health = await super().health_check()
        base_health.update({
            'transport_type': self.transport_type,
            'bind_address': self.bind_address,
            'server_task_running': self.server_task is not None and not self.server_task.done(),
            'socket_connected': self.socket is not None
        })
        return base_health
