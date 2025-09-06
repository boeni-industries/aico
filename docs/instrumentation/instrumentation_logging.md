---
title: Unified Logging Implementation Guide
---

# Unified Logging: Frontend (Flutter) & Backend (Python)

This document provides a step-by-step, directly usable guide for implementing unified, privacy-first logging across both the frontend (Flutter) and backend (Python) in AICO. It covers schema, transport, integration patterns, and best practices to ensure all logs are collected, stored, and visualized together.

---

## Log Envelope Schema

Define a JSON structure for all log messages. Both frontend and backend MUST use this schema:

```json
{
  "timestamp": "2025-08-02T23:10:00Z",
  "level": "INFO",            // INFO, WARNING, ERROR, DEBUG
  "module": "frontend.chat_ui", // e.g., frontend.chat_ui, backend.llm
  "function": "sendMessage",     // Calling function or method name
  "file": "chat_screen.dart",    // (optional) Source file
  "line": 42,                    // (optional) Line number
  "topic": "ui.button.click",   // Event/topic name
  "message": "User clicked Send",
  "user_id": "local-user-123", // optional, if available
  "trace_id": "abc123",         // optional, for tracing
  "extra": { ... },               // optional, any additional context
  "severity": "low",             // optional, severity level (low, medium, high)
  "origin": "frontend",          // optional, log origin (frontend, backend)
  "environment": "dev",         // optional, environment (dev, prod, staging)
  "session_id": "session-123",  // optional, session ID
  "error_details": { ... }       // optional, error details if applicable
}
```

- **Required fields:** `timestamp`, `level`, `module`, `function`, `topic`, `message`
- **Recommended fields:** `file`, `line` (if available)
- **Optional fields:** `user_id`, `trace_id`, `extra`, `severity`, `origin`, `environment`, `session_id`, `error_details`

**Why?** Including the calling function, and optionally file/class/line, makes it much easier to pinpoint the source of issues during debugging, especially in a distributed system.

---

## Frontend (Flutter)

- Create a Dart logging utility that formats logs per the shared schema.
- **Always include:**
  - `module`: e.g., `frontend.chat_ui`
  - `function`: Use Dart's `StackTrace.current` or pass the function name explicitly
  - `file`/`line`: Use a logging helper or macro if possible, or pass manually
- Serialize logs to JSON.
- **Transport:** Send logs to the backend via WebSocket or HTTP POST.
- **Failure Handling:**
  - Implement local buffering with a maximum size (e.g., 1000 logs) to handle temporary network failures.
  - Use a retry strategy with exponential backoff (e.g., 1s, 2s, 4s, 8s) for failed log sends.
  - Fallback to a local log file if all retry attempts fail.
- **Example:**

```dart
void logEvent({
  required String level,
  required String module,
  required String functionName,
  required String topic,
  required String message,
  String? file,
  int? line,
  String? userId,
  String? traceId,
  Map<String, dynamic>? extra,
  String? severity,
  String? origin,
  String? environment,
  String? sessionId,
  Map<String, dynamic>? errorDetails,
}) {
  final log = {
    'timestamp': DateTime.now().toIso8601String(),
    'level': level,
    'module': module,
    'function': functionName,
    'file': file,
    'line': line,
    'topic': topic,
    'message': message,
    'user_id': userId,
    'trace_id': traceId,
    'extra': extra,
    'severity': severity,
    'origin': origin,
    'environment': environment,
    'session_id': sessionId,
    'error_details': errorDetails,
  };
  // Send via WebSocket/HTTP with retry and fallback
  _sendLog(log);
}

// Usage
logEvent(
  level: 'INFO',
  module: 'frontend.chat_ui',
  functionName: 'sendMessage',
  topic: 'ui.button.click',
  message: 'User clicked Send',
  file: 'chat_screen.dart',
  line: 42,
);
```

- **Best Practice:** Tag all frontend logs with `module: frontend.*` and always specify the function.

---

## Backend (Python)

- Use Python logging or a custom logger to emit logs in the same envelope format.
- **Always include:**
  - `module`: e.g., `backend.llm`
  - `function`: Use `inspect.currentframe()` or a logging helper to capture the calling function
  - `file`/`line`: Use `__file__` and `inspect` to capture file and line number
