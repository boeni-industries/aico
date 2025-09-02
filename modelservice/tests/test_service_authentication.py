"""
Test Service Authentication between Modelservice and API Gateway

Tests the complete service-to-service authentication flow including:
- Service token generation and validation
- API Gateway authentication
- Logging client authentication
- Health check integration
"""

import pytest
import asyncio
import httpx
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager
from aico.security.transport import TransportIdentityManager
from aico.security.service_auth import ServiceAuthManager, ServiceToken
from aico.security.exceptions import EncryptionError
from backend.api_gateway.models.core.auth import AuthenticationManager, AuthMethod, AuthResult
from modelservice.api.logging_client import APIGatewayLoggingClient
from modelservice.api.dependencies import get_service_auth_manager


class TestServiceAuthentication:
    """Test service authentication components"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration manager"""
        config = Mock(spec=ConfigurationManager)
        config.get.side_effect = lambda key, default=None: {
            "api_gateway.rest.host": "127.0.0.1",
            "api_gateway.rest.port": 8771,
            "modelservice.api_gateway.rest.host": "127.0.0.1",
            "modelservice.api_gateway.rest.port": 8771
        }.get(key, default)
        return config
    
    @pytest.fixture
    def mock_key_manager(self):
        """Mock AICO key manager"""
        key_manager = Mock(spec=AICOKeyManager)
        key_manager.authenticate.return_value = b"mock_master_key" * 2  # 32 bytes
        key_manager.derive_transport_key.return_value = b"mock_transport_key" * 2  # 32 bytes
        key_manager.keyring = Mock()
        return key_manager
    
    @pytest.fixture
    def mock_identity_manager(self, mock_key_manager):
        """Mock transport identity manager"""
        identity_manager = Mock(spec=TransportIdentityManager)
        
        # Mock component identity
        mock_identity = Mock()
        mock_identity.component_name = "modelservice"
        mock_identity.verify_key = Mock()
        mock_identity.verify_key.encode.return_value = Mock()
        mock_identity.verify_key.encode().hex.return_value = "abcd1234567890ef" * 2
        mock_identity.signing_key = Mock()
        mock_identity.signing_key.encode.return_value = b"mock_signing_key" * 2
        
        identity_manager.get_component_identity.return_value = mock_identity
        return identity_manager
    
    @pytest.fixture
    def service_auth_manager(self, mock_key_manager, mock_identity_manager):
        """Service authentication manager"""
        return ServiceAuthManager(mock_key_manager, mock_identity_manager)
    
    @pytest.fixture
    def api_gateway_auth(self, mock_config):
        """API Gateway authentication manager"""
        with patch('backend.api_gateway.models.core.auth.AICOKeyManager') as mock_km, \
             patch('backend.api_gateway.models.core.auth.TransportIdentityManager') as mock_tim, \
             patch('backend.api_gateway.models.core.auth.ServiceAuthManager') as mock_sam:
            
            # Mock the key manager methods
            mock_km_instance = Mock()
            mock_km_instance.get_jwt_secret.return_value = "mock_jwt_secret"
            mock_km.return_value = mock_km_instance
            
            # Mock service auth manager
            mock_sam_instance = Mock()
            mock_sam.return_value = mock_sam_instance
            
            auth_manager = AuthenticationManager(mock_config)
            return auth_manager


