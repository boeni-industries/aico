# ✅ Phase 1 Optimization - COMPLETE

## Changes Applied

### Modified File: `modelservice/handlers/tts_handler.py`

**Lines 64-78**: Removed MPS backend, added CPU optimization

```python
# PHASE 1 OPTIMIZATION: Use CPU only (MPS is slower for XTTS on Apple Silicon)
# See: https://github.com/coqui-ai/TTS/issues/3649
import torch

# Optimize CPU performance for M2 Max (8 performance cores)
torch.set_num_threads(8)
self._logger.info("🚀 Optimized CPU threads: 8 (M2 Max performance cores)")

self._tts = await asyncio.to_thread(
    TTS,
    "tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False  # CPU is faster than MPS for XTTS
)

self._logger.info("✅ TTS model loaded on CPU (optimized for Apple Silicon)")
```

### What Was Removed
- ❌ `.to("mps")` call (line 79 in old code)
- ❌ `torch.backends.mps.is_available()` check
- ❌ Metal GPU acceleration attempt
- ❌ Misleading log messages about GPU acceleration

### What Was Added
- ✅ `torch.set_num_threads(8)` for M2 Max optimization
- ✅ Clear documentation of why CPU-only
- ✅ Reference to GitHub issue #3649
- ✅ Accurate logging about CPU usage

---

## Verification

### ✅ Confirmed Changes
```bash
# No MPS calls found (expected: exit code 1)
$ grep -n "\.to(\"mps\")" modelservice/handlers/tts_handler.py
# (no output - correct!)

# Thread optimization found (expected: line 69)
$ grep -n "set_num_threads" modelservice/handlers/tts_handler.py
69:            torch.set_num_threads(8)
```

---

## Expected Performance Improvement

### Before Phase 1
- First chunk: ~10,000ms
- Total (724 chars): ~73,000ms
- Throughput: ~10 chars/sec

### After Phase 1 (Target)
- First chunk: 3,000-5,000ms (2-3x faster)
- Total (724 chars): 25,000-35,000ms (2-3x faster)
- Throughput: 20-30 chars/sec

### Improvement Factor
**2-3x faster** overall performance

---

## Testing Instructions

### Quick Test
```bash
# 1. Restart modelservice
aico dev restart modelservice

# 2. Check logs for new messages
tail -f ~/.aico/logs/modelservice.log | grep "TTS"

# Expected log output:
# 🚀 Optimized CPU threads: 8 (M2 Max performance cores)
# ✅ TTS model loaded on CPU (optimized for Apple Silicon)
```

### Full Benchmark
```bash
# Run benchmark script
python scripts/benchmark_tts.py

# Compare results with baseline:
# - First chunk should be <5 seconds
# - Total time should be <35 seconds for long text
```

### Frontend Test
1. Start services: `aico dev start`
2. Open Flutter app
3. Click "Read Aloud" on a message
4. Observe timing in console/logs

---

## Success Criteria

### ✅ Phase 1 Success
- [ ] First chunk latency reduced by 50% or more
- [ ] Total synthesis time reduced by 50% or more
- [ ] No errors or crashes
- [ ] Consistent performance across multiple runs

### ⚠️ Needs Investigation
- [ ] Improvement less than 50%
- [ ] Intermittent errors
- [ ] Performance varies significantly

### ❌ Phase 1 Failed
- [ ] No improvement or slower
- [ ] Crashes or errors
- [ ] Model fails to load

---

## Next Steps

### If Successful (2-3x improvement)
✅ **Proceed to Phase 2**: Low-level API refactoring
- Target: 5-10x total improvement (1-2s first chunk)
- Estimated time: 2-3 hours
- See: `XTTS_OPTIMIZATION_PLAN.md` Phase 2 section

### If Marginal (<1.5x improvement)
⚠️ **Investigate before Phase 2**:
1. Profile CPU usage during synthesis
2. Check for thermal throttling
3. Verify thread count is optimal
4. Consider alternative approaches

### If Failed (no improvement or worse)
❌ **Troubleshooting steps**:
1. Verify changes applied: `git diff modelservice/handlers/tts_handler.py`
2. Check PyTorch version: `python -c "import torch; print(torch.__version__)"`
3. Review logs for errors
4. Consider reverting: `git checkout modelservice/handlers/tts_handler.py`

---

## Technical Notes

### Why MPS Was Slower

**Issue**: XTTS v2 uses transformer operations not fully optimized for Metal
- Some operations fall back to CPU emulation on MPS
- Overhead of CPU↔GPU data transfer
- Metal shader compilation overhead

**Evidence**: 
- GitHub Issue #3649: Multiple users report hangs/slowness
- Community consensus: CPU faster than MPS for XTTS on M1/M2

### Why 8 Threads

**M2 Max Architecture**:
- 8 performance cores (high-power)
- 4 efficiency cores (low-power)
- Setting to 8 uses all performance cores
- Avoids efficiency cores for maximum speed

**Alternative**: If thermal throttling occurs, reduce to 4 threads

---

## Files Created

1. ✅ `PHASE1_COMPLETE.md` (this file)
2. ✅ `PHASE1_TESTING.md` (detailed testing guide)
3. ✅ `scripts/benchmark_tts.py` (automated benchmark)
4. ✅ `XTTS_OPTIMIZATION_PLAN.md` (complete optimization plan)

---

## Ready to Test!

**Restart modelservice and run benchmarks to measure improvement.**

```bash
# Quick start
aico dev restart modelservice

# Watch for optimization logs
tail -f ~/.aico/logs/modelservice.log | grep -E "(Optimized|TTS model loaded)"

# Run benchmark when ready
python scripts/benchmark_tts.py
```

---

**Phase 1 implementation complete. Ready for testing! 🚀**
