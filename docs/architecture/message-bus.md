# Core Message Bus Architecture

## Overview

The Core Message Bus is the central nervous system of AICO, enabling modular, event-driven communication between all system components. It implements a publish-subscribe (pub/sub) pattern that allows modules to communicate without direct dependencies, supporting AICO's core principles of modularity, autonomy, and extensibility.

**🔒 Security First:** All message bus communication is encrypted using CurveZMQ with mandatory authentication. There is no plaintext fallback - the system enforces secure communication or fails completely.

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

The Core Message Bus implements a **hybrid broker pattern** with the backend service acting as the central message coordinator:

**Internal Communication (Backend Modules):**
- **Protocol**: ZeroMQ with Protocol Buffers 6.32
- **Transport**: TCP for all communication (inproc/ipc not used)
- **Pattern**: Pub/Sub with topic hierarchy and wildcard pattern matching
- **Broker**: Backend service runs central ZeroMQ broker on ports 5555 (frontend) and 5556 (backend)
- **Encryption**: Mandatory CurveZMQ with no plaintext fallback

**External Communication (Subsystems):**
- **Frontend (Flutter)**: REST API (Dio client) + WebSocket for streaming, Protocol Buffers 5.0 (wire-compatible)
- **CLI (Python)**: Direct ZeroMQ with CurveZMQ encryption, REST API fallback
- **Studio (React)**: REST API for admin operations (early development)
- **Transport**: All external clients connect to backend's API Gateway on port 8771

### Message Bus Technology

The Core Message Bus uses **ZeroMQ** with **CurveZMQ encryption**:

- **High-performance:** Asynchronous messaging with minimal overhead
- **Secure by default:** Mandatory CurveZMQ encryption for all communication
- **Flexible patterns:** Pub/sub with hierarchical topic routing
- **Embedded:** No external message broker dependencies

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

## Topic Hierarchy

The message bus uses a hierarchical topic structure that organizes messages by functional domain and purpose:

### Core Domains

**IMPORTANT**: AICO uses a centralized topic registry (`AICOTopics`) with slash-based notation for all message bus topics.

### ZeroMQ Subscription Behavior

#### Critical Considerations

1. **ZeroMQ uses prefix matching only**
   - When you subscribe to a pattern, ZeroMQ converts it to a prefix filter
   - Example: `logs/*` becomes ZMQ filter `logs/`
   - This means ZeroMQ will deliver ANY message whose topic starts with that prefix

2. **Application-level pattern matching**
   - After ZeroMQ delivers messages based on prefix, AICO performs application-level pattern matching
   - This is where wildcard semantics are applied

#### ZeroMQ Prefix Matching

ZeroMQ uses simple prefix matching (no wildcards):

| Pattern | ZMQ Filter | Behavior | Matches |
|---------|------------|----------|----------|
| `logs/backend` | `logs/backend` | Exact prefix match | `logs/backend`, `logs/backend/main`, `logs/backend/api` |
| `logs/` | `logs/` | Prefix match | All topics starting with `logs/` |
| `*` or `**` | `""` (empty) | Match all | Every message on the bus |

#### Common Subscription Patterns

| Use Case | Pattern | ZMQ Filter | Matches |
|----------|---------|------------|----------|
| All logs | `logs/` | `logs/` | All topics starting with `logs/` |
| Backend logs | `logs/backend/` | `logs/backend/` | All topics starting with `logs/backend/` |
| Specific module | `logs/backend/main` | `logs/backend/main` | Topics starting with `logs/backend/main` |
| All messages | `*` or `**` | `""` (empty) | Every message on the bus |

#### Best Practices

1. **Use prefix patterns for hierarchical subscriptions**
   - Subscribe to `logs/` to receive all log messages
   - Subscribe to `logs/backend/` to receive all backend logs
   - Be specific with prefixes to avoid unnecessary message delivery

2. **Understand ZeroMQ's prefix behavior**
   - ZeroMQ delivers ANY message whose topic starts with your filter
   - No application-level filtering is implemented
   - Design topics carefully to leverage prefix matching effectively

#### Common Pitfalls

1. **Expecting wildcard behavior**
   - ZeroMQ does NOT support `*` or `**` wildcards
   - `logs/*` is treated as literal prefix `logs/*`, not a wildcard
   - Use proper prefixes like `logs/` instead

2. **Over-subscribing with broad prefixes**
   - Subscribing to `logs/` delivers ALL log messages
   - This can cause performance issues with high message volume
   - Use specific prefixes when possible

3. **Inconsistent topic structure**
   - Design hierarchical topics to work well with prefix matching
   - Use consistent separators (slashes) for topic hierarchy

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

1. **CurveZMQ Encryption**:
   - **Mandatory encryption**: All message bus communication uses CurveZMQ with no plaintext fallback
   - **Deterministic key derivation**: Keys derived from master key using Argon2id + Z85 encoding
   - **Mutual authentication**: Both broker and clients authenticate using public key cryptography
   - **Fail-secure behavior**: System fails completely rather than falling back to plaintext

