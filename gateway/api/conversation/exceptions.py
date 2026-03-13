from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, status


class ConversationException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.conversation_id = conversation_id
        self.user_id = user_id


class ConversationNotFoundException(ConversationException):
    def __init__(self, conversation_id: str, user_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found",
            conversation_id=conversation_id,
            user_id=user_id,
        )


class InvalidConversationException(ConversationException):
    def __init__(self, conversation_id: str, reason: str = "Invalid conversation ID format"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid conversation ID '{conversation_id}': {reason}",
            conversation_id=conversation_id,
        )


class MessageProcessingException(ConversationException):
    def __init__(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        processing_error: Optional[str] = None,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {processing_error or 'Unknown error'}",
            conversation_id=conversation_id,
            user_id=user_id,
        )
        self.original_message = message
        self.processing_error = processing_error


class ConversationTimeoutException(ConversationException):
    def __init__(
        self,
        conversation_id: str,
        timeout_seconds: int,
        user_id: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Conversation processing timed out after {timeout_seconds} seconds",
            conversation_id=conversation_id,
            user_id=user_id,
            headers=headers,
        )
        self.timeout_seconds = timeout_seconds


class WebSocketAuthenticationException(ConversationException):
    def __init__(self, reason: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"WebSocket authentication failed: {reason}",
        )


class MessageBusConnectionException(ConversationException):
    def __init__(self, error_details: str, conversation_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Message bus connection failed: {error_details}",
            conversation_id=conversation_id,
        )
        self.error_details = error_details
