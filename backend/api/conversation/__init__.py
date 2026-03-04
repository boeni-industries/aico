"""
AICO Conversation API

Handles conversation initiation, message processing, and real-time communication
with the conversation engine through the message bus.
"""

from .router import router
from .catchup import router as catchup_router

# Include catch-up routes in main router
router.include_router(catchup_router, tags=["conversation-catchup"])

__all__ = ["router"]
