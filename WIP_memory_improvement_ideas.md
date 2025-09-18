# AICO Memory System Improvement Ideas

## Current Status
- ✅ Basic NER entity extraction working
- ✅ Semantic memory storage in ChromaDB functional
- ✅ Complete conversation segmentation pipeline operational

## Known Issues & Improvement Opportunities

### 1. NER Geographic Entity Misclassification

**Issue**: SpaCy NER incorrectly classifies geographic entities as PERSON entities.
- **Example**: "Schaffhausen" classified as PERSON instead of GPE in context "born in Schaffhausen (switzerland)"
- **Root cause**: Small spaCy models have limited geographic knowledge and context understanding
- **Impact**: Semantic memory stores incorrect entity types, reducing search/context accuracy

**Solution Options** (in order of preference):

#### Option A: Upgrade to Larger spaCy Models ⭐ RECOMMENDED
- **Current**: `en_core_web_sm` (15MB), `de_core_news_sm`, etc.
- **Upgrade to**: `xx_core_web_lg` (560MB multilingual) or language-specific large models
- **Benefits**:
  - 15-25% better accuracy on geographic entities
  - Better Swiss place name recognition (Schaffhausen, Zürich, St. Gallen)
  - Improved multilingual support (German/French/Italian place names)
  - Better contextual understanding of "born in [PLACE]" patterns
- **Trade-offs**:
  - Memory: 15MB → 560MB (37x increase)
  - Loading time: 0.5s → 3-5s startup
  - Processing speed: 2-3x slower per request
- **Swiss context benefits**: Handles "Geneva" vs "Genève" vs "Genf" variations

#### Option B: EntityRuler (Hybrid Rule-Based + Statistical)
- **Approach**: Add spaCy EntityRuler component before NER in pipeline
- **Benefits**:
  - Maintainable (patterns in external JSON files, not hardcoded)
  - Context-aware patterns: "born in {PLACE}", "from {PLACE}"
  - Integrates with existing NER pipeline
  - Industry standard approach
- **Implementation**: EntityRuler → NER → minimal post-processing
- **Maintenance**: Update pattern files as needed, no code changes

#### Option C: Fine-Tuning with Domain-Specific Data
- **Approach**: Train NER model on Swiss/geographic-specific examples
- **Benefits**:
  - Learns contextual patterns automatically
  - Generalizes to unseen entities
  - No ongoing maintenance once trained
- **Drawbacks**: Requires training data creation and model retraining process

#### Option D: Multiple Language-Specific Models
- **Approach**: Load different large models based on detected language
- **Models**: `en_core_web_lg`, `de_core_news_lg`, `fr_core_news_lg`, `it_core_news_lg`
- **Benefits**: Best accuracy per language
- **Drawbacks**: 3-4x memory usage (multiple models loaded simultaneously)

### 2. Sentiment Analysis Implementation

**Current State**: Hardcoded to `"neutral"` in semantic memory storage.

**Implementation Options**:
1. **Modelservice Integration**: Add sentiment analysis endpoint alongside NER
2. **Local Analysis**: Use TextBlob or lightweight sentiment library
3. **Rule-Based**: Simple keyword-based sentiment detection

### 3. Topic Extraction

**Current State**: Empty array `[]` in semantic memory.

**Potential Approaches**:
1. **Keyword extraction**: TF-IDF or similar
2. **Topic modeling**: LDA or similar unsupervised methods
3. **Rule-based**: Extract topics from entity types and context

## Configuration Notes

Current spaCy configuration in `config/defaults/core.yaml`:
- Languages: en, de, fr, es, it (small models)
- Auto-install enabled
- Memory management: auto-unload after 30min, max 2 concurrent models
- Memory threshold: 85% before unloading

**For large model upgrade**: May need to adjust:
- `max_concurrent_models: 1` (due to memory usage)
- `memory_threshold_percent: 70` (earlier unloading)
- `auto_unload_minutes: 15` (more aggressive unloading)

## Testing Plan

1. **Benchmark current accuracy** on Swiss geographic entities
2. **Test xx_core_web_lg** model performance and memory usage
3. **Compare accuracy improvements** on real conversation data
4. **Measure performance impact** in production-like environment
5. **Evaluate EntityRuler** as alternative/complementary approach

## Priority

**High Priority**: NER geographic entity accuracy (directly impacts semantic memory quality)
**Medium Priority**: Sentiment analysis implementation
**Low Priority**: Topic extraction (nice-to-have for richer metadata)

---
*Last updated: 2025-09-18*
*Status: Research complete, testing phase*
