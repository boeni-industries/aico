"""
Feedback Event Store

Manages feedback events in the feedback_events table.
Shared between backend and CLI for consistent feedback tracking.
"""

from typing import Optional, Dict, Any, List
import json
import uuid
import time

from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.core.logging import get_logger
from .types import FeedbackEventType

logger = get_logger("shared", "feedback.events")


class FeedbackEventStore:
    """
    Manages feedback events in feedback_events table.
    Shared between backend and CLI for consistent feedback tracking.
    """
    
    def __init__(self, db_connection: EncryptedLibSQLConnection):
        """
        Initialize FeedbackEventStore with encrypted database connection.
        
        Args:
            db_connection: Encrypted LibSQL connection (injected via dependency injection)
        """
        self.db = db_connection
    
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
        
        event_id = f"fb_{uuid.uuid4().hex}"
        
        await self.db.execute(
            """
            INSERT INTO feedback_events (
                id, user_uuid, conversation_id, message_id,
                event_type, event_category, payload, timestamp, is_sensitive
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                user_uuid,
                conversation_id,
                message_id,
                event_type.value,
                event_category,
                json.dumps(payload),
                int(time.time()),
                1 if is_sensitive else 0,
            )
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
        
        query = "SELECT * FROM feedback_events WHERE user_uuid = ?"
        params = [user_uuid]
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        if event_category:
            query += " AND event_category = ?"
            params.append(event_category)
        
        if conversation_id:
            query += " AND conversation_id = ?"
            params.append(conversation_id)
        
        if start_timestamp:
            query += " AND timestamp >= ?"
            params.append(start_timestamp)
        
        if end_timestamp:
            query += " AND timestamp <= ?"
            params.append(end_timestamp)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        results = await self.db.execute(query, tuple(params))
        
        return [dict(row) for row in results]
