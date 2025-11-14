# Modelservice Architecture

## Overview ✅

`modelservice` is a **ZeroMQ-based service** that provides unified access to foundational AI models, primarily integrating with Ollama for LLM inference. It communicates via encrypted message bus rather than REST API.

## Current Implementation ✅

- **Protocol**: ZeroMQ message bus (not REST)
- **Port**: Internal message bus communication (5555/5556)
- **Encryption**: CurveZMQ encrypted transport
- **Model Runner**: Ollama with native binary management
- **Integration**: Direct ZMQ topics for backend communication

## Features ✅

- **Text Generation**: LLM completions via ZMQ message topics with streaming support
- **Embeddings**: Sentence-transformers for semantic embeddings (768-dim)
- **Entity Extraction**: GLiNER Medium v2.1 for zero-shot NER
- **Sentiment Analysis**: BERT Multilingual, RoBERTa emotion classification
- **Intent Classification**: XLM-RoBERTa for multilingual intent understanding
- **Model Management**: List, pull, and remove Ollama models
- **Health Monitoring**: Service and Ollama status checks
- **Ollama Integration**: Complete lifecycle management with auto-installation
- **Streaming Responses**: Real-time token streaming via WebSocket integration

## OllamaManager ✅

**Core Component**: Complete Ollama lifecycle management

- **Auto-Installation**: Downloads platform-specific binaries from GitHub releases
- **Process Management**: Subprocess lifecycle with startup/shutdown
- **Health Monitoring**: Continuous health checks and restart on failure
- **Model Management**: Auto-pull default models and resource management

### Binary Management ✅

**Installation Paths**:
- **Windows**: `%LOCALAPPDATA%\boeni-industries\aico\bin\ollama.exe`
- **macOS**: `~/Library/Application Support/boeni-industries/aico/bin/ollama`
- **Linux**: `~/.local/share/boeni-industries/aico/bin/ollama`

**Features**: Platform detection, GitHub releases API, SHA256 verification

### Configuration ✅

**Environment Variables**:
```bash
OLLAMA_MODELS=/path/to/aico/models
OLLAMA_HOST=127.0.0.1:11434
OLLAMA_NUM_PARALLEL=4        # Concurrent requests (Ollama 0.12+)
OLLAMA_MAX_LOADED_MODELS=2   # Max models in memory
OLLAMA_MAX_QUEUE=128         # Max queued requests
```

**Port**: 11434 (from core.yaml configuration)

**Resource Management** (core.yaml):
```yaml
modelservice:
  ollama:
    resources:
      auto_unload_minutes: 30
      max_concurrent_models: 2
      memory_threshold_percent: 85
```

### Model Storage ✅

**Directory Structure**:
- **Linux**: `~/.local/share/boeni-industries/aico/models/`
- **macOS**: `~/Library/Application Support/boeni-industries/aico/models/`
- **Windows**: `%LOCALAPPDATA%\boeni-industries\aico\models\`

**Isolation**: All model data contained within AICO directory structure

### Native Binary Approach ✅

Local-first design with zero external dependencies. No Docker required for simplified installation and better user experience.

## Logging Integration ✅

**ZMQ Transport**: Ollama logs routed through message bus to Log Consumer
**Unified Storage**: Encrypted database storage with other system logs
**CLI Access**: Available via `aico logs` commands

**Fallback Paths**:
- **Linux**: `~/.local/share/boeni-industries/aico/logs/ollama.log`
- **macOS**: `~/Library/Application Support/boeni-industries/aico/logs/ollama.log`
- **Windows**: `%LOCALAPPDATA%\boeni-industries\aico\logs\ollama.log`

## Security ✅

**Transport Encryption**: CurveZMQ for all message bus communication
**Message Validation**: Protocol Buffer schema validation
**Access Control**: Internal service-to-service communication only
**Logging**: All operations logged via ZMQ transport to encrypted database

## ZMQ Message Topics ✅

**Completions**:
- Request: `modelservice/completions/request/v1`
- Response: `modelservice/completions/response/v1`
- Streaming: `modelservice/completions/stream/v1`

**Embeddings**:
- Request: `modelservice/embeddings/request/v1`
- Response: `modelservice/embeddings/response/v1`

**NER (Named Entity Recognition)**:
- Request: `modelservice/ner/request/v1`
- Response: `modelservice/ner/response/v1`

**Sentiment Analysis**:
- Request: `modelservice/sentiment/request/v1`
- Response: `modelservice/sentiment/response/v1`

**Ollama Management**:
- `ollama/status/request`
- `ollama/models/request`
- `ollama/models/pull/request`
- `ollama/models/remove/request`

**Message Format**: Protocol Buffer serialization with correlation IDs and versioned topics

## CLI Integration ✅

### Ollama Commands
```bash
aico ollama status          # Ollama status and running models
aico ollama models list     # List available models
aico ollama models pull     # Download models
aico ollama models remove   # Remove models
aico ollama logs           # View Ollama logs
```

### Modelservice Commands
```bash
aico modelservice start     # Start modelservice with Ollama
aico modelservice stop      # Stop modelservice
aico modelservice status    # Service health check
aico modelservice test      # Test completions and embeddings
```

**Communication**: CLI uses ZMQ message bus for modelservice operations

### Character Model Generation
```bash
aico ollama generate eve    # Create Eve character from Modelfile
aico ollama generate eve --force  # Regenerate after Modelfile changes
```

**Modelfiles**: Custom character personalities defined in `config/modelfiles/`

## Integration Pattern ✅

- **Backend Communication**: ZMQ message bus topics (not REST)
- **Model Access**: Only modelservice communicates with Ollama directly
- **Encapsulation**: All model logic contained within modelservice
- **Logging**: Unified ZMQ transport to encrypted database
- **Security**: CurveZMQ encryption for all communications

## Security & Deployment ✅

- **Local-Only**: Runs on localhost with no external network access
- **Encrypted Transport**: CurveZMQ for all message bus communication
- **Process Isolation**: Ollama managed as subprocess with controlled environment
- **No HTTP Endpoints**: Pure ZMQ message-based communication

## Current Status ✅

**Production Ready**: ZMQ-based service with complete Ollama integration and transformers support

**Default Models**:
- **Conversation**: `huihui_ai/qwen3-abliterated:8b-v2` (primary, auto-pull, priority 1)
- **Vision**: `llama3.2-vision:11b` (optional, priority 2)
- **Lightweight**: `llama3.2:1b` (optional, priority 4)

**Transformers Models**:
- **Entity Extraction**: GLiNER Medium v2.1 (urchade/gliner_medium-v2.1)
- **Embeddings**: Sentence-Transformers Paraphrase Multilingual MPNet
- **Sentiment**: BERT Multilingual, RoBERTa Emotion, Twitter RoBERTa
- **Intent**: XLM-RoBERTa Base

**Ollama 0.12+ Features**:
- **Parallel Processing**: 4 concurrent requests per model
- **Max Loaded Models**: 2 models simultaneously
- **Max Queue**: 128 requests
- **Auto-unload**: Models unload after 30 minutes of inactivity

**Auto-Management**: Binary installation, model pulling, and lifecycle management
**Integration**: Full message bus integration with backend conversation system and streaming support

**Future**: Additional model runners and inference types via same ZMQ pattern
