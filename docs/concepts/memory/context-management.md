# Context Management & Thread Resolution

## Overview

AICO's context management system provides intelligent, automatic thread resolution that eliminates manual thread switching while maintaining natural conversation flow. The system uses semantic analysis, temporal patterns, and behavioral learning to seamlessly manage conversation continuity.

## Context Assembly System

### Context Types

The system manages six primary context types that inform conversation decisions:

1. **Thread Context**: Current conversation state and history
2. **User Context**: Individual relationship and communication preferences  
3. **Emotional Context**: Current emotional state and mood progression
4. **Personality Context**: Active personality traits and behavioral parameters
5. **Memory Context**: Relevant episodic and semantic memories
6. **Environmental Context**: Time, device, and situational factors

### Context Router & Memory Manager

```python
class ContextRouter:
    """Central coordination for context assembly and memory retrieval"""
    
    def __init__(self, memory_manager: AICOMemoryManager):
        self.memory_manager = memory_manager
        self.relevance_scorer = RelevanceScorer()
        self.context_optimizer = ContextOptimizer()
        
    async def assemble_context(self, user_id: str, message: str) -> ConversationContext:
        """Coordinate context retrieval across all memory tiers"""
        
        # 1. Analyze incoming message
        message_analysis = await self.analyze_message(message)
        
        # 2. Retrieve context from each tier
        working_ctx = await self.memory_manager.working_memory.get_context(user_id)
        episodic_ctx = await self.retrieve_episodic_context(user_id, message_analysis)
        semantic_ctx = await self.retrieve_semantic_context(user_id, message_analysis)
        procedural_ctx = await self.retrieve_procedural_context(user_id)
        
        # 3. Score and filter for relevance
        relevant_context = self.relevance_scorer.score_and_filter(
            working_ctx, episodic_ctx, semantic_ctx, procedural_ctx,
            current_message=message_analysis
        )
        
        # 4. Optimize for token usage
        optimized_context = self.context_optimizer.optimize_for_tokens(
            relevant_context, max_tokens=4000
        )
        
        return optimized_context
```

### Relevance Scoring Algorithm

**Multi-Factor Scoring**:
- **Recency Weight**: Recent memories weighted higher (exponential decay)
- **Semantic Similarity**: Vector cosine similarity with current message
- **Emotional Relevance**: Match between emotional contexts
- **User Importance**: Learned importance based on user behavior patterns
- **Topic Coherence**: Alignment with current conversation topic

```python
class RelevanceScorer:
    def calculate_relevance(self, memory_item: MemoryItem, current_context: MessageAnalysis) -> float:
        # Recency score (0.0 to 1.0)
        recency_score = self.calculate_recency_score(memory_item.timestamp)
        
        # Semantic similarity (0.0 to 1.0)
        semantic_score = cosine_similarity(
            memory_item.embedding, 
            current_context.embedding
        )
        
        # Emotional alignment (0.0 to 1.0)
        emotional_score = self.calculate_emotional_similarity(
            memory_item.emotional_context,
            current_context.emotional_state
        )
        
        # User importance (learned weight)
        importance_weight = memory_item.user_importance_score
        
        # Weighted combination
        relevance = (
            0.3 * recency_score +
            0.4 * semantic_score +
            0.2 * emotional_score +
            0.1 * importance_weight
        )
        
        return min(relevance, 1.0)
```

## Thread Resolution Engine

### Decision Matrix

The thread resolution system uses a sophisticated decision matrix that combines multiple factors:

**Continue Existing Thread When**:
- Semantic similarity > 0.7 with recent messages
- Time gap < user's learned conversation pause duration  
- Topic coherence maintained (topic modeling score > 0.6)
- User explicitly references previous context
- Emotional continuity detected (mood alignment)
- No clear conversation boundary markers

**Create New Thread When**:
- Semantic similarity < 0.4 with active thread
- Time gap > adaptive dormancy threshold
- Clear topic boundary detected (greeting patterns, "let's talk about...")
- User intent classification shows major shift
- Maximum thread complexity reached (configurable limit)
- Explicit new conversation indicators

**Reactivate Dormant Thread When**:
- High semantic similarity (> 0.8) with dormant thread content
- User references specific past conversation elements
- Temporal patterns suggest natural conversation resumption
- Cross-thread relationship detected (related topics)

### Thread Resolution Algorithm

