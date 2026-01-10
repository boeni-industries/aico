# AICO Metrics API v2.0

**Modern, modular metrics system built on InfluxDB with clean architecture.**

## Overview

Complete architectural overhaul of the metrics system with:
- ✅ **Zero LibSQL dependencies** - 100% InfluxDB-native
- ✅ **Modular design** - Separated concerns, easy to maintain
- ✅ **Type-safe** - Full Pydantic validation
- ✅ **Testable** - Pure functions, dependency injection
- ✅ **Performant** - Optimized Flux queries
- ✅ **Documented** - Comprehensive inline docs

## Architecture

```
backend/api/metrics/
├── __init__.py                 # Package exports
├── models.py                   # Pydantic response models (DRY)
├── influx_client.py           # InfluxDB query abstraction
├── router.py                  # Main router (aggregates endpoints)
├── endpoints/
│   ├── gateway.py             # API Gateway metrics
│   ├── modelservice.py        # Model inference metrics
│   ├── memory.py              # Memory system metrics
│   ├── scheduler.py           # Task scheduler metrics
│   ├── messagebus.py          # Message bus metrics
│   └── system.py              # System health metrics
└── README.md                  # This file
```

## Design Principles

### 1. **Single Responsibility**
Each module has one clear purpose:
- `models.py` - Data models only
- `influx_client.py` - Query logic only
- `endpoints/*.py` - Endpoint handlers only

### 2. **DRY (Don't Repeat Yourself)**
- Shared models in `models.py`
- Reusable query helpers in `influx_client.py`
- Common utilities (percentile, trend, status)

### 3. **Type Safety**
- Full type hints throughout
- Pydantic models for validation
- No `Any` types where avoidable

### 4. **Testability**
- Pure functions where possible
- Dependency injection via context managers
- Mockable InfluxDB client

### 5. **Performance**
- Optimized Flux queries
- Batch operations
- Efficient aggregations

### 6. **Maintainability**
- Clear module boundaries
- Comprehensive documentation
- Consistent patterns

## Key Components

### `models.py`
Centralized Pydantic models for all metrics responses:
- `MetricValue` - Rich metric with trend, status, sparklines
- `GatewayMetrics` - API performance metrics
- `ModelserviceMetrics` - Inference metrics
- `MemoryMetrics` - Memory system metrics
- `SchedulerMetrics` - Task scheduler metrics
- `MessageBusMetrics` - Message bus metrics
- `SystemHealthMetrics` - Overall health

### `influx_client.py`
High-level InfluxDB query abstraction:
- `MetricsInfluxClient` - Context manager for queries
- `count_points()` - Count data points
- `mean_field()` - Calculate field average
- `percentile_field()` - Calculate percentiles
- `group_count()` - Group and count by tag
- `sparkline()` - Generate time-series data

Helper functions:
- `calculate_percentile()` - Client-side percentile
- `calculate_trend()` - Percentage change
- `get_metric_status()` - Status from thresholds

### `endpoints/*.py`
Individual endpoint modules:
- **gateway.py** - API Gateway performance
  - Request throughput (RPS)
  - Response times (avg, P95, P99)
  - Error rates
  - Status code distribution
  - Top endpoints
  - Protocol distribution

- **modelservice.py** - Model inference
  - LLM metrics (TTFT, TPS, latency)
  - NER metrics (entities, types)
  - Sentiment metrics (confidence, distribution)
  - Embeddings metrics (throughput, dimensions)

- **memory.py** - Memory system
  - Working memory size
  - Semantic query performance
  - Knowledge graph statistics
  - Storage breakdown

- **scheduler.py** - Task scheduler
  - Job execution stats
  - Success/failure rates
  - Queue utilization
  - Job type distribution

- **messagebus.py** - Message bus
  - Message throughput
  - Backlog depth
  - Topic statistics
  - Latency by topic

- **system.py** - System health
  - Overall health score
  - Component status
  - Resource utilization
  - System-wide metrics

## Usage

### Import in Backend

```python
from backend.api.metrics import router as metrics_router

app.include_router(metrics_router)
```

### API Endpoints

```bash
# Gateway metrics
GET /metrics/gateway

# Modelservice metrics
GET /metrics/modelservice

# Memory metrics
GET /metrics/memory

# Scheduler metrics
GET /metrics/scheduler

# Message bus metrics
GET /metrics/messagebus

# System health
GET /metrics/system

# Health check
GET /metrics/health
```

### Example Response

```json
{
  "requests_per_second": {
    "value": 45.2,
    "unit": "req/s",
    "trend": 8.5,
    "status": "healthy",
    "sparkline_data": [40.1, 42.3, 43.5, ...],
    "avg_1h": 43.8,
    "avg_24h": 41.2,
    "avg_7d": 39.5
  },
  ...
}
```

## InfluxDB Schema

All metrics query these InfluxDB measurements:

| Measurement | Source | Tags | Fields |
|------------|--------|------|--------|
| `api_request` | Backend OTel | service, method, path, status_class | latency_ms_f, status_code_i |
| `model_inference` | Modelservice OTel | service, model_name, task_type | duration_ms_f, tokens_generated_i |
| `memory_query` | Backend OTel | service, query_type | query_time_ms_f, results_count_i |
| `scheduler_job` | Backend OTel | service, job_type, queue_name | duration_ms_f, success_b |
| `messagebus_event` | Backend OTel | service, topic | message_count_i, processing_time_ms_f |

## Migration from Old System

### What Changed

**Before (LibSQL-based):**
```python
# Old: Direct SQL queries to otel_* tables
result = conn.execute(
    "SELECT COUNT(*) FROM otel_api_requests WHERE timestamp > ?",
    (cutoff_24h,)
).fetchone()
```

**After (InfluxDB-based):**
```python
# New: Flux queries via abstraction layer
with MetricsInfluxClient() as client:
    count = client.count_points("api_request", "-24h", filters)
```

### Benefits

1. **No LibSQL dependency** - Clean separation
2. **Better performance** - InfluxDB optimized for time-series
3. **Richer queries** - Flux is more powerful than SQL for metrics
4. **Easier testing** - Mockable client
5. **Better maintainability** - Modular structure

## Testing

```python
# Example test
def test_gateway_metrics():
    with MetricsInfluxClient() as client:
        metrics = get_gateway_metrics()
        assert metrics.requests_per_second.value >= 0
        assert metrics.error_rate.value <= 100
```

## Performance Considerations

- **Query optimization** - Use filters to reduce data scanned
- **Caching** - Consider caching for expensive queries
- **Batch operations** - Group related queries
- **Time windows** - Use appropriate time ranges

## Future Enhancements

- [ ] Add caching layer for expensive queries
- [ ] Implement `/metrics/all` endpoint (single request)
- [ ] Add historical trend analysis
- [ ] Implement alerting thresholds
- [ ] Add custom metric aggregations
- [ ] Support for custom time ranges
- [ ] Export metrics to Prometheus format

## Contributing

When adding new metrics:

1. Add model to `models.py`
2. Create endpoint in `endpoints/`
3. Add query helpers to `influx_client.py` if needed
4. Include router in `router.py`
5. Update this README

## License

Part of AICO project - see root LICENSE file.
