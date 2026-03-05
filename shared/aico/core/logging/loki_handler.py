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
from datetime import datetime, timezone
import email.utils
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
        # NOTE: Do NOT rely on deque(maxlen=...) because it silently drops items and
        # bypasses our dropped-record statistics. Enforce buffer_size manually.
        self.buffer = deque()
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

        self._last_ts_per_stream: Dict[str, int] = {}
        self._last_ts_lock = threading.Lock()

        # Estimate of Loki clock offset relative to this process:
        #   loki_time ~= local_time + _loki_time_offset_ns
        # Updated opportunistically from HTTP Date headers on push responses.
        self._loki_time_offset_ns = 0
        self._loki_time_offset_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "records_buffered": 0,
            "records_written": 0,
            "records_dropped": 0,
            "timestamps_clamped": 0,
            "timestamps_monotonic_adjusted": 0,
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
                if len(self.buffer) >= self.buffer_size:
                    if self.overflow_strategy == "drop_newest":
                        # Drop this record
                        with self.stats_lock:
                            self.stats["records_dropped"] += 1
                        return

                    # drop_oldest
                    if self.buffer:
                        self.buffer.popleft()
                        with self.stats_lock:
                            self.stats["records_dropped"] += 1

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

        try:
            standard_attrs = {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "taskName",
            }

            for key, value in (getattr(record, "__dict__", {}) or {}).items():
                if not isinstance(key, str):
                    continue
                if key in standard_attrs:
                    continue
                if key in log_obj:
                    continue
                if key.startswith("_"):
                    continue

                try:
                    json.dumps({key: value}, ensure_ascii=False)
                    log_obj[key] = value
                except Exception:
                    try:
                        log_obj[key] = str(value)
                    except Exception:
                        pass
        except Exception:
            pass

        # Remove None values and JSON-serialize
        log_obj = {k: v for k, v in log_obj.items() if v is not None}
        log_line = json.dumps(log_obj, ensure_ascii=False, separators=(",", ":"))
        
        ts_ns = int(record.created * 1_000_000_000)
        # Defensive: Loki rejects samples too far in the future. If a producer clock
        # drifts or a record has a bad timestamp, clamp to a small future tolerance
        # to avoid silent ingestion gaps.
        now_ns = int(time.time() * 1_000_000_000)
        with self._loki_time_offset_lock:
            loki_offset_ns = int(self._loki_time_offset_ns)

        # Clamp against Loki time, not local time. On dev machines with sleep/wake
        # cycles, Docker/Loki time can drift behind local time, leading to
        # "timestamp too new" rejects even if we clamp against local time.
        loki_now_ns = now_ns + loki_offset_ns
        max_future_ns = loki_now_ns + 10_000_000_000  # 10s tolerance
        if ts_ns > max_future_ns:
            ts_ns = max_future_ns
            with self.stats_lock:
                self.stats["timestamps_clamped"] += 1

        return {
            "timestamp": ts_ns,  # nanoseconds
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

            # Loki expects entries to be ordered by timestamp per stream.
            # Also enforce monotonicity per stream to avoid ingestion rejects
            # during clock adjustments (sleep/wake) or multi-threaded log bursts.
            for label_str, stream in streams.items():
                try:
                    stream["values"].sort(key=lambda v: int(v[0]))
                except Exception:
                    pass

                with self._last_ts_lock:
                    last_ts = self._last_ts_per_stream.get(label_str)

                if last_ts is not None:
                    adjusted = 0
                    prev = last_ts
                    for item in stream["values"]:
                        try:
                            ts = int(item[0])
                        except Exception:
                            continue
                        if ts <= prev:
                            ts = prev + 1
                            item[0] = str(ts)
                            adjusted += 1
                        prev = ts

                    if adjusted:
                        with self.stats_lock:
                            self.stats["timestamps_monotonic_adjusted"] += adjusted

                    with self._last_ts_lock:
                        self._last_ts_per_stream[label_str] = prev
                else:
                    if stream.get("values"):
                        try:
                            last_val = int(stream["values"][-1][0])
                            with self._last_ts_lock:
                                self._last_ts_per_stream[label_str] = last_val
                        except Exception:
                            pass
            
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

            # Opportunistically learn Loki time from the HTTP Date header to
            # compensate for host/container clock skew.
            try:
                self._update_loki_time_offset_from_response(response)
            except Exception:
                pass
            
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

    def _update_loki_time_offset_from_response(self, response: Any) -> None:
        date_header = None
        try:
            date_header = response.headers.get("Date")
        except Exception:
            date_header = None

        if not date_header:
            return

        try:
            dt = email.utils.parsedate_to_datetime(date_header)
        except Exception:
            return

        if dt is None:
            return

        if dt.tzinfo is None:
            # HTTP dates are supposed to be GMT; treat as UTC if tz is missing.
            dt = dt.replace(tzinfo=timezone.utc)

        loki_now_ns = int(dt.timestamp() * 1_000_000_000)
        local_now_ns = int(time.time() * 1_000_000_000)
        offset_ns = loki_now_ns - local_now_ns

        # Clamp insane offsets (e.g., bad headers) to avoid harming ingestion.
        # If offset is outside +/- 6 hours, ignore it.
        if abs(offset_ns) > int(6 * 3600 * 1_000_000_000):
            return

        with self._loki_time_offset_lock:
            # Smooth slightly to avoid jitter.
            prev = int(self._loki_time_offset_ns)
            self._loki_time_offset_ns = int(prev * 0.9 + offset_ns * 0.1)
    
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
