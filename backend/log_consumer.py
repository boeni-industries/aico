"""
AICO Log Consumer Service

Subscribes to log messages from the message bus and persists them to the database.
This bridges the gap between ZMQ log transport and database storage.
"""

import threading
import time
import json
import zmq
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from aico.core.bus import MessageBusClient
from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.proto.aico_core_logging_pb2 import LogEntry, LogLevel
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.security import AICOKeyManager
from aico.core.paths import AICOPaths
import sys
import os
import contextlib

# Fix Windows asyncio event loop compatibility with ZMQ
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Global flag to track if we're running in foreground mode
_is_foreground_mode = False

def set_foreground_mode(enabled: bool):
    """Set whether we're running in foreground mode for debug output"""
    global _is_foreground_mode
    _is_foreground_mode = enabled

def debugPrint(message: str):
    """Print debug messages only when running in foreground mode"""
    if _is_foreground_mode:
        print(message)

class AICOLogConsumer:
    """Consumes log messages from message bus and persists to database"""
    
    def __init__(self, config_manager: ConfigurationManager, db_connection: EncryptedLibSQLConnection, zmq_context: zmq.Context):
        if not db_connection:
            raise ValueError("AICOLogConsumer requires a valid db_connection.")
        if not zmq_context:
            raise ValueError("AICOLogConsumer requires a ZMQ context.")
        self.config_manager = config_manager
        
        # Set foreground mode based on environment variable
        is_foreground = os.getenv('AICO_DETACH_MODE') == 'false'
        set_foreground_mode(is_foreground)
        self.client: Optional[MessageBusClient] = None
        self.db_connection = db_connection
        self.context = zmq_context
        self.running = False
        self.logger = get_logger("log_consumer", "service")
        from backend.log_consumer import debugPrint
        # Only print ZMQ context type at startup in foreground mode
        debugPrint(f"[LOG CONSUMER] Using ZMQ context type: {type(self.context).__name__}")
    
    async def _handle_debug_message(self, topic: str, payload):
        """Legacy debug handler - kept for potential future debugging needs"""
        pass
    
    def start(self):
        """Start the log consumer (synchronous, threaded)"""
        try:
            self.running = True
            self.logger.info("Starting log consumer service")

            if self.db_connection is None:
                self.logger.error("Database connection is missing after initialization")
                raise ConnectionError("LogConsumer is missing its database connection.")

            # Only print database connection type at startup in foreground mode
            debugPrint(f"[LOG CONSUMER] Using database connection: {type(self.db_connection).__name__}")

            # Get message bus configuration - connect to SUBSCRIBER port (broker backend)
            sub_port = self.config_manager.get("message_bus.sub_port", 5556)
            host = self.config_manager.get("message_bus.host", "localhost")

            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.setsockopt(zmq.RCVHWM, 10000)
            self.subscriber.connect(f"tcp://{host}:{sub_port}")
            self.logger.info(f"Connected to message bus at tcp://{host}:{sub_port}")
            self.subscriber.setsockopt(zmq.SUBSCRIBE, b"logs.")
            time.sleep(0.2)

            def message_loop():
                # Only print message loop start in foreground mode
                debugPrint("[LOG CONSUMER] Starting message loop (threaded)")
                try:
                    while self.running:
                        try:
                            if self.subscriber.poll(timeout=100):
                                topic_bytes, data = self.subscriber.recv_multipart(zmq.NOBLOCK)
                                topic = topic_bytes.decode('utf-8')
                                # For deep debugging only; comment out by default
                                # debugPrint(f"[LOG CONSUMER] Received message on topic: {topic}")
                                try:
                                    log_entry = LogEntry()
                                    log_entry.ParseFromString(data)
                                    self._insert_log_to_database(log_entry)
                                except Exception as e:
                                    self.logger.warning(f"Failed to process message: {e}")
                            else:
                                time.sleep(0.01)
                        except zmq.Again:
                            continue
                        except Exception as e:
                            self.logger.error(f"Error in message loop: {e}")
                            time.sleep(1)
                except Exception as e:
                    # Normal exception handling for message loop errors
                    self.logger.error(f"Unhandled error in message loop: {e}")
                    return
                # Only print message loop exit in foreground mode
                debugPrint("[LOG CONSUMER] Message loop exiting")

            self.message_thread = threading.Thread(target=message_loop, daemon=True)
            self.message_thread.start()
            self.logger.info("Log consumer started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start log consumer: {e}")
            raise
    
    def stop(self):
        """Stop the log consumer service"""
        self.logger.info("Stopping log consumer service")
        
        # Close ZMQ subscriber first to stop new messages
        if hasattr(self, 'subscriber') and self.subscriber:
            self.subscriber.close()
        
        self.running = False

        # Wait for message thread to exit
        if hasattr(self, 'message_thread') and self.message_thread:
            self.message_thread.join(timeout=3.0)

        # Close database connection
        if self.db_connection:
            try:
                self.db_connection.disconnect()
            except Exception as e:
                self.logger.warning(f"Database cleanup failed during shutdown: {e}")
            self.db_connection = None

        self.logger.info("Log consumer stopped")

    
    async def _zmq_message_loop(self):
        """Main message processing loop with cancellation handling"""
        debugPrint("[LOG CONSUMER] Starting message loop")
        
        try:
            while self.running:
                try:
                    # Process all available messages in this poll cycle
                    poll_result = await self.subscriber.poll(timeout=100, flags=zmq.POLLIN)
                except Exception as poll_error:
                    self.logger.error(f"Poll failed: {poll_error}")
                    await asyncio.sleep(1)
                    continue
                
                # Process ALL available messages without delays
                messages_processed = 0
                while poll_result:
                    try:
                        topic_bytes, data = await self.subscriber.recv_multipart(flags=zmq.NOBLOCK)
                        topic = topic_bytes.decode('utf-8')
                        messages_processed += 1
                        
                        try:
                            # Parse protobuf LogEntry
                            log_entry = LogEntry()
                            log_entry.ParseFromString(data)
                            
                            # Insert into database
                            try:
                                self._insert_log_to_database(log_entry)
                            except Exception as db_error:
                                self.logger.error(f"Database insertion failed: {db_error}")
                                
                        except Exception as parse_error:
                            self.logger.warning(f"Protobuf parsing failed: {parse_error}")
                            continue
                        
                        # Check for more messages immediately
                        poll_result = await self.subscriber.poll(timeout=0, flags=zmq.POLLIN)
                        
                    except zmq.Again:
                        break
                    except Exception as recv_error:
                        self.logger.error(f"Failed to receive message: {recv_error}")
                        break
                
                # Only pause if no messages were processed
                if messages_processed == 0:
                    await asyncio.sleep(0.01)
                
        except asyncio.CancelledError:
            # Only restart if we're still supposed to be running
            if self.running:
                debugPrint("[LOG CONSUMER] Restarting message loop after cancellation")
                self.message_task = asyncio.create_task(self._zmq_message_loop())
            else:
                debugPrint("[LOG CONSUMER] Message loop cancelled during shutdown - staying stopped")
            raise
    
    async def _handle_log_message(self, log_entry: LogEntry):
        """Handle incoming protobuf log messages and persist to database"""
        try:
            self._insert_log_to_database(log_entry)
        except Exception as e:
            self.logger.error(f"Failed to insert log to database: {e}")
            debugPrint(f"[LOG CONSUMER] Lost log entry: {log_entry.subsystem}.{log_entry.module} - {log_entry.message}")
    
    def _insert_log_to_database(self, log_entry: LogEntry):
        """Insert protobuf log entry into the database"""
        try:
            # Convert protobuf timestamp to ISO string
            timestamp_str = log_entry.timestamp.ToDatetime().isoformat() + "Z"
            
            # Convert protobuf LogLevel enum to string
            level_str = LogLevel.Name(log_entry.level)
            
            # Convert extra metadata to JSON
            extra_json = None
            if log_entry.extra:
                try:
                    extra_json = json.dumps(dict(log_entry.extra))
                except Exception:
                    extra_json = json.dumps({k: str(v) for k, v in dict(log_entry.extra).items()})
            
            # Prepare all fields for schema alignment
            file_path = getattr(log_entry, 'file_path', None) or None
            line_number = getattr(log_entry, 'line_number', None) or None
            user_uuid = getattr(log_entry, 'user_uuid', None) or None
            session_id = getattr(log_entry, 'session_id', None) or None
            trace_id = getattr(log_entry, 'trace_id', None) or None
            
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
            
            # Commit the transaction
            self.db_connection.commit()
            
        except BaseException as e:
            # Check if this is a shutdown-related error (connection closed)
            error_str = str(e)
            if "Option::unwrap()" in error_str or "None value" in error_str or "PanicException" in str(type(e)):
                # TODO: Fix shutdown race condition properly - the background thread can still
                # attempt DB access after connection is closed during shutdown. Current workaround
                # catches the Rust panic and returns silently, but ideally we should prevent
                # the race condition entirely through better thread synchronization.
                return
            
            self.logger.error(f"Database insertion failed: {e}")
            debugPrint(f"[LOG CONSUMER] Failed to insert: {log_entry.subsystem}.{log_entry.module} - {log_entry.message}")
            try:
                if self.db_connection:
                    self.db_connection.rollback()
            except Exception as rollback_error:
                self.logger.error(f"Rollback also failed: {rollback_error}")
            raise

if __name__ == "__main__":
    import asyncio
    from aico.core.config import ConfigurationManager
    # print("[LOG CONSUMER] __main__ entry reached")
    consumer = AICOLogConsumer(ConfigurationManager())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(consumer.start())
    try:
        # print("[LOG CONSUMER] Running. Press Ctrl+C to exit.")
        loop.run_forever()
    except KeyboardInterrupt:
        # print("[LOG CONSUMER] Stopping...")
        loop.run_until_complete(consumer.stop())
