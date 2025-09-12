# Thread Resolution System

## Overview

AICO's thread resolution system provides intelligent, automatic thread management that eliminates manual thread switching while maintaining natural conversation flow. This system integrates the existing ThreadManager service with advanced semantic analysis and behavioral learning capabilities.

> **Note**: This document consolidates and extends the ThreadManager service documentation, providing a comprehensive view of both current implementation and future memory system integration.

## Hybrid Architecture Approach

### Problem & Solution

Traditional separated endpoint architectures (`POST /threads`, `POST /threads/{id}/messages`) force manual thread management, contradicting the principle of seamless, automatic thread switching that users expect from modern AI companions.

AICO implements a hybrid approach that combines automatic thread resolution with explicit thread control:

- **Automatic by Default**: Primary endpoint handles thread resolution transparently
- **Manual Override Available**: Separated endpoints for advanced use cases  
- **Progressive Enhancement**: Clients choose their complexity level
- **Backward Compatible**: Maintains clean separation benefits

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

## ThreadManager Service Implementation

### Current Implementation (Phase 1)

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
        try:
            # Get user's recent threads
            recent_threads = await self.get_user_threads(user_id)
            
            if recent_threads:
                most_recent = recent_threads[0]
                
                # Check if most recent thread is still active
                if self.is_thread_active(most_recent):
                    return ThreadResolution(
                        thread_id=most_recent.id,
                        action="continued",
                        confidence=0.9,
                        reasoning="Recent thread within dormancy threshold"
                    )
            
            # Create new thread
            new_thread = await self.create_thread(user_id, message)
            return ThreadResolution(
                thread_id=new_thread.id,
                action="created",
                confidence=1.0,
                reasoning="No recent active thread found"
            )
            
        except Exception as e:
            # Fallback: always create new thread on errors
            fallback_thread = await self.create_thread(user_id, message)
            return ThreadResolution(
                thread_id=fallback_thread.id,
                action="created",
                confidence=0.5,
                reasoning=f"Fallback due to error: {str(e)}"
            )
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

## Enhanced Resolution Logic (Future Phases)

### Semantic Analysis Integration

```python
class EnhancedThreadManager:
    """Advanced thread manager with semantic understanding"""
    
    def __init__(self):
        self.semantic_analyzer = SemanticAnalyzer()
        self.temporal_analyzer = TemporalAnalyzer()
        self.user_behavior_analyzer = UserBehaviorAnalyzer()
        self.thread_cache = ThreadCache()
        self.decision_engine = ThreadDecisionEngine()

    async def resolve_thread_semantic(
        self, 
        user_id: str, 
        message: str
    ) -> ThreadResolution:
        """Enhanced resolution with semantic analysis"""
        
        # 1. Semantic Analysis
        message_embedding = await self.semantic_analyzer.embed_message(message)
        topic_analysis = await self.semantic_analyzer.analyze_topics(message)
        
        # 2. Get candidate threads
        active_threads = await self.get_active_threads_with_context(user_id)
        dormant_threads = await self.get_dormant_threads_with_embeddings(user_id, limit=5)
        
        # 3. Calculate similarities and scores
        thread_scores = []
        
        for thread in active_threads:
            similarity = await self.calculate_thread_similarity(thread, message_embedding)
            temporal_score = self.calculate_temporal_score(thread)
            behavioral_score = await self.calculate_behavioral_score(thread, user_id)
            
            combined_score = (
                0.5 * similarity +
                0.3 * temporal_score +
                0.2 * behavioral_score
            )
            
            thread_scores.append((thread, combined_score, "continued"))
            
        for thread in dormant_threads:
            similarity = await self.calculate_thread_similarity(thread, message_embedding)
            if similarity > 0.8:  # High threshold for reactivation
                thread_scores.append((thread, similarity, "reactivated"))
        
        # 4. Apply decision logic
        if thread_scores:
            best_thread, best_score, action = max(thread_scores, key=lambda x: x[1])
            
            if best_score > self.get_user_threshold(user_id):
                return ThreadResolution(
                    thread_id=best_thread.id,
                    action=action,
                    confidence=best_score,
                    reasoning=f"Semantic match: {best_score:.3f}"
                )
        
        # Create new thread
        new_thread = await self.create_thread_with_analysis(user_id, message, topic_analysis)
        return ThreadResolution(
            thread_id=new_thread.id,
            action="created",
            confidence=1.0,
            reasoning="No suitable existing thread found"
        )
```

