"""
Transport Security Layer for AICO

Provides libsodium-based encryption for HTTP/WebSocket communication
extending the existing transport security architecture to frontend-backend.
"""

import os
import json
import time
import base64
from typing import Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from nacl.public import PrivateKey, PublicKey, Box
from nacl.signing import SigningKey, VerifyKey
from nacl.secret import SecretBox
from nacl.utils import random
from nacl.encoding import Base64Encoder
from nacl.exceptions import CryptoError

from aico.core.logging import get_logger
from aico.security.key_manager import AICOKeyManager
from .exceptions import EncryptionError, DecryptionError


@dataclass
class ComponentIdentity:
    """Component identity with Ed25519 keypair"""
    component_name: str
    signing_key: SigningKey
    verify_key: VerifyKey
    
    @classmethod
    def generate(cls, component_name: str) -> 'ComponentIdentity':
        """Generate new component identity"""
        signing_key = SigningKey.generate()
        verify_key = signing_key.verify_key
        return cls(component_name, signing_key, verify_key)
    
    @classmethod
    def from_seed(cls, component_name: str, seed: bytes) -> 'ComponentIdentity':
        """Create identity from seed"""
        signing_key = SigningKey(seed)
        verify_key = signing_key.verify_key
        return cls(component_name, signing_key, verify_key)
    
    def public_key_bytes(self) -> bytes:
        """Get public key as bytes"""
        return bytes(self.verify_key)
    
    def sign(self, message: bytes) -> bytes:
        """Sign message with identity"""
        return self.signing_key.sign(message).signature


@dataclass
class HandshakeMessage:
    """Handshake message format"""
    component: str
    public_key: str  # Base64 encoded - X25519 for key exchange
    timestamp: float
    challenge: str  # Base64 encoded
    signature: Optional[str] = None  # Base64 encoded
    identity_key: Optional[str] = None  # Base64 encoded Ed25519 for signatures
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "component": self.component,
            "public_key": self.public_key,
            "timestamp": self.timestamp,
            "challenge": self.challenge,
            "signature": self.signature
        }
        if self.identity_key:
            result["identity_key"] = self.identity_key
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HandshakeMessage':
        return cls(**data)


