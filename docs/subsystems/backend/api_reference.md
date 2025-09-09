---
title: API Reference
---

# API Reference

AICO's networking architecture is designed around the principle of **adaptive communication** - choosing the right protocol for each interaction pattern while maintaining a unified developer experience. The system supports both local-first operation (coupled mode) and distributed deployment (detached mode), with seamless transitions between connectivity states.

## Design Philosophy

The multi-protocol approach serves three core objectives:

1. **Interaction Diversity**: Different user interactions require different communication patterns - real-time conversation needs low latency, while configuration changes can use traditional request-response
2. **Deployment Flexibility**: Support both embedded local deployments and distributed cloud architectures without changing application logic
3. **Progressive Enhancement**: Start with simple HTTP APIs and add real-time capabilities as needed, without breaking existing integrations

## Protocol Selection Strategy

| Protocol | Purpose | Transport | Use Case | Rationale |
|----------|---------|-----------|----------|----------|
| **REST API** | Commands, queries, configuration | HTTP/HTTPS | Standard client-server operations | Universal compatibility, stateless, cacheable |
| **WebSocket** | Real-time bidirectional communication | WSS/WS | Live updates, notifications | Low latency, persistent connection, event-driven |
| **gRPC** | High-performance binary protocol | HTTP/2 | Optional internal services | Type safety, streaming, efficient serialization |

### Protocol Selection Logic

**REST API** is the foundation - every operation must be possible via REST to ensure maximum compatibility. WebSocket and gRPC are enhancements that provide better user experience for specific scenarios.

**WebSocket** enables AICO's real-time personality expression. When AICO's emotional state changes or when it wants to initiate conversation, WebSocket allows immediate communication without polling overhead.

**gRPC** is optional but valuable for high-throughput scenarios like vector similarity searches or when type safety is critical for internal service communication.

## REST API Architecture

### Design Principles

AICO's REST API follows **resource-oriented design** with a focus on **semantic clarity**. Each endpoint represents a meaningful action in the context of AI companionship rather than generic CRUD operations.

**Stateless by Design**: Each request contains all necessary context, enabling horizontal scaling and simplifying error recovery. Session state is maintained through JWT tokens rather than server-side sessions.

**Consistent Error Handling**: All endpoints use the same error format and HTTP status codes, making client integration predictable and debugging straightforward.

### Base Configuration
- **Base URL**: `http://localhost:8080/api/v1` (coupled) / `https://{backend-host}/api/v1` (detached)
- **Content-Type**: `application/json`
- **Authentication**: JWT Bearer tokens (enables stateless scaling)
- **Rate Limiting**: Per-endpoint limits (protects against abuse while allowing normal interaction patterns)

### Authentication Strategy

AICO uses **JWT-based authentication** to support both single-device and multi-device scenarios. The token-based approach enables seamless roaming between devices while maintaining security.

#### Core Authentication Flow

Authentication is designed around AICO's **family recognition** concept - users don't need traditional usernames/passwords but instead use natural recognition patterns.

```
POST /auth/login      # Natural recognition or fallback authentication
POST /auth/logout     # Secure session termination
POST /auth/refresh    # Token renewal without re-authentication
GET  /auth/session    # Current session validation and info
```

#### User Identity Management

User profiles in AICO represent **relationship context** rather than just account data. The profile contains interaction preferences, privacy settings, and relationship history.

```
POST /auth/register        # Initial relationship establishment
GET  /auth/profile         # Current relationship context
PUT  /auth/profile         # Update interaction preferences
POST /auth/change-password # Security credential updates
```

#### Multi-Device Coordination

Device management enables AICO's **roaming capabilities** - the AI companion can maintain continuity across different devices while respecting privacy boundaries.

```
GET    /auth/devices       # List trusted devices in family network
POST   /auth/devices/pair  # Establish trust with new device
DELETE /auth/devices/{id}  # Revoke device access
POST   /auth/emergency-reset # Complete relationship reset (privacy protection)
```

### Core Interaction Architecture

AICO's interaction endpoints are designed around **conversational AI patterns** rather than traditional application APIs. Each endpoint supports the natural flow of AI companionship.

#### Conversation Management

Conversation endpoints handle the **primary interaction loop** between user and AI. Unlike conversationbots, AICO maintains conversational context and can initiate interactions.

