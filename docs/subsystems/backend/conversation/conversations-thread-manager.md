# Thread Manager Service Documentation

## Overview

The ThreadManager service provides intelligent, automatic thread management for AICO's conversation system. It eliminates manual thread switching while maintaining natural conversation flow through semantic analysis, temporal context, and user behavior patterns.

## Architecture Problem & Solution

### Problem Identified
Traditional separated endpoint architectures (`POST /threads`, `POST /threads/{id}/messages`) force manual thread management, contradicting the core principle of seamless, automatic thread switching that users expect from modern AI companions.

### Hybrid Architecture Solution
The ThreadManager implements a hybrid approach that combines automatic thread resolution with explicit thread control:

- **Automatic by Default**: Primary endpoint handles thread resolution transparently
- **Manual Override Available**: Separated endpoints for advanced use cases  
- **Progressive Enhancement**: Clients choose their complexity level
- **Backward Compatible**: Maintains clean separation benefits

## Service Implementation

### Current Implementation (Minimal)

The ThreadManager currently uses simple time-based heuristics as a foundation:

```python
class ThreadManager:
    """
    Minimal ThreadManager implementation with simple time-based heuristics.
    
    Current Logic:
    - Continue most recent thread if < 2 hours old
    - Create new thread otherwise
    - Simple dormancy detection
    """
    
    def __init__(self, dormancy_threshold_hours: int = 2):
        self.dormancy_threshold = timedelta(hours=dormancy_threshold_hours)
        self.max_thread_age_days = 30
```

### Core Data Models

```python
@dataclass
class ThreadResolution:
    """Result of thread resolution process"""
    thread_id: str
    action: str  # "continued", "created", "reactivated"
    confidence: float
    reasoning: str
    created_at: Optional[datetime] = None

@dataclass
class ThreadInfo:
    """Basic thread information for resolution"""
    thread_id: str
    last_activity: datetime
    message_count: int
    status: str  # "active", "dormant", "archived"
```

### Thread Resolution Logic

The core resolution method implements the following algorithm:

1. **Get User's Recent Threads**: Query active and dormant threads
2. **Time-Based Analysis**: Check time since last activity
3. **Decision Making**: Continue recent thread or create new one
4. **Fallback Handling**: Create new thread on errors

```python
async def resolve_thread_for_message(
    self, 
    user_id: str, 
    message: str, 
    context: Optional[Dict[str, Any]] = None
) -> ThreadResolution:
    """
    Resolve which thread should handle the incoming message.
    
    Current: Time-based heuristics
    Future: Semantic analysis, user behavior patterns
    """
```

## API Integration

### Primary Endpoint (Automatic Thread Management)

```
POST /api/v1/conversation/messages
```

**Purpose**: Send message with automatic thread resolution  
**Behavior**: ThreadManager automatically continues/creates/reactivates threads  
**User Experience**: Seamless, no thread management required  
**Use Case**: Default for all clients, mobile apps, simple integrations

**Request Schema**:
```python
class UnifiedMessageRequest(BaseModel):
    message: str = Field(..., description="Message content")
    message_type: str = Field("text", description="Message type")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context for thread resolution")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
```

**Response Schema**:
```python
class UnifiedMessageResponse(BaseModel):
    success: bool
    message_id: str
    thread_id: str
    thread_action: str  # "continued", "created", "reactivated"
    thread_reasoning: str
    status: str  # "processing", "queued", "error"
    timestamp: datetime
```

### Advanced Endpoints (Manual Thread Management)

```
POST /api/v1/conversation/threads           # Create specific thread
POST /api/v1/conversation/threads/{id}/messages  # Send to specific thread
GET /api/v1/conversation/threads/{id}       # Get thread metadata
GET /api/v1/conversation/threads            # List threads
```

**Purpose**: Explicit thread control for advanced clients  
**Behavior**: Direct thread operations, bypasses automatic resolution  
**Use Case**: Advanced UIs, debugging, administrative tools

### Legacy Support