```python
class ThreadResolver:
    def __init__(self, config: ThreadConfig):
        self.semantic_analyzer = SemanticAnalyzer()
        self.temporal_analyzer = TemporalAnalyzer()
        self.behavioral_analyzer = BehavioralAnalyzer()
        self.decision_engine = ThreadDecisionEngine()
        
    async def resolve_thread(self, user_id: str, message: str) -> ThreadResolution:
        """Determine optimal thread for incoming message"""
        
        # 1. Analyze message characteristics
        message_analysis = await self.semantic_analyzer.analyze(message)
        
        # 2. Get candidate threads
        active_threads = await self.get_active_threads(user_id)
        dormant_threads = await self.get_dormant_threads(user_id, limit=10)
        
        # 3. Score each candidate
        thread_scores = []
        
        for thread in active_threads:
            score = await self.score_thread_match(thread, message_analysis)
            thread_scores.append((thread, score, "continue"))
            
        for thread in dormant_threads:
            score = await self.score_dormant_match(thread, message_analysis)
            if score > 0.6:  # Only consider high-confidence dormant matches
                thread_scores.append((thread, score, "reactivate"))
        
        # 4. Apply decision logic
        best_match = max(thread_scores, key=lambda x: x[1]) if thread_scores else None
        
        if best_match and best_match[1] > self.config.continuation_threshold:
            return ThreadResolution(
                thread_id=best_match[0].id,
                action=best_match[2],
                confidence=best_match[1],
                reasoning=f"High similarity match: {best_match[1]:.3f}"
            )
        else:
            # Create new thread
            new_thread = await self.create_new_thread(user_id, message_analysis)
            return ThreadResolution(
                thread_id=new_thread.id,
                action="created",
                confidence=1.0,
                reasoning="No suitable existing thread found"
            )
```

### Semantic Analysis Components

**Vector Similarity Matching**:
- Generate embeddings using sentence transformers (`all-MiniLM-L6-v2`)
- Calculate cosine similarity with thread context
- Apply dynamic thresholds based on conversation patterns

**Topic Modeling**:
- Extract conversation topics using BERTopic or LDA
- Track topic evolution within threads
- Detect topic coherence and natural boundaries

**Intent Classification**:
- Classify user intent (question, statement, request, greeting)
- Detect conversation control signals ("let's change topics")
- Identify thread management cues

## Behavioral Learning System

### User Pattern Recognition

```python
class BehavioralAnalyzer:
    def learn_user_patterns(self, user_id: str) -> UserConversationProfile:
        """Build user-specific conversation preferences"""
        
        # Analyze historical thread transitions
        transitions = self.analyze_thread_transitions(user_id)
        
        # Calculate user-specific thresholds
        dormancy_threshold = self.calculate_dormancy_preference(transitions)
        topic_sensitivity = self.calculate_topic_switching_tolerance(transitions)
        
        # Learn timing patterns
        conversation_rhythms = self.analyze_conversation_timing(user_id)
        
        return UserConversationProfile(
            user_id=user_id,
            dormancy_threshold=dormancy_threshold,
            topic_sensitivity=topic_sensitivity,
            conversation_rhythms=conversation_rhythms,
            thread_switching_tolerance=self.calculate_switching_tolerance(transitions)
        )
```

### Adaptive Thresholds

The system continuously adapts decision thresholds based on user behavior:

- **Similarity Thresholds**: Adjust based on user correction patterns
- **Dormancy Periods**: Learn individual conversation rhythm preferences  
- **Topic Sensitivity**: Adapt to user comfort with topic jumping
- **Context Depth**: Optimize context window size for user preferences

### Feedback Integration

**Implicit Feedback**:
- Monitor conversation flow smoothness
- Track user satisfaction indicators (conversation length, engagement)
- Learn from natural conversation patterns

**Explicit Feedback** (future enhancement):
- Allow users to correct thread decisions
- Provide thread management preferences interface
- Learn from manual thread switching patterns

## Context Optimization

### Token Management

```python
class ContextOptimizer:
    def optimize_for_tokens(self, context: ConversationContext, max_tokens: int) -> ConversationContext:
        """Optimize context to fit within token limits while preserving relevance"""
        
        # 1. Calculate current token usage
        current_tokens = self.calculate_token_count(context)
        
        if current_tokens <= max_tokens:
            return context
            
        # 2. Apply compression strategies
        compressed_context = context.copy()
        
        # Summarize older episodic memories
        if current_tokens > max_tokens:
            compressed_context.episodic_memories = self.summarize_episodes(
                context.episodic_memories, target_reduction=0.3
            )
            
        # Reduce semantic facts to most relevant
        if self.calculate_token_count(compressed_context) > max_tokens:
            compressed_context.semantic_facts = self.filter_top_facts(
                context.semantic_facts, max_facts=20
            )
            
        # Truncate working memory if necessary
        if self.calculate_token_count(compressed_context) > max_tokens:
            compressed_context.working_memory = self.truncate_working_memory(
                context.working_memory, max_tokens - self.calculate_base_tokens(compressed_context)
            )
            
        return compressed_context
```

### Compression Strategies

**Episodic Memory Compression**:
- Summarize older conversation segments
- Preserve key emotional moments and relationship milestones
- Maintain conversation flow markers

**Semantic Memory Filtering**:
- Prioritize facts by relevance score and recency
- Remove redundant or contradictory information
- Preserve core user preferences and relationship context

**Working Memory Optimization**:
- Use sliding window for recent messages
- Preserve conversation objectives and emotional state
- Maintain thread coherence markers

This context management system enables AICO to maintain sophisticated conversation awareness while operating efficiently on local hardware, providing the foundation for natural, relationship-aware interactions.
