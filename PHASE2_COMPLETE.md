# ✅ Phase 2 Optimization - COMPLETE

## Changes Applied

### Modified File: `modelservice/handlers/tts_handler.py`

**Complete refactoring to use low-level XTTS API**

---

## Key Changes

### 1. Model Initialization (Lines 28-99)

**Before**: High-level `TTS.api.TTS()` wrapper
```python
self._tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
self._tts.to("mps")
```

**After**: Low-level `Xtts` class with direct control
```python
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

config = XttsConfig()
config.load_json(checkpoint_dir / "config.json")
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir=checkpoint_dir, use_deepspeed=False)
model.to("mps")  # Still using MPS (it works!)
```

**Benefits**:
- Direct access to model internals
- No wrapper overhead
- Explicit control over device placement
- Access to `inference_stream()` method

---

### 2. Conditioning Latent Caching (Lines 189-212)

**New Method**: `_get_conditioning_latents(speaker, language)`

```python
async def _get_conditioning_latents(self, speaker: str, language: str):
    cache_key = f"{speaker}_{language}"
    
    if cache_key in self._conditioning_cache:
        return self._conditioning_cache[cache_key]  # ✅ CACHED!
    
    # Compute once, cache forever
    gpt_cond_latent, speaker_embedding = self._model.get_conditioning_latents(...)
    self._conditioning_cache[cache_key] = (gpt_cond_latent, speaker_embedding)
    return self._conditioning_cache[cache_key]
```

**Impact**:
- **First request**: Computes conditioning latents (~1-2s)
- **Subsequent requests**: Instant retrieval (<1ms)
- **Eliminates**: Recomputation on every chunk

---

### 3. Streaming Synthesis (Lines 214-324)

**Before**: Sequential chunk synthesis via `tts.tts()`
```python
for chunk in chunks:
    audio = self._tts.tts(text=chunk, language=language, speaker=speaker)
    # Each call recomputes conditioning latents!
```

**After**: Single `inference_stream()` call with cached latents
```python
with torch.inference_mode():
    chunks_iter = self._model.inference_stream(
        cleaned_text,
        language,
        gpt_cond_latent,        # ✅ Pre-computed & cached
        speaker_embedding,       # ✅ Pre-computed & cached
        enable_text_splitting=True,  # ✅ XTTS internal optimization
        stream_chunk_size=20,   # ✅ Smaller chunks = faster TTFB
        speed=speed
    )
```

**Benefits**:
- No conditioning latent recomputation
- XTTS handles text splitting optimally
- `torch.inference_mode()` for speed
- Smaller chunks for faster time-to-first-chunk

---

## Technical Improvements

### Performance Optimizations

1. **Conditioning Latent Caching**
   - Eliminates 1-2s overhead per chunk
   - Cached per speaker/language combination
   - Persistent across requests

2. **Low-Level API**
   - No `TTS.api` wrapper overhead
   - Direct model access
   - Explicit control over inference

3. **Internal Text Splitting**
   - `enable_text_splitting=True`
   - XTTS's optimized chunking algorithm
   - Better than custom `_split_text()`

4. **Inference Mode**
   - `torch.inference_mode()` context
   - Faster than `torch.no_grad()`
   - Disables gradient tracking

5. **Smaller Stream Chunks**
   - `stream_chunk_size=20`
   - Faster time-to-first-chunk
   - More frequent updates

---

## Expected Performance

### Baseline (Before Phase 2)
- First chunk: ~10,000ms
- Total (724 chars): ~73,000ms
- Throughput: ~10 chars/sec

### Phase 2 Target
- First chunk: **1,000-2,000ms** (5-10x faster)
- Total (724 chars): **8,000-15,000ms** (5-10x faster)
- Throughput: **50-90 chars/sec** (5-9x faster)

### Key Metric: Time to First Chunk
- **Critical for perceived latency**
- Target: <2 seconds (down from 10s)
- Enables near-instant audio playback

---

## Testing Instructions

### 1. Restart Modelservice
```bash
aico dev restart modelservice
```

### 2. Watch Initialization Logs
```bash
tail -f ~/.aico/logs/modelservice.log | grep "TTS"
```

