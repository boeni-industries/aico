# AICO Memory System V2 Refactor

**Status**: Work In Progress  
**Target**: Replace 4-tier memory system with intelligent 2-tier fact-centric architecture  
**Goal**: Best-in-class conversational AI memory surpassing current market solutions

## Core Principles & Rules

### Development Guidelines
1. **Follow AICO Guidelines**: Strict adherence to `docs/guides/developer/guidelines.md`
2. **No Legacy Retention**: Clean deletion of obsolete code - no backwards compatibility
3. **Fail Loudly**: No silent failures - raise meaningful errors with full context
4. **No Silent Fallbacks**: No degraded functionality - full capability or explicit failure
5. **Root Cause Fixes Only**: No patches or workarounds - solve underlying problems completely
6. **Multilingual First**: All text processing must support 100+ languages via modelservice
7. **Privacy First**: All processing local via Ollama/ChromaDB - no external APIs
8. **Intelligent Simplicity**: Simple architecture with sophisticated algorithms

## Architecture Overview

### Current State (4-Tier - TO BE REMOVED)
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Working   │  │  Episodic   │  │  Semantic   │  │ Procedural  │
│   Memory    │  │   Memory    │  │   Memory    │  │   Memory    │
│   (LMDB)    │  │  (libSQL)   │  │ (ChromaDB)  │  │  (libSQL)   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

### Target State (2-Tier Fact-Centric)
```
┌─────────────────┐    ┌──────────────────────────┐
│  Session Memory │    │    Knowledge Memory      │
│     (LMDB)      │    │  (ChromaDB + libSQL)     │
│                 │    │                          │
│ • Recent msgs   │    │ • Identity facts         │
│ • Active context│    │ • Preference facts       │
│ • conversation_ │    │ • Relationship facts     │
│   id scoping    │    │ • Temporal facts         │
│ • Sub-ms access │    │ • Semantic search        │
└─────────────────┘    └──────────────────────────┘
```

## Fact-Centric Memory Model

### Fact Definition
```python
@dataclass
class Fact:
    # Core content
    fact_id: str                    # UUID
    content: str                    # "User's name is Sarah"
    fact_type: FactType            # IDENTITY, PREFERENCE, RELATIONSHIP, TEMPORAL
    confidence: float              # 0.0-1.0 (LLM-determined)
    
    # Classification (LLM-determined)
    is_immutable: bool             # True for identity facts
    category: str                  # LLM-classified category
    
    # Temporal validity
    valid_from: datetime
    valid_until: Optional[datetime] = None
    
    # Multilingual entities (via GLiNER)
    entities: List[ExtractedEntity]  # Multilingual NER entities
    
    # Provenance
    user_id: str
    source_conversation_id: str
    extraction_method: str         # "llm_synthesis", "ner_enhanced"
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

### Fact Types & Immutability Rules
```python
class FactType(Enum):
    IDENTITY = "identity"          # Name, birthdate - IMMUTABLE when confidence > 0.9
    PREFERENCE = "preference"      # Food, music - MUTABLE, versioned
    RELATIONSHIP = "relationship"  # Family, friends - SEMI-IMMUTABLE
    TEMPORAL = "temporal"         # Events, experiences - IMMUTABLE
    DEMOGRAPHIC = "demographic"   # Age, location - SEMI-MUTABLE
