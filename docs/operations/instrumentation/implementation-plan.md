---
title: OpenTelemetry Implementation Plan
---

# OpenTelemetry Implementation Plan

## Overview
This document outlines the implementation plan for integrating OpenTelemetry into AICO's instrumentation system, replacing mock metrics with real telemetry data while maintaining minimal code disruption.

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    AICO Application                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   API    │  │  Model   │  │  Memory  │  │Scheduler │   │
│  │ Gateway  │  │ service  │  │  System  │  │          │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │              │             │          │
│       └─────────────┴──────────────┴─────────────┘          │
│                         │                                    │
│              ┌──────────▼──────────┐                        │
│              │  OpenTelemetry SDK  │                        │
│              │  ┌────┐ ┌────┐ ┌───┐│                        │
│              │  │Trace│ │Metric│ │Log││                     │
│              │  └────┘ └────┘ └───┘│                        │
│              └──────────┬──────────┘                        │
└─────────────────────────┼───────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼─────┐    ┌────▼─────┐    ┌────▼─────┐
    │  Local   │    │Prometheus│    │   OTLP   │
    │ Storage  │    │ Exporter │    │ Exporter │
    │ (SQLite) │    │(/metrics)│    │ (Jaeger) │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │                │
    ┌────▼─────┐    ┌────▼─────┐    ┌────▼─────┐
    │  Studio  │    │ Grafana  │    │  Jaeger  │
    │Dashboard │    │   (Dev)  │    │   (Dev)  │
    └──────────┘    └──────────┘    └──────────┘
```

## Phase 1: Core OpenTelemetry Integration

### 1.1 Install Dependencies
**File:** `pyproject.toml`

```toml
[project.dependencies]
# Core OpenTelemetry
opentelemetry-api = "^1.20.0"
opentelemetry-sdk = "^1.20.0"

# Auto-instrumentation
opentelemetry-instrumentation-fastapi = "^0.41b0"
opentelemetry-instrumentation-sqlite3 = "^0.41b0"
opentelemetry-instrumentation-requests = "^0.41b0"

