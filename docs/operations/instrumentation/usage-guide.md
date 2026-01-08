# OpenTelemetry Instrumentation Usage Guide

## Overview

AICO uses OpenTelemetry for comprehensive system instrumentation. Metrics are automatically collected and stored in the encrypted `aico.db` database, feeding the Studio dashboard.

## Automatic Instrumentation

### API Gateway

**Automatic** - All HTTP requests are tracked automatically via middleware.

No code changes needed. Metrics collected:
- Request method and path
- Response status code
- Request latency
- Protocol type

## Manual Instrumentation

### Modelservice

Track model inference performance:

```python
from modelservice.core.metrics import track_inference

# Context manager approach (recommended)
with track_inference("llama-3.2-3b", task_type="completion") as tracker:
    result = model.generate(prompt)
    tracker.set_tokens(len(result.tokens))
    tracker.set_success(True)

# Direct recording
from modelservice.core.metrics import record_inference

record_inference(
    model_name="llama-3.2-3b",
    duration_seconds=0.5,
    tokens=150,
    success=True,
    task_type="completion"
)
```

### Memory System

Track memory query performance:

```python
from aico.ai.memory.metrics import track_query

# Context manager approach
with track_query("semantic_search", memory_layer="semantic") as tracker:
    results = semantic_memory.search(query, limit=10)
    tracker.set_results_count(len(results))
    tracker.set_success(True)

# Direct recording
from aico.ai.memory.metrics import record_query

record_query(
    query_type="episodic_retrieval",
    duration_seconds=0.1,
    results_count_value=5,
    success=True,
    memory_layer="episodic"
)
```

### Scheduler

Track job execution:

```python
from backend.services.scheduler.metrics import track_job

# Context manager approach
with track_job("maintenance.database_vacuum", queue_name="maintenance") as tracker:
    try:
        perform_vacuum()
        tracker.set_success(True)
    except Exception as e:
        tracker.set_success(False)
        tracker.set_error(str(e))

# Direct recording
from backend.services.scheduler.metrics import record_job

record_job(
    job_type="ams.memory_consolidation",
    duration_seconds=2.5,
    success=True,
    queue_name="background"
)
```

### Message Bus

Track message processing:

```python
from aico.core.bus.metrics import track_message

# Context manager approach
with track_message("conversation.input") as tracker:
    process_message(msg)
    tracker.set_backlog_depth(current_backlog)
    tracker.set_consumer_count(active_consumers)

# Direct recording
from aico.core.bus.metrics import record_message

record_message(
    topic="logs.backend",
    duration_seconds=0.05,
    backlog_depth=0,
    consumer_count=1
)
```

## Metrics Storage

All metrics are stored in the encrypted `aico.db` database:

- **`otel_api_requests`** - API Gateway HTTP requests
- **`otel_model_inferences`** - Modelservice inference operations
- **`otel_memory_queries`** - Memory system queries
- **`otel_scheduler_jobs`** - Scheduler job executions
- **`otel_message_bus_events`** - Message bus events

## Querying Metrics

### Via CLI

```bash
# Query API request metrics
uv run aico db query "SELECT * FROM otel_api_requests ORDER BY timestamp DESC LIMIT 10"

# Query model inference metrics
uv run aico db query "SELECT model_name, AVG(inference_time_ms) as avg_time FROM otel_model_inferences GROUP BY model_name"

# Query memory performance
uv run aico db query "SELECT query_type, AVG(query_time_ms) as avg_time FROM otel_memory_queries GROUP BY query_type"
```

### Via Studio Dashboard

Metrics are automatically displayed in the Studio Metrics tab with:
- Real-time charts
- Performance trends
- System health indicators

## Best Practices

1. **Use context managers** - Automatically handles timing and error cases
2. **Set success status** - Always indicate whether operation succeeded
3. **Include relevant attributes** - Add context-specific metadata
4. **Don't over-instrument** - Focus on critical paths and bottlenecks
5. **Monitor slow operations** - API Gateway automatically logs requests >1s

## Configuration

Instrumentation is configured in `config/defaults/core.yaml`:

```yaml
instrumentation:
  mode: dev  # casual, pro, dev, production
  opentelemetry:
    enabled: true
  exporters:
    prometheus:
      enabled: false  # Enable for Prometheus scraping
    otlp:
      enabled: false  # Enable for Jaeger/Tempo tracing
```

## Modes

- **casual** (default) - Local metrics only, no exporters
- **pro** - Local metrics + optional exporters (user opt-in)
- **dev** - All exporters enabled for development
- **production** - All exporters with security controls

## Privacy

All metrics are:
- Stored locally in encrypted database
- Never sent externally by default
- PII-free (no user data in metrics)
- Configurable retention policies

## Troubleshooting

### Metrics not appearing

1. Check OpenTelemetry initialization in backend logs:
   ```
   [✓] OpenTelemetry initialized (mode: dev)
   [✓] Local metrics storage: Enabled (encrypted)
   ```

2. Verify tables exist:
   ```bash
   uv run aico db query "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'otel_%'"
   ```

3. Check for errors in storage adapter:
   ```bash
   uv run aico logs query --service backend --level ERROR --last 1h
   ```

### High overhead

Metrics collection is designed to be lightweight (<1% overhead), but if you notice performance issues:

1. Reduce metric collection frequency in storage adapter
2. Disable non-critical instrumentation
3. Use sampling for high-volume operations

## Next Steps

- Add custom metrics for your specific use cases
- Configure Prometheus/Grafana for visualization
- Set up alerting based on metric thresholds
- Integrate with health monitoring system
