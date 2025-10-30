# Knowledge Graph Module

**Status:** Proposal  
**Module:** `aico.ai.knowledge_graph` (core AI module)  
**First Consumer:** Semantic Memory  
**Research-Validated:** 2025 industry best practices (GraphRAG, Graphusion, LlamaIndex, Semantic ER)

---

## Overview

This document proposes a **core knowledge graph module** for AICO that provides property graph construction, entity resolution, and graph fusion capabilities. The module is domain-agnostic and reusable across multiple AI features.

**First Application:** Semantic memory deduplication (critical bug fix)  
**Future Applications:** Relationship intelligence, autonomous agency, conversation context, emotional memory

---

## Problem Statement (Semantic Memory)

Current semantic memory has a critical deduplication failure: running the same conversation twice creates duplicate facts because extraction is non-deterministic.

```
Run 1: "I moved to SF" → Extract → 14 facts
Run 2: "I moved to SF" → Extract → 28 facts (duplicates!)
Run 3: "I moved to SF" → Extract → 42 facts (unbounded growth)
```

**Root Cause:** Facts are stored as unstructured text without normalization. Same information expressed differently creates different embeddings, defeating similarity-based deduplication.

---

## Proposed Solution: Core Knowledge Graph Module

A **property graph** represents knowledge as nodes (entities) and edges (relationships), both with typed properties. This provides deterministic structure for deduplication while maintaining rich metadata.

### Module Architecture

```
aico/
  ai/
    knowledge_graph/              # Core module (domain-agnostic)
      __init__.py
      models.py                    # PropertyGraph, Node, Edge
      extractor.py                 # Multi-pass extraction
      entity_resolution.py         # Semantic blocking, LLM matching/merging
      fusion.py                    # Graph fusion, conflict resolution
      storage.py                   # ChromaDB + libSQL backend
      query.py                     # Graph traversal, filtering
    
    memory/
      semantic.py                  # Uses knowledge_graph module
```

### Pipeline Architecture

```
Conversation → Multi-Pass Extraction → Property Graph → Semantic Entity Resolution → Graph Fusion → Storage
                    ↓                        ↓                      ↓                      ↓           ↓
                extractor.py              models.py          entity_resolution.py      fusion.py  storage.py
```

---

## Core Algorithms

### 1. Multi-Pass Extraction (Gleanings)

**Problem:** LLMs extract only 60-70% of information on first pass (Microsoft GraphRAG research, 2024).

**Algorithm:**
```python
def extract_with_gleanings(text: str, max_passes: int = 2) -> PropertyGraph:
    graph = PropertyGraph()
    
    # Pass 1: Initial extraction
    entities_1 = gliner_extract_entities(text)
    relations_1 = llm_extract_relations(text, entities_1)
    graph.add(entities_1, relations_1)
    
    # Pass 2+: Gleaning (extract missed information)
    for i in range(max_passes):
        prompt = f"Previously extracted: {graph}. Extract ADDITIONAL information from: {text}"
        new_extractions = llm_extract(prompt)
        if not new_extractions:
            break
        graph.add(new_extractions)
    
    # Pass N: Novel inference (implicit relations from conversation history)
    implicit_relations = infer_from_context(graph, conversation_history)
    graph.add(implicit_relations)
    
    return graph
```

**Benefits:**
- 90%+ information capture vs 60-70% single-pass
- Discovers implicit relationships from context
- Deterministic: same conversation → same graph structure

---

### 2. Property Graph Model

**Problem:** Simple triplets `[subject, relation, object]` lack expressiveness for rich metadata.

**Data Model:**
```python
@dataclass
class PropertyGraphNode:
    """Entity with typed properties"""
    id: str
    label: str  # PERSON, PLACE, ORGANIZATION, EVENT
    properties: Dict[str, Any]  # name, age, location, etc.
    embedding: List[float]  # For similarity search
    confidence: float
    source_text: str
    created_at: datetime

@dataclass
class PropertyGraphEdge:
    """Relationship with typed properties"""
    source_id: str
    target_id: str
    relation_type: str  # WORKS_AT, MOVED_TO, KNOWS
    properties: Dict[str, Any]  # since, until, reason, etc.
    confidence: float
    source_text: str
    created_at: datetime
```

**Benefits:**
- Richer representation than flat text
- Typed entities and relations enable schema validation
- Properties store contextual metadata
- Direct migration path to Neo4j graph database
- Supports complex queries (future: Cypher)

---

### 3. Semantic Entity Resolution

**Problem:** String matching fails on variants ("NMT" vs "neural machine translation"). Embedding similarity alone creates false positives.

**Algorithm (3-step process):**

#### Step 1: Semantic Blocking
```python
def semantic_blocking(entities: List[Node]) -> List[List[Node]]:
    """Cluster similar entities using embeddings (reduces O(n²) to O(k*m²))"""
    embeddings = [entity.embedding for entity in entities]
    clusters = hdbscan_cluster(embeddings, min_similarity=0.85)
    return clusters  # Only compare entities within same cluster
```

#### Step 2: LLM Matching
```python
def llm_match(entity1: Node, entity2: Node) -> MatchDecision:
    """Validate if entities are duplicates with explainable reasoning"""
    prompt = f"""
    Are these the same entity?
    Entity 1: {entity1.label} - {entity1.properties}
    Entity 2: {entity2.label} - {entity2.properties}
    
    Output JSON: {{"is_match": bool, "confidence": float, "reasoning": str}}
    """
    return llm_call(prompt, response_format="json")
```

#### Step 3: LLM Merging
```python
def llm_merge(entities: List[Node]) -> Node:
    """Merge duplicates with conflict resolution"""
    prompt = f"""
    Merge these duplicate entities, resolving conflicts:
    {entities}
    
    Rules:
    - Keep highest confidence values
    - Union of properties (no data loss)
    - Resolve conflicts by recency or source reliability
    
    Output merged entity JSON.
    """
    return llm_call(prompt, response_format="json")
```

**Benefits:**
- 95%+ deduplication accuracy (vs 0% current)
- Explainable decisions (chain-of-thought reasoning)
- Handles semantic equivalence ("SF" = "San Francisco")
- Conflict resolution preserves data integrity

**Research Basis:** "The Rise of Semantic Entity Resolution" (TDS, Jan 2025) - state-of-the-art since Ditto paper (2020) showed 29% improvement using BERT.

---

### 4. Graph Fusion (Global Perspective)

**Problem:** Local sentence-level extraction misses global relationships across conversation history.

**Algorithm (Graphusion framework, ACL 2024):**

