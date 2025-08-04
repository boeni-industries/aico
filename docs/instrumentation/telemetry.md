---
title: Telemetry Architecture
---

# AICO Telemetry System

## Overview

The AICO Telemetry System provides comprehensive, privacy-respecting observability capabilities designed specifically for AI researchers and developers to understand complex system interactions, diagnose issues, and improve system performance. It complements the existing [Instrumentation](instrumentation.md), [Logging](instrumentation_logging.md), and [Audit](../security/audit.md) systems while focusing on the unique needs of AI system development.

This document outlines the architecture, implementation, and best practices for AICO's telemetry system, which serves as the foundation for system understanding, performance optimization, and AI behavior analysis.

## Core Principles

### 1. Development-Focused Insights

- Telemetry is designed primarily for researchers and developers
- Captures detailed information about AI behavior, performance, and interactions
- Provides visibility into complex, distributed system interactions
- Enables root cause analysis of emergent behaviors and performance issues

### 2. Privacy-First Collection

- All telemetry data is stored locally by default
- No telemetry information leaves the device without explicit user consent
- Sensitive data is redacted or anonymized in telemetry records
- Users maintain full control over telemetry data retention and access

### 3. Comprehensive Coverage

- Captures data across all system components and their interactions
- Monitors both technical metrics and AI-specific behavioral patterns
- Covers both frontend and backend with consistent schema
- Works in all deployment patterns (coupled and detached)

### 4. Minimal Performance Impact

- Efficient, asynchronous telemetry recording with minimal latency impact
- Configurable verbosity levels based on development needs
- Sampling strategies for high-volume telemetry data
- Background processing for telemetry analysis

### 5. Actionable Intelligence

- Real-time visualization of system behavior and performance
- Historical analysis for pattern detection and anomaly identification
- Clear correlation between telemetry data and system activities
- Exportable telemetry data for offline analysis

## Telemetry Categories

The AICO Telemetry System captures data across six primary categories:

### 1. System Performance

- CPU, memory, disk, and network utilization
- Component-level performance metrics
- Message bus throughput and latency
- Database performance and query statistics
- Thread/task execution timing
- Resource bottlenecks and constraints

### 2. AI Behavior

- LLM inference statistics (token counts, generation time)
- Emotion simulation state transitions
- Personality trait expression patterns
- Goal generation and completion metrics
- Planning system decision trees
- Curiosity engine exploration patterns

### 3. User Interaction Patterns

- Conversation flow and turn-taking metrics
- Response timing and user engagement statistics
- Feature usage patterns (anonymized)
- Session duration and frequency
- Interaction modality preferences
- Embodiment engagement metrics

### 4. Component Interactions

- Message flow between system components
- Cross-component dependencies and bottlenecks
- Plugin activity and resource usage
- API call patterns and frequencies
- Event propagation timing
- System topology visualization data

### 5. Error & Exception Patterns

- Exception frequency and distribution
- Error recovery success rates
- Retry patterns and backoff statistics
- Degraded mode performance metrics
- Failure correlation data
- Root cause indicators

### 6. AI Research Metrics

- Emotion recognition accuracy metrics
- Personality consistency measurements
- Memory recall precision and latency
- Learning and adaptation metrics
- Goal achievement statistics
- User satisfaction indicators (if explicitly shared)

## Telemetry Record Schema

All telemetry events conform to a standardized schema to ensure consistency across components:

```json
{
  "timestamp": "2025-08-04T07:42:53.123Z",
  "type": "telemetry",
  "category": "ai_behavior",
  "subcategory": "emotion_simulation",
  "component": "emotion_engine",
  "event": "emotion_state_transition",
  "level": "info",
  "data": {
    "previous_state": {
      "joy": 0.3,
      "sadness": 0.1,
      "anger": 0.0,
      "fear": 0.0,
      "surprise": 0.2
    },
    "current_state": {
      "joy": 0.7,
      "sadness": 0.0,
      "anger": 0.0,
      "fear": 0.0,
      "surprise": 0.4
    },
    "trigger": "user_interaction",
    "appraisal_factors": {
      "novelty": 0.8,
      "pleasantness": 0.9,
      "goal_relevance": 0.7
    }
  },
  "metadata": {
    "session_id": "session-123abc",
    "trace_id": "trace-456def",
    "span_id": "span-789ghi",
    "user_mode": "developer",
    "deployment_type": "coupled",
    "version": "0.5.2"
  }
}
```

