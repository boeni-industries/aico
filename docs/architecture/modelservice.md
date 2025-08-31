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
- **(Optional) Model Management:** List/load/unload models (future-proof, but minimal for MVP).
- **Extensible Model Types:** While LLMs are the first and core supported type, the architecture is designed to support other foundational model types (e.g., embedding models, vision models) via the same gateway and API pattern.

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