```
POST /conversation/message  # Send message and receive AI response
GET  /conversation/history   # Retrieve conversation timeline
GET  /conversation/context   # Current conversational state and topics
POST /conversation/clear     # Reset conversation (privacy control)
```

**Design Rationale**: The message endpoint is synchronous to provide immediate feedback, while history and context are separate to enable efficient partial loading and context management.

#### Personality & Emotion Dynamics

These endpoints expose AICO's **emotional intelligence** - both current state and the ability to observe emotional patterns over time.

```
GET  /personality/current    # Current personality expression
PUT  /personality/traits     # Adjust personality parameters
GET  /emotion/current        # Real-time emotional state
GET  /emotion/history        # Emotional patterns and trends
```

**Design Rationale**: Personality is adjustable to allow relationship customization, while emotion is primarily observable to maintain authentic AI behavior.

#### Memory & Context Intelligence

Memory endpoints enable AICO's **long-term relationship building** - storing, retrieving, and connecting experiences across time.

```
POST /memory/store          # Explicitly store important information
GET  /memory/search         # Semantic search across memories
GET  /memory/recent         # Recent memories and experiences
DELETE /memory/{id}         # Privacy-controlled memory deletion
```

**Design Rationale**: Explicit memory storage allows users to highlight important information, while semantic search enables natural memory retrieval patterns.

#### Autonomous Agency

Agency endpoints support AICO's **proactive behavior** - the AI can set goals, track progress, and initiate actions independently.

```
GET  /agency/goals          # Current AI goals and initiatives
POST /agency/goals          # User can suggest goals for AI
PUT  /agency/goals/{id}     # Modify or prioritize goals
DELETE /agency/goals/{id}   # Cancel goals (user override)
```

**Design Rationale**: Goals are collaborative - both AI and user can create them, but user always has override control for trust and safety.

### Admin Endpoints (Existing)
```
GET    /health
GET    /gateway/status
GET    /gateway/stats
GET    /auth/sessions
DELETE /auth/sessions/{id}
POST   /auth/tokens/revoke
GET    /security/stats
POST   /security/block-ip
DELETE /security/block-ip/{ip}
GET    /config
POST   /routing/mapping
DELETE /routing/mapping/{external_topic}
```

### Request/Response Format

#### Standard Request Envelope
```json
{
  "metadata": {
    "request_id": "uuid",
    "timestamp": "ISO8601",
    "client_version": "1.0.0"
  },
  "payload": {
    // Endpoint-specific data
  }
}
```

#### Standard Response Envelope
```json
{
  "metadata": {
    "request_id": "uuid",
    "timestamp": "ISO8601",
    "status": "success|error",
    "version": "1.0.0"
  },
  "data": {
    // Response data
  },
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

### Error Handling

#### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Rate Limited
- `500` - Internal Server Error

#### Error Response Format
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Request validation failed",
    "details": {
      "field": "password",
      "reason": "Password must be at least 8 characters"

### Connection Management
- **URL**: `ws://localhost:8080/ws` (coupled) / `wss://{backend-host}/ws` (detached)`
- **Authentication**: JWT token in connection headers (maintains security without breaking real-time flow)
- **Heartbeat**: 30-second ping/pong interval (ensures connection health without being intrusive)
- **Reconnection**: Automatic with exponential backoff (seamless recovery from network interruptions)

### Message Format
```json
{
  "type": "message_type",
  "id": "message_id",
  "timestamp": "ISO8601",
  "data": {
    // Message-specific payload
  }
}
```

### Communication Patterns

#### Subscription-Based Updates

Clients subscribe to **relationship-relevant events** rather than technical system events. This keeps the focus on meaningful AI companion interactions.

**Topic Subscription Logic**: Users choose what aspects of AICO's internal state they want to observe - emotional changes, goal progress, or conversation insights.

```json
{
  "type": "subscribe",
  "data": {
    "topics": ["emotion.state", "conversation.events"]
  }
}
```

#### Real-Time Conversation Flow

**Immediate Response Pattern**: Unlike REST where conversation requires polling, WebSocket enables natural conversation timing with immediate AI responses.

