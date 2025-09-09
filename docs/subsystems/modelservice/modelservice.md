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

- **Text Generation**: LLM completions via ZMQ message topics
- **Model Management**: List, pull, and remove Ollama models
- **Health Monitoring**: Service and Ollama status checks
- **Ollama Integration**: Complete lifecycle management with auto-installation

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
OLLAMA_KEEP_ALIVE=-1  # Keep models loaded
```

**Port**: 11434 (from core.yaml configuration)

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

**Completions**: `modelservice.completions.request`
**Models**: `modelservice.models.request`
**Health**: `modelservice.health.request`
**Status**: `modelservice.status.request`

**Ollama Management**:
- `ollama.status.request`
- `ollama.models.request`
- `ollama.models.pull.request`
- `ollama.models.remove.request`

**Message Format**: Protocol Buffer serialization with correlation IDs

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
```

**Communication**: CLI uses ZMQ message bus for modelservice operations

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

**Production Ready**: ZMQ-based service with complete Ollama integration
**Default Models**: `hermes3:8b` for conversation, vision models available
**Auto-Management**: Binary installation, model pulling, and lifecycle management
**Integration**: Full message bus integration with backend conversation system

**Future**: Additional model runners and inference types via same ZMQ pattern
