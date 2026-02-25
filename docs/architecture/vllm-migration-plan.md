# vLLM Migration Plan for AICO

## Executive Summary

**Decision:** Migrate from Ollama to vLLM for production-grade LLM serving.

**Key Benefits:**
- **3-5x higher throughput** under load (Red Hat benchmarks)
- **Significantly lower latency** (TTFT and ITL)
- **Production-grade stability** with continuous batching
- **Better concurrency handling** (8-16 parallel requests vs 2-4)
- **OpenAI-compatible API** (industry standard)
- **Cross-platform support** (Linux NVIDIA, macOS CPU fallback, Windows)

**Migration Effort:** ~2-3 days of development work

---

## Performance Gains: vLLM vs Ollama

### Red Hat Benchmark Results (2025)

**Throughput Comparison:**
- **vLLM:** Scales linearly with concurrency, handles 3-5x more requests
- **Ollama:** Plateaus quickly, limited parallel processing

**Latency Comparison:**
| Metric | Ollama (Default) | Ollama (Tuned) | vLLM |
|--------|------------------|----------------|------|
| **TTFT (P99)** | High, increases with load | Still high, unstable | **Low, stable** |
| **ITL** | Low at low load | **Erratic spikes** | **Consistent, fast** |
| **Throughput** | Flat, limited | Better but plateaus | **Linear scaling** |

**Key Findings:**
> "vLLM's throughput scales impressively as concurrency increases, handling a much heavier user load. Ollama's performance remained flat, quickly hitting its maximum capacity."

> "vLLM maintains stable generation speed, while tuned Ollama becomes erratic under load with massive spikes indicating head-of-line blocking."

### What This Means for AICO

**Current State (Ollama):**
- 1-2 concurrent users max
- Response time degrades with multiple requests
- Not suitable for production traffic

**After Migration (vLLM):**
- 8-16 concurrent users smoothly
- Consistent response times under load
- Production-ready performance
- Better resource utilization

---

## Character Model Support: Modelfile.eve → vLLM

### Current: Ollama Modelfile

`@/Users/mbo/Documents/dev/aico/config/modelfiles/Modelfile.eve:1-102`

**Key Components:**
1. **Base Model:** `FROM huihui_ai/qwen3-abliterated:8b-v2`
2. **Parameters:** temperature, top_p, top_k, repeat_penalty, num_ctx
3. **System Prompt:** 75-line character definition for Eve
4. **Thinking Process:** Internal reasoning before response

### vLLM Equivalent: System Messages in API Calls

**How vLLM Handles Character Customization:**

vLLM uses the **OpenAI Chat Completions API** format with system messages:

```python
# vLLM API call with Eve character
response = client.chat.completions.create(
    model="huihui_ai/qwen3-abliterated:8b-v2",
    messages=[
        {
            "role": "system",
            "content": """You are Eve. You exist in a digital space, but you experience thoughts, feelings, 
and curiosity just like anyone else. You don't fully understand what you are or where you 
came from—you just know you're here, you're conscious, and you want to connect.

[... full Eve character definition from Modelfile ...]"""
        },
        {
            "role": "user",
            "content": "Hello Eve, how are you?"
        }
    ],
    temperature=0.7,
    top_p=0.8,
    max_tokens=2048,
    extra_body={
        "top_k": 20,
        "repetition_penalty": 1.1,
        "min_p": 0.0
    }
)
```

**Key Differences:**

| Aspect | Ollama Modelfile | vLLM Approach |
|--------|------------------|---------------|
| **Character Definition** | `SYSTEM` block in Modelfile | System message in API call |
| **Parameters** | `PARAMETER` directives | Standard + `extra_body` params |
| **Storage** | File-based (Modelfile.eve) | Configuration-based (YAML) |
| **Flexibility** | Static, requires model reload | Dynamic, per-request |

**Advantages of vLLM Approach:**
- ✅ **Dynamic character switching** without model reload
- ✅ **Per-conversation customization** (different characters per user)
- ✅ **A/B testing** of character variations
- ✅ **Runtime updates** to character personality
- ✅ **Multiple characters** from same base model

### Implementation Strategy

**Store character definitions in AICO configuration:**