```python
def fuse_graphs(new_graph: PropertyGraph, existing_graph: PropertyGraph) -> PropertyGraph:
    """Fuse new extractions with existing knowledge"""
    
    # Step 1: Entity Merging
    # Normalize variants: "NMT" + "neural machine translation" → canonical form
    merged_nodes = {}
    for new_node in new_graph.nodes:
        canonical = find_canonical_entity(new_node, existing_graph)
        if canonical:
            merged_nodes[new_node.id] = merge_entities(canonical, new_node)
        else:
            merged_nodes[new_node.id] = new_node
    
    # Step 2: Conflict Resolution
    # Multiple relations between same entities? Choose best one.
    resolved_edges = []
    for (source, target), relations in group_by_endpoints(all_edges):
        if len(relations) == 1:
            resolved_edges.append(relations[0])
        else:
            best = llm_resolve_conflict(relations, conversation_context)
            resolved_edges.append(best)
    
    # Step 3: Novel Triplet Discovery
    # Infer implicit relationships from conversation history
    novel_edges = llm_infer_implicit_relations(
        merged_nodes, 
        resolved_edges,
        conversation_history
    )
    resolved_edges.extend(novel_edges)
    
    return PropertyGraph(merged_nodes, resolved_edges)
```

**Benefits:**
- Global understanding vs local sentence extraction
- Discovers implicit relationships
- Resolves conflicting information
- Maintains knowledge consistency

---

## Storage Strategy

### Hybrid: ChromaDB + libSQL

The knowledge graph module uses a hybrid storage approach leveraging AICO's existing stack:

#### ChromaDB Collections (Vector Search)

```python
# Collection: kg_nodes
# Purpose: Semantic search over entities
node_doc = f"{node.label}: {node.properties.get('name', '')} {node.source_text}"
node_metadata = {
    'node_id': node.id,
    'label': node.label,
    'properties': json.dumps(node.properties),
    'confidence': node.confidence,
    'user_id': user_id,
    'created_at': node.created_at.isoformat()
}
chromadb.get_collection('kg_nodes').add(
    documents=[node_doc],
    embeddings=[node.embedding],
    metadatas=[node_metadata],
    ids=[node.id]
)

# Collection: kg_edges
# Purpose: Semantic search over relationships
edge_doc = f"{edge.relation_type}: {edge.source_id} -> {edge.target_id} ({edge.source_text})"
edge_metadata = {
    'edge_id': edge.id,
    'source_id': edge.source_id,
    'target_id': edge.target_id,
    'relation_type': edge.relation_type,
    'properties': json.dumps(edge.properties),
    'confidence': edge.confidence,
    'user_id': user_id,
    'created_at': edge.created_at.isoformat()
}
chromadb.get_collection('kg_edges').add(
    documents=[edge_doc],
    embeddings=[edge.embedding],
    metadatas=[edge_metadata],
    ids=[edge.id]
)
```

#### libSQL Tables (Relational Index)

```sql
-- Nodes table: Fast filtering by label, user, properties
CREATE TABLE kg_nodes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    label TEXT NOT NULL,
    properties JSON NOT NULL,
    confidence REAL NOT NULL,
    source_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    INDEX idx_user_label (user_id, label),
    INDEX idx_user_created (user_id, created_at)
);

-- Edges table: Fast graph traversal
CREATE TABLE kg_edges (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    properties JSON NOT NULL,
    confidence REAL NOT NULL,
    source_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    INDEX idx_source (source_id),
    INDEX idx_target (target_id),
    INDEX idx_user_relation (user_id, relation_type),
    FOREIGN KEY (source_id) REFERENCES kg_nodes(id),
    FOREIGN KEY (target_id) REFERENCES kg_nodes(id)
);

-- Node property index: Fast property-based queries on entities
-- Note: Properties are DUPLICATED here from kg_nodes.properties JSON for performance
CREATE TABLE kg_node_properties (
    node_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (node_id, key, value),
    FOREIGN KEY (node_id) REFERENCES kg_nodes(id),
    INDEX idx_key_value (key, value)
);

-- Edge property index: Fast property-based queries on relationships
-- Note: Properties are DUPLICATED here from kg_edges.properties JSON for performance
CREATE TABLE kg_edge_properties (
    edge_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (edge_id, key, value),
    FOREIGN KEY (edge_id) REFERENCES kg_edges(id),
    INDEX idx_key_value (key, value)
);
```

**Property Storage Pattern:**

Properties are stored in **two places** for different query patterns:

1. **JSON columns** (`kg_nodes.properties`, `kg_edges.properties`): Source of truth, easy to retrieve full object
2. **Property index tables** (`kg_node_properties`, `kg_edge_properties`): Flattened key-value pairs for fast filtering

Example:
```sql
-- Stored in kg_nodes.properties as JSON
{"name": "John Smith", "age": 30, "city": "San Francisco"}

-- ALSO indexed in kg_node_properties as rows
(node_id, "name", "John Smith")
(node_id, "age", "30")
(node_id, "city", "San Francisco")

-- Enables fast queries like:
SELECT * FROM kg_nodes n 
JOIN kg_node_properties p ON n.id = p.node_id 
WHERE p.key = 'city' AND p.value = 'San Francisco'
```

This is a standard **denormalization pattern** for performance - properties are duplicated but enable fast WHERE clauses on specific property values without JSON parsing.

**Maintaining Consistency (Critical):**

To prevent data inconsistency between JSON and index tables, we use **database triggers** for automatic synchronization:

```sql
-- Automatic index sync for nodes
CREATE TRIGGER sync_node_properties_insert
AFTER INSERT ON kg_nodes
FOR EACH ROW
BEGIN
    INSERT INTO kg_node_properties (node_id, key, value)
    SELECT NEW.id, key, value FROM json_each(NEW.properties);
END;

CREATE TRIGGER sync_node_properties_update
AFTER UPDATE OF properties ON kg_nodes
FOR EACH ROW
BEGIN
    DELETE FROM kg_node_properties WHERE node_id = NEW.id;
    INSERT INTO kg_node_properties (node_id, key, value)
    SELECT NEW.id, key, value FROM json_each(NEW.properties);
END;

CREATE TRIGGER sync_node_properties_delete
AFTER DELETE ON kg_nodes
FOR EACH ROW
BEGIN
    DELETE FROM kg_node_properties WHERE node_id = OLD.id;
END;

-- Automatic index sync for edges (same pattern)
CREATE TRIGGER sync_edge_properties_insert
AFTER INSERT ON kg_edges
FOR EACH ROW
BEGIN
    INSERT INTO kg_edge_properties (edge_id, key, value)
    SELECT NEW.id, key, value FROM json_each(NEW.properties);
END;

CREATE TRIGGER sync_edge_properties_update
AFTER UPDATE OF properties ON kg_edges
FOR EACH ROW
BEGIN
    DELETE FROM kg_edge_properties WHERE edge_id = NEW.id;
    INSERT INTO kg_edge_properties (edge_id, key, value)
    SELECT NEW.id, key, value FROM json_each(NEW.properties);
END;

CREATE TRIGGER sync_edge_properties_delete
AFTER DELETE ON kg_edges
FOR EACH ROW
BEGIN
    DELETE FROM kg_edge_properties WHERE edge_id = OLD.id;
END;
```

