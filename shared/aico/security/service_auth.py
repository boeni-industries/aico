"""
Service-to-Service Authentication for AICO

Provides JWT-based service authentication that integrates with existing
transport security and component identity infrastructure.
"""

import time
import json
import base64
import jwt
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from aico.core.logging import get_logger
from aico.security.key_manager import AICOKeyManager
from .transport import ComponentIdentity, TransportIdentityManager
from .exceptions import EncryptionError


@dataclass
class ServiceToken:
    """Service identity token for service-to-service authentication"""
    service_name: str
    target_service: str
    permissions: List[str]
    component_id: str
    issued_at: datetime
    expires_at: datetime
    
    def to_jwt_claims(self) -> Dict[str, Any]:
        """Convert to JWT claims"""
        return {
            "iss": "aico-system",
            "sub": self.service_name,
            "aud": self.target_service,
            "iat": int(self.issued_at.timestamp()),
            "exp": int(self.expires_at.timestamp()),
            "service_type": self.service_name,
            "permissions": self.permissions,
            "component_id": self.component_id
        }
    
    @classmethod
    def from_jwt_claims(cls, claims: Dict[str, Any]) -> 'ServiceToken':
        """Create from JWT claims"""
        return cls(
            service_name=claims["sub"],
            target_service=claims["aud"],
            permissions=claims.get("permissions", []),
            component_id=claims.get("component_id", ""),
            issued_at=datetime.fromtimestamp(claims["iat"]),
            expires_at=datetime.fromtimestamp(claims["exp"])
        )


