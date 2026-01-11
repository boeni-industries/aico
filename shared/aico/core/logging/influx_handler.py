"""
InfluxDB Log Handler

High-performance async log handler that writes directly to InfluxDB.
Replaces ZMQ/protobuf/message-bus complexity with simple, fast, direct writes.

Features:
- Async in-memory buffer (non-blocking log calls)
- Batch writes for efficiency
- Graceful overflow handling
- Line protocol format
- Connection pooling
"""

import logging
import threading
import time
from collections import deque
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor


class InfluxDBLogHandler(logging.Handler):
    """
    Async log handler that writes to InfluxDB.
    
    Logs are buffered in memory and written in batches to InfluxDB.
    Never blocks the calling thread - all I/O happens in background.
    """
    
    def __init__(
        self,
        influx_url: str,
        org: str,
        bucket: str,
        token: str,
        service_name: str,
        buffer_size: int = 1000,
        flush_interval: float = 5.0,
        batch_size: int = 100,
        overflow_strategy: str = "drop_oldest"
    ):
        """
        Initialize InfluxDB log handler.
        
        Args:
            influx_url: InfluxDB URL (e.g. http://localhost:8086)
            org: InfluxDB organization
            bucket: InfluxDB bucket name
            token: InfluxDB API token
            service_name: Service identifier (backend, modelservice, cli, etc)
            buffer_size: Max records in memory buffer
            flush_interval: Seconds between batch writes
            batch_size: Records per batch write
            overflow_strategy: "drop_oldest" or "drop_newest"
        """
        super().__init__()
        
        # InfluxDB connection params
        self.influx_url = influx_url
        self.org = org
        self.bucket = bucket
        self.token = token
        self.service_name = service_name
        
        # Buffer configuration
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.overflow_strategy = overflow_strategy
        
        # In-memory buffer (thread-safe deque)
        self.buffer = deque(maxlen=buffer_size if overflow_strategy == "drop_oldest" else None)
        self.buffer_lock = threading.Lock()
        
        # Background flush thread
        self.running = False
        self.flush_thread = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="influx-log")
        
        # Statistics
        self.stats = {
            "records_buffered": 0,
            "records_written": 0,
            "records_dropped": 0,
            "write_errors": 0,
            "last_flush": None
        }
        self.stats_lock = threading.Lock()
        
        # Start background flusher
        self._start_flusher()
    
    def emit(self, record: logging.LogRecord):
        """
        Emit a log record (non-blocking).
        
        Formats the record and adds to buffer. Never blocks - if buffer
        is full, applies overflow strategy.
        """
        try:
            # Format log record to InfluxDB line protocol
            line = self._format_line_protocol(record)
            
            with self.buffer_lock:
                # Check buffer overflow
                if self.overflow_strategy == "drop_newest" and len(self.buffer) >= self.buffer_size:
                    with self.stats_lock:
                        self.stats["records_dropped"] += 1
                    return
                
                # Add to buffer (deque handles drop_oldest automatically via maxlen)
                self.buffer.append(line)
                
                with self.stats_lock:
                    self.stats["records_buffered"] += 1
                    if self.overflow_strategy == "drop_oldest" and len(self.buffer) >= self.buffer_size:
                        self.stats["records_dropped"] += 1
        
        except Exception:
            # Never let logging errors crash the application
            self.handleError(record)
    
    def _format_line_protocol(self, record: logging.LogRecord) -> str:
        """
        Format log record as InfluxDB line protocol.
        
        Format: measurement,tag1=value1,tag2=value2 field1=value1,field2=value2 timestamp
        
        Example:
        logs,service=backend,level=ERROR,component=api message="Request failed",user_id="123" 1234567890000000000
        """
        # Timestamp in nanoseconds
        timestamp_ns = int(record.created * 1_000_000_000)
        
        # Tags (indexed, for filtering)
        tags = {
            "service": self.service_name,
            "level": record.levelname,
            "logger": record.name,
        }
        
        # Add module/function info if available
        if record.module:
            tags["module"] = record.module
        if record.funcName and record.funcName != "<module>":
            tags["function"] = record.funcName
        
        # Add thread/process info as tags for filtering
        if record.threadName and record.threadName != "MainThread":
            tags["thread"] = record.threadName
        if record.processName and record.processName != "MainProcess":
            tags["process"] = record.processName
        
        # Fields (not indexed, for data)
        fields = []
        
        # Add a numeric field for aggregations (always present)
        fields.append(f"count=1i")  # Integer field for counting logs
        
        # Add string fields
        fields.append(f"message={self._escape_string_field(record.getMessage())}")
        
        # Add source location info (useful for debugging)
        fields.append(f"pathname={self._escape_string_field(record.pathname)}")
        fields.append(f"lineno={record.lineno}i")
        
        # Add thread/process IDs
        fields.append(f"thread_id={record.thread}i")
        fields.append(f"process_id={record.process}i")
        
        # Add extra fields from record (via extra={} parameter)
        if hasattr(record, "user_id") and record.user_id:
            fields.append(f"user_id={self._escape_string_field(record.user_id)}")
        if hasattr(record, "request_id") and record.request_id:
            fields.append(f"request_id={self._escape_string_field(record.request_id)}")
        if hasattr(record, "conversation_id") and record.conversation_id:
            fields.append(f"conversation_id={self._escape_string_field(record.conversation_id)}")
        if hasattr(record, "duration_ms") and record.duration_ms is not None:
            fields.append(f"duration_ms={float(record.duration_ms)}")
        if hasattr(record, "error_code") and record.error_code:
            fields.append(f"error_code={self._escape_string_field(record.error_code)}")
        
        # Add exception info if present (logger.exception() or exc_info=True)
        if record.exc_info:
            exc_text = self.formatter.formatException(record.exc_info) if self.formatter else str(record.exc_info)
            fields.append(f"exception={self._escape_string_field(exc_text)}")
            # Add exception type for easier filtering
            if record.exc_info[0]:
                tags["exc_type"] = record.exc_info[0].__name__
        
        # Build line protocol string
        tag_string = ",".join(f"{k}={self._escape_tag_value(v)}" for k, v in tags.items())
        field_string = ",".join(fields)
        
        return f"logs,{tag_string} {field_string} {timestamp_ns}"
    
    def _escape_tag_value(self, value: str) -> str:
        """Escape tag value for line protocol."""
        return str(value).replace(",", "\\,").replace(" ", "\\ ").replace("=", "\\=")
    
    def _escape_string_field(self, value: str) -> str:
        """Escape string field value for line protocol (quoted string)."""
        # Escape backslashes first, then quotes, then newlines
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{escaped}"'
    
    def _start_flusher(self):
        """Start background flush thread."""
        self.running = True
        self.flush_thread = threading.Thread(
            target=self._flush_loop,
            name="influx-log-flusher",
            daemon=True
        )
        self.flush_thread.start()
    
    def _flush_loop(self):
        """Background loop that periodically flushes buffer to InfluxDB."""
        print(f"[InfluxDBLogHandler] Flush thread started (interval: {self.flush_interval}s, running={self.running})", flush=True)
        try:
            while self.running:
                try:
                    time.sleep(self.flush_interval)
                    buffer_size = len(self.buffer)
                    if buffer_size > 0:
                        print(f"[InfluxDBLogHandler] Flushing {buffer_size} buffered logs...", flush=True)
                    self._flush_buffer()
                except Exception as e:
                    # Log to stderr but don't crash
                    print(f"[InfluxDBLogHandler] Flush error: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            print(f"[InfluxDBLogHandler] FATAL: Flush thread crashed: {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            print(f"[InfluxDBLogHandler] Flush thread stopped (running={self.running})", flush=True)
    
    def _flush_buffer(self):
        """Flush buffered logs to InfluxDB."""
        if not self.buffer:
            return
        
        # Get batch from buffer
        with self.buffer_lock:
            batch_size = min(len(self.buffer), self.batch_size)
            if batch_size == 0:
                return
            
            batch = [self.buffer.popleft() for _ in range(batch_size)]
        
        # Write to InfluxDB (in executor to avoid blocking flush thread)
        try:
            self.executor.submit(self._write_batch, batch)
        except RuntimeError:
            # Executor shutdown during interpreter exit - write synchronously
            self._write_batch(batch)
    
    def _write_batch(self, batch: list):
        """Write batch of log lines to InfluxDB."""
        try:
            import requests
            
            # Prepare request
            url = f"{self.influx_url}/api/v2/write"
            params = {
                "org": self.org,
                "bucket": self.bucket,
                "precision": "ns"
            }
            headers = {
                "Authorization": f"Token {self.token}",
                "Content-Type": "text/plain; charset=utf-8"
            }
            data = "\n".join(batch)
            
            # Write to InfluxDB
            response = requests.post(
                url,
                params=params,
                headers=headers,
                data=data,
                timeout=5.0
            )
            
            if response.status_code == 204:
                # Success
                with self.stats_lock:
                    self.stats["records_written"] += len(batch)
                    self.stats["last_flush"] = datetime.utcnow().isoformat()
                print(f"[InfluxDBLogHandler] ✅ Successfully wrote {len(batch)} logs to InfluxDB", flush=True)
            else:
                # Error
                with self.stats_lock:
                    self.stats["write_errors"] += 1
                print(f"[InfluxDBLogHandler] ❌ Write failed: {response.status_code} {response.text}", flush=True)
        
        except Exception as e:
            with self.stats_lock:
                self.stats["write_errors"] += 1
            print(f"[InfluxDBLogHandler] Write exception: {e}", flush=True)
    
    def flush(self):
        """Flush all buffered logs immediately."""
        self._flush_buffer()
    
    def close(self):
        """Close handler and flush remaining logs."""
        print(f"[InfluxDBLogHandler] close() called! Stack trace:", flush=True)
        import traceback
        traceback.print_stack()
        self.running = False
        
        # Flush remaining logs
        while self.buffer:
            self._flush_buffer()
            time.sleep(0.1)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        if self.flush_thread:
            self.flush_thread.join(timeout=2.0)
        
        super().close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        with self.stats_lock:
            return {
                **self.stats,
                "buffer_size": len(self.buffer),
                "buffer_capacity": self.buffer_size
            }