[project.optional-dependencies]
dev = [
    "opentelemetry-exporter-prometheus = ^0.41b0",
    "opentelemetry-exporter-otlp = ^1.20.0",
    "prometheus-client = ^0.19.0"
]
```

### 1.2 Create OpenTelemetry Bootstrap Module
**File:** `backend/core/telemetry.py`

**Purpose:** Initialize OpenTelemetry providers and exporters based on configuration

**Key Features:**
- Lazy initialization (only when needed)
- Configuration-driven (dev mode vs production)
- Local storage by default
- Optional Prometheus/OTLP exporters

**Responsibilities:**
- Initialize TracerProvider, MeterProvider, LoggerProvider
- Configure exporters based on mode (casual/pro/dev)
- Set up auto-instrumentation
- Provide singleton access to tracer/meter instances

### 1.3 FastAPI Auto-Instrumentation
**File:** `backend/main.py` (modify existing)

**Changes:**
- Import `FastAPIInstrumentor`
- Instrument FastAPI app during startup
- Zero code changes to existing routes

**Impact:** Automatic tracing of all HTTP requests with:
- Request/response timing
- Status codes
- HTTP method/path
- Client IP (redacted in casual mode)

## Phase 2: Custom Metrics for Business Logic

### 2.1 API Gateway Metrics
**File:** `backend/api_gateway/middleware/metrics_middleware.py` (new)

**Metrics to Collect:**
- `aico.api.requests.total` (Counter) - Total requests by endpoint, method, status
- `aico.api.request.duration` (Histogram) - Request latency distribution
- `aico.api.errors.total` (Counter) - Errors by type, endpoint
- `aico.api.active_connections` (UpDownCounter) - Current active connections

**Implementation:**
- Middleware wraps existing request handling
- Records metrics using OTel Meter API
- No changes to existing route handlers

### 2.2 Modelservice Metrics
**File:** `modelservice/core/inference_tracker.py` (new)

**Metrics to Collect:**
- `aico.modelservice.inferences.total` (Counter) - Total inferences by model
- `aico.modelservice.inference.duration` (Histogram) - Inference time distribution
- `aico.modelservice.tokens.generated` (Counter) - Total tokens by model
- `aico.modelservice.models.active` (UpDownCounter) - Currently loaded models

**Implementation:**
- Decorator for inference functions
- Automatic metric recording
- Model name as attribute

### 2.3 Memory System Metrics
**File:** `shared/aico/ai/memory/metrics.py` (new)

**Metrics to Collect:**
- `aico.memory.queries.total` (Counter) - Queries by type (semantic, working, KG)
- `aico.memory.query.duration` (Histogram) - Query latency
- `aico.memory.entities.total` (Gauge) - Total KG entities
- `aico.memory.relationships.total` (Gauge) - Total KG relationships
- `aico.memory.consolidation.duration` (Histogram) - Consolidation time

**Implementation:**
- Instrument query methods
- Periodic gauge updates for entity counts
- Consolidation tracking

### 2.4 Scheduler Metrics
**File:** `backend/core/scheduler_metrics.py` (new)

**Metrics to Collect:**
- `aico.scheduler.jobs.total` (Counter) - Jobs by type, status (success/failure)
- `aico.scheduler.job.duration` (Histogram) - Job execution time
- `aico.scheduler.queue.depth` (Gauge) - Current queue depth by queue
- `aico.scheduler.jobs.failed` (Counter) - Failed jobs with reason

**Implementation:**
- Wrap job execution
- Record start/end times
- Track failures with attributes

### 2.5 Message Bus Metrics
**File:** `backend/core/message_bus_metrics.py` (new)

**Metrics to Collect:**
- `aico.messagebus.messages.total` (Counter) - Messages by topic
- `aico.messagebus.message.duration` (Histogram) - Processing time
- `aico.messagebus.backlog.depth` (Gauge) - Current backlog by topic
- `aico.messagebus.consumers.active` (Gauge) - Active consumers by topic

**Implementation:**
- Instrument message publish/consume
- Track backlog via queue inspection
- Consumer health monitoring

## Phase 3: Local Storage Adapter

### 3.1 OpenTelemetry to SQLite Bridge
**File:** `backend/core/otel_storage_adapter.py` (new)

**Purpose:** Bridge OpenTelemetry metrics to local SQLite for Studio dashboard

**Design:**
- Implements OTel MetricReader interface
- Periodically exports metrics to SQLite
- Maintains existing metrics table schema
- Aggregates metrics for dashboard queries

**Key Methods:**
- `collect()` - Gather metrics from OTel SDK
- `export()` - Write to SQLite tables
- `aggregate()` - Calculate rates, percentiles, trends

**Tables:**
- Reuse existing `api_request_metrics`, `modelservice_inference_metrics`, etc.
- OTel metrics map directly to existing schema

### 3.2 Metrics API Refactor
**File:** `backend/api/system/metrics.py` (modify existing)

**Changes:**
- Remove all mock data
- Query SQLite metrics tables (populated by OTel adapter)
- Use HealthCalculator for scoring
- Return real data only

**Endpoints:**
- `/metrics/gateway` - Query `api_request_metrics` table
- `/metrics/modelservice` - Query `modelservice_inference_metrics` table
- `/metrics/memory` - Query `memory_query_metrics` + direct DB counts
- `/metrics/scheduler` - Query `scheduler_job_metrics` table
- `/metrics/message_bus` - Query `message_bus_metrics` table
- `/metrics/all` - Aggregate all metrics + health calculation

## Phase 4: Health Calculation Integration

### 4.1 Update Response Models
**File:** `backend/api/system/metrics.py` (modify)

**Add to Models:**
```python
class ComponentHealth(BaseModel):
    score: int  # 0-100
    status: str  # "healthy", "degraded", "critical"
    issues: List[HealthIssue]

