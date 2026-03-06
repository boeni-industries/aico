# LLM Serving Architecture for AICO

## Executive Summary

**Problem:** Docker containers on macOS cannot access GPU acceleration due to Apple's Virtualization Framework limitations. Current Ollama container runs at 100% CPU utilization with no Metal/MPS access, resulting in extremely slow LLM inference.

**Solution:** Run LLM inference engine natively on host OS for direct GPU access, while keeping application services containerized.

## Current Architecture (Problematic)

```
┌─────────────────────────────────────────────┐
│   Docker Compose                            │
│                                             │
│   ┌─────────────────────────────────────┐  │
│   │  Ollama Container                   │  │
│   │  - CPU ONLY (no GPU access)         │  │
│   │  - 100% CPU utilization             │  │
│   │  - 5.7 GB model in CPU memory       │  │
│   │  - M2 Max GPU idle (38 cores)       │  │
│   └─────────────────────────────────────┘  │
│                                             │
│   [Backend, Modelservice, PostgreSQL, etc.] │
└─────────────────────────────────────────────┘
```

**Performance Issues:**
- 100% CPU utilization
- Slow response times (10-20s per request)
- M2 Max GPU completely unused
- No concurrency control
- Memory inefficiency

## Professional Best Practices

### Industry Standard Deployment Patterns

Based on research of production LLM deployments:

1. **Native Inference Engine Execution**
   - LLM inference runs directly on host OS
   - Direct GPU access (Metal/CUDA/ROCm)
   - Zero virtualization overhead
   - Maximum performance

2. **Containerized Application Logic**
   - API gateways, business logic, databases in containers
   - Stateless services benefit from containerization
   - Inference engine accessed via HTTP/gRPC

3. **Professional Inference Engines**
   - **vLLM**: Production serving, high concurrency, PagedAttention
   - **TGI**: HuggingFace ecosystem, good documentation
   - **TensorRT-LLM**: Ultra-low latency (NVIDIA only)
   - **Ollama**: Development/prototyping only

### Why Docker + GPU Doesn't Work on macOS

**Technical Limitation:**
- Apple's mandatory Virtualization Framework blocks GPU passthrough
- Docker Desktop on Mac: CPU only, no Metal/MPS access
- No workaround exists (platform limitation, not configuration)

**Quote from Docker documentation:**
> "Docker Desktop on Windows with WSL supports GPU acceleration, not Docker Desktop on Mac."

**Quote from Andreas Kunar (Apple Silicon LLM expert):**
> "Apple's mandatory 'Apple Virtualization Framework' seems mostly to blame for this, the silicon should technically support it from M2 onwards. Parallels, Docker,… all have to use it."

## Recommended Architecture

### Option 1: Native Ollama (Development/Local)

**Architecture:**
```
┌─────────────────────────────────────────────┐
│   macOS Host (M2 Max)                       │
│                                             │
│   ┌─────────────────────────────────────┐  │
│   │  Ollama (Native Process)            │  │
│   │  - Direct Metal GPU access          │  │
│   │  - Port 11434                       │  │
│   │  - Full GPU utilization (38 cores)  │  │
│   │  - 5-10x faster than CPU            │  │
│   └─────────────────────────────────────┘  │
│              ↕ HTTP                         │
│   ┌─────────────────────────────────────┐  │
│   │  Docker Compose                     │  │
│   │  - Backend (gateway/core)           │  │
│   │  - Modelservice (connects to        │  │
│   │    localhost:11434)                 │  │
│   │  - PostgreSQL, NATS, InfluxDB, etc. │  │
│   └─────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**Installation:**
```bash
# Install Ollama natively on macOS
brew install ollama

# Start Ollama service (runs with Metal GPU access)
ollama serve

# Pull model
ollama pull huihui_ai/qwen3-abliterated:8b-v2
```

**Configuration Changes:**
```yaml
# config/defaults/modelservice.yaml
ollama:
  host: "localhost"  # Changed from "ollama" (container name)
  port: 11434
  auto_install: false
  auto_start: false  # Managed by user/system service