- **Transport:** Publish logs directly to the ZeroMQ message bus under topic `logs.frontend.*` or `logs.backend.*`.
- **Failure Handling:**
  - Implement local buffering with a maximum size (e.g., 1000 logs) to handle temporary network failures.
  - Use a retry strategy with exponential backoff (e.g., 1s, 2s, 4s, 8s) for failed log sends.
  - Fallback to a local log file if all retry attempts fail.

### ⚠️ CRITICAL WARNING: Logging Recursion Loops

**🚨 DANGER: Improper logging implementations can create infinite recursion loops that crash the entire system.**

**NEVER log within logging transport or handler code:**
- ❌ **NEVER call `logger.info()`, `logger.error()`, etc. inside ZMQ transport methods**
- ❌ **NEVER log inside message bus send/receive operations**  
- ❌ **NEVER log inside database write operations for log storage**
- ❌ **NEVER log inside log consumer or log handler methods**

**Use print() statements for debugging logging infrastructure:**
```python
# CORRECT - debugging logging system itself
def _send_log_to_zmq(self, log_data):
    try:
        self.socket.send_json(log_data)
        print(f"[ZMQ TRANSPORT] Log sent successfully")  # ✅ Safe
    except Exception as e:
        print(f"[ZMQ TRANSPORT] Failed to send: {e}")    # ✅ Safe
        # self.logger.error(f"Send failed: {e}")         # ❌ RECURSION!
```

**Why this matters:** When logging code tries to log its own operations, it creates infinite recursion:
1. Logger tries to send message via ZMQ
2. ZMQ transport logs the send operation  
3. This creates another log message to send
4. Loop continues until stack overflow crashes the system

**Infrastructure logger pattern prevents this:**
- ✅ **Use `create_infrastructure_logger()` from `aico.core.logging_context` for all backend services**
- ❌ **NEVER mix `get_logger()` and `create_infrastructure_logger()` in the same service**
- ❌ **NEVER import logging functions that may not be available in service contexts**
- **Example:**

```python
import json
import zmq
import inspect
from datetime import datetime

def log_event(level, module, topic, message, extra=None, severity=None, origin=None, environment=None, session_id=None, error_details=None):
    frame = inspect.currentframe().f_back
    function = frame.f_code.co_name
    file = frame.f_code.co_filename
    line = frame.f_lineno
    log_event = {
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "level": level,
        "module": module,
        "function": function,
        "file": file,
        "line": line,
        "topic": topic,
        "message": message,
        "extra": extra,
        "severity": severity,
        "origin": origin,
        "environment": environment,
        "session_id": session_id,
        "error_details": error_details,
    }
    # Send to ZeroMQ with retry and fallback
    _send_log(log_event)

# Usage
log_event(
    level="INFO",
    module="backend.llm",
    topic="llm.inference",
    message="LLM generated response"
)
```

- **Best Practice:** Tag all backend logs with `module: backend.*` and always specify the function.

---

## Retention & Rollover

- **Maximum File Size:** 100MB
- **Retention Period:** 30 days
- **Rotation Method:** Daily rotation with compression (e.g., gzip)

---

## Backend Bridge

- The backend bridge is a lightweight service (e.g., Python Flask app) that receives logs from the Flutter frontend via HTTP or WebSocket and republishes them to ZeroMQ under `logs.frontend.*`.
- The bridge can enrich logs with function/file/line info if needed.

**Example Flask Bridge:**
```python
from flask import Flask, request
import zmq

app = Flask(__name__)
socket = zmq.Context().socket(zmq.PUB)
socket.connect("tcp://127.0.0.1:5555")

@app.route('/log', methods=['POST'])
def receive_log():
    log_event = request.get_json()
    # Optionally enrich with backend info here
    socket.send_json(log_event)
    return '', 204
```

- Point the Flutter HTTP log sender to the `/log` endpoint of this bridge.

**Summary:**
- The backend bridge is **mandatory** for reliable, cross-platform logging from Flutter to ZeroMQ.
- Do **not** attempt direct ZeroMQ publishing from Flutter in production, regardless of platform.


---

## Central Log Collector & Storage

- Subscribe to `logs.*` topics on the ZeroMQ bus.
- **Store logs in a dedicated `logs` table in libSQL** (AICO’s structured, encrypted database).
    - This enables fast search, filtering, and correlation by timestamp, user, session, etc.
    - Supports privacy, retention, and deletion policies directly at the database level.
    - Integrates with the repository/data access pattern used throughout AICO.
- Optionally, mirror recent logs to file for redundancy or debugging (not the primary store).
- Provide CLI or dashboard for unified log viewing and querying.
- **Pinpointing Issues:** With `module`, `function`, `file`, and `line`, you can quickly trace the source of any problem.

