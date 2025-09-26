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

logger = get_logger("shared", "ai.memory.working")


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
        self._named_dbs = self.config.get("core.memory.working.named_databases", [])
        self._ttl_seconds = self.config.get("core.memory.working.ttl_seconds", 86400)  # Updated default to 24 hours

    async def initialize(self) -> None:
        """Initialize LMDB environment and open named databases."""
        if self._initialized:
            return

        logger.info(f"[DEBUG] WorkingMemoryStore: Initializing at {self._db_path}")
        try:
            initialize_lmdb_env(self.config)
            self.env = lmdb.open(str(self._db_path), max_dbs=len(self._named_dbs) + 1)

            # Open handles to named databases (create if they don't exist)
            for db_name in self._named_dbs:
                self.dbs[db_name] = self.env.open_db(db_name.encode('utf-8'), create=True)


        except Exception as e:
            logger.error(f"Failed to initialize working memory store: {e}")
            raise

    async def store_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Store a message in the working memory store."""
        if not self._initialized:
            await self.initialize()

        logger.info(f"💾 [WORKING_MEMORY] Storing message for user {user_id}")
        logger.info(f"💾 [WORKING_MEMORY] Message type: {message.get('message_type', 'unknown')}")

        try:
            db = self.dbs.get("conversation_history")
            if db is None:
                raise ConnectionError("conversation_history database not open.")

            timestamp = datetime.utcnow()
            key_str = f"{user_id}:{timestamp.isoformat()}Z"
            key = key_str.encode('utf-8')

            # Convert datetime objects to ISO format strings for JSON serialization
            serializable_message = {}
            for msg_key, msg_value in message.items():
                if isinstance(msg_value, datetime):
                    serializable_message[msg_key] = msg_value.isoformat() + "Z"
                else:
                    serializable_message[msg_key] = msg_value
            
            storage_data = {
                **serializable_message,
                "_stored_at": timestamp.isoformat() + "Z",
                "_expires_at": (timestamp + timedelta(seconds=self._ttl_seconds)).isoformat() + "Z"
            }

            with self.env.begin(write=True, db=db) as txn:
                txn.put(key, json.dumps(storage_data).encode('utf-8'))

            logger.info(f"💾 [WORKING_MEMORY] ✅ Message stored successfully")
            return True

        except Exception as e:
            logger.error(f"💾 [WORKING_MEMORY] ❌ Failed to store message: {e}")
            return False

    async def retrieve_user_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent messages for a given user_id."""
        if not self._initialized:
            await self.initialize()

        logger.info(f"🔍 [WORKING_MEMORY] Retrieving history for user {user_id} (limit: {limit})")

        history = []
        try:
            db = self.dbs.get("conversation_history")
            if db is None:
                raise ConnectionError("conversation_history database not open.")

            logger.info(f"[DEBUG] WorkingMemoryStore: Retrieving history for user {user_id}.")
            with self.env.begin(db=db) as txn:
                cursor = txn.cursor()
                # Seek to the start of the desired user
                prefix = f"{user_id}:".encode('utf-8')
                if cursor.set_range(prefix):
                    for key, value in cursor:
                        if not key.startswith(prefix):
                            break  # Moved past the desired user

                        data = json.loads(value.decode('utf-8'))
                        if self._is_expired(data):
                            # Optional: could delete expired entries here in a separate write txn
                            continue

                        history.append(data)
                        if len(history) >= limit:
                            break

            # LMDB iterates in lexicographical order, so we need to sort by timestamp
            history.sort(key=lambda x: x.get("_stored_at"), reverse=True)
            
            logger.info(f"🔍 [WORKING_MEMORY] ✅ Retrieved {len(history)} messages from history")
            return history

        except Exception as e:
            logger.error(f"🔍 [WORKING_MEMORY] ❌ Failed to retrieve thread history: {e}")
            return []

    async def _get_recent_user_messages(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent messages for a user across all threads within the specified time window."""
        if not self._initialized:
            await self.initialize()

        recent_messages = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        logger.debug(f"Cutoff time for recent messages: {cutoff_time} UTC")
        
        try:
            db = self.dbs.get("conversation_history")
            if db is None:
                raise ConnectionError("conversation_history database not open.")

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
            # Parse expiration timestamp as UTC (consistent with storage)
            if expires_at_str.endswith('Z'):
                expires_at = datetime.fromisoformat(expires_at_str[:-1])
            elif '+' in expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace('+00:00', ''))
            else:
                expires_at = datetime.fromisoformat(expires_at_str)
            
            now_utc = datetime.utcnow()
            is_expired = now_utc > expires_at
            logger.debug(f"Expiration check: now={now_utc} UTC, expires={expires_at} UTC, expired={is_expired}")
            return is_expired
        except (ValueError, TypeError):
            return True