```
POST /api/v1/conversation/start  # Deprecated, redirects to /messages
```

## Future Enhancement Architecture

### Planned Components

```python
class ThreadManager:
    def __init__(self):
        self.semantic_analyzer = SemanticAnalyzer()
        self.temporal_analyzer = TemporalAnalyzer()
        self.user_behavior_analyzer = UserBehaviorAnalyzer()
        self.thread_cache = ThreadCache()
        self.decision_engine = ThreadDecisionEngine()
```

### Decision Engine Logic

1. **Semantic Analysis**: Compare incoming message with active thread topics using vector similarity
2. **Temporal Analysis**: Evaluate time gaps and conversation rhythm patterns
3. **Behavioral Analysis**: Consider user-specific conversation preferences and patterns
4. **Context Evaluation**: Assess thread relevance and continuation appropriateness
5. **Decision Synthesis**: Combine all factors to make thread continuation or creation decision

### Thread Decision Matrix

**Continue Existing Thread When**:
- Semantic similarity > 0.7 with recent messages
- Time gap < user's typical conversation pause duration
- Topic relates to ongoing thread discussion
- User explicitly references previous context
- No clear conversation boundary markers detected

**Create New Thread When**:
- Semantic similarity < 0.4 with active thread
- Time gap > dormancy threshold (default: 2 hours)
- Clear topic shift detected (greetings, new subjects)
- User indicates new conversation ("Let's talk about something else")
- Maximum thread length reached (configurable limit)

**Reactivate Dormant Thread When**:
- High semantic similarity with dormant thread content
- User references specific past conversation elements
- Temporal patterns suggest natural conversation resumption
- Explicit thread reference or continuation cues detected

## Implementation Strategy

### Phase 1: Minimal Implementation ✅
- Time-based heuristics (< 2 hours = continue, > 2 hours = new thread)
- Basic thread creation and validation
- API integration with unified `/messages` endpoint
- Fallback error handling

### Phase 2: Semantic Analysis
- Vector embeddings for message content
- Similarity thresholds and topic modeling
- Context window analysis
- Dynamic threshold adjustment

### Phase 3: Temporal Pattern Recognition
- User activity pattern learning
- Session boundary detection
- Dormancy threshold optimization
- Reactivation trigger detection

### Phase 4: User Behavior Integration
- Implicit feedback learning
- Explicit correction handling
- Individual preference profiles
- Adaptive algorithm improvement

## Configuration

### Current Settings
- **Dormancy Threshold**: 2 hours (configurable)
- **Max Thread Age**: 30 days before archival
- **Fallback Behavior**: Always create new thread on errors

### Future Configuration Options
- Semantic similarity thresholds
- User-specific dormancy periods
- Topic modeling parameters
- Behavioral learning rates

## Security & Privacy

### Access Control
- Thread access validation per user
- User isolation (no cross-user thread access)
- Permission-based thread operations

### Privacy Considerations
- Local-first processing where possible
- User data isolation
- Configurable data retention policies
- Transparent thread management decisions

## Testing & Validation

### Test Coverage
- Automatic thread resolution scenarios
- Explicit thread management operations
- Error handling and fallback behavior
- Legacy endpoint compatibility
- Performance under load

### Validation Metrics
- Thread resolution accuracy
- User satisfaction with automatic decisions
- Performance impact on conversation flow
- Error rates and recovery success

## Migration & Deployment

### Backward Compatibility
- Legacy `/start` endpoint maintained (deprecated)
- Existing separated endpoints preserved
- Gradual client migration path
- Feature flag support for rollout

### Deployment Strategy
1. Deploy minimal ThreadManager with time-based logic
2. Monitor automatic thread resolution performance
3. Gradually enhance with semantic analysis
4. Collect user feedback and iterate
5. Full semantic/behavioral implementation

This documentation provides a comprehensive guide to the ThreadManager service, from current minimal implementation to future advanced capabilities, ensuring seamless automatic thread management while maintaining architectural flexibility.
