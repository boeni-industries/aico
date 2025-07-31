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

All messages follow a consistent envelope structure:
```json
{
  "metadata": {
    "message_id": "uuid-string",
    "timestamp": "2025-07-29T14:48:25.123Z",
    "source": "module-name",
    "message_type": "topic.subtopic",
    "version": "1.0"
  },
  "payload": {
    // Message-specific content
  }
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

### Message Bus Technology

The Core Message Bus is implemented using **ZeroMQ** as the standard and only supported internal message bus for AICO.

- High-performance, asynchronous messaging library
- Lightweight and embedded within the application
- Supports multiple messaging patterns (pub/sub, request/reply)
- Provides reliable message delivery with minimal overhead

ZeroMQ is chosen for its performance, flexibility, and suitability for all local and internal communication needs in AICO.

### Message Format

All messages use JSON for serialization, providing:
- Human-readable format for debugging
- Wide language and platform support
- Flexible schema evolution
- Native compatibility with web technologies

### Message Validation

Messages are validated against JSON Schema definitions to ensure:
- Structural correctness
- Type safety
- Required fields presence
- Version compatibility

## Topic Hierarchy

The message bus uses a hierarchical topic structure that organizes messages by functional domain and purpose:

### Core Domains

- **emotion.*** - Emotion simulation related messages
  - `emotion.state.current` - Current emotional state
  - `emotion.state.update` - Emotional state changes
  - `emotion.appraisal.event` - Emotional appraisal of events

- **personality.*** - Personality simulation related messages
  - `personality.state.current` - Current personality state
  - `personality.expression.communication` - Communication style parameters
  - `personality.expression.decision` - Decision-making parameters
  - `personality.expression.emotional` - Emotional tendency parameters

- **agency.*** - Autonomous agency related messages
  - `agency.goals.current` - Current agent goals
  - `agency.initiative` - Proactive engagement initiatives
  - `agency.decision.request` - Decision-making requests
  - `agency.decision.response` - Decision outcomes

- **conversation.*** - Conversation and dialogue related messages
  - `conversation.context` - Current conversation context
  - `conversation.history` - Historical conversation data
  - `conversation.intent` - Detected user intents

- **memory.*** - Memory and learning related messages
  - `memory.store` - Memory storage requests
  - `memory.retrieve` - Memory retrieval requests/responses
  - `memory.consolidation` - Consolidated memory data

- **user.*** - User-related messages
  - `user.interaction.history` - User interaction patterns
  - `user.feedback` - Explicit and implicit user feedback
  - `user.state` - Inferred user state

- **llm.*** - Large Language Model related messages
  - `llm.conversation.events` - Conversation events from LLM
  - `llm.prompt.conditioning.request` - Requests for prompt conditioning
  - `llm.prompt.conditioning.response` - Prompt conditioning parameters

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

1. Personality Simulation publishes `personality.expression.emotional` messages
2. Emotion Simulation subscribes to these messages to adjust emotional tendencies
3. Emotion Simulation publishes `emotion.state.current` messages
4. Personality Simulation subscribes to these messages to inform personality expression

This bidirectional communication happens without direct dependencies between the modules.

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

## Conclusion

The Core Message Bus architecture is fundamental to AICO's modular, event-driven design. It enables:

- **Modularity**: Components can be developed, tested, and deployed independently
- **Extensibility**: New modules and plugins can be integrated without modifying existing code
- **Resilience**: Failures in one module don't cascade to others
- **Adaptability**: The system can evolve through versioned message formats
- **Autonomy**: Modules can operate independently based on events

By providing a standardized communication backbone, the message bus facilitates the complex interactions required for AICO's proactive agency, emotional presence, personality consistency, and multi-modal embodiment.

For specific message formats used by individual modules, refer to the respective message format documentation:
- Emotion Simulation: [emotion_sim_msg.md](./emotion_sim_msg.md)
- Personality Simulation: [personality_sim_msg.md](./personality_sim_msg.md)
- Integration Messages: [integration_msg.md](./integration_msg.md)
