---
title: Instrumentation Architecture
---

# Instrumentation Architecture

## Overview
AICO's instrumentation system provides unified, privacy-respecting observability across all modules, modes, and devices using **OpenTelemetry** as the industry-standard foundation. It is designed to support both **coupled** (single-device) and **detached** (multi-device/federated) deployments, in line with AICO's core architectural principles as outlined in the [Architecture Overview](../../architecture/architecture-overview.md).

### Technology Foundation
- **OpenTelemetry (OTel)**: CNCF-graduated standard for traces, metrics, and logs
- **Auto-Instrumentation**: Zero-code instrumentation for FastAPI, PostgreSQL, and other frameworks
- **Vendor-Neutral**: Export to any backend (Prometheus, Jaeger, Grafana, etc.)
- **Local-First**: All telemetry stored locally by default, with optional export in dev mode
- **Apache 2.0 License**: Fully open-source and compatible with AICO's licensing

## Design Goals
- **Consistent Observability:** Unified approach for logging, metrics, tracing, and auditing across all modules and plugins.
- **Privacy-First:** All instrumentation is local-first, user-controlled, and zero-knowledge by default. No sensitive data is exported without explicit user consent.
- **Modular & Extensible:** Instrumentation is a cross-cutting concern, integrated via standard interfaces and message bus topics.
- **Multi-Modal & Embodied:** Observes not just backend logic, but also embodiment, emotion, and user interaction layers.
- **Works in All Modes:** Fully functional in both coupled (all-in-one) and detached (distributed/federated) deployments.

## Instrumentation Modes & Stages

AICO’s instrumentation system is designed to be **privacy-first, local-first, and user-friendly by default**, with opt-in escalation for advanced users and developers. There are three distinct stages:

### 1. Casual User (Default)
- **Minimal, non-technical logging:** Only essential events and errors are logged, using clear, human-friendly messages.
- **User notifications:** Important system events are surfaced as simple notifications (e.g., "AICO restarted"), not technical logs.
- **No metrics, tracing, or analytics** are collected or exposed.
- **No external dashboards or endpoints.**
- **Privacy:** All data remains local, never leaves the device.

### 2. Pro User (Opt-In)
- **Resource & health insights:** In-app dashboard or status page shows resource usage, performance, and health (CPU, memory, uptime, etc.).
- **In-depth logs:** More detailed logs are available for inspection/export.
- **Debug Capsules:** On-demand, session-based instrumentation "capsules" can be generated (encrypted, portable files containing logs/metrics for a session). Users can review/redact before sharing for support.
- **Metrics Export (Optional):** Can enable Prometheus `/metrics` endpoint for integration with monitoring systems.
- **Still local-first:** All insights and data remain on-device unless explicitly exported by the user.

### 3. Developer Mode (Opt-In Plugin)
- **Full observability plugin:** When enabled, exposes advanced instrumentation endpoints (Prometheus `/metrics`, OTLP exporters).
- **Local Prometheus/Jaeger/Grafana:** Pre-configured stack runs locally (never required for normal use).
- **Predefined dashboards:** Pre-built Grafana dashboards for all AICO subsystems.
- **Advanced tracing and analytics:** Full distributed tracing via Jaeger, activity streams, and audit logs.
- **OpenTelemetry Collector:** Optional local collector for advanced telemetry routing.
- **Plugin isolation:** Dev tools are sandboxed and can be disabled/removed at any time.

### 4. Production Mode (Enterprise/Self-Hosted)
- **Prometheus Integration:** `/metrics` endpoint available for production monitoring systems.
- **Grafana Dashboards:** Pre-built dashboards work with production Grafana instances.
- **OTLP Export:** Optional export to production observability backends (Jaeger, Tempo, etc.).
- **Privacy Controls:** Automatic PII redaction, configurable data retention.
- **Security:** Metrics endpoint can be secured with authentication, rate limiting.
- **Local-First Option:** Can run entirely local even in production (no external export required).

---

## Core Components (Across All Stages)

### Instrumentation Layer (OpenTelemetry)
- **Traces:** Distributed tracing with end-to-end context propagation across HTTP/WebSocket and NATS/JetStream
- **Metrics:** Counters, gauges, histograms for performance and health monitoring
- **Logs:** Structured logs with trace correlation and semantic attributes
- **Auto-Instrumentation:** FastAPI, PostgreSQL, HTTP clients instrumented automatically
- **Custom Instrumentation:** Business logic instrumented via OTel SDK