**Example: Log Table Schema (libSQL)**
```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    module TEXT NOT NULL,
    function TEXT,
    file TEXT,
    line INTEGER,
    topic TEXT,
    message TEXT,
    user_id TEXT,
    trace_id TEXT,
    session_id TEXT,
    error_details TEXT,
    extra JSON,
    severity TEXT,
    origin TEXT,
    environment TEXT
);
```

- Enforce retention (e.g., delete logs older than 30 days) via scheduled jobs or background tasks.
- All log writes and queries should use the repository/data access layer for consistency and testability.

---

## ETL to Analytics Engine

For advanced analytics, periodic ETL (Extract-Transform-Load) moves log data from libSQL to DuckDB. This process is not just a copy—it prepares logs for observability, dashboards, and automated insights:

- **Why?** DuckDB is optimized for analytical queries, aggregations, and dashboarding on large datasets.
- **When?** Run ETL on a schedule (e.g., hourly, daily) or trigger on demand.

### What Happens During ETL?

1. **Parsing & Normalization**
    - Standardize all timestamps (e.g., convert to UTC, ISO8601).
    - Ensure field types are correct (e.g., integers, categories, booleans).
2. **Flattening & Enrichment**
    - Flatten nested JSON fields (e.g., `error_details`, `extra`) into top-level columns for fast queries.
    - Add derived fields: error type, stack hash, severity bucket, etc.
    - Optionally join with user/session tables for richer analytics.
3. **Privacy Scrubbing**
    - Remove or mask any sensitive data before analytics.
    - Drop or anonymize fields as required by privacy policy.
4. **Filtering**
    - Exclude low-value logs (e.g., DEBUG) if not needed for analytics.
    - Filter out logs outside the retention window.
5. **Aggregation & Summarization**
    - Precompute rollups (e.g., error counts per module/day, mean response time).
    - Store trend tables for dashboards.
6. **Indexing & Partitioning**
    - Partition analytics tables by day/week/month for fast queries.
    - Index on key columns (timestamp, level, module, user_id).

### Example: ETL Transformations (Python)
```python
def transform_log(row):
    # Parse timestamp to datetime (UTC)
    row['timestamp'] = parse_iso8601(row['timestamp'])
    # Flatten error_details JSON
    if row.get('error_details'):
        error = json.loads(row['error_details'])
        row['error_type'] = error.get('type')
        row['error_message'] = error.get('message')
        row['error_stack'] = error.get('stack')
    # Flatten extra JSON
    if row.get('extra'):
        extra = json.loads(row['extra'])
        for k, v in extra.items():
            row[f'extra_{k}'] = v
    # Map level to severity bucket
    row['severity_bucket'] = map_severity(row['level'])
    # Remove raw JSON fields for analytics
    row.pop('error_details', None)
    row.pop('extra', None)
    return row
```

### Example: Aggregation in DuckDB
```sql
-- Daily error counts by module
SELECT
  date_trunc('day', timestamp) AS day,
  module,
  COUNT(*) AS error_count
FROM logs_analytics
WHERE level = 'ERROR'
GROUP BY day, module
ORDER BY day DESC, error_count DESC;
```

**Key Benefits:**
- Clean, queryable analytics tables for dashboards and monitoring
- Fast aggregation and trend analysis
- Privacy and compliance by design
- Efficient storage and retrieval for observability

---

## Privacy & Best Practices

- Never log sensitive data (PII, secrets, etc.).
- Respect user privacy settings and retention policies.
- Tag logs clearly by origin (`frontend` or `backend`).
- Use log rotation and local-first storage.
- Document all log topics and schemas in code and docs.
- **Always include function and file/line for actionable logs.**

---

## Example End-to-End Flow

1. Flutter emits log as JSON (with module/function/file/line) → sends to backend via WebSocket/HTTP.
2. Backend bridge receives log → republishes to ZeroMQ.
3. Backend modules emit logs directly to ZeroMQ (with full context).
4. Central collector subscribes to `logs.*` → stores, rotates, and serves logs for dashboards or CLI.

---

## References
- [ZeroMQ](https://zeromq.org/)
- [Python logging](https://docs.python.org/3/library/logging.html)
- [inspect module](https://docs.python.org/3/library/inspect.html)
- [Dart logging](https://pub.dev/packages/logger)
- [AICO Instrumentation Architecture](instrumentation.md)
