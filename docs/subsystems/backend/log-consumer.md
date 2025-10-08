# Log Consumer Service

## Overview

The Log Consumer Service persists application logs from the ZeroMQ message bus to the encrypted database. It runs as a backend plugin and provides reliable log storage for the entire AICO system.

## Architecture ✅

### Core Components

- **AICOLogConsumer**: Main service class with ZMQ subscription and database persistence
- **Plugin Integration**: Runs as `log_consumer` plugin in backend service container
- **Message Bus Subscription**: Connects to port 5556 with `logs.*` topic filtering
- **Database Storage**: Persists to encrypted `aico.db` logs table

### Message Flow ✅

```
Application Logger → ZMQ Transport → Message Bus (5555/5556) → Log Consumer → Database
```

**Current Implementation**:
1. **Logger** creates LogEntry protobuf message
2. **ZMQ Transport** sends to message bus on `logs.*` topics
3. **Message Bus Broker** routes to subscriber port 5556
4. **Log Consumer** processes and inserts to encrypted database

## Implementation ✅

### ZMQ Subscription

```python
# Direct ZMQ subscription to message bus
self.subscriber = self.context.socket(zmq.SUB)
self.subscriber.connect(f"tcp://localhost:5556")
self.subscriber.setsockopt(zmq.SUBSCRIBE, b"logs.")
```

### LogEntry Processing

**Protobuf Fields**:
- `timestamp`: ISO datetime string
- `level`: LogLevel enum (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `subsystem`: Component name (e.g., "api_gateway", "backend")
- `module`: Module identifier
- `function`: Function name
- `message`: Log message text
- `extra`: JSON metadata (optional)

### Database Schema ✅

**Logs Table** (encrypted libSQL):
```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    subsystem TEXT NOT NULL,
    module TEXT NOT NULL,
    function_name TEXT,
    message TEXT NOT NULL,
    extra TEXT  -- JSON metadata
);
```

### Plugin Lifecycle ✅

- **Plugin Loading**: Initialized via backend service container
- **Background Thread**: Runs message processing loop in separate thread
- **Graceful Shutdown**: Responds to plugin stop() method
- **Error Recovery**: Continues processing despite individual message failures

## Configuration ✅

**Message Bus Settings** (`config/defaults/core.yaml`):
```yaml
core:
  message_bus:
    host: "localhost"
    pub_port: 5555    # Publisher port
    sub_port: 5556    # Subscriber port
```

## Backend Integration ✅

### Plugin System

**Startup Sequence**:
1. **Message Bus Plugin** starts ZMQ broker (ports 5555/5556)
2. **Log Consumer Plugin** initializes and connects to subscriber port
3. **Shared Resources** use same encrypted database connection
4. **Coordinated Lifecycle** with other backend plugins

**Current Status**: Active plugin in production backend

## Performance ✅

**Characteristics**:
- **Throughput**: Handles typical application log volume efficiently
- **Memory**: Minimal footprint with streaming message processing
- **Error Handling**: Individual message failures don't stop service
- **Database**: Efficient single-row insertions with proper error handling

## Monitoring ✅

### Service Status
```bash
# Check if log consumer is active
aico gateway status  # Shows active plugins

# View recent logs
aico logs tail

# Test message bus connectivity
aico bus test
```

### Debug Information
- **Plugin Status**: Visible in backend startup logs
- **Message Processing**: Debug output shows successful insertions
- **Database Health**: Verified via CLI log retrieval

## Security ✅

**Data Protection**:
- **Encrypted Database**: All logs stored in encrypted `aico.db`
- **Local Processing**: No external log transmission
- **Access Control**: Database restricted to backend service
- **CurveZMQ**: Message bus encryption for transport security

**Privacy**:
- **Local-First**: All processing on user device
- **User Control**: Complete control over log retention
- **No Telemetry**: Logs never transmitted externally

## Troubleshooting ✅

**Common Issues**:
1. **No Logs**: Check if message bus plugin is active
2. **Database Errors**: Verify encryption key and database initialization
3. **Connection Issues**: Ensure backend service is running

**Diagnostic Commands**:
```bash
aico gateway status    # Check plugin status
aico logs tail         # View recent logs
aico db status         # Database health
aico bus test          # Message bus connectivity
```
