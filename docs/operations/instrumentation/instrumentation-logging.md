---
title: Unified Logging Implementation Guide
---

# Unified Logging Implementation

This guide covers implementing unified, privacy-first logging across frontend (Flutter) and backend (Python) components in AICO.

---

## Log Schema

Standardized JSON structure for all log messages:

```json
{
  "timestamp": "2025-08-02T23:10:00Z",
  "level": "INFO",
  "module": "frontend.conversation_ui",
  "function": "sendMessage",
  "file": "conversation_screen.dart",
  "line": 42,
  "topic": "ui/button/click",
  "message": "User clicked Send",
  "trace_id": "abc123",
  "session_id": "session-123"
}
```

**Required:** `timestamp`, `level`, `module`, `function`, `topic`, `message`  
**Optional:** `file`, `line`, `trace_id`, `session_id`, `extra`, `error_details`

---

## Frontend (Flutter)

**Implementation:**
- Create Dart logging utility using shared schema
- Include `module`, `function`, `file`/`line` in all logs
- Send to backend via WebSocket/HTTP POST
- Local buffering with retry strategy and fallback

**Example:**

```dart
void logEvent({
  required String level,
  required String module,
  required String functionName,
  required String topic,
  required String message,
  String? file,
  int? line,
  String? traceId,
  String? sessionId,
}) {
  final log = {
    'timestamp': DateTime.now().toIso8601String(),
    'level': level,
    'module': module,
    'function': functionName,
    'topic': topic,
    'message': message,
    if (file != null) 'file': file,
    if (line != null) 'line': line,
    if (traceId != null) 'trace_id': traceId,
    if (sessionId != null) 'session_id': sessionId,
  };
  _sendLog(log);
}

// Usage
logEvent(
  level: 'INFO',
  module: 'frontend.conversation_ui',
  functionName: 'sendMessage',
  topic: 'ui/button/click',
  message: 'User clicked Send',
);
```

---

## Backend (Python)

**Implementation:**
- Use `create_infrastructure_logger()` from `aico.core.logging_context` for infrastructure components
- Use standard Python `logging` for components that must avoid circular dependencies
- Include `module`, `function`, `file`/`line` in all logs
- Publish to ZeroMQ message bus under `logs.*` topics
- Local buffering with retry strategy and fallback

**Infrastructure vs Standard Logging:**
- **Infrastructure Logger**: For most backend services (prevents circular dependencies with core logging system)
- **Standard Logger**: For logging transport, message bus, and database components that support the logging infrastructure itself

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

**Safe logging pattern:**
- ✅ Use `create_infrastructure_logger()` for all backend services
- ❌ Never mix different logger types in the same service
- ❌ Never log inside logging transport code

**Example:**
```python
from aico.core.logging_context import create_infrastructure_logger

class MyService:
    def __init__(self):
        self.logger = create_infrastructure_logger("my_service")
    
    def process_request(self):
        self.logger.info("Processing request", extra={
            "module": "backend.my_service",
            "function": "process_request",
            "topic": "service.request"
        })
```

---

## Retention & Rollover

- **Maximum File Size:** 100MB
- **Retention Period:** 30 days
- **Rotation Method:** Daily rotation with compression (e.g., gzip)

---

## Backend Bridge

Lightweight service receiving logs from Flutter frontend and republishing to ZeroMQ:

```python
from flask import Flask, request
import zmq

app = Flask(__name__)
socket = zmq.Context().socket(zmq.PUB)
socket.connect("tcp://127.0.0.1:5555")

@app.route('/log', methods=['POST'])
def receive_log():
    log_event = request.get_json()
    socket.send_json(log_event)
    return '', 204
```

**Note:** Backend bridge is mandatory for reliable Flutter-to-ZeroMQ logging.


---

## Central Log Collector & Storage

**Implementation:**
- Subscribe to `logs.*` topics on ZeroMQ bus
- Store in dedicated `logs` table in libSQL (encrypted)
- Enable fast search, filtering, correlation
- Support privacy and retention policies
- Provide CLI/dashboard for log viewing

**Benefits:** Fast issue tracing with `module`, `function`, `file`, `line` context

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

For advanced analytics, periodic ETL (Extract-Transform-Load) can move log data from libSQL to analytical databases (DuckDB planned). This process prepares logs for observability, dashboards, and automated insights:

- **Why?** Analytical databases are optimized for queries, aggregations, and dashboarding on large datasets.
- **When?** Run ETL on a schedule (e.g., hourly, daily) or trigger on demand.
- **Status:** Currently uses libSQL only; DuckDB integration planned.

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

### Example: Aggregation in libSQL (Current)
```sql
-- Daily error counts by module
SELECT
  date(timestamp) AS day,
  module,
  COUNT(*) AS error_count
FROM logs
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

- Never log sensitive data (PII, secrets)
- Respect user privacy and retention policies
- Tag logs by origin (`frontend`/`backend`)
- Use log rotation and local-first storage
- Always include function and file/line context

## End-to-End Flow

1. **Flutter** → JSON log → WebSocket/HTTP → Backend bridge
2. **Backend bridge** → ZeroMQ republish
3. **Backend modules** → Direct ZeroMQ logging
4. **Central collector** → Subscribe `logs.*` → Store in libSQL

---

## References
- [ZeroMQ](https://zeromq.org/)
- [Python logging](https://docs.python.org/3/library/logging.html)
- [inspect module](https://docs.python.org/3/library/inspect.html)
- [Dart logging](https://pub.dev/packages/logger)
- [AICO Instrumentation Architecture](instrumentation.md)