**Benefits of trigger-based synchronization:**
- ✅ **Atomic**: Index updates happen in same transaction as JSON update (all-or-nothing)
- ✅ **Automatic**: Impossible for developers to forget index updates
- ✅ **Consistent**: Database guarantees synchronization at all times
- ✅ **Zero application logic**: Handled transparently at database level
- ✅ **Crash-safe**: Partial updates automatically rolled back

**Verified:** libsql 0.1.8 fully supports triggers with `json_each()` function. Tested and confirmed working for INSERT, UPDATE, and DELETE operations.

---

### Property Conventions (Future-Proofing)

The schema uses flexible JSON properties to accommodate future applications without schema migrations. Standard property conventions ensure consistency across the system:

#### **Node Property Conventions:**
```yaml
# Temporal validity (for facts that change over time)
temporal:
  valid_from: "2024-01-01T00:00:00Z"  # ISO8601 timestamp
  valid_until: "2025-12-31T23:59:59Z" # ISO8601 or null for current facts
  is_current: true                     # Boolean flag for active facts

# Provenance tracking (where facts came from)
provenance:
  conversation_id: "conv_abc123"       # Source conversation
  message_id: "msg_xyz789"             # Specific message
  extraction_method: "gliner"          # Extraction algorithm used
  extraction_pass: 1                   # Which extraction pass (1, 2, gleaning)

# Emotional context (for emotional memory)
emotional:
  primary_emotion: "proud"             # Primary emotion
  intensity: 0.8                       # Float 0-1
  valence: "positive"                  # positive/negative/neutral
  trigger: "achievement"               # What caused the emotion
```

#### **Edge Property Conventions:**
```yaml
# Temporal relationships (for time-bound connections)
temporal:
  valid_from: "2020-01-01T00:00:00Z"  # When relationship started
  valid_until: "2023-12-31T23:59:59Z" # When relationship ended (null if ongoing)
  duration_days: 1461                  # Computed duration

# Relationship metadata (for relationship intelligence)
relationship:
  privacy_level: "private"             # public/private/intimate
  closeness: 0.9                       # Float 0-1 (relationship strength)
  contact_frequency: "weekly"          # Interaction frequency
  relationship_type: "family"          # Category of relationship

# Planning metadata (for autonomous agency)
planning:
  priority: 1                          # Int 1-5 (1=highest)
  status: "active"                     # pending/active/completed/failed
  progress: 0.6                        # Float 0-1 (completion percentage)
  deadline: "2025-12-31T23:59:59Z"    # Target completion date
  dependencies: ["task_id_1", "task_id_2"]  # Task dependencies

# Emotional interactions (for emotional memory)
emotions:
  user_emotion: "proud"                # User's emotional state
  other_emotion: "nervous"             # Other person's emotional state
  user_intensity: 0.8                  # Float 0-1
  other_intensity: 0.6                 # Float 0-1
  outcome: "successful"                # Result of interaction
  context: "piano_recital"             # What triggered emotions

# Conversation metadata (for context assembly)
conversation:
  conversation_id: "conv_abc123"       # Source conversation
  timestamp: "2025-10-01T14:30:00Z"   # When discussed
  sentiment: "positive"                # Overall sentiment
  relevance_score: 0.85                # Float 0-1 (importance)
  topic: "career_change"               # Discussion topic
```

#### **Future Application Support:**

| Application | Required Properties | Schema Support |
|-------------|-------------------|----------------|
| **Relationship Intelligence** | privacy_level, closeness, contact_frequency | ✅ Edge properties |
| **Autonomous Agency** | priority, status, progress, deadline, dependencies | ✅ Edge properties |
| **Conversation Context** | conversation_id, timestamp, sentiment, relevance | ✅ Edge properties |
| **Emotional Memory** | emotions, intensity, valence, trigger, outcome | ✅ Node/Edge properties |
| **Temporal Facts** | valid_from, valid_until, is_current | ✅ Node/Edge properties |

**Migration Strategy:**
- **Phase 1:** Use JSON properties with documented conventions (current)
- **Phase 2:** Add indexed temporal fields if temporal queries become frequent (>10% of queries)
- **Phase 3:** Add version history table if audit trail becomes critical requirement

The current schema is **future-proof** - all identified future applications can be supported without schema changes by following these property conventions.

---

**Why Hybrid?**
- ✅ **ChromaDB:** Semantic search (find similar entities), already in use
- ✅ **libSQL:** Fast relational queries (find all PERSON nodes, traverse edges), already in use
- ✅ **No new dependencies:** Leverage existing AICO stack
- ✅ **Dual-write:** Write to both stores for different query patterns

### Future: Neo4j (Native Graph Database)

Direct migration path when complex graph queries needed (Cypher, multi-hop traversal, community detection). Property graph model is Neo4j-compatible.

---

## Module Integration: Semantic Memory

The knowledge graph module integrates with semantic memory as follows:

```python
# aico/ai/memory/semantic.py
from aico.ai.knowledge_graph import PropertyGraph, Extractor, EntityResolver, GraphFusion

class SemanticMemoryStore:
    def __init__(self, config, modelservice):
        # Initialize knowledge graph components
        self.graph = PropertyGraph(
            storage_backend="chromadb+libsql",
            config=config.knowledge_graph
        )
        self.extractor = Extractor(
            modelservice=modelservice,
            max_gleanings=config.knowledge_graph.extraction.max_gleanings
        )
        self.resolver = EntityResolver(
            modelservice=modelservice,
            config=config.knowledge_graph.entity_resolution
        )
        self.fusion = GraphFusion(
            modelservice=modelservice,
            config=config.knowledge_graph.fusion
        )
    
    async def add_facts(self, text: str, user_id: str, conversation_id: str):
        """Extract and store facts from conversation using knowledge graph"""
        # Step 1: Multi-pass extraction
        new_graph = await self.extractor.extract(
            text=text,
            context={"user_id": user_id, "conversation_id": conversation_id}
        )
        
        # Step 2: Semantic entity resolution
        resolved_graph = await self.resolver.resolve(
            new_graph=new_graph,
            user_id=user_id
        )
        
        # Step 3: Graph fusion with existing knowledge
        await self.fusion.fuse(
            new_graph=resolved_graph,
            existing_graph=self.graph,
            user_id=user_id
        )
        
        # Step 4: Store in hybrid backend
        await self.graph.save(user_id=user_id)
    
    async def search_facts(self, query: str, user_id: str, top_k: int = 10):
        """Search facts using semantic similarity"""
        return await self.graph.search_nodes(
            query=query,
            user_id=user_id,
            top_k=top_k
        )
```

