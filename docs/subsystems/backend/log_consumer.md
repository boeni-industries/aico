# Log Consumer Service Architecture

## Overview

The Log Consumer Service is a critical component of AICO's logging pipeline that bridges the gap between ZeroMQ log transport and database persistence. It runs as part of the backend service and ensures all log messages are reliably persisted to the encrypted database.

## Architecture

### Components

- **AICOLogConsumer**: Main service class managing ZMQ subscription and database persistence
- **ZMQ Subscription**: Connects to message bus subscriber port (5556) with topic filtering
- **Protobuf Processing**: Deserializes Protocol Buffer LogEntry messages
- **Database Integration**: Persists logs to encrypted libSQL database
- **Threading Model**: Runs in dedicated thread for non-blocking operation

### Message Flow

```
Logger → ZMQ Transport → Message Bus Broker → Log Consumer → Encrypted Database
```

1. **Log Generation**: Application loggers create structured log entries
2. **ZMQ Transport**: Logs serialized as Protocol Buffers and sent via ZMQ
3. **Message Bus**: Broker routes messages to subscriber port with topic filtering
4. **Log Consumer**: Subscribes to `logs.*` topics and processes messages
5. **Database Persistence**: Converts protobuf to SQL and inserts into logs table

## Implementation Details

### ZMQ Integration

```python
# Connects to message bus subscriber port
sub_port = self.config_manager.get("message_bus.sub_port", 5556)
self.subscriber = self.context.socket(zmq.SUB)
self.subscriber.connect(f"tcp://{host}:{sub_port}")
self.subscriber.setsockopt(zmq.SUBSCRIBE, b"logs.")
```

### Protobuf Processing

The service processes `LogEntry` protobuf messages with these fields:
- `timestamp`: ISO datetime with timezone
- `level`: Log level enum (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `subsystem`: Component identifier (e.g., "api_gateway", "backend")
- `module`: Module name within subsystem
- `function`: Function name where log originated
- `message`: Log message content
- `extra`: JSON metadata for structured logging

### Database Schema

Logs are persisted to the `logs` table with encrypted storage:

```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    subsystem TEXT NOT NULL,
    module TEXT NOT NULL,
    function_name TEXT,
    file_path TEXT,
    line_number INTEGER,
    topic TEXT,
    message TEXT NOT NULL,
    user_uuid TEXT,
    session_id TEXT,
    trace_id TEXT,
    extra TEXT
);
```

### Threading and Lifecycle

- **Threaded Operation**: Runs in daemon thread to avoid blocking main process
- **Graceful Shutdown**: Responds to `running` flag for clean termination
- **Error Handling**: Continues operation despite individual message failures
- **Resource Cleanup**: Properly closes ZMQ sockets and database connections

## Configuration

The log consumer is configured via the message bus section:

```yaml
message_bus:
  host: "localhost"
  pub_port: 5555      # Publisher port (broker frontend)
  sub_port: 5556      # Subscriber port (broker backend)
```

## Integration with Backend

### Plugin System Integration

The log consumer is started as part of the API Gateway plugin system:

1. **Message Bus Plugin**: Starts ZMQ broker on configured ports
2. **Log Consumer Plugin**: Initializes and starts log consumer service
3. **Shared Database**: Uses same encrypted connection as other components
4. **Lifecycle Management**: Coordinated startup/shutdown with other plugins

### Process Management

- **Foreground Mode**: Debug output enabled when `AICO_DETACH_MODE=false`
- **Background Mode**: Silent operation for daemon/service deployment
- **Signal Handling**: Responds to graceful shutdown signals
- **Error Recovery**: Continues operation despite transient failures

## Performance Characteristics

### Throughput
- **High Volume**: Designed to handle 1000+ messages per second
- **Batch Processing**: Processes all available messages in each poll cycle
- **Low Latency**: Sub-100ms message processing under normal load

### Resource Usage
- **Memory**: Minimal memory footprint with streaming processing
- **CPU**: Low CPU usage with efficient protobuf deserialization
- **I/O**: Optimized database insertions with transaction management

### Error Handling
- **Message Failures**: Individual message failures don't stop processing
- **Connection Issues**: Automatic reconnection on ZMQ socket errors
- **Database Errors**: Proper rollback and error logging
- **Shutdown Race**: Handles database connection closure during shutdown

## Monitoring and Debugging

### Debug Output
When running in foreground mode (`AICO_DETACH_MODE=false`):
- ZMQ context type and connection status
- Message processing statistics
- Database operation confirmations
- Error details and recovery actions

### Log Levels
- **INFO**: Service lifecycle events (start, stop, connection status)
- **WARNING**: Recoverable errors (message parsing failures)
- **ERROR**: Serious issues (database connection problems)

### Health Checks
The service health can be monitored through:
- Backend health endpoint status
- Database log insertion verification
- ZMQ connection status
- Message processing metrics

## Security Considerations

### Data Protection
- **Encrypted Storage**: All logs stored in encrypted libSQL database
- **Key Management**: Uses derived keys from master key via AICOKeyManager
- **Transport Security**: ZMQ messages can use CurveZMQ for encryption
- **Access Control**: Database access restricted to backend service

### Privacy
- **Local Processing**: All log processing occurs locally
- **No External Transmission**: Logs never leave the local system
- **User Control**: Users control log retention and access policies
- **Audit Trail**: Log consumer operations are themselves logged

## Troubleshooting

### Common Issues
1. **No Logs Appearing**: Check ZMQ broker status and topic subscriptions
2. **Database Errors**: Verify encryption key availability and database permissions
3. **High Memory Usage**: Check for message processing backlogs
4. **Connection Failures**: Verify message bus configuration and port availability

### Diagnostic Commands
```bash
# Check backend service status
aico gateway status

# View recent logs
aico logs tail

# Test database connectivity
aico db status

# Monitor message bus
aico bus test
```
