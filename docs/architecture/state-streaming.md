# AICO State Streaming Architecture

This document defines AICO's real-time state streaming architecture for maintaining full transparency and progressive disclosure of system state to users. The design leverages existing WebSocket infrastructure and proven distributed systems patterns to provide sub-second state updates across all system components.

## Core Principles

1. **Full State Transparency**: Users always know what AICO is doing
2. **Progressive Disclosure**: Information revealed at appropriate detail levels
3. **Real-Time Updates**: Sub-second latency for critical state changes
4. **Minimal Overhead**: Efficient state updates without overwhelming the system
5. **Graceful Degradation**: System remains functional if state streaming fails
6. **Research-Based Design**: Built on proven patterns from distributed systems (Vector Clocks, Pub/Sub filtering, Progress UX best practices)

## Current Implementation Status

### Backend WebSocket Infrastructure ✅

**Location**: `/backend/api_gateway/adapters/websocket_adapter.py`

**Capabilities**:
- ✅ Bidirectional WebSocket communication
- ✅ JWT authentication with session management
- ✅ Topic-based pub/sub subscriptions
- ✅ Heartbeat/keepalive mechanism (30s interval)
- ✅ Connection state management
- ✅ Rate limiting and validation
- ✅ Broadcast to topic subscribers
- ✅ Request/response pattern support
- ✅ Session validation and revocation

**Configuration**:
```yaml
api_gateway:
  protocols:
    websocket:
      enabled: true
      port: 8772
      path: "/ws"
      heartbeat_interval: 30
      max_connections: 1000
```

**Message Types Supported**:
- `auth`: Authentication with JWT token
- `subscribe`: Subscribe to state topics
- `unsubscribe`: Unsubscribe from topics
- `request`: API request via WebSocket
- `heartbeat`: Connection keepalive
- `broadcast`: Server-to-client state updates

### Frontend WebSocket Infrastructure ✅

**Location**: `/frontend/lib/networking/clients/websocket_client.dart`

**Capabilities**:
- ✅ Automatic reconnection with exponential backoff
- ✅ Message queue for offline resilience
- ✅ Optional end-to-end encryption
- ✅ Token-based authentication
- ✅ Connection state management
- ✅ Heartbeat mechanism

**Connection States**: `disconnected`, `connecting`, `connected`, `reconnecting`

### Conversation WebSocket Endpoint ⚠️

**Location**: `/backend/api/conversation/router.py`

**Status**: Partially implemented
- ✅ WebSocket endpoint exists (`/api/v1/conversation/ws`)
- ⚠️ Currently accepts connections without authentication (see TODO in code)
- ⚠️ Basic message bus integration for streaming responses
- ❌ No generalized, structured state streaming service (this document describes the target design)

## State Streaming Architecture

### Hierarchical State Categories (Dot-Notation)

States use hierarchical dot-notation for granular filtering (e.g., `conversation.processing.llm`, `system.resource.model_loading`).

**Complete Category Hierarchy**:

```
conversation (Primary UX - User-facing states)
├── processing
│   ├── message_received          - "Processing your message..."
│   ├── message_analysis          - "Understanding your message..."
│   ├── memory                    - "Recalling relevant context..."
│   ├── context_assembly          - "Preparing response context..."
│   └── llm                       - "Thinking..."
├── completion
│   └── response_ready            - "Response ready"
└── error
    ├── timeout                   - "Response taking longer than expected"
    ├── failure                   - "Unable to generate response"
    └── degraded                  - "Responding with limited context"

system (User-impacting system states)
├── startup
│   ├── initializing              - "Waking up..." (first launch, model loading)
│   └── ready                     - "Ready to chat!"
└── error
    ├── unavailable               - "I'm temporarily unavailable. Please try again in a moment."
    └── degraded                  - "I'm running slower than usual right now."

debug (Verbose/debug detail level only - progressive disclosure)
├── ai_processing
│   ├── entities_extracted           - Entities found: Michael (PERSON), June 28 1972 (DATE), Berlin (LOCATION)
│   ├── sentiment_detected           - Sentiment: Positive (87% confidence) 😊
│   ├── emotions_detected            - Emotions: Curious, Friendly
│   ├── intent_classified            - Intent: Asking about schedule
│   └── topics_identified            - Topics: Work, Meeting, Calendar
└── memory
    ├── facts_learned                - New facts: "User's name is Michael", "Birthday is June 28, 1972"
    ├── context_retrieved            - Retrieved: 3 relevant facts, 2 past conversations
    ├── memory_consolidated          - Consolidated: 5 messages → 2 episodic segments
    └── knowledge_updated            - Updated knowledge: User preferences, mentioned topics
```