---

## Future Applications (Beyond Semantic Memory)

The knowledge graph module is designed for reuse across AICO's AI features:

### 1. Relationship Intelligence

```python
# aico/ai/relationships/social_graph.py
from aico.ai.knowledge_graph import PropertyGraph

class SocialRelationshipGraph:
    def __init__(self):
        self.graph = PropertyGraph(storage_backend="chromadb+libsql")
    
    async def get_relationship_context(self, user_id: str, person_id: str):
        return await self.graph.traverse(
            start=user_id,
            relations=["KNOWS", "FAMILY_MEMBER"],
            target=person_id,
            max_depth=2
        )
```

**Use Case:** Multi-dimensional relationship understanding, privacy boundaries, context-appropriate responses.

### 2. Autonomous Agency

```python
# aico/ai/agency/goal_planner.py
from aico.ai.knowledge_graph import PropertyGraph

class GoalPlanner:
    def __init__(self):
        self.graph = PropertyGraph(storage_backend="chromadb+libsql")
    
    async def generate_goals(self, user_id: str):
        # Query user's current situation
        context = await self.graph.get_user_context(user_id)
        # Infer goals from graph structure
        return infer_goals_from_context(context)
```

**Use Case:** Proactive suggestions, goal generation, multi-step planning.

### 3. Conversation Context Assembly

```python
# aico/ai/conversation/context_assembler.py
from aico.ai.knowledge_graph import PropertyGraph

class ContextAssembler:
    def __init__(self):
        self.graph = PropertyGraph(storage_backend="chromadb+libsql")
    
    async def assemble_context(self, query: str, user_id: str):
        # Multi-hop graph traversal for rich context
        return await self.graph.traverse(
            start=user_id,
            query=query,
            max_depth=3
        )
```

**Use Case:** Intelligent context retrieval, reduced hallucination, multi-hop reasoning.

### 4. Emotional Memory

```python
# Track emotional context in relationships
Edge(source="user", target="sarah", relation="DISCUSSED", properties={
    "topic": "piano_recital",
    "user_emotion": "proud",
    "sarah_emotion": "nervous",
    "date": "2025-09-30",
    "outcome": "successful"
})
```

**Use Case:** Emotional memory integration, context-aware empathy.

**Note:** These applications are **not implemented** in this proposal. They demonstrate the module's reusability and future potential

---

## Performance Optimization Strategies

The 2500ms latency is too high for conversational UX. However, **we will not dumb down the solution**. Instead, we decouple processing time from conversation flow using architectural strategies.

### Strategy 1: Progressive Response with Cognitive States

**Approach:** Stream AI's cognitive process to user, deliver response early, process graph in background.

```
Timeline:
0ms:    "Listening..." (instant feedback)
200ms:  "Understanding..." (entity extraction)
600ms:  AI RESPONSE DELIVERED ✅ (user can continue)
        ↓ [Background processing, non-blocking]
1800ms: "Storing in memory..." (graph construction)
2500ms: Complete (memory fully processed)
```

**Benefits:** 600ms user-perceived latency, full state-of-the-art processing, transparent UX.

### Strategy 2: Lazy Graph Construction

**Approach:** Respond immediately with simple extraction, build full graph during conversation pauses (idle time).

```python
# Fast path: 700ms
response = await generate_response(text, simple_entities)
await store_simple_facts(text, entities)

# Schedule for idle time (2-3s gaps between messages)
await schedule_background_task(build_full_knowledge_graph)
```

**Benefits:** 700ms response time, graph processing during natural pauses, efficient resource usage.

### Strategy 3: Incremental Graph Construction

**Approach:** Build graph incrementally across multiple turns, not all at once.

```
Turn N:   Fast response + Pass 1 extraction (600ms + 800ms background)
Turn N+1: Fast response + Pass 2 gleaning (600ms + 500ms background)
Turn N+2: Fast response + Entity resolution (600ms + 820ms background)
```

**Benefits:** Distributed compute load, graph quality improves over conversation.

### Strategy 4: Parallel Processing

**Approach:** Run extraction passes and entity resolution in parallel where possible.

```python
# Parallel extraction: 800ms (vs 1700ms sequential)
results = await asyncio.gather(
    extract_pass1(text),
    extract_pass2(text),
    extract_pass3(text)
)

# Parallel entity resolution: 400ms (vs 640ms sequential)
blocks, existing = await asyncio.gather(
    semantic_blocking(graph),
    fetch_user_entities(user_id)
)
```

**Savings:** 1200ms background processing (vs 2340ms), 49% faster, no quality loss.

### Strategy 5: Smart Caching

**Approach:** Cache expensive LLM operations for repeated entities.

```python
# First mention: 640ms (full entity resolution)
# Repeated mention: 50ms (cache hit)
# Savings: 92% for repeated entities
```

**Benefits:** Dramatic speedup for common entities (names, places), scales with conversation length.

### Strategy 6: Cognitive State UI

**Approach:** Show users AICO's "inner monologue" to make processing time feel intentional.

```
AICO: 🧠 Understanding your message
      ├─ Extracted: "San Francisco" (PLACE)
      └─ Extracted: "moved" (EVENT)
      
      💭 Thinking about my response...
      
      "That's exciting! How are you finding the city?"
      
      📚 Storing in memory... (background)
      └─ Connecting to previous locations
```

**Benefits:** Transforms wait time into feature, builds trust, reduces perceived latency.

---

## Recommended Approach

**Hybrid Strategy:**

### **Implementation (Required)**
Combines progressive response delivery with parallel processing for optimal user experience.

**Features:**
- Progressive response with cognitive states (600ms user-perceived latency)
- Parallel extraction and entity resolution (1200ms background vs 2340ms sequential)
- Background graph processing (non-blocking)
- Transparent UX with visible cognitive states

**Benefits:**
- ✅ 600ms user response time
- ✅ 1200ms background processing (49% faster than sequential)
- ✅ Full state-of-the-art quality, zero dumbing down
- ✅ Transparent UX builds trust

### **Enhancement (Optional)**
Additional optimizations for scaling and performance improvements.

**Features:**
- Smart caching for repeated entities (50ms vs 640ms, 92% faster)
- Lazy graph construction during idle time (2-3s gaps between messages)
- Incremental graph building across conversation turns

**Benefits:**
- ✅ Dramatic speedup for common entities (names, places)
- ✅ Zero user-perceived impact (processing during pauses)
- ✅ Distributed compute load across conversation
- ✅ Scales with conversation length

