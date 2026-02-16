"""
AICO Working Memory Store

This module provides high-performance short-term memory storage for active conversation sessions,
managing temporary context, session state, and thread-specific information with automatic expiration.

Core Functionality:
- Session context storage: Maintains active conversation state and user session data
- Thread context management: Stores recent messages and conversation flow within threads
- Temporary data caching: High-speed access to frequently used conversation elements
- Automatic expiration: Time-based cleanup of stale session data and inactive threads
- Memory pressure handling: Intelligent eviction policies when memory limits are reached
- Real-time updates: Immediate storage and retrieval for active conversation processing

Storage Architecture:
- Key-value storage optimized for conversation data patterns
- Thread-safe concurrent access for multi-user conversation handling
- Memory-mapped files for optimal performance on conversation-heavy workloads
- Configurable retention policies based on session activity and thread importance

Technologies & Dependencies:
- LMDB (Lightning Memory-Mapped Database): High-performance, memory-mapped key-value store.
  Rationale: Offers performance competitive with RocksDB, especially for read-heavy workloads, but with a much simpler, dependency-free installation, making it ideal for user deployment.
  Python Integration: The `lmdb` package provides pre-compiled binaries for all major platforms.
  Installation: `uv add lmdb`
  Platform Support: Linux, macOS, and Windows are fully supported out-of-the-box.
- asyncio: Asynchronous I/O operations for non-blocking memory access
- dataclasses: Structured representation of session and thread context data
- datetime: Temporal operations for expiration policies and session timing
- json: Serialization of complex conversation context objects
- collections: Python standard library for efficient session data structures
- AICO ConfigurationManager: Database paths, retention policies, and performance tuning
- AICO Logging: Structured logging for memory operations and performance monitoring

Performance Characteristics:
- Sub-millisecond read/write latency for active session data
- Automatic background compaction to maintain optimal storage efficiency
- Configurable write buffers and cache sizes based on conversation volume
- Memory usage monitoring and automatic cleanup of expired sessions
"""

import lmdb
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.data.lmdb import get_lmdb_path, initialize_lmdb_env
from aico.ai.memory.temporal import TemporalMetadata
from .metrics import track_query

logger = get_logger("shared.ai.memory.working")