class TestServiceTokenGeneration:
    """Test service token generation and validation"""
    
    def test_generate_service_token(self, service_auth_manager):
        """Test service token generation"""
        with patch('jwt.encode') as mock_jwt_encode:
            mock_jwt_encode.return_value = "mock.jwt.token"
            
            token = service_auth_manager.generate_service_token("modelservice")
            
            assert token == "mock.jwt.token"
            mock_jwt_encode.assert_called_once()
            
            # Verify JWT claims
            call_args = mock_jwt_encode.call_args
            claims = call_args[0][0]  # First positional argument
            
            assert claims["iss"] == "aico-system"
            assert claims["sub"] == "modelservice"
            assert claims["aud"] == "api-gateway"
            assert claims["service_type"] == "modelservice"
            assert "logs:write" in claims["permissions"]
            assert "health:read" in claims["permissions"]
    
    def test_validate_service_token_success(self, service_auth_manager):
        """Test successful service token validation"""
        mock_token = "valid.jwt.token"
        
        with patch('jwt.decode') as mock_jwt_decode:
            # Mock JWT decode to return valid claims
            mock_claims = {
                "iss": "aico-system",
                "sub": "modelservice",
                "aud": "api-gateway",
                "iat": int(datetime.utcnow().timestamp()),
                "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
                "service_type": "modelservice",
                "permissions": ["logs:write", "health:read"],
                "component_id": "abcd1234567890ef"
            }
            mock_jwt_decode.return_value = mock_claims
            
            service_token = service_auth_manager.validate_service_token(mock_token)
            
            assert service_token.service_name == "modelservice"
            assert service_token.target_service == "api-gateway"
            assert "logs:write" in service_token.permissions
            assert service_token.component_id == "abcd1234567890ef"
    
    def test_validate_service_token_expired(self, service_auth_manager):
        """Test validation of expired service token"""
        mock_token = "expired.jwt.token"
        
        with patch('jwt.decode') as mock_jwt_decode:
            from jwt import ExpiredSignatureError
            mock_jwt_decode.side_effect = ExpiredSignatureError("Token expired")
            
            with pytest.raises(EncryptionError, match="Service token expired"):
                service_auth_manager.validate_service_token(mock_token)
    
    def test_validate_service_token_invalid(self, service_auth_manager):
        """Test validation of invalid service token"""
        mock_token = "invalid.jwt.token"
        
        with patch('jwt.decode') as mock_jwt_decode:
            from jwt import InvalidTokenError
            mock_jwt_decode.side_effect = InvalidTokenError("Invalid token")
            
            with pytest.raises(EncryptionError, match="Invalid service token"):
                service_auth_manager.validate_service_token(mock_token)


