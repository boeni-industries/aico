"""
API client utilities for CLI commands.

Provides encrypted HTTP client configuration and error handling for AICO CLI commands.
Uses the same transport security patterns as backend-modelservice communication.
"""

import httpx
import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Dict, Any, Optional, Generator

from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager
from aico.security.transport import TransportIdentityManager, SecureTransportChannel
from aico.security.exceptions import EncryptionError


class CLIModelServiceClient:
    """Encrypted HTTP client for CLI-modelservice communication."""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.config_manager.initialize()
        
        # Get API Gateway configuration (handshake endpoint is on gateway, not modelservice)
        gateway_config = self.config_manager.get("core.api_gateway", {})
        rest_config = gateway_config.get("rest", {})
        host = rest_config.get("host", "127.0.0.1")
        port = rest_config.get("port", 8771)
        self.base_url = f"http://{host}:{port}"
        
        # Initialize encryption
        self.key_manager = AICOKeyManager(self.config_manager)
        self.identity_manager = TransportIdentityManager(self.key_manager)
        self.secure_channel: Optional[SecureTransportChannel] = None
        self.session_established = False
        
        self._initialize_secure_channel()
    
    def _initialize_secure_channel(self):
        """Initialize secure transport channel for CLI component."""
        try:
            self.secure_channel = self.identity_manager.create_secure_channel("cli")
        except Exception as e:
            raise EncryptionError(f"Failed to initialize secure channel for modelservice: {e}") from e
    
    async def _ensure_session(self):
        """Ensure encrypted session is established with modelservice."""
        if self.session_established and self.secure_channel.is_session_valid():
            return
        
        try:
            # Perform handshake with modelservice
            handshake_request = self.secure_channel.create_handshake_request()
            
            # Wrap handshake request in expected format
            handshake_payload = {
                "handshake_request": handshake_request
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/handshake",
                    json=handshake_payload
                )
                
                if response.status_code != 200:
                    raise EncryptionError(f"Modelservice handshake failed: HTTP {response.status_code} - {response.text}")
                
                response_data = response.json()
                
                # Extract handshake response from API Gateway wrapper
                if response_data.get("status") == "session_established":
                    handshake_response = response_data.get("handshake_response", {})
                    success = self.secure_channel.process_handshake_response(handshake_response)
                else:
                    raise EncryptionError(f"Handshake failed: {response_data.get('error', 'Unknown error')}")
                
                if not success:
                    raise EncryptionError("Modelservice handshake response processing failed")
                
                self.session_established = True
                
        except httpx.RequestError as e:
            raise EncryptionError(f"Network error during modelservice handshake: {e}") from e
    
    async def request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make encrypted HTTP request to modelservice."""
        await self._ensure_session()
        
        if not self.secure_channel:
            raise EncryptionError("No secure channel available for modelservice communication")
        
        url = f"{self.base_url}/api/v1{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Create client_id from identity key
                identity = self.identity_manager.get_component_identity("cli")
                client_id = bytes(identity.verify_key).hex()[:16]
                
                # Prepare headers
                headers = {
                    "X-Client-ID": client_id,
                    "Content-Type": "application/json"
                }
                
                # Encrypt request payload if provided
                if data:
                    encrypted_payload = self.secure_channel.encrypt_json_payload(data)
                    request_data = {
                        "encrypted": True,
                        "payload": encrypted_payload,
                        "client_id": client_id
                    }
                else:
                    # For GET requests, still need to indicate encryption
                    request_data = {
                        "encrypted": True,
                        "client_id": client_id
                    }
                
                # Make HTTP request
                if method.upper() == "GET":
                    # GET requests can't have JSON body, use query params or headers
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=request_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status_code != 200:
                    raise httpx.HTTPStatusError(
                        f"Modelservice API error: {method} {endpoint} returned HTTP {response.status_code}",
                        request=response.request,
                        response=response
                    )
                
                # Decrypt response
                response_data = response.json()
                if "encrypted_payload" in response_data:
                    return self.secure_channel.decrypt_json_payload(response_data["encrypted_payload"])
                else:
                    raise EncryptionError(f"Received unencrypted response from {endpoint}")
                    
        except httpx.RequestError as e:
            raise EncryptionError(f"Network error during {method} {endpoint}: {e}") from e
    
    def get(self, endpoint: str):
        """Synchronous GET request - returns JSON data directly."""
        return asyncio.run(self.request("GET", endpoint))
    
    def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None):
        """Synchronous POST request - returns JSON data directly.""" 
        return asyncio.run(self.request("POST", endpoint, json))
    
    def delete(self, endpoint: str):
        """Synchronous DELETE request - returns JSON data directly."""
        return asyncio.run(self.request("DELETE", endpoint))


# Global client instance
_cli_modelservice_client: Optional[CLIModelServiceClient] = None


@contextmanager
def get_modelservice_client() -> Generator[CLIModelServiceClient, None, None]:
    """Get encrypted modelservice client for CLI commands."""
    global _cli_modelservice_client
    
    if _cli_modelservice_client is None:
        _cli_modelservice_client = CLIModelServiceClient()
    
    yield _cli_modelservice_client


@contextmanager  
def get_gateway_client() -> Generator[httpx.Client, None, None]:
    """Get configured HTTP client for API Gateway."""
    # Load configuration
    config_manager = ConfigurationManager()
    config_manager.initialize()
    
    # Get gateway configuration
    gateway_config = config_manager.get("api_gateway", {})
    rest_config = gateway_config.get("rest", {})
    host = rest_config.get("host", "127.0.0.1")
    port = rest_config.get("port", 8771)
    
    base_url = f"http://{host}:{port}"
    
    # Create client with reasonable timeouts
    with httpx.Client(
        base_url=base_url,
        timeout=httpx.Timeout(10.0, connect=5.0),
        headers={"User-Agent": "AICO-CLI/1.0"}
    ) as client:
        yield client