```json
{
  "type": "message",
  "data": {
    "content": "Hello AICO",
    "context": {}  // Conversation context for continuity
  }
}
```

#### AI-Initiated Communication

**Proactive Engagement**: AICO can initiate conversations, share emotional insights, or provide updates without user prompting - essential for authentic AI companionship.

```json
{
  "type": "emotion_update",
  "data": {
    "valence": 0.7,    // Emotional positivity
    "arousal": 0.4,    // Energy level
    "dominance": 0.6   // Confidence/control
  }
}

{
  "type": "conversation_response",
  "data": {
    "content": "Hello! How can I help you today?",
    "emotion": "friendly",
    "confidence": 0.95  // AI's confidence in response appropriateness
  }
}
```

**Design Rationale**: Emotional updates include dimensional values (valence/arousal/dominance) to enable nuanced UI responses, while conversation responses include confidence to help users understand AI certainty.

### Topic Architecture

#### Relationship-Focused Topics

Topics are organized around **aspects of AI companionship** rather than technical system boundaries. This makes subscription decisions intuitive for users.

- **`emotion.state`** - Real-time emotional state updates (enables empathetic UI responses)
- **`personality.expression`** - Personality expression changes (shows AI character development)
- **`conversation.events`** - Conversation flow events (typing indicators, topic shifts, context changes)
- **`agency.goals`** - Goal updates and achievements (shows AI initiative and progress)
- **`system.status`** - System health and notifications (technical updates when necessary)

**Topic Design Philosophy**: Each topic represents information that enhances the human-AI relationship. Users subscribe based on how they want to experience AICO's presence, not technical implementation details.

## gRPC Architecture (Optional)

### High-Performance Communication Strategy

gRPC serves AICO's **computational intensive operations** - vector searches, large-scale memory retrieval, and bulk data synchronization. It's not used for user-facing interactions but for internal service communication.

**Type Safety Benefits**: Protocol Buffers ensure consistent data structures across services, reducing integration bugs and enabling confident refactoring.

**Streaming Capabilities**: gRPC's bidirectional streaming supports continuous data flows like real-time emotion analysis or ongoing memory indexing.

### Service Architecture

**Message-Oriented Design**: Services are organized around AI capabilities rather than technical functions.

```protobuf
service AICOService {
  rpc SendMessage(MessageRequest) returns (MessageResponse);      // Core conversation
  rpc GetEmotionState(EmptyRequest) returns (EmotionState);       // Emotional intelligence
  rpc StreamUpdates(SubscriptionRequest) returns (stream Update); // Real-time updates
}
```

**Structured Communication**: All messages include semantic context, not just raw data.

```protobuf
message MessageRequest {
  string content = 1;                    // User message content
  map<string, string> context = 2;       // Conversation context and metadata
}

message MessageResponse {
  string response = 1;                   // AI response content
  EmotionState emotion = 2;              // AI's emotional state during response
  float confidence = 3;                  // Response confidence level
}
```

### Connection Strategy
- **Address**: `localhost:8081` (coupled) / `{backend-host}:8081` (detached)
- **TLS**: Required for detached mode (maintains security for internal communication)
- **Authentication**: JWT metadata (consistent with REST/WebSocket authentication)
- **Compression**: gzip enabled (efficient for large AI model data transfers)

## Protocol Selection Framework

### Decision Matrix for AI Companion Interactions

#### REST API - Foundation Layer
**Primary Use Cases:**
- **Relationship Management**: User profiles, device pairing, privacy settings
- **Memory Operations**: Storing experiences, searching memories, managing context
- **Configuration**: Personality adjustments, interaction preferences
- **Administrative Tasks**: System health, security management

**Why REST for These Operations:**
- **Stateless Nature**: Each memory or configuration operation is self-contained
- **Cacheability**: User preferences and memories can be cached for performance
- **Universal Access**: Any client can integrate without special protocol support
- **Debugging**: HTTP tools make troubleshooting straightforward

#### WebSocket - Presence Layer
**Primary Use Cases:**
- **Live Conversation**: Natural conversation flow with immediate responses
- **Emotional Expression**: Real-time emotional state sharing
- **Proactive Engagement**: AI-initiated interactions and suggestions
- **Contextual Updates**: Conversation topic shifts, mood changes

