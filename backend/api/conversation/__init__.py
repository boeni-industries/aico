"""
AICO Conversation API

Handles conversation initiation, message processing, and real-time communication
with the conversation engine through the message bus.
"""

from .router import router

__all__ = ["router"]