### Required Fields

- `timestamp`: ISO 8601 timestamp with millisecond precision
- `type`: Always "telemetry" to distinguish from logs and audit records
- `category`: One of the six primary telemetry categories
- `subcategory`: More specific classification within the category
- `component`: The system component generating the telemetry
- `event`: Specific event or metric being recorded
- `level`: Importance level (debug, info, warning, error)
- `data`: Event-specific payload containing the telemetry data

### Optional Fields

- `metadata`: Additional context about the telemetry record
  - `session_id`: Unique identifier for the user session
  - `trace_id`: Distributed tracing identifier
  - `span_id`: Specific span within the trace
  - `user_mode`: Current user mode (casual, pro, developer)
  - `deployment_type`: Coupled or detached deployment
  - `version`: Software version generating the telemetry

## Architecture Integration

The Telemetry System integrates with AICO's existing architecture through several key mechanisms:

### 1. Message Bus Integration

Telemetry events are published to dedicated topics on the ZeroMQ message bus:

```
telemetry.system_performance.*
telemetry.ai_behavior.*
telemetry.user_interaction.*
telemetry.component_interactions.*
telemetry.error_patterns.*
telemetry.ai_research.*
```

This allows the Telemetry Collector service to subscribe to all telemetry events while maintaining the system's message-driven architecture.

### 2. Telemetry API

Both frontend and backend components use a consistent API to generate telemetry events:

```python
# Backend (Python)
from aico.telemetry import record_telemetry

record_telemetry(
    category="ai_behavior",
    subcategory="emotion_simulation",
    event="emotion_state_transition",
    level="info",
    data={
        "previous_state": {...},
        "current_state": {...},
        "trigger": "user_interaction",
        "appraisal_factors": {...}
    }
)
```

```dart
// Frontend (Flutter)
import 'package:aico/telemetry/telemetry.dart';

recordTelemetry(
  category: "user_interaction",
  subcategory: "conversation_flow",
  event: "user_response_time",
  level: "info",
  data: {
    "response_time_ms": 2500,
    "conversation_turn": 5,
    "interaction_type": "text"
  }
);
```

### 3. Telemetry Collector Service

A dedicated Telemetry Collector service:

- Subscribes to all telemetry topics on the message bus
- Validates and processes incoming telemetry events
- Stores events in the telemetry database
- Provides real-time streaming for dashboards
- Manages retention policies and privacy controls

### 4. Integration with Existing Systems

The Telemetry System integrates with:

- **Instrumentation System**: Shares the same message bus infrastructure and follows similar principles
- **Logging System**: Complements logs with more structured, AI-specific metrics
- **Audit System**: Clear separation of concerns, with audit focusing on security and compliance while telemetry focuses on development and research

## Data Storage and Retention

### 1. Storage Implementation

- Primary storage uses a dedicated `telemetry` table in libSQL
- Time-series optimized schema for efficient querying
- Automatic partitioning by time period
- Configurable retention policies based on telemetry category and importance

### 2. Schema Design

```sql
CREATE TABLE telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    component TEXT NOT NULL,
    event TEXT NOT NULL,
    level TEXT NOT NULL,
    data JSON NOT NULL,
    metadata JSON,
    session_id TEXT,
    trace_id TEXT,
    span_id TEXT
);

-- Indexes for common query patterns
CREATE INDEX idx_telemetry_timestamp ON telemetry(timestamp);
CREATE INDEX idx_telemetry_category ON telemetry(category);
CREATE INDEX idx_telemetry_component ON telemetry(component);
CREATE INDEX idx_telemetry_session ON telemetry(session_id);
CREATE INDEX idx_telemetry_trace ON telemetry(trace_id);
```

### 3. Retention Policies

- **System Performance**: 7-30 days depending on importance
- **AI Behavior**: 30-90 days for research purposes
- **User Interaction**: 7-30 days (anonymized)
- **Component Interactions**: 7-30 days
- **Error Patterns**: 30-90 days
- **AI Research Metrics**: 90-365 days