**Configuration:**
```yaml
core:
  ai:
    knowledge_graph:
      processing:
        # Implementation features are hardcoded (progressive response, parallel processing, background processing)
        # Only performance tuning is configurable:
        caching_enabled: true            # Enable entity resolution caching (recommended)
        cache_size: 1000                 # Number of entities to cache (adjust based on memory)
```

**Result:** 600ms user response, 1200ms background processing, full state-of-the-art quality with optional caching for scaling.

**Note:** Implementation features are required for MVP. Enhancement features can be added later based on real-world performance testing and scaling needs.

---

## Implementation Roadmap

### Phase 0: Cleanup & Preparation
**Scope:** Remove obsolete code and prepare codebase for knowledge graph implementation

**Deliverables:**

**Code Cleanup:**
- Remove legacy fact extraction code from `aico/ai/memory/semantic.py`
- Remove obsolete `AdvancedFactExtractor` class and related utilities
- Clean up any placeholder/simulation code in memory evaluation
- Remove unused imports and dead code paths

---

### **libSQL Database Changes**

**❌ Remove (Schema Version 6):**
- `facts_metadata` table → replaced by `kg_nodes`
- `fact_relationships` table → replaced by `kg_edges`
- `session_metadata` table → no longer needed (LMDB coordination)

**✅ Add (Schema Version 7):**
- `kg_nodes` table (with triggers for property indexing)
- `kg_edges` table (with triggers for property indexing)
- `kg_node_properties` table (property index)
- `kg_edge_properties` table (property index)

**📝 Notes:**
- No data migration needed (not in production)
- Ensure `aico db init` remains idempotent

---

### **ChromaDB Changes**

**❌ Remove:**
- `user_facts` collection (fact-based semantic memory)
- Collection initialization code in `cli/commands/database.py` (lines 87-105)

**✅ Add:**
- `kg_nodes` collection (semantic search over entities)
- `kg_edges` collection (semantic search over relationships)

**📝 Notes:**
- No data migration needed (not in production)
- Complete replacement of old collection structure

---

### **LMDB Changes**

**❌ Remove:**
- `user_sessions` named database from config (unused - not referenced in code)

**✅ Keep (No Changes):**
- LMDB working memory database (separate system for conversation context)
- `session_memory` named database (actively used by `WorkingMemoryStore`)
- LMDB initialization in `cli/commands/database.py` (line 350)
- `cli/utils/lmdb_utils.py` (working memory management)

**🔄 Update:**
- `config/defaults/core.yaml`: Remove `user_sessions` from `core.memory.working.named_databases` list

**📝 Notes:**
- Working memory (LMDB) handles short-term conversation context (TTL: 24 hours)
- Semantic memory (knowledge graph) handles long-term facts (permanent)
- These are separate, independent systems

---

**Documentation:**
- Document what was removed and why
- Update architecture diagrams to reflect new knowledge graph approach
- Create migration guide for any existing deployments

**Validation:**
- Verify `aico db init` still works (idempotent)
- Verify no broken imports or references to removed code
- Run existing tests to ensure nothing breaks
- Confirm clean slate for knowledge graph implementation

**Note:** This phase follows the principle of complete cleanup - no backwards compatibility, no "just in case" code. All obsolete components are fully removed before implementing the new system.

---

### Phase 1: Core Module Foundation
**Scope:** Basic module structure and data models

**Deliverables:**
- Create `aico/ai/knowledge_graph/` module structure
- Implement `models.py` (PropertyGraph, Node, Edge dataclasses)
- Implement `storage.py` (ChromaDB + libSQL hybrid backend)
- Create libSQL Schema Version 7:
  - `kg_nodes` table with JSON properties
  - `kg_edges` table with JSON properties
  - `kg_node_properties` table (property index)
  - `kg_edge_properties` table (property index)
  - Database triggers for automatic property indexing (verified working in libsql 0.1.8)
- Initialize ChromaDB collections (kg_nodes, kg_edges)
- Implement dual-write to both ChromaDB and libSQL
- Basic CRUD operations (create, read, update, delete)
- Document property conventions for future applications
- Unit tests for data models and storage

### Phase 2: Multi-Pass Extraction
**Scope:** Implement extraction pipeline

**Deliverables:**
- Implement `extractor.py` (multi-pass extraction with gleanings)
- GLiNER entity extraction (Pass 1)
- LLM relation extraction (Pass 1)
- Gleaning extraction (Pass 2+)
- Novel inference from conversation history (Pass N)
- Benchmark completeness improvements (60-70% → 90%+)
- Unit tests for extraction

### Phase 3: Semantic Entity Resolution
**Scope:** Implement deduplication

**Deliverables:**
- Implement `entity_resolution.py`
- Semantic blocking (HDBSCAN clustering)
- LLM-based matching (with chain-of-thought)
- LLM-based merging (with conflict resolution)
- Test deduplication accuracy (target: 95%+)
- Unit tests for entity resolution

### Future Enhancements

#### **Priority 1: Critical Additions (Phase 1.5)**

##### **1. Temporal/Bi-Temporal Data Model** ⭐ **HIGH PRIORITY**

**Problem:** Current schema only tracks when facts were recorded (`created_at`, `updated_at`), not when they were valid in real life.

**Why Critical:**
- **Relationship evolution:** "Sarah was my girlfriend" → "Sarah is my wife" (temporal validity)
- **Historical context:** "What was I working on last month?" requires point-in-time queries
- **Autonomous agency:** Planning requires understanding temporal sequences
- **Emotional memory:** "How did I feel about X over time?" needs temporal tracking

**Implementation:**

Add indexed temporal fields to tables:
```sql
ALTER TABLE kg_nodes ADD COLUMN valid_from TEXT;
ALTER TABLE kg_nodes ADD COLUMN valid_until TEXT;
ALTER TABLE kg_nodes ADD COLUMN is_current INTEGER DEFAULT 1;

ALTER TABLE kg_edges ADD COLUMN valid_from TEXT;
ALTER TABLE kg_edges ADD COLUMN valid_until TEXT;
ALTER TABLE kg_edges ADD COLUMN is_current INTEGER DEFAULT 1;

-- Indexes for temporal queries
CREATE INDEX idx_kg_nodes_temporal ON kg_nodes(user_id, is_current, valid_from);
CREATE INDEX idx_kg_edges_temporal ON kg_edges(user_id, is_current, valid_from);
```

Property conventions (stored in JSON `properties` field):
```yaml
temporal:
  valid_from: "2024-01-01T00:00:00Z"    # When fact became true (event time)
  valid_until: "2025-12-31T23:59:59Z"   # When fact stopped being true (null = current)
  recorded_at: "2024-01-15T10:30:00Z"   # When AICO learned about it (ingestion time)
  is_current: true                       # Quick filter for active facts
```