2. **Authentication**:
   - All modules authenticate to the message bus using CurveZMQ certificates
   - Broker validates specific client public keys (no CURVE_ALLOW_ANY)
   - Unauthorized connections are rejected with comprehensive security logging
   - Plugin authentication uses separate CurveZMQ credentials

3. **Authorization**:
   - Topic-level access control limits which modules can publish/subscribe
   - Sensitive topics have restricted access
   - Plugin access is limited to approved topics

### Privacy Protection

1. **Data Minimization**:
   - Messages contain only necessary information
   - Sensitive data is filtered before publication
   - User identifiers are anonymized where possible

2. **End-to-End Encryption**:
   - **Transport encryption**: All message bus traffic encrypted with CurveZMQ
   - **Message payload encryption**: Sensitive payloads additionally encrypted at application level
   - **Zero plaintext transmission**: No unencrypted data crosses network boundaries
   - **Key management**: Automatic key derivation with secure storage integration

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

### CurveZMQ Implementation

AICO's message bus implements mandatory CurveZMQ encryption for all inter-component communication with the following core principles:

1. **Mandatory Encryption**: No plaintext fallback – system fails securely if encryption cannot be established.
2. **Mutual Authentication**: Broker and clients authenticate using public key cryptography.
3. **Deterministic Key Derivation**: All keys derived from the master key using Argon2id + Z85 encoding.
4. **Fail-Secure Design**: Encryption failures result in system failure, not insecure fallback.

Key management, broker/client configuration, socket options, and security logging are all encapsulated in `MessageBusBroker`, `MessageBusClient`, and `AICOKeyManager`, so most code only needs to create a client and connect.

### Testing and Validation

Encryption and message bus behavior can be verified via the existing test script (`scripts/test_curve_zmq.py`) and the `aico bus` CLI commands (`test`, `monitor`, `stats`). Detailed command output is omitted here to keep the architecture doc focused.

### Migration from Plaintext

#### Removed Components
1. **Plaintext fallback code**: All fallback mechanisms removed
2. **CURVE_ALLOW_ANY**: Replaced with explicit client authentication
3. **Raw ZMQ sockets**: All components use encrypted MessageBusClient
4. **IPC adapter**: Unused ZeroMQ IPC adapter removed

#### Breaking Changes
- **No backward compatibility**: Old plaintext clients cannot connect
- **Master key required**: All components require master key for operation
- **Fail-secure only**: No graceful degradation to plaintext mode

### Troubleshooting

#### Common Issues

**Authentication Failures:**
```
[SECURITY] CRITICAL: Failed to setup CurveZMQ authentication
```
**Solution**: Verify master key is available and AICOKeyManager is properly configured.

**Key Derivation Errors:**
```
[SECURITY] CRITICAL: Failed to setup CurveZMQ encryption
```
**Solution**: Check master key authentication and key manager initialization.

**Connection Refused:**
```
MessageBusError: CurveZMQ socket configuration failed
```
**Solution**: Ensure broker is running and client public key is in authorized list.

#### Debug Logging

Debug logging for the message bus can be enabled via the standard Python logging configuration on the `aico.core.bus` logger.

### Security Guarantees

#### What is Protected
✅ **All message bus traffic encrypted**  
✅ **Mutual authentication between all components**  
✅ **No plaintext fallback possible**  
✅ **Deterministic key derivation from master key**  
✅ **Comprehensive security logging**  

#### What is NOT Protected
❌ **Application-level message content** (use additional encryption if needed)  
❌ **Topic names** (visible in ZeroMQ subscription filters)  
❌ **Message timing/frequency** (traffic analysis still possible)  

### Performance Impact

#### Encryption Overhead
- **CPU**: ~5-10% overhead for CurveZMQ encryption/decryption
- **Memory**: Minimal additional memory usage
- **Latency**: <1ms additional latency per message
- **Throughput**: >95% of plaintext performance maintained

#### Optimization Tips
1. **Reuse connections**: Avoid frequent connect/disconnect cycles
2. **Batch messages**: Group small messages when possible
3. **Monitor key derivation**: Cache derived keys when appropriate

## Conclusion

The Core Message Bus architecture is fundamental to AICO's modular, event-driven design. It enables:

- **Modularity**: Components can be developed, tested, and deployed independently
- **Extensibility**: New modules and plugins can be integrated without modifying existing code
- **Resilience**: Failures in one module don't cascade to others
- **Adaptability**: The system can evolve through versioned message formats
- **Autonomy**: Modules can operate independently based on events
- **Performance**: Binary serialization optimizes for speed and size
- **Cross-Platform**: Consistent message format across all platforms and devices
- **Security**: Mandatory CurveZMQ encryption ensures all communication is protected

By providing a standardized, secure communication backbone, the message bus facilitates the complex interactions required for AICO's proactive agency, emotional presence, personality consistency, and multi-modal embodiment across its federated device network.