class TestAPIGatewayAuthentication:
    """Test API Gateway service token authentication"""
    
    @pytest.mark.asyncio
    async def test_authenticate_service_token_success(self, api_gateway_auth):
        """Test successful service token authentication"""
        mock_token = "valid.service.token"
        
        # Mock service token validation
        mock_service_token = ServiceToken(
            service_name="modelservice",
            target_service="api-gateway",
            permissions=["logs:write", "health:read"],
            component_id="abcd1234",
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        api_gateway_auth.service_auth.validate_service_token.return_value = mock_service_token
        
        client_info = {"headers": {"authorization": f"Bearer {mock_token}"}}
        result = await api_gateway_auth.authenticate(None, client_info)
        
        assert result.success is True
        assert result.method == AuthMethod.SERVICE_TOKEN
        assert result.user.username == "modelservice"
        assert "logs:write" in result.user.permissions
        assert result.user.roles == ["service"]
    
    @pytest.mark.asyncio
    async def test_authenticate_service_token_invalid(self, api_gateway_auth):
        """Test authentication with invalid service token"""
        mock_token = "invalid.service.token"
        
        # Mock service token validation failure
        api_gateway_auth.service_auth.validate_service_token.side_effect = EncryptionError("Invalid token")
        
        client_info = {"headers": {"authorization": f"Bearer {mock_token}"}}
        result = await api_gateway_auth.authenticate(None, client_info)
        
        assert result.success is False
        assert "Invalid service token" in result.error


class TestLoggingClientAuthentication:
    """Test logging client authentication with API Gateway"""
    
    @pytest.fixture
    def logging_client(self, mock_config, service_auth_manager):
        """Logging client instance"""
        return APIGatewayLoggingClient(
            config={"api_gateway": {"rest": {"host": "127.0.0.1", "port": 8771}}},
            service_auth=service_auth_manager
        )
    
    @pytest.mark.asyncio
    async def test_get_service_token(self, logging_client):
        """Test service token retrieval"""
        mock_token = "test.service.token"
        
        with patch.object(logging_client.service_auth, 'ensure_service_token') as mock_ensure:
            mock_ensure.return_value = mock_token
            
            token = await logging_client._get_service_token()
            
            assert token == mock_token
            mock_ensure.assert_called_once_with("modelservice")
    
    @pytest.mark.asyncio
    async def test_submit_log_success(self, logging_client):
        """Test successful log submission"""
        mock_token = "test.service.token"
        
        with patch.object(logging_client, '_get_service_token') as mock_get_token, \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_get_token.return_value = mock_token
            
            # Mock successful HTTP response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await logging_client.submit_log("INFO", "Test message", "test_module")
            
            assert result is True
            
            # Verify request was made with correct headers
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            headers = call_args[1]['headers']
            assert headers['Authorization'] == f'Bearer {mock_token}'
            assert headers['Content-Type'] == 'application/json'
    
    @pytest.mark.asyncio
    async def test_submit_log_auth_failure(self, logging_client):
        """Test log submission with authentication failure"""
        with patch.object(logging_client, '_get_service_token') as mock_get_token, \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_get_token.side_effect = Exception("Token generation failed")
            
            result = await logging_client.submit_log("INFO", "Test message", "test_module")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_api_gateway_health_success(self, logging_client):
        """Test successful API Gateway health check"""
        mock_token = "test.service.token"
        
        with patch.object(logging_client, '_get_service_token') as mock_get_token, \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_get_token.return_value = mock_token
            
            # Mock successful health response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            health = await logging_client.check_api_gateway_health()
            
            assert health["status"] == "healthy"
            assert health["reachable"] is True
            assert health["response_time_ms"] == 100.0
            assert health["api_gateway_status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_check_api_gateway_health_connection_error(self, logging_client):
        """Test API Gateway health check with connection error"""
        with patch.object(logging_client, '_get_service_token') as mock_get_token, \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_get_token.return_value = "test.token"
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            
            health = await logging_client.check_api_gateway_health()
            
            assert health["status"] == "unhealthy"
            assert health["reachable"] is False
            assert health["error"] == "connection_refused"


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_authentication_flow(self, service_auth_manager, api_gateway_auth):
        """Test complete authentication flow from token generation to validation"""
        
        # Step 1: Generate service token
        with patch('jwt.encode') as mock_encode, \
             patch('jwt.decode') as mock_decode:
            
            mock_token = "integration.test.token"
            mock_encode.return_value = mock_token
            
            # Generate token
            token = service_auth_manager.generate_service_token("modelservice")
            assert token == mock_token
            
            # Step 2: Validate token in API Gateway
            mock_claims = {
                "iss": "aico-system",
                "sub": "modelservice", 
                "aud": "api-gateway",
                "iat": int(datetime.utcnow().timestamp()),
                "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
                "service_type": "modelservice",
                "permissions": ["logs:write", "health:read"],
                "component_id": "abcd1234"
            }
            mock_decode.return_value = mock_claims
            
            # Mock service token object
            mock_service_token = ServiceToken(
                service_name="modelservice",
                target_service="api-gateway", 
                permissions=["logs:write", "health:read"],
                component_id="abcd1234",
                issued_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            
            api_gateway_auth.service_auth.validate_service_token.return_value = mock_service_token
            
            # Authenticate request
            client_info = {"headers": {"authorization": f"Bearer {token}"}}
            result = await api_gateway_auth.authenticate(None, client_info)
            
            assert result.success is True
            assert result.user.username == "modelservice"
            assert "logs:write" in result.user.permissions
    
    def test_token_storage_and_retrieval(self, service_auth_manager):
        """Test token storage and retrieval from keyring"""
        mock_token = "stored.test.token"
        service_name = "modelservice"
        
        # Test storage
        service_auth_manager.store_service_token(service_name, mock_token)
        service_auth_manager.key_manager.keyring.set_password.assert_called_once_with(
            f"aico-service-{service_name}",
            "auth_token", 
            mock_token
        )
        
        # Test retrieval
        service_auth_manager.key_manager.keyring.get_password.return_value = mock_token
        
        with patch.object(service_auth_manager, 'validate_service_token') as mock_validate:
            mock_validate.return_value = Mock()  # Valid token
            
            retrieved_token = service_auth_manager.load_service_token(service_name)
            
            assert retrieved_token == mock_token
            service_auth_manager.key_manager.keyring.get_password.assert_called_once_with(
                f"aico-service-{service_name}",
                "auth_token"
            )
    
    def test_permission_validation(self, service_auth_manager):
        """Test service permission validation"""
        # Test modelservice permissions
        modelservice_permissions = service_auth_manager.get_service_permissions("modelservice")
        assert "logs:write" in modelservice_permissions
        assert "health:read" in modelservice_permissions
        
        # Test unknown service
        unknown_permissions = service_auth_manager.get_service_permissions("unknown_service")
        assert unknown_permissions == []
        
        # Test permission checking
        mock_service_token = ServiceToken(
            service_name="modelservice",
            target_service="api-gateway",
            permissions=["logs:write", "health:read"],
            component_id="test",
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert service_auth_manager.has_permission(mock_service_token, "logs:write") is True
        assert service_auth_manager.has_permission(mock_service_token, "admin:write") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