```

## Implementation Strategy

### Phase 1: Core Infrastructure (Week 1)
1. **Remove Obsolete Code**
   - Delete `SemanticRequestQueue` and circuit breaker complexity
   - Remove episodic and procedural memory stores
   - Clean up memory consolidation logic
   - Delete conversation segment processing

2. **Implement Fact Extraction Pipeline**
   ```python
   class FactExtractionPipeline:
       async def extract_facts(self, message: str, user_id: str, conversation_id: str) -> List[Fact]:
           # 1. Multilingual NER via GLiNER (modelservice)
           entities = await self.modelservice.extract_entities(message)
           
           # 2. LLM fact synthesis (Hermes3 via Ollama)
           facts = await self.modelservice.synthesize_facts(message, entities)
           
           # 3. Confidence scoring and classification
           validated_facts = []
           for fact in facts:
               confidence = await self.validate_fact_confidence(fact, entities)
               if confidence >= 0.7:  # Minimum threshold
                   fact.confidence = confidence
                   fact.is_immutable = self.determine_immutability(fact)
                   validated_facts.append(fact)
           
           return validated_facts
   ```

3. **Implement Fact Storage System**
   ```python
   class FactStorage:
       async def store_fact(self, fact: Fact) -> bool:
           # 1. Check for conflicts
           similar_facts = await self.find_similar_facts(fact)
           
           # 2. LLM conflict resolution (ADD/UPDATE/DELETE/NOOP)
           operation = await self.resolve_conflicts(fact, similar_facts)
           
           # 3. Execute operation
           if operation.type == "ADD":
               await self.add_fact(fact)
           elif operation.type == "UPDATE":
               await self.update_fact(operation.target_fact, fact)
           elif operation.type == "DELETE":
               await self.delete_fact(operation.target_fact)
           # NOOP = no action needed
           
           return operation.type != "NOOP"
   ```

### Phase 2: Advanced Features (Week 2)
1. **Context Assembly Intelligence**
   ```python
   class ContextAssembler:
       async def assemble_context(self, user_id: str, current_message: str, conversation_id: str) -> Dict:
           # 1. Recent session context (LMDB - ultra-fast)
           session_context = await self.session_store.get_recent_messages(
               user_id, conversation_id, limit=10
           )
           
           # 2. Relevant facts (ChromaDB semantic search)
           relevant_facts = await self.knowledge_store.semantic_search(
               query=current_message,
               user_id=user_id,
               limit=20,
               confidence_threshold=0.7
           )
           
           # 3. Context switch detection (intent + semantic analysis)
           context_switch = await self.detect_context_switch(current_message, session_context)
           if context_switch:
               # Load additional context for new topic
               topic_facts = await self.get_topic_facts(context_switch.new_topic, user_id)
               relevant_facts.extend(topic_facts)
           
           # 4. Optimize context (token management)
           return self.optimize_context(session_context, relevant_facts)
   ```

2. **Multilingual Fact Validation**
   ```python
   class MultilingualFactValidator:
       async def validate_fact_confidence(self, fact: Fact, entities: List[ExtractedEntity]) -> float:
           # NO PATTERN MATCHING - Use LLM for multilingual validation
           validation_prompt = f"""
           Analyze this fact for accuracy and confidence:
           Fact: "{fact.content}"
           Entities: {[e.text for e in entities]}
           Type: {fact.fact_type}
           
           Consider:
           1. Entity validation (are entities correctly identified?)
           2. Fact coherence (does the fact make logical sense?)
           3. Source reliability (direct statement vs inferred)
           4. Linguistic certainty (definitive vs uncertain language)
           
           Return confidence score 0.0-1.0 with reasoning.
           """
           
           result = await self.modelservice.get_completions(validation_prompt)
           return self.parse_confidence_score(result)
   ```

### Phase 3: Integration & Testing (Week 3)
1. **Memory Manager Refactor**
   ```python
   class MemoryManagerV2(BaseAIProcessor):
       async def process(self, context: ProcessingContext) -> ProcessingResult:
           # 1. Store message in session memory (immediate, non-blocking)
           await self.session_store.store_message(
               context.user_id, context.conversation_id, context.message_content
           )
           
           # 2. Extract and store facts (background, non-blocking)
           asyncio.create_task(self.extract_and_store_facts(context))
           
           # 3. Assemble context for response (immediate)
           memory_context = await self.context_assembler.assemble_context(
               context.user_id, context.message_content, context.conversation_id
           )
           
           # 4. Update processing context
           context.shared_state["memory_context"] = memory_context
           
           return ProcessingResult(
               component=self.component_name,
               operation="memory_processing",
               success=True,
               result_data=memory_context
           )
   ```

## Database Schema Changes

### libSQL Schema V5 (New Tables)
```sql
-- Facts metadata with full multilingual support
CREATE TABLE facts_metadata (
    fact_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    category TEXT NOT NULL,
    confidence REAL NOT NULL,
    is_immutable BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Temporal validity
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP,
    
    -- Content and extraction
    content TEXT NOT NULL,
    entities_json TEXT,  -- GLiNER entities
    extraction_method TEXT NOT NULL,
    
    -- Provenance
    source_conversation_id TEXT NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
);

