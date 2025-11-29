# XTTS Performance Optimization Plan
## MacBook Pro M2 Max - Complete Analysis & Implementation Guide

---

## Executive Summary

**Current State**: XTTS v2 synthesis is **50x slower** than benchmarks
- Your system: 10s first chunk, 73s total (724 chars)
- Benchmark: 200ms first chunk, ~2s total (with DeepSpeed)
- **Goal**: Achieve 2s first chunk (5x improvement) through systematic optimizations

---

## Current Setup Analysis

### Hardware
- **Device**: MacBook Pro M2 Max
- **GPU**: Apple Metal (MPS) - 38 cores
- **RAM**: Unified memory architecture
- **OS**: macOS

### Software Stack
```
Location: /modelservice/handlers/tts_handler.py
Model: tts_models/multilingual/multi-dataset/xtts_v2
API: TTS.api.TTS() (high-level wrapper)
Backend: PyTorch 2.8.0
Device: CPU → .to("mps") manual transfer
Dependencies:
  - coqui-tts (idiap fork, dev branch)
  - transformers==4.50.3
  - torch>=2.8.0
```

### Current Performance Metrics
```
Text: 724 characters
Chunks: 4-5 (via _split_text)
First chunk: ~10,000ms
Total time: ~73,000ms
Throughput: ~10 chars/second
```

---

## Root Cause Analysis

### Issue #1: MPS Backend is SLOWER than CPU ⚠️

**Evidence**:
- GitHub Issue #3649: "XTTS v2 hangs on MPS device on Apple Silicon"
- Community reports: M1/M2 users report CPU faster than MPS
- Your logs show MPS is active but performance is terrible

**Why MPS Fails**:
```python
# Current code (lines 76-81)
if torch.backends.mps.is_available():
    self._logger.info("🚀 Moving TTS model to Metal GPU for acceleration")
    self._tts.to("mps")  # ❌ This SLOWS DOWN XTTS!
else:
    self._logger.info("⚠️ Metal GPU not available, using CPU")
```

**Root Cause**:
- XTTS uses operations not optimized for Metal Performance Shaders
- MPS backend lacks support for certain transformer operations
- Fallback to CPU emulation on MPS is slower than native CPU

**Fix**: Remove MPS, use CPU only
**Expected Improvement**: 2-3x faster (10s → 3-5s first chunk)

---

### Issue #2: High-Level API Overhead

**Current Implementation**:
```python
# Line 69-73: Using high-level API
self._tts = await asyncio.to_thread(
    TTS,
    "tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False
)

# Line 224-240: Synthesis via wrapper
audio = await asyncio.to_thread(
    self._tts.tts,  # ❌ High-level wrapper
    text=chunk,
    language=language,
    speaker=speaker,
    speed=speed
)
```

**Problems**:
1. `TTS.api` wrapper adds overhead
2. Recomputes conditioning latents every call
3. No access to streaming optimizations
4. No control over inference parameters

**Solution**: Use low-level `Xtts` class directly
```python
from TTS.tts.models.xtts import Xtts
from TTS.tts.configs.xtts_config import XttsConfig

# Load model directly
config = XttsConfig()
config.load_json(checkpoint_dir + "/config.json")
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir=checkpoint_dir)

# Pre-compute conditioning latents (ONCE)
gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
    audio_path=speaker_wav
)

# Use streaming inference
chunks = model.inference_stream(
    text,
    language,
    gpt_cond_latent,
    speaker_embedding,
    enable_text_splitting=True  # Let XTTS handle chunking
)
```

**Expected Improvement**: 2-3x faster (3-5s → 1-2s first chunk)

---

### Issue #3: Inefficient Text Chunking

**Current Implementation**:
```python
# Line 208: Custom chunking
chunks = self._split_text(cleaned_text)

# Line 213-261: Sequential synthesis
for i, chunk in enumerate(chunks):
    audio = await asyncio.to_thread(self._tts.tts, ...)
    # Each chunk waits for previous to complete
```

**Problems**:
1. Custom `_split_text()` may not be optimal
2. Sequential processing (no parallelization)
3. Large chunks = high first-chunk latency
4. No streaming within chunks

**Solution**: Use XTTS internal splitting
```python
# Let XTTS handle chunking optimally
for chunk in model.inference_stream(
    text,
    language,
    gpt_cond_latent,
    speaker_embedding,
    enable_text_splitting=True,  # ✅ Internal optimization
    stream_chunk_size=20,        # Smaller chunks = faster TTFB
):
    yield chunk
```

**Expected Improvement**: 20-30% faster, smoother streaming

---

### Issue #4: No PyTorch Optimizations

**Missing Optimizations**:
1. No `torch.inference_mode()` (faster than `no_grad()`)
2. No CPU thread optimization
3. No model compilation (`torch.compile()`)
4. No BetterTransformer

**Solution**:
```python
import torch

# Set CPU threads for M2 (performance cores)
torch.set_num_threads(8)  # M2 Max has 8 performance cores

# Use inference mode
with torch.inference_mode():
    chunks = model.inference_stream(...)

# Optional: Compile model (PyTorch 2.0+)
model = torch.compile(model, mode="reduce-overhead")
```

**Expected Improvement**: 10-20% faster

---

## Optimization Implementation Plan

### Phase 1: Quick Wins (30 minutes)
**Target**: 3-5s first chunk (2-3x improvement)

1. **Remove MPS backend**
   ```python
   # Remove lines 76-81
   # Don't call .to("mps")
   # Keep model on CPU
   ```