**Filtering Examples**:
- `conversation.*` - All conversation states
- `conversation.processing.*` - All processing substates  
- `*.error.*` - All errors across categories
- `system.startup.*` - System startup states
- `debug.memory.*` - All memory debug states
- `debug.*` - All debug states (verbose mode only)

### State Message Structure

**Source of Truth**: All state message structures, enums, and constants are defined in **`/proto/aico_state_streaming.proto`**. This protobuf schema is the single source of truth and generates type-safe code for both backend (Python) and frontend (Dart).

**Design Principles**:
1. **UTC Timestamps**: Always UTC, explicitly labeled
2. **Hybrid Logical Clocks**: Combines physical time + logical counter for distributed ordering
3. **Flat Discriminated Union**: Single `type` field for easy client-side parsing
4. **Type Safety**: Protobuf schema enables compile-time safety in Python and Dart
5. **Progress Safety**: Explicit `-1` for indeterminate progress, never fake percentages

**Protobuf Schema**: `/proto/aico_state_streaming.proto`

**Protobuf Enums** (defined in `/proto/aico_state_streaming.proto`):

The protobuf schema defines enums for state priority, detail level, event severity, lifecycle status, progress type, and update type. These enums are shared between backend and frontend, so both sides interpret priorities and lifecycle transitions consistently.

**Base Message Structure**

Conceptually, every state update carries:

- A protocol `version` and `timestamp_utc` (always UTC).
- A `sequence` (hybrid logical clock fields) for ordering.
- `state_category` and `state_key` for routing and correlation.
- User and conversation context (`user_id`, `conversation_id`, `request_id`).
- A small `ui` section (priority, detail level, optional user message).
- Optional `details` for technical/debug information.

Concrete field names and enum values are defined in the proto file and generated into Python/Dart; this document focuses on the conceptual shape, not the generated types.

### Sequence Ordering (Hybrid Logical Clock)

**Problem**: Multiple backend services emit states independently - simple counter won't work.

**Solution**: Hybrid Logical Clock (HLC) combining physical time + logical counter.

**Ordering Algorithm**:
1. Sort by `sequence.timestamp_ms` (physical time) first
2. If equal, sort by `sequence.counter` (logical counter)
3. If still equal, sort by `sequence.source` (deterministic)

**Benefits**:
- Works across distributed services without coordination
- Deterministic ordering
- Lightweight (no vector clock overhead)
- Causality tracking within same millisecond

## Conversation State Streaming (Priority 1)

### Message Processing Pipeline States

**State Flow**:
```
conversation.processing.message_received → 
  conversation.processing.message_analysis → 
    conversation.processing.memory → 
      conversation.processing.context_assembly → 
        conversation.processing.llm → 
          conversation.completion.response_ready
```

**Concrete State Examples** (conceptual)

Rather than mirroring implementation, this section focuses on the shape of a few representative states.

**Lifecycle example (conversation processing):**

```json
{
  "type": "lifecycle",
  "state_category": "conversation.processing.message_analysis",
  "state_key": "msg_analysis_req123",
  "user_id": "user_456",
  "conversation_id": "conv_789",
  "request_id": "req_123",
  "status": "in_progress",
  "progress_type": "indeterminate",
  "ui": {
    "priority": "normal",
    "detail_level": "normal",
    "user_message": "Understanding your message..."
  },
  "details": {
    "detected_topic": "greeting"
  }
}
```

#### Inner Monologue (Chain-of-Thought) Streaming