-- Fact relationships for conflict detection
CREATE TABLE fact_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_fact_id TEXT NOT NULL,
    target_fact_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,  -- contradicts, supports, relates_to
    confidence REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (source_fact_id) REFERENCES facts_metadata(fact_id) ON DELETE CASCADE,
    FOREIGN KEY (target_fact_id) REFERENCES facts_metadata(fact_id) ON DELETE CASCADE
);
```

### ChromaDB Collections
```python
# User facts collection (per-user isolation)
collection_name = f"user_facts_{user_id}"
metadata_schema = {
    "fact_id": str,
    "fact_type": str,
    "category": str,
    "confidence": float,
    "is_immutable": bool,
    "valid_from": str,
    "valid_until": str,
    "entities": List[str]
}
```

## Migration Plan

### Step 0: CLI and Database Structure Updates (FIRST PRIORITY)
**This MUST be completed before any code refactoring begins**

#### 1. Update LMDB CLI Commands (`cli/commands/lmdb.py`)
```python
# UPDATE: Change sub-database names in help examples
# OLD examples (lines 29-32):
"aico lmdb count conversation_history",
"aico lmdb dump message_index --limit 10", 
"aico lmdb tail conversation_history --limit 5",
"aico lmdb tail message_index --limit 3 --full"

# NEW examples:
"aico lmdb count session_memory",
"aico lmdb dump session_memory --limit 10",
"aico lmdb tail session_memory --limit 5", 
"aico lmdb tail user_sessions --limit 3 --full"
```

#### 2. Update ChromaDB CLI Commands (`cli/commands/chroma.py`)
```python
# UPDATE: Change collection references in help examples  
# OLD examples (lines 36-42):
"aico chroma count user_facts",
"aico chroma query user_facts 'What is my name?'",
"aico chroma add 'My name is John' --metadata '{\"type\": \"personal_info\"}'",
"aico chroma add 'I like pizza' --collection user_facts --id my_preference",
"aico chroma tail user_facts --limit 5",
"aico chroma tail user_facts --limit 3 --full",

# NEW examples (same collection name, different metadata structure):
"aico chroma count user_facts",
"aico chroma query user_facts 'What is my name?'", 
"aico chroma add 'User name is John' --metadata '{\"fact_type\": \"identity\", \"confidence\": 0.95}'",
"aico chroma add 'User likes pizza' --collection user_facts --id fact_preference_001",
"aico chroma tail user_facts --limit 5",
"aico chroma tail user_facts --limit 3 --full",
```

#### 3. Update Core Configuration (`config/defaults/core.yaml`)
```yaml
# UPDATE: Lines 259-262 - Change LMDB named databases
memory:
  working:
    ttl_seconds: 86400 # Keep same
    named_databases:
      - "session_memory"      # Was: conversation_history
      - "user_sessions"       # Was: user_state  
      # REMOVE: "message_index" (obsolete)

# UPDATE: Lines 269-271 - Remove conversation_segments collection
  semantic:
    enabled: true
    embedding_timeout_seconds: 120.0
    collections:
      user_facts: "user_facts"  # Keep same name, change structure
      # REMOVE: conversation_segments (obsolete)
    embedding_model: "paraphrase-multilingual"
    max_results: 20
```

#### 4. Update Database Initialization (`aico db init`) - IDEMPOTENT DESIGN
**Location**: `cli/commands/database.py` (find and update)

**CRITICAL: Maintain full idempotency - safe to run multiple times**

```python
# UPDATE: Initialize new LMDB sub-databases (IDEMPOTENT)
LMDB_SUBDATABASES = [
    "session_memory",    # Was: conversation_history
    "user_sessions"      # Was: user_state
    # REMOVE: message_index (but don't fail if it exists)
]

