"""
Conversation API Exceptions

Custom exception classes for conversation-specific error handling.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class ConversationException(HTTPException):
    """Base exception for conversation API errors"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.conversation_id = conversation_id
        self.user_id = user_id


class ConversationNotFoundException(ConversationException):
    """Raised when a conversation is not found"""
    
    def __init__(self, conversation_id: str, user_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found",
            conversation_id=conversation_id,
            user_id=user_id
        )


class InvalidConversationException(ConversationException):
    """Raised when conversation ID is invalid or malformed"""
    
    def __init__(self, conversation_id: str, reason: str = "Invalid conversation ID format"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid conversation ID '{conversation_id}': {reason}",
            conversation_id=conversation_id
        )


class MessageProcessingException(ConversationException):
    """Raised when message processing fails"""
    
    def __init__(
        self, 
        message: str, 
        conversation_id: Optional[str] = None, 
        user_id: Optional[str] = None,
        processing_error: Optional[str] = None
    ):
        detail = f"Failed to process message: {processing_error or 'Unknown error'}"
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            conversation_id=conversation_id,
            user_id=user_id
        )
        self.original_message = message
        self.processing_error = processing_error


class ConversationTimeoutException(ConversationException):
    """Raised when conversation processing times out"""
    
    def __init__(self, conversation_id: str, timeout_seconds: int, user_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Conversation processing timed out after {timeout_seconds} seconds",
            conversation_id=conversation_id,
            user_id=user_id
        )
        self.timeout_seconds = timeout_seconds


class MessageTooLongException(ConversationException):
    """Raised when message exceeds maximum length"""
    
    def __init__(self, message_length: int, max_length: int = 10000):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Message too long ({message_length} characters). Maximum allowed: {max_length}"
        )
        self.message_length = message_length
        self.max_length = max_length


class ConversationRateLimitException(ConversationException):
    """Raised when user exceeds conversation rate limits"""
    
    def __init__(self, user_id: str, retry_after_seconds: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many conversation requests. Try again in {retry_after_seconds} seconds",
            user_id=user_id,
            headers={"Retry-After": str(retry_after_seconds)}
        )
        self.retry_after_seconds = retry_after_seconds


class WebSocketAuthenticationException(ConversationException):
    """Raised when WebSocket authentication fails"""
    
    def __init__(self, reason: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"WebSocket authentication failed: {reason}"
        )


class MessageBusConnectionException(ConversationException):
    """Raised when message bus connection fails"""
    
    def __init__(self, error_details: str, conversation_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Message bus connection failed: {error_details}",
            conversation_id=conversation_id
        )
        self.error_details = error_details


class ConversationEngineException(ConversationException):
    """Raised when conversation engine encounters an error"""
    
    def __init__(
        self, 
        engine_error: str, 
        conversation_id: Optional[str] = None, 
        user_id: Optional[str] = None
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversation engine error: {engine_error}",
            conversation_id=conversation_id,
            user_id=user_id
        )
        self.engine_error = engine_error


class InvalidMessageTypeException(ConversationException):
    """Raised when an invalid message type is provided"""
    
    def __init__(self, message_type: str, valid_types: list):
        valid_types_str = ", ".join(valid_types)
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid message type '{message_type}'. Valid types: {valid_types_str}"
        )
        self.message_type = message_type
        self.valid_types = valid_types


# ConversationStateException removed - no explicit state management with semantic memory


class WebSocketConnectionException(ConversationException):
    """Raised when WebSocket connection encounters an error"""
    
    def __init__(self, connection_error: str, conversation_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"WebSocket connection error: {connection_error}",
            conversation_id=conversation_id
        )
        self.connection_error = connection_error
