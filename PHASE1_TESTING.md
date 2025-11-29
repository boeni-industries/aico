# Phase 1 Optimization - Testing Guide

## Changes Made

### File: `/modelservice/handlers/tts_handler.py`

**Removed**:
- `.to("mps")` call that was moving model to Metal GPU
- MPS availability checks
- Metal-related logging

**Added**:
- `torch.set_num_threads(8)` for M2 Max optimization
- CPU-only execution path
- Updated logging to reflect CPU-only approach

**Why**: MPS (Metal Performance Shaders) is actually SLOWER than CPU for XTTS on Apple Silicon due to incomplete operation support. This is a known issue (GitHub #3649).

---

## Expected Improvements

### Before (Current Performance)
- First chunk: ~10,000ms (10 seconds)
- Total synthesis (724 chars): ~73,000ms (73 seconds)
- Throughput: ~10 chars/second

### After Phase 1 (Target)
- First chunk: 3,000-5,000ms (3-5 seconds)
- Total synthesis (724 chars): 25,000-35,000ms (25-35 seconds)
- Throughput: ~20-30 chars/second
- **Improvement**: 2-3x faster

---

## Testing Instructions

### Option 1: Run Benchmark Script

```bash
# From project root
cd /Users/mbo/Documents/dev/aico

# Activate virtual environment
source .venv/bin/activate

# Run benchmark
python scripts/benchmark_tts.py
```

This will test three text lengths and provide detailed metrics:
- Time to first chunk
- Total synthesis time
- Real-time factor (RTF)
- Throughput (chars/second)

### Option 2: Test via Frontend

1. Start the backend services:
   ```bash
   aico dev start
   ```

2. Open Flutter app and test "Read Aloud" feature

3. Check modelservice logs for timing:
   ```bash
   tail -f ~/.aico/logs/modelservice.log
   ```

4. Look for these log lines:
   - `⏱️ [TTS TIMING] Chunk X synthesis: XXXms`
   - `⏱️ [TTS TIMING] ========== TOTAL SYNTHESIS TIME: XXXms ==========`

### Option 3: Quick Manual Test

```bash
# Start modelservice
aico dev start modelservice

# In another terminal, test via backend API
curl -X POST http://localhost:8771/api/v1/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world, this is a test of the optimized TTS system.",
    "language": "en"
  }' \
  --output test_audio.wav

# Check timing in modelservice logs
```

---

## What to Look For

### Success Indicators ✅

1. **Startup logs show CPU optimization**:
   ```
   🚀 Optimized CPU threads: 8 (M2 Max performance cores)
   ✅ TTS model loaded on CPU (optimized for Apple Silicon)
   ```

2. **No MPS-related logs** (these should be gone):
   ```
   # Should NOT see:
   🚀 Moving TTS model to Metal GPU for acceleration
   ```

3. **Faster synthesis times**:
   - First chunk: <5 seconds (down from 10s)
   - Total time: <35 seconds for long text (down from 73s)

4. **Consistent performance** (no hangs or freezes)

### Warning Signs ⚠️

1. **Slower than before**: Something went wrong, revert changes
2. **Model loading errors**: Check PyTorch installation
3. **Thread warnings**: May need to adjust thread count

---

## Benchmark Metrics Explained

### Time to First Chunk (TTFC)
- Time from request start to first audio data
- Most important for perceived latency
- Target: <5 seconds

### Total Synthesis Time
- Complete time to synthesize all audio
- Important for long texts
- Target: <35 seconds for 724 chars

### Real-Time Factor (RTF)
- Ratio of synthesis time to audio duration
- RTF < 1.0 = faster than real-time
- RTF = 2.0 = takes 2 seconds to generate 1 second of audio
- Target: RTF < 5.0

### Throughput
- Characters processed per second
- Higher is better
- Target: >20 chars/second

---

## Troubleshooting

### Issue: No improvement or slower

**Check**:
1. Verify MPS code is removed: `grep -n "\.to\(\"mps\"\)" modelservice/handlers/tts_handler.py`
2. Verify thread count is set: `grep -n "set_num_threads" modelservice/handlers/tts_handler.py`
3. Check PyTorch version: `python -c "import torch; print(torch.__version__)"`

**Solution**: Ensure changes were applied correctly, restart modelservice

### Issue: Thread warnings

**Symptoms**:
```
Warning: Too many threads requested
```

**Solution**: Reduce thread count from 8 to 4:
```python
torch.set_num_threads(4)
```

### Issue: Model loading fails

**Symptoms**:
```
Failed to initialize TTS handler
```

**Solution**: 
1. Check internet connection (model download)
2. Clear cache: `rm -rf ~/.aico/cache/tts_models`
3. Reinstall: `pip install --force-reinstall coqui-tts`

---

## Next Steps

### If Phase 1 Succeeds (2-3x improvement)
✅ Proceed to Phase 2: Low-level API refactoring
- Target: 5-10x improvement
- Time estimate: 2-3 hours

### If Phase 1 Shows Minimal Improvement (<1.5x)
⚠️ Investigate further:
1. Check CPU usage during synthesis
2. Profile with `py-spy` or similar
3. Consider hardware limitations
4. May need to jump to Piper TTS alternative

### If Phase 1 Makes Things Worse
❌ Revert changes:
```bash
git checkout modelservice/handlers/tts_handler.py
```
And investigate why MPS was faster in your specific setup.

---

## Recording Results

Please record benchmark results for comparison:

```
PHASE 1 RESULTS:
Date: ___________
Hardware: M2 Max

Test Case: Long (724 chars)
- First chunk: _______ms (was: 10,000ms)
- Total time: _______ms (was: 73,000ms)
- Improvement: _______x

Test Case: Medium (~150 chars)
- First chunk: _______ms
- Total time: _______ms

Test Case: Short (~30 chars)
- First chunk: _______ms
- Total time: _______ms
```

---

## Questions?

- Check `XTTS_OPTIMIZATION_PLAN.md` for detailed explanations
- Review GitHub issue: https://github.com/coqui-ai/TTS/issues/3649
- Consult memory: "XTTS Performance Analysis and Optimization Plan for M2 MacBook Pro"