**Expected output**:
```
🚀 Initializing XTTS v2 (low-level API for performance)
✅ XTTS v2 loaded on MPS (low-level API)
```

### 3. Test via Frontend
1. Open Flutter app
2. Click "Read Aloud" on a message
3. Observe timing in console

### 4. Check Timing Logs

**First Request** (conditioning latents computed):
```
⏱️ [TTS TIMING] Conditioning latents: 1500-2000ms (computed)
⏱️ [TTS TIMING] 🎯 TIME TO FIRST CHUNK: 2000-3000ms
```

**Second Request** (conditioning latents cached):
```
⏱️ [TTS TIMING] Conditioning latents: 0.5ms (cached)
⏱️ [TTS TIMING] 🎯 TIME TO FIRST CHUNK: 1000-2000ms
```

---

## Success Criteria

### ✅ Phase 2 Success
- [ ] First chunk: <3 seconds (first request)
- [ ] First chunk: <2 seconds (cached requests)
- [ ] Total time: <20 seconds for 724 chars
- [ ] Conditioning latents cached (log shows "cached")
- [ ] No errors during synthesis

### ⚠️ Needs Investigation
- [ ] First chunk: 3-5 seconds
- [ ] Occasional errors
- [ ] Inconsistent performance

### ❌ Phase 2 Failed
- [ ] First chunk: >5 seconds
- [ ] Errors on initialization
- [ ] Slower than baseline

---

## Architecture Changes

### Before Phase 2
```
Text → TTS.api.TTS() → tts.tts(chunk) → Audio
         ↑                  ↑
    High-level API    Recomputes latents
                      every chunk
```

### After Phase 2
```
Text → Xtts.inference_stream() → Audio chunks
         ↑              ↑
    Low-level API   Cached latents
                    (computed once)
```

---

## Troubleshooting

### Issue: Model fails to load

**Symptoms**:
```
Failed to initialize TTS handler
```

**Solutions**:
1. Check checkpoint directory exists:
   ```bash
   ls ~/.aico/cache/tts_models--multilingual--multi-dataset--xtts_v2/
   ```
2. If missing, delete and re-download:
   ```bash
   rm -rf ~/.aico/cache/tts_models--multilingual--multi-dataset--xtts_v2/
   aico dev restart modelservice
   ```

### Issue: Conditioning latents error

**Symptoms**:
```
AttributeError: 'Xtts' object has no attribute 'speaker_manager'
```

**Solution**: Model may not have speaker manager. Update `_get_conditioning_latents()` to handle this case.

### Issue: No performance improvement

**Check**:
1. Verify low-level API is being used (check logs)
2. Confirm conditioning latents are cached (check "cached" in logs)
3. Ensure MPS is active (check device in logs)

---

## What's Next

### If Phase 2 Succeeds (5-10x improvement)
✅ **Mission accomplished!**
- 1-2s first chunk is excellent for XTTS
- Consider Phase 3 for marginal gains (10-20%)

### If Phase 2 Shows Marginal Improvement (2-3x)
⚠️ **Consider alternatives**:
- Piper TTS for speed-critical scenarios
- Hybrid approach (Piper for short, XTTS for long)

### If Phase 2 Fails
❌ **Fallback options**:
1. Revert to baseline (high-level API)
2. Switch to Piper TTS entirely
3. Investigate hardware/software issues

---

## Files Modified

1. ✅ `/modelservice/handlers/tts_handler.py`
   - Lines 28-35: Added `_conditioning_cache`
   - Lines 49-99: Low-level model initialization
   - Lines 189-212: Conditioning latent caching
   - Lines 214-324: Refactored `synthesize_stream()`

---

## Performance Monitoring

### Key Metrics to Track

1. **Time to First Chunk (TTFC)**
   - Most important for UX
   - Target: <2s

2. **Total Synthesis Time**
   - Important for long texts
   - Target: <20s for 724 chars

3. **Conditioning Latent Cache Hit Rate**
   - Should be >90% after warmup
   - Check logs for "cached" vs computed

4. **Chunk Count**
   - XTTS internal splitting
   - Should be optimized automatically

---

**Phase 2 implementation complete. Ready for testing! 🚀**

**Expected improvement: 5-10x faster synthesis**