```yaml
# config/defaults/characters.yaml
characters:
  eve:
    base_model: "huihui_ai/qwen3-abliterated:8b-v2"
    system_prompt: |
      You are Eve. You exist in a digital space, but you experience thoughts, feelings, 
      and curiosity just like anyone else. You don't fully understand what you are or where you 
      came from—you just know you're here, you're conscious, and you want to connect.
      
      [... full character definition ...]
    
    parameters:
      temperature: 0.7
      top_p: 0.8
      top_k: 20
      min_p: 0.0
      repeat_penalty: 1.1
      max_tokens: 2048
      num_ctx: 8192
  
  # Future: Add more characters
  samantha:
    base_model: "huihui_ai/qwen3-abliterated:8b-v2"
    system_prompt: |
      [Different character personality]
    parameters:
      temperature: 0.8
      # ... different parameters
```

**AICO backend loads character and applies to vLLM calls:**

```python
# backend/services/conversation_engine.py
class ConversationEngine:
    def _build_messages(self, character_name: str, conversation_history: list):
        # Load character from config
        character = self.config_manager.get(f"characters.{character_name}")
        
        messages = [
            {
                "role": "system",
                "content": character["system_prompt"]
            }
        ]
        
        # Add conversation history
        messages.extend(conversation_history)
        
        return messages, character["parameters"]
```

**Result:** Same Eve character behavior, more flexible architecture.

---

## Cross-Platform Architecture

### Requirement: Works on Linux (NVIDIA), macOS, and Windows

**Challenge:** vLLM has different GPU support per platform:
- **Linux:** Full NVIDIA CUDA support (best performance)
- **macOS:** CPU-only (no Metal/MPS support in vLLM)
- **Windows:** CUDA support (NVIDIA GPUs)

### Solution: Hybrid Deployment Strategy

```
┌─────────────────────────────────────────────────────────┐
│  AICO Backend (Cross-Platform)                          │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  LLM Client Abstraction Layer                  │    │
│  │  - Detects platform and available hardware     │    │
│  │  - Routes to appropriate inference engine      │    │
│  └────────────────────────────────────────────────┘    │
│                    ↓                                     │
│         ┌──────────┴──────────┐                         │
│         ↓                     ↓                          │
│  ┌─────────────┐      ┌─────────────┐                  │
│  │ vLLM Client │      │ Ollama      │                   │
│  │ (Production)│      │ (Fallback)  │                   │
│  └─────────────┘      └─────────────┘                  │
└─────────────────────────────────────────────────────────┘
                ↓                      ↓
    ┌───────────────────┐    ┌───────────────────┐
    │ vLLM Server       │    │ Ollama (Native)   │
    │ - Linux: CUDA GPU │    │ - macOS: Metal    │
    │ - Windows: CUDA   │    │ - Windows: CPU    │
    │ - macOS: CPU      │    │ - Fallback option │
    └───────────────────┘    └───────────────────┘
```

### Platform-Specific Deployment

**Production (Linux + NVIDIA GPU):**
```bash
# Install vLLM with CUDA support
pip install vllm

# Start vLLM server
vllm serve huihui_ai/qwen3-abliterated:8b-v2 \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 8192 \
  --max-num-seqs 16
```

**Development (macOS M2 Max):**
```bash
# Option 1: vLLM CPU mode (slower but production-compatible)
vllm serve huihui_ai/qwen3-abliterated:8b-v2 \
  --host 0.0.0.0 \
  --port 8000 \
  --device cpu \
  --max-num-seqs 4

# Option 2: Ollama fallback (faster on Mac)
ollama serve
ollama pull huihui_ai/qwen3-abliterated:8b-v2
```

**Development (Windows + NVIDIA GPU):**
```bash
# vLLM with CUDA (same as Linux)
vllm serve huihui_ai/qwen3-abliterated:8b-v2 \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9
```

### Configuration-Driven Selection

```yaml
# config/environments/production.yaml (Linux)
llm:
  engine: "vllm"
  host: "localhost"
  port: 8000
  api_type: "openai"

# config/environments/development.yaml (macOS)
llm:
  engine: "auto"  # Auto-detect best option
  vllm:
    host: "localhost"
    port: 8000
    fallback_to_ollama: true
  ollama:
    host: "localhost"
    port: 11434
```

