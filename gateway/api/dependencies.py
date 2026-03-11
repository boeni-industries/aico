"""Global API dependencies.

This module is the canonical place for REST + WebSocket authentication dependencies.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from aico.core.logging import get_logger

from aico.common.errors import raise_api_error


# Allow endpoints to decide whether missing credentials is an error.
# This lets local/dev disable auth entirely via configuration.
security = HTTPBearer(auto_error=False)
logger = get_logger("api.dependencies")


def _is_security_enabled() -> bool:
    try:
        from aico.core.config import ConfigurationManager

        cfg = ConfigurationManager()
        cfg.initialize(lightweight=True)
        return bool(cfg.get("api_gateway.plugins.security.enabled", True))
    except Exception:
        return True


def get_auth_manager(request: Request):
    if not hasattr(request.app.state, "service_container"):
        raise_api_error(
            status_code=500,
            error_code="SERVICE_CONTAINER_NOT_INITIALIZED",
            message="Service container not initialized",
        )

    container = request.app.state.service_container
    # Gateway no longer loads the legacy security plugin in most deployments.
    # Prefer the directly-registered auth_manager service, then fall back to
    # a gateway reference when available.
    try:
        auth_manager = container.get_service("auth_manager")
        if auth_manager is not None:
            return auth_manager
    except Exception:
        pass

    gateway = getattr(request.app.state, "gateway", None)
    if gateway is not None and getattr(gateway, "auth_manager", None) is not None:
        return gateway.auth_manager

    raise_api_error(
        status_code=500,
        error_code="AUTH_MANAGER_NOT_INITIALIZED",
        message="Authentication manager not initialized",
    )


def _normalize_user_payload(*, token: str, payload: dict[str, Any]) -> Dict[str, Any]:
    user_id = payload.get("user_id") or payload.get("user_uuid") or payload.get("sub")
    if not user_id:
        raise_api_error(
            status_code=401,
            error_code="AUTH_TOKEN_MISSING_USER_ID",
            message="Invalid token: missing user id",
        )

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise_api_error(
            status_code=401,
            error_code="AUTH_TOKEN_MISSING_TENANT_ID",
            message="Invalid token: missing tenant id",
        )
    roles = payload.get("roles", [])
    permissions = set(payload.get("permissions", []))

    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "user_uuid": user_id,
        "username": payload.get("username"),
        "roles": roles,
        "permissions": permissions,
        "token": token,
    }


def _decode_and_verify_jwt(*, token: str, auth_manager) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            auth_manager._get_jwt_secret(),
            algorithms=[getattr(auth_manager, "jwt_algorithm", "HS256")],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise_api_error(status_code=401, error_code="AUTH_TOKEN_EXPIRED", message="Token has expired")
    except jwt.InvalidTokenError:
        raise_api_error(status_code=401, error_code="AUTH_TOKEN_INVALID", message="Invalid token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    request: Request = None,
    auth_manager=None,
) -> Dict[str, Any]:
    if credentials is None:
        if not _is_security_enabled():
            return {
                "tenant_id": "local",
                "user_id": "system_user",
                "user_uuid": "system_user",
                "username": "system",
                "roles": ["system"],
                "permissions": set(),
                "token": None,
            }
        # Missing credentials should be a 401 so clients can trigger re-auth / token refresh.
        raise_api_error(status_code=401, error_code="AUTH_TOKEN_REQUIRED", message="Not authenticated")

    if auth_manager is None:
        if request is None:
            raise_api_error(
                status_code=500,
                error_code="SERVICE_CONTAINER_NOT_INITIALIZED",
                message="Service container not initialized",
            )

        auth_manager = get_auth_manager(request)

    token = credentials.credentials

    payload = _decode_and_verify_jwt(token=token, auth_manager=auth_manager)

    if hasattr(auth_manager, "revoked_tokens") and token in auth_manager.revoked_tokens:
        raise_api_error(status_code=401, error_code="AUTH_TOKEN_REVOKED", message="Token has been revoked")

    return _normalize_user_payload(token=token, payload=payload)


def authenticate_websocket(*, websocket: WebSocket) -> Dict[str, Any]:
    auth_header = websocket.headers.get("authorization")
    token: Optional[str] = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if token is None:
        token = websocket.query_params.get("token")
    if token is None:
        if not _is_security_enabled():
            return {
                "tenant_id": "local",
                "user_id": "system_user",
                "user_uuid": "system_user",
                "username": "system",
                "roles": ["system"],
                "permissions": set(),
                "token": None,
            }
        raise_api_error(status_code=401, error_code="AUTH_TOKEN_REQUIRED", message="Missing token")

    if not hasattr(websocket.app.state, "service_container"):
        raise_api_error(
            status_code=500,
            error_code="SERVICE_CONTAINER_NOT_INITIALIZED",
            message="Service container not initialized",
        )

    container = websocket.app.state.service_container
    security_plugin = container.get_service("security_plugin")
    if security_plugin is None or not hasattr(security_plugin, "auth_manager"):
        if not _is_security_enabled():
            return {
                "tenant_id": "local",
                "user_id": "system_user",
                "user_uuid": "system_user",
                "username": "system",
                "roles": ["system"],
                "permissions": set(),
                "token": None,
            }
        raise_api_error(
            status_code=500,
            error_code="SECURITY_PLUGIN_NOT_INITIALIZED",
            message="Security plugin not initialized",
        )

    auth_manager = security_plugin.auth_manager
    payload = _decode_and_verify_jwt(token=token, auth_manager=auth_manager)
    if hasattr(auth_manager, "revoked_tokens") and token in auth_manager.revoked_tokens:
        raise_api_error(status_code=401, error_code="AUTH_TOKEN_REVOKED", message="Token has been revoked")

    return _normalize_user_payload(token=token, payload=payload)


def create_auth_dependency(auth_manager):
    """
    Factory function to create auth dependency with injected auth_manager.
    This will be called from main.py during app initialization.
    """
    async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        try:
            token = credentials.credentials
            
            # Decode and validate JWT token
            try:
                payload = jwt.decode(
                    token,
                    auth_manager._get_jwt_secret(),
                    algorithms=[auth_manager.jwt_algorithm],
                    options={"verify_aud": False}
                )
            except jwt.ExpiredSignatureError:
                raise_api_error(status_code=401, error_code="AUTH_TOKEN_EXPIRED", message="Token has expired")
            except jwt.InvalidTokenError:
                raise_api_error(status_code=401, error_code="AUTH_TOKEN_INVALID", message="Invalid token")
            
            # Check if token is revoked
            if token in auth_manager.revoked_tokens:
                raise_api_error(status_code=401, error_code="AUTH_TOKEN_REVOKED", message="Token has been revoked")
            
            return {
                "user_uuid": payload["user_uuid"],
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": set(payload.get("permissions", [])),
                "token": token
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise_api_error(status_code=401, error_code="AUTH_FAILED", message="Authentication failed")
    
    return verify_token


def create_admin_dependency(auth_manager):
    """
    Factory function to create admin auth dependency.
    Requires admin role or appropriate permissions.
    """
    verify_token = create_auth_dependency(auth_manager)
    
    async def verify_admin(user: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
        roles = user.get("roles", [])
        permissions = user.get("permissions", set())
        
        if "admin" not in roles and "*" not in permissions and "admin.*" not in permissions:
            raise_api_error(status_code=403, error_code="ADMIN_REQUIRED", message="Admin access required")
        
        return user
    
    return verify_admin
