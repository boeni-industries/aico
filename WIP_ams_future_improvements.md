# AMS Future Improvements

## Phase 4: Unified Indexing (Not Yet Implemented)

**Status:** Planned for future implementation  
**Priority:** Medium (nice-to-have optimization)  
**Estimated Effort:** 2-3 weeks

### Overview

Phase 4 will implement a unified memory indexing system that provides seamless cross-layer retrieval across all memory tiers (L0: raw data, L1: structured memory, L2: parameterized memory). This is an optimization layer that improves retrieval performance but is not required for core functionality.

### Components to Implement

**1. Cross-Layer Indexing (`unified/index.py`)**
- Unified index structure spanning working, semantic, and behavioral memory
- Single query interface for all memory types
- Automatic index maintenance and updates
- **Benefit:** Faster retrieval, reduced query complexity

**2. Unified Retrieval Interface (`unified/retrieval.py`)**
- Single API for querying all memory tiers
- Cross-tier relevance ranking
- Result merging and deduplication
- **Benefit:** Simpler application code, better UX

**3. Memory Lifecycle Management (`unified/lifecycle.py`)**
- Automated memory tier transitions (working → semantic → archive)
- TTL enforcement across all tiers
- Memory promotion/demotion based on usage
- **Benefit:** Automatic memory optimization

### Why It Can Wait

**Current System Works Well:**
- ✅ Working memory (LMDB) - fast, 24hr TTL
- ✅ Semantic memory (ChromaDB) - efficient vector search
- ✅ Behavioral memory (libSQL) - Thompson Sampling working
- ✅ Memory consolidation - automated transfer working

**Phase 4 is an Optimization:**
- Current retrieval is already fast (<50ms)
- Each tier has optimized storage
- Consolidation handles tier transitions
- No user-facing issues

**When to Implement:**
- After 1000+ users (scaling needs)
- When retrieval latency becomes noticeable
- When cross-tier queries become common
- When memory management becomes complex

### Implementation Checklist

**Files to Create:**
- `shared/aico/ai/memory/unified/index.py` (~250 lines) - Cross-layer index builder
- `shared/aico/ai/memory/unified/retrieval.py` (~250 lines) - Unified query interface
- `shared/aico/ai/memory/unified/lifecycle.py` (~200 lines) - Memory tier transitions

**Files to Modify:**
- `shared/aico/ai/memory/manager.py` - Add unified index initialization
- `shared/aico/ai/memory/context/assembler.py` - Use unified retrieval API

**Database Changes:**
- Add `unified_index` table for cross-layer metadata
- Add indexes for efficient cross-tier queries

**Tasks:**
1. Design unified index schema (1-2 days)
2. Implement cross-layer indexing (3-4 days)
3. Build unified retrieval API (3-4 days)
4. Add memory lifecycle automation (2-3 days)
5. Integration testing (2-3 days)
6. Performance optimization (2-3 days)

**Total Effort:** ~2-3 weeks

### Technical Notes

**Storage Footprint:** ~5-10KB per user (index metadata)  
**Performance Impact:** Minimal (index updates are incremental)  
**Complexity:** Medium (requires careful design to avoid over-engineering)

---

## Knowledge Graph Quality Feedback Loop

### Automated Analysis
- **Keyword Detection**: Flag feedback containing KG-related terms ("knowledge graph", "facts", "verify")
- **Entity Extraction**: Extract entities mentioned in AI response and user feedback
- **KG Comparison**: Automatically compare AI claims against current KG data
- **Discrepancy Detection**: Identify mismatches between AI response and KG facts
- **Auto-Triage**: Create review tasks when discrepancies found

### Human Review Workflow
- **Review Dashboard**: Queue of KG verification tasks with priority
- **Context Display**: Show AI response, KG facts, user feedback side-by-side
- **Action Options**: Approve KG, update KG, request more info
- **Pattern Tracking**: Log common KG error types for future detection

### Closed-Loop Learning
- **KG Updates**: Apply corrections from human review to knowledge graph
- **Skill Adjustment**: Penalize skills that produce KG-related errors
- **Freshness Checks**: Trigger validation for entities flagged as outdated
- **Error Patterns**: Learn from repeated issues to prevent future errors

### Sub-Category Enhancement
**Current:**
```
reason: "incorrect_info"
free_text: "should verify facts against the knowledge graph!"
```

**Enhanced:**
```
reason: "incorrect_info"
sub_reason: "knowledge_graph_verification"
free_text: "should verify facts against the knowledge graph!"
kg_entities: ["Marcus", "TechCorp"]
requires_review: true
```

### Implementation Priority

**Phase 1 (High Value, Low Effort):**
1. Keyword detection in free text
2. Auto-flag feedback for review
3. Entity extraction from conversations

**Phase 2 (High Value, Medium Effort):**
4. Automated KG vs AI response comparison
5. Structured review task creation
6. KG error pattern tracking

**Phase 3 (High Value, High Effort):**
7. Human review dashboard
8. KG update workflow integration
9. Skill confidence adjustment based on KG errors

### Benefits
- **Data Quality**: Continuous KG improvement through user feedback
- **Trust**: Users see their feedback directly improving system
- **Accuracy**: Reduced hallucinations and factual errors
- **Learning**: System learns which skills use KG correctly
- **Transparency**: Clear feedback loop from user → KG → AI

### Technical Notes
- Leverage existing feedback classification pipeline
- Extend `feedback_events` schema with KG-specific fields
- Create new `kg_review_tasks` table for human review queue
- Add KG verification metrics to skill confidence calculation

## Feedback Classification Quality Improvements

The current zero-shot embedding-based classification achieves 70-85% accuracy across 50+ languages, which is adequate for trend analysis and Thompson Sampling. However, for ambiguous or low-confidence cases (similarity < 0.25), quality can be improved through a hybrid approach: (1) add confidence scoring to flag uncertain classifications for human review or LLM verification, (2) implement multi-label classification to handle feedback with multiple issues (e.g., both "too verbose" AND "wrong tone"), (3) use an LLM-based classifier for edge cases where embedding similarity is inconclusive, asking the LLM to categorize based on semantic understanding rather than vector similarity, and (4) after collecting 500+ classified examples, fine-tune a lightweight model on actual AICO feedback data for domain-specific accuracy. This hybrid strategy balances automation (fast, multilingual embeddings) with precision (LLM for hard cases) while maintaining the language-agnostic benefits of the current approach.

### Identified Issues (Nov 2025)

**Similarity Threshold Too Low:**
- Current threshold: 0.2 (very permissive)
- Observed misclassification: "very friendly reply. good tone" → classified as "wrong_tone" (similarity: 0.422)
- **Recommendation:** Raise threshold to 0.4-0.5 to reduce false positives
- **Impact:** Better precision, fewer incorrect category assignments
- **Trade-off:** Some feedback may remain uncategorized (acceptable for analytics)

**Category Label Improvements:**
- Current categories are too generic and may have semantic overlap
- Example: "wrong_tone" has high similarity with positive tone descriptions
- **Recommendation:** 
  - Refine category labels to be more semantically distinct
  - Add explicit negative/positive markers in labels
  - Consider renaming "wrong_tone" → "inappropriate_tone" or "unprofessional_tone"
  - Add example phrases to each category definition for better embedding alignment

**Priority:** Medium (doesn't break functionality, Thompson Sampling uses reward not category)

**When to Address:**
- After collecting 100+ classified feedback samples
- When category-based analytics become important
- Before building any category-specific automation
