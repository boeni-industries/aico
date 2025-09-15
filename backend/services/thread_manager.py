"""
Thread Manager Service - Minimal Implementation

Provides automatic thread resolution with simple time-based heuristics.
Future enhancements will add semantic analysis, temporal patterns, and user behavior learning.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import uuid
from aico.core.logging import get_logger

logger = get_logger("backend", "services.thread_manager")


@dataclass
class ThreadResolution:
    """Result of thread resolution process"""
    thread_id: str
    action: str  # "continued", "created", "reactivated"
    confidence: float
    reasoning: str
    created_at: Optional[datetime] = None


@dataclass
class ThreadInfo:
    """Basic thread information for resolution"""
    thread_id: str
    last_activity: datetime
    message_count: int
    status: str  # "active", "dormant", "archived"


class ThreadManager:
    """
    Minimal ThreadManager implementation with simple time-based heuristics.
    
    Current Logic:
    - Continue most recent thread if < 2 hours old
    - Create new thread otherwise
    - Simple dormancy detection
    
    Future Enhancements:
    - Semantic similarity analysis
    - User behavior pattern learning
    - Temporal context analysis
    - Intent classification
    """
    
    def __init__(self, dormancy_threshold_hours: int = 2):
        self.dormancy_threshold = timedelta(hours=dormancy_threshold_hours)
        self.max_thread_age_days = 30  # Archive threads older than 30 days
        
    async def resolve_thread_for_message(
        self, 
        user_id: str, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ThreadResolution:
        """
        Resolve which thread should handle the incoming message.
        
        Minimal implementation using time-based heuristics:
        1. Get user's recent threads
        2. Continue most recent if within dormancy threshold
        3. Otherwise create new thread
        """
        logger.info(f"[THREAD_MANAGER] ENTRY: resolve_thread_for_message called for user {user_id}")
        logger.info(f"[THREAD_MANAGER] Message preview: '{message[:50]}...'")
        logger.info(f"[THREAD_MANAGER] Context: {context}")
        
        try:
            
            # Get user's recent threads
            logger.info(f"[THREAD_MANAGER] Calling _get_user_recent_threads for user {user_id}")
            recent_threads = await self._get_user_recent_threads(user_id)
            logger.info(f"[THREAD_MANAGER] Found {len(recent_threads)} recent threads for user {user_id}")
            
            if recent_threads:
                for i, thread in enumerate(recent_threads):
                    logger.info(f"[THREAD_MANAGER] Thread {i}: {thread.thread_id}, last_activity: {thread.last_activity}")
            
            if not recent_threads:
                # No existing threads - create new one
                logger.info(f"[THREAD_MANAGER] No recent threads found, creating new thread")
                return await self._create_new_thread(user_id, message, context)
            
            # Find most recent active thread
            logger.info(f"[THREAD_MANAGER] Finding most recent thread from {len(recent_threads)} candidates")
            most_recent = max(recent_threads, key=lambda t: t.last_activity)
            time_since_activity = datetime.utcnow() - most_recent.last_activity
            logger.info(f"[THREAD_MANAGER] Most recent thread: {most_recent.thread_id}, time since activity: {time_since_activity}")
            
            if time_since_activity <= self.dormancy_threshold:
                # Continue recent thread
                logger.info(f"[THREAD_MANAGER] CONTINUING thread {most_recent.thread_id} (last activity {time_since_activity.total_seconds()//60:.0f}m ago)")
                resolution = ThreadResolution(
                    thread_id=most_recent.thread_id,
                    action="continued",
                    confidence=0.8,
                    reasoning=f"Continuing recent thread (last activity {time_since_activity.total_seconds()//60:.0f}m ago)"
                )
                logger.info(f"[THREAD_MANAGER] Returning resolution: {resolution.action} - {resolution.thread_id}")
                return resolution
            else:
                # Create new thread - too much time has passed
                logger.info(f"[THREAD_MANAGER] Time threshold exceeded ({time_since_activity} > {self.dormancy_threshold}), creating new thread")
                return await self._create_new_thread(
                    user_id, 
                    message, 
                    context,
                    reasoning=f"Creating new thread (last activity {time_since_activity.total_seconds()//3600:.1f}h ago)"
                )
                
        except Exception as e:
            logger.error(f"[THREAD_MANAGER] EXCEPTION in resolve_thread_for_message for user {user_id}: {e}")
            logger.error(f"[THREAD_MANAGER] Exception type: {type(e).__name__}")
            logger.error(f"[THREAD_MANAGER] Exception message: {str(e)}")
            import traceback
            logger.error(f"[THREAD_MANAGER] Full traceback: {traceback.format_exc()}")
            logger.error(f"[THREAD_MANAGER] FALLING BACK TO NEW THREAD - CONTEXT WILL BE LOST")
            logger.error(f"[THREAD_MANAGER] THIS IS WHY CONVERSATIONS DON'T CONTINUE - FIX THIS IMMEDIATELY")
            # Fallback: create new thread
            return await self._create_new_thread(
                user_id, 
                message, 
                context,
                reasoning="Fallback due to resolution error"
            )
    
    async def _get_user_recent_threads(self, user_id: str) -> List[ThreadInfo]:
        """
        Get user's recent threads for resolution analysis.
        
        Query LMDB working memory to find recent threads for the user.
        """
        logger.info(f"[THREAD_MANAGER] _get_user_recent_threads ENTRY for user {user_id}")
        
        try:
            # Use the global shared working memory store instead of creating a new one
            # This ensures we see the same data that ConversationEngine is writing to
            import sys
            import os
            
            # Add the project root to Python path if not already there
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from aico.ai import ai_registry
            
            logger.info(f"[THREAD_MANAGER] Getting shared memory processor from ai_registry")
            
            # Get the shared memory processor that ConversationEngine uses
            memory_processor = ai_registry.get("memory")
            if not memory_processor:
                raise RuntimeError("Memory processor not found in ai_registry")
            
            # Ensure memory processor is initialized
            if not memory_processor._initialized:
                logger.info(f"[THREAD_MANAGER] Memory processor not initialized, initializing now")
                # Trigger initialization by calling process() with dummy data
                dummy_request = {
                    "thread_id": "dummy",
                    "user_id": "dummy", 
                    "message": "dummy",
                    "message_type": "user_input"
                }
                await memory_processor.process(dummy_request)
            
            working_store = memory_processor._working_store
            if not working_store:
                raise RuntimeError("WorkingMemoryStore not initialized in memory processor")
            
            logger.info(f"[THREAD_MANAGER] Using shared WorkingMemoryStore instance")
            
            # Get recent messages for this user from LMDB
            logger.info(f"[THREAD_MANAGER] Calling _get_recent_user_messages for user {user_id}")
            recent_messages = await working_store._get_recent_user_messages(user_id, hours=24)
            logger.info(f"[THREAD_MANAGER] Retrieved {len(recent_messages)} recent messages for user {user_id}")
            
            # Group messages by thread_id and find most recent activity per thread
            logger.info(f"[THREAD_MANAGER] Processing {len(recent_messages)} messages to find thread activities")
            thread_activities = {}
            for i, msg_data in enumerate(recent_messages):
                thread_id = msg_data.get('thread_id')
                timestamp_str = msg_data.get('timestamp')
                logger.debug(f"[THREAD_MANAGER] Message {i}: thread_id={thread_id}, timestamp={timestamp_str}")
                
                if thread_id and timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if thread_id not in thread_activities or timestamp > thread_activities[thread_id]:
                            thread_activities[thread_id] = timestamp
                            logger.debug(f"[THREAD_MANAGER] Updated thread {thread_id} activity to {timestamp}")
                    except ValueError as ve:
                        logger.warning(f"[THREAD_MANAGER] Invalid timestamp format: {timestamp_str} - {ve}")
                else:
                    logger.warning(f"[THREAD_MANAGER] Message {i} missing thread_id or timestamp")
            
            # Convert to ThreadInfo objects
            user_threads = []
            for thread_id, last_activity in thread_activities.items():
                user_threads.append(ThreadInfo(
                    thread_id=thread_id,
                    user_id=user_id,
                    last_activity=last_activity,
                    message_count=1  # Simplified for now
                ))
            
            return user_threads
            
        except Exception as e:
            logger.error(f"[THREAD_MANAGER] ❌ CRITICAL FAILURE in _get_user_recent_threads for user {user_id}: {e}")
            logger.error(f"[THREAD_MANAGER] ❌ Exception type: {type(e).__name__}")
            logger.error(f"[THREAD_MANAGER] ❌ Exception message: {str(e)}")
            import traceback
            logger.error(f"[THREAD_MANAGER] ❌ Full traceback: {traceback.format_exc()}")
            logger.error(f"[THREAD_MANAGER] ❌ RETURNING EMPTY LIST - THREAD RESOLUTION WILL FAIL")
            logger.error(f"[THREAD_MANAGER] ❌ THIS IS WHY CONTEXT IS BROKEN - FIX THIS IMMEDIATELY")
            return []
    
    async def _create_new_thread(
        self, 
        user_id: str, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        reasoning: str = "New conversation"
    ) -> ThreadResolution:
        """
        Create a new conversation thread.
        """
        thread_id = str(uuid.uuid4())
        logger.info(f"[THREAD_MANAGER] CREATING new thread {thread_id} for user {user_id}")
        logger.info(f"[THREAD_MANAGER] Reasoning: {reasoning}")
        
        resolution = ThreadResolution(
            thread_id=thread_id,
            action="created",
            confidence=1.0,
            reasoning=reasoning
        )
        
        logger.info(f"[THREAD_MANAGER] New thread resolution: {resolution.action} - {resolution.thread_id}")
        return resolution
    
    async def create_explicit_thread(
        self, 
        user_id: str, 
        thread_type: str = "conversation",
        initial_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ThreadResolution:
        """
        Create an explicit new thread (bypasses automatic resolution).
        Used by the separated /threads endpoint.
        """
        thread_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        # TODO: Persist thread to database with metadata
        logger.info(f"Created explicit thread {thread_id} (type: {thread_type}) for user {user_id}")
        
        return ThreadResolution(
            thread_id=thread_id,
            action="created",
            confidence=1.0,
            reasoning="Explicitly created thread",
            created_at=created_at
        )
    
    async def get_thread_info(self, thread_id: str, user_id: str) -> Optional[ThreadInfo]:
        """Get thread information for status queries"""
        # TODO: Implement actual database query
        # Mock implementation - return basic thread info for testing
        return ThreadInfo(
            thread_id=thread_id,
            last_activity=datetime.utcnow() - timedelta(minutes=5),
            message_count=1,
            status="active"
        )
    
    async def validate_thread_access(self, thread_id: str, user_id: str) -> bool:
        """Validate that user has access to the specified thread"""
        # TODO: Implement actual access validation
        # For now, assume all access is valid
        return True


# Dependency injection function for FastAPI
async def get_thread_manager() -> ThreadManager:
    """FastAPI dependency for ThreadManager"""
    return ThreadManager()