# IDEMPOTENT LMDB initialization logic:
def init_lmdb_idempotent():
    """Initialize LMDB with idempotent operations"""
    # 1. Create new sub-databases if they don't exist
    for db_name in LMDB_SUBDATABASES:
        if not lmdb_db_exists(db_name):
            create_lmdb_subdatabase(db_name)
            logger.info(f"Created LMDB sub-database: {db_name}")
        else:
            logger.info(f"LMDB sub-database already exists: {db_name}")
    
    # 2. Handle obsolete sub-databases (don't delete, just ignore)
    # message_index may still exist from old installations - that's OK
    # Let it exist but don't use it in new code

# UPDATE: Initialize ChromaDB collections with new metadata schema (IDEMPOTENT)
CHROMADB_COLLECTIONS = {
    "user_facts": {
        "embedding_model": "paraphrase-multilingual",
        "metadata_schema": {
            "user_id": str,
            "fact_type": str,        # identity, preference, relationship, temporal
            "category": str,         # personal_info, preferences, relationships
            "confidence": float,     # 0.0-1.0
            "is_immutable": bool,    # True for identity facts
            "valid_from": str,       # ISO timestamp
            "valid_until": str,      # ISO timestamp or null
            "entities": list,        # Extracted entities
            "source_conversation_id": str
        }
    }
    # NOTE: conversation_segments may exist from old installations - ignore it
}

# IDEMPOTENT ChromaDB initialization logic:
def init_chromadb_idempotent():
    """Initialize ChromaDB with idempotent operations"""
    # 1. Create user_facts collection if it doesn't exist
    if not chromadb_collection_exists("user_facts"):
        create_chromadb_collection("user_facts", CHROMADB_COLLECTIONS["user_facts"])
        logger.info("Created ChromaDB collection: user_facts")
    else:
        # Verify existing collection has correct embedding model
        existing_collection = get_chromadb_collection("user_facts")
        if existing_collection.embedding_model != "paraphrase-multilingual":
            logger.warning("user_facts collection exists with different embedding model")
        else:
            logger.info("ChromaDB collection already exists: user_facts")
    
    # 2. Handle obsolete collections (don't delete, just ignore)
    # conversation_segments may still exist - that's OK, just don't use it

# IDEMPOTENT libSQL schema initialization:
def init_libsql_schema_idempotent():
    """Initialize libSQL schema with idempotent operations"""
    # Schema migration system is already idempotent
    # Will only apply version 5 if not already applied
    apply_schema_migrations_to_latest()  # Existing idempotent function
```

#### 5. Update CLI Utility Functions
**Files to update:**
- `cli/utils/lmdb_utils.py` - Update sub-database references
- `cli/utils/chroma_utils.py` - Update collection metadata handling  
- Any other CLI utilities that reference old structure

#### 6. Verify `aico db init` Idempotency
**Critical requirement**: Ensure `aico db init` command:
- Creates new LMDB sub-databases: `session_memory`, `user_sessions` (if not exist)
- **DOES NOT delete** obsolete sub-database `message_index` (graceful coexistence)
- Creates ChromaDB `user_facts` collection with new metadata schema (if not exist)
- **DOES NOT delete** obsolete collection `conversation_segments` (graceful coexistence)
- Remains **100% idempotent** (safe to run multiple times without side effects)
- Updates libSQL schema to version 5 with new fact tables (if not already applied)

**Idempotency Test Protocol:**
```bash
# Test 1: Fresh installation
aico db init                    # Should complete without errors
aico db status                 # Should show schema version 5

# Test 2: Idempotency verification  
aico db init                    # Should complete without errors (no changes)
aico db init                    # Should complete without errors (no changes)
aico db init                    # Should complete without errors (no changes)

# Test 3: Verify database structure
aico lmdb ls                   # Should show: session_memory, user_sessions (+ any old dbs)
aico chroma ls                 # Should show: user_facts (+ any old collections)

