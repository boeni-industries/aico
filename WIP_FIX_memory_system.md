# Memory System & Performance Optimization Plan

**Status:** Research Complete - Ready for Implementation  
**Date:** 2025-11-09  
**Priority:** HIGH - Core system performance

---

## Current Issues (Root Causes)

### 1. Embedding Request Queue Overload
- **Symptom:** 60s timeouts on embedding requests
- **Root Cause:** Ollama processes requests sequentially. Every conversation turn triggers:
  - User message embedding (~100ms)
  - AI response embedding (~100ms)
  - LLM generation (~3-5s)
  - Background semantic searches (more embeddings)
- **Impact:** Queue fills up, background tasks block user-facing requests

### 2. KG Extraction Causing Embedding Flood
- **Symptom:** KG extraction triggers 100+ embedding requests per message
- **Root Cause:** Entity resolution uses N² embedding comparisons
  - GLiNER extracts 10 entities
  - Each entity compared to all existing entities
  - 10 entities × 10 comparisons = 100 embedding requests
- **Impact:** Modelservice queue overload

### 3. Semantic Memory Storage Blocking
- **Symptom:** Background timeouts after response delivered
- **Root Cause:** `store_message()` awaits `get_embeddings()` synchronously
- **Impact:** Even "background" storage blocks conversation flow

### 4. No Request Queue Management
- **Root Cause:** Modelservice has no queue visibility or prioritization
- **Impact:** Low-priority background tasks block high-priority user requests

---

## Research-Backed Solutions

### Key Findings:
1. **Ollama 0.2+** has native concurrency with configurable queue management
2. **Ollama batch API** (`/api/embed`) accepts array of texts
3. **asyncio.PriorityQueue** is production-ready for request prioritization
4. **EAGER research** shows embedding caching + TF-IDF outperforms pure embeddings
5. **aiobreaker** library provides async circuit breaker with Redis backing

---

## PHASE 1: Immediate Fixes (Tonight/Tomorrow)

### 1.1 Implement Request Priority Queue in Modelservice
**Location:** `modelservice/src/services/request_handler.py`

**Implementation:**
```python
import asyncio
from enum import IntEnum

class RequestPriority(IntEnum):
    HIGH = 0    # LLM chat requests (user-facing)
    MEDIUM = 1  # Context retrieval embeddings
    LOW = 2     # Background storage embeddings

# Replace FIFO queue with priority queue
self.request_queue = asyncio.PriorityQueue()

# Enqueue with priority
await self.request_queue.put((priority, timestamp, request))
```

**Effort:** 4 hours  
**Impact:** Prevents background tasks from blocking user requests

---

### 1.2 Batch Embedding Requests
**Location:** `modelservice/src/services/embedding_service.py`

**Implementation:**
- Use Ollama's `/api/embed` endpoint (supports array input)
- Collect requests for 100ms window
- Send single batch (max 50 texts)
- Distribute results to waiting coroutines

**Effort:** 2 hours  
**Impact:** Reduces queue pressure by 10-50×

---

### 1.3 Implement Embedding Cache with SQLite
**Location:** `shared/aico/ai/embeddings/cache.py` (new file)

**Schema:**
```sql
CREATE TABLE embedding_cache (
    text_hash TEXT PRIMARY KEY,
    text TEXT,
    model TEXT,
    embedding BLOB,
    created_at INTEGER,
    access_count INTEGER
);
CREATE INDEX idx_model_hash ON embedding_cache(model, text_hash);
```

**Strategy:**
- SHA256 hash of `(model, text)` as key
- LRU eviction at 100K entries
- 99% hit rate for entity resolution

**Effort:** 3 hours  
**Impact:** Eliminates redundant embedding computation

---

## PHASE 2: Structural Improvements (This Week)

### 2.1 Defer Semantic Memory Storage
**Location:** `shared/aico/ai/memory/semantic.py`

**Implementation:**
```python
# Fire-and-forget with retry
asyncio.create_task(store_with_retry(message, max_retries=3))
```

**Effort:** 2 hours  
**Impact:** Eliminates blocking storage operations

---

### 2.2 Implement Circuit Breaker with aiobreaker
**Location:** `modelservice/src/services/circuit_breaker.py` (new file)

**Implementation:**
```python
from aiobreaker import CircuitBreaker
from datetime import timedelta

chat_breaker = CircuitBreaker(
    fail_max=3,
    reset_timeout=timedelta(seconds=30),
    expected_exception=TimeoutError
)

embedding_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=timedelta(seconds=60)
)
```

**Fallback Strategies:**
- Chat: Return "service busy" message
- Embeddings: Use TF-IDF similarity
- KG extraction: Skip and mark for retry

**Effort:** 3 hours  
**Impact:** Graceful degradation instead of cascading failures

---