class ServiceAuthManager:
    """
    Manages service-to-service authentication tokens
    
    Integrates with AICO's existing transport security and key management
    to provide JWT-based service authentication.
    """
    
    def __init__(self, key_manager: AICOKeyManager, identity_manager: TransportIdentityManager):
        self.key_manager = key_manager
        self.identity_manager = identity_manager
        self.logger = get_logger("shared", "security.service_auth")
        
        # Service permissions mapping
        self.service_permissions = {
            "modelservice": ["logs:write", "health:read"],
            "frontend": ["logs:write", "conversation:read", "conversation:write"],
            "cli": ["admin:read", "admin:write", "logs:read", "system:read"],
            "studio": ["logs:write", "system:read", "admin:read"]
        }
    
    def generate_service_token(self, service_name: str, target_service: str = "api-gateway", 
                             validity_hours: int = 8760) -> str:  # 1 year default
        """Generate service identity token"""
        try:
            # Get component identity for signing
            identity = self.identity_manager.get_component_identity(service_name)
            
            # Get service permissions
            permissions = self.service_permissions.get(service_name, [])
            
            # Create token
            now = datetime.utcnow()
            expires = now + timedelta(hours=validity_hours)
            
            service_token = ServiceToken(
                service_name=service_name,
                target_service=target_service,
                permissions=permissions,
                component_id=bytes(identity.verify_key).hex()[:16],
                issued_at=now,
                expires_at=expires
            )
            
            # Sign with component identity (Ed25519)
            # Convert PyNaCl signing key to cryptography Ed25519PrivateKey for PyJWT
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            
            # PyNaCl SigningKey uses 32-byte seed, cryptography Ed25519PrivateKey expects same
            signing_key_bytes = bytes(identity.signing_key)[:32]  # Get the 32-byte seed
            crypto_private_key = Ed25519PrivateKey.from_private_bytes(signing_key_bytes)
            
            # Generate JWT
            token = jwt.encode(
                service_token.to_jwt_claims(),
                crypto_private_key,
                algorithm="EdDSA"  # Ed25519 signature
            )
            
            self.logger.info("Service token generated successfully", extra={
                "service": service_name,
                "target": target_service,
                "permissions": permissions,
                "component_id": bytes(identity.verify_key).hex()[:16],
                "expires": expires.isoformat(),
                "auth_method": "JWT_EdDSA"
            })
            
            # Print statement for successful token generation
            print(f"[TOKEN GENERATED] Service '{service_name}' obtained authentication token for '{target_service}' with permissions: {permissions}")
            
            return token
            
        except Exception as e:
            self.logger.error(f"Failed to generate service token for {service_name}: {e}")
            raise EncryptionError(f"Service token generation failed: {e}")
    
    def validate_service_token(self, token: str, expected_service: str = None) -> ServiceToken:
        """Validate service identity token"""
        try:
            # Decode without verification first to get component_id
            unverified = jwt.decode(token, options={"verify_signature": False})
            service_name = unverified.get("sub")
            component_id = unverified.get("component_id")
            
            if not service_name or not component_id:
                raise EncryptionError("Invalid token format")
            
            # Get component identity for verification
            identity = self.identity_manager.get_component_identity(service_name)
            # Convert PyNaCl verify key to cryptography Ed25519PublicKey for PyJWT
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            
            # PyNaCl VerifyKey uses 32-byte public key, cryptography Ed25519PublicKey expects same
            verify_key_bytes = bytes(identity.verify_key)
            crypto_public_key = Ed25519PublicKey.from_public_bytes(verify_key_bytes)
            
            # Verify JWT signature
            claims = jwt.decode(
                token,
                crypto_public_key,
                algorithms=["EdDSA"],
                audience="api-gateway",
                issuer="aico-system"
            )
            
            # Create service token from claims
            service_token = ServiceToken.from_jwt_claims(claims)
            
            # Additional validation
            if expected_service and service_token.service_name != expected_service:
                raise EncryptionError(f"Token service mismatch: expected {expected_service}, got {service_token.service_name}")
            
            # Check component ID matches
            if service_token.component_id != bytes(identity.verify_key).hex()[:16]:
                raise EncryptionError("Component ID mismatch")
            
            self.logger.info("Service authentication successful", extra={
                "service": service_token.service_name,
                "target": service_token.target_service,
                "permissions": service_token.permissions,
                "component_id": service_token.component_id,
                "expires": service_token.expires_at.isoformat(),
                "auth_method": "JWT_EdDSA"
            })
            
            # Print statement for successful authentication
            print(f"[+] {service_token.service_name.title()} has connected successfully")
            #print(f"[AUTH SUCCESS] Service '{service_token.service_name}' authenticated to '{service_token.target_service}' with permissions: {service_token.permissions}")
            
            return service_token
            
        except jwt.ExpiredSignatureError:
            raise EncryptionError("Service token expired")
        except jwt.InvalidTokenError as e:
            raise EncryptionError(f"Invalid service token: {e}")
        except Exception as e:
            self.logger.error(f"Service token validation failed: {e}")
            raise EncryptionError(f"Token validation failed: {e}")
    
    def get_service_permissions(self, service_name: str) -> List[str]:
        """Get permissions for a service"""
        return self.service_permissions.get(service_name, [])
    
    def has_permission(self, service_token: ServiceToken, required_permission: str) -> bool:
        """Check if service token has required permission"""
        return required_permission in service_token.permissions
    
    def store_service_token(self, service_name: str, token: str):
        """Store service token in keyring"""
        try:
            import keyring
            keyring.set_password(
                f"aico-service-{service_name}",
                "auth_token",
                token
            )
            
            self.logger.debug("Service token stored", extra={
                "service": service_name
            })
            
        except Exception as e:
            self.logger.error(f"Failed to store service token for {service_name}: {e}")
            raise EncryptionError(f"Token storage failed: {e}")
    
    def load_service_token(self, service_name: str) -> Optional[str]:
        """Load service token from keyring"""
        try:
            import keyring
            token = keyring.get_password(
                f"aico-service-{service_name}",
                "auth_token"
            )
            
            if token:
                # Validate token is not expired
                try:
                    service_token = self.validate_service_token(token, service_name)
                    return token
                except EncryptionError:
                    # Token expired or invalid, remove it
                    self.clear_service_token(service_name)
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load service token for {service_name}: {e}")
            return None
    
    def clear_service_token(self, service_name: str):
        """Clear stored service token"""
        try:
            import keyring
            keyring.delete_password(
                f"aico-service-{service_name}",
                "auth_token"
            )
            
            self.logger.debug("Service token cleared", extra={
                "service": service_name
            })
            
        except Exception as e:
            self.logger.debug(f"Service token clear failed (may not exist): {e}")
    
    def ensure_service_token(self, service_name: str, target_service: str = "api-gateway") -> str:
        """Ensure valid service token exists, generate if needed"""
        # Try to load existing token
        token = self.load_service_token(service_name)
        
        if token:
            return token
        
        # Generate new token
        token = self.generate_service_token(service_name, target_service)
        self.store_service_token(service_name, token)
        
        return token