**Why WebSocket for These Operations:**
- **Conversational Timing**: Natural conversation requires immediate response capability
- **AI Initiative**: AICO needs to initiate interactions without user prompting
- **Emotional Authenticity**: Real-time emotional expression feels more genuine
- **Reduced Latency**: No request overhead for frequent updates

#### gRPC - Intelligence Layer
**Primary Use Cases:**
- **Vector Operations**: Semantic search, similarity matching, embedding generation
- **Bulk Synchronization**: Multi-device data sync, large memory transfers
- **AI Model Communication**: Internal service coordination, model inference
- **Performance-Critical Paths**: High-throughput data processing

**Why gRPC for These Operations:**
- **Computational Efficiency**: Binary serialization reduces CPU overhead
- **Type Safety**: Complex AI data structures benefit from schema validation
- **Streaming**: Large datasets can be processed incrementally
- **Service Mesh**: Internal services need reliable, efficient communication

### Integration Strategy

**Layered Approach**: Start with REST for basic functionality, add WebSocket for real-time features, use gRPC for performance optimization.

**Fallback Capability**: Every gRPC and WebSocket operation has a REST equivalent, ensuring compatibility across different deployment scenarios.

**Progressive Enhancement**: Clients can use increasingly sophisticated protocols as their capabilities allow, without losing core functionality.

## Security Architecture

### Trust Model for AI Companions

AICO's security is built around **relationship-based trust** rather than traditional system security. The AI companion needs access to personal information to be effective, so security focuses on protecting that trust.

**Zero-Trust Foundation**: Every request is authenticated and authorized, even in local deployments, to establish consistent security patterns.

**Privacy-First Design**: Security measures protect user privacy without hindering the natural flow of AI companionship.

### Authentication Strategy

**JWT-Based Identity**: Enables seamless roaming between devices while maintaining security boundaries.

1. **Natural Recognition**: AICO attempts family recognition first (biometric, behavioral)
2. **Fallback Authentication**: Traditional credentials when recognition fails
3. **Token Issuance**: JWT access token (short-lived) + refresh token (longer-lived)
4. **Continuous Validation**: Every request validates current authorization
5. **Graceful Renewal**: Tokens refresh automatically without interrupting interaction

**Design Rationale**: The two-token system balances security (short access token lifetime) with user experience (automatic renewal without re-authentication).

### Transport Security

**TLS 1.3 Minimum**: Modern encryption standards protect all network communication.
- **AEAD Ciphers Only**: Authenticated encryption prevents tampering
- **Certificate Validation**: Required for detached mode to prevent man-in-the-middle attacks
- **HSTS**: Forces secure connections to prevent downgrade attacks

**Local vs Remote Security**: Even local deployments use TLS to establish consistent security patterns and protect against local network threats.

### Rate Limiting Philosophy

**Interaction-Aware Limits**: Rate limits are designed around natural conversation patterns rather than arbitrary technical limits.

- **Authentication**: 5 attempts per minute (prevents brute force while allowing legitimate retries)
- **Conversation**: 1000 requests per hour (supports extended conversations without restriction)
- **Real-Time**: 100 WebSocket messages per minute (natural conversation pace)
- **Administrative**: 10 requests per minute (administrative tasks are infrequent)

**Adaptive Limiting**: Limits can adjust based on relationship trust level and interaction history.

## Integration Architecture

### Frontend Integration Strategy

**Multi-Protocol Client Design**: Frontend applications use different protocols for different interaction patterns, creating a seamless user experience.

**REST for State Management**: Configuration, memory, and relationship management use REST for reliability and simplicity.

```dart
// Relationship and memory management
final response = await http.post(
  Uri.parse('$baseUrl/api/v1/conversation/message'),
  headers: {
    'Authorization': 'Bearer $token',
    'Content-Type': 'application/json',
  },
  body: jsonEncode({'content': message}),
);
```

**WebSocket for Live Interaction**: Real-time conversation and emotional expression use WebSocket for immediate responsiveness.

```dart
// Real-time conversation and presence
final channel = WebSocketChannel.connect(
  Uri.parse('$wsUrl/ws'),
  protocols: ['aico-v1'],  // Version-specific protocol
);
```

**Progressive Degradation**: If WebSocket fails, the application falls back to REST polling, ensuring functionality across different network conditions.