To provide transparency into the AI's reasoning process, the system utilizes a **Chain-of-Thought (CoT)** prompting technique. The `hermes3:8b` model is instructed to generate its reasoning process, or "inner monologue," before providing the final answer. This is not a separate data stream from the model but is part of the standard text generation.

**Implementation:**

1.  **Prompt Engineering**: The model is prompted to wrap its step-by-step reasoning within `<thought>...</thought>` tags.
2.  **Backend Parsing**: The `ConversationEngine` parses the streaming output from the model.
3.  **State Emission**:
    *   Content inside the `<thought>` tags is extracted and published as a series of `conversation.processing.llm` state updates. This allows the UI to display the "Thinking..." process in real-time.
    *   Content outside the tags is considered the final response to the user.

**Example Flow**:

1.  **Model Output Stream**: `<thought>The user is asking about my memory. I should first check my semantic memory for facts about the user, then check episodic memory for recent conversations.</thought>Hello! I remember we spoke yesterday about project deadlines.`
2.  **State Stream**: A `state_update` with `state_category: "conversation.processing.llm"` is emitted, with `ui.user_message` containing "The user is asking about my memory...".
3.  **Final Response**: The text "Hello! I remember we spoke yesterday about project deadlines." is delivered as the final message from the AI.

**Event example (error path):**

```json
{
  "type": "event",
  "state_category": "conversation.error.timeout",
  "state_key": "timeout_req123",
  "user_id": "user_456",
  "conversation_id": "conv_789",
  "request_id": "req_123",
  "severity": "warning",
  "message": "Response is taking longer than expected",
  "support_code": "LLM_TIMEOUT_001",
  "ui": {
    "priority": "high",
    "detail_level": "normal",
    "user_message": "I'm taking a bit longer to think about this..."
  }
}
```

Other conversation and system states follow the same pattern: a clear `state_category`, a stable `state_key`, and minimal UI + debug fields.

## System State Streaming (Priority 2)

### Startup States

A similar pattern is used for system startup:

- `system.startup.initializing` lifecycle state while core services and models load.
- `system.startup.ready` event once the system is fully online.

### Error States

System-level error states (e.g. `system.error.unavailable`, `system.error.degraded`) reuse the same event pattern shown above, with different user-facing messages and debug `details`.

## Debug State Streaming (Priority 3)

**Note**: Debug states only emitted when `detail_level: "verbose"` or `"debug"` is requested.