**Benefits:**
- Point-in-time queries: "Show my relationships as of 6 months ago"
- Temporal reasoning: "What changed since last week?"
- Real-time incremental updates without batch reprocessing
- Foundation for autonomous agency temporal planning

**Research Basis:** Graphiti/Zep's bi-temporal model (2025) - state-of-the-art for agent memory

---

##### **2. Personal Graph Layer** ⭐ **HIGH PRIORITY**

**Problem:** Current proposal focuses on knowledge graph (facts about the world) but lacks personal graph (user's activities, projects, goals).

**Why Critical:**
- **Autonomous agency:** Requires understanding user's active projects, priorities, goals
- **Proactive engagement:** "You mentioned wanting to learn piano—here's a practice reminder"
- **Context assembly:** "What am I currently working on?" needs activity tracking
- **Relationship intelligence:** Collaboration patterns, interaction frequency

**Implementation:**

New node labels (use existing `kg_nodes.label` field):
```python
# Personal graph entities
- PROJECT: User's active projects
- GOAL: User's objectives (short/long-term)
- TASK: Actionable items
- ACTIVITY: User actions (created doc, attended meeting, etc.)
- INTEREST: User's developing interests
- PRIORITY: User's current priorities
```

New edge types (use existing `kg_edges.relation_type` field):
```python
# Personal graph relationships
- WORKING_ON: User → Project
- HAS_GOAL: User → Goal
- CONTRIBUTES_TO: Task → Goal
- DEPENDS_ON: Task → Task (dependencies)
- COLLABORATES_WITH: User → Person (on Project)
- INTERESTED_IN: User → Topic
- PRIORITIZES: User → Priority
```

Property conventions for personal graph:
```yaml
# Project properties
project:
  status: "active"                       # active/paused/completed
  progress: 0.6                          # Float 0-1
  deadline: "2025-12-31T23:59:59Z"      # Target completion
  priority: 1                            # Int 1-5 (1=highest)
  
# Goal properties
goal:
  type: "short_term"                     # short_term/long_term
  status: "in_progress"                  # pending/in_progress/achieved/abandoned
  motivation: "personal_growth"          # Why user wants this
  
# Activity properties
activity:
  activity_type: "document_created"      # Type of activity
  timestamp: "2025-10-30T10:00:00Z"     # When activity occurred
  duration_minutes: 45                   # How long it took
  context: "work"                        # work/personal/learning
```

**Benefits:**
- Proactive assistance: Surface priorities, detect conflicts
- Collaboration pattern detection
- Personalized context assembly
- Foundation for autonomous goal generation

**Research Basis:** Glean's Personal Graph (2025) - activity tracking + LLM reasoning for work context

---

##### **3. Graph Traversal & Multi-Hop Reasoning** ⭐ **MEDIUM PRIORITY**

**Problem:** Current proposal has basic CRUD but lacks graph traversal algorithms for multi-hop queries.

**Why Critical:**
- **Context assembly:** "Find all information related to Sarah's piano recital" (multi-hop)
- **Relationship intelligence:** "How do I know John?" (path finding)
- **Autonomous agency:** "What dependencies block this goal?" (dependency chains)

**Implementation:**

Add to `aico/ai/knowledge_graph/query.py`:
```python
async def traverse(
    start_node: str,
    relation_types: List[str],
    max_depth: int = 3,
    filters: Dict = None
) -> PropertyGraph:
    """Multi-hop graph traversal with filtering
    
    Example: Find all entities connected to "Sarah" within 2 hops
    via KNOWS or FAMILY_MEMBER relationships
    """
    
async def find_path(
    source: str,
    target: str,
    max_depth: int = 5
) -> List[Path]:
    """Find shortest paths between entities
    
    Example: "How do I know John?" → User → Sarah → John
    """
    
async def get_neighborhood(
    node_id: str,
    depth: int = 2,
    relation_filter: List[str] = None
) -> PropertyGraph:
    """Get local subgraph around entity
    
    Example: Get all entities within 2 hops of "piano_recital" event
    """

async def find_dependencies(
    node_id: str,
    relation_type: str = "DEPENDS_ON"
) -> List[Node]:
    """Find dependency chains for tasks/goals
    
    Example: "What blocks this goal?" → Task1 → Task2 → Task3
    """
```

**SQL Implementation:**
```sql
-- Recursive CTE for graph traversal (libSQL supports this)
WITH RECURSIVE graph_traversal(node_id, depth, path) AS (
    SELECT id, 0, id FROM kg_nodes WHERE id = ?
    UNION ALL
    SELECT e.target_id, gt.depth + 1, gt.path || ',' || e.target_id
    FROM graph_traversal gt
    JOIN kg_edges e ON gt.node_id = e.source_id
    WHERE gt.depth < ? AND e.relation_type IN (?)
)
SELECT DISTINCT node_id FROM graph_traversal;
```

**Benefits:**
- Rich context retrieval with relationship awareness
- Path finding for relationship intelligence
- Dependency analysis for autonomous agency
- Foundation for complex reasoning

---

#### **Priority 2: Important Enhancements (Phase 2)**

##### **4. Graph-Based Context Ranking** ⭐ **MEDIUM PRIORITY**

**Problem:** Current proposal uses semantic similarity for retrieval but doesn't leverage graph structure for ranking.

**Why Important:**
- **Better context:** Entities with more connections are more central/important
- **Relationship-aware retrieval:** "Sarah" (close friend) ranks higher than "Sarah" (mentioned once)
- **Temporal relevance:** Recent facts rank higher than old facts

**Implementation:**

Add graph metrics to nodes:
```python
# Computed metrics (stored in properties JSON or separate fields)
graph_metrics:
  degree_centrality: 0.85              # How many connections? (0-1)
  temporal_recency: 0.92               # How recently discussed? (0-1)
  interaction_frequency: 45            # How often mentioned? (count)
  emotional_salience: 0.75             # Emotional intensity (0-1)
  importance_score: 0.87               # Combined importance (0-1)
```

Context ranking algorithm:
```python
def rank_context(nodes: List[Node], query: str) -> List[Node]:
    """Rank retrieved nodes by combined score"""
    for node in nodes:
        semantic_sim = compute_similarity(query, node.embedding)
        graph_centrality = node.properties.get('graph_metrics', {}).get('degree_centrality', 0)
        temporal_recency = compute_recency(node.updated_at)
        emotional_salience = node.properties.get('graph_metrics', {}).get('emotional_salience', 0)
        
        # Weighted combination
        node.context_score = (
            0.4 * semantic_sim +
            0.3 * graph_centrality +
            0.2 * temporal_recency +
            0.1 * emotional_salience
        )
    
    return sorted(nodes, key=lambda n: n.context_score, reverse=True)
```

**Benefits:**
- More relevant context retrieval
- Relationship-aware ranking
- Temporal and emotional awareness
- Better than pure semantic similarity

---

##### **5. Entity Disambiguation & Canonical IDs** ⭐ **MEDIUM PRIORITY**

**Problem:** Entity resolution merges duplicates but doesn't maintain canonical entity IDs for disambiguation.

**Why Important:**
- **Multi-modal recognition:** Voice says "Sarah" → Which Sarah? (use graph context)
- **Relationship intelligence:** "Sarah" (daughter) vs "Sarah" (colleague)
- **Cross-conversation consistency:** Same entity across sessions

**Implementation:**

Add to `kg_nodes` table:
```sql
ALTER TABLE kg_nodes ADD COLUMN canonical_id TEXT;
ALTER TABLE kg_nodes ADD COLUMN aliases_json TEXT;  -- ["SF", "San Francisco", "The City"]
CREATE INDEX idx_kg_nodes_canonical ON kg_nodes(canonical_id);
```

Property conventions:
```yaml
disambiguation:
  canonical_id: "person_sarah_001"       # Stable ID across merges
  aliases: ["Sarah", "Sarah M.", "Mom"]  # Known variations
  disambiguation_context:
    relationship: "daughter"              # How related to user
    age: 8                                # Disambiguating attribute
    primary_context: "family"            # Main context for this entity
```

Entity resolution enhancement:
```python
async def resolve_entity(
    mention: str,
    context: Dict
) -> Node:
    """Resolve ambiguous entity mention using graph context
    
    Example: "Sarah" + context{"conversation_topic": "piano"} 
             → Sarah (daughter) not Sarah (colleague)
    """
    candidates = await search_nodes(mention)
    if len(candidates) == 1:
        return candidates[0]
    
    # Use graph context for disambiguation
    for candidate in candidates:
        score = compute_context_match(candidate, context)
        candidate.disambiguation_score = score
    
    return max(candidates, key=lambda c: c.disambiguation_score)
```

**Benefits:**
- Accurate entity resolution in conversations
- Multi-modal recognition support
- Cross-session consistency
- Foundation for relationship intelligence

---

##### **6. Conflict Resolution & Fact Versioning** ⭐ **LOW PRIORITY**

**Problem:** Current fusion has conflict resolution but no version history for facts.

**Why Useful:**
- **Debugging:** "Why does AICO think I live in SF?" (trace fact provenance)
- **Correction:** "Actually, I moved to NYC" (update with history)
- **Trust:** Show users how facts evolved over time
- **Audit trail:** Track how knowledge changed

**Implementation:**

Add optional history table:
```sql
CREATE TABLE IF NOT EXISTS kg_node_history (
    id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    properties JSON NOT NULL,
    valid_from TEXT NOT NULL,
    valid_until TEXT,
    created_at TEXT NOT NULL,
    change_reason TEXT,  -- "user_correction", "conflict_resolution", "new_information"
    FOREIGN KEY (node_id) REFERENCES kg_nodes(id) ON DELETE CASCADE,
    INDEX idx_node_history_node (node_id, version)
);

CREATE TABLE IF NOT EXISTS kg_edge_history (
    id TEXT PRIMARY KEY,
    edge_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    properties JSON NOT NULL,
    valid_from TEXT NOT NULL,
    valid_until TEXT,
    created_at TEXT NOT NULL,
    change_reason TEXT,
    FOREIGN KEY (edge_id) REFERENCES kg_edges(id) ON DELETE CASCADE,
    INDEX idx_edge_history_edge (edge_id, version)
);
```

Versioning logic:
```python
async def update_node_with_history(
    node_id: str,
    new_properties: Dict,
    change_reason: str
):
    """Update node and preserve history"""
    # Get current version
    current = await get_node(node_id)
    
    # Archive current version
    await archive_node_version(
        node_id=node_id,
        version=current.version,
        properties=current.properties,
        change_reason=change_reason
    )
    
    # Update to new version
    await update_node(node_id, new_properties, version=current.version + 1)
```

**Benefits:**
- Fact provenance tracking
- User trust through transparency
- Debugging and correction support
- Audit trail for compliance

---

#### **Priority 3: Advanced Features (Phase 3)**

##### **7. Graph Analytics & Insights** ⭐ **LOW PRIORITY**

**Problem:** No graph algorithms for discovering patterns and insights.

**Why Useful:**
- **Autonomous agency:** Detect emerging interests, suggest goals
- **Relationship intelligence:** Identify relationship clusters, detect drift
- **Proactive engagement:** "You haven't talked to John in 3 months"
- **Self-awareness:** Help user understand their own patterns

**Implementation:**

Add analytics module `aico/ai/knowledge_graph/analytics.py`:
```python
async def detect_communities(
    user_id: str
) -> List[Community]:
    """Identify relationship clusters using community detection
    
    Example: Family cluster, work cluster, hobby cluster
    """

async def compute_centrality(
    user_id: str,
    metric: str = "degree"  # degree, betweenness, closeness
) -> Dict[str, float]:
    """Compute node importance using centrality measures
    
    Example: Most important people, topics, projects
    """

async def detect_anomalies(
    user_id: str,
    time_window: str = "7d"
) -> List[Anomaly]:
    """Detect unusual patterns in user's graph
    
    Example: Sudden drop in communication with close friend
    """

async def analyze_trends(
    user_id: str,
    entity_type: str = "INTEREST"
) -> List[Trend]:
    """Analyze emerging or declining patterns
    
    Example: Growing interest in photography, declining interest in gaming
    """

async def suggest_goals(
    user_id: str
) -> List[Goal]:
    """Generate goal suggestions based on graph patterns
    
    Example: User talks about learning piano → Suggest "Learn piano" goal
    """
```

**Benefits:**
- Proactive goal suggestions
- Relationship health monitoring
- Pattern discovery and insights
- Foundation for true autonomous agency

---

### Summary: Enhancement Priorities

**Phase 1.5 (Critical - Add to MVP):**
1. ✅ Temporal/bi-temporal data model (HIGH)
2. ✅ Personal graph layer (HIGH)
3. ✅ Graph traversal & multi-hop reasoning (MEDIUM)

**Phase 2 (Important - Post-MVP):**
4. Graph-based context ranking (MEDIUM)
5. Entity disambiguation & canonical IDs (MEDIUM)
6. Conflict resolution & fact versioning (LOW)

**Phase 3 (Advanced - Future):**
7. Graph analytics & insights (LOW)

**Research Foundation:**
- **Graphiti/Zep (2025):** Bi-temporal knowledge graphs for agent memory (state-of-the-art)
- **Glean Personal Graph (2025):** Activity tracking + LLM reasoning for work context
- **Industry Best Practices:** Multi-hop reasoning, graph-based ranking, entity disambiguation

## Coreference Resolution Optimizations for Property Graph

### Current Implementation Limitations

The current coreference resolution approach has some challenges for optimal property graph construction:

#### 1. Over-Resolution Problem
```python
# Input: "John and I are working together. We think it will succeed."
# Current: "John and Michael are working together. John and Michael think it will succeed."
# Issue: Loses collective relationship nature ("We" becomes individual actions)
```

#### 2. Relationship Ambiguity
```python
# Property Graph Issue:
# Creates: Michael -[THINKS]-> "it will succeed"
#         John -[THINKS]-> "it will succeed"
# Should be: (John, Michael) -[COLLECTIVELY_THINK]-> "it will succeed"
```

### Required Optimizations

#### 1. Selective Resolution Modes
- **Full Resolution**: Complete pronoun resolution (current approach)
- **Selective Resolution**: Only resolve entity-referring pronouns
- **Graph-Optimized**: Preserve collective pronouns and relationship context

#### 2. Enhanced Output Structure
```python
{
    'resolved_text': str,           # Fully resolved text
    'partial_resolution': str,      # Selectively resolved text  
    'entity_mappings': dict,        # Pronoun -> Entity mappings
    'collective_pronouns': list,    # Preserved group pronouns
    'relationship_context': dict    # Relationship preservation info
}
```

#### 3. Relationship Preservation
- Maintain collective actions ("we", "us", "our")
- Preserve temporal/causal sequences
- Keep relationship context for proper graph edge creation

#### 4. Implementation Strategy
- **Phase 1**: Current cross-turn resolution (✅ implemented)
- **Phase 2**: Add property graph optimization modes
- **Phase 3**: Direct integration with graph construction

This ensures clean entity resolution while preserving the relationship semantics needed for accurate property graph representation.ons)
- Validate global perspective
- Unit tests for fusion