### Backend Integration Patterns

**Protocol Bridge Architecture**: The API Gateway translates between external protocols (REST/WebSocket/gRPC) and internal message bus communication.

**Unified Message Flow**: All external requests become internal messages, enabling consistent processing regardless of input protocol.

```python
# Protocol-agnostic message processing
@app.post("/api/v1/conversation/message")
async def send_message(request: MessageRequest):
    # Convert REST request to internal message
    internal_message = {
        'source': 'rest_api',
        'user_id': get_user_from_token(),
        'content': request.content,
        'context': request.context
    }
    
    # Publish to conversation engine via message bus
    await message_bus.publish(
        topic="conversation.user_message",
        payload=internal_message
    )
    
    # Wait for AI response
    response = await message_bus.request(
        topic="conversation.response_request",
        payload=internal_message,
        timeout=30.0  # Reasonable conversation response time
    )
    
    return MessageResponse(**response)
```

**Design Benefits**: This architecture allows adding new protocols without changing core AI logic, and enables consistent behavior across different client types.

## Performance Architecture

### Connection Management Strategy

**Protocol-Specific Optimization**: Each protocol is optimized for its specific use patterns in AI companion interactions.

**REST Connection Efficiency**:
- **HTTP/2 Multiplexing**: Multiple API calls share connections (efficient for rapid memory searches)
- **Keep-Alive**: Reduces connection overhead for conversation sessions
- **Connection Pooling**: Reuses connections across different API operations

**WebSocket Persistence**:
- **Single Long-Lived Connection**: Maintains conversational presence without reconnection overhead
- **Heartbeat Optimization**: Minimal bandwidth heartbeats maintain connection health
- **Graceful Degradation**: Automatic reconnection with conversation state preservation

**gRPC Efficiency**:
- **Connection Pooling**: Distributes high-throughput operations across multiple connections
- **Load Balancing**: Distributes AI model requests for optimal resource utilization
- **Stream Reuse**: Long-lived streams for continuous operations like emotion monitoring

### Caching Philosophy

**Relationship-Aware Caching**: Cache duration based on the nature of AI companion data rather than technical considerations.

- **Personality Data**: 1 hour cache (personality changes slowly)
- **Memory Searches**: 5 minutes cache (memories are relatively stable)
- **Emotional State**: No caching (emotions change rapidly and must be current)
- **Conversation Context**: No caching (context is dynamic and session-specific)
- **User Preferences**: 1 day cache (preferences change infrequently)

**Cache Invalidation**: Proactive invalidation when AI learns new information or user makes changes.

### Monitoring Strategy

**User Experience Metrics**: Monitor performance from the perspective of AI companion interaction quality.

- **Conversation Latency**: p95 response time under 2 seconds (natural conversation pace)
- **Emotional Update Frequency**: Real-time emotional state updates within 100ms
- **Memory Search Performance**: Semantic search results within 500ms
- **Connection Stability**: WebSocket uptime > 99.9% (maintains conversational presence)
- **Authentication Success Rate**: > 99% (seamless access to AI companion)

**Relationship Quality Indicators**: Metrics that indicate the health of human-AI relationships.
- **Conversation Continuity**: Successful context maintenance across sessions
- **Proactive Interaction Success**: User engagement with AI-initiated conversations
- **Memory Relevance**: Accuracy of memory retrieval in context

## Summary

AICO's network protocol architecture prioritizes **authentic AI companionship** over technical optimization. Each protocol serves specific aspects of the human-AI relationship:

- **REST API** provides the reliable foundation for relationship management and memory operations
- **WebSocket** enables real-time presence and natural conversation flow
- **gRPC** optimizes performance-critical AI operations without compromising user experience

The **adaptive communication** approach ensures that AICO can provide consistent, engaging interaction across different deployment scenarios while maintaining security and privacy standards appropriate for personal AI companions.

**Key Design Principles Achieved**:
- **Interaction Diversity**: Right protocol for each communication pattern
- **Deployment Flexibility**: Seamless operation in local and distributed modes
- **Progressive Enhancement**: Graceful degradation maintains functionality across different client capabilities
- **Relationship Focus**: All technical decisions serve the goal of authentic AI companionship
