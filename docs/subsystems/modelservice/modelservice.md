# Modelservice Architecture

## Purpose
`modelservice` is a minimal, REST-based subsystem that provides a unified API gateway to foundational large language model (LLM) inference, initially integrating with Ollama. It abstracts direct model runner access, ensuring modularity, security, and future extensibility for additional foundational models.

## Architectural Role
- **Gateway/Proxy:** Sits between the AICO backend and foundational model runners (e.g., Ollama), exposing a simple REST API for inference and model management.
- **Abstraction:** Shields the rest of the system from model runner specifics, versioning, and protocol changes.
- **Security:** Restricts model runner access to only the backend via the modelservice API.
- **Extensibility:** Designed to support additional model runners and inference types in the future, not just LLMs. This gateway will be the integration point for all foundational models, including embeddings, vision, and other modalities as AICO evolves.

## Features (Minimal, LLM/Ollama Focus)
- **Text Generation Endpoint:** Unified REST endpoint for generating completions from foundational LLMs.
- **Model Info Endpoint:** Query available models and their metadata.
- **Health Endpoint:** Liveness/readiness check for orchestration.
- **Extensible Model Types:** While LLMs are the first and core supported type, the architecture is designed to support other foundational model types (e.g., embedding models, vision models) via the same gateway and API pattern.

## Model Runner Integration: Native Binary Approach

### OllamaManager Component
The `OllamaManager` is a core component within modelservice responsible for complete Ollama lifecycle management:

- **Automated Installation:** Downloads platform-specific Ollama binaries from GitHub releases API with zero user intervention
- **Binary Management:** Installs Ollama in AICO's controlled `/bin` directory structure
- **Process Lifecycle:** Manages Ollama as a subprocess with proper startup, monitoring, and graceful shutdown
- **Health Monitoring:** Continuous health checks and automatic restart on failure
- **Update Management:** Automatic updates via GitHub releases API with version tracking

### Cross-Platform Binary Management
- **Platform Detection:** Automatically detects OS and architecture for correct binary selection
- **GitHub Releases Integration:** Uses official Ollama releases API for reliable, versioned downloads
- **Binary Verification:** SHA256 checksum validation for security and integrity
- **Installation Paths:**
  - **Windows:** `%LOCALAPPDATA%\boeni-industries\aico\bin\ollama.exe`
  - **macOS:** `~/Library/Application Support/boeni-industries/aico/bin/ollama`
  - **Linux:** `~/.local/share/boeni-industries/aico/bin/ollama`

### Environment Configuration
OllamaManager configures Ollama with AICO-specific environment variables:
```bash
OLLAMA_MODELS=/path/to/aico/models     # Model storage in AICO structure
OLLAMA_LOGS=/path/to/aico/logs/ollama.log  # Logs in AICO directory
OLLAMA_HOST=127.0.0.1:11434           # Local-only binding
OLLAMA_KEEP_ALIVE=5m                  # Resource-aware model unloading
```

### Model Storage and Directory Structure

Ollama's model storage is fully contained within the AICO deployment directory structure, following AICO's OS-specific standard path conventions (see `/shared/`).