### Decision Matrix

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

## Configuration

### Current Settings (Phase 1)
```yaml
thread_management:
  dormancy_threshold_hours: 2
  max_thread_age_days: 30
  fallback_behavior: "create_new"  # Always create new thread on errors
```

### Future Configuration Options
```yaml
thread_management:
  semantic_similarity:
    continuation_threshold: 0.7
    creation_threshold: 0.4
    embedding_model: "all-MiniLM-L6-v2"
  
  temporal_analysis:
    dormancy_threshold: "2h"
    session_gap_threshold: "30m"
    daily_reset_time: "06:00"
  
  behavioral_learning:
    adaptation_rate: 0.1
    feedback_weight: 0.8
    pattern_history_days: 30
```

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

## Memory System Integration

### Working Memory Integration
The thread resolution system directly interfaces with AICO's working memory layer:

- **Session Context**: Active conversation state maintained in working memory
- **Thread Continuity**: Seamless context transfer between thread decisions
- **Context Assembly**: Relevant context retrieved for thread resolution decisions
- **Real-time Updates**: Working memory updated with thread resolution results

### Episodic Memory Integration
Thread resolution leverages episodic memory for historical context:

- **Conversation History**: Past thread interactions inform resolution decisions
- **Temporal Patterns**: User conversation rhythms stored in episodic memory
- **Thread Relationships**: Parent-child thread relationships tracked
- **Emotional Context**: Emotional metadata influences thread continuation decisions

### Semantic Memory Integration
Advanced thread resolution uses semantic memory for intelligent decisions:

- **Topic Similarity**: Vector embeddings compare message topics with thread content
- **Knowledge Retrieval**: Relevant knowledge base content influences thread decisions
- **Concept Mapping**: Related concepts help determine thread continuation appropriateness
- **Semantic Clustering**: Similar conversations grouped for better thread management

### Procedural Memory Integration
User behavior patterns from procedural memory enhance thread resolution:

- **User Preferences**: Learned conversation patterns influence thread decisions
- **Behavioral Adaptation**: Thread resolution adapts to individual user styles
- **Pattern Recognition**: Recurring conversation patterns inform automatic decisions
- **Feedback Learning**: User corrections improve future thread resolution accuracy

## Testing & Validation

### Test Coverage
- Automatic thread resolution scenarios
- Explicit thread management operations
- Error handling and fallback behavior
- Legacy endpoint compatibility
- Performance under load
- Memory system integration points
- Cross-memory-tier data consistency

### Validation Metrics
- Thread resolution accuracy
- User satisfaction with automatic decisions
- Performance impact on conversation flow
- Error rates and recovery success
- Memory system integration performance
- Context retrieval efficiency

## Migration & Deployment

### Backward Compatibility
- Legacy `/start` endpoint maintained (deprecated)
- Existing separated endpoints preserved
- Gradual client migration path
- Feature flag support for rollout
- Memory system backward compatibility

### Deployment Strategy
1. Deploy minimal ThreadManager with time-based logic (Phase 1) ✅
2. Monitor automatic thread resolution performance
3. Gradually enhance with semantic analysis (Phase 2)
4. Integrate with memory system components (Phase 3)
5. Collect user feedback and iterate
6. Full semantic/behavioral implementation (Phase 4)

### Memory System Migration
- **Phase 1**: Basic thread persistence in episodic memory
- **Phase 2**: Working memory integration for session context
- **Phase 3**: Semantic memory integration for topic analysis
- **Phase 4**: Procedural memory integration for behavioral learning

## Related Documentation

- [Memory System Overview](overview.md) - Core memory architecture and components
- [Memory Architecture](architecture.md) - Detailed four-tier memory system design
- [Context Management](context-management.md) - Context assembly and relevance scoring
- [Implementation Strategy](implementation.md) - Phased implementation approach

This thread resolution system provides the foundation for seamless conversation management while maintaining architectural flexibility for future memory system enhancements.