### 2.3 Optimize KG Entity Resolution (Two-Pass EAGER Approach)
**Location:** `shared/aico/ai/knowledge_graph/resolver.py`

**Implementation:**
1. **First pass:** TF-IDF + Levenshtein distance (no embeddings)
   - Filters 90% of non-matches
   - O(N log N) complexity
2. **Second pass:** Embedding similarity for remaining 10%
   - Only candidates need embeddings
   - Reduces from 100 requests to 10

**Effort:** 4 hours  
**Impact:** 90% reduction in embedding requests for KG

---

## PHASE 3: Advanced Optimization (Next Sprint)

### 3.1 Priority Scheduling with asynkit
**Library:** `asynkit.experimental.priority`

**Features:**
- Priority inheritance (prevents priority inversion)
- Automatic priority boosting (prevents starvation)
- `PriorityTask`, `PriorityLock`, `DefaultPriorityEventLoop`

**Effort:** 4 hours  
**Impact:** Prevents low-priority tasks from holding locks

---

### 3.2 Lazy Embedding Generation with Background Worker
**Location:** `shared/aico/ai/memory/embedding_worker.py` (new file)

**Strategy:**
- Store messages with `embedding_status = 'pending'`
- Background worker processes during idle (CPU < 50%)
- Prioritize recent conversations
- Fallback to keyword search if embedding missing

**Effort:** 4 hours  
**Impact:** Defers non-critical work to idle time

---

### 3.3 Separate Embedding Model (Optional)
**Implementation:**
```bash
# Run second Ollama instance for embeddings
OLLAMA_HOST=127.0.0.1:11435 ollama serve
```

**Configuration:**
- Primary Ollama (port 11434): Chat models
- Secondary Ollama (port 11435): `nomic-embed-text:latest`

**Effort:** 2 hours  
**Impact:** Doubles throughput without hardware changes

---

### 3.4 Ollama Configuration Tuning
**Environment Variables:**
```bash
export OLLAMA_MAX_LOADED_MODELS=2  # Chat + embedding model
export OLLAMA_NUM_PARALLEL=4       # 4 parallel requests per model
export OLLAMA_MAX_QUEUE=128        # Limit queue depth
```

**Monitoring:**
- Track queue depth via health endpoint
- Reject requests when queue > 100 (fail fast)

**Effort:** 1 hour  
**Impact:** Leverage native Ollama 0.2+ concurrency

---

## Implementation Timeline

### Week 1 (Days 1-2)
- [ ] 1.1 Priority queue in modelservice (4h)
- [ ] 1.3 Embedding cache with SQLite (3h)
- [ ] 1.2 Batch embedding requests (2h)

### Week 1 (Days 3-5)
- [ ] 2.1 Defer semantic storage (2h)
- [ ] 2.2 Circuit breaker with aiobreaker (3h)
- [ ] 2.3 Two-pass KG entity resolution (4h)

### Week 2
- [ ] 3.1 asynkit priority scheduling (4h)
- [ ] 3.2 Lazy embedding worker (4h)
- [ ] 3.4 Ollama config tuning (1h)
- [ ] 3.3 *(Optional)* Separate embedding instance (2h)

**Total Effort:** ~29 hours (3.5 days focused work)

---

## Expected Results

| Metric | Current | Target |
|--------|---------|--------|
| Response time | 3-5s | < 5s (consistent under load) |
| Throughput | 1 concurrent user | 10 concurrent users |
| Timeout rate | ~30% under load | 0% |
| KG extraction | Disabled | Re-enabled without impact |

---

## Dependencies to Install

```bash
# Circuit breaker
uv add aiobreaker

# Priority scheduling (optional, Phase 3)
uv add asynkit
```

---

## Testing Strategy

1. **Load testing:** Simulate 10 concurrent conversations
2. **Timeout monitoring:** Track embedding request latency
3. **Queue depth:** Monitor modelservice queue size
4. **Cache hit rate:** Track embedding cache effectiveness
5. **KG performance:** Measure entity resolution time

---

## References

