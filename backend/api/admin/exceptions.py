"""
Admin Management API Exceptions

Admin-specific error handling and custom exceptions.
"""

from fastapi import HTTPException, status


class AdminAccessDeniedError(HTTPException):
    """Raised when non-admin user attempts admin operations"""
    def __init__(self, operation: str = "admin operation"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin access required for {operation}"
        )


class SessionNotFoundError(HTTPException):
    """Raised when a requested session is not found"""
    def __init__(self, session_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )


class TokenAlreadyRevokedError(HTTPException):
    """Raised when attempting to revoke an already revoked token"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Token has already been revoked"
        )


class InvalidTokenError(HTTPException):
    """Raised when token format is invalid"""
    def __init__(self, reason: str = "Invalid token format"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason
        )


class GatewayServiceError(HTTPException):
    """Raised when gateway service operations fail"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(
            status_code=status_code,
            detail=f"Gateway service error: {message}"
        )


class SecurityOperationError(HTTPException):
    """Raised when security operations fail"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(
            status_code=status_code,
            detail=f"Security operation failed: {message}"
        )


class RoutingConfigurationError(HTTPException):
    """Raised when routing configuration operations fail"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Routing configuration error: {message}"
        )


class IpAlreadyBlockedError(HTTPException):
    """Raised when attempting to block an already blocked IP"""
    def __init__(self, ip: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"IP address {ip} is already blocked"
        )


class IpNotBlockedError(HTTPException):
    """Raised when attempting to unblock an IP that isn't blocked"""
    def __init__(self, ip: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IP address {ip} is not currently blocked"
        )


def handle_admin_service_exceptions(func):
    """
    Decorator to handle common admin service exceptions and convert them to HTTP exceptions.
    """
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            # Convert service-level exceptions to HTTP exceptions
            error_msg = str(e).lower()
            
            if "not found" in error_msg:
                if "session" in error_msg:
                    raise SessionNotFoundError("unknown")
                else:
                    raise HTTPException(status_code=404, detail=str(e))
            elif "access denied" in error_msg or "forbidden" in error_msg:
                raise AdminAccessDeniedError()
            elif "already exists" in error_msg or "already blocked" in error_msg:
                raise HTTPException(status_code=409, detail=str(e))
            elif "invalid" in error_msg:
                raise HTTPException(status_code=400, detail=str(e))
            else:
                raise GatewayServiceError(str(e))
    
    return wrapper
