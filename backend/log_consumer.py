"""
AICO Log Consumer Service

Subscribes to log messages from the message bus and persists them to the database.
This bridges the gap between ZMQ log transport and database storage.
"""

import asyncio
import json
import zmq
import zmq.asyncio
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from aico.core.bus import MessageBusClient
from aico.core.config import ConfigurationManager
from aico.proto.aico_core_logging_pb2 import LogEntry, LogLevel
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.security import AICOKeyManager
from aico.core.paths import AICOPaths
import sys

# Fix Windows asyncio event loop compatibility with ZMQ
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class AICOLogConsumer:
    """Consumes log messages from message bus and persists to database"""
    
    def __init__(self, config_manager: ConfigurationManager, db_connection: EncryptedLibSQLConnection, zmq_context: zmq.asyncio.Context):
        if not db_connection:
            raise ValueError("AICOLogConsumer requires a valid db_connection.")
        if not zmq_context:
            raise ValueError("AICOLogConsumer requires a ZMQ context.")
        self.config_manager = config_manager
        self.client: Optional[MessageBusClient] = None
        self.db_connection = db_connection
        self.context = zmq_context
        self.running = False
    
    async def _handle_debug_message(self, topic: str, payload):
        """Debug handler to see all messages"""
        # print(f"[LOG CONSUMER DEBUG] Received ANY message - Topic: {topic}, Type: {type(payload)}")
    
    async def start(self):
        """Start the log consumer"""
        try:
            # Set running flag to True FIRST
            self.running = True
            print(f"[LOG CONSUMER] Set running flag to True")
            
            # The database connection is now required and injected at initialization.
            if self.db_connection is None:
                # This should not happen due to the __init__ check, but as a safeguard:
                print("[LOG CONSUMER ERROR] Database connection is missing after initialization.")
                raise ConnectionError("LogConsumer is missing its database connection.")
            
            print(f"[LOG CONSUMER] Using injected database connection: {self.db_connection}")
            
            # Use direct ZMQ subscription for raw LogEntry messages
            import zmq
            import zmq.asyncio
            import asyncio
            
            # Get message bus configuration - connect to SUBSCRIBER port (broker backend)
            sub_port = self.config_manager.get("message_bus.sub_port", 5556)
            host = self.config_manager.get("message_bus.host", "localhost")
            
            print(f"[LOG CONSUMER] Connecting to SUBSCRIBER port tcp://{host}:{sub_port}")
            self.subscriber = self.context.socket(zmq.SUB)
            
            # CRITICAL: Set high water mark to prevent message loss during startup
            # This allows ZMQ to buffer up to 10,000 messages while consumer starts
            self.subscriber.setsockopt(zmq.RCVHWM, 10000)
            print(f"[LOG CONSUMER] Set receive high water mark to 10,000 messages")
            
            # Brief delay for broker startup
            await asyncio.sleep(0.1)
            
            self.subscriber.connect(f"tcp://{host}:{sub_port}")
            print(f"[LOG CONSUMER] Connected SUB socket to tcp://{host}:{sub_port}")
            
            # Subscribe to logs.* topics only
            self.subscriber.setsockopt(zmq.SUBSCRIBE, b"logs.")
            print(f"[LOG CONSUMER] SUBSCRIBED to topic prefix: b'logs.'")
            
            # Also subscribe to empty prefix to catch ALL messages for debugging
            self.subscriber.setsockopt(zmq.SUBSCRIBE, b"")
            print(f"[LOG CONSUMER] SUBSCRIBED to ALL messages (empty prefix) for debugging")
            
            # Give subscription a moment to propagate before starting message loop
            await asyncio.sleep(0.2)
            print(f"[LOG CONSUMER] Subscription ready, starting message loop")
            
            # CRITICAL: Immediately drain any buffered messages that arrived during startup
            print(f"[LOG CONSUMER] Checking for buffered startup messages...")
            startup_messages = 0
            while True:
                try:
                    poll_result = await self.subscriber.poll(timeout=10, flags=zmq.POLLIN)
                    if poll_result:
                        topic_bytes, data = await self.subscriber.recv_multipart(flags=zmq.NOBLOCK)
                        startup_messages += 1
                        # Process immediately
                        try:
                            log_entry = LogEntry()
                            log_entry.ParseFromString(data)
                            self._insert_log_to_database(log_entry)
                            if startup_messages % 50 == 0:
                                print(f"[LOG CONSUMER] Processed {startup_messages} startup messages...")
                        except Exception as e:
                            print(f"[LOG CONSUMER] Failed to process startup message {startup_messages}: {e}")
                    else:
                        break
                except zmq.Again:
                    break
                except Exception as e:
                    print(f"[LOG CONSUMER] Error draining startup messages: {e}")
                    break
            
            print(f"[LOG CONSUMER] Processed {startup_messages} buffered startup messages")
            
            # Test if we can receive any messages at all
            print(f"[LOG CONSUMER] Testing immediate message reception...")
            test_poll = await self.subscriber.poll(timeout=100, flags=zmq.POLLIN)
            print(f"[LOG CONSUMER] Test poll result: {test_poll}")
            
            # Start the message processing loop
            message_task = asyncio.create_task(self._zmq_message_loop())
            self.message_task = message_task  # Store reference to monitor it
            print(f"[LOG CONSUMER] Created message loop task: {message_task}")
            print(f"[LOG CONSUMER] Task done: {message_task.done()}, cancelled: {message_task.cancelled()}")
            print(f"[LOG CONSUMER] Started successfully with direct ZMQ subscription")
            
            # Add task monitoring with restart capability
            def monitor_task():
                import time
                import threading
                count = 0
                while self.running:
                    time.sleep(3)
                    count += 1
                    if hasattr(self, 'message_task'):
                        task = self.message_task
                        print(f"[LOG CONSUMER MONITOR {count}] Task status - Done: {task.done()}, Cancelled: {task.cancelled()}")
                        if task.done():
                            if task.cancelled():
                                print(f"[LOG CONSUMER MONITOR {count}] Task was cancelled - checking restart")
                                if self.running:
                                    print(f"[LOG CONSUMER MONITOR {count}] Restarting cancelled task")
                                    # Restart the task
                                    try:
                                        self.message_task = asyncio.create_task(self._zmq_message_loop())
                                        print(f"[LOG CONSUMER MONITOR {count}] New task created: {self.message_task}")
                                    except Exception as e:
                                        print(f"[LOG CONSUMER MONITOR {count}] Failed to restart task: {e}")
                            else:
                                try:
                                    result = task.result()
                                    print(f"[LOG CONSUMER MONITOR {count}] Task completed with result: {result}")
                                except Exception as e:
                                    print(f"[LOG CONSUMER MONITOR {count}] Task failed with exception: {e}")
                    else:
                        print(f"[LOG CONSUMER MONITOR {count}] No message task found")
                print(f"[LOG CONSUMER MONITOR] Monitor stopping - consumer no longer running")
            
            import threading
            monitor_thread = threading.Thread(target=monitor_task, daemon=True)
            monitor_thread.start()
            print(f"[LOG CONSUMER] Started task monitor thread")
            
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
        """Main message processing loop with cancellation handling"""
        print("[LOG CONSUMER] Starting message loop")
        print(f"[LOG CONSUMER] Message loop running status: {self.running}")
        print(f"[LOG CONSUMER] Subscriber socket: {self.subscriber}")
        print(f"[LOG CONSUMER] ZMQ context: {self.context}")
        
        loop_count = 0
        
        try:
            while self.running:
                loop_count += 1
                if loop_count % 10 == 1:  # Print every 1 second (10 * 0.1s) for more visibility
                    print(f"[LOG CONSUMER] Message loop active - cycle {loop_count}, running: {self.running}")
                
                try:
                    # Process all available messages in this poll cycle
                    poll_result = await self.subscriber.poll(timeout=10, flags=zmq.POLLIN)
                    if poll_result:
                        print(f"[LOG CONSUMER] Poll returned: {poll_result} - messages available")
                    elif loop_count % 50 == 1:  # Less frequent polling status
                        print(f"[LOG CONSUMER] Poll timeout - no messages available (cycle {loop_count})")
                except Exception as poll_error:
                    print(f"[LOG CONSUMER ERROR] Poll failed: {poll_error}")
                    await asyncio.sleep(1)
                    continue
                
                # Process ALL available messages without delays
                messages_processed = 0
                while poll_result:
                    try:
                        topic_bytes, data = await self.subscriber.recv_multipart(flags=zmq.NOBLOCK)
                        topic = topic_bytes.decode('utf-8')
                        messages_processed += 1
                        
                        trace_id = str(uuid.uuid4())[:8]
                        print(f"[CONSUMER TRACE {trace_id}] STEP 4: Received ZMQ message #{messages_processed} - Topic: {topic}, Data: {len(data)} bytes")
                        
                        try:
                            # Parse protobuf LogEntry
                            log_entry = LogEntry()
                            log_entry.ParseFromString(data)
                            print(f"[CONSUMER TRACE {trace_id}] STEP 5: Protobuf parsed - Subsystem: {log_entry.subsystem}, Module: {log_entry.module}, Message: {log_entry.message}")
                            
                            # Insert into database
                            try:
                                print(f"[CONSUMER TRACE {trace_id}] STEP 6: Attempting database insertion")
                                self._insert_log_to_database(log_entry)
                                print(f"[CONSUMER TRACE {trace_id}] STEP 7: Database insertion SUCCESS - Log persisted")
                            except Exception as db_error:
                                print(f"[CONSUMER TRACE {trace_id}] STEP 7: Database insertion FAILED: {db_error}")
                                
                        except Exception as parse_error:
                            print(f"[CONSUMER TRACE {trace_id}] STEP 5: Protobuf parsing FAILED: {parse_error}")
                            continue
                        
                        # Check for more messages immediately (no delay)
                        poll_result = await self.subscriber.poll(timeout=0, flags=zmq.POLLIN)
                        
                    except zmq.Again:
                        # No more messages available - break out of message processing loop
                        print(f"[LOG CONSUMER] Processed {messages_processed} messages in this cycle")
                        break
                    except Exception as recv_error:
                        print(f"[LOG CONSUMER ERROR] Failed to receive message: {recv_error}")
                        break
                
                # Only pause if no messages were processed
                if messages_processed == 0:
                    await asyncio.sleep(0.01)  # Much shorter pause when idle
                
        except asyncio.CancelledError:
            print("[LOG CONSUMER] Message loop was cancelled - checking if restart is needed")
            # If we're still supposed to be running, restart the loop
            if self.running:
                print("[LOG CONSUMER] Restarting message loop after cancellation")
                # Create a new task to replace the cancelled one
                self.message_task = asyncio.create_task(self._zmq_message_loop())
            else:
                print("[LOG CONSUMER] Message loop cancelled during shutdown - exiting gracefully")
            raise  # Re-raise to maintain proper cancellation semantics
    
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
            print(f"[LOG CONSUMER DB] Attempting to insert log: {log_entry.subsystem}.{log_entry.module} - {log_entry.message}")
            
            # Convert protobuf timestamp to ISO string
            timestamp_str = log_entry.timestamp.ToDatetime().isoformat() + "Z"
            print(f"[LOG CONSUMER DB] Timestamp: {timestamp_str}")
            
            # Convert protobuf LogLevel enum to string
            level_str = LogLevel.Name(log_entry.level)
            print(f"[LOG CONSUMER DB] Level: {level_str}")
            
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

            print(f"[LOG CONSUMER DB] Inserting with values: subsystem={log_entry.subsystem}, module={log_entry.module}, message={log_entry.message}")

            # Check connection state before insertion
            print(f"[LOG CONSUMER DB] Connection state before insert: {type(self.db_connection)}")
            
            # Execute the insert
            cursor = self.db_connection.execute("""
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
            print(f"[LOG CONSUMER DB] Insert executed, cursor: {cursor}")
            print(f"[LOG CONSUMER DB] Rows affected: {cursor.rowcount if hasattr(cursor, 'rowcount') else 'unknown'}")
            
            # Commit the transaction
            print(f"[LOG CONSUMER DB] Committing transaction...")
            self.db_connection.commit()
            print(f"[LOG CONSUMER DB] Transaction committed successfully")
            
            # Verify the insert by checking row count and recent entries
            try:
                count_cursor = self.db_connection.execute("SELECT COUNT(*) FROM logs")
                total_rows = count_cursor.fetchone()[0]
                print(f"[LOG CONSUMER DB] Total rows in logs table after insert: {total_rows}")
                
                # Show the 3 most recent entries to verify timestamp format
                recent_cursor = self.db_connection.execute("""
                    SELECT id, timestamp, level, subsystem, module, message 
                    FROM logs 
                    ORDER BY timestamp DESC 
                    LIMIT 3
                """)
                recent_logs = recent_cursor.fetchall()
                print(f"[LOG CONSUMER DB] Recent entries in database:")
                for log in recent_logs:
                    print(f"[LOG CONSUMER DB]   ID={log[0]}, timestamp='{log[1]}', level={log[2]}, {log[3]}.{log[4]}: {log[5][:50]}...")
                    
            except Exception as count_error:
                print(f"[LOG CONSUMER DB] Could not verify row count: {count_error}")
            
            print(f"[LOG CONSUMER DB] Successfully inserted log entry")
            
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
