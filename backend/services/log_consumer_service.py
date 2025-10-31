"""
AICO Log Consumer Service - Clean Implementation

Pure service implementation for consuming logs from message bus and persisting to database.
Eliminates brittleness through clear error handling, proper lifecycle management, and fail-fast behavior.
"""

import asyncio
import threading
import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from aico.core.logging_context import create_infrastructure_logger
from aico.core.topics import AICOTopics
from aico.core.bus import MessageBusClient
from aico.proto.aico_core_envelope_pb2 import AicoMessage
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
        
        # Use infrastructure logger to prevent feedback loops
        self.logger = create_infrastructure_logger("log_consumer")
        
        # Configuration - use message_bus config for ZMQ settings
        self.log_config = self.get_config("core.logging", {})
        self.message_bus_config = self.get_config("core.message_bus", {})
        self.enabled = self.get_config("core.api_gateway.plugins.log_consumer.enabled", True)
        
        # Runtime state
        self.message_bus_client: Optional[MessageBusClient] = None
        self.message_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Dependencies (resolved during initialization)
        self.db_connection: Optional[EncryptedLibSQLConnection] = None
        
        self.logger.info(f"Log consumer service created (enabled: {self.enabled})")
    
    async def initialize(self) -> None:
        """Initialize the log consumer service"""
        try:
            self.logger.info("Initializing log consumer service...")
            
            # Check if service is enabled
            if not self.enabled:
                self.logger.info("Log consumer service is disabled")
                self.state = ServiceState.STOPPED
                return
            
            # Resolve dependencies
            self.db_connection = self.container.get_service("database")
            
            if not self.db_connection:
                raise RuntimeError("Database service not available")
            
            # Create encrypted MessageBusClient using container config
            self.message_bus_client = MessageBusClient("log_consumer")
            
            # Validate configuration
            self._validate_config()
            
            self.logger.info("Log consumer service initialized successfully")
            self.state = ServiceState.INITIALIZED
            
        except Exception as e:
            self.logger.error(f"Failed to initialize log consumer service: {e}")
            self.state = ServiceState.ERROR
            raise
    
    async def start(self) -> None:
        """Start the log consumer service"""
        try:
            if self.state != ServiceState.INITIALIZED:
                raise RuntimeError(f"Service not initialized (state: {self.state})")
            
            self.logger = create_infrastructure_logger("aico.infrastructure.log_consumer")
            
            # Connect to message bus with encryption
            await self.message_bus_client.connect()
            
            # Subscribe to log messages with callback
            # ZMQ uses prefix matching, so "logs/" will match all topics starting with "logs/"
            subscription_topic = AICOTopics.ZMQ_LOGS_PREFIX  # This is "logs/"
            await self.message_bus_client.subscribe(
                subscription_topic,
                self._handle_log_message
            )
            
            self.running = True
            self.logger.info("Log consumer service started successfully")
            self.state = ServiceState.RUNNING
            
        except Exception as e:
            self.logger.error(f"Failed to start log consumer service: {e}")
            self.state = ServiceState.ERROR
            raise
    
    async def connect_when_broker_ready(self) -> None:
        """Connect to message bus when broker becomes available"""
        if not self.running or not self.message_bus_client:
            return
            
        try:
            #print(f"[LOG CONSUMER] Broker ready notification received - attempting connection...")
            
            # Try to connect now that broker is ready
            await self.message_bus_client.connect()
            #print(f"[LOG CONSUMER] Connected to message bus successfully")
            
            # Subscribe to log messages with callback
            # ZMQ uses prefix matching, so "logs/" will match all topics starting with "logs/"
            subscription_topic = AICOTopics.ZMQ_LOGS_PREFIX  # This is "logs/"
            #print(f"[LOG CONSUMER] Subscribing to topic: {subscription_topic}")
            await self.message_bus_client.subscribe(
                subscription_topic,
                self._handle_log_message
            )
            #print(f"[LOG CONSUMER] Subscription complete - ready to receive log messages")
            
        except Exception as e:
            self.logger.error(f"Failed to connect when broker ready: {e}")

    async def stop(self) -> None:
        """Stop the log consumer service"""
        try:
            self.logger.info("Stopping log consumer service...")
            
            # Stop message processing
            self.running = False
            
            # Disconnect from message bus
            if self.message_bus_client:
                await self.message_bus_client.disconnect()
                self.message_bus_client = None
            
            self.logger.info("Log consumer service stopped")
            self.state = ServiceState.STOPPED
            
        except Exception as e:
            self.logger.error(f"Error stopping log consumer service: {e}")
            self.state = ServiceState.ERROR
    
    async def health_check(self) -> Dict[str, Any]:
        """Check log consumer health status"""
        base_health = await super().health_check()
        
        log_consumer_health = {
            **base_health,
            "enabled": self.enabled,
            "running": self.running,
            "message_bus_client": self.message_bus_client is not None,
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
                self.message_bus_client is not None
            )
        else:
            log_consumer_health["healthy"] = True  # Disabled services are considered healthy
        
        return log_consumer_health
    
    def _validate_config(self) -> None:
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
    
    def _handle_log_message(self, message: AicoMessage) -> None:
        """Handle incoming log message from message bus"""
        
        # Process incoming log message silently
        
        try:
            if message.HasField('any_payload'):
                # Unpack the Any payload to LogEntry
                # The Any payload should now contain LogEntry directly (no double-wrapping)
                try:
                    log_entry = LogEntry()
                    success = message.any_payload.Unpack(log_entry)
                    
                    # Check unpack success
                    if success:
                        # Process the log entry asynchronously (don't block message handler)
                        import asyncio
                        asyncio.create_task(self._process_log_entry(log_entry))
                        # Log processing task created
                    else:
                        # Unpack failed - type mismatch
                        self.logger.error("Unpack returned False - type mismatch")
                        
                except Exception as e:
                    # Unpack exception occurred
                    self.logger.error(f"Failed to unpack Any payload to LogEntry: {e}")
            else:
                # Message has no any_payload field
                self.logger.error("Message has no any_payload field")
        except Exception as e:
            # Message processing failed
            self.logger.error(f"Failed to process message: {e}")
    
    async def _process_log_entry(self, log_entry: LogEntry) -> None:
        """Process individual log entry"""
        try:
                        
            # Filter: Ignore logs generated by this log consumer itself to prevent feedback loop
            if (log_entry.subsystem == "service" and log_entry.module and log_entry.module.startswith("log_consumer")):
                                return

                        # Insert to database (async to avoid blocking event loop)
            await self._insert_log_to_database(log_entry)
            
                            
        except Exception as e:
            self.logger.warning(f"Failed to process log entry: {e}")
    
    async def _insert_log_to_database(self, log_entry: LogEntry) -> None:
        """Insert log entry to database with error handling - runs in thread pool"""
        import asyncio
        
        def _sync_db_write():
            """Synchronous database write - runs in thread pool"""
            # Convert protobuf timestamp to ISO8601 string (TEXT column)
            ts_seconds = int(log_entry.timestamp.seconds)
            ts_nanos = int(getattr(log_entry.timestamp, 'nanos', 0))
            ts = ts_seconds + (ts_nanos / 1_000_000_000)
            timestamp_iso = datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc).isoformat()

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

            # Insert to database using LibSQL execute() method
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
        
        try:
            # Run blocking database write in thread pool to avoid event loop blocking
            await asyncio.to_thread(_sync_db_write)
        except Exception as e:
            self.logger.error(f"Failed to insert log to database: {e}")
            # Don't raise - we don't want to crash the consumer for individual log failures

    async def _setup_curve_encryption(self):
        """Setup CurveZMQ encryption for the log consumer"""
        if not self.encryption_enabled:
            self.logger.info("CurveZMQ encryption disabled for log consumer")
            return
            
        try:
            # Initialize configuration and key manager
            config_manager = ConfigurationManager()
            key_manager = AICOKeyManager(config_manager)
            
            # Get master key (non-interactive for service mode)
            master_key = key_manager.authenticate(interactive=False)
            
            # Derive CurveZMQ keypair for this log consumer
            self.public_key, self.secret_key = key_manager.derive_curve_keypair(master_key, "message_bus_client_log_consumer")
            
            self.logger.debug("CurveZMQ keys derived for log consumer")
            
        except Exception as e:
            self.logger.error(f"Failed to setup CurveZMQ encryption: {e}")
            # NO PLAINTEXT FALLBACK - Fail securely
            raise RuntimeError(f"CurveZMQ encryption setup failed: {e}")

    def _get_broker_public_key(self) -> str:
        """Get broker's public key for server authentication"""
        try:
            # Initialize configuration and key manager
            config_manager = ConfigurationManager()
            key_manager = AICOKeyManager(config_manager)
            
            # Get master key (non-interactive for service mode)
            master_key = key_manager.authenticate(interactive=False)
            
            # Derive broker's public key (same as broker derives for itself)
            broker_public_key, _ = key_manager.derive_curve_keypair(master_key, "message_bus_broker")
            
            return broker_public_key
            
        except Exception as e:
            self.logger.error(f"Failed to get broker public key: {e}")
            raise


def create_log_consumer_service(container: ServiceContainer) -> LogConsumerService:
    """Factory function for service container registration"""
    return LogConsumerService("log_consumer", container)