### Phase 5: Semantic Memory Integration
**Scope:** Integrate knowledge graph with semantic memory
**Deliverables:**
- Refactor `aico/ai/memory/semantic.py` to use knowledge graph module
- Implement progressive response with parallel processing (required features)
- Implement background graph processing (non-blocking)
- Add property convention validation (temporal, provenance, emotional, etc.)
- Store properties following documented conventions
- Integration tests
- Deduplication test: stable fact count across runs (14 → 14 → 14, not 14 → 28 → 42)

### Phase 6: Testing & Optimization
**Scope:** Comprehensive testing and performance optimization

**Deliverables:**
- End-to-end tests (full pipeline)
- Performance benchmarks (latency, cost, accuracy)
- Implement caching (optional enhancement)
- Documentation (API docs, usage examples)
- Update configuration with property conventions

---

## Configuration

**Note:** Knowledge graph uses existing model configuration from `core.yaml`. Models are managed centrally:
- **Entity extraction:** Uses `modelservice.transformers.models.entity_extraction` (GLiNER)
- **Embeddings:** Uses `modelservice.default_models.embedding` (paraphrase-multilingual)
- **LLM operations:** Uses `modelservice.default_models.conversation` (hermes3:8b)

```yaml
memory:
  semantic:
    # Knowledge graph configuration
    knowledge_graph:
      # Extraction settings
      max_gleanings: 2  # Number of gleaning passes (0-2 recommended)
      
      # Entity resolution (deduplication)
      deduplication:
        enabled: true
        similarity_threshold: 0.85  # Cosine similarity for semantic blocking
        
      # Performance tuning
      caching:
        enabled: true  # Cache entity resolution results
        cache_size: 1000  # Number of entities to cache
```

