!!! success "Foundation I Complete"
    ✅ All essential infrastructure completed. System ready for MVP companion features.

# Foundation I Roadmap

Build the **essential** system infrastructure required for MVP companion features. **Focus on minimal viable infrastructure to support AI features, not comprehensive system architecture.**

**Status**: ✅ **COMPLETE** - All phases finished, system operational in production.

## Phase 1: Minimal Running System ✅

### Basic Service Layer
- [x] **Python Service**: FastAPI-based backend service with basic project structure
- [x] **Configuration System**: Simple YAML/JSON config with environment variables
- [x] **Logging Framework**: Basic structured logging (console + file)
- [x] **Health Monitoring**: Simple health check endpoint
- [x] **API Gateway**: Basic REST endpoints for frontend communication

### Basic Flutter Foundation
- [x] **Project Structure**: Standard Flutter project with basic folder organization
- [x] **State Management**: Simple Provider setup for app-wide state
- [x] **Navigation**: Basic navigation (can upgrade to Go Router later)
- [x] **Theme System**: Basic Material 3 theme with dark/light mode
- [x] **API Client**: Simple HTTP client with error handling

### Minimal Message Bus
- [x] **ZeroMQ Setup**: Core pub/sub message bus implementation
- [x] **Basic Topics**: Essential topics (system.*, conversation.*, ui.*)
- [x] **Message Envelope**: Protocol Buffer message format
- [x] **Message Routing**: Basic topic-based routing

### Basic Data Layer
- [x] **libSQL Setup**: Modern SQLite fork for local database (encryption can come later)
- [x] **Basic Schema**: Minimal tables for system state and config
- [x] **Migration System**: Simple schema versioning

### Basic Security Layer
- [x] **Master Password Setup**: Require user to set a master password on first run. Never store the password—use it transiently for key derivation only. Derived keys stored securely for automatic service authentication.
- [x] **Unified Key Management**: Implement `AICOKeyManager` class supporting three scenarios: initial setup (interactive), user authentication (interactive), and service startup (automatic). Uses Argon2id-based key derivation from user master password with platform-native secure storage.
- [x] **Persistent Service Authentication**: Backend services can restart automatically without user password re-entry. Master key retrieved from secure storage (macOS Keychain, Windows Credential Manager, Linux Secret Service) on service startup, enabling zero-effort security for non-technical users.
- [x] **Database Encryption Setup**: Implement application-level encryption using database-native features (SQLCipher for libSQL, DuckDB encryption, LMDB EncryptedEnv). All data at rest is encrypted by default with optimal performance.
- [x] **File Encryption Wrapper**: Create `EncryptedFile` wrapper class using AES-256-GCM for files without native encryption support (configs, logs, ChromaDB files). Drop-in replacement for Python's `open()` function.
- [x] **Database Key Derivation**: Extend `AICOKeyManager` with `derive_database_key()` and `derive_file_encryption_key()` methods for purpose-specific key generation from master key.
- [x] **Access Control Skeleton**: Add a basic access control mechanism (deny by default, allow for core system processes only). All access is explicit, with a foundation for future ABAC/RBAC policies.

## Phase 2: Core Infrastructure ✅

### Enhanced Message Bus
- [x] **Basic Topic Expansion**: Add topics as AI modules are developed (start minimal)

### Task Scheduler Component
- [x] **Background Scheduler**: Implement task scheduler for zero-maintenance operations (log cleanup, key rotation, health checks)
- [x] **Cron-like Scheduling**: Support for periodic tasks with configurable intervals
- [x] **Task Registry**: Plugin system for registering scheduled tasks from different subsystems
- [x] **Failure Recovery**: Automatic retry logic and error handling for scheduled tasks
- [x] **Performance**: Optimize for 1000+ messages/second with <100ms latency

### Service Layer Enhancement
- [x] **Service Management**: Windows Service / Linux daemon / macOS LaunchAgent
- [x] **Graceful Shutdown**: Clean service restart without data loss
- [x] **WebSocket Support**: Real-time bidirectional communication

### Data Layer Enhancement
- [x] **libSQL Encryption**: Enable built-in database encryption
- [x] **Basic Schema**: Minimal schema for MVP AI features (expand incrementally)

