# Knowledge Graph Entity Extraction Improvements

## Date: 2025-11-04

## Problem
GLiNER was failing to extract complex noun phrases like "website redesign project" as single entities, preventing accurate PROJECT classification in the knowledge graph.

## Root Cause
1. **`flat_ner=True`** - GLiNER was configured to reject nested/overlapping entities
2. **Abstract label definitions** - Semantic similarity matching failed with abstract definitions
3. **High confidence filtering** - 0.5 threshold was rejecting valid low-confidence entities

## Solution

### 1. Enable Nested Entity Extraction
**File:** `/modelservice/core/zmq_handlers.py`
```python
flat_ner=False  # Allow nested entities like "website redesign project"
```

### 2. Example-Based Label Definitions
**File:** `/shared/aico/ai/knowledge_graph/extractor.py`
```python
LABEL_DEFINITIONS = {
    "PROJECT": "work project, software project, website redesign, app development...",
    # Concrete examples instead of abstract definitions
}
```

### 3. Lower Semantic Threshold
```python
if best_similarity > 0.4:  # Was 0.6
    return best_label
```

### 4. Remove Confidence Filter
Removed hardcoded 0.5 filter, respecting GLiNER's threshold parameter (0.1 for high recall).

### 5. Deduplication Logic
Added overlap detection to keep longest/most specific entity spans:
- "website" vs "website redesign project" → keep longer
- Reduces noise from partial matches

### 6. False Positive Monitoring
```python
if low_confidence_count > len(deduplicated) * 0.3:
    logger.warning("High false positive risk...")
```

## Results

### Before
- ❌ "website redesign project" → Not extracted
- ❌ Only extracted "website" (partial)

### After
- ✅ "website redesign project" → Extracted as PROJECT
- ✅ Semantic correction: EVENT → PROJECT (similarity: 0.571)
- ✅ Deduplication removes overlapping "website"

## Configuration

### Current Thresholds
| Parameter | Value | Purpose |
|-----------|-------|---------|
| GLiNER threshold | 0.15 | Balanced recall/precision (filters low-confidence entities) |
| Semantic similarity | 0.4 | Accept reasonable matches |
| False positive alert | 30% | Warn if >30% entities have confidence < 0.3 |

### Adjusting Thresholds
- **Increase GLiNER threshold (0.15 → 0.2)** if still too many false positives
- **Decrease GLiNER threshold (0.15 → 0.1)** if missing important entities
- **Increase semantic threshold (0.4 → 0.5)** if incorrect label corrections

## Impact on Graph Quality

### Improvements
- ✅ Better recall for complex phrases
- ✅ More accurate entity labels
- ✅ Multilingual support maintained

### Trade-offs
- ⚠️ More low-confidence entities (monitored)
- ⚠️ Slightly higher processing time (deduplication)

## Monitoring

Watch for these indicators in logs:
```
logger.warning("High false positive risk...")  # >30% low confidence
logger.debug("Deduplication: X → Y entities")  # Track overlap rate
```

If false positive rate is high:
1. Check `logger.warning` messages
2. Increase GLiNER threshold to 0.15-0.2
3. Increase semantic threshold to 0.45-0.5

## Testing

Test with:
```
I'm working on a website redesign project for my company.
```

Expected:
- ✅ Extract "website redesign project" as PROJECT
- ✅ Deduplicate overlapping "website"
- ✅ Confidence > 0.2