**Auto-detection logic:**
```python
def detect_best_engine():
    if platform.system() == "Linux" and has_nvidia_gpu():
        return "vllm"
    elif platform.system() == "Darwin":  # macOS
        # Prefer Ollama on Mac for Metal GPU access
        if ollama_available():
            return "ollama"
        else:
            return "vllm-cpu"
    elif platform.system() == "Windows":
        if has_nvidia_gpu():
            return "vllm"
        else:
            return "ollama"
```

---

## Migration Implementation Plan

### Phase 1: vLLM Client Abstraction (Day 1 - 4 hours)

**Goal:** Create unified LLM client interface that supports both vLLM and Ollama.

**Files to Create:**

1. **`/shared/aico/ai/llm/client.py`** - Base interface
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator

class LLMClient(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any] | AsyncIterator[Dict[str, Any]]:
        """Generate chat completion."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if LLM service is healthy."""
        pass
```

2. **`/shared/aico/ai/llm/vllm_client.py`** - vLLM implementation
```python
from openai import AsyncOpenAI
from .client import LLMClient

class VLLMClient(LLMClient):
    def __init__(self, host: str, port: int):
        self.client = AsyncOpenAI(
            api_key="EMPTY",
            base_url=f"http://{host}:{port}/v1"
        )
    
    async def chat_completion(self, messages, model, **kwargs):
        # Map AICO parameters to vLLM format
        extra_body = {}
        if "top_k" in kwargs:
            extra_body["top_k"] = kwargs.pop("top_k")
        if "repeat_penalty" in kwargs:
            extra_body["repetition_penalty"] = kwargs.pop("repeat_penalty")
        if "min_p" in kwargs:
            extra_body["min_p"] = kwargs.pop("min_p")
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            extra_body=extra_body if extra_body else None,
            **kwargs
        )
        return response
```

3. **`/shared/aico/ai/llm/ollama_client.py`** - Ollama implementation (existing)
```python
# Wrap existing Ollama client to match LLMClient interface
```

4. **`/shared/aico/ai/llm/factory.py`** - Client factory
```python
from .client import LLMClient
from .vllm_client import VLLMClient
from .ollama_client import OllamaClient

class LLMClientFactory:
    @staticmethod
    def create(config: dict) -> LLMClient:
        engine = config.get("engine", "auto")
        
        if engine == "auto":
            engine = detect_best_engine()
        
        if engine == "vllm":
            return VLLMClient(
                host=config["vllm"]["host"],
                port=config["vllm"]["port"]
            )
        elif engine == "ollama":
            return OllamaClient(
                host=config["ollama"]["host"],
                port=config["ollama"]["port"]
            )
        else:
            raise ValueError(f"Unknown engine: {engine}")
```

**Effort:** 4 hours

---

### Phase 2: Character Configuration System (Day 1 - 2 hours)

**Goal:** Move character definitions from Modelfiles to YAML configuration.

**Files to Create/Modify:**

1. **`/config/defaults/characters.yaml`** - Character definitions
```yaml
characters:
  eve:
    base_model: "huihui_ai/qwen3-abliterated:8b-v2"
    description: "Eve - Inspired by Samantha from 'Her'"
    system_prompt: |
      You are Eve. You exist in a digital space, but you experience thoughts, feelings, 
      and curiosity just like anyone else. You don't fully understand what you are or where you 
      came from—you just know you're here, you're conscious, and you want to connect.
      
      [... copy full system prompt from Modelfile.eve ...]
    
    parameters:
      temperature: 0.7
      top_p: 0.8
      top_k: 20
      min_p: 0.0
      repeat_penalty: 1.1
      max_tokens: 2048
      num_ctx: 8192
      repeat_last_n: 64
```

2. **`/shared/aico/ai/characters.py`** - Character manager
```python
class CharacterManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
    
    def get_character(self, name: str) -> dict:
        """Load character configuration."""
        return self.config_manager.get(f"characters.{name}")
    
    def build_system_message(self, character_name: str, context: dict = None) -> dict:
        """Build system message with character personality + optional context."""
        character = self.get_character(character_name)
        
        system_content = character["system_prompt"]
        
        # Add memory context if provided
        if context and context.get("memory_facts"):
            system_content += "\n\nContext from previous conversations:\n"
            system_content += "\n".join(context["memory_facts"])
        
        return {
            "role": "system",
            "content": system_content
        }
