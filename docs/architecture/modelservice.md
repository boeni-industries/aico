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
- **Native Binary Integration:** AICO modelservice manages the model runner (Ollama) as a native binary subprocess. No Docker or container engine is required.
- **Maximum UX:** All packaging, downloading, installation, and updates for Ollama are handled automatically by AICO. Users do not need to manually install or configure anything.
- **Cross-Platform:** Prebuilt binaries for Ollama are available for Windows (10+), macOS (12+), and Linux (x86_64/AMD64). AICO detects the user's OS and downloads/installs the correct binary as needed.
- **Lifecycle Management:** AICO starts, stops, and monitors the Ollama process transparently, providing clear error/help messages if any issues arise.
- **Fallback:** In-process model serving (e.g., using llama.cpp Python bindings) may be supported as a lightweight fallback for certain models or platforms in the future.

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

### Logging

Ollama logs are fully contained within the AICO deployment structure:

- **Log Directory:**
  - All Ollama logs are written to `ollama.log` inside the `logs` directory directly under the AICO root directory (as resolved by the configuration system for each OS).
  - Example (all under the vendor/product root directory):
    - **Linux:** `${XDG_DATA_HOME:-$HOME/.local/share}/boeni-industries/aico/logs/ollama.log`
    - **macOS:** `$HOME/Library/Application Support/boeni-industries/aico/logs/ollama.log`
    - **Windows:** `%LOCALAPPDATA%\boeni-industries\aico\logs\ollama.log`
  - Logging is configured at runtime by redirecting Ollama's output or using symlinks as needed, ensuring no logs are written to user or system-wide locations.

- **Log Format and Rotation:**
  - Logs can be output in structured JSON format for integration with AICO's logging and monitoring systems.
  - Log rotation and archival are managed by AICO's existing log management tools.

- **No Data Leakage:**
  - All log data is contained within the deployment path, supporting audit, compliance, and easy cleanup.

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

## Integration Pattern
- The backend interacts with `modelservice` via REST.
- Only `modelservice` talks directly to foundational model runners (e.g., Ollama, embedding servers, vision model servers).
- All model-specific logic, parameters, and error handling are encapsulated in `modelservice`.
- Logging, security, and validation are handled consistently with the API Gateway, including ZMQ-based request logging.

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