### AI Processing States
```

#### Knowledge Updated (Event - Info)
```json
{
  "state_category": "debug.memory.knowledge_updated",
  "state_key": "knowledge_req123",
  "event": {
    "severity": "info",
    "message": "Knowledge base updated"
  },
  "ui": {
    "priority": "debug",
    "detail_level": "verbose",
    "user_message": "Updated my knowledge: User preferences • Mentioned topics • Conversation patterns"
  },
  "details": {
    "updates": [
      {
        "category": "preferences",
        "updates": ["meeting_time: afternoon", "communication_style: direct"],
        "confidence": 0.87
      },
      {
        "category": "topics",
        "new_topics": ["museum_visit", "weekend_plans"],
        "topic_frequency_updated": {"work": 15, "personal": 8}
      },
      {
        "category": "patterns",
        "patterns_detected": ["asks_about_schedule_on_mondays", "mentions_cat_frequently"],
        "pattern_confidence": 0.73
      }
    ],
    "update_time_ms": 189
  }
}
```

## WebSocket Topic Structure

### Topic Hierarchy

States are published to hierarchical topics matching the state category structure:

```
state/
├── user/{user_id}/
│   ├── conversation/{conversation_id}/
│   │   ├── processing/*          - All processing states
│   │   ├── completion/*          - Completion states
│   │   └── error/*               - Conversation errors
│   └── system/
│       ├── resource/*            - Resource states affecting this user
│       └── service/*             - Service states affecting this user
├── system/
│   ├── resource/*                - System-wide resource states
│   └── service/*                 - System-wide service states
└── debug/
    ├── ai_processing/*           - AI processing debug states
    └── memory/*                  - Memory system debug states
```

### Subscription Patterns

**User subscribes to their conversation states**:
```json
{"type": "subscribe", "topic": "state/user/{user_id}/conversation/{conversation_id}/#"}
```

**User subscribes to system states affecting them**:
```json
{"type": "subscribe", "topic": "state/user/{user_id}/system/#"}
```

**Developer subscribes to debug states for a conversation**:
```json
{"type": "subscribe", "topic": "state/debug/#"}
```

**Wildcard filtering examples**:
- `state/user/user_456/conversation/conv_789/processing/*` - All processing states for a conversation
- `state/user/user_456/conversation/*/error/*` - All errors across all user's conversations
- `state/system/resource/*` - All system resource states
- `state/debug/memory/*` - All memory debug states

## Protobuf Code Generation

**Prerequisites**: Install protobuf compiler and language plugins

```bash
# Install protoc compiler
brew install protobuf  # macOS
apt-get install protobuf-compiler  # Linux

# Install Python plugin
pip install grpcio-tools

# Install Dart plugin
dart pub global activate protoc_plugin
```

**Generate Python Code**:
```bash
cd /Users/mbo/Documents/dev/aico
python -m grpc_tools.protoc \
  -I./proto \
  --python_out=./backend/generated \
  --pyi_out=./backend/generated \
  proto/aico_state_streaming.proto
```

**Generate Dart Code**:
```bash
cd /Users/mbo/Documents/dev/aico
protoc \
  -I./proto \
  --dart_out=./frontend/lib/generated \
  proto/aico_state_streaming.proto
```

**Import Generated Code**:

```python
# Backend Python
from backend.generated.aico_state_streaming_pb2 import (
    StateUpdate,
    LifecycleStateUpdate,
    EventStateUpdate,
    StatePriority,
    LifecycleStatus,
    ProgressType,
)
```

```dart
// Frontend Dart
import 'package:aico/generated/aico_state_streaming.pb.dart';
```

## Implementation Plan

### Phase 0: Protobuf Setup (Week 1)

**Tasks**:
1. ✅ Create `/proto/aico_state_streaming.proto` schema
2. Generate Python protobuf code for backend
3. Generate Dart protobuf code for frontend
4. Update build scripts to auto-generate on proto changes
5. Create type adapters for JSON ↔ Protobuf conversion (WebSocket transport)

### Phase 1: Conversation State Streaming (Week 1-2)

**Backend**:
1. Create `StateStreamingService` in `/backend/services/state_streaming.py`
2. Integrate with `ConversationEngine` to emit state updates using protobuf types
3. Add state publishing to message bus
4. Create state aggregation and filtering logic
5. Add JSON serialization for WebSocket transport

**Frontend**:
1. Create `StateStreamingProvider` in Riverpod using generated Dart protobuf classes
2. Add state subscription management
3. Create UI components for state display
4. Implement progressive disclosure logic
5. Add JSON deserialization to protobuf objects

**Priority States**:
- Message processing pipeline
- LLM generation progress
- Memory retrieval status
- Error/timeout states

### Phase 2: AI Component States (Week 3)

**Backend**:
1. Add state emission to memory system
2. Add state emission to entity extraction
3. Add state emission to sentiment analysis
4. Implement state buffering and throttling

**Frontend**:
1. Create detailed state visualization
2. Add developer mode with verbose states
3. Implement state history/timeline view

### Phase 3: System State Streaming (Week 4)

**Backend**:
1. Add service health state emission
2. Add resource monitoring state emission
3. Add model loading state emission
4. Implement system-wide state aggregation

**Frontend**:
1. Create system status dashboard
2. Add resource usage visualization
3. Implement alert/notification system

### Phase 4: Optimization & Polish (Week 5)

1. Implement state throttling and batching
2. Add state compression for high-frequency updates
3. Optimize WebSocket bandwidth usage
4. Add state persistence for offline resilience
5. Performance testing and tuning

## State Emission Patterns

### Backend Implementation

**StateStreamingService** (`/backend/services/state_streaming.py`):

**Core Responsibilities**:
- Emit state updates to WebSocket subscribers via message bus
- Maintain Hybrid Logical Clock (timestamp_ms + counter) per service
- Cache recent states for new subscribers
- Build hierarchical topics from state categories
- Convert StateUpdate to JSON for WebSocket transmission

**Key Methods**:
- `emit_state(state: StateUpdate)` - Publish state to appropriate topic
- `_build_topic(state: StateUpdate) -> str` - Convert state_category to WebSocket topic
- `_increment_sequence()` - Increment HLC counter for ordering

**Topic Routing Logic**:
- `conversation.*` → `state/user/{user_id}/conversation/{conversation_id}/*`
- `system.*` → `state/system/*` (broadcast to all users)
- `debug.*` → `state/debug/*` (only if verbose/debug mode enabled)

**State Caching**:
- Cache last 100 states per user for reconnection recovery
- TTL: 5 minutes
- Indexed by `{user_id}:{state_key}`

### Frontend Implementation

**StateStreamingProvider** (Riverpod - `/frontend/lib/core/providers/state_streaming_provider.dart`):

**State Management**:
- Maintains `Map<String, StateUpdate>` indexed by `state_key`
- Automatically sorts by `sequence.timestamp_ms` then `sequence.counter`
- Filters states by `state_category` pattern matching
- Auto-cleanup completed states after 30 seconds

**Key Methods**:
- `updateState(StateUpdate update)` - Add/update state
- `getState(String stateKey)` - Get specific state
- `getConversationStates(String conversationId)` - Get all states for conversation
- `filterByCategory(String pattern)` - Filter by dot-notation pattern (e.g., `"conversation.processing.*"`)
- `clearCompletedStates()` - Remove completed/failed states

**Progress Handling**:
```dart
Widget buildProgressIndicator(StateUpdate state) {
  // Type-safe pattern matching with discriminated union
  if (state.type == 'lifecycle') {
    if (state.progressType == 'determinate' && state.progress != null) {
      // Show determinate progress bar
      return LinearProgressIndicator(value: state.progress! / 100);
    } else if (state.progressType == 'stepped') {
      // Show step indicator (e.g., "3/5")
      return Text('${state.stepCurrent}/${state.stepTotal}');
    } else {
      // Show indeterminate spinner
      return CircularProgressIndicator();
    }
  }
  return SizedBox.shrink();
}
```

### UI/UX Integration

**Conversation Screen**:
- **Typing Indicator**: Shows current `conversation.processing.*` state with appropriate progress indicator
- **User Messages**: Display `ui.user_message` for user-friendly text
- **Technical Details**: Show `details` object when user taps "More info" or in developer mode
- **Support Codes**: Display `event.support_code` for error states with "Copy" button
- **Auto-hide**: Completed states fade out after 2 seconds

**System Status Banner**:
- Show `system.service.*` and `system.resource.*` states with `priority: "high"` or `"critical"`
- Persistent banner until state resolves
- Tap to view technical details and support code
- Color coding: Critical (red), Warning (orange), Info (blue)

**Developer Mode** (Settings toggle):
- **State Timeline**: Scrollable list of all states with timestamps
- **Category Filtering**: Filter by state_category pattern
- **Technical View**: Show full JSON for each state
- **Performance Metrics**: Show `processing_time_ms` from details
- **Sequence Visualization**: Timeline graph showing state transitions

### Debug Mode UX - Visual Examples

**AI Processing Panel** (Progressive disclosure):
```
┌─────────────────────────────────────────────────────────┐
│ 🧠 AI Analysis                                    [×]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 👤 Entities Found:                                      │
│   • Michael (person) ████████████░ 95%                  │
│   • June 28, 1972 (date) ███████████░ 92%               │
│   • Berlin (location) ██████████░ 89%                   │
│                                                         │
│ 😊 Sentiment: Positive (87% confident)                  │
│   ★★★★☆ 4.2/5 stars                                    │
│                                                         │
│ 💭 Emotions Detected:                                   │
│   • Curious (primary) ████████░ 82%                     │
│   • Friendly ███████░ 76%                               │
│   • Excited ██████░ 68%                                 │
│                                                         │
│ 🎯 Intent: Asking about schedule                        │
│   Category: Information seeking                         │
│                                                         │
│ 📌 Topics:                                              │
│   • Work (primary) ████████░ 88%                        │
│   • Meeting ███████░ 75%                                │
│   • Calendar ██████░ 69%                                │
│                                                         │
│ ⏱️ Processing: 234ms                                    │
└─────────────────────────────────────────────────────────┘
```

**Memory Panel** (Progressive disclosure):
```
┌─────────────────────────────────────────────────────────┐
│ 🧠 Memory Activity                                [×]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ✨ I Learned:                                           │
│   • Your name is Michael ████████████░ 95%              │
│   • Your birthday is June 28, 1972 ███████████░ 92%     │
│   • You live in Berlin ██████████░ 89%                  │
│                                                         │
│ 💡 I Remembered:                                        │
│                                                         │
│   📊 3 facts about you:                                 │
│   • You prefer morning meetings (7 days ago)            │
│   • You work in software development (14 days ago)      │
│   • Your cat is named Whiskers (3 days ago)             │
│                                                         │
│   💬 2 past conversations:                              │
│   • Discussion about project deadline                   │
│     Oct 1, 2:30 PM • 8 messages • 81% relevant          │
│   • Planning team meeting                               │
│     Sep 30, 10:15 AM • 5 messages • 74% relevant        │
│                                                         │
│ 📦 Organized:                                           │
│   5 messages → 2 conversation segments                  │
│   Extracted 3 new facts                                 │
│                                                         │
│ 🔄 Updated Knowledge:                                   │
│   • Preferences: afternoon meetings, direct style       │
│   • New topics: museum visit, weekend plans             │
│   • Patterns: asks about schedule on Mondays            │
│                                                         │
│ ⏱️ Total: 568ms                                         │
└─────────────────────────────────────────────────────────┘
```

**Conversation Flow Visualization**:
```
┌─────────────────────────────────────────────────────────┐
│ 🔍 Processing Timeline                            [×]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ✓ Message received                          0ms        │
│ ✓ Analyzing message                        45ms        │
│ ✓ Entities extracted                      234ms        │
│   └─ Michael, June 28 1972, Berlin                     │
│ ✓ Sentiment detected                      156ms        │
│   └─ Positive 😊 (87%)                                 │
│ ✓ Recalling context                       234ms        │
│   └─ 3 facts, 2 conversations                          │
│ ✓ Thinking...                            2340ms        │
│   └─ hermes3:8b • 450 tokens                           │
│ ✓ Response ready                         2800ms        │
│                                                         │
│ Total processing time: 2.8 seconds                      │
└─────────────────────────────────────────────────────────┘
```

**Key UX Principles**:
1. **Progressive Disclosure**: Collapsed by default, expand on tap
2. **Visual Confidence**: Progress bars for confidence scores
3. **Emoji Icons**: Quick visual recognition of categories
4. **Bullet Points**: Scannable, not walls of text
5. **Timing Info**: Shows performance, builds trust
6. **Real Content**: Actual extracted data, not just "processing..."
7. **Relevance Scores**: Shows why AICO retrieved specific memories
8. **Temporal Context**: "7 days ago" helps user understand memory freshness

## Performance Considerations

### State Throttling

**High-Frequency States** (e.g., progress updates):
- Throttle to max 10 updates/second
- Batch multiple updates if possible
- Use progress percentage instead of absolute values

**Low-Priority States**:
- Batch updates every 500ms
- Only send if state actually changed
- Compress details for verbose states

### Bandwidth Optimization

**State Compression**:
- Use short field names in JSON
- Omit null/empty fields
- Delta updates for repeated states
- Binary encoding for debug mode

**Selective Subscription**:
- Users only subscribe to their own states
- Detail level filtering server-side
- Unsubscribe from completed conversations

## Error Handling

### State Streaming Failures

**If WebSocket disconnects**:
1. Frontend maintains last known state
2. Show "Reconnecting..." indicator
3. Request state snapshot on reconnection
4. Resume normal state streaming

**If state update fails**:
1. Log error but don't block processing
2. Retry critical state updates
3. Fall back to polling for system states
4. Notify user if persistent failure

### Timeout Handling

**State-Based Timeouts**: Emit warning states when operations exceed expected time (e.g., `llm_timeout_warning` with expected vs elapsed time, still_processing flag, priority: high)

## Security Considerations

1. **Authentication**: All WebSocket connections require JWT authentication
2. **Authorization**: Users can only subscribe to their own state topics
3. **Data Filtering**: Sensitive details filtered based on user role
4. **Rate Limiting**: Prevent state subscription abuse
5. **Encryption**: Optional E2E encryption for state updates

## Monitoring & Metrics

### State Streaming Metrics

- State update latency (target: <100ms)
- WebSocket connection stability
- State update delivery rate
- Bandwidth usage per user
- State cache hit rate

### Alerting

- State streaming service down
- High state update latency (>500ms)
- WebSocket connection failures
- State update backlog growing

## Future Enhancements

1. **State Persistence**: Store state history for debugging
2. **State Replay**: Replay state transitions for issue diagnosis
3. **Predictive States**: Estimate completion times using ML
4. **Adaptive Detail**: Auto-adjust detail level based on user behavior
5. **State Aggregation**: Combine related states for cleaner UX
6. **Multi-Device Sync**: Sync state across user's devices

## Support Code Reference

**Format**: `{COMPONENT}_{TYPE}_{NUMBER}`

**Conversation Errors**:
- `LLM_TIMEOUT_001` - LLM generation timeout
- `LLM_FAIL_002` - LLM generation failed
- `MEM_DEGRADED_003` - Memory system degraded

**System Errors**:
- `SVC_UNAVAIL_001` - Service unavailable
- `SVC_DEGRADED_002` - Service degraded performance
- `MODEL_LOAD_003` - Model loading failed

**Usage**: Users report support code, support/admins can filter logs and states by code for quick diagnosis.

## Summary

### Key Design Decisions

1. **Protobuf Schema as Source of Truth**: `/proto/aico_state_streaming.proto` defines all structures and enums, ensuring consistency across backend (Python) and frontend (Dart)
2. **UTC Timestamps**: All timestamps are UTC with explicit `_utc` suffix to avoid timezone confusion
3. **Hybrid Logical Clocks**: Solves distributed ordering without coordination overhead
4. **Hierarchical Dot-Notation**: Enables granular filtering (`conversation.processing.llm`, `*.error.*`)
5. **Flat Discriminated Union**: Single `type` field enables type-safe client parsing with switch statements
6. **Three State Types**: Lifecycle (stateful), Event (one-time), Snapshot (current values) - discriminated by `type` field
7. **Progress Safety**: Explicit `-1` for indeterminate progress, never fake percentages
8. **Dual-Layer Messages**: User-friendly `ui.user_message` + technical `details` for support
9. **Support Codes**: Short codes for easy user reporting and log filtering

### Research-Based Foundations

- **Vector Clocks**: Adapted Hybrid Logical Clock approach from distributed systems research
- **Pub/Sub Filtering**: Hierarchical topic-based + content-based filtering (Wikipedia Pub/Sub pattern)
- **Progress UX**: Never fake progress, use indeterminate indicators when unknown (Nielsen Norman Group)
- **State Machines**: Proper lifecycle states (idle → starting → in_progress → completed/failed)

### Implementation Priorities

**Priority 1** (Week 1-2): Conversation states - critical for user experience
**Priority 2** (Week 3-4): System states - user-impacting resource/service states  
**Priority 3** (Week 5): Debug states - verbose/debug mode for developers

### Benefits

**For Users**:
- Always know what AICO is doing ("Thinking...", "Recalling context...")
- Clear error messages with support codes for reporting issues
- Realistic progress indicators (no fake percentages)
- Graceful degradation messaging ("Responding with limited context")

**For Support/Admins**:
- Support codes for quick issue identification
- Technical details in `details` object for debugging
- Component identification for targeted fixes
- Performance metrics for optimization

**For Developers**:
- Debug mode with full state timeline
- Category filtering for focused debugging
- Sequence visualization for understanding flow
- Performance metrics in state details

This state streaming architecture provides AICO with comprehensive real-time transparency while maintaining performance and user experience. The design leverages existing WebSocket infrastructure, follows proven distributed systems patterns, and provides a solid foundation for future enhancements in autonomous agency and proactive engagement.