### Storage & Export
- **Local Storage (Always):** PostgreSQL-based metrics store for Studio dashboard
- **Prometheus Exporter (Pro/Dev/Production):** `/metrics` endpoint for Prometheus scraping
  - Casual: Disabled by default
  - Pro: Opt-in, local only
  - Dev: Enabled by default
  - Production: Configurable, with authentication
- **OTLP Exporter (Dev/Production):** Push traces/metrics/logs via OTLP (typically to an OpenTelemetry Collector)
  - Casual/Pro: Disabled
  - Dev: Enabled by default
  - Production: Opt-in, configurable endpoint
- **Grafana Integration (All Modes):** Pre-built dashboards work with any Grafana instance

### Privacy & Security
- **Local-First:** All telemetry stored locally by default
- **Opt-In Export:** External backends only enabled in dev mode
- **Data Redaction:** Sensitive data automatically scrubbed from telemetry
- **Audit Logs:** Instrumentation access and export tracked
- **Debug Capsules:** Encrypted, portable telemetry bundles for support

---

## Architectural Integration

### Distributed Tracing in a Message Bus Architecture

**OpenTelemetry Context Propagation via NATS / JetStream:**
- Every NATS message includes W3C Trace Context headers
- Producers inject trace context; consumers extract context and start child spans
- Enables end-to-end tracing across HTTP/WebSocket → NATS request/reply, pub/sub, and JetStream work-queue flows

**Envelope Format (W3C Trace Context):**
```json
{
  "headers": {
    "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
    "tracestate": "aico=module:conversation,priority:high"
  },
  "trace": {
    "trace_id": "0af7651916cd43dd8448eb211c80319c",
    "span_id": "b7ad6b7169203331",
    "parent_span_id": "00f067aa0ba902b7",
    "trace_flags": "01"
  }
}
```

**Implementation:**
- Use `opentelemetry.propagate` to inject/extract context
- Inject into NATS message headers (preferred: native headers)
- Extract in NATS subscribers and JetStream consumers before invoking handlers
- Always propagate a stable `request_id` / `correlation_id` (for idempotency + joins) alongside trace context

---

## Extended Strategy (Core Services)

### What we optimize for
- **Stable golden-path observability:** when architecture changes, the same core flows remain traceable.
- **Per-operation metrics by default:** consistent duration + error-rate coverage without case-by-case profiling.
- **Drilldown workflow:** dashboard → trace → span → correlated logs.

### Golden paths (must be end-to-end)
- **Gateway request → Core processing → Modelservice inference**
- **NATS request/reply** (command/response) and **streaming subjects** (ephemeral)
- **JetStream work-queue jobs** (durable) including retry/redelivery
- **Persistence boundaries** (Postgres): conversation writes, outbox publication, working memory, interaction tables

### Span model (naming + boundaries)
- **HTTP/WebSocket entry:** `http.server` / `ws.session`
- **Domain operations:** `conversation.handle_message`, `memory.assemble_context`, `interactions.process`, `tts.synthesize`
- **Bus operations:** `nats.publish`, `nats.request`, `nats.consume`, `jetstream.ack`
- **I/O operations:** `db.query`, `db.transaction`

Span attributes must be bounded (low-cardinality) for metrics and search:
- `service.name`, `operation`, `success`
- `nats.subject` (bounded taxonomy)
- `model.name` (bounded set)
- Avoid high-cardinality identifiers (e.g. `user_id`, `conversation_id`) as metric dimensions.

### Per-operation metrics (two layers)
- **Custom business metrics (OTel Meter):** use the documented AICO pattern for stable, curated KPIs.
- **RED metrics from spans (Collector):** derive rate/errors/duration per operation from traces using span-to-metrics.

### Sampling (keep overhead low, keep slow/error)
- Default head sampling can be modest.
- Add tail-based rules in the collector to retain:
  - slow traces
  - traces with errors
  - traces for selected critical operations

### Trace → Log correlation (Grafana + Loki)
- Include `trace_id` (and ideally `span_id`) in all structured logs.
- Configure Grafana to jump from Tempo trace spans to Loki logs by `trace_id`.

---

## Implementation Architecture

### Layer 1: OpenTelemetry SDK (Core)
```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

# Initialize providers
trace.set_tracer_provider(TracerProvider())
metrics.set_meter_provider(MeterProvider())

# Get instruments
tracer = trace.get_tracer("aico.backend")
meter = metrics.get_meter("aico.backend")
```

