# Core Message Bus Architecture

## Overview

The Core Message Bus is the central nervous system of AICO, enabling modular, event-driven communication between all system components. It implements a publish-subscribe (pub/sub) pattern that allows modules to communicate without direct dependencies, supporting AICO's core principles of modularity, autonomy, and extensibility.

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

All messages follow a consistent envelope structure defined in Protocol Buffers:

```protobuf
message AicoMessage {
  MessageMetadata metadata = 1;
  oneof payload {
    EmotionState emotion_state = 2;
    ConversationMessage conversation_message = 3;
    // Other message types...
  }
}

message MessageMetadata {
  string message_id = 1;       // UUID string
  string timestamp = 2;        // ISO 8601 format
  string source = 3;           // Source module name
  string message_type = 4;     // topic/subtopic format
  string version = 5;          // Schema version
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
- **Protocol**: ZeroMQ with Protocol Buffers
- **Transport**: `inproc://` for same-process modules, `ipc://` for cross-process
- **Pattern**: Pub/Sub with topic hierarchy
- **Host**: Backend service runs central ZeroMQ broker on `tcp://localhost:5555`

**External Communication (Subsystems):**
- **Frontend (Flutter)**: WebSocket for real-time updates, REST API for commands
- **CLI (Python)**: ZeroMQ IPC with localhost REST fallback
- **Studio (React)**: REST API for admin operations, WebSocket for monitoring
- **Transport**: All external clients connect to backend's API Gateway

### Message Bus Technology

The Core Message Bus uses **ZeroMQ** as the standard internal messaging system:

- High-performance, asynchronous messaging library
- Lightweight and embedded within the application
- Supports multiple messaging patterns (pub/sub, request/reply)
- Provides reliable message delivery with minimal overhead
- Proven architecture pattern (similar to ROS robotics framework)

ZeroMQ is chosen for its performance, flexibility, and suitability for all local and internal communication needs in AICO.

### Message Format

All messages use Protocol Buffers for serialization, providing:
- High-performance binary serialization
- Strong typing and schema validation
- Cross-language code generation
- Efficient size (smaller than JSON)
- Backward compatibility through versioning

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
  - `conversation/context/current` - Current conversation context
  - `conversation/history/add` - Historical conversation data
  - `conversation/intent/detected` - Detected user intents

- **memory/** - Memory and learning related messages
  - `memory/store/request` - Memory storage requests
  - `memory/retrieve/request` - Memory retrieval requests
  - `memory/consolidation/start` - Memory consolidation triggers

- **user/** - User-related messages
  - `user/interaction/history` - User interaction patterns
  - `user/feedback/explicit` - Explicit user feedback
  - `user/state/update` - Inferred user state changes

- **llm/** - Large Language Model related messages
  - `llm/conversation/events` - Conversation events from LLM
  - `llm/prompt/conditioning/request` - Requests for prompt conditioning
  - `llm/prompt/conditioning/response` - Prompt conditioning parameters

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
  - `logs/entry` - Individual log entries
  - `logs/*` - All log topics (wildcard subscription)

### Cross-Cutting Concerns

- **crisis.*** - Crisis detection and handling
  - `crisis.detection` - Crisis signals and alerts
  - `crisis.response` - Crisis response coordination

- **expression.*** - Cross-modal expression coordination
  - `expression.coordination` - Coordinated expression directives
  - `expression.feedback` - Expression effectiveness feedback

- **learning.*** - Shared learning coordination
  - `learning.coordination` - Learning signals and coordination
  - `learning.feedback` - Learning effectiveness feedback

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

All code should use the `AICOTopics` class instead of string literals:

```python
from aico.core.topics import AICOTopics

# Correct usage
await client.publish(AICOTopics.EMOTION_STATE_CURRENT, emotion_data)
await client.subscribe(AICOTopics.ALL_PERSONALITY, handler)

# Incorrect usage (deprecated)
await client.publish("emotion.state.current", emotion_data)  # DON'T DO THIS
```

**Migration Support**: The `TopicMigration` class provides automatic conversion from old dot notation to new slash notation for backward compatibility during the transition period.

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
   - All modules authenticate to the message bus
   - Unauthorized connections are rejected
   - Plugin authentication uses separate credentials

2. **Authorization**:
   - Topic-level access control limits which modules can publish/subscribe
   - Sensitive topics have restricted access
   - Plugin access is limited to approved topics

### Privacy Protection

1. **Data Minimization**:
   - Messages contain only necessary information
   - Sensitive data is filtered before publication
   - User identifiers are anonymized where possible

2. **Encryption**:
   - Message payloads containing sensitive data are encrypted
   - Transport-level encryption protects all message bus traffic
   - Key rotation policies ensure long-term security

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

## Message Persistence

### Storage Strategy

**Database**: libSQL (already integrated and encrypted)
- **Selective persistence** for audit logs, debugging, and cross-device sync
- **Append-only message log** with SQL queryability
- **JSON metadata** support for flexible message attributes

**Storage Schema**:
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    topic TEXT,
    source TEXT,
    message_type TEXT,
    payload BLOB,      -- Protocol Buffer binary
    metadata JSON,     -- Flexible attributes
    INDEX(topic, timestamp)
);
```

**Persistence Policy**:
- **Always**: Security events, audit logs, admin actions
- **Optional**: Debug mode message replay, cross-device sync
- **Never**: High-frequency emotion states (unless debugging)

## Monitoring and Debugging

The message bus includes facilities for:

1. **Message Tracing**:
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

## Conclusion

The Core Message Bus architecture is fundamental to AICO's modular, event-driven design. It enables:

- **Modularity**: Components can be developed, tested, and deployed independently
- **Extensibility**: New modules and plugins can be integrated without modifying existing code
- **Resilience**: Failures in one module don't cascade to others
- **Adaptability**: The system can evolve through versioned message formats
- **Autonomy**: Modules can operate independently based on events
- **Performance**: Binary serialization optimizes for speed and size
- **Cross-Platform**: Consistent message format across all platforms and devices

By providing a standardized communication backbone, the message bus facilitates the complex interactions required for AICO's proactive agency, emotional presence, personality consistency, and multi-modal embodiment across its federated device network.