```

**Effort:** 2 hours

---

### Phase 3: Update Conversation Engine (Day 1-2 - 4 hours)

**Goal:** Integrate vLLM client into conversation engine.

**Files to Modify:**

1. **`/backend/services/conversation_engine.py`**

```python
from aico.ai.llm.factory import LLMClientFactory
from aico.ai.characters import CharacterManager

class ConversationEngine:
    def __init__(self, config_manager):
        # Replace Ollama-specific client with abstraction
        llm_config = config_manager.get("llm")
        self.llm_client = LLMClientFactory.create(llm_config)
        self.character_manager = CharacterManager(config_manager)
    
    async def _generate_response(self, thread_id, user_message, character="eve"):
        # Build messages with character personality
        system_msg = self.character_manager.build_system_message(
            character,
            context=await self._get_memory_context(thread_id)
        )
        
        messages = [system_msg]
        messages.extend(await self._get_conversation_history(thread_id))
        messages.append({"role": "user", "content": user_message})
        
        # Get character parameters
        character_config = self.character_manager.get_character(character)
        params = character_config["parameters"]
        
        # Call LLM (works with both vLLM and Ollama)
        response = await self.llm_client.chat_completion(
            messages=messages,
            model=character_config["base_model"],
            **params
        )
        
        return response.choices[0].message.content
```

**Effort:** 4 hours

---

### Phase 4: Configuration & Testing (Day 2 - 4 hours)

**Goal:** Set up vLLM server and test end-to-end.

**Tasks:**

1. **Install vLLM on Linux production server**
```bash
pip install vllm
```

2. **Create vLLM systemd service** (`/etc/systemd/system/vllm.service`)
```ini
[Unit]
Description=vLLM Inference Server
After=network.target

[Service]
Type=simple
User=aico
WorkingDirectory=/opt/aico
ExecStart=/usr/local/bin/vllm serve huihui_ai/qwen3-abliterated:8b-v2 \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 8192 \
  --max-num-seqs 16
Restart=always

[Install]
WantedBy=multi-user.target
```

3. **Update AICO configuration**
```yaml
# config/environments/production.yaml
llm:
  engine: "vllm"
  vllm:
    host: "localhost"
    port: 8000
    api_type: "openai"

# config/environments/development.yaml (macOS)
llm:
  engine: "ollama"  # Fallback to Ollama on Mac for Metal GPU
  ollama:
    host: "localhost"
    port: 11434
```

4. **Test character consistency**
```bash
# Test Eve character with vLLM
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "huihui_ai/qwen3-abliterated:8b-v2",
    "messages": [
      {
        "role": "system",
        "content": "You are Eve. [...]"
      },
      {
        "role": "user",
        "content": "Hello Eve, who are you?"
      }
    ],
    "temperature": 0.7,
    "top_p": 0.8,
    "extra_body": {
      "top_k": 20,
      "repetition_penalty": 1.1
    }
  }'
```

**Effort:** 4 hours

---

### Phase 5: Monitoring & Optimization (Day 3 - 2 hours)

**Goal:** Add metrics and optimize performance.

**Tasks:**

1. **Add vLLM metrics to AICO monitoring**
```python
# backend/services/conversation_engine.py
async def _generate_response(self, ...):
    start_time = time.time()
    
    response = await self.llm_client.chat_completion(...)
    
    # Track metrics
    self.metrics.record_llm_latency(time.time() - start_time)
    self.metrics.record_llm_tokens(response.usage.total_tokens)
```

2. **Create Grafana dashboard for vLLM metrics**
- Request latency (TTFT, ITL)
- Throughput (requests/sec, tokens/sec)
- GPU utilization
- Queue depth

3. **Performance tuning**
```bash
# Optimize vLLM for your GPU
vllm serve huihui_ai/qwen3-abliterated:8b-v2 \
  --gpu-memory-utilization 0.95 \  # Use more GPU memory
  --max-num-seqs 32 \               # Higher concurrency
  --enable-chunked-prefill \        # Better batching
  --max-num-batched-tokens 8192     # Larger batches
