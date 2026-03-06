# vLLM Deployment Guide

## Platform-Aware Deployment

AICO's vLLM integration automatically detects your platform and deploys using the optimal method:

- **Linux**: Docker container with GPU support
- **macOS**: Native daemon (CPU mode)
- **Windows**: Docker container with GPU support

---

## Quick Start

### Deploy vLLM

```bash
# Deploy with default character (Eve)
aico vllm deploy

# Deploy with specific character
aico vllm deploy --character joi

# Force restart if already running
aico vllm deploy --force

# Run in foreground (for debugging)
aico vllm deploy --foreground
```

### Check Status

```bash
aico vllm status
```

### Stop Server

```bash
aico vllm stop
```

---

## Platform-Specific Details

### macOS Deployment

**Method**: Native Python daemon

**What Happens**:
1. Checks if vLLM is installed (installs if missing)
2. Starts vLLM server as background process
3. Saves PID to `~/.aico/vllm.pid`
4. Logs to `/tmp/vllm.log`

**Command**:
```bash
python -m vllm.entrypoints.openai.api_server \
  --model huihui_ai/qwen3-abliterated:8b-v2 \
  --host 0.0.0.0 \
  --port 8774 \
  --device cpu \
  --max-model-len 8192
```

**Notes**:
- Runs in CPU mode (vLLM doesn't support Metal yet)
- First request will be slow (model loading)
- Use `tail -f /tmp/vllm.log` to monitor

### Linux Deployment

**Method**: Docker container with GPU

**What Happens**:
1. Checks Docker is installed
2. Stops/removes existing container if present
3. Pulls `vllm/vllm-openai:latest` image
4. Starts container with GPU passthrough
5. Maps port 8774 (host) → 8000 (container)

**Command**:
```bash
docker run -d \
  --name aico-vllm \
  --gpus all \
  -p 8774:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model huihui_ai/qwen3-abliterated:8b-v2 \
  --host 0.0.0.0 \
  --port 8000 \
  --gpu-memory-utilization 0.9 \
  --max-num-seqs 16 \
  --max-model-len 8192
```

**Notes**:
- Requires NVIDIA GPU + nvidia-docker
- First run downloads model (~5GB)
- Use `docker logs -f aico-vllm` to monitor

### Windows Deployment

**Method**: Docker container (same as Linux)

**What Happens**:
Same as Linux, but without `--gpus all` flag (unless WSL2 + NVIDIA GPU)

**Notes**:
- Requires Docker Desktop
- GPU support requires WSL2 + NVIDIA drivers
- Falls back to CPU if no GPU

---

## API Endpoint

All deployments expose the same OpenAI-compatible API:

```
http://localhost:8774
```

**Endpoints**:
- `GET /v1/models` - List loaded models
- `POST /v1/chat/completions` - Chat completion
- `GET /health` - Health check

---

## CLI Output Examples

### macOS Deployment

```
🚀 vLLM Deployment

→ Detected platform: Darwin
→ Character: eve
→ Model: huihui_ai/qwen3-abliterated:8b-v2

📱 macOS Deployment Strategy
vLLM on macOS runs natively (no Docker GPU support)

✓ vLLM 0.11.0 installed

Starting vLLM server...
Command: python -m vllm.entrypoints.openai.api_server --model huihui_ai/qwen3-abliterated:8b-v2 --host 0.0.0.0 --port 8774 --device cpu --max-model-len 8192

→ Starting as background daemon
✓ vLLM daemon started (PID: 12345)
Logs: /tmp/vllm.log
API: http://localhost:8774

Note: First request will be slow (model loading)
```

### Linux Deployment

```
🚀 vLLM Deployment

→ Detected platform: Linux
→ Character: eve
→ Model: huihui_ai/qwen3-abliterated:8b-v2

🐳 Docker Deployment (Linux)
vLLM will run in Docker container with GPU support

✓ Docker version 24.0.7, build afdd53b

→ GPU support enabled (--gpus all)

Starting vLLM Docker container...
Command: docker run --name aico-vllm -p 8774:8000 -v /home/user/.cache/huggingface:/root/.cache/huggingface...

→ Starting as detached container
✓ vLLM container started (a1b2c3d4e5f6)
Container: aico-vllm
API: http://localhost:8774
Logs: docker logs -f aico-vllm

Note: First request will be slow (model downloading + loading)
```

---

## Troubleshooting

### macOS: "vLLM not installed"

The CLI will automatically install vLLM. If it fails:

```bash
pip install vllm
```

### Linux: "Docker not found"

Install Docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### Linux: "GPU not detected"

Install nvidia-docker:

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### Port 8774 Already in Use

Stop the existing server:

```bash
aico vllm stop
```

Or use `--force` to restart:

```bash
aico vllm deploy --force
```

### Model Not Loading

Check logs:

**macOS**:
```bash
tail -f /tmp/vllm.log
```

**Linux/Windows**:
```bash
docker logs -f aico-vllm
```

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  vLLM Server (Separate Process)             │
│  - macOS: Native daemon                      │
│  - Linux/Windows: Docker container          │
│  - Port 8774                                 │
│  - OpenAI-compatible API                     │
└─────────────────────────────────────────────┘
                    ↕ HTTP
┌─────────────────────────────────────────────┐
│  AICO Backend                                │
│  - Conversation Engine                       │
│  - VLLMClient (HTTP client)                 │
│  - Character Manager                         │
└─────────────────────────────────────────────┘
```

---

## Configuration

### Character Configuration

`config/defaults/characters.yaml`:

```yaml
characters:
  eve:
    base_model: "huihui_ai/qwen3-abliterated:8b-v2"
    system_prompt: |
      You are Eve...
    parameters:
      temperature: 0.7
      top_k: 20
```

### LLM Configuration

`config/defaults/llm.yaml`:

```yaml
vllm:
  host: "localhost"
  port: 8774
  api_key: "EMPTY"
  default_character: "eve"
```

---

## Production Deployment

For production, consider:

1. **Kubernetes + Helm** (official vLLM Production Stack)
2. **systemd service** (Linux servers)
3. **Docker Compose** (multi-service orchestration)

See: https://github.com/vllm-project/production-stack

---

## Summary

- ✅ **Zero configuration**: Detects platform and deploys optimally
- ✅ **Clear output**: Shows exactly what's being done
- ✅ **Consistent API**: Always `http://localhost:8774`
- ✅ **Easy management**: `deploy`, `stop`, `status` commands
- ✅ **Cross-platform**: macOS, Linux, Windows support
