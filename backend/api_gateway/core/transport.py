"""
Adaptive Transport Layer for AICO API Gateway

Implements platform-independent transport negotiation with automatic fallback:
- ZeroMQ IPC (optimal performance)
- WebSocket (real-time fallback)
- REST (universal fallback)
"""

import asyncio
import platform
import socket
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import sys
from pathlib import Path

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.logging import get_logger


class TransportType(Enum):
    """Available transport types"""
    ZEROMQ_IPC = "zeromq_ipc"
    WEBSOCKET = "websocket"
    REST = "rest"
    GRPC = "grpc"


@dataclass
class TransportCapability:
    """Transport capability information"""
    transport_type: TransportType
    available: bool
    endpoint: str
    metadata: Dict[str, Any]


class AdaptiveTransport:
    """
    Adaptive transport layer with automatic fallback
    
    Negotiates the best available transport for each client based on:
    - Platform capabilities
    - Client preferences
    - Network conditions
    - Performance requirements
    """
    
    def __init__(self, transport_config: Dict[str, Any]):
        self.logger = get_logger("api_gateway.transport")
        self.config = transport_config
        
        # Transport priority order
        self.priority = transport_config.get("priority", ["zeromq_ipc", "websocket", "rest"])
        self.negotiation_timeout = transport_config.get("negotiation_timeout", 5)
        self.auto_fallback = transport_config.get("auto_fallback", True)
        
        # Platform detection
        self.platform = platform.system().lower()
        self.is_windows = self.platform == "windows"
        self.is_unix = self.platform in ["linux", "darwin"]
        
        # Transport availability cache
        self.transport_cache: Dict[str, TransportCapability] = {}
        
        self.logger.info("Adaptive transport initialized", extra={
            "platform": self.platform,
            "priority": self.priority,
            "auto_fallback": self.auto_fallback
        })
    
    async def negotiate_transport(self, client_capabilities: Dict[str, Any], 
                                 protocol_configs: Dict[str, Any]) -> Optional[TransportCapability]:
        """
        Negotiate best transport for client
        
        Args:
            client_capabilities: Client's supported transports and preferences
            protocol_configs: Available protocol configurations
            
        Returns:
            Best available transport capability or None
        """
        try:
            # Get available transports
            available_transports = await self._get_available_transports(protocol_configs)
            
            # Filter by client capabilities
            compatible_transports = self._filter_compatible_transports(
                available_transports, 
                client_capabilities
            )
            
            # Select best transport based on priority
            best_transport = self._select_best_transport(compatible_transports)
            
            if best_transport:
                self.logger.debug(f"Transport negotiated: {best_transport.transport_type.value}", extra={
                    "endpoint": best_transport.endpoint,
                    "client_id": client_capabilities.get("client_id", "unknown")
                })
            else:
                self.logger.warning("No compatible transport found", extra={
                    "client_capabilities": client_capabilities,
                    "available_transports": [t.transport_type.value for t in available_transports]
                })
            
            return best_transport
            
        except Exception as e:
            self.logger.error(f"Transport negotiation error: {e}")
            return None
    
    async def _get_available_transports(self, protocol_configs: Dict[str, Any]) -> List[TransportCapability]:
        """Get list of available transports"""
        transports = []
        
        # ZeroMQ IPC
        if protocol_configs.get("zeromq_ipc", {}).get("enabled", False):
            ipc_capability = await self._check_zeromq_ipc(protocol_configs["zeromq_ipc"])
            if ipc_capability:
                transports.append(ipc_capability)
        
        # WebSocket
        if protocol_configs.get("websocket", {}).get("enabled", False):
            ws_capability = await self._check_websocket(protocol_configs["websocket"])
            if ws_capability:
                transports.append(ws_capability)
        
        # REST
        if protocol_configs.get("rest", {}).get("enabled", False):
            rest_capability = await self._check_rest(protocol_configs["rest"])
            if rest_capability:
                transports.append(rest_capability)
        
        # gRPC
        if protocol_configs.get("grpc", {}).get("enabled", False):
            grpc_capability = await self._check_grpc(protocol_configs["grpc"])
            if grpc_capability:
                transports.append(grpc_capability)
        
        return transports
    
    async def _check_zeromq_ipc(self, config: Dict[str, Any]) -> Optional[TransportCapability]:
        """Check ZeroMQ IPC availability"""
        try:
            # Platform-specific IPC paths
            if self.is_windows:
                endpoint = config.get("windows_pipe", "\\\\.\\pipe\\aico_gateway")
                # Test named pipe availability
                available = await self._test_windows_pipe(endpoint)
            else:
                endpoint = config.get("unix_socket", "/tmp/aico_gateway.sock")
                # Test Unix socket availability
                available = await self._test_unix_socket(endpoint)
            
            if not available and self.auto_fallback:
                # Fallback to TCP
                fallback_port = config.get("fallback_tcp_port", 8082)
                endpoint = f"tcp://127.0.0.1:{fallback_port}"
                available = await self._test_tcp_port("127.0.0.1", fallback_port)
            
            return TransportCapability(
                transport_type=TransportType.ZEROMQ_IPC,
                available=available,
                endpoint=endpoint,
                metadata={
                    "platform": self.platform,
                    "ipc_type": "named_pipe" if self.is_windows else "unix_socket",
                    "fallback_used": "tcp" if endpoint.startswith("tcp://") else None
                }
            )
            
        except Exception as e:
            self.logger.error(f"ZeroMQ IPC check failed: {e}")
            return None
    
    async def _check_websocket(self, config: Dict[str, Any]) -> Optional[TransportCapability]:
        """Check WebSocket availability"""
        try:
            port = config.get("port", 8081)
            path = config.get("path", "/ws")
            endpoint = f"ws://127.0.0.1:{port}{path}"
            
            # Test WebSocket port availability
            available = await self._test_tcp_port("127.0.0.1", port)
            
            return TransportCapability(
                transport_type=TransportType.WEBSOCKET,
                available=available,
                endpoint=endpoint,
                metadata={
                    "port": port,
                    "path": path,
                    "heartbeat_interval": config.get("heartbeat_interval", 30)
                }
            )
            
        except Exception as e:
            self.logger.error(f"WebSocket check failed: {e}")
            return None
    
    async def _check_rest(self, config: Dict[str, Any]) -> Optional[TransportCapability]:
        """Check REST availability"""
        try:
            port = config.get("port", 8771)
            prefix = config.get("prefix", "/api/v1")
            endpoint = f"http://127.0.0.1:{port}{prefix}"
            
            # Test REST port availability
            available = await self._test_tcp_port("127.0.0.1", port)
            
            return TransportCapability(
                transport_type=TransportType.REST,
                available=available,
                endpoint=endpoint,
                metadata={
                    "port": port,
                    "prefix": prefix,
                    "cors_enabled": config.get("cors", {}).get("enabled", False)
                }
            )
            
        except Exception as e:
            self.logger.error(f"REST check failed: {e}")
            return None
    
    async def _check_grpc(self, config: Dict[str, Any]) -> Optional[TransportCapability]:
        """Check gRPC availability"""
        try:
            port = config.get("port", 8083)
            endpoint = f"grpc://127.0.0.1:{port}"
            
            # Test gRPC port availability
            available = await self._test_tcp_port("127.0.0.1", port)
            
            return TransportCapability(
                transport_type=TransportType.GRPC,
                available=available,
                endpoint=endpoint,
                metadata={
                    "port": port,
                    "reflection": config.get("reflection", True)
                }
            )
            
        except Exception as e:
            self.logger.error(f"gRPC check failed: {e}")
            return None
    
    async def _test_windows_pipe(self, pipe_name: str) -> bool:
        """Test Windows named pipe availability"""
        try:
            import win32pipe
            import win32file
            
            # Try to connect to existing pipe or check if we can create one
            try:
                handle = win32file.CreateFile(
                    pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0, None,
                    win32file.OPEN_EXISTING,
                    0, None
                )
                win32file.CloseHandle(handle)
                return True
            except:
                # Pipe doesn't exist, check if we can create one
                return True  # Assume we can create it
                
        except ImportError:
            # pywin32 not available, fallback to TCP
            return False
        except Exception:
            return False
    
    async def _test_unix_socket(self, socket_path: str) -> bool:
        """Test Unix socket availability"""
        try:
            import os
            
            # Check if socket file exists and is accessible
            if os.path.exists(socket_path):
                # Try to connect to existing socket
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    sock.connect(socket_path)
                    sock.close()
                    return True
                except:
                    # Socket file exists but not connectable, remove it
                    os.unlink(socket_path)
            
            # Check if we can create socket in the directory
            socket_dir = os.path.dirname(socket_path)
            return os.access(socket_dir, os.W_OK)
            
        except Exception:
            return False
    
    async def _test_tcp_port(self, host: str, port: int) -> bool:
        """Test TCP port availability"""
        try:
            # Try to bind to the port to check availability
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                sock.close()
                return True
            except OSError:
                # Port is in use or not accessible
                sock.close()
                return False
                
        except Exception:
            return False
    
    def _filter_compatible_transports(self, available_transports: List[TransportCapability],
                                    client_capabilities: Dict[str, Any]) -> List[TransportCapability]:
        """Filter transports compatible with client"""
        client_transports = set(client_capabilities.get("supported_transports", []))
        
        # If client doesn't specify, assume all are supported
        if not client_transports:
            return [t for t in available_transports if t.available]
        
        compatible = []
        for transport in available_transports:
            if transport.available and transport.transport_type.value in client_transports:
                compatible.append(transport)
        
        return compatible
    
    def _select_best_transport(self, compatible_transports: List[TransportCapability]) -> Optional[TransportCapability]:
        """Select best transport based on priority"""
        if not compatible_transports:
            return None
        
        # Sort by priority order
        for transport_name in self.priority:
            for transport in compatible_transports:
                if transport.transport_type.value == transport_name:
                    return transport
        
        # If no priority match, return first available
        return compatible_transports[0]
    
    def get_transport_info(self, transport_type: TransportType) -> Optional[Dict[str, Any]]:
        """Get information about a transport type"""
        capability = self.transport_cache.get(transport_type.value)
        if capability:
            return {
                "type": capability.transport_type.value,
                "available": capability.available,
                "endpoint": capability.endpoint,
                "metadata": capability.metadata
            }
        return None
