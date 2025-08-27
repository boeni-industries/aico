"""
AICO Log Consumer Service

Subscribes to log messages from the message bus and persists them to the database.
This bridges the gap between ZMQ log transport and database storage.
"""

import asyncio
import json
import zmq
import zmq.asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from aico.core.bus import MessageBusClient
from aico.core.config import ConfigurationManager
from aico.proto.aico_core_logging_pb2 import LogEntry, LogLevel
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.security import AICOKeyManager
from aico.core.paths import AICOPaths


class AICOLogConsumer:
    """Consumes log messages from message bus and persists to database"""
    
    def __init__(self, config_manager, db_connection=None):
        self.config_manager = config_manager
        self.client: Optional[MessageBusClient] = None
        self.db_connection = db_connection  # Accept injected connection
        self.running = False
    
    def _get_database_connection(self) -> EncryptedLibSQLConnection:
        """Get database connection for log consumer"""
        key_manager = AICOKeyManager()
        paths = AICOPaths()
        db_path = paths.resolve_database_path("aico.db")
        # print(f"[LOG CONSUMER] Using database path: {db_path}")
        
        # Check if database file exists
        if not db_path.exists():
            # print(f"[LOG CONSUMER] ERROR: Database file does not exist: {db_path}")
            raise FileNotFoundError(f"Database file not found: {db_path}")
        
        # Check if salt file exists
        salt_path = db_path.with_suffix(db_path.suffix + '.salt')
        if not salt_path.exists():
            # print(f"[LOG CONSUMER] ERROR: Salt file does not exist: {salt_path}")
            raise FileNotFoundError(f"Salt file not found: {salt_path}")
        
        # print(f"[LOG CONSUMER] Database file size: {db_path.stat().st_size} bytes")
        # print(f"[LOG CONSUMER] Salt file size: {salt_path.stat().st_size} bytes")
        
        # Try cached key first (for active sessions)
        cached_key = key_manager._get_cached_session()
        if cached_key:
            key_manager._extend_session()
            db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
            # print(f"[LOG CONSUMER] Using cached session key: {db_key.hex()[:16]}...")
            conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
            try:
                conn.connect()
                # Test the connection with a simple query
                conn.execute("SELECT 1").fetchone()
                # print(f"[LOG CONSUMER] Database connection successful (cached key)")
                return conn
            except Exception as e:
                # print(f"[LOG CONSUMER] Database connection failed (cached key): {e}")
                raise
        
        # Try stored key from keyring (for backend services)
        import keyring
        stored_key = keyring.get_password(key_manager.service_name, "master_key")
        if stored_key:
            master_key = bytes.fromhex(stored_key)
            key_manager._cache_session(master_key)  # Cache for future use
            db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            # print(f"[LOG CONSUMER] Using stored master key: {db_key.hex()[:16]}...")
            conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
            try:
                conn.connect()
                # Test the connection with a simple query
                conn.execute("SELECT 1").fetchone()
                # print(f"[LOG CONSUMER] Database connection successful (stored key)")
                return conn
            except Exception as e:
                # print(f"[LOG CONSUMER] Database connection failed (stored key): {e}")
                raise
        
        # No key available - backend cannot run without authentication
        print("[LOG CONSUMER] No master key available - backend requires prior authentication")
        raise Exception("No master key available - backend requires prior authentication")
    
    async def _handle_debug_message(self, topic: str, payload):
        """Debug handler to see all messages"""
        # print(f"[LOG CONSUMER DEBUG] Received ANY message - Topic: {topic}, Type: {type(payload)}")
    
    async def start(self):
        """Start the log consumer"""
        try:
            # Use injected connection or create new one as fallback
            if self.db_connection is None:
                self.db_connection = self._get_database_connection()
                # print(f"[LOG CONSUMER] Created new database connection")
            else:
                pass
                # print(f"[LOG CONSUMER] Using injected database connection")
            
            # Use direct ZMQ subscription for raw LogEntry messages
            import zmq
            import zmq.asyncio
            import asyncio
            
            # Get message bus configuration - connect to SUBSCRIBER port (broker backend)
            sub_port = self.config_manager.get("message_bus.sub_port", 5556)
            host = self.config_manager.get("message_bus.host", "localhost")
            
            print(f"[LOG CONSUMER] Connecting to SUBSCRIBER port tcp://{host}:{sub_port}")
            self.context = zmq.asyncio.Context()
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect(f"tcp://{host}:{sub_port}")
            print(f"[LOG CONSUMER] Connected SUB socket to tcp://{host}:{sub_port}")
            
            # Subscribe to logs.* topics only
            self.subscriber.setsockopt(zmq.SUBSCRIBE, b"logs.")
            print(f"[LOG CONSUMER] SUBSCRIBED to topic prefix: b'logs.'")
            
            self.running = True
            
            # Start message processing loop
            asyncio.create_task(self._zmq_message_loop())
            print("[LOG CONSUMER] Started successfully with direct ZMQ subscription")
            
        except Exception as e:
            print(f"[LOG CONSUMER ERROR] Failed to start: {e}")
            raise
    
    async def stop(self):
        """Stop the log consumer service"""
        self.running = False
        if hasattr(self, 'subscriber') and self.subscriber:
            self.subscriber.close()
        if hasattr(self, 'context') and self.context:
            self.context.term()
        if self.db_connection:
            # Use proper LibSQL disconnect method
            try:
                self.db_connection.disconnect()
            except Exception as e:
                # Log cleanup failure but don't crash - this is during shutdown
                print(f"[LOG CONSUMER] Warning: Database cleanup failed during shutdown: {e}")

    
    async def _zmq_message_loop(self):
        """Direct ZMQ message processing loop"""
        while self.running:
            try:
                # Receive message with topic
                topic, message_data = await self.subscriber.recv_multipart()
                topic_str = topic.decode('utf-8')
                
                # Deserialize protobuf LogEntry
                log_entry = LogEntry()
                log_entry.ParseFromString(message_data)
                
                print(f"[LOG CONSUMER DEBUG] Received message - Topic: {topic_str}, Subsystem: {log_entry.subsystem}, Module: {log_entry.module}, Message: {log_entry.message}")
                
                # Handle the protobuf LogEntry message
                await self._handle_log_message(log_entry)
            except Exception as e:
                if self.running:
                    # Log error but continue processing - critical for log consumer stability
                    print(f"[LOG CONSUMER] Error processing message (continuing): {e}")
                    import traceback
                    print(f"[LOG CONSUMER] Traceback: {traceback.format_exc()}")
            await asyncio.sleep(0.1)
    
    async def _handle_log_message(self, log_entry: LogEntry):
        """Handle incoming protobuf log messages and persist to database"""
        try:
            # Insert protobuf LogEntry into database
            self._insert_log_to_database(log_entry)
            
        except Exception as e:
            # CRITICAL: Database insertion failed - log to console as last resort
            print(f"[LOG CONSUMER] CRITICAL: Failed to insert log to database: {e}")
            print(f"[LOG CONSUMER] Lost log entry: {log_entry.subsystem}.{log_entry.module} - {log_entry.message}")
            import traceback
            print(f"[LOG CONSUMER] Traceback: {traceback.format_exc()}")
    
    def _insert_log_to_database(self, log_entry: LogEntry):
        """Insert protobuf log entry into the database"""
        try:
            # Convert protobuf timestamp to ISO string
            timestamp_str = log_entry.timestamp.ToDatetime().isoformat() + "Z"
            
            # Convert protobuf LogLevel enum to string
            level_str = LogLevel.Name(log_entry.level)
            
            # Convert extra metadata to JSON (SQLite cannot store dict directly)
            extra_json = None
            if log_entry.extra:
                try:
                    extra_json = json.dumps(dict(log_entry.extra))
                except Exception:
                    # Fallback: best-effort string conversion
                    extra_json = json.dumps({k: str(v) for k, v in dict(log_entry.extra).items()})
            
            # Prepare all fields for schema alignment
            file_path = getattr(log_entry, 'file_path', None) or None
            line_number = getattr(log_entry, 'line_number', None) or None
            user_uuid = getattr(log_entry, 'user_uuid', None) or None
            session_id = getattr(log_entry, 'session_id', None) or None
            trace_id = getattr(log_entry, 'trace_id', None) or None
            # extra_json already prepared above as JSON string



            self.db_connection.execute("""
                INSERT INTO logs (
                    timestamp, level, subsystem, module, function_name, 
                    file_path, line_number, topic, message, user_uuid, 
                    session_id, trace_id, extra
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp_str,
                level_str,
                log_entry.subsystem,
                log_entry.module,
                log_entry.function,
                file_path,
                line_number,
                log_entry.topic,
                log_entry.message,
                user_uuid,
                session_id,
                trace_id,
                extra_json
            ))
            self.db_connection.commit()
            
        except Exception as e:
            # CRITICAL: Database insertion failed - log to console as last resort
            print(f"[LOG CONSUMER] CRITICAL: Database insertion failed: {e}")
            print(f"[LOG CONSUMER] Failed to insert: level={log_entry.level}, subsystem={log_entry.subsystem}, module={log_entry.module}")
            print(f"[LOG CONSUMER] Message: {log_entry.message}")
            import traceback
            print(f"[LOG CONSUMER] Traceback: {traceback.format_exc()}")
            # Try to rollback transaction
            try:
                self.db_connection.rollback()
            except Exception as rollback_error:
                print(f"[LOG CONSUMER] CRITICAL: Rollback also failed: {rollback_error}")

if __name__ == "__main__":
    import asyncio
    from aico.core.config import ConfigurationManager
    print("[LOG CONSUMER] __main__ entry reached")
    consumer = AICOLogConsumer(ConfigurationManager())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(consumer.start())
    try:
        print("[LOG CONSUMER] Running. Press Ctrl+C to exit.")
        loop.run_forever()
    except KeyboardInterrupt:
        print("[LOG CONSUMER] Stopping...")
        loop.run_until_complete(consumer.stop())