```

**Docker Compose Changes:**
```yaml
# docker/docker-compose.local.yml
# Remove entire ollama service definition
# Modelservice connects to host's Ollama via localhost:11434
```

**Pros:**
- ✅ Full M2 Max GPU acceleration (Metal)
- ✅ 5-10x faster inference vs CPU
- ✅ Simple migration (minimal code changes)
- ✅ Keep existing AICO architecture
- ✅ Works on development machines

**Cons:**
- ⚠️ Ollama not production-grade for high concurrency
- ⚠️ Manual Ollama installation required
- ⚠️ Not suitable for cloud deployment

**Use Case:** Local development, personal use, prototyping

### Option 2: Native vLLM (Production-Ready)

**Architecture:**
```
┌─────────────────────────────────────────────┐
│   Linux Host (NVIDIA GPU)                   │
│                                             │
│   ┌─────────────────────────────────────┐  │
│   │  vLLM Server (Native Process)       │  │
│   │  - OpenAI-compatible API            │  │
│   │  - PagedAttention algorithm         │  │
│   │  - Continuous batching              │  │
│   │  - 4-8 parallel requests            │  │
│   │  - Port 8000                        │  │
│   └─────────────────────────────────────┘  │
│              ↕ HTTP (OpenAI API)            │
│   ┌─────────────────────────────────────┐  │
│   │  Docker Compose                     │  │
│   │  - Backend (OpenAI-compatible       │  │
│   │    client to vLLM)                  │  │
│   │  - All other services               │  │
│   └─────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**Installation:**
```bash
# Install vLLM on Linux with NVIDIA GPU
pip install vllm

# Start vLLM server with OpenAI-compatible API
vllm serve huihui_ai/qwen3-abliterated:8b-v2 \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.9
```

**Configuration Changes:**
```yaml
# config/defaults/modelservice.yaml
ollama:
  # Replace with vLLM configuration
  enabled: false

vllm:
  enabled: true
  host: "localhost"
  port: 8000
  api_type: "openai"  # OpenAI-compatible API
  max_concurrent_requests: 8
```

**Code Changes Required:**
- Add vLLM client to modelservice
- Implement OpenAI-compatible API adapter
- Update request/response handling

**Pros:**
- ✅ Production-grade performance
- ✅ High concurrency (4-8 parallel requests)
- ✅ PagedAttention for efficient memory usage
- ✅ Continuous batching for throughput
- ✅ OpenAI-compatible API (easy integration)
- ✅ Industry standard for production

**Cons:**
- ⚠️ Requires Linux + NVIDIA GPU
- ⚠️ More complex setup
- ⚠️ Not compatible with M2 Max (no Metal support)
- ⚠️ Requires code changes in AICO

**Use Case:** Production deployment, cloud hosting, high-traffic applications

### Option 3: Hybrid Approach (Recommended)

**Strategy:**
```
Development Environment (macOS):
  - Native Ollama with Metal GPU
  - Docker for backend services
  - Fast local development

Production Environment (Linux):
  - Native vLLM with CUDA GPU
  - Docker for backend services
  - High-performance serving

Shared:
  - Same AICO codebase
  - Abstracted LLM client interface
  - Configuration-driven deployment
```

**Implementation:**
```python
# shared/aico/ai/llm/client.py
class LLMClientFactory:
    @staticmethod
    def create(config: dict) -> LLMClient:
        engine = config.get("engine", "ollama")
        
        if engine == "ollama":
            return OllamaClient(config)
        elif engine == "vllm":
            return VLLMClient(config)
        elif engine == "openai":
            return OpenAIClient(config)
        else:
            raise ValueError(f"Unknown LLM engine: {engine}")
```

**Configuration:**
```yaml
# config/environments/development.yaml
llm:
  engine: "ollama"
  host: "localhost"
  port: 11434

# config/environments/production.yaml
llm:
  engine: "vllm"
  host: "localhost"
  port: 8000
  api_type: "openai"
```

**Pros:**
- ✅ Best of both worlds
- ✅ Fast local development (Ollama + Metal)
- ✅ Production-grade deployment (vLLM + CUDA)
- ✅ Same codebase for both environments
- ✅ Easy migration path

**Cons:**
- ⚠️ Requires abstraction layer
- ⚠️ More configuration complexity
- ⚠️ Need to test both engines

**Use Case:** Professional development with production deployment

## Migration Plan

### Phase 1: Immediate Fix (Development Environment)

**Goal:** Get GPU acceleration working on M2 Max

**Steps:**
1. Install Ollama natively on macOS
   ```bash
   brew install ollama
   ollama serve
   ollama pull huihui_ai/qwen3-abliterated:8b-v2
   ```

2. Update configuration
   ```yaml
   # config/defaults/modelservice.yaml
   ollama:
     host: "localhost"
     port: 11434
   ```

3. Remove Ollama from docker-compose.local.yml
   ```yaml
   # Comment out or remove ollama service
   ```

4. Restart AICO services
   ```bash
   cd docker
   docker compose -f docker-compose.local.yml down
   docker compose -f docker-compose.local.yml up -d
   ```

5. Verify GPU usage
   ```bash
   # Check Ollama logs for [metal] indicator
   tail -f ~/.ollama/logs/server.log
   ```

**Expected Results:**
- 5-10x faster LLM responses
- 50-70% GPU utilization (Metal)
- CPU usage drops to 20-30%
- Smooth conversation experience

**Effort:** 30 minutes
**Risk:** Low (easy rollback)