class HealthIssue(BaseModel):
    severity: str  # "critical", "warning", "info"
    metric: str
    current_value: float
    threshold: float
    impact: int  # Points deducted
    message: str
```

### 4.2 Health Calculator Integration
**File:** `backend/api/system/metrics.py` (modify)

**Changes:**
- Import HealthCalculator
- Calculate health for each component
- Include health details in responses
- Add degradation reasons to SystemHealthMetrics

## Phase 5: Exporters for All Modes

### 5.1 Prometheus Exporter
**File:** `backend/core/telemetry.py` (modify)

**Available In:** Pro, Dev, Production modes

**Configuration:**
```yaml
instrumentation:
  mode: "production"  # casual, pro, dev, production
  prometheus:
    enabled: true
    port: 9090
    # Production-specific settings
    authentication:
      enabled: true
      type: "bearer"  # bearer, basic, none
      token_env: "PROMETHEUS_TOKEN"
    rate_limiting:
      enabled: true
      requests_per_minute: 60
    allowed_ips:
      - "127.0.0.1"
      - "10.0.0.0/8"  # Internal network
```

**Security Features:**
- Optional authentication (bearer token, basic auth)
- IP allowlist for access control
- Rate limiting to prevent abuse
- Automatic PII redaction in metric labels
- TLS support for encrypted transport

### 5.2 OTLP Exporter (Jaeger/Tempo)
**File:** `backend/core/telemetry.py` (modify)

**Available In:** Dev, Production modes

**Configuration:**
```yaml
instrumentation:
  mode: "production"
  otlp:
    enabled: true
    # Traces
    traces:
      endpoint: "https://jaeger.company.com:4317"
      protocol: "grpc"  # grpc, http/protobuf
      headers:
        authorization: "Bearer ${OTLP_TOKEN}"
      compression: "gzip"
      timeout_seconds: 10
    # Metrics (optional)
    metrics:
      endpoint: "https://metrics.company.com:4317"
      protocol: "grpc"
    # Sampling
    sampling:
      type: "probabilistic"  # always_on, always_off, probabilistic
      rate: 0.1  # 10% of traces
