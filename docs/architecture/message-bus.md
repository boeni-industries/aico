# Core Message Bus Architecture

## Overview

The Core Message Bus is the central nervous system of AICO, enabling modular, event-driven communication between all system components. It implements a publish-subscribe (pub/sub) pattern that allows modules to communicate without direct dependencies, supporting AICO's core principles of modularity, autonomy, and extensibility.

**🔒 Security First:** All message bus communication is secured via NATS authentication/authorization and deployment-level transport security; there is no plaintext fallback mode in production deployments.

**⚠️ CRITICAL: Logging Recursion Prevention** - Avoid standard logging within message bus operations to prevent infinite recursion loops.

This architecture document describes the design, implementation, and integration patterns of AICO's central message bus system, which serves as the foundation for inter-module communication and coordination.

## Design Principles

The Core Message Bus architecture is built on the following key principles:

### 1. Loose Coupling

Modules communicate exclusively through the message bus rather than direct method calls, enabling:
- Independent development and testing of modules
- Ability to replace or upgrade modules without affecting others
- Simplified integration of new capabilities

### 2. Event-Driven Architecture

The system operates on an event-driven paradigm where:
- Modules publish events (messages) when state changes occur
- Interested modules subscribe to relevant topics
- Processing occurs asynchronously and reactively

### 3. Standardized Communication

All messages follow a consistent envelope structure defined in Protocol Buffers. Conceptually:

```protobuf
message AicoMessage {
  MessageMetadata metadata = 1;
  google.protobuf.Any any_payload = 2; // Domain-specific message
}

message MessageMetadata {
  string message_id = 1;   // UUID
  string timestamp = 2;    // ISO 8601
  string source = 3;       // Originating module
  string message_type = 4; // Topic name from AICOTopics
  string version = 5;      // Schema version
}
```

### 4. Topic-Based Routing

Messages are organized in a hierarchical topic structure:
- Primary category (e.g., `emotion`, `personality`, `agency`)
- Subcategory (e.g., `state`, `expression`, `goals`)
- Action/type (e.g., `current`, `update`, `request`)

### 5. Versioned Message Formats

All message formats are explicitly versioned to enable:
- Backward compatibility
- Graceful evolution of the system
- Support for multiple message format versions simultaneously

## Technical Implementation

### Message Bus Architecture

The Core Message Bus implements a **brokered messaging pattern** using **NATS** as the central broker, with **JetStream** used selectively for durability where required.

**Internal Communication (Backend Modules):**
- **Protocol**: NATS with Protocol Buffers payloads
- **Transport**: NATS subjects for pub/sub and request/reply
- **Pattern**: Pub/Sub + request/reply (correlation + reply subjects) + streaming chunk fanout
- **Broker**: NATS server (single node for local-first, clustered for enterprise)
- **Durability**: JetStream for correctness-critical flows (e.g. work queues, durable notifications)

**External Communication (Subsystems):**
- **Frontend (Flutter)**: REST API + WebSocket for realtime delivery; HTTP catch-up is always available
- **CLI (Python)**: REST API (admin/ops) and internal messaging only where explicitly required
- **Studio (React)**: REST API for admin operations (early development)
- **Transport**: All external clients connect to backend's API Gateway on port 8771

### Message Bus Technology

The Core Message Bus uses **NATS**:

- **High-performance:** Asynchronous messaging with minimal overhead
- **Secure by default:** Centralized authentication/authorization at the broker
- **Flexible patterns:** Pub/sub, request/reply, and JetStream-backed durable streams
- **Operationally simple:** Single broker abstraction used across local-first and enterprise deployments

### Message Format

Protocol Buffers provide:
- **Binary serialization:** Compact, fast encoding/decoding
- **Strong typing:** Compile-time validation and code generation
- **Versioning:** Backward compatibility through schema evolution
- **Cross-language:** Python (6.32), Dart (5.0) - wire-compatible
- **Production Status:** All core messages use protobuf (logs, events, modelservice requests)