All retention periods are configurable by the user, with clear defaults based on the telemetry category.

## Privacy Controls

The Telemetry System implements several privacy safeguards:

### 1. Data Minimization

- Only collect what's necessary for development and research
- Automatic redaction of personal identifiers
- Configurable verbosity levels to control data collection
- Sampling strategies for high-volume data

### 2. Access Control

- Role-based access to telemetry data
- Developer-specific permissions for telemetry access
- Audit logging of all telemetry data access

### 3. Retention Limits

- Automatic purging of telemetry data based on configurable retention policies
- User-controlled retention periods
- Emergency purge capability

### 4. Encryption

- All telemetry data is encrypted at rest
- Secure transmission of telemetry data
- Key management integrated with AICO's security architecture

## Implementation Components

### 1. OpenTelemetry Integration

AICO leverages OpenTelemetry as the standard framework for all telemetry needs:

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure OpenTelemetry with AICO-specific resources
resource = Resource.create({"service.name": "aico"})

# Set up trace provider
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# Set up metrics provider
meter_provider = MeterProvider(resource=resource)
metrics.set_meter_provider(meter_provider)

# Get tracers and meters for components
tracer = trace.get_tracer("aico.emotion_engine")
meter = metrics.get_meter("aico.system_metrics")
```

### 2. ZeroMQ Message Bus Integration

Integrates with the existing message bus using an OpenTelemetry processor:

```python
class ZeroMQSpanProcessor:
    def __init__(self, zmq_context):
        self.socket = zmq_context.socket(zmq.PUB)
        self.socket.connect("tcp://localhost:5555")
    
    def on_end(self, span):
        # Convert span to telemetry event and publish to ZeroMQ
        topic = f"telemetry.{span.name}"
        message = json.dumps({
            "timestamp": span.start_time,
            "duration": span.end_time - span.start_time,
            "attributes": span.attributes
        })
        self.socket.send_multipart([topic.encode(), message.encode()])
```

### 3. Unified Storage

Reuses the existing libSQL database with a simplified schema:

```python
# Using the main AICO database instead of a separate telemetry DB
conn = libsql.connect("aico.db")

# Create a time-series optimized table
conn.execute("""
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        name TEXT NOT NULL,
        attributes JSON NOT NULL
    )
""")

# Create indexes for common query patterns
conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_name ON telemetry(name)")
```

### 4. Simplified Query API

Leverages OpenTelemetry's query capabilities with libSQL integration:

```python
# Get time series data for a specific metric
```

### 5. Visualization Components

- Real-time dashboards for system monitoring
- Interactive visualizations for AI behavior analysis
- Time-series charts for performance metrics
- Network diagrams for component interactions
- Heat maps for error patterns
- Custom views for AI research metrics

## Deployment Considerations

### 1. Coupled Mode (Single Device)

In coupled mode, where frontend and backend run on the same device:

- All telemetry components run locally
- Direct ZeroMQ communication between components
- Local storage of all telemetry data
- Unified visualization in the Admin UI

### 2. Detached Mode (Distributed)

In detached mode, where frontend and backend run on separate devices:

- Backend telemetry collected and stored on the backend device
- Frontend telemetry sent to backend via secure channel
- Synchronized visualization when devices reconnect
- Optional local caching of telemetry on frontend device

### 3. Federation Scenarios

When multiple AICO instances synchronize:

- Each instance maintains its own telemetry data
- Optional aggregation of telemetry across instances
- Clear identification of source instance in aggregated views

## Developer Tools and Interfaces

### 1. CLI Interface

Command-line tools for telemetry management:

```bash
# Query telemetry events
aico telemetry query --category=ai_behavior --component=emotion_engine --last=24h

# Export telemetry data
aico telemetry export --format=json --output=telemetry_export.json --last=7d

# View real-time telemetry
aico telemetry watch --category=system_performance