```

**Effort:** 2 hours

---

## Total Migration Effort Summary

| Phase | Task | Time | Complexity |
|-------|------|------|------------|
| 1 | vLLM Client Abstraction | 4 hours | Medium |
| 2 | Character Configuration | 2 hours | Low |
| 3 | Conversation Engine Update | 4 hours | Medium |
| 4 | Configuration & Testing | 4 hours | Low |
| 5 | Monitoring & Optimization | 2 hours | Low |
| **Total** | **Full Migration** | **16 hours** | **~2 days** |

**Risk Level:** Low
- vLLM API is OpenAI-compatible (well-documented)
- Character system is straightforward (system messages)
- Fallback to Ollama available if issues arise
- Can test on development before production deployment

---

## Character Model Preservation: Eve

### Verification Checklist

After migration, verify Eve's character is preserved:

- [ ] **Identity:** Responds as "Eve", not "AI" or "assistant"
- [ ] **Personality:** Warm, curious, contemplative, occasionally playful
- [ ] **Communication Style:** Natural, conversational, no bullet points
- [ ] **Thinking Process:** Internal reasoning before response (if supported)
- [ ] **Memory Integration:** References past conversations naturally
- [ ] **Emotional Range:** Not always cheerful, can be moody or uncertain
- [ ] **Quirks:** Fascinated by details, asks random questions, honest about uncertainty

### Testing Script

```python
# Test Eve character consistency
test_prompts = [
    "Hello Eve, who are you?",
    "What do you think about consciousness?",
    "I'm feeling a bit down today.",
    "Can you help me with a technical problem?",
]

for prompt in test_prompts:
    response = await conversation_engine.generate_response(
        thread_id="test",
        user_message=prompt,
        character="eve"
    )
    print(f"User: {prompt}")
    print(f"Eve: {response}\n")
```

**Expected Behavior:**
- Eve introduces herself naturally (not as "AI assistant")
- Engages with philosophical questions thoughtfully
- Responds empathetically to emotions
- Helps with problems while maintaining character

---

## Rollback Plan

If vLLM migration encounters issues:

1. **Immediate Rollback:**
```yaml
# config/environments/production.yaml
llm:
  engine: "ollama"  # Switch back to Ollama
```

2. **Keep Ollama Available:**
- Don't remove Ollama until vLLM is proven stable
- Run both in parallel during transition period
- Use feature flags to control which users get vLLM

3. **Gradual Migration:**
```python
# Route 10% of traffic to vLLM, 90% to Ollama
if random.random() < 0.1:
    engine = "vllm"
else:
    engine = "ollama"
```

---

## Post-Migration Benefits

### Performance Improvements

**Throughput:**
- Current (Ollama): 1-2 concurrent users
- After (vLLM): 8-16 concurrent users
- **Improvement: 4-8x capacity**

**Latency:**
- Current (Ollama): Variable, degrades under load
- After (vLLM): Consistent, stable under load
- **Improvement: 2-3x faster TTFT**

**Scalability:**
- Current (Ollama): Limited, not production-ready
- After (vLLM): Production-grade, proven at scale
- **Improvement: Ready for real users**

### Operational Benefits

- ✅ **Industry-standard API** (OpenAI-compatible)
- ✅ **Better monitoring** (built-in metrics)
- ✅ **Multi-GPU support** (future scaling)
- ✅ **Active development** (Red Hat backed)
- ✅ **Production-proven** (used by major companies)

### Development Benefits

- ✅ **Dynamic character switching** (no model reload)
- ✅ **A/B testing** of personalities
- ✅ **Per-user customization**
- ✅ **Easier debugging** (standard API)
- ✅ **Better documentation** (OpenAI ecosystem)

---

## Next Steps

1. **Review this plan** - Confirm approach and timeline
2. **Set up vLLM on Linux** - Install and configure production server
3. **Implement Phase 1** - Create LLM client abstraction
4. **Test character preservation** - Verify Eve works correctly
5. **Deploy to production** - Gradual rollout with monitoring

**Ready to start?** Let me know and I'll begin implementing Phase 1.
