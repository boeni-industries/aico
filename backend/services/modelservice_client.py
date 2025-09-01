"""
Encrypted HTTP client for backend-modelservice communication.

Uses the same transport security patterns as frontend-backend communication
with mandatory encryption and proper ZMQ logging integration.
"""

import json
import httpx
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager
from aico.security.transport import TransportIdentityManager, SecureTransportChannel
from aico.security.exceptions import EncryptionError, DecryptionError


@dataclass
class ModelServiceConfig:
    """Configuration for modelservice client."""
    base_url: str
    timeout: float
    encryption_enabled: bool = True


class ModelServiceClient:
    """
    Encrypted HTTP client for modelservice communication.
    
    Provides the same zero-effort encryption as frontend-backend communication
    using existing transport security infrastructure.
    """
    
    def __init__(self, key_manager: AICOKeyManager, config_manager: ConfigurationManager, config: Optional[ModelServiceConfig] = None):
        self.key_manager = key_manager
        self.config_manager = config_manager
        
        # Load configuration from AICO config system
        if config is None:
            modelservice_config = config_manager.get("modelservice", {})
            rest_config = modelservice_config.get("rest", {})
            host = rest_config.get("host", "127.0.0.1")
            port = rest_config.get("port", 8773)
            base_url = f"http://{host}:{port}"
            timeout = modelservice_config.get("timeout", 30.0)
            self.config = ModelServiceConfig(base_url=base_url, timeout=timeout)
        else:
            self.config = config
            
        self.logger = get_logger("backend", "modelservice_client")
        
        # Initialize transport security
        self.identity_manager = TransportIdentityManager(key_manager)
        self.secure_channel: Optional[SecureTransportChannel] = None
        self.session_established = False
        
        if self.config.encryption_enabled:
            self._initialize_secure_channel()
    
    def _initialize_secure_channel(self):
        """Initialize secure transport channel for backend component."""
        try:
            self.secure_channel = self.identity_manager.create_secure_channel("backend")
            self.logger.info(
                "Secure transport channel initialized for modelservice communication",
                extra={"topic": AICOTopics.SECURITY_TRANSPORT_SESSION}
            )
        except Exception as e:
            error_msg = f"Failed to initialize secure channel for modelservice: {e}"
            self.logger.error(
                error_msg,
                extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
            )
            raise EncryptionError(error_msg) from e
    
    async def _ensure_session(self):
        """Ensure encrypted session is established with modelservice."""
        if not self.config.encryption_enabled:
            raise EncryptionError("Encryption is disabled - secure communication required")
        
        if self.session_established and self.secure_channel.is_session_valid():
            return
        
        try:
            # Perform handshake with modelservice
            handshake_request = self.secure_channel.create_handshake_request()
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.config.base_url}/api/v1/handshake",
                    json=handshake_request
                )
                
                if response.status_code != 200:
                    error_msg = f"Modelservice handshake failed: HTTP {response.status_code} - {response.text}"
                    self.logger.error(
                        error_msg,
                        extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
                    )
                    raise EncryptionError(error_msg)
                
                handshake_response = response.json()
                success = self.secure_channel.process_handshake_response(handshake_response)
                
                if not success:
                    error_msg = "Modelservice handshake response processing failed - invalid cryptographic response"
                    self.logger.error(
                        error_msg,
                        extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
                    )
                    raise EncryptionError(error_msg)
                
                self.session_established = True
                self.logger.info(
                    "Encrypted session established with modelservice",
                    extra={"topic": AICOTopics.SECURITY_TRANSPORT_SESSION}
                )
                
        except httpx.RequestError as e:
            error_msg = f"Network error during modelservice handshake: {e}"
            self.logger.error(
                error_msg,
                extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
            )
            raise EncryptionError(error_msg) from e
        except EncryptionError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during modelservice session establishment: {e}"
            self.logger.error(
                error_msg,
                extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
            )
            raise EncryptionError(error_msg) from e
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make encrypted HTTP request to modelservice."""
        await self._ensure_session()
        
        if not self.secure_channel:
            error_msg = "No secure channel available for modelservice communication"
            self.logger.error(
                error_msg,
                extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
            )
            raise EncryptionError(error_msg)
        
        url = f"{self.config.base_url}/api/v1{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                # Encrypt request payload
                if data:
                    try:
                        encrypted_payload = self.secure_channel.encrypt_json_payload(data)
                        request_data = {"encrypted_payload": encrypted_payload}
                    except Exception as e:
                        error_msg = f"Failed to encrypt request payload for {endpoint}: {e}"
                        self.logger.error(
                            error_msg,
                            extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
                        )
                        raise EncryptionError(error_msg) from e
                else:
                    request_data = None
                
                # Make HTTP request
                if method.upper() == "GET":
                    response = await client.get(url)
                elif method.upper() == "POST":
                    response = await client.post(url, json=request_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status_code != 200:
                    error_msg = f"Modelservice API error: {method} {endpoint} returned HTTP {response.status_code} - {response.text}"
                    self.logger.error(
                        error_msg,
                        extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
                    )
                    raise httpx.HTTPStatusError(
                        error_msg,
                        request=response.request,
                        response=response
                    )
                
                # Decrypt response
                try:
                    response_data = response.json()
                    if "encrypted_payload" in response_data:
                        decrypted_data = self.secure_channel.decrypt_json_payload(response_data["encrypted_payload"])
                        self.logger.debug(
                            f"Successfully decrypted response from {endpoint}",
                            extra={"topic": AICOTopics.SECURITY_TRANSPORT_SESSION}
                        )
                        return decrypted_data
                    else:
                        # Unencrypted response - this should not happen in secure mode
                        error_msg = f"Received unencrypted response from {endpoint} - security violation"
                        self.logger.error(
                            error_msg,
                            extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
                        )
                        raise EncryptionError(error_msg)
                except DecryptionError as e:
                    error_msg = f"Failed to decrypt response from {endpoint}: {e}"
                    self.logger.error(
                        error_msg,
                        extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
                    )
                    raise EncryptionError(error_msg) from e
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON response from {endpoint}: {e}"
                    self.logger.error(
                        error_msg,
                        extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
                    )
                    raise EncryptionError(error_msg) from e
                    
        except httpx.RequestError as e:
            error_msg = f"Network error during {method} {endpoint}: {e}"
            self.logger.error(
                error_msg,
                extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
            )
            raise EncryptionError(error_msg) from e
        except EncryptionError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during {method} {endpoint}: {e}"
            self.logger.error(
                error_msg,
                extra={"topic": AICOTopics.SECURITY_TRANSPORT_ERROR}
            )
            raise EncryptionError(error_msg) from e
    
    async def health_check(self) -> Dict[str, Any]:
        """Check modelservice health."""
        return await self._make_request("GET", "/health")
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        response = await self._make_request("GET", "/models")
        return response.get("models", [])
    
    async def create_completion(
        self,
        model: str,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text completion."""
        request_data = {
            "model": model,
            "prompt": prompt,
            "parameters": {}
        }
        
        if max_tokens is not None:
            request_data["parameters"]["max_tokens"] = max_tokens
        if temperature is not None:
            request_data["parameters"]["temperature"] = temperature
        
        # Add any additional parameters
        request_data["parameters"].update(kwargs)
        
        return await self._make_request("POST", "/completions", request_data)


# Singleton instance for backend use
_modelservice_client: Optional[ModelServiceClient] = None


def get_modelservice_client(key_manager: AICOKeyManager, config_manager: ConfigurationManager) -> ModelServiceClient:
    """Get singleton modelservice client instance."""
    global _modelservice_client
    
    if _modelservice_client is None:
        _modelservice_client = ModelServiceClient(key_manager, config_manager)
    
    return _modelservice_client
