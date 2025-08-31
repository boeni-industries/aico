!!! info "Strategic Development Approach"
    Foundation I → MVP → Foundation II → PoCs → Feature Groups. Essential infrastructure only.

# Foundation I Roadmap

Build the **essential** system infrastructure required for MVP companion features. **Focus on minimal viable infrastructure to support AI features, not comprehensive system architecture.**

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
- [x] **Database Encryption Setup**: Implement application-level encryption using database-native features (SQLCipher for libSQL, DuckDB encryption, RocksDB EncryptedEnv). All data at rest is encrypted by default with optimal performance.
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
- [ ] **Service Management**: Windows Service / Linux daemon / macOS LaunchAgent
- [x] **Graceful Shutdown**: Clean service restart without data loss
- [x] **WebSocket Support**: Real-time bidirectional communication

### Data Layer Enhancement
- [x] **libSQL Encryption**: Enable built-in database encryption
- [x] **Basic Schema**: Minimal schema for MVP AI features (expand incrementally)

### Flutter Enhancement
- [x] **WebSocket Client**: Real-time communication with backend
- [x] **Request/Response Models**: Typed data models for API communication (MVP-needed)
- [x] **Error Handling**: Standardized error handling and user feedback (MVP-needed)

## Phase 3: MVP-Critical Infrastructure

### WebView Avatar Integration (Required for MVP Embodiment)
- [ ] **WebView Widget**: Flutter WebView setup for avatar rendering
- [ ] **JavaScript Bridge**: Bidirectional communication channels
- [ ] **Three.js Foundation**: Basic 3D scene setup with camera and lighting
- [ ] **Ready Player Me**: Avatar loading and customization pipeline
- [ ] **TalkingHead.js**: Lip-sync and facial expression integration
- [ ] **Performance Optimization**: WebView memory management

### Basic Resource Management (Required for LLM Operations)
- [ ] **Resource Monitor**: CPU, memory, battery, and system load tracking
- [ ] **Job Scheduler**: Task queue with priority scheduling for LLM operations
- [ ] **Resource Policies**: Configurable limits for LLM inference
- [ ] **Background Processing**: Pause/resume capabilities for non-critical tasks
- [ ] **Battery Awareness**: Reduced processing on battery power
- [ ] **User Activity Detection**: Idle detection for opportunistic processing

### Security & Privacy (MVP Requirements)
- [x] **Authentication**: Basic user authentication system
- [x] **Authorization**: Role-based access control
- [x] **Data Encryption**: End-to-end encryption for sensitive data
- [x] **Secure Communication**: TLS for all network communication
- [ ] **Privacy Controls**: Granular consent management

## Foundation I Complete When

### Core Functionality
- [ ] Message bus handles 1000+ messages/second with < 100ms latency
- [ ] Core services restart gracefully without data loss
- [ ] Development environment setup < 5 minutes
- [ ] All components work offline by default
- [ ] LLM operations can run with resource monitoring

### System Integration
- [x] Flutter app communicates with backend via REST/WebSocket
- [ ] Avatar system renders in WebView with real-time updates
- [x] Message bus routes messages between all core modules
- [ ] Resource monitor enforces CPU/memory/battery policies for LLM
- [ ] Encrypted local storage with backup/restore
- [x] Cross-platform deployment (Windows/macOS/Linux)

### Architecture Compliance
- [ ] **Message-Driven**: All module communication via ZeroMQ pub/sub
- [ ] **Modular Design**: Independent modules with clear boundaries
- [ ] **Loose Coupling**: Modules only depend on message contracts
- [ ] **Local-First**: All core functionality works offline
- [ ] **Privacy-First**: Encryption and consent management operational
- [ ] **Agency-Ready**: Infrastructure supports autonomous behavior

**Next**: See [MVP Roadmap](mvp.md) for companion AI features, then [Foundation II](foundation_II.md) for advanced infrastructure.
