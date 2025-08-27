"""
Encryption Plugin for AICO API Gateway

Leverages existing transport security infrastructure from /shared/aico/security/transport.py
for libsodium-based encryption, handshake negotiation, and session management.
"""

import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import Request, Response

from ..core.plugin_registry import PluginInterface, PluginMetadata, PluginPriority
from ..middleware.encryption import EncryptionMiddleware
from aico.security.key_manager import AICOKeyManager
from aico.security.transport import TransportIdentityManager, SecureTransportChannel
from aico.security.exceptions import EncryptionError, DecryptionError


class EncryptionPlugin(PluginInterface):
    """
    Transport encryption plugin using libsodium
    
    Integrates EncryptionMiddleware into the plugin system for:
    - /api/v1/handshake endpoint handling
    - Session-based encryption/decryption
    - Transport security with XChaCha20-Poly1305
    - Ed25519 identity and X25519 key exchange
    """
    
    def __init__(self, config: Dict[str, Any], logger):
        super().__init__(config, logger)
        self.encryption_middleware: Optional[EncryptionMiddleware] = None
        self.key_manager: Optional[AICOKeyManager] = None
        self.identity_manager: Optional[TransportIdentityManager] = None
        self.secure_channel: Optional[SecureTransportChannel] = None
        
        # Configuration
        self.handshake_path = "/api/v1/handshake"
        self.require_encryption = config.get("require_encryption", True)
        self.session_timeout = config.get("session_timeout_seconds", 3600)
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="encryption",
            version="1.0.0",
            description="libsodium transport encryption with handshake negotiation",
            priority=PluginPriority.HIGHEST,  # Must run before security
            dependencies=[],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "require_encryption": {"type": "boolean", "default": True},
                "session_timeout_seconds": {"type": "integer", "default": 3600},
                "handshake_timeout_seconds": {"type": "integer", "default": 30},
                "max_payload_size": {"type": "integer", "default": 1048576}
            }
        )
    
    async def initialize(self, dependencies: Dict[str, Any]) -> None:
        """Initialize encryption middleware and transport security"""
        try:
            config_manager = dependencies.get('config')
            self.key_manager = dependencies.get('key_manager')
            
            if not config_manager or not self.key_manager:
                raise ValueError("ConfigurationManager and AICOKeyManager dependencies required")
            
            # Initialize transport security components
            self.identity_manager = TransportIdentityManager(self.key_manager)
            self.secure_channel = self.identity_manager.create_secure_channel("api_gateway")
            
            # Create encryption middleware instance
            # Note: This will be integrated with FastAPI app separately
            self.encryption_middleware = EncryptionMiddleware(None, self.key_manager)
            
            self.logger.info("Encryption plugin initialized", extra={
                "handshake_path": self.handshake_path,
                "require_encryption": self.require_encryption,
                "session_timeout": self.session_timeout
            })
            
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption plugin: {e}")
            raise
    
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through encryption layer"""
        if not self.enabled:
            return context
        
        try:
            protocol = context.get('protocol')
            request_data = context.get('request_data')
            
            # Handle handshake requests specially
            if self._is_handshake_request(context):
                response = await self._handle_handshake_request(context)
                context['response'] = response
                context['skip_further_processing'] = True
                return context
            
            # For REST protocol, encryption is handled by FastAPI middleware
            if protocol == 'rest':
                # Middleware handles encryption/decryption automatically
                return context
            
            # For other protocols (WebSocket, ZeroMQ), handle encryption here
            if protocol in ['websocket', 'zeromq_ipc']:
                decrypted_data = await self._decrypt_request(request_data, context)
                if decrypted_data:
                    context['request_data'] = decrypted_data
            
            return context
            
        except EncryptionError as e:
            self.logger.warning(f"Encryption error: {e}")
            context['error'] = {
                'status_code': 400,
                'message': 'Encryption error',
                'detail': str(e)
            }
            return context
        except Exception as e:
            self.logger.error(f"Encryption plugin error: {e}")
            context['error'] = {
                'status_code': 500,
                'message': 'Encryption processing error',
                'detail': str(e)
            }
            return context
    
    async def process_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process outgoing response through encryption"""
        if not self.enabled or context.get('skip_further_processing'):
            return context
        
        try:
            protocol = context.get('protocol')
            response = context.get('response')
            
            # For non-REST protocols, encrypt response
            if protocol in ['websocket', 'zeromq_ipc'] and response:
                encrypted_response = await self._encrypt_response(response, context)
                if encrypted_response:
                    context['response'] = encrypted_response
            
            return context
            
        except Exception as e:
            self.logger.error(f"Response encryption error: {e}")
            return context
    
    def _is_handshake_request(self, context: Dict[str, Any]) -> bool:
        """Check if this is a handshake request"""
        request_data = context.get('request_data', {})
        
        # For REST requests
        if isinstance(request_data, dict):
            path = request_data.get('path', '')
            return path == self.handshake_path
        
        # For other protocols, check message type
        if hasattr(request_data, 'message_type'):
            return request_data.message_type == 'handshake'
        
        return False
    
    async def _handle_handshake_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle encryption handshake request using existing transport security"""
        try:
            request_data = context.get('request_data', {})
            client_info = context.get('client_info', {})
            
            # Extract handshake data
            if isinstance(request_data, dict):
                # REST request
                body = request_data.get('body', b'')
                if isinstance(body, bytes):
                    payload = json.loads(body.decode('utf-8'))
                else:
                    payload = body
                
                # Extract the actual handshake request from the wrapper
                if 'handshake_request' in payload:
                    handshake_data = payload['handshake_request']
                else:
                    handshake_data = payload
            else:
                # Other protocols
                handshake_data = request_data
            
            # Add timestamp if not present (required by HandshakeMessage)
            import time
            if 'timestamp' not in handshake_data:
                handshake_data['timestamp'] = time.time()
            
            # Use existing SecureTransportChannel to process handshake
            response_data = self.secure_channel.process_handshake_request(handshake_data)
            
            self.logger.info("Handshake completed using transport security", extra={
                'client_component': handshake_data.get('component', 'unknown'),
                'client_id': client_info.get('client_id', 'unknown')
            })
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"Handshake error: {e}")
            import traceback
            self.logger.error(f"Handshake traceback: {traceback.format_exc()}")
            raise EncryptionError(f"Handshake failed: {e}")
    
    async def _decrypt_request(self, request_data: Any, context: Dict[str, Any]) -> Any:
        """Decrypt request data using existing transport security"""
        try:
            if not isinstance(request_data, dict):
                return request_data
            
            encrypted_payload = request_data.get('encrypted_payload')
            
            if not encrypted_payload:
                # Not encrypted
                return request_data
            
            # Use existing SecureTransportChannel decrypt method
            if self.secure_channel.is_session_valid():
                decrypted_data = self.secure_channel.decrypt_json_payload(encrypted_payload)
                return decrypted_data
            else:
                raise DecryptionError("No valid session for decryption")
            
        except Exception as e:
            self.logger.error(f"Decryption error: {e}")
            raise DecryptionError(f"Failed to decrypt request: {e}")
    
    async def _encrypt_response(self, response: Any, context: Dict[str, Any]) -> Any:
        """Encrypt response data using existing transport security"""
        try:
            if not self.secure_channel.is_session_valid():
                # No valid session, return unencrypted
                return response
            
            # Use existing SecureTransportChannel encrypt method
            if isinstance(response, dict):
                encrypted_payload = self.secure_channel.encrypt_json_payload(response)
                return {
                    'encrypted_payload': encrypted_payload,
                    'encrypted': True
                }
            else:
                # Convert to dict first
                response_dict = {'data': response}
                encrypted_payload = self.secure_channel.encrypt_json_payload(response_dict)
                return {
                    'encrypted_payload': encrypted_payload,
                    'encrypted': True
                }
            
        except Exception as e:
            self.logger.error(f"Response encryption error: {e}")
            return response  # Return unencrypted on error
    
    def get_encryption_middleware(self) -> Optional[EncryptionMiddleware]:
        """Get the encryption middleware instance for FastAPI integration"""
        return self.encryption_middleware
    
    def configure_fastapi_middleware(self, app):
        """Configure encryption middleware on FastAPI app"""
        if not self.enabled or not self.encryption_middleware:
            return
        
        from ..middleware.encryption import EncryptionMiddleware
        app.add_middleware(EncryptionMiddleware, key_manager=self.key_manager)
        self.logger.info("Encryption middleware configured on FastAPI app")
    
    async def shutdown(self) -> None:
        """Cleanup encryption plugin resources"""
        await self.stop()
        self.logger.info("Encryption plugin shutdown")
