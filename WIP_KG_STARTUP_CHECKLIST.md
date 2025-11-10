# Knowledge Graph - Startup Checklist

**Date:** 2025-11-10  
**Status:** ✅ READY FOR TESTING

---

## Pre-Startup Verification

### ✅ Dependencies
- [x] `hnswlib==0.8.0` installed via `uv sync`
- [x] All imports verified (`Edge` added to entity_resolution.py)

### ✅ Code Changes
- [x] HNSW entity resolution implemented (O(N log M))
- [x] LLM batch matching implemented (single call)
- [x] Dead code removed (`_cosine_similarity`)
- [x] Critical failures raise exceptions (no silent data loss)
- [x] Degraded modes are LOUD (80-char banners)
- [x] Comprehensive logging and print statements

### ✅ KG Extraction ENABLED
- [x] `/shared/aico/ai/memory/manager.py` line 645: `if self._kg_initialized and role == "user"`
- [x] Entity resolution enabled (lines 910-927)
- [x] Graph fusion skipped (not critical for testing)

### ✅ KG Retrieval ENABLED
- [x] `/shared/aico/ai/memory/context/assembler.py` line 144: `if self.kg_storage and self.kg_modelservice`

---

## Expected Behavior on Startup

### First User Message
```
🕸️ [KG_CHECK] Checking if KG extraction should run: kg_initialized=True, role=user
🕸️ [KG] ✅ Triggering background extraction for user message (len: 50)
🕸️ [KG] 🚀 Background extraction task STARTED for user test_user_123
🕸️ [KG] Calling extractor.extract()...
🕸️ [KG] Extraction complete: 5 nodes, 3 edges

🔍 [ENTITY_RESOLVER] Starting resolution for 5 new entities
🔍 [ENTITY_RESOLVER] Step 1: Indexing 0 existing nodes
🔍 [ENTITY_RESOLVER] HNSW index is empty, no existing nodes to compare against
🔍 [ENTITY_RESOLVER] No duplicate candidates found, adding 5 new nodes to index
🔍 [ENTITY_RESOLVER] Added 5 nodes to HNSW index (total indexed: 5)

🕸️ [KG] Saving graph to storage...
🕸️ [KG] ✅ Knowledge graph saved successfully!
```

### Second User Message (with duplicates)
```
🕸️ [KG] Extraction complete: 8 nodes, 5 edges

🔍 [ENTITY_RESOLVER] Starting resolution for 8 new entities
🔍 [ENTITY_RESOLVER] Step 1: Indexing 5 existing nodes
🔍 [ENTITY_RESOLVER] All 5 existing nodes already indexed
🔍 [ENTITY_RESOLVER] Step 2: HNSW search (O(N log M) complexity)
🔍 [ENTITY_RESOLVER] Searching for k=5 nearest neighbors per node (indexed: 5)
🔍 [ENTITY_RESOLVER] HNSW search complete: 3 candidates above threshold
🔍 [ENTITY_RESOLVER] Step 3: LLM batch matching (3 pairs in single call)
🔍 [ENTITY_RESOLVER] Sending 3 pairs to LLM (single batch call)
🔍 [ENTITY_RESOLVER] LLM batch matching result: 2/3 confirmed as duplicates
🔍 [ENTITY_RESOLVER] Step 4: Merging 2 duplicate pairs
🔍 [ENTITY_RESOLVER] Building merge groups from 2 duplicate pairs
🔍 [ENTITY_RESOLVER] Created 2 merge groups
🔍 [ENTITY_RESOLVER] ✅ Resolution complete: 8 → 6 nodes
🔍 [ENTITY_RESOLVER] Added 6 nodes to HNSW index (total indexed: 11)
```

---

## What to Watch For

### ✅ Success Indicators
- `✅ Knowledge graph saved successfully!`
- `✅ Resolution complete: X → Y nodes` (Y ≤ X)
- `Added N nodes to HNSW index (total indexed: M)` (M grows incrementally)
- No exceptions or 🚨 alerts

### ⚠️ Warning Indicators (Degraded Mode)
```
================================================================================
🔍 [ENTITY_RESOLVER] 🚨 LLM BATCH MATCHING TIMEOUT after 30.0s
🔍 [ENTITY_RESOLVER] DEGRADED MODE: Accepting all candidates
🔍 [ENTITY_RESOLVER] ⚠️  PRECISION DEGRADED: ~85-90% accuracy
================================================================================
```
**Action:** Check LLM performance, consider increasing timeout in config

### 🚨 Critical Failures
```
🔍 [ENTITY_RESOLVER] 🚨 CRITICAL: No embeddings generated for 5 nodes
RuntimeError: CRITICAL: No embeddings generated for 5 nodes - modelservice failure
```
**Action:** Check modelservice logs, verify embedding model loaded

---

## Performance Expectations

| Metric | Target | Alert If |
|--------|--------|----------|
| **First message** | 1-5s | >10s |
| **Subsequent messages** | 1-8s | >15s |
| **Entity extraction** | 10-20 entities | >50 entities (check extraction quality) |
| **HNSW search** | <100ms | >500ms |
| **LLM batch matching** | 2-5s | >30s (timeout) |
| **Total KG processing** | 3-10s | >30s |

---

## Startup Commands

```bash
# Terminal 1: Start backend
cd /Users/mbo/Documents/dev/aico
uv run python -m backend.main

# Watch for:
# - "🕸️ [KG] Initializing knowledge graph components..."
# - "🕸️ [KG] ✅ Knowledge graph components initialized successfully"
# - "🔍 [ENTITY_RESOLVER] Initialized with HNSW index"
```

---

## Test Scenario

### Message 1: Create entities
```
User: "I'm working on the website redesign project with Sarah"
```
**Expected:** Extract entities: "website redesign project", "Sarah"

### Message 2: Duplicate entities
```
User: "The website redesign is going well, Sarah is doing great work"
```
**Expected:** 
- Extract: "website redesign", "Sarah" 
- Resolve: Merge duplicates (2 → 1 for each)
- Result: No duplicate entities in graph

### Message 3: Verify retrieval
```
User: "What projects am I working on?"
```
**Expected:**
- KG context retrieval finds "website redesign project"
- AI response mentions the project

---

## Rollback Plan

If critical issues occur:

```bash
# Disable KG extraction
# Edit: /shared/aico/ai/memory/manager.py line 645
if False and self._kg_initialized and role == "user":  # DISABLED

# Disable KG retrieval  
# Edit: /shared/aico/ai/memory/context/assembler.py line 144
if False and self.kg_storage and self.kg_modelservice:  # DISABLED
```

---

## Status

- ✅ Code ready
- ✅ Dependencies installed
- ✅ KG extraction enabled
- ✅ KG retrieval enabled
- ✅ Logging comprehensive
- ✅ Error handling robust
- 🟢 **READY TO START BACKEND**
