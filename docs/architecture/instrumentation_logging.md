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
  "extra": { ... }               // optional, any additional context
}
```

- **Required fields:** `timestamp`, `level`, `module`, `function`, `topic`, `message`
- **Recommended fields:** `file`, `line` (if available)
- **Optional fields:** `user_id`, `trace_id`, `extra`

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
  };
  // Send via WebSocket/HTTP
  websocket.send(jsonEncode(log));
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
- **Example:**

```python
import json
import zmq
import inspect
from datetime import datetime

def log_event(level, module, topic, message, extra=None):
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
    }
    socket.send_json(log_event)

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

## Backend Bridge for Frontend Logs

### Cross-Platform Requirement
A backend bridge is the **required and default solution** for forwarding frontend (Flutter) logs to the ZeroMQ message bus. This is necessary because:
- Direct ZeroMQ publishing from Flutter is **not reliably supported across all target platforms** (Linux, macOS, iOS, Android, Windows).
- The `dartzmq` package only supports a subset of platforms (Windows, Android) and requires complex native setup.
- For a robust, portable, and maintainable architecture, **all frontend logs should be sent to a backend bridge via HTTP or WebSocket**.

### Bridge Architecture
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

## 5. Central Log Collector & Storage

- Subscribe to `logs.*` topics on the ZeroMQ bus.
- Store logs locally (e.g., file, SQLite, or log management service).
- Provide CLI or dashboard for unified log viewing.
- **Pinpointing Issues:** With `module`, `function`, `file`, and `line`, you can quickly trace the source of any problem.

---

## 6. Privacy & Best Practices

- Never log sensitive data (PII, secrets, etc.).
- Respect user privacy settings and retention policies.
- Tag logs clearly by origin (`frontend` or `backend`).
- Use log rotation and local-first storage.
- Document all log topics and schemas in code and docs.
- **Always include function and file/line for actionable logs.**

---

## 7. Example End-to-End Flow

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