### Message Validation

Messages are validated through Protocol Buffers' built-in validation:
- Compile-time type checking
- Runtime schema validation
- Required fields enforcement
- Automatic versioning support

### Topic Hierarchy

The message bus uses a hierarchical topic structure that organizes messages by functional domain and purpose:

### Core Domains

**IMPORTANT**: AICO uses a centralized topic registry (`AICOTopics`) with slash-based notation for all message bus topics.

### Subject Naming and Tenancy

Subjects are **tenant-scoped** to enforce hard isolation in multi-tenant deployments.

- **Subject format**: `aico.<tenant_id>.<domain>.<action>`
- **User scoping**: user identity is passed via message metadata attributes (not by exploding subjects)
- **JetStream streams**: configured with tenant-scoped wildcards (e.g. `aico.*.conversation.>`)

- **emotion/** - Emotion simulation related messages
  - `emotion/state/current` - Current emotional state
  - `emotion/state/update` - Emotional state changes
  - `emotion/appraisal/event` - Emotional appraisal of events

- **personality/** - Personality simulation related messages
  - `personality/state/current` - Current personality state
  - `personality/expression/communication` - Communication style parameters
  - `personality/expression/decision` - Decision-making parameters
  - `personality/expression/emotional` - Emotional tendency parameters

- **agency/** - Autonomous agency related messages
  - `agency/goals/current` - Current agent goals
  - `agency/initiative` - Proactive engagement initiatives
  - `agency/decision/request` - Decision-making requests
  - `agency/decision/response` - Decision outcomes

- **conversation/** - Conversation and dialogue related messages
  - `conversation/user/input/v1` - User input messages
  - `conversation/ai/response/v1` - AI response messages
  - `conversation/context/current` - Current conversation context
  - `conversation/history/add` - Historical conversation data

- **memory/** - Memory and learning related messages
  - `memory/store/request` - Memory storage requests
  - `memory/retrieve/request` - Memory retrieval requests
  - `memory/consolidation/start` - Memory consolidation triggers
  - `memory/semantic/query` - Semantic memory queries
  - `memory/working/update` - Working memory updates

- **user/** - User-related messages
  - `user/interaction/history` - User interaction patterns
  - `user/feedback/explicit` - Explicit user feedback
  - `user/state/update` - Inferred user state changes

- **modelservice/** - Model service related messages
  - `modelservice/completions/request/v1` - LLM completion requests
  - `modelservice/completions/response/v1` - LLM completion responses
  - `modelservice/embeddings/request/v1` - Embedding generation requests
  - `modelservice/embeddings/response/v1` - Embedding responses
  - `modelservice/ner/request/v1` - Named entity recognition requests
  - `modelservice/ner/response/v1` - NER responses
  - `modelservice/sentiment/request/v1` - Sentiment analysis requests
  - `modelservice/sentiment/response/v1` - Sentiment analysis responses

- **ui/** - User Interface related messages
  - `ui/state/update` - UI state changes (theme, navigation, connection status)
  - `ui/interaction/event` - User interactions (clicks, input, gestures)
  - `ui/notification/show` - Display notifications and alerts
  - `ui/command/execute` - Backend commands to frontend
  - `ui/preferences/update` - UI preferences and settings updates

- **system/** - System management messages
  - `system/bus/started` - Message bus startup events
  - `system/bus/stopping` - Message bus shutdown events
  - `system/module/registered` - Module registration events
  - `system/health` - System health checks

- **logs/** - Logging and audit messages
  - `logs/backend/main` - Backend main process logs
  - `logs/backend/api_gateway` - API Gateway logs
  - `logs/cli/*` - All CLI command logs
  - `logs/modelservice/*` - Modelservice logs
  - `logs/*` - All log topics (wildcard subscription)

### Cross-Cutting Concerns

- **crisis/** - Crisis detection and handling
  - `crisis/detection` - Crisis signals and alerts
  - `crisis/response` - Crisis response coordination

- **expression/** - Cross-modal expression coordination
  - `expression/coordination` - Coordinated expression directives
  - `expression/feedback` - Expression effectiveness feedback

- **learning/** - Shared learning coordination
  - `learning/coordination` - Learning signals and coordination
  - `learning/feedback` - Learning effectiveness feedback

## Module Integration Patterns

### Publisher-Subscriber Pattern

Modules interact with the message bus through a consistent pattern:

1. **Initialization**:
   - Modules connect to the message bus on startup
   - They declare topic subscriptions based on their functionality
   - They register message handlers for each subscribed topic

2. **Message Publication**:
   - Modules publish messages when their internal state changes
   - Messages include standardized metadata and domain-specific payloads
   - Publication is non-blocking and asynchronous

3. **Message Consumption**:
   - Modules receive messages for their subscribed topics
   - Message handlers process incoming messages
   - Processing may trigger internal state changes or new message publications

### Example: Emotion-Personality Integration

The Emotion Simulation and Personality Simulation modules integrate through the message bus:

1. Personality Simulation publishes `personality/expression/emotional` messages
2. Emotion Simulation subscribes to these messages to adjust emotional tendencies
3. Emotion Simulation publishes `emotion/state/current` messages
4. Personality Simulation subscribes to these messages to inform personality expression

This bidirectional communication happens without direct dependencies between the modules.

### Using the Central Topic Registry

All code should use the `AICOTopics` class instead of string literals. In practice this looks like:

```python
from aico.core.bus import create_client
from aico.core.topics import AICOTopics

client = create_client("api_gateway")
await client.connect()

await client.publish(AICOTopics.EMOTION_STATE_CURRENT, emotion_data)
await client.subscribe(AICOTopics.CONVERSATION_USER_INPUT, handler)
```

The `TopicMigration` helper converts legacy dot-notation topics to the new slash-based scheme for backward compatibility where needed.

## Plugin Integration

The Plugin Manager mediates plugin access to the message bus:

1. **Topic Access Control**:
   - Plugins request access to specific topics
   - Plugin Manager enforces access policies based on plugin permissions
   - Unauthorized topic access attempts are blocked and logged

2. **Message Validation**:
   - All plugin-originated messages are validated before publication
   - Malformed messages are rejected to prevent system instability
   - Message rate limiting prevents denial-of-service attacks

3. **Sandboxed Publication**:
   - Plugins publish through the Plugin Manager proxy
   - Messages are tagged with plugin identity for traceability
   - Plugin-specific topic prefixes isolate plugin messages

## Security and Privacy Considerations

### Message Security

1. **Authentication**:
   - NATS enforces client authentication at the broker boundary.
   - Production deployments do not run an unauthenticated broker.

2. **Authorization**:
   - Subject-level authorization is enforced at the broker boundary.
   - Tenancy is primarily enforced via tenant-scoped subjects (`aico.<tenant_id>....`).
   - User identity is carried via message metadata attributes for routing and policy checks.

### Privacy Protection

1. **Data Minimization**:
   - Messages contain only necessary information
   - Sensitive data is filtered before publication
   - User identifiers are anonymized where possible

2. **Transport and Payload Protection**:
   - Transport security is provided by the deployment (NATS configuration + environment).
   - Sensitive payloads should be treated as sensitive even on internal subjects; minimize content and rely on Postgres as the system of record.

## Performance Considerations

### Message Throughput

The message bus is designed to handle:
- High-frequency emotional state updates
- Real-time conversation events
- Periodic memory consolidation
- Burst traffic during multi-modal coordination

### Optimization Strategies

1. **Message Prioritization**:
   - Critical messages (e.g., crisis detection) receive higher priority
   - Non-time-sensitive messages may be queued during high load

2. **Payload Optimization**:
   - Large payloads may use compression
   - References instead of full content where appropriate
   - Selective field inclusion for performance-critical paths

3. **Subscription Optimization**:
   - Fine-grained topic subscriptions to reduce unnecessary message processing
   - Message filtering at the source when possible
   - Local caching of frequently accessed message data

   - Correlation IDs link related messages
   - End-to-end tracing of message flows
   - Timing metrics for message processing

2. **Traffic Monitoring**:
   - Topic-level message volume metrics
   - Latency measurements for critical paths
   - Queue depth monitoring for backpressure detection

3. **Debugging Tools**:
   - Message bus inspector for real-time monitoring
   - Message replay capabilities for testing
   - Topic subscription viewer to understand module connectivity

## Message Definition and Code Generation

### Protocol Buffer Definitions

All message definitions are maintained as Protocol Buffer (`.proto`) files in the `/proto/` directory:

- Core message envelope: `/proto/core/envelope.proto`
- Emotion messages: `/proto/emotion/emotion.proto`
- Conversation messages: `/proto/conversation/conversation.proto`
- Personality messages: `/proto/personality/personality.proto`
- Integration messages: `/proto/integration/integration.proto`
- UI messages: `/proto/ui/ui.proto`

### Code Generation Pipeline

The build process automatically generates language-specific code from these definitions:

1. Python classes for backend services
2. Dart classes for Flutter frontend
3. Additional language bindings as needed

### NATS Security Model

NATS security (authentication + authorization) is enforced at the broker boundary; application code should treat the message bus as a trusted internal fabric and rely on tenant-scoped subjects plus metadata for routing and policy enforcement.

### Testing and Validation

Message bus behavior can be verified via the `aico bus` CLI commands (`test`, `monitor`, `stats`) and integration tests that validate tenant scoping and JetStream durability policies.

### Migration from Plaintext

#### Removed Components
1. **Plaintext fallback code**: All fallback mechanisms removed
2. **Mixed message bus stacks**: Legacy broker paths are not supported in the current architecture.

#### Breaking Changes
- **No backward compatibility**: Old plaintext clients cannot connect
- **Fail-secure only**: No insecure fallback modes

### Troubleshooting

#### Common Issues

**Authentication/Authorization Failures:**
Verify NATS connectivity, credentials, and subject permissions for the service.

#### Debug Logging

Debug logging for the message bus can be enabled via the standard Python logging configuration on the `aico.core.bus` logger.

### Security Guarantees

#### What is Protected
✅ **Broker-authenticated clients**  
✅ **Subject-level authorization**  
✅ **Tenant-scoped subjects for isolation**  
✅ **No insecure fallback modes in production**  

#### What is NOT Protected
❌ **Application-level message content** (use additional encryption if needed)  
❌ **Subject names** (metadata for routing/operations)  
❌ **Message timing/frequency** (traffic analysis still possible)  

### Performance Impact

#### Encryption Overhead
- **CPU**: depends on the chosen transport security configuration
- **Memory**: Minimal additional memory usage
- **Latency**: typically sub-millisecond per message on local networks
- **Throughput**: >95% of plaintext performance maintained

#### Optimization Tips
1. **Reuse connections**: Avoid frequent connect/disconnect cycles
2. **Batch messages**: Group small messages when possible
3. **Monitor connection churn**: Prefer long-lived connections where possible

## Conclusion

The Core Message Bus architecture is fundamental to AICO's modular, event-driven design. It enables:

- **Modularity**: Components can be developed, tested, and deployed independently
- **Extensibility**: New modules and plugins can be integrated without modifying existing code
- **Resilience**: Failures in one module don't cascade to others
- **Adaptability**: The system can evolve through versioned message formats
- **Autonomy**: Modules can operate independently based on events
- **Performance**: Binary serialization optimizes for speed and size
- **Cross-Platform**: Consistent message format across all platforms and devices
- **Security**: Broker-enforced authentication/authorization and tenant scoping

By providing a standardized, secure communication backbone, the message bus facilitates the complex interactions required for AICO's proactive agency, emotional presence, personality consistency, and multi-modal embodiment across its federated device network.