```

**Production Features:**
- Configurable endpoints (Jaeger, Tempo, Grafana Cloud, etc.)
- Authentication via headers
- Compression for bandwidth efficiency
- Sampling to reduce volume
- Batch export with retry logic

### 5.3 Grafana Dashboards
**File:** `config/grafana/dashboards/` (new directory)

**Pre-built Dashboards (Work in All Modes):**
- `aico-overview.json` - System-wide health and metrics
- `aico-api-gateway.json` - API Gateway performance
- `aico-modelservice.json` - Inference metrics
- `aico-memory.json` - Memory system metrics
- `aico-scheduler.json` - Job execution metrics
- `aico-message-bus.json` - Message bus metrics

**Deployment Options:**
- **Dev Mode:** Local Grafana instance (Docker Compose)
- **Production Mode:** Import to existing Grafana instance
- **Grafana Cloud:** Compatible with managed Grafana

**Dashboard Features:**
- Variable templating for filtering by component
- Alerting rules for critical thresholds
- Links to trace views (Jaeger integration)
- Annotations for deployments/incidents
- Multi-instance support (federated deployments)

## Phase 6: ZeroMQ Context Propagation

### 6.1 Custom Propagator
**File:** `backend/core/zmq_propagator.py` (new)

**Purpose:** Inject/extract W3C Trace Context in ZeroMQ messages

**Implementation:**
- Implement OTel Propagator interface
- Inject `traceparent` header into message envelope
- Extract context on message receive
- Create child spans for message handlers

**Envelope Format:**
```python
{
    "headers": {
        "traceparent": "00-{trace_id}-{span_id}-{flags}"
    },
    "payload": {...}
}
```

## Implementation Order

1. **Week 1: Core Setup**
   - Install dependencies
   - Create telemetry bootstrap module
   - Add FastAPI auto-instrumentation
   - Verify basic tracing works

2. **Week 2: Custom Metrics**
   - API Gateway metrics middleware
   - Modelservice inference tracking
   - Memory system instrumentation
   - Scheduler job tracking
   - Message bus metrics

3. **Week 3: Storage & API**
   - OTel to SQLite adapter
   - Refactor metrics API endpoints
   - Remove all mock data
   - Integrate health calculator

4. **Week 4: Dev Mode & Polish**
   - Prometheus exporter
   - OTLP exporter
   - Grafana dashboards
   - ZeroMQ propagator
   - Documentation updates

## Testing Strategy

### Unit Tests
- Test metric recording functions
- Verify health calculation logic
- Test storage adapter

### Integration Tests
- End-to-end request tracing
- Metric aggregation accuracy
- Health score calculation with real data

### Performance Tests
- Measure instrumentation overhead (<5% target)
- Verify no memory leaks
- Test under load

## Rollout Strategy

1. **Feature Flag:** `instrumentation.opentelemetry.enabled`
2. **Mode-Based Configuration:**
   - Casual: No exporters, local only
   - Pro: Optional Prometheus (opt-in)
   - Dev: All exporters enabled by default
   - Production: All exporters available, configurable
3. **Gradual Rollout:**
   - Enable in dev environment first
   - Test with production-like config
   - Enable in production after validation
4. **Fallback:** Keep existing MetricsCollector as backup
5. **Migration:** Run both systems in parallel initially

## Success Criteria

- ✅ Zero mock data in metrics API
- ✅ All metrics from real telemetry
- ✅ Health scores with transparent reasoning
- ✅ <5% performance overhead
- ✅ Studio dashboard shows real data
- ✅ Dev mode exporters functional
- ✅ Trace context propagates across modules
- ✅ Privacy controls enforced

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance overhead | High | Benchmark early, optimize hot paths |
| Breaking existing code | High | Comprehensive testing, gradual rollout |
| Privacy leaks | Critical | Automatic PII redaction, audit logs |
| Complex debugging | Medium | Enhanced logging, trace visualization |
| Dependency bloat | Low | Optional dev dependencies |

## Configuration Examples

### Casual Mode (Default)
```yaml
instrumentation:
  mode: "casual"
  opentelemetry:
    enabled: true
  exporters:
    prometheus:
      enabled: false
    otlp:
      enabled: false
  storage:
    local:
      enabled: true
      retention_days: 7
```

### Pro Mode
```yaml
instrumentation:
  mode: "pro"
  opentelemetry:
    enabled: true
  exporters:
    prometheus:
      enabled: false  # User can opt-in via UI
      port: 9090
      bind: "127.0.0.1"  # Local only
    otlp:
      enabled: false
  storage:
    local:
      enabled: true
      retention_days: 30
```

### Production Mode
```yaml
instrumentation:
  mode: "production"
  opentelemetry:
    enabled: true
  exporters:
    prometheus:
      enabled: true
      port: 9090
      bind: "0.0.0.0"  # All interfaces
      authentication:
        enabled: true
        type: "bearer"
        token_env: "PROMETHEUS_TOKEN"
      rate_limiting:
        enabled: true
        requests_per_minute: 120
      allowed_ips:
        - "10.0.0.0/8"
        - "172.16.0.0/12"
    otlp:
      enabled: true
      traces:
        endpoint: "https://jaeger.company.com:4317"
        headers:
          authorization: "Bearer ${OTLP_TOKEN}"
      sampling:
        type: "probabilistic"
        rate: 0.1
  storage:
    local:
      enabled: true
      retention_days: 90
  privacy:
    pii_redaction: true
    sensitive_fields:
      - "user_id"
      - "email"
      - "ip_address"
```

## Next Steps

1. Review and approve this plan
2. Create implementation tickets
3. Set up dev environment with Jaeger/Grafana
4. Begin Phase 1 implementation
