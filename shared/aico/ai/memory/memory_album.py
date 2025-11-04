"""
Memory Album Store

Manages user-curated memories in user_memories table.
Shared between backend and CLI for consistent memory management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import uuid

from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.core.logging import get_logger

logger = get_logger("shared", "ai.memory.memory_album")


class MemoryAlbumStore:
    """
    Manages user-curated memories in user_memories table.
    Shared between backend and CLI for consistent memory management.
    """
    
    def __init__(self, db_connection: EncryptedLibSQLConnection):
        """
        Initialize MemoryAlbumStore with encrypted database connection.
        
        Args:
            db_connection: Encrypted LibSQL connection (injected via dependency injection)
        """
        self.db = db_connection
    
    async def store_user_curated_fact(
        self,
        user_id: str,
        conversation_id: str,
        message_id: Optional[str],
        content: str,
        fact_type: str,
        category: str,
        content_type: str = "message",
        user_note: Optional[str] = None,
        tags: Optional[List[str]] = None,
        emotional_tone: Optional[str] = None,
        memory_type: str = "fact",
        conversation_title: Optional[str] = None,
        conversation_summary: Optional[str] = None,
        turn_range: Optional[str] = None,
        key_moments: Optional[List[str]] = None,
    ) -> str:
        """
        Store a user-curated fact (Memory Album entry).
        
        Args:
            user_id: User identifier
            conversation_id: Source conversation identifier
            message_id: Source message identifier
            content: The remembered text
            fact_type: Type of fact (identity, preference, relationship, temporal)
            category: Category (personal_info, preferences, relationships, etc.)
            user_note: Optional user annotation
            tags: Optional list of user-defined tags
            emotional_tone: Optional emotional tone (joyful, reflective, etc.)
            memory_type: Type of memory (fact, insight, moment, milestone, wisdom)
        
        Returns:
            fact_id: The ID of the stored fact
        """
        
        fact_id = f"fact_{uuid.uuid4().hex}"
        # Store UTC time with explicit timezone marker
        now = datetime.now(timezone.utc).isoformat()
        
        cursor = self.db.execute(
            """
            INSERT INTO user_memories (
                fact_id, user_id, fact_type, category, confidence,
                is_immutable, valid_from, content, extraction_method,
                source_conversation_id, source_message_id,
                user_note, tags_json, emotional_tone, memory_type,
                content_type, conversation_title, conversation_summary,
                turn_range, key_moments_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact_id,
                user_id,
                fact_type,
                category,
                1.0,  # User-curated = 100% confidence
                False,
                now,
                content,
                "user_curated",  # KEY: Distinguishes from AI-extracted
                conversation_id,
                message_id,
                user_note,
                json.dumps(tags or []),
                emotional_tone,
                memory_type,
                content_type,
                conversation_title,
                conversation_summary,
                turn_range,
                json.dumps(key_moments or []),
                now,
                now,
            )
        )
        cursor.close()
        
        logger.info(f"Stored user-curated fact: {fact_id}", extra={
            "user_id": user_id,
            "conversation_id": conversation_id,
            "category": category,
        })
        
        return fact_id
    
    async def get_user_curated_facts(
        self,
        user_id: str,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        favorites_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve user-curated facts (Memory Album entries).
        
        Args:
            user_id: User identifier
            category: Optional filter by category
            start_date: Optional filter by start date
            end_date: Optional filter by end date
            favorites_only: Only return favorited memories
            limit: Maximum number of results
            offset: Pagination offset
        
        Returns:
            List of user-curated facts as dictionaries
        """
        
        query = """
            SELECT 
                fact_id, content, category, fact_type,
                user_note, tags_json, is_favorite, emotional_tone, memory_type,
                source_conversation_id, source_message_id,
                revisit_count, last_revisited,
                content_type, conversation_title, conversation_summary,
                turn_range, key_moments_json,
                created_at, updated_at
            FROM user_memories
            WHERE user_id = ?
                AND extraction_method = 'user_curated'
        """
        
        params = [user_id]
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date.isoformat())
        
        if favorites_only:
            query += " AND is_favorite = 1"
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self.db.execute(query, tuple(params))
        results = cursor.fetchall()
        
        # Convert rows to dictionaries using column names
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in results]
    
    async def update_fact_metadata(
        self,
        fact_id: str,
        user_id: str,
        user_note: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_favorite: Optional[bool] = None,
    ) -> bool:
        """
        Update Memory Album metadata for a fact.
        
        Args:
            fact_id: Fact identifier
            user_id: User identifier (for verification)
            user_note: Optional new user note
            tags: Optional new tags list
            is_favorite: Optional favorite status
        
        Returns:
            True if update succeeded, False otherwise
        """
        
        updates = []
        params = []
        
        if user_note is not None:
            updates.append("user_note = ?")
            params.append(user_note)
        
        if tags is not None:
            updates.append("tags_json = ?")
            params.append(json.dumps(tags))
        
        if is_favorite is not None:
            updates.append("is_favorite = ?")
            params.append(1 if is_favorite else 0)
        
        if not updates:
            return False
        
        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        
        params.extend([fact_id, user_id])
        
        query = f"""
            UPDATE user_memories
            SET {', '.join(updates)}
            WHERE fact_id = ? AND user_id = ?
        """
        
        cursor = self.db.execute(query, tuple(params))
        rowcount = cursor.rowcount
        cursor.close()
        return rowcount > 0
    
    async def record_revisit(self, fact_id: str, user_id: str) -> bool:
        """
        Increment revisit count when user views a memory.
        
        Args:
            fact_id: Fact identifier
            user_id: User identifier (for verification)
        
        Returns:
            True if update succeeded, False otherwise
        """
        
        cursor = self.db.execute(
            """
            UPDATE user_memories
            SET revisit_count = revisit_count + 1,
                last_revisited = CURRENT_TIMESTAMP
            WHERE fact_id = ? AND user_id = ?
            """,
            (fact_id, user_id)
        )
        cursor.close()
        return True
    
    async def delete_fact(self, fact_id: str, user_id: str) -> bool:
        """
        Delete a user-curated fact.
        
        Args:
            fact_id: Fact identifier
            user_id: User identifier (for verification)
        
        Returns:
            True if deletion succeeded, False otherwise
        """
        
        cursor = self.db.execute(
            """
            DELETE FROM user_memories
            WHERE fact_id = ? AND user_id = ? AND extraction_method = 'user_curated'
            """,
            (fact_id, user_id)
        )
        rowcount = cursor.rowcount
        cursor.close()
        if rowcount > 0:
            logger.info(f"Deleted user-curated fact: {fact_id}", extra={
                "user_id": user_id,
                "fact_id": fact_id,
            })
            return True
        
        return False