- **Model Directory:**
  - All Ollama models (blobs and manifests) are stored in a dedicated `models` directory directly under the AICO root directory (as resolved by the configuration system for each OS).
  - This path is managed and set by AICO, using the `OLLAMA_MODELS` environment variable at runtime to ensure Ollama does not store data outside the deployment directory.
  - Example (all under the vendor/product root directory):
    - **Linux:** `${XDG_DATA_HOME:-$HOME/.local/share}/boeni-industries/aico/models/`
    - **macOS:** `$HOME/Library/Application Support/boeni-industries/aico/models/`
    - **Windows:** `%LOCALAPPDATA%\boeni-industries\aico\models\`
  - This guarantees that all model files are isolated from user or system-wide locations and are managed exclusively by AICO.

- **Symlink Alternative:**
  - On Unix-like systems, a symlink from the default Ollama models directory to the AICO-managed models directory may be used as an alternative for compatibility.

- **No Data Leakage:**
  - No model data is written outside the AICO deployment structure, supporting strict containment and easy backup/restore.

### Why Native Binary?
AICO is designed for local-first, privacy-first, and non-expert-friendly installation. Docker is not required, as it adds bloat and complexity. Native binaries provide the best user experience, performance, and compatibility.

### Logging Integration

Ollama logs are integrated into AICO's unified logging system:

- **ZMQ Log Transport:** Ollama logs are captured and routed through AICO's ZeroMQ message bus to the central Log Consumer service
- **Unified Log Storage:** All Ollama logs are stored in the encrypted AICO database alongside other system logs
- **Log Directory Fallback:** Local `ollama.log` file in AICO's logs directory as backup when ZMQ transport unavailable
- **Structured Format:** Ollama output parsed and formatted as structured log entries with proper timestamps and levels
- **CLI Access:** Ollama logs accessible via `aico logs` commands with filtering and search capabilities

**Log Paths (fallback only):**
- **Linux:** `${XDG_DATA_HOME:-$HOME/.local/share}/boeni-industries/aico/logs/ollama.log`
- **macOS:** `$HOME/Library/Application Support/boeni-industries/aico/logs/ollama.log`
- **Windows:** `%LOCALAPPDATA%\boeni-industries\aico\logs\ollama.log`

## Middleware & Security Stack
- **Encryption:** All inbound and outbound payloads are encrypted using the same libsodium/session-based encryption as the API Gateway (EncryptionMiddleware).
- **Security:** Request sanitization, IP filtering, and attack surface minimization via SecurityMiddleware.
- **Rate Limiting:** Per-client request throttling using token bucket algorithm (RateLimiter).
- **Validation:** Strict schema/protobuf validation for all request/response payloads (MessageValidator).
- **Request Logging:** All requests and responses are logged via ZMQ transport using the RequestLoggingMiddleware, ensuring consistent audit trails across the platform.
- **Shared Security:** Integrates with AICOKeyManager for key management, SecureTransportChannel for encrypted transport, and SessionService for JWT/session validation.

> All middleware is reused or extended from the API Gateway and shared security modules to ensure architectural consistency and robust security.

## REST API Endpoints

### 1. `POST /api/v1/completions`
- **Purpose:** Generate one or more completions from a foundational LLM (Ollama), following the industry-standard endpoint naming (plural) and the API Gateway route structure (`/api/v1/`).
- **Request:**
  ```json
  {
    "model": "llama3",
    "prompt": "Hello, how are you?",
    "parameters": {
      "max_tokens": 128,
      "temperature": 0.7
    }
  }
  ```
- **Response:**
  ```json
  {
    "completion": "I'm well, thank you! How can I help you today?",
    "model": "llama3",
    "usage": { "prompt_tokens": 6, "completion_tokens": 15 }
  }
  ```

### 2. `GET /v1/models`
- **Purpose:** List available foundational models (from Ollama or others). The endpoint will be extended to support other model types in the future.
- **Response:**
  ```json
  [
    { "name": "llama3", "description": "Meta Llama 3 8B", "status": "loaded", "type": "llm" },
    { "name": "mistral", "description": "Mistral 7B", "status": "available", "type": "llm" },
    { "name": "clip", "description": "CLIP Vision Model", "status": "available", "type": "vision" }
  ]
  ```

### 3. `GET /v1/health`
- **Purpose:** Health check for orchestration/monitoring.
- **Response:**
  ```json
  { "status": "ok" }
  ```

## CLI Integration

### Command Groups
- **`aico ollama`** - Direct Ollama and model management commands
- **`aico modelservice`** - Modelservice operations (start/stop/status/health)

### Ollama Commands (`aico ollama`)
```bash
aico ollama status          # Show Ollama status and running models
aico ollama install         # Force reinstall/update Ollama binary
aico ollama models list     # List available and installed models
aico ollama models pull     # Download specific models
aico ollama models remove   # Remove models to free space
aico ollama logs           # View Ollama-specific logs
aico ollama serve          # Start Ollama directly (debug mode)
```

### Modelservice Commands (`aico modelservice`)
```bash
aico modelservice start     # Start modelservice with OllamaManager
aico modelservice stop      # Stop modelservice and Ollama
aico modelservice status    # Service health and endpoint status
aico modelservice health    # Detailed health check and diagnostics
```

### CLI Integration Architecture
- **Rich Visual Style:** Follows AICO CLI visual guide with cyan headers, green values, and clean tables
- **Shared Logic:** CLI commands use modelservice REST API and OllamaManager for consistency
- **Error Handling:** Actionable error messages with clear next steps
- **Progress Indicators:** Rich progress bars for model downloads and installations

## Integration Pattern
- The backend interacts with `modelservice` via REST.
- Only `modelservice` talks directly to foundational model runners (e.g., Ollama, embedding servers, vision model servers).
- All model-specific logic, parameters, and error handling are encapsulated in `modelservice`.
- Logging, security, and validation are handled consistently with the API Gateway, including ZMQ-based request logging.
- **OllamaManager** handles all Ollama binary management, process lifecycle, and environment configuration.

## Security & Deployment
- Only accessible within the trusted network (e.g., Docker compose, localhost, or VPN).
- No direct access to model runners from outside the modelservice container.
- Minimal surface area: only exposes essential endpoints for foundational model inference and info.

## Extensibility (Future)
- Support for embeddings, vision, or other foundational models.
- Pluggable adapters for additional model runners.
- Advanced model management (load/unload, update, metrics).

---

**Status:** MVP design focuses on LLM (Ollama) integration and minimal REST API. All additional foundational model types will be integrated through this gateway as AICO evolves.