# Test 4: Mixed state handling (old + new coexistence)
# If old databases exist, new ones should be created alongside them
# No data should be lost or corrupted
```

**Idempotency Requirements:**
1. **No destructive operations** - never delete existing data
2. **Existence checks** - always check if resource exists before creating
3. **Graceful coexistence** - old and new structures can coexist safely
4. **Schema versioning** - use existing idempotent migration system
5. **Logging clarity** - distinguish between "created" vs "already exists"

### Step 1: Preparation  
1. **Backup existing data** (if any)
2. **Create new schema version 5**
3. **Implement new fact extraction pipeline**
4. **Test with isolated user data**

### Step 2: Code Removal (Clean Slate)
```bash
# Files to DELETE completely
rm shared/aico/ai/memory/episodic.py
rm shared/aico/ai/memory/procedural.py
rm shared/aico/ai/memory/consolidation.py

# Code sections to REMOVE from existing files
# - SemanticRequestQueue class
# - Circuit breaker logic
# - Rate limiting code
# - Conversation segment processing
# - Memory consolidation logic
```

### Step 3: Implementation
1. **Refactor semantic.py** → fact storage system
2. **Refactor working.py** → session memory only
3. **Refactor manager.py** → 2-tier coordination
4. **Refactor context.py** → intelligent context assembly

### Step 4: Integration
1. **Update memory configuration**
2. **Test fact extraction accuracy**
3. **Validate multilingual support**
4. **Performance benchmarking**

## Success Metrics

### Performance Targets
- **Latency**: 91% reduction vs current system (Mem0 benchmark)
- **Token Usage**: 90% reduction in context assembly
- **Accuracy**: 26% improvement over current fact retrieval
- **Memory Usage**: <100MB total memory footprint

### Quality Targets
- **Identity Fact Accuracy**: 99.9% precision for immutable facts
- **Multilingual Support**: 100+ languages via modelservice
- **Context Preservation**: Perfect conversation continuity
- **Conflict Resolution**: 95% accurate fact conflict detection
- **Data Loss**: Complete backup before migration
- **Performance Regression**: Benchmark at each step
- **Multilingual Failures**: Comprehensive language testing
- **Fact Extraction Errors**: Confidence thresholds and validation

### Mitigation Strategies
- **Incremental rollout**: Test with single user first
- **Rollback plan**: Keep backup until system proven stable
- **Monitoring**: Real-time performance and accuracy metrics
- **Fail-fast**: Immediate failure on any data corruption

## Implementation Notes

### Critical Requirements
1. **No Pattern Matching**: All text analysis via LLM/NER models
2. **Multilingual First**: Every component supports 100+ languages
3. **Root Cause Solutions**: No patches or workarounds
4. **Clean Architecture**: Follow AICO BaseAIProcessor patterns
5. **Privacy Preservation**: All processing local via Ollama

### Error Handling
```python
# Example: Proper error handling with context
try:
    facts = await self.extract_facts(message, user_id)
except ModelServiceError as e:
    logger.error(f"Fact extraction failed for user {user_id}: {e}")
    raise MemoryProcessingError(
        f"Cannot extract facts: modelservice unavailable",
        user_id=user_id,
        conversation_id=conversation_id,
        original_error=e
    )
