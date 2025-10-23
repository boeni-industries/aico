# AICO Chat Bubble Features

**Version:** 2.0 | **Date:** Oct 23, 2025 | **Status:** Refined

## Design Principles

- **Sub-500ms interactions** - Fast, non-blocking
- **Ambient emotional feedback** - Avatar presence, not theatrical interruptions  
- **Progressive disclosure** - Actions hidden until needed
- **Relationship-first** - Natural conversation dynamics, not AI training

## Actions

### User Messages: `[Copy] | [Remember]`
### AICO Messages: `[Copy] | [Remember] [Regenerate]`

---

## 1. Copy Text ✅ Implemented

- Copies message to clipboard
- Inline checkmark confirmation (700ms)
- Icon: 📋 → ✓ with accent color background

---

## 2. Remember This 🔨 To Implement

### What It Does

**User Messages:**
- Creates knowledge graph node with `user_curated: true` property
- Stored as entity in semantic memory with elevated confidence (1.0)
- Marked as immutable fact (won't be overwritten by auto-extraction)
- Example: "I'm allergic to shellfish" → PERSON node with allergy property, prioritized in retrieval

**AICO Messages:**
- Stores conversation segment in ChromaDB with boosted relevance
- Creates knowledge graph node referencing valuable insight
- Easier retrieval via semantic search with higher ranking
- Example: Career advice → bookmarked segment with high confidence score

### Why Users Want It

**Emotional:** Creates shared memory moments - "This mattered to me, now it matters to us"  
**Practical:** Ensures critical info isn't forgotten + bookmarks insights without full export

**vs Automatic Semantic Memory:**
- **Automatic**: Background extraction from conversations (multi-pass, entity resolution)
- **Remember This**: User-curated importance signal (explicit bookmark, immutable)
- **Difference**: User-marked facts get `user_curated: true` + confidence: 1.0 + immutable flag
- **Storage**: Both use knowledge graph infrastructure (ChromaDB + libSQL)

### Future: Knowledge Graph Enhancement

**Current (V3):** Simple fact storage in `facts_metadata` table  
**Future (Knowledge Graph):** Rich entity-relationship graph with deduplication

**What Changes:**
- Facts become **property graph nodes** (entities with typed properties)
- Automatic **entity resolution** prevents duplicates ("SF" = "San Francisco")
- **Multi-pass extraction** captures 90%+ of information (vs 60-70% single-pass)
- **Graph fusion** discovers implicit relationships across conversations

**User-Curated Facts in Knowledge Graph:**
```python
# User marks: "I'm allergic to shellfish"
Node(
  label="PERSON",
  properties={
    "name": "User",
    "allergy": "shellfish",
    "user_curated": true,  # Marked by user
    "confidence": 1.0,      # Immutable
    "extraction_method": "manual_bookmark"
  }
)
```

**Benefits:**
- No duplicates ("shellfish allergy" = "allergic to shellfish")
- Richer representation (entity properties vs flat text)
- Better retrieval (graph traversal + semantic search)
- Future-proof for relationship intelligence, emotional memory

### Technical Implementation

**Current (V3) - Simple Facts:**
```sql
-- Create fact entry in facts_metadata
INSERT INTO facts_metadata (
  fact_id, user_id, fact_type, category, confidence,
  is_immutable, content, source_conversation_id,
  source_message_id, extraction_method
) VALUES (
  uuid(), user_id, 'user_curated', 'important',
  1.0, TRUE, message_content, conversation_id,
  message_id, 'manual_bookmark'
);

-- Store in ChromaDB
collection.add(
  documents=[content],
  metadatas=[{"user_curated": true, "importance": "high"}],
  ids=[fact_id]
);
```

**Future - Knowledge Graph:**
```python
# Extract entity from user message
node = Node(
  label="PERSON",
  properties={
    "name": extract_name(message),
    "user_curated": true,
    "confidence": 1.0,
    "extraction_method": "manual_bookmark"
  }
)

# Store in hybrid backend (ChromaDB + libSQL)
await knowledge_graph.add_node(
  node=node,
  user_id=user_id,
  conversation_id=conversation_id
)

# Entity resolution prevents duplicates
await entity_resolver.resolve_and_merge(
  new_node=node,
  existing_nodes=user_graph
)
```

**Visual Design:**
- **Icon:** ✨ at 18px | **Color:** Purple accent (#B8A1EA)
- **Flow (200-300ms):** Click → Haptic → Purple glow → Avatar smile → ✨ indicator
- **Avatar:** Ambient only - warm smile, eyes brighten, mood ring purple

---

## 3. Regenerate Response 🔨 To Implement

### What It Does

1. **Preserves context:** Working memory (LMDB) + conversation history intact
2. **Resends to LLM:** Same user message with full context via modelservice
3. **New generation:** Different sampling/temperature creates variation
4. **Updates storage:** Replaces message in working memory + episodic store
5. **Optional history:** "Show previous" keeps old response accessible

### Why Users Want It

- **Misunderstanding:** "Tell me about Python" → 🐍 snakes instead of programming
- **Too generic:** "That's interesting!" → wants deeper engagement  
- **Wrong tone:** Too formal/casual for the moment
- **Incomplete:** Cut off or surface-level answer

### Why Better Than "Not Quite" Feedback

**"Not Quite" (rejected):** Click → AICO asks "What do you mean?" → User explains → Extra back-and-forth → Feels like training AI

**Regenerate:** One click → Immediate new attempt → No explanation needed → Feels like "Let's try that again" with a friend

### Technical Implementation

**Backend Flow:**
```python
# 1. Get current context from working memory (LMDB)
context = await working_memory.get_context(conversation_id)

# 2. Remove last AICO message from context
context.messages = context.messages[:-1]

# 3. Regenerate via modelservice with same context
response = await modelservice.generate_completion(
    messages=context.messages,
    temperature=0.8,  # Slight randomness for variation
    model=config.conversation_model
)

# 4. Update working memory + episodic store
await working_memory.update_message(message_id, response)
await episodic_store.replace_message(message_id, response)
```

**Visual Design:**
- **Icon:** 🔄 at 18px | **Color:** Accent color
- **Flow:** Click → Dim previous (200ms) → Thinking indicator → Stream new response
- **History:** Optional "Show previous" link (subtle, bottom of message)

---

## Backend Integration

**Remember This:**
```
POST /api/v1/memory/facts/create
Payload: {
  messageId: string,
  conversationId: string,
  content: string,
  factType: "user_curated",
  isImmutable: true
}
Response: { factId, stored: true }
```

**Regenerate:**
```
POST /api/v1/conversations/{conversationId}/regenerate
Payload: {
  messageId: string,
  keepHistory: boolean
}
Response: SSE stream of new message
```

**Storage Architecture:**

**Current (V3):**
- **Working Memory:** LMDB (session context, active threads)
- **Episodic Memory:** libSQL encrypted (conversation history)
- **Semantic Memory:** ChromaDB (vector embeddings) + libSQL (facts_metadata)
- **Facts Table:** `facts_metadata` with confidence, immutability, provenance

**Future (Knowledge Graph):**
- **Working Memory:** LMDB (unchanged)
- **Episodic Memory:** libSQL encrypted (unchanged)
- **Semantic Memory:** Knowledge graph with entity resolution
  - **ChromaDB:** `kg_nodes` + `kg_edges` collections (semantic search)
  - **libSQL:** `kg_nodes` + `kg_edges` tables (graph traversal, property queries)
  - **Property Indexing:** `kg_node_properties` + `kg_edge_properties` (fast filtering)
- **Migration:** `facts_metadata` → `kg_nodes` (schema v7)

**Conversation Export:** ✅ Already implemented (top bar, not message bubbles)

---

## Implementation Notes

### Current State (V3)
- Simple fact storage in `facts_metadata` table
- ChromaDB for vector embeddings
- No deduplication (same fact extracted multiple times creates duplicates)
- User-curated facts marked with `is_immutable: true`

### Future Enhancement (Knowledge Graph)
- Property graph with entity resolution (prevents duplicates)
- Multi-pass extraction (90%+ information capture)
- Graph fusion (discovers implicit relationships)
- Richer representation (entities + relationships vs flat facts)
- **Migration path:** `facts_metadata` → `kg_nodes` (schema v7)
- **Timeline:** Proposed, not yet implemented

### Remember This Implementation Path

**Phase 1 (Current):** Implement with `facts_metadata` table
- Quick to implement, uses existing infrastructure
- Good enough for MVP, validates user need
- Known limitation: potential duplicates

**Phase 2 (Future):** Migrate to knowledge graph
- Automatic migration from `facts_metadata` → `kg_nodes`
- User-curated facts preserve `user_curated: true` property
- No user-facing changes (same UX, better backend)
- Benefits: deduplication, richer representation, graph queries

---

## Key Insight

Both features feel like natural relationship interactions:
- **Remember** = "This moment matters to our relationship"
- **Regenerate** = "Let's try that again" (like asking a friend to rephrase)

Emotional design through **ambient presence** (avatar expressions, subtle glows), not **theatrical interruptions** (particles, multi-phase animations, forced feedback).

---