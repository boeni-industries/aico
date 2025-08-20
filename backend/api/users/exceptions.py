"""
User Management API Exceptions

User-specific error handling and custom exceptions.
"""

from fastapi import HTTPException, status
from typing import Optional


class UserNotFoundError(HTTPException):
    """Raised when a requested user is not found"""
    def __init__(self, user_uuid: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with UUID {user_uuid} not found"
        )


class UserAlreadyExistsError(HTTPException):
    """Raised when attempting to create a user that already exists"""
    def __init__(self, identifier: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with identifier {identifier} already exists"
        )


class InvalidCredentialsError(HTTPException):
    """Raised when authentication credentials are invalid"""
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )


class UserAccountLockedError(HTTPException):
    """Raised when user account is locked due to failed attempts"""
    def __init__(self, user_uuid: str):
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            detail=f"User account {user_uuid} is locked due to failed authentication attempts"
        )


class UserInactiveError(HTTPException):
    """Raised when attempting to authenticate with an inactive user"""
    def __init__(self, user_uuid: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account {user_uuid} is inactive"
        )


class InvalidUserDataError(HTTPException):
    """Raised when user data validation fails"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user data: {message}"
        )


class UserServiceError(HTTPException):
    """Raised when user service operations fail"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(
            status_code=status_code,
            detail=f"User service error: {message}"
        )


class PinRequiredError(HTTPException):
    """Raised when PIN is required but not provided"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN is required for this user type"
        )


class PinTooWeakError(HTTPException):
    """Raised when PIN doesn't meet security requirements"""
    def __init__(self, requirements: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PIN doesn't meet requirements: {requirements}"
        )


def handle_user_service_exceptions(func):
    """
    Decorator to handle common user service exceptions and convert them to HTTP exceptions.
    """
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Convert service-level exceptions to HTTP exceptions
            if "not found" in str(e).lower():
                raise UserNotFoundError("unknown")
            elif "already exists" in str(e).lower():
                raise UserAlreadyExistsError("unknown")
            elif "invalid credentials" in str(e).lower():
                raise InvalidCredentialsError()
            elif "locked" in str(e).lower():
                raise UserAccountLockedError("unknown")
            elif "inactive" in str(e).lower():
                raise UserInactiveError("unknown")
            else:
                raise UserServiceError(str(e))
    
    return wrapper