```

### Testing Strategy
1. **Unit Tests**: Each component isolated
2. **Integration Tests**: Full pipeline testing
3. **Multilingual Tests**: 10+ language validation
4. **Performance Tests**: Latency and memory benchmarks
5. **Accuracy Tests**: Fact extraction precision validation

## Conversation Engine Radical Simplification

### Current Complexity Problems
**The current memory integration is UNREADABLE and UNMAINTAINABLE:**

1. **82 lines** of complex memory retrieval logic (Lines 496-578)
2. **60 lines** of XML processing and context assembly (Lines 677-736)  
3. **25 lines** of AI response storage with race conditions (Lines 932-956)
4. **Multiple async handlers** for memory responses (Lines 603-611)
5. **Feature flags everywhere** making code paths unpredictable
6. **Timeout handling, error recovery, fallbacks** - unnecessary complexity

### Target: 10 Lines Total Memory Integration

**REPLACE 167+ lines of complex code with 10 simple lines:**

```python
class ConversationEngine(BaseService):
    def __init__(self, name: str, container):
        super().__init__(name, container)
        # Memory is REQUIRED - no feature flags, no fallbacks
        self.memory_manager = None  # Injected during startup
    
    async def start(self) -> None:
        # Memory manager MUST be available or startup fails
        self.memory_manager = ai_registry.get("memory")
        if not self.memory_manager:
            raise RuntimeError("Memory manager required but not available")
    
    async def _handle_user_input(self, message) -> None:
        # Extract message data
        user_id = conv_message.user_id
        conversation_id = conv_message.message.conversation_id
        message_text = conv_message.message.text
        
        # 1. Store user message (1 line)
        await self.memory_manager.store_message(user_id, conversation_id, message_text, "user")
        
        # 2. Get context (1 line)  
        context = await self.memory_manager.assemble_context(user_id, message_text)
        
        # 3. Generate LLM response (1 line)
        response_text = await self._generate_llm_response(context, message_text)
        
        # 4. Store AI response (1 line)
        await self.memory_manager.store_message(user_id, conversation_id, response_text, "assistant")
        
        # 5. Deliver response (1 line)
        await self._deliver_response(conversation_id, response_text)
    
    def _build_prompt(self, facts: List[Dict], recent: List[Dict], message: str) -> str:
        # Simple prompt building (3 lines)
        facts_text = "\n".join([f"- {fact['content']}" for fact in facts[-5:]])
        recent_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent[-3:]])
        return f"Facts:\n{facts_text}\n\nRecent:\n{recent_text}\n\nUser: {message}\nAssistant:"
```

### Massive Code Deletion Required

**DELETE COMPLETELY (167+ lines):**
```python
# DELETE: Lines 496-578 (82 lines)
async def _request_memory_retrieval(...)  # ENTIRE METHOD

# DELETE: Lines 603-611 (9 lines)  
async def _handle_memory_response(...)    # ENTIRE METHOD

# DELETE: Lines 677-736 (60 lines)
# All XML processing, memory item filtering, context assembly complexity

# DELETE: Lines 932-956 (25 lines)
# Complex AI response storage with error handling

# DELETE: Lines 125-129 (5 lines)
# All feature flag initialization

# DELETE: Lines 399-405 (7 lines)  
# Feature flag checks in response generation

# DELETE: Lines 835-865 (30 lines)
# Complex system prompt building with XML processing
```

**REPLACE WITH (10 lines total):**
```python
# NEW: Simple memory integration
async def _store_message(self, user_id: str, conversation_id: str, content: str, role: str):
    await self.memory_manager.store_message(user_id, conversation_id, content, role)

async def _get_context(self, user_id: str, message: str) -> Dict:
    return await self.memory_manager.assemble_context(user_id, message)

def _build_simple_prompt(self, facts: List, recent: List, message: str) -> str:
    facts_str = "\n".join([f"- {f['content']}" for f in facts[-5:]])
    recent_str = "\n".join([f"{m['role']}: {m['content']}" for m in recent[-3:]])
    return f"User Facts:\n{facts_str}\n\nRecent:\n{recent_str}\n\nUser: {message}"
```

### Benefits of Radical Simplification

1. **Readability**: 10 lines vs 167+ lines
2. **Maintainability**: No complex async coordination
3. **Debuggability**: Simple linear flow
4. **Performance**: No timeouts, no complex processing
5. **Reliability**: Fail fast, no silent errors
6. **Testability**: Easy to unit test simple methods

### Implementation Priority

**This simplification is CRITICAL for the refactor success:**
- Current complexity makes memory integration nearly impossible to debug
- Feature flags create unpredictable code paths
- Async coordination adds unnecessary race conditions
- XML processing is overkill for simple fact assembly

**The conversation engine should be SIMPLE and READABLE** - its job is to coordinate, not to implement complex memory logic.

---

**Implementation Timeline**: 3 weeks  
**Success Criteria**: Surpass current market solutions in accuracy, speed, and multilingual support  
**Failure Criteria**: Any silent failures, fallbacks, or pattern matching regressions