### Layer 2: Auto-Instrumentation
- **FastAPI:** `opentelemetry-instrumentation-fastapi` (automatic middleware)
- **PostgreSQL:** `opentelemetry-instrumentation-PostgreSQL3` (query tracing)
- **HTTP Clients:** `opentelemetry-instrumentation-requests` (outbound calls)
- **NATS/JetStream:** Propagator that injects/extracts W3C Trace Context into NATS headers

### Layer 3: Custom Metrics (Business Logic)
```python
# API Gateway metrics
request_counter = meter.create_counter(
    "aico.api.requests",
    description="Total API requests",
    unit="1"
)
latency_histogram = meter.create_histogram(
    "aico.api.latency",
    description="Request latency",
    unit="ms"
)

# Modelservice metrics
inference_counter = meter.create_counter(
    "aico.modelservice.inferences",
    description="Total inferences",
    unit="1"
)
inference_duration = meter.create_histogram(
    "aico.modelservice.inference_duration",
    description="Inference duration",
    unit="s"
)
```

### Layer 4: Storage & Export

**Casual Mode (Default):**
- Local PostgreSQL metrics database for Studio dashboard
- No external export
- No metrics endpoint exposed

**Pro Mode:**
- Metrics aggregation for in-app insights
- Debug capsule generation
- Optional Prometheus `/metrics` endpoint (opt-in, local only)

**Dev Mode:**
- Prometheus exporter on `/metrics` (enabled by default)
- OTLP exporter to OpenTelemetry Collector (traces + optional span-derived metrics)
- Grafana dashboards (pre-configured local stack)

**Production Mode:**
- All exporters available and configurable
- Prometheus `/metrics` with optional authentication
- OTLP export to production backends
- Grafana dashboards for production monitoring
- Privacy controls enforced (PII redaction)
- Configurable data retention and sampling

### Health Calculation
- OpenTelemetry metrics feed into health calculator
- Transparent scoring with degradation reasons
- Real-time component status based on actual telemetry

---

## Unified Instrumentation Architecture Diagram

```mermaid
graph TD;
  subgraph AICO Application
    API[API Gateway<br/>FastAPI]
    Model[Modelservice]
    Memory[Memory System]
    Scheduler[Scheduler]
    Bus[Message Bus<br/>NATS/JetStream]
  end
  
  subgraph OpenTelemetry SDK
    Tracer[Tracer Provider]
    Meter[Meter Provider]
    Logger[Logger Provider]
  end
  
  API --> Tracer
  API --> Meter
  Model --> Tracer
  Model --> Meter
  Memory --> Tracer
  Memory --> Meter
  Scheduler --> Tracer
  Scheduler --> Meter
  Bus --> Tracer
  
  Tracer --> LocalStore[Local Storage<br/>PostgreSQL]
  Meter --> LocalStore
  Logger --> LocalStore
  
  LocalStore --> Studio[Studio Dashboard]
  
  subgraph Dev Mode Only
    Tracer -.-> OTLP[OTLP Exporter]
    Meter -.-> Prom[Prometheus<br/>/metrics]
    OTLP -.-> Collector[OpenTelemetry Collector]
    Collector -.-> Tempo[Tempo]
    Tempo -.-> Grafana[Grafana]
  end
```

## Dependencies

### Core (Always Installed)
```toml
[project.dependencies]
opentelemetry-api = "^1.20.0"
opentelemetry-sdk = "^1.20.0"
opentelemetry-instrumentation-fastapi = "^0.41b0"
opentelemetry-instrumentation-PostgreSQL3 = "^0.41b0"
```

### Dev Mode (Optional)
```toml
[project.optional-dependencies]
dev = [
    "opentelemetry-exporter-prometheus = ^0.41b0",
    "opentelemetry-exporter-otlp = ^1.20.0",
    "prometheus-client = ^0.19.0"
]
```

## Migration Path

1. **Phase 1:** Install OTel SDK, add auto-instrumentation to FastAPI
2. **Phase 2:** Add custom metrics for business logic (API Gateway, Modelservice, etc.)
3. **Phase 3:** Create local storage adapter, feed Studio dashboard
4. **Phase 4:** Add health calculator using OTel metrics
5. **Phase 5:** Add OpenTelemetry Collector + Tempo for trace drilldown in Grafana
6. **Phase 6:** Create pre-built Grafana dashboards (logs + metrics + traces)

## References
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry FastAPI](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
- [Prometheus](https://prometheus.io/)
- [Grafana Tempo](https://grafana.com/oss/tempo/)
- [Grafana](https://grafana.com/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