# Manage retention policies
aico telemetry retention --set --category=ai_behavior --days=60
```

### 2. Admin UI

Dedicated section in the Admin UI for telemetry visualization and management:

- Dashboard with key metrics and system health
- Interactive visualizations of AI behavior
- Component interaction diagrams
- Performance profiling tools
- Query builder for custom telemetry analysis
- Configuration panel for telemetry settings

### 3. Developer SDK

SDK for custom telemetry integration:

- Telemetry API clients for multiple languages
- Visualization components for custom dashboards
- Query builders for telemetry analysis
- Export/import utilities for offline analysis

## Relationship to Audit System

While the [Audit System](../security/audit.md) and Telemetry System both collect data about AICO's operation, they serve different purposes and have distinct characteristics:

| Aspect | Audit System | Telemetry System |
|--------|-------------|-----------------|
| **Primary Purpose** | Security, compliance, and operational transparency | Development, debugging, and AI research |
| **User Audience** | System administrators and security personnel | Developers, researchers, and AI engineers |
| **Data Focus** | Security-relevant events and user actions | System performance, AI behavior, and component interactions |
| **Legal Requirements** | May be subject to compliance and regulatory requirements | Primarily for internal development and research |
| **Retention** | Typically longer retention for compliance | Shorter, flexible retention based on development needs |
| **Access Control** | Strict, role-based access | Development team access with appropriate controls |
| **Tamper Protection** | Cryptographic tamper-evidence required | Standard database integrity sufficient |
| **Volume** | Lower volume, focused on security events | Higher volume, comprehensive system metrics |

### Key Differences in Implementation

1. **Schema Design**:
   - Audit: Focused on who, what, when, where for security events
   - Telemetry: Focused on detailed metrics, states, and performance data

2. **Storage**:
   - Audit: Tamper-evident, append-only storage with hash chaining
   - Telemetry: Time-series optimized storage with efficient querying

3. **API**:
   - Audit: Security-focused API with strict validation
   - Telemetry: Development-focused API with flexible data structures

4. **Visualization**:
   - Audit: Timeline views, security dashboards, compliance reports
   - Telemetry: Performance charts, behavior visualizations, system diagrams

### Integration Points

The Telemetry and Audit systems are designed to work together:

1. **Shared Infrastructure**: Both use the ZeroMQ message bus with different topics
2. **Correlated Analysis**: Events can be correlated across systems using trace IDs
3. **Unified Admin Interface**: Both accessible through the Admin UI with appropriate permissions
4. **Complementary Coverage**: Together provide complete system observability

## Best Practices

### 1. Telemetry Design Guidelines

For developers implementing telemetry:

- Focus on actionable metrics that provide insight
- Use consistent naming conventions for events and components
- Include context that helps correlate telemetry with other events
- Consider the performance impact of high-volume telemetry
- Use appropriate sampling for high-frequency events

### 2. Privacy Considerations

When implementing telemetry collection:

- Never collect personally identifiable information
- Anonymize user interaction data
- Be transparent about what telemetry is collected
- Provide clear controls for users to manage telemetry
- Respect user preferences for telemetry verbosity

### 3. Implementation Guidelines

For developers implementing telemetry hooks:

- Use the telemetry API consistently across all modules
- Include all required fields in every telemetry event
- Ensure telemetry calls don't block the main execution path
- Use appropriate telemetry levels based on importance
- Test telemetry coverage as part of development

### 4. Operational Recommendations

For system administrators and developers:

- Regularly review telemetry dashboards for anomalies
- Configure appropriate retention periods for different categories
- Use sampling for high-volume telemetry in production
- Export important telemetry data for offline analysis
- Correlate telemetry with logs and audit events for complete understanding

## Conclusion

The AICO Telemetry System provides comprehensive visibility into system operations, AI behavior, and component interactions, enabling developers and researchers to understand, debug, and improve the complex interactions within AICO. By capturing detailed metrics across all components while respecting user privacy, it enables effective development, research, and optimization.

The time-series optimized storage ensures efficient querying of telemetry data, while the flexible visualization capabilities support both real-time monitoring and historical analysis. Together with AICO's broader instrumentation architecture, the Telemetry System forms a critical component of the platform's development and research toolkit.

## References

- [AICO Architecture Overview](../architecture/architecture_overview.md)
- [AICO Instrumentation](instrumentation.md)
- [AICO Instrumentation Logging](instrumentation_logging.md)
- [AICO Audit System](../security/audit.md)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