### Phase 2: Production Architecture (Future)

**Goal:** Prepare for production deployment

**Steps:**
1. Design LLM client abstraction layer
2. Implement vLLM client adapter
3. Add OpenAI-compatible API support
4. Create production configuration
5. Test on Linux + NVIDIA GPU
6. Document deployment procedures

**Effort:** 2-3 days
**Risk:** Medium (requires testing)

### Phase 3: Cloud Deployment (Optional)

**Goal:** Enable cloud-based LLM serving

**Options:**
- AWS EC2 with GPU instances (g5.xlarge)
- GCP Compute Engine with GPU
- Azure NC-series VMs
- Managed services (AWS Bedrock, etc.)

**Considerations:**
- Cost optimization (spot instances)
- Auto-scaling for traffic spikes
- Model caching strategies
- Monitoring and observability

## Performance Expectations

### Current Performance (Docker Ollama - CPU Only)
- **Response Time:** 10-20 seconds
- **CPU Usage:** 100%
- **GPU Usage:** 0%
- **Throughput:** 1-2 requests/minute
- **Concurrency:** 1 request at a time

### After Migration (Native Ollama - Metal GPU)
- **Response Time:** 1-3 seconds (5-10x faster)
- **CPU Usage:** 20-30%
- **GPU Usage:** 50-70%
- **Throughput:** 10-20 requests/minute
- **Concurrency:** 2-4 requests simultaneously

### Production Setup (vLLM - CUDA GPU)
- **Response Time:** 0.5-1.5 seconds
- **GPU Usage:** 70-90%
- **Throughput:** 50-100 requests/minute
- **Concurrency:** 8-16 requests simultaneously
- **Batching:** Continuous batching for efficiency

## Monitoring and Observability

### Key Metrics to Track

**Inference Performance:**
- Time to First Token (TTFT)
- Tokens per second
- Request latency (p50, p95, p99)
- GPU utilization
- Memory usage

**System Health:**
- Request queue depth
- Error rates
- Model load/unload events
- Cache hit rates

**Tools:**
- Prometheus + Grafana (already in AICO)
- vLLM built-in metrics endpoint
- Custom instrumentation in modelservice

## Security Considerations

### Native Process Security

**Concerns:**
- LLM process runs outside container isolation
- Direct network exposure (port 11434/8000)
- Model file access permissions

**Mitigations:**
- Firewall rules (localhost-only binding)
- Process isolation (dedicated user account)
- File permissions (read-only model directory)
- TLS/mTLS for production deployments

### API Security

**Current:** AICO backend → Ollama (HTTP, no auth)
**Production:** AICO backend → vLLM (HTTP + API key)

**Recommendations:**
- API key authentication for vLLM
- Rate limiting at application level
- Request validation and sanitization
- Audit logging for all LLM requests

## Cost Analysis

### Development (Native Ollama)
- **Hardware:** M2 Max (already owned)
- **Software:** Free (Ollama open source)
- **Operational:** $0/month

### Production (Native vLLM on Cloud)
- **AWS g5.xlarge:** ~$1.00/hour (~$730/month)
- **GCP n1-standard-4 + T4:** ~$0.60/hour (~$440/month)
- **Spot instances:** 50-70% discount
- **Reserved instances:** 30-50% discount

### Production (Self-Hosted)
- **Hardware:** NVIDIA RTX 4090 (~$1,600 one-time)
- **Power:** ~$30/month (450W @ $0.12/kWh)
- **Maintenance:** Minimal
- **Break-even:** ~2-3 months vs cloud

## References

### Research Sources
- [vLLM vs TGI vs TensorRT-LLM vs Ollama](https://compute.hivenet.com/post/vllm-vs-tgi-vs-tensorrt-llm-vs-ollama)
- [Apple Silicon GPUs, Docker and Ollama: Pick two](https://chariotsolutions.com/blog/post/apple-silicon-gpus-docker-and-ollama-pick-two/)
- [Ray Serve LLM Deployment with vLLM](https://medium.com/@kaige.yang0110/ray-serve-llm-deployment-with-vllm-qwen-model-28293a36b072)

### Key Insights
> "Use Ollama for rapid prototyping and development. Once applications mature, migrate to vLLM or TGI for production deployment where performance and reliability become critical."

> "Docker Desktop on Mac does not see the GPU. Apple's mandatory Virtualization Framework blocks GPU passthrough."

> "Native Ollama on Apple Silicon with Metal support provides 5-10x performance improvement over CPU-only execution."

## Conclusion

**Immediate Action:** Migrate Ollama out of Docker to native execution on macOS for GPU acceleration.

**Long-term Strategy:** Implement hybrid architecture with Ollama for development and vLLM for production.

**Expected Impact:** 5-10x faster LLM inference, better user experience, production-ready architecture.