class SecureTransportChannel:
    """
    Secure transport channel using libsodium for HTTP/WebSocket communication
    
    Extends AICO's existing transport security to frontend-backend communication
    while maintaining JSON payload compatibility.
    """
    
    def __init__(self, identity: ComponentIdentity, key_manager: AICOKeyManager):
        self.identity = identity
        self.key_manager = key_manager
        self.logger = get_logger("security", "transport")
        
        # Session state
        self.peer_identity: Optional[ComponentIdentity] = None
        self.session_box: Optional[Box] = None
        self.session_established = False
        self.session_timestamp = 0
        
        # Configuration
        self.session_timeout = 3600  # 1 hour
        self.handshake_timeout = 30  # 30 seconds
        
    def create_handshake_request(self) -> Dict[str, Any]:
        """Create handshake request message"""
        challenge = random(32)
        timestamp = time.time()
        
        # Generate ephemeral X25519 keypair for session
        self.session_private_key = PrivateKey.generate()
        session_public_key = self.session_private_key.public_key
        
        message = HandshakeMessage(
            component=self.identity.component_name,
            public_key=base64.b64encode(bytes(session_public_key)).decode(),
            identity_key=base64.b64encode(bytes(self.identity.verify_key)).decode(),
            timestamp=timestamp,
            challenge=base64.b64encode(challenge).decode()
        )
        
        # Sign the challenge
        signature = self.identity.sign(challenge)
        message.signature = base64.b64encode(signature).decode()
        
        self.logger.debug("Created handshake request", extra={
            "component": self.identity.component_name,
            "timestamp": timestamp
        })
        
        return message.to_dict()
    
    def process_handshake_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming handshake request and create response"""
        try:
            request = HandshakeMessage.from_dict(request_data)
            
            # Verify timestamp freshness
            if abs(time.time() - request.timestamp) > self.handshake_timeout:
                raise EncryptionError("Handshake timestamp too old")
            
            # Verify signature using identity key (Ed25519)
            if hasattr(request, 'identity_key') and request.identity_key:
                peer_verify_key = VerifyKey(base64.b64decode(request.identity_key))
            else:
                # Fallback for old format
                peer_verify_key = VerifyKey(base64.b64decode(request.public_key))
            
            challenge = base64.b64decode(request.challenge)
            signature = base64.b64decode(request.signature)
            
            try:
                peer_verify_key.verify(challenge, signature)
            except Exception:
                raise EncryptionError("Invalid handshake signature")
            
            # Store peer's X25519 public key for session establishment
            if hasattr(request, 'identity_key') and request.identity_key:
                # New format: separate identity and session keys
                peer_session_key = base64.b64decode(request.public_key)
            else:
                # Old format: use same key for both (fallback)
                peer_session_key = base64.b64decode(request.public_key)
            
            # Create peer identity with Ed25519 key for verification
            self.peer_identity = ComponentIdentity(
                component_name=request.component,
                signing_key=None,  # We don't have their private key
                verify_key=peer_verify_key
            )
            
            # Store peer's X25519 session key separately
            self.peer_session_key = peer_session_key
            
            # Generate ephemeral X25519 keypair for session
            self.session_private_key = PrivateKey.generate()
            session_public_key = self.session_private_key.public_key
            
            # Create response with X25519 public key for session
            response_challenge = random(32)
            response = HandshakeMessage(
                component=self.identity.component_name,
                public_key=base64.b64encode(bytes(session_public_key)).decode(),
                identity_key=base64.b64encode(bytes(self.identity.verify_key)).decode(),
                timestamp=time.time(),
                challenge=base64.b64encode(response_challenge).decode()
            )
            
            # Sign response challenge with Ed25519 identity key
            response_signature = self.identity.sign(response_challenge)
            response.signature = base64.b64encode(response_signature).decode()
            
            # Establish session keys using the generated keypair
            self._establish_session_keys()
            
            self.logger.info("Handshake request processed", extra={
                "peer_component": request.component,
                "session_established": self.session_established
            })
            
            return response.to_dict()
            
        except Exception as e:
            self.logger.error(f"Handshake processing failed: {e}")
            raise EncryptionError(f"Handshake failed: {e}")
    
    def process_handshake_response(self, response_data: Dict[str, Any]) -> bool:
        """Process handshake response and establish session"""
        try:
            response = HandshakeMessage.from_dict(response_data)
            
            # Store response for session key establishment
            self.peer_handshake_response = response
            
            # Verify timestamp freshness
            if abs(time.time() - response.timestamp) > self.handshake_timeout:
                raise EncryptionError("Handshake response timestamp too old")
            
            # Verify signature using identity key (Ed25519), not public key (X25519)
            peer_verify_key = VerifyKey(base64.b64decode(response.identity_key))
            challenge = base64.b64decode(response.challenge)
            signature = base64.b64decode(response.signature)
            
            try:
                peer_verify_key.verify(challenge, signature)
            except Exception:
                raise EncryptionError("Invalid handshake response signature")
            
            # Create peer identity
            self.peer_identity = ComponentIdentity(
                component_name=response.component,
                signing_key=None,
                verify_key=peer_verify_key
            )
            
            # Establish session keys
            self._establish_session_keys()
            
            self.logger.info("Handshake completed", extra={
                "peer_component": response.component,
                "session_established": self.session_established
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Handshake response processing failed: {e}")
            return False
    
    def _establish_session_keys(self):
        """Establish session encryption keys using X25519"""
        if not self.peer_identity:
            raise EncryptionError("No peer identity for session establishment")
        
        try:
            # Use the session private key generated during handshake
            if not hasattr(self, 'session_private_key'):
                raise EncryptionError("No session private key - handshake not completed")
            
            # Get peer's X25519 public key from handshake response
            if hasattr(self, 'peer_session_key'):
                peer_public_key = PublicKey(self.peer_session_key)
            else:
                # Use the public_key from handshake response (X25519 session key)
                peer_public_key = PublicKey(base64.b64decode(self.peer_handshake_response.public_key))
            
            # Create Box for encryption using the consistent keypair
            self.session_box = Box(self.session_private_key, peer_public_key)
            self.session_established = True
            self.session_timestamp = time.time()
            
            self.logger.debug("Session keys established", extra={
                "peer_component": self.peer_identity.component_name,
                "timestamp": self.session_timestamp
            })
            
        except Exception as e:
            self.logger.error(f"Session key establishment failed: {e}")
            raise EncryptionError(f"Failed to establish session: {e}")
    
    def encrypt_json_payload(self, payload: Dict[str, Any]) -> str:
        """Encrypt JSON payload for transport"""
        if not self.session_established or not self.session_box:
            raise EncryptionError("No established session for encryption")
        
        # Check session timeout
        if time.time() - self.session_timestamp > self.session_timeout:
            raise EncryptionError("Session expired")
        
        try:
            # Serialize JSON payload
            json_data = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            
            # Encrypt with session box
            encrypted = self.session_box.encrypt(json_data)
            
            # Return base64 encoded ciphertext
            return base64.b64encode(encrypted).decode()
            
        except Exception as e:
            self.logger.error(f"Payload encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt payload: {e}")
    
    def decrypt_json_payload(self, encrypted_payload: str) -> Dict[str, Any]:
        """Decrypt JSON payload from transport"""
        if not self.session_established or not self.session_box:
            raise DecryptionError("No established session for decryption")
        
        # Check session timeout
        if time.time() - self.session_timestamp > self.session_timeout:
            raise DecryptionError("Session expired")
        
        try:
            # Decode base64
            encrypted_data = base64.b64decode(encrypted_payload)
            
            # Decrypt with session box
            decrypted = self.session_box.decrypt(encrypted_data)
            
            # Parse JSON
            return json.loads(decrypted.decode('utf-8'))
            
        except Exception as e:
            self.logger.error(f"Payload decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt payload: {e}")
    
    def is_session_valid(self) -> bool:
        """Check if current session is valid"""
        if not self.session_established:
            return False
        
        if time.time() - self.session_timestamp > self.session_timeout:
            return False
        
        return True
    
    def reset_session(self):
        """Reset session state"""
        self.peer_identity = None
        self.session_box = None
        self.session_established = False
        self.session_timestamp = 0
        
        self.logger.debug("Session reset")


class TransportIdentityManager:
    """
    Manages component identities for transport security
    
    Integrates with existing AICOKeyManager for persistent identity storage.
    """
    
    def __init__(self, key_manager: AICOKeyManager):
        self.key_manager = key_manager
        self.logger = get_logger("security", "transport_identity")
        self._identities: Dict[str, ComponentIdentity] = {}
    
    def get_component_identity(self, component_name: str) -> ComponentIdentity:
        """Get or create component identity"""
        if component_name in self._identities:
            return self._identities[component_name]
        
        # Try to load existing identity
        try:
            master_key = self.key_manager.authenticate(interactive=False)
            seed = self.key_manager.derive_transport_key(
                master_key,
                component_name,
                32  # 32 bytes for Ed25519 seed
            )
            
            identity = ComponentIdentity.from_seed(component_name, seed)
            self._identities[component_name] = identity
            
            self.logger.info("Component identity loaded", extra={
                "component": component_name
            })
            
            return identity
            
        except Exception as e:
            self.logger.error(f"Failed to load identity for {component_name}: {e}")
            raise EncryptionError(f"Failed to load component identity: {e}")
    
    def create_secure_channel(self, component_name: str) -> SecureTransportChannel:
        """Create secure transport channel for component"""
        identity = self.get_component_identity(component_name)
        return SecureTransportChannel(identity, self.key_manager)

    def process_handshake_and_create_channel(self, handshake_request: Dict[str, Any], component_name: str) -> Tuple[str, Dict[str, Any], SecureTransportChannel]:
        """Process handshake, create channel, and return client_id, response, and channel."""
        channel = self.create_secure_channel(component_name)
        response_data = channel.process_handshake_request(handshake_request)

        if "identity_key" not in handshake_request:
            raise EncryptionError("Handshake request missing 'identity_key'")

        identity_key_b64 = handshake_request["identity_key"]
        identity_key_bytes = base64.b64decode(identity_key_b64)
        client_id = identity_key_bytes.hex()[:16]

        self.logger.info(f"Processed handshake for client_id: {client_id}")

        return client_id, response_data, channel
