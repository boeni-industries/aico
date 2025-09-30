# Deduplication Testing Instructions

## 🎯 Purpose
Test that the fact deduplication system works correctly by running the same scenarios with the same user multiple times.

## ✅ What Was Implemented

### 1. Deduplication System (`/shared/aico/ai/memory/semantic.py`)
- **`_generate_embedding()`**: Centralized embedding generation
- **`_find_duplicate_fact()`**: Semantic similarity detection (threshold: 0.92)
- **`_update_fact()`**: Merge strategy for duplicate facts
- **`_insert_new_fact()`**: Clean insertion of new facts
- **Modified `store_fact()`**: Three-stage deduplication process

### 2. Configuration (`/config/defaults/core.yaml`)
```yaml
deduplication:
  enabled: true
  similarity_threshold: 0.92  # 0.90-0.95 recommended
  check_top_n: 5  # Check top N similar facts
```

### 3. Test Framework Updates
- **`evaluator.py`**: Added `reuse_user` parameter
- **`test_multi_scenario.py`**: Added `--reuse-user` flag
- **`cli.py`**: Added `--reuse-user` option to run command

## 🧪 How to Test Deduplication

### Method 1: Using the CLI (Recommended)

```bash
# Clear existing facts (optional)
uv run aico chroma clear user_facts --force

# Run 1: Baseline (creates ~14 facts for 3 scenarios)
uv run scripts/run_memory_benchmark.py run --reuse-user

# Check fact count
uv run aico chroma tail user_facts --limit 50

# Run 2: Test deduplication (should stay at ~14 facts, NOT double to 28!)
uv run scripts/run_memory_benchmark.py run --reuse-user

# Check fact count again - should be SAME as Run 1
uv run aico chroma tail user_facts --limit 50
```

### Method 2: Using Python Module

```bash
# Run with reuse-user flag
uv run python -m scripts.memory_benchmark.test_multi_scenario --reuse-user
```

## 📊 Expected Results

### ✅ SUCCESS (Deduplication Working)
- **Run 1**: ~14 facts created (6 + 4 + 4 for 3 scenarios)
- **Run 2**: ~14 facts total (SAME count, facts updated not duplicated)
- **Logs show**: `📋 [DEDUP] Duplicate detected (similarity: 0.9XX)`
- **Logs show**: `✅ [DEDUP] Updated fact: fact_xxx_xxx`

### ❌ FAILURE (Deduplication Not Working)
- **Run 1**: ~14 facts created
- **Run 2**: ~28 facts total (DOUBLED!)
- **Logs show**: Only `✅ [CHROMADB_STORE] Stored new fact`
- **No deduplication logs**

## 🔍 Verification Commands

```bash
# Count total facts
uv run aico chroma tail user_facts | grep "Showing last"

# View all facts with details
uv run aico chroma tail user_facts --full --limit 50

# Check for specific user's facts
uv run aico chroma tail user_facts --full --limit 50 | grep "user_id:"

# Look for deduplication logs
tail -f logs/backend.log | grep DEDUP
```

## 📝 What to Look For

### In Logs (Second Run)
```
📋 [DEDUP] Duplicate detected (similarity: 0.950)
📋 [DEDUP] Existing: person: Michael lives in San Francisco...
📋 [DEDUP] New: person: Michael moved to San Francisco...
✅ [DEDUP] Updated fact: fact_user123_1234567890 (confidence: 0.85)
```

### In ChromaDB
- Same fact ID appears with `updated_at` timestamp
- Confidence may increase
- Content may be updated
- No duplicate facts with similar content

## 🎯 Success Criteria

1. **Fact count remains stable** across multiple runs with same user
2. **Deduplication logs appear** in second run
3. **Facts are updated** (not duplicated)
4. **Confidence scores merge** (keeps higher value)
5. **Timestamps update** (`updated_at` field)

## 🔧 Troubleshooting

### If deduplication doesn't trigger:
1. Check `similarity_threshold` in config (try lowering to 0.88)
2. Verify `dedup_enabled` is True
3. Check logs for embedding generation errors
4. Ensure same user_id is being used

### If facts still duplicate:
1. Check `_find_duplicate_fact()` is being called
2. Verify ChromaDB query is working
3. Check similarity calculation logic
4. Review L2 distance to cosine similarity conversion

## 📚 Related Files

- `/shared/aico/ai/memory/semantic.py` - Deduplication logic
- `/config/defaults/core.yaml` - Configuration
- `/scripts/memory_benchmark/evaluator.py` - Test framework
- `/scripts/memory_benchmark/cli.py` - CLI interface
- `/scripts/run_memory_benchmark.py` - Entry point
