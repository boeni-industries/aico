"""
AICO Log Consumer Service - Clean Implementation

Pure service implementation for consuming logs from message bus and persisting to database.
Eliminates brittleness through clear error handling, proper lifecycle management, and fail-fast behavior.
"""

import asyncio
import threading
import time
import json
import zmq
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from aico.proto.aico_core_logging_pb2 import LogEntry, LogLevel
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from backend.core.service_container import BaseService, ServiceContainer, ServiceState

class LogConsumerService(BaseService):
    """
    Clean log consumer service implementation
    
    Consumes log messages from ZMQ message bus and persists them to encrypted database.
    Follows AICO principles with fail-fast behavior and clear error handling.
    """
    
    def __init__(self, name: str, container: ServiceContainer):
        super().__init__(name, container)
        
        # Configuration - use message_bus config for ZMQ settings
        self.log_config = self.get_config("core.logging", {})
        self.message_bus_config = self.get_config("core.message_bus", {})
        self.enabled = self.get_config("core.api_gateway.plugins.log_consumer.enabled", True)
        
        # Runtime state
        self.subscriber: Optional[zmq.Socket] = None
        self.message_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Dependencies (resolved during initialization)
        self.db_connection: Optional[EncryptedLibSQLConnection] = None
        self.zmq_context: Optional[zmq.Context] = None
        
        self.logger.info(f"Log consumer service created (enabled: {self.enabled})")
    
    async def initialize(self) -> None:
        """Initialize log consumer with dependencies"""
        if not self.enabled:
            self.logger.info("ZMQ log transport disabled, log consumer will not start")
            return
        
        # Get required dependencies
        self.db_connection = self.require_service("database")
        self.zmq_context = self.require_service("zmq_context")
        
        if not self.db_connection:
            raise ValueError("Log consumer requires database connection")
        
        if not self.zmq_context:
            raise ValueError("Log consumer requires ZMQ context")
        
        # Validate configuration
        self._validate_configuration()
        
        self.logger.info("Log consumer initialized with dependencies")
    
    async def start(self) -> None:
        """Start log consumer operations"""
        if not self.enabled:
            self.logger.info("Log consumer disabled, not starting")
            return
        
        if not self.db_connection or not self.zmq_context:
            raise RuntimeError("Log consumer not properly initialized - missing dependencies")
        
        try:
            self.running = True
            self.logger.info("Starting log consumer service")
            
            # Setup ZMQ subscriber
            self._setup_subscriber()
            
            # Start message processing thread
            self._start_message_thread()
            
            self.logger.info("Log consumer started successfully - ZMQ log transport active")
            
        except Exception as e:
            self.running = False
            self.logger.error(f"Failed to start log consumer: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop log consumer operations"""
        if not self.running:
            return
        
        self.logger.info("Stopping log consumer service")
        
        # Signal shutdown
        self.running = False
        
        # Wait for message thread to finish
        if self.message_thread and self.message_thread.is_alive():
            self.logger.debug("Waiting for message thread to finish...")
            self.message_thread.join(timeout=2.0)
            
            if self.message_thread.is_alive():
                self.logger.warning("Message thread did not finish within timeout")
        
        # Close ZMQ socket
        if self.subscriber:
            try:
                self.subscriber.close()
                self.logger.debug("ZMQ subscriber socket closed")
            except Exception as e:
                self.logger.warning(f"Error closing ZMQ socket: {e}")
            finally:
                self.subscriber = None
        
        self.logger.info("Log consumer stopped successfully")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check log consumer health status"""
        base_health = await super().health_check()
        
        log_consumer_health = {
            **base_health,
            "enabled": self.enabled,
            "running": self.running,
            "zmq_subscriber": self.subscriber is not None,
            "message_thread": {
                "exists": self.message_thread is not None,
                "alive": self.message_thread.is_alive() if self.message_thread else False
            },
            "configuration": {
                "zmq_enabled": self.enabled,
                "sub_port": self.message_bus_config.get("sub_port"),
                "host": self.message_bus_config.get("host")
            }
        }
        
        # Overall health determination
        if self.enabled:
            log_consumer_health["healthy"] = (
                self.running and 
                self.subscriber is not None and 
                self.message_thread is not None and 
                self.message_thread.is_alive()
            )
        else:
            log_consumer_health["healthy"] = True  # Disabled services are considered healthy
        
        return log_consumer_health
    
    def _validate_configuration(self) -> None:
        """Validate log consumer configuration"""
        if not self.message_bus_config:
            raise ValueError("Missing message_bus configuration")
            
        required_config = ["sub_port", "host"]
        
        for key in required_config:
            if key not in self.message_bus_config:
                raise ValueError(f"Missing required message_bus configuration: {key}")
        
        # Validate port range
        sub_port = self.message_bus_config["sub_port"]
        if not isinstance(sub_port, int) or sub_port < 1024 or sub_port > 65535:
            raise ValueError(f"Invalid ZMQ sub_port: {sub_port} (must be 1024-65535)")
        
        self.logger.debug("Log consumer configuration validated")
    
    def _setup_subscriber(self) -> None:
        """Setup ZMQ subscriber socket"""
        try:
            # Get configuration from message_bus config
            sub_port = self.message_bus_config["sub_port"]
            host = self.message_bus_config["host"]
            
            # Create and configure subscriber socket
            self.subscriber = self.zmq_context.socket(zmq.SUB)
            self.subscriber.setsockopt(zmq.RCVHWM, 10000)  # High water mark
            self.subscriber.connect(f"tcp://{host}:{sub_port}")
            
            # Subscribe to log messages
            subscription_pattern = AICOTopics.ZMQ_LOGS_PREFIX
            self.subscriber.setsockopt(zmq.SUBSCRIBE, subscription_pattern.encode('utf-8'))
            
            self.logger.info(f"ZMQ subscriber connected to tcp://{host}:{sub_port}")
            self.logger.debug(f"Subscribed to pattern: {subscription_pattern}")
            
            # Brief pause to ensure subscription is registered
            time.sleep(0.1)
            
        except Exception as e:
            self.logger.error(f"Failed to setup ZMQ subscriber: {e}")
            raise
    
    def _start_message_thread(self) -> None:
        """Start message processing thread"""
        try:
            self.message_thread = threading.Thread(
                target=self._message_loop,
                name=f"log_consumer_{self.name}",
                daemon=True
            )
            self.message_thread.start()
            
            self.logger.debug("Message processing thread started")
            
        except Exception as e:
            self.logger.error(f"Failed to start message thread: {e}")
            raise
    
    def _message_loop(self) -> None:
        """Main message processing loop (runs in separate thread)"""
        #print(f"[DEBUG] Log consumer message loop started")
        
        last_poll_log = 0
        poll_log_interval = 30  # Log polling status every 30 seconds
        
        try:
            while self.running:
                try:
                    # Poll for messages with timeout
                    if self.subscriber.poll(timeout=100):  # 100ms timeout
                        #print(f"[DEBUG] Log consumer detected message available")
                        # Receive message
                        topic_bytes, data = self.subscriber.recv_multipart(zmq.NOBLOCK)
                        topic = topic_bytes.decode('utf-8')
                        
                        #print(f"[DEBUG] Log consumer received message: topic={topic}, size={len(data)}")
                        
                        # Process log entry
                        self._process_log_message(topic, data)
                        
                    else:
                        # No message received - periodic status logging
                        current_time = time.time()
                        if current_time - last_poll_log >= poll_log_interval:
                            #print(f"[DEBUG] Log consumer polling - no messages received in {poll_log_interval}s")
                            last_poll_log = current_time
                        
                        # Brief sleep to prevent busy waiting
                        time.sleep(0.01)
                        
                except zmq.Again:
                    # No message available, continue polling
                    continue
                    
                except Exception as e:
                    self.logger.error(f"Error in message loop: {e}")
                    if self.running:
                        # Brief pause before retrying
                        time.sleep(1.0)
                    
        except Exception as e:
            self.logger.error(f"Fatal error in message loop: {e}")
        finally:
            self.logger.debug("Message processing loop ended")
    
    def _process_log_message(self, topic: str, data: bytes) -> None:
        """Process individual log message"""
        try:
            #print(f"[DEBUG] Log consumer received message on topic: {topic}, data size: {len(data)} bytes")
            
            # Parse protobuf log entry
            log_entry = LogEntry()
            log_entry.ParseFromString(data)
            
            #print(f"[DEBUG] Parsed log entry: {log_entry.subsystem}.{log_entry.module} - {log_entry.message[:50]}...")
            
            # Filter: Ignore logs generated by this log consumer itself to prevent feedback loop
            if (log_entry.subsystem == "service" and log_entry.module and log_entry.module.startswith("log_consumer")):
                #print(f"[DEBUG] Skipping own log entry to prevent feedback loop: {log_entry.subsystem}.{log_entry.module}")
                return

            # Insert to database
            self._insert_log_to_database(log_entry)
            
            #print(f"[DEBUG] Log entry inserted to database successfully")
                
        except Exception as e:
            #print(f"[DEBUG] Failed to process log message from topic '{topic}': {e}")
            self.logger.warning(f"Failed to process log message from topic '{topic}': {e}")
    
    def _insert_log_to_database(self, log_entry: LogEntry) -> None:
        """Insert log entry to database with error handling"""
        try:
            # Convert protobuf timestamp to ISO8601 string (TEXT column)
            # google.protobuf.Timestamp has seconds and nanos
            ts_seconds = int(log_entry.timestamp.seconds)
            ts_nanos = int(getattr(log_entry.timestamp, 'nanos', 0))
            ts = ts_seconds + (ts_nanos / 1_000_000_000)
            timestamp_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

            # Level should be stored as TEXT (e.g., "INFO")
            try:
                level_str = LogLevel.Name(log_entry.level)
            except Exception:
                level_str = str(log_entry.level)

            # Serialize metadata/extra maps into JSON for extra_data TEXT column
            extra_payload = {}
            if log_entry.metadata:
                extra_payload['metadata'] = dict(log_entry.metadata)
            if hasattr(log_entry, 'extra') and log_entry.extra:
                extra_payload['extra'] = dict(log_entry.extra)
            extra_json = json.dumps(extra_payload) if extra_payload else None

            # Insert to database using LibSQL execute() method with schema-compatible columns
            self.db_connection.execute("""
                INSERT INTO logs (
                    timestamp, level, subsystem, module, function_name, file_path, line_number, topic, message,
                    user_uuid, session_id, trace_id, extra
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp_iso,
                level_str,
                log_entry.subsystem or None,
                log_entry.module or None,
                getattr(log_entry, 'function', None),
                getattr(log_entry, 'file_path', None),
                getattr(log_entry, 'line_number', None),
                getattr(log_entry, 'topic', None),
                log_entry.message,
                getattr(log_entry, 'user_uuid', None),
                getattr(log_entry, 'session_id', None),
                getattr(log_entry, 'trace_id', None),
                extra_json
            ))

            self.db_connection.commit()
        
        except Exception as e:
            self.logger.error(f"Failed to insert log to database: {e}")
            # Don't raise - we don't want to crash the consumer for individual log failures


def create_log_consumer_service(container: ServiceContainer) -> LogConsumerService:
    """Factory function for service container registration"""
    return LogConsumerService("log_consumer", container)