class WorkingMemoryStore:
    """
    Fast, ephemeral storage for active conversation context using LMDB.
    """

    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self.env = None
        self.dbs = {}
        self._initialized = False
        self._db_path = get_lmdb_path(self.config)
        self._named_dbs = self.config.get("memory.working.named_databases", [])
        self._ttl_seconds = self.config.get("memory.working.ttl_seconds", 2592000)  # Default: 30 days (fallback if config missing)

    async def initialize(self) -> None:
        """Initialize LMDB environment and open named databases."""
        if self._initialized:
            return

        logger.debug(f"[DEBUG] WorkingMemoryStore: Initializing at {self._db_path}")
        try:
            initialize_lmdb_env(self.config)
            self.env = lmdb.open(str(self._db_path), max_dbs=len(self._named_dbs) + 1)

            # Open handles to named databases (create if they don't exist)
            for db_name in self._named_dbs:
                self.dbs[db_name] = self.env.open_db(db_name.encode('utf-8'), create=True)

            self._initialized = True
            logger.debug(f"[DEBUG] WorkingMemoryStore: Initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize working memory store: {e}")
            raise

    async def store_message(self, conversation_id: str, message: Dict[str, Any]) -> bool:
        """Store a message in the working memory store by conversation_id."""
        if not self._initialized:
            await self.initialize()

        logger.info(f"💾 [WORKING_MEMORY] Storing message for conversation {conversation_id}")
        logger.info(f"💾 [WORKING_MEMORY] Message type: {message.get('message_type', 'unknown')}")

        with track_query("working_memory_store", memory_layer="working") as tracker:
            try:
                db = self.dbs.get("session_memory")
                if db is None:
                    raise ConnectionError("session_memory database not open.")

                timestamp = datetime.utcnow()
                # Use conversation_id as primary key with timestamp for ordering
                key_str = f"{conversation_id}:{timestamp.isoformat()}Z"
                key = key_str.encode('utf-8')

                # Convert datetime objects to ISO format strings for JSON serialization
                serializable_message = {}
                for msg_key, msg_value in message.items():
                    if isinstance(msg_value, datetime):
                        serializable_message[msg_key] = msg_value.isoformat() + "Z"
                    else:
                        serializable_message[msg_key] = msg_value
                
                # Create temporal metadata for this message
                temporal_meta = TemporalMetadata(
                    created_at=timestamp,
                    last_updated=timestamp,
                    last_accessed=timestamp,
                    access_count=0,
                    confidence=1.0,
                    version=1
                )
                
                storage_data = {
                    **serializable_message,
                    "_stored_at": timestamp.isoformat() + "Z",
                    "_expires_at": (timestamp + timedelta(seconds=self._ttl_seconds)).isoformat() + "Z",
                    "temporal_metadata": temporal_meta.to_dict()
                }

                with self.env.begin(write=True, db=db) as txn:
                    txn.put(key, json.dumps(storage_data).encode('utf-8'))

                logger.info(f"💾 [WORKING_MEMORY] ✅ Message stored successfully")
                tracker.set_results_count(1)
                tracker.set_success(True)
                return True

            except Exception as e:
                logger.error(f"💾 [WORKING_MEMORY] ❌ Failed to store message: {e}")
                tracker.set_success(False)
                return False

    async def retrieve_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent messages for a given conversation_id."""
        if not self._initialized:
            await self.initialize()

        logger.info(f"🔍 [WORKING_MEMORY] Retrieving history for conversation {conversation_id} (limit: {limit})")

        with track_query("working_memory_retrieve", memory_layer="working") as tracker:
            history = []
            try:
                db = self.dbs.get("session_memory")
                if db is None:
                    raise ConnectionError("session_memory database not open.")

                logger.debug(f"[DEBUG] WorkingMemoryStore: Retrieving history for conversation {conversation_id}.")
                with self.env.begin(db=db) as txn:
                    cursor = txn.cursor()
                    # Seek to the start of the desired conversation
                    prefix = f"{conversation_id}:".encode('utf-8')
                    if cursor.set_range(prefix):
                        for key, value in cursor:
                            if not key.startswith(prefix):
                                break  # Moved past the desired conversation

                            data = json.loads(value.decode('utf-8'))
                            if self._is_expired(data):
                                # Optional: could delete expired entries here in a separate write txn
                                continue

                            # Update temporal metadata on access
                            self._update_temporal_access(data)
                            history.append(data)
                            # Don't break early - collect ALL messages for this conversation

                # CRITICAL: Sort by timestamp FIRST, then limit
                # LMDB iterates in lexicographical key order, not timestamp order
                history.sort(key=lambda x: x.get("_stored_at"), reverse=True)
                
                # Now take the most recent N messages after sorting
                history = history[:limit]
                
                logger.info(f"🔍 [WORKING_MEMORY] ✅ Retrieved {len(history)} messages from conversation history")
                tracker.set_results_count(len(history))
                tracker.set_success(True)
                return history

            except Exception as e:
                logger.error(f"🔍 [WORKING_MEMORY] ❌ Failed to retrieve conversation history: {e}")
                tracker.set_success(False)
                return []

    async def retrieve_user_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent messages for a given user_id across all conversations."""
        if not self._initialized:
            await self.initialize()

        logger.info(f"🔍 [WORKING_MEMORY] Retrieving history for user {user_id} (limit: {limit})")

        history = []
        try:
            db = self.dbs.get("session_memory")
            if db is None:
                raise ConnectionError("session_memory database not open.")

            logger.debug(f"[DEBUG] WorkingMemoryStore: Retrieving history for user {user_id}.")
            with self.env.begin(db=db) as txn:
                cursor = txn.cursor()
                # Iterate through all keys to find messages for this user
                # CRITICAL: Collect ALL messages first, then sort, then limit
                for key, value in cursor:
                    data = json.loads(value.decode('utf-8'))
                    
                    # Check if message belongs to this user
                    if data.get('user_id') == user_id:
                        if self._is_expired(data):
                            continue

                        history.append(data)
                        # Don't break early - collect ALL messages for proper sorting

            # Sort by timestamp (newest first) THEN limit
            history.sort(key=lambda x: x.get("_stored_at"), reverse=True)
            history = history[:limit]  # Take only the most recent N messages after sorting
            
            logger.info(f"🔍 [WORKING_MEMORY] ✅ Retrieved {len(history)} messages from user history")
            return history

        except Exception as e:
            logger.error(f"🔍 [WORKING_MEMORY] ❌ Failed to retrieve user history: {e}")
            return []

    async def _get_recent_user_messages(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent messages for a user across all threads within the specified time window."""
        if not self._initialized:
            await self.initialize()

        recent_messages = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        logger.debug(f"Cutoff time for recent messages: {cutoff_time} UTC")
        
        try:
            db = self.dbs.get("session_memory")
            if db is None:
                raise ConnectionError("session_memory database not open.")

            with self.env.begin(db=db) as txn:
                cursor = txn.cursor()
                for key, value in cursor:
                    try:
                        data = json.loads(value.decode('utf-8'))
                        
                        # Check if message belongs to this user
                        if data.get('user_id') == user_id:
                            # Check if message is within time window
                            timestamp_str = data.get('timestamp')
                            if timestamp_str:
                                # Parse timestamp as UTC (remove timezone info for consistent comparison)
                                if timestamp_str.endswith('Z'):
                                    timestamp = datetime.fromisoformat(timestamp_str[:-1])
                                elif '+' in timestamp_str or timestamp_str.endswith('+00:00'):
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('+00:00', ''))
                                else:
                                    # Assume UTC if no timezone info
                                    timestamp = datetime.fromisoformat(timestamp_str)
                                
                                logger.debug(f"Message timestamp: {timestamp} UTC, cutoff: {cutoff_time} UTC")
                                if timestamp >= cutoff_time:
                                    recent_messages.append(data)
                                    logger.debug(f"Message included (within {hours}h window)")
                                else:
                                    logger.debug(f"Message excluded (outside {hours}h window)")
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Failed to parse message data: {e}")
                        continue

            logger.debug(f"Found {len(recent_messages)} recent messages for user {user_id} within {hours}h window")
            return recent_messages

        except Exception as e:
            logger.error(f"Failed to get recent user messages: {e}")
            return []

    async def cleanup_expired(self) -> int:
        """
        Delete expired entries from LMDB.
        
        Returns:
            Number of entries deleted
        """
        if not self._initialized:
            await self.initialize()
        
        deleted_count = 0
        
        try:
            # Collect expired keys first (can't delete while iterating)
            expired_keys = []
            total_checked = 0
            
            session_db = self.dbs.get("session_memory")
            if session_db is None:
                logger.warning("session_memory database not found")
                return 0
            
            with self.env.begin(db=session_db) as txn:
                cursor = txn.cursor()
                for key, value in cursor:
                    total_checked += 1
                    try:
                        data = json.loads(value.decode('utf-8'))
                        if self._is_expired(data):
                            expired_keys.append(key)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Invalid data, mark for deletion
                        expired_keys.append(key)
            
            logger.info(f"Checked {total_checked} entries, found {len(expired_keys)} expired")
            
            # Delete expired entries in a write transaction
            if expired_keys:
                with self.env.begin(db=session_db, write=True) as txn:
                    for key in expired_keys:
                        txn.delete(key)
                        deleted_count += 1
                
                logger.info(f"Cleaned up {deleted_count} expired entries from working memory")
            else:
                logger.debug("No expired entries to clean up")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired entries: {e}")
            return 0
    
    async def cleanup(self) -> None:
        """Close the LMDB environment."""
        if self.env:
            self.env.close()
            self.env = None
            self._initialized = False
            logger.info("Working memory store cleaned up.")

    def _is_expired(self, data: Dict[str, Any]) -> bool:
        """Check if a data entry has expired."""
        expires_at_str = data.get("_expires_at")
        if not expires_at_str:
            return False
        
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', ''))
            return datetime.utcnow() > expires_at
        except (ValueError, AttributeError, TypeError):
            return False
    
    def _update_temporal_access(self, data: Dict[str, Any]) -> None:
        """Update temporal metadata to record access."""
        temporal_meta_dict = data.get("temporal_metadata")
        if temporal_meta_dict:
            try:
                temporal_meta = TemporalMetadata.from_dict(temporal_meta_dict)
                temporal_meta.record_access()
                data["temporal_metadata"] = temporal_meta.to_dict()
            except Exception as e:
                logger.debug(f"Failed to update temporal metadata: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get working memory statistics."""
        if not self._initialized:
            await self.initialize()
        
        try:
            session_db = self.dbs.get("session_memory")
            if session_db is None:
                return {
                    'active_items': 0,
                    'capacity': 10000,
                    'utilization_percent': 0.0,
                    'ttl_utilization_percent': 0.0,
                    'eviction_rate_per_min': 0.0,
                    'recent_activity': []
                }
            
            # Count active (non-expired) items and collect activity
            active_items = 0
            expired_items = 0
            recent_activity = []
            ttl_sum = 0.0
            ttl_count = 0
            
            # Collect all items first for proper sorting
            all_items = []
            with self.env.begin(db=session_db) as txn:
                cursor = txn.cursor()
                for key, value in cursor:
                    try:
                        data = json.loads(value.decode('utf-8'))
                        key_str = key.decode('utf-8')
                        stored_at = data.get('_stored_at', 'unknown')
                        expires_at = data.get('_expires_at')
                        
                        if self._is_expired(data):
                            expired_items += 1
                        else:
                            active_items += 1
                            
                            # Calculate TTL utilization for this item
                            if stored_at != 'unknown' and expires_at:
                                try:
                                    stored_time = datetime.fromisoformat(stored_at.rstrip('Z'))
                                    expires_time = datetime.fromisoformat(expires_at.rstrip('Z'))
                                    now = datetime.utcnow()
                                    total_ttl = (expires_time - stored_time).total_seconds()
                                    remaining_ttl = (expires_time - now).total_seconds()
                                    if total_ttl > 0:
                                        ttl_used = ((total_ttl - remaining_ttl) / total_ttl) * 100
                                        ttl_sum += ttl_used
                                        ttl_count += 1
                                except:
                                    pass
                            
                            # Extract conversation_id and message info
                            conv_id = key_str.split(':')[0]
                            message_role = data.get('role', 'unknown')
                            # Return full content - frontend will handle truncation
                            message_preview = data.get('content', '') if isinstance(data.get('content'), str) else ''
                            
                            all_items.append({
                                'key_str': key_str,
                                'stored_at': stored_at,
                                'conv_id': conv_id,
                                'role': message_role,
                                'preview': message_preview
                            })
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
            
            # Sort by timestamp (most recent first) and take last 10
            all_items.sort(key=lambda x: x['stored_at'], reverse=True)
            for item in all_items[:10]:
                recent_activity.append({
                    'id': item['key_str'],
                    'timestamp': item['stored_at'],
                    'action': 'stored',
                    'conversation_id': item['conv_id'],
                    'role': item['role'],
                    'preview': item['preview']
                })
            
            # Calculate capacity and utilization
            capacity = max(10000, active_items * 2)
            utilization_percent = (active_items / capacity) * 100 if capacity > 0 else 0
            ttl_utilization_percent = (ttl_sum / ttl_count) if ttl_count > 0 else 0.0
            eviction_rate_per_min = expired_items / 60.0 if expired_items > 0 else 0.0
            
            return {
                'active_items': active_items,
                'capacity': capacity,
                'utilization_percent': round(utilization_percent, 2),
                'ttl_utilization_percent': round(ttl_utilization_percent, 2),
                'eviction_rate_per_min': round(eviction_rate_per_min, 2),
                'recent_activity': recent_activity[:10]
            }
            
        except Exception as e:
            error_msg = f"❌ CRITICAL: Failed to get working memory stats: {e}"
            logger.error(error_msg, exc_info=True)
            print(f"\n{'='*80}")
            print(f"❌ WORKING MEMORY GET_STATS FAILURE")
            print(f"{'='*80}")
            print(f"Error: {e}")
            print(f"Initialized: {self._initialized}")
            print(f"LMDB env: {self.env}")
            print(f"{'='*80}\n")
            raise RuntimeError(error_msg) from e