- [Ollama 0.2 Concurrency](https://medium.com/@simeon.emanuilov/ollama-0-2-revolutionizing-local-model-management-with-concurrency-2318115ce961)
- [Ollama Embedding API](https://deepwiki.com/ollama/ollama/3.3-embedding-api)
- [EAGER: Embedding-Assisted Entity Resolution](https://scads.ai/embedding-assisted-knowledge-graph-entity-resolution-eager/)
- [asyncio PriorityQueue Best Practices](https://towardsdatascience.com/unleashing-the-power-of-python-asyncios-queue-f76e3188f1c4/)
- [aiobreaker Circuit Breaker](https://github.com/arlyon/aiobreaker)
- [asynkit Priority Scheduling](https://pypi.org/project/asynkit/)

---

## Notes

- **Current workaround:** KG extraction disabled to prevent timeouts
- **Root cause:** No request prioritization + sequential Ollama processing
- **Key insight:** Ollama 0.2+ has native concurrency we're not leveraging
- **Quick win:** Embedding cache will eliminate 99% of redundant requests
- **Long-term:** Separate embedding instance doubles throughput

---

---

## Ollama Version Analysis

**Current Version:** `0.11.10`  
**Latest Version:** `0.12.10` (released 2025)  
**Status:** ⚠️ **UPDATE RECOMMENDED**

### Key Features in 0.12.x (Missing in 0.11.10):
- **Concurrency improvements** (0.2.0+)
  - `OLLAMA_MAX_LOADED_MODELS` - Control concurrent model loading
  - `OLLAMA_NUM_PARALLEL` - Parallel requests per model (default: 4)
  - `OLLAMA_MAX_QUEUE` - Queue depth limit (default: 512)
- **Batch embedding support** - `/api/embed` endpoint
- **Better memory management** - Intelligent model unloading
- **Improved error handling** - Tool call IDs, better timeouts
- **Vulkan support** - Flash attention for Intel GPUs

### Update Benefits:
1. **Native concurrency** - No need to implement external queue management
2. **Batch embeddings** - 10-50× reduction in request overhead
3. **Queue limits** - Fail fast instead of timeout
4. **Better resource management** - Automatic model unloading

### Update Command:
```bash
# Via AICO CLI
uv run aico ollama update

# Or manually
cd /Users/mbo/Library/Application\ Support/aico/bin
curl -fsSL https://ollama.com/install.sh | sh
```

### Post-Update Configuration:
```bash
# Add to modelservice environment
export OLLAMA_MAX_LOADED_MODELS=2  # Chat + embedding model
export OLLAMA_NUM_PARALLEL=4       # 4 parallel requests per model
export OLLAMA_MAX_QUEUE=128        # Limit queue to 128 (fail fast)
```

**Recommendation:** Update to 0.12.10 BEFORE implementing Phase 1. The native concurrency features will simplify our implementation and provide better performance out-of-the-box.

---

---

## ACTUAL ROOT CAUSE FOUND (2025-11-09 22:30)

**The Real Bottleneck:** Entity label correction in KG extraction

### Issue:
- Every entity goes through `correct_entity_label_semantic()` 
- Each call makes individual embedding request (~150ms)
- 20 entities × 150ms = **3 seconds of sequential embedding requests**

### Location:
`/shared/aico/ai/knowledge_graph/extractor.py` lines 360-371

### Fix Applied:
✅ **Optimization 1: Filter before calling** (5 min)
- Only call semantic correction for ambiguous labels (ENTITY, EVENT)
- Skip correction for specific labels (PERSON, ORGANIZATION, etc.)
- **Impact:** Reduces embedding requests by 50-80%

### Remaining Optimizations:
✅ **Optimization 2: Batch entity embeddings** (30 min) - DONE
- Implemented `correct_entity_labels_batch()` function
- Collects all entities needing correction
- Sends ONE batch embedding request instead of N individual requests
- **Impact:** 20 × 150ms → 1 × 500ms = 6× speedup

✅ **Optimization 3: Cache entity embeddings** (1 hour) - DONE
- Per-user entity embedding cache with TTL (1 hour)
- Automatic expiration cleanup on each request
- Cache invalidation functions: `clear_entity_embedding_cache()`, `get_cache_stats()`
- **Impact:** 80% cache hit rate = 80% fewer requests

### Cache Invalidation Strategy:
- **TTL-based:** Entries expire after 1 hour (prevents stale embeddings)
- **Per-user scoping:** Each user has separate cache (prevents cross-user pollution)
- **Automatic cleanup:** Expired entries removed on each batch request
- **Manual clear:** `clear_entity_embedding_cache(user_id)` for explicit invalidation
- **Model updates:** Call `clear_entity_embedding_cache()` when embedding model changes

### Expected Performance:
| State | Time | Status |
|-------|------|--------|
| Before fixes | 2.5-4s | ❌ Too slow |
| After Opt 1 | 1.5-2.5s | ⚠️ Better |
| After Opt 2 | 1.1-1.5s | ✅ Good |
| After Opt 3 | 0.8-1.2s | ✅ Excellent |

---

**Next Steps:**
1. ✅ **DONE:** Ollama updated to 0.12.10
2. ✅ **DONE:** Ollama concurrency configured
3. ✅ **DONE:** Thinking tags fixed (native API)
4. ✅ **DONE:** Optimization 1 implemented (filter before calling)
5. ✅ **DONE:** Optimization 2 implemented (batch embeddings)
6. ✅ **DONE:** Optimization 3 implemented (embedding cache with TTL)
7. 🔴 **TODO:** Test KG extraction with all optimizations
8. 🔴 **TODO:** Monitor cache hit rates and performance
9. 🔴 **TODO:** Re-enable KG extraction and verify no timeouts