2. **Set CPU thread count**
   ```python
   import torch
   torch.set_num_threads(8)  # M2 Max performance cores
   ```

3. **Test and benchmark**

---

### Phase 2: Low-Level API (2-3 hours)
**Target**: 1-2s first chunk (5-10x improvement)

1. **Refactor to `Xtts` class**
   - Replace `TTS.api.TTS()` with `Xtts.init_from_config()`
   - Load config and checkpoint manually
   - Use `inference_stream()` method

2. **Implement conditioning latent caching**
   ```python
   class TtsHandler:
       def __init__(self):
           self._conditioning_cache = {}  # speaker -> (latent, embedding)
       
       async def _get_conditioning_latents(self, speaker_wav):
           cache_key = hash(speaker_wav)
           if cache_key not in self._conditioning_cache:
               latent, embedding = self._model.get_conditioning_latents(
                   audio_path=speaker_wav
               )
               self._conditioning_cache[cache_key] = (latent, embedding)
           return self._conditioning_cache[cache_key]
   ```

3. **Enable internal text splitting**
   ```python
   for chunk in model.inference_stream(
       text,
       language,
       gpt_cond_latent,
       speaker_embedding,
       enable_text_splitting=True,
       stream_chunk_size=20,
   ):
       yield chunk
   ```

---

### Phase 3: Advanced Optimizations (1-2 hours)
**Target**: 500ms-1s first chunk (10-20x improvement)

1. **Add inference mode**
   ```python
   with torch.inference_mode():
       for chunk in model.inference_stream(...):
           yield chunk
   ```

2. **Optimize warmup**
   - Pre-compute all speaker embeddings at startup
   - Warm up with short text samples
   - Cache model state

3. **Consider torch.compile()**
   ```python
   # Experimental for M2
   model = torch.compile(model, mode="reduce-overhead")
   ```

---

## Expected Results

### Performance Targets

| Optimization Level | First Chunk | Total (724 chars) | Improvement |
|-------------------|-------------|-------------------|-------------|
| **Current** | 10,000ms | 73,000ms | Baseline |
| **Phase 1** (CPU only) | 3,000-5,000ms | 25,000-35,000ms | 2-3x |
| **Phase 2** (Low-level API) | 1,000-2,000ms | 8,000-15,000ms | 5-10x |
| **Phase 3** (Full optimization) | 500-1,000ms | 4,000-8,000ms | 10-20x |
| **Benchmark** (DeepSpeed) | 200ms | 2,000ms | 50x |

### Realistic Goal for M2 CPU
- **First chunk**: 1-2 seconds
- **Total synthesis**: 5-10 seconds
- **5-10x improvement** over current performance

---

## Implementation Checklist

### Phase 1: CPU Optimization
- [ ] Remove `.to("mps")` call (line 79)
- [ ] Add `torch.set_num_threads(8)`
- [ ] Test and benchmark
- [ ] Document performance improvement

### Phase 2: Low-Level API
- [ ] Import `Xtts` and `XttsConfig`
- [ ] Refactor `initialize()` to use low-level API
- [ ] Implement conditioning latent caching
- [ ] Refactor `synthesize_stream()` to use `inference_stream()`
- [ ] Enable `enable_text_splitting=True`
- [ ] Test and benchmark

### Phase 3: Advanced
- [ ] Add `torch.inference_mode()` context
- [ ] Optimize warmup procedure
- [ ] Test `torch.compile()` (optional)
- [ ] Final benchmarking
- [ ] Update documentation

---

## Alternative: Piper TTS

If XTTS optimizations don't meet requirements:

**Piper Performance**:
- First chunk: <100ms
- Total (724 chars): <300ms
- **244x faster** than current XTTS

**Trade-offs**:
- ❌ No voice cloning
- ❌ Slightly lower quality
- ✅ Instant playback
- ✅ Trivial to integrate

**Recommendation**: Implement Piper as fallback option for speed-critical scenarios

---

## Files to Modify

1. `/modelservice/handlers/tts_handler.py`
   - Lines 36-169: `initialize()` method
   - Lines 171-269: `synthesize_stream()` method

2. `/pyproject.toml`
   - No changes needed (dependencies already correct)

3. `/config/defaults/core.yaml`
   - May need to add optimization flags

---

## Testing Strategy

### Benchmark Script
```python
import time
import asyncio
from modelservice.handlers.tts_handler import TtsHandler

async def benchmark():
    handler = TtsHandler()
    await handler.initialize()
    
    test_texts = [
        "Hello world",  # Short
        "This is a medium length sentence for testing.",  # Medium
        "A" * 724,  # Your actual test case
    ]
    
    for text in test_texts:
        start = time.time()
        first_chunk_time = None
        
        async for chunk in handler.synthesize_stream(text):
            if first_chunk_time is None:
                first_chunk_time = time.time() - start
        
        total_time = time.time() - start
        print(f"Text: {len(text)} chars")
        print(f"First chunk: {first_chunk_time*1000:.0f}ms")
        print(f"Total: {total_time*1000:.0f}ms")
        print()

asyncio.run(benchmark())
```

---

## Success Criteria

✅ **Minimum Viable**: 3-5s first chunk (Phase 1)
✅ **Target**: 1-2s first chunk (Phase 2)
✅ **Stretch**: <1s first chunk (Phase 3)

---

## Next Steps

1. Review this document
2. Confirm optimization priorities
3. Start with Phase 1 (30 min quick win)
4. Benchmark and iterate
5. Proceed to Phase 2 if needed
