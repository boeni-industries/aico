"""
Feedback Event Store

Manages feedback events in the feedback_events table.
Shared between backend and CLI for consistent feedback tracking.
"""

from typing import Optional, Dict, Any, List
import json
import uuid
import time

from aico.core.logging import get_logger
from .types import FeedbackEventType

logger = get_logger("shared.feedback.events")


class FeedbackEventStore:
    """
    Manages feedback events in feedback_events table.
    Shared between backend and CLI for consistent feedback tracking.
    Uses UnitOfWork pattern for PostgreSQL access.
    """
    
    def __init__(self):
        """
        Initialize FeedbackEventStore.
        No longer takes db_connection - uses UnitOfWork pattern.
        """
        pass
    
    async def record_event(
        self,
        user_uuid: str,
        conversation_id: str,
        event_type: FeedbackEventType,
        event_category: str,
        payload: Dict[str, Any],
        message_id: Optional[str] = None,
        is_sensitive: bool = False,
    ) -> str:
        """
        Record a feedback event (append-only).
        
        Args:
            user_uuid: User identifier
            conversation_id: Conversation identifier (user_uuid_timestamp format)
            event_type: Type of feedback event (signal, action, rating, survey)
            event_category: Specific category within event type
            payload: JSON-serializable event data
            message_id: Optional message identifier for message-level feedback
            is_sensitive: Whether event contains sensitive data (exclude from federation)
        
        Returns:
            event_id: The ID of the recorded event
        """
        
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        
        event_id = f"fb_{uuid.uuid4().hex}"
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            # Note: feedback_events repository would need to be created
            # For now, using direct SQL via asyncpg connection as allowed for admin/infra
            from aico.data.postgres.connection import get_connection
            async with get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO feedback_events (
                        id, user_uuid, conversation_id, message_id,
                        event_type, event_category, payload, timestamp, is_sensitive
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    event_id,
                    user_uuid,
                    conversation_id,
                    message_id,
                    event_type.value,
                    event_category,
                    json.dumps(payload),
                    int(time.time()),
                    is_sensitive,
                )
        
        logger.info(f"Recorded feedback event: {event_type.value}/{event_category}", extra={
            "event_id": event_id,
            "user_uuid": user_uuid,
            "conversation_id": conversation_id,
        })
        
        return event_id
    
    async def get_events(
        self,
        user_uuid: str,
        event_type: Optional[FeedbackEventType] = None,
        event_category: Optional[str] = None,
        conversation_id: Optional[str] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Query feedback events with filters.
        
        Args:
            user_uuid: User identifier
            event_type: Optional filter by event type
            event_category: Optional filter by event category
            conversation_id: Optional filter by conversation
            start_timestamp: Optional filter by start time (unix timestamp)
            end_timestamp: Optional filter by end time (unix timestamp)
            limit: Maximum number of results
            offset: Pagination offset
        
        Returns:
            List of feedback events as dictionaries
        """
        
        from aico.data.postgres.connection import get_connection
        
        query = "SELECT * FROM feedback_events WHERE user_uuid = $1"
        params = [user_uuid]
        param_idx = 2
        
        if event_type:
            query += f" AND event_type = ${param_idx}"
            params.append(event_type.value)
            param_idx += 1
        
        if event_category:
            query += f" AND event_category = ${param_idx}"
            params.append(event_category)
            param_idx += 1
        
        if conversation_id:
            query += f" AND conversation_id = ${param_idx}"
            params.append(conversation_id)
            param_idx += 1
        
        if start_timestamp:
            query += f" AND timestamp >= ${param_idx}"
            params.append(start_timestamp)
            param_idx += 1
        
        if end_timestamp:
            query += f" AND timestamp <= ${param_idx}"
            params.append(end_timestamp)
            param_idx += 1
        
        query += f" ORDER BY timestamp DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([limit, offset])
        
        async with get_connection() as conn:
            rows = await conn.fetch(query, *params)
        
        return [dict(row) for row in rows]