### Flutter Enhancement
- [x] **WebSocket Client**: Real-time communication with backend
- [x] **Request/Response Models**: Typed data models for API communication (MVP-needed)
- [x] **Error Handling**: Standardized error handling and user feedback (MVP-needed)

## Phase 3: MVP-Critical Infrastructure ✅

### Basic Model Service (Required for text-based conversations) ✅
- [x] **Model Service**: ZeroMQ-based modelservice with Ollama integration
- [x] **Model Configuration**: Qwen3 Abliterated 8B with custom character personalities (Modelfiles)
- [x] **Model Execution**: Streaming completions with WebSocket support
- [x] **Transformers Integration**: GLiNER (NER), sentence-transformers (embeddings), BERT/RoBERTa (sentiment)
- [x] **Auto-Management**: Automatic Ollama binary installation and model pulling
- [x] **Resource Management**: Ollama 0.12+ parallel processing (4 concurrent, 2 max loaded)

### WebView Avatar Integration (Ready for MVP Integration)
- [x] **InAppWebView Package**: flutter_inappwebview with localhost server support
- [x] **InAppLocalhostServer**: Built-in HTTP server for ES6 module support
- [x] **JavaScript Bridge**: Bidirectional communication (evaluateJavascript + handlers)
- [x] **Three.js Foundation**: WebGL rendering with GLTFLoader ready
- [x] **Ready Player Me**: Avatar model integration pattern defined
- [x] **Animation System**: Separate GLB files with AnimationMixer
- [x] **TalkingHead.js**: Integration pattern defined (Phase 2)
- [ ] **Active Integration**: Not yet connected to live conversations (MVP task)

### Basic Resource Management (Required for LLM Operations) ✅
- [x] **Resource Monitor**: CPU, memory tracking implemented in task scheduler
- [x] **Job Scheduler**: Cron-based task scheduler with resource awareness
- [x] **Resource Policies**: Configurable limits via core.yaml (memory_threshold_percent: 85)
- [x] **Background Processing**: Task scheduler with adaptive execution
- [x] **Ollama Resource Management**: Auto-unload after 30 minutes, max 2 concurrent models
- [ ] **Battery Awareness**: Not yet implemented (future enhancement)
- [ ] **User Activity Detection**: Not yet implemented (future enhancement)

### Security & Privacy (MVP Requirements) ✅
- [x] **Authentication**: JWT-based authentication with 24-hour expiry
- [x] **Authorization**: Service-to-service authentication via CurveZMQ
- [x] **Data Encryption**: SQLCipher (AES-256-GCM) for all databases
- [x] **Secure Communication**: CurveZMQ encryption for all message bus traffic
- [x] **Key Management**: Argon2id + PBKDF2 with platform keychain integration
- [ ] **Privacy Controls**: Granular consent management (future enhancement)

## Foundation I Completion Status ✅

### Core Functionality ✅
- [x] Message bus handles high-frequency messages with CurveZMQ encryption
- [x] Core services restart gracefully without data loss
- [x] Development environment setup via UV workspace (< 5 minutes)
- [x] All components work offline by default
- [x] LLM operations run with resource monitoring and auto-management

### System Integration ✅
- [x] Flutter app communicates with backend via REST/WebSocket with streaming
- [x] Avatar system architecture ready (integration pending in MVP)
- [x] Message bus routes messages between all core modules with CurveZMQ
- [x] Resource monitor enforces CPU/memory policies for LLM (Ollama 0.12+)
- [x] Encrypted local storage (SQLCipher for all databases)
- [x] Cross-platform deployment (Windows/macOS/Linux) with production CLI v1.1.0
- [ ] Backup/restore (future enhancement)

### Architecture Compliance
- [x] **Message-Driven**: All module communication via ZeroMQ pub/sub
- [x] **Modular Design**: Independent modules with clear boundaries
- [x] **Loose Coupling**: Modules only depend on message contracts
- [x] **Local-First**: All core functionality works offline
- [x] **Privacy-First**: Encryption and consent management operational
- [x] **Agency-Ready**: Infrastructure supports autonomous behavior

**Status**: ✅ **FOUNDATION I COMPLETE**

**Next**: See [MVP Roadmap](mvp.md) for companion AI features (in progress), then [Foundation II](foundation-II.md) for advanced infrastructure.
