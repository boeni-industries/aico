"""
Loki Log Handler

High-performance async log handler that writes directly to Loki.
Purpose-built for log aggregation with efficient storage and querying.

Features:
- Async in-memory buffer (non-blocking log calls)
- Batch writes for efficiency
- Label-based indexing (not full-text)
- Native log streaming support
- 10x more efficient storage than InfluxDB for logs
"""

import logging
import threading
import time
import json
from collections import deque
from datetime import datetime
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor


class LokiLogHandler(logging.Handler):
    """
    Async log handler that writes to Loki.
    
    Logs are buffered in memory and written in batches to Loki.
    Never blocks the calling thread - all I/O happens in background.
    """
    
    def __init__(
        self,
        loki_url: str,
        service_name: str,
        buffer_size: int = 1000,
        flush_interval: float = 5.0,
        batch_size: int = 100,
        overflow_strategy: str = "drop_oldest"
    ):
        """
        Initialize Loki log handler.
        
        Args:
            loki_url: Loki URL (e.g. http://localhost:3100)
            service_name: Service identifier (backend, modelservice, cli, etc)
            buffer_size: Max records in memory buffer
            flush_interval: Seconds between batch writes
            batch_size: Records per batch write
            overflow_strategy: "drop_oldest" or "drop_newest"
        """
        super().__init__()
        
        # Loki connection params
        self.loki_url = loki_url.rstrip('/')
        self.push_url = f"{self.loki_url}/loki/api/v1/push"
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
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="loki-log")

        # HTTP session is created lazily in the flush thread
        self._http_session = None

        # Prevent queuing many pending writes
        self._write_in_flight = threading.Event()

        # Shutdown guard to prevent scheduling work during interpreter teardown
        self._closing = threading.Event()
        
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
        
        Adds record to buffer. If buffer is full, applies overflow strategy.
        """
        try:
            # Format the log entry
            log_entry = self._format_log_entry(record)
            
            # Add to buffer (thread-safe)
            with self.buffer_lock:
                if self.overflow_strategy == "drop_newest" and len(self.buffer) >= self.buffer_size:
                    # Drop this record
                    with self.stats_lock:
                        self.stats["records_dropped"] += 1
                    return
                
                self.buffer.append(log_entry)
                
                with self.stats_lock:
                    self.stats["records_buffered"] += 1
        
        except Exception:
            # Never let logging errors crash the application
            self.handleError(record)
    
    def _format_log_entry(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Format log record for Loki.
        
        Returns dict with labels and log line.
        """
        # Infer service from logger name if not explicitly set
        inferred_service = self.service_name
        if isinstance(record.name, str):
            if record.name.startswith("backend."):
                inferred_service = "backend"
            elif record.name.startswith("modelservice."):
                inferred_service = "modelservice"
            elif record.name.startswith("cli."):
                inferred_service = "cli"
            elif record.name.startswith("shared.") or record.name.startswith("aico."):
                inferred_service = "shared"

        # Extract logger prefix (first 2 segments) for low-cardinality label
        # Skip service name prefix to avoid duplication (e.g., backend.backend.main -> backend.main)
        logger_prefix = "unknown"
        if isinstance(record.name, str) and "." in record.name:
            parts = record.name.split(".")
            # If first part matches service name, skip it
            if parts[0] == inferred_service:
                parts = parts[1:]
            logger_prefix = ".".join(parts[:2]) if len(parts) >= 2 else parts[0] if parts else "unknown"
        
        # Labels (indexed, low cardinality only)
        labels = {
            "service": inferred_service,
            "level": record.levelname,
            "logger_prefix": logger_prefix,
        }

        # Build a single JSON object as the log line.
        # This is the only approach that gives Grafana/Loki first-class structured log UX.
        log_obj: Dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "service": inferred_service,
            "logger": record.name,
            "logger_prefix": logger_prefix,
            "msg": record.getMessage(),
            "module": record.module,
            "function": record.funcName if record.funcName != "<module>" else None,
            "pathname": record.pathname,
            "lineno": record.lineno,
        }

        # Attach OpenTelemetry trace correlation (if active).
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            if span is not None:
                ctx = span.get_span_context()
                if getattr(ctx, "is_valid", False):
                    log_obj["trace_id"] = format(ctx.trace_id, "032x")
                    log_obj["span_id"] = format(ctx.span_id, "016x")
        except Exception:
            pass

        # Attach exception info if present
        if record.exc_info:
            exc_text = self.formatter.formatException(record.exc_info) if self.formatter else str(record.exc_info)
            log_obj["exception"] = exc_text
            if record.exc_info[0]:
                log_obj["exc_type"] = record.exc_info[0].__name__

        # Attach a small, explicit set of known correlation IDs (avoid high-cardinality labels)
        if hasattr(record, "user_id") and record.user_id:
            log_obj["user_id"] = record.user_id
        if hasattr(record, "request_id") and record.request_id:
            log_obj["request_id"] = record.request_id
        if hasattr(record, "client_id") and record.client_id:
            log_obj["client_id"] = record.client_id
        if hasattr(record, "session_id") and record.session_id:
            log_obj["session_id"] = record.session_id
        if hasattr(record, "conversation_id") and record.conversation_id:
            log_obj["conversation_id"] = record.conversation_id

        # Remove None values and JSON-serialize
        log_obj = {k: v for k, v in log_obj.items() if v is not None}
        log_line = json.dumps(log_obj, ensure_ascii=False, separators=(",", ":"))
        
        return {
            "timestamp": int(record.created * 1_000_000_000),  # nanoseconds
            "labels": labels,
            "line": log_line
        }
    
    def _start_flusher(self):
        """Start background flush thread."""
        self.running = True
        self.flush_thread = threading.Thread(
            target=self._flush_loop,
            name="loki-log-flusher",
            daemon=True
        )
        self.flush_thread.start()
    
    def _flush_loop(self):
        """Background thread that periodically flushes buffer to Loki."""
        import requests
        
        # Create HTTP session for connection pooling
        self._http_session = requests.Session()
        self._http_session.headers.update({
            "Content-Type": "application/json"
        })
        
        while self.running:
            try:
                time.sleep(self.flush_interval)
                self._flush_buffer()
            except Exception as e:
                # Log errors but keep running
                print(f"[LokiLogHandler] Flush error: {e}", flush=True)
    
    def _flush_buffer(self):
        """Flush buffered records to Loki."""
        if not self.buffer:
            return

        if self._closing.is_set():
            return
        
        # Don't queue multiple writes
        if self._write_in_flight.is_set():
            return
        
        # Get batch of records
        batch = []
        with self.buffer_lock:
            while self.buffer and len(batch) < self.batch_size:
                batch.append(self.buffer.popleft())
        
        if not batch:
            return
        
        # Submit write to executor (non-blocking)
        self._write_in_flight.set()
        try:
            # ThreadPoolExecutor raises RuntimeError if shutdown has started.
            self.executor.submit(self._write_batch, batch)
        except RuntimeError:
            # During shutdown / interpreter exit we may not be able to schedule.
            self._write_in_flight.clear()
            with self.stats_lock:
                self.stats["write_errors"] += 1
    
    def _write_batch(self, batch: List[Dict[str, Any]]):
        """Write batch of log entries to Loki."""
        try:
            # Group logs by label set (Loki requirement)
            streams = {}
            for entry in batch:
                # Create label string
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(entry["labels"].items()))
                
                if label_str not in streams:
                    streams[label_str] = {
                        "stream": entry["labels"],
                        "values": []
                    }
                
                # Add log entry [timestamp_ns, line]
                streams[label_str]["values"].append([
                    str(entry["timestamp"]),
                    entry["line"]
                ])
            
            # Build Loki push request
            payload = {
                "streams": list(streams.values())
            }
            
            # Send to Loki
            response = self._http_session.post(
                self.push_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                # Success
                with self.stats_lock:
                    self.stats["records_written"] += len(batch)
                    self.stats["last_flush"] = datetime.now().isoformat()
            else:
                # Error
                with self.stats_lock:
                    self.stats["write_errors"] += 1
                print(f"[LokiLogHandler] Write failed: {response.status_code} {response.text}", flush=True)
        
        except Exception as e:
            with self.stats_lock:
                self.stats["write_errors"] += 1
            print(f"[LokiLogHandler] Write error: {e}", flush=True)
        
        finally:
            self._write_in_flight.clear()
    
    def flush(self):
        """Flush all buffered records immediately."""
        self._flush_buffer()
        # Wait for in-flight write to complete
        timeout = 10
        start = time.time()
        while self._write_in_flight.is_set() and (time.time() - start) < timeout:
            time.sleep(0.1)
    
    def close(self):
        """Close handler and flush remaining records."""
        self._closing.set()
        self.running = False

        try:
            # Flush remaining records
            self.flush()
        except Exception:
            pass

        # Wait for flush thread to finish
        try:
            if self.flush_thread and self.flush_thread.is_alive():
                self.flush_thread.join(timeout=5)
        except Exception:
            pass

        # Close HTTP session
        try:
            if self._http_session is not None:
                self._http_session.close()
        except Exception:
            pass

        # Shutdown executor last
        try:
            if self.executor is not None:
                self.executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass

        super().close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        with self.stats_lock:
            return self.stats.copy()