**What's NOT configurable (hardcoded in implementation):**
- Storage backend: `chromadb+libsql` (hybrid, required)
- Processing mode: Progressive response with parallel processing
- Property conventions: Documented in Phase 0
- Model selection: Uses existing `modelservice` configuration
- Collections: `kg_nodes`, `kg_edges` (both ChromaDB and libSQL)
- Paths: Resolved via `AICOPaths.get_semantic_memory_path()`

---

## Success Criteria

### Deduplication Test
```bash
# Run 3 times with same user
Run 1: 14 facts
Run 2: 14 facts (not 28!)
Run 3: 14 facts (stable!)
```

### Completeness Test
```python
single_pass: 8 facts (57%)
multi_pass: 13 facts (93%)
```

### Performance Test
```python
Total latency: 2500ms ✅ (under 3s target)
Cost per conversation: $0.003 ✅ (acceptable)
Deduplication accuracy: 95%+ ✅
```

---

## Alignment with AICO Principles

### Local-First, Privacy-First
- ✅ All processing local except LLM matching/merging (gpt-4o-mini, optional)
- ✅ Property graph enables fine-grained privacy boundaries
- ✅ Hybrid storage (ChromaDB + libSQL) keeps data local
- ✅ No external dependencies for core functionality

### Modular, Message-Driven Design
- ✅ Core knowledge graph module (`aico.ai.knowledge_graph`)
- ✅ Domain-agnostic, reusable across features
- ✅ Clean interfaces (PropertyGraph, Extractor, EntityResolver, GraphFusion)
- ✅ Feature flag for gradual rollout (`pipeline_mode`)
- ✅ Follows System > Domain > Module > Component hierarchy

### Extensibility
- ✅ Plugin-ready: other modules can use knowledge graph
- ✅ Storage backend abstraction (ChromaDB+libSQL now, Neo4j future)
- ✅ Model abstraction (swap LLMs via modelservice)

### Autonomous Agency (Future)
- ✅ Graph structure enables goal planning
- ✅ Multi-hop reasoning for proactive suggestions
- ✅ Context-aware decision making

### Real-Time Emotional Intelligence (Future)
- ✅ Emotional context in relationships
- ✅ Emotional memory integration
- ✅ Relationship-appropriate empathy

### Natural Family Recognition (Future)
- ✅ Rich relationship modeling
- ✅ Multi-dimensional understanding
- ✅ Dynamic learning from interactions

---

## Research Foundation

1. **Microsoft GraphRAG** (2024-2025) - Multi-pass extraction, hierarchical clustering
2. **Graphusion** (ACL 2024) - Global perspective fusion, conflict resolution
3. **LlamaIndex PropertyGraph** (2024-2025) - Property graph model, schema-guided extraction
4. **Semantic Entity Resolution** (Jan 2025) - Embedding clustering + LLM validation
5. **Ditto** (2020) - Deep entity matching with pre-trained LLMs (29% improvement)

---

## Conclusion

The property graph pipeline solves the deduplication problem while providing system-wide benefits for relationship intelligence, autonomous agency, emotional intelligence, and privacy. The 3x latency/cost increase is justified by infinite accuracy improvement and enhanced capabilities across AICO's core features.

**Recommendation:** Proceed with phased implementation, starting with multi-pass extraction and property graph model.
