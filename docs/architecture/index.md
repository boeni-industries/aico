# Architecture

## Project Summary

AICO is an open-source experiment to build an **emotionally present, embodied, and proactive AI companion**—meant to act as more of a confidante and sidekick than a traditional assistant. Unlike typical productivity-oriented virtual assistants, AICO is designed to sense and adapt to the user's moods, initiate engagement, and form an evolving, personality-rich relationship.

**Core Principles:**
- **Autonomous agency** - AICO has its own goals, interests, and curiosities that drive self-directed behavior and learning
- **Strong user-centric privacy** - Local-first with full user control
- **Modular, extensible architecture** - Prioritizes companionship and long-term learning
- **Real-time emotional awareness** - Multi-modal emotion recognition and adaptation

## System Features

AICO's features are organized into logical modules for development and deployment:

### 🗣️ Conversation & Interaction
- **Chat Interface**: Real-time text-based conversation
- **Voice Interaction**: Speech-to-text and text-to-speech processing
- **Context Management**: Conversation thread management and context switching
- **Autonomous Agency**: Multi-faceted self-directed behavior including:
  - **Goal Generation**: Self-formulated objectives and sub-goals
  - **Curiosity-Driven Learning**: Intrinsic motivation to explore and learn
  - **Interest Development**: Autonomous preference formation and pursuit
  - **Planning & Reasoning**: Multi-step strategic thinking and adaptation
  - **Meta-Cognition**: Self-awareness of learning progress and capabilities
- **Multi-turn Dialogue**: Complex conversation flow management
- **Interruption Handling**: Natural conversation interruption and resumption

### 🧠 Intelligence & Memory
- **Personality Simulation**: Multi-dimensional trait-based personality modeling with:
  - **Trait Vector System**: Management of personality traits (Big Five, HEXACO)
  - **Value System**: Ethical principles and preference management
  - **Expression Mapper**: Translation of traits to behavioral parameters
  - **Consistency Validator**: Ensuring behavioral coherence over time
  - **Personality Evolution**: Gradual adaptation based on interactions
- **Episodic Memory**: Personal experience and interaction history
- **Semantic Memory**: Knowledge base and learned concepts
- **Vector Storage**: Embedding-based similarity search and retrieval
- **Memory Consolidation**: Long-term memory formation and optimization
- **Context Retrieval**: Relevant memory recall based on current situation

### 😊 Emotion & Awareness
- **Facial Recognition**: Computer vision-based emotion detection
- **Voice Analysis**: Audio-based emotion and sentiment recognition
- **Text Sentiment**: Natural language emotion understanding
- **Behavioral Patterns**: User habit and preference learning
- **Mood Tracking**: Long-term emotional state monitoring
- **Empathetic Responses**: Emotion-appropriate reaction generation

### 🎭 Embodiment & Presence
- **Avatar System**: Visual representation and animation
- **Gesture Recognition**: Body language understanding
- **Spatial Awareness**: Environmental context understanding
- **Physical Presence**: Desktop, mobile, or projected embodiment
- **AR/VR Integration**: Immersive interaction capabilities
- **Multi-device Sync**: Consistent presence across devices

### 🔒 Privacy & Security
- **Local Processing**: Edge-first computation and storage
- **Data Encryption**: End-to-end encryption for all personal data
- **Consent Management**: Granular privacy control and permissions
- **Audit Logging**: Transparent data usage tracking
- **Homomorphic Encryption**: Privacy-preserving cloud computations
- **Zero-knowledge Authentication**: Secure access without data exposure

### 🔌 Extensibility & Integration
- **Plugin System**: Community-developed extensions and skills
- **API Gateway**: Unified interface for all system components
- **External Integrations**: Calendar, email, smart home connectivity
- **Custom Skills**: User-defined behaviors and responses
- **Developer Tools**: SDKs and documentation for extensions
- **Marketplace**: Plugin discovery and distribution platform
- **Automated Updates**: Self-updating system with user control
- **Self-Restart Management**: Graceful restarts with state preservation

## System Architecture

AICO follows a **modular, message-driven architecture** designed for local-first privacy, extensibility, and autonomous behavior. The system is organized into modules containing related components that communicate through a central message bus, enabling loose coupling and real-time, event-driven interactions.

### Core Design Principles

#### 🏠 Local-First by Default
All personal data and core inference runs locally (PC, workstation, or powerful edge device). Only opt-in features use cloud or edge APIs when stronger compute is required.

#### 📦 Containerized Modules
Each subsystem (personality engine, memory, emotion recognition) runs as a separate service or container (Docker, Podman). This enables:
- Platform flexibility
- Easy updates
- Strict isolation for privacy
- Independent scaling

#### 🌐 Unified API Gateway
A local gRPC or HTTP API combines all modules. All frontends (avatar, chat, desktop widget, AR/VR) communicate through this unified interface.

#### 🔌 Plugin System
Expose a plugin interface for community extensions (skills, connectors, UI themes) in scripting languages (Python, Node.js).

#### 🔒 Privacy Controller
Central user-governed dashboard for:
- Toggling features
- Controlling cloud data sharing
- Data lifecycle management
- Audit logging

## Autonomous Agency Architecture

AICO's autonomous agency is built on a multi-layered architecture that enables genuine self-directed behavior, working in concert with the Personality Simulation and Emotion Simulation modules:

### Agency Layers

#### 🎯 Goal Generation Layer
- **Autonomous Goal Formation**: Dynamic creation of objectives based on curiosity and interests
- **Hierarchical Planning**: Multi-level goal decomposition and strategic planning
- **Goal Prioritization**: Self-directed importance assessment and resource allocation

#### 🔍 Curiosity & Exploration Layer
- **Intrinsic Motivation Engine**: RND/ICM algorithms for curiosity-driven exploration
- **Novelty Detection**: Identification of new experiences and learning opportunities
- **Interest Tracking**: Development and evolution of autonomous preferences

#### 🧠 Planning & Reasoning Layer
- **Strategic Planning**: MCTS-based multi-step decision making
- **Behavior Trees**: Goal-oriented action selection and execution
- **Context Integration**: Environmental awareness and situational reasoning

#### 🪞 Meta-Cognitive Layer
- **Self-Assessment**: Understanding of own capabilities and limitations
- **Learning Progress Monitoring**: Awareness of knowledge acquisition and skill development
- **Adaptive Behavior**: Self-modification based on performance and outcomes

#### 🧠 Decision-Making Layer
- **Reasoning Engine**: Logical and causal reasoning capabilities
- **Ethical Framework**: Value-aligned decision making
- **Risk Assessment**: Evaluation of action consequences
- **Personality-Agency Fusion**: Ensures autonomous behavior aligns with personality traits through:
  - **Trait Expression Parameters**: Decision-making parameters from Personality Simulation
  - **Value System Integration**: Ethical boundaries and priorities from personality traits
  - **Coherence Validation**: Consistency checking against personality model
- **Human-Agency Balance**: Maintains appropriate boundaries and user control

### Agency Integration
- **Unified Agency Controller**: Coordinates all autonomous behaviors
- **Goal-Memory Interface**: Links autonomous objectives with episodic/semantic memory
- **Personality-Agency Fusion**: Ensures autonomous behavior aligns with personality traits
- **Human-Agency Balance**: Maintains appropriate boundaries and user control

## System Architecture

### Core Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Chat Engine** | Real-time conversation management and threading | WebSocket, FastAPI, conversation state |
| **Personality Simulation** | Trait-based personality modeling and expression | TraitEmergence architecture, multi-dimensional vector modeling |
| **Context Manager** | Conversation context and thread management | Redis, conversation graphs |
| **LLM Interface** | Language model integration and prompt management | Llama.cpp, Ollama, OpenAI adapters |
| **Personality Engine** | Dynamic personality modeling and adaptation | Local ML models, behavior trees |
| **Emotion Recognition** | Multi-modal emotion detection (visual, audio, text) | ONNX models, TensorFlow Lite |
| **Emotion Simulation** | Sophisticated emotion generation using AppraisalCloudPCT | Component Process Model, appraisal theory, optional cloud enhancement |
| **Memory System** | Episodic and semantic memory with encryption | SQLite, DuckDB, LiteFS |
| **Vector Store** | Embedding storage and similarity search | ChromaDB, Qdrant, FAISS |
| **Autonomous Agent** | Multi-faceted autonomous behavior system | Goal generation, curiosity engine, planning system |
| **Goal System** | Dynamic goal formation and hierarchical planning | MCTS, behavior trees, goal-conditioned RL |
| **Curiosity Engine** | Intrinsic motivation and exploration drive | RND, ICM, novelty detection algorithms |
| **Planning System** | Strategic reasoning and multi-step execution | Monte Carlo Tree Search, hierarchical planning |
| **Voice & Audio** | Speech-to-text and text-to-speech | Whisper.cpp, Coqui, Piper |
| **Avatar System** | Real-time 3D avatar with lip-sync and expressions | Three.js, Ready Player Me, TalkingHead.js |
| **Privacy Controller** | Advanced privacy and consent management | Homomorphic encryption, ZK proofs |
| **API Gateway** | Unified interface for all modules | FastAPI/gRPC, local web server |
| **Plugin Manager** | Dynamic plugin loading and management | Hot-reload system, sandboxing |
| **Update Manager** | Automated system updates with rollback | Version control, delta updates, integrity checks |
| **Restart Controller** | Graceful system restarts and recovery | Process management, state persistence, health monitoring |

### Technology Stack

#### Interface Layer
- **Primary UI**: Flutter cross-platform application
- **Avatar Integration**: WebView embedding Three.js + Ready Player Me + TalkingHead.js
- **Native Performance**: Flutter for app logic, WebView for 3D avatar rendering
- **JavaScript Bridge**: Real-time communication between Flutter and avatar system
- **Management Panel**: Flutter-based settings and data management UI
- **Advanced Embodiment**: Unity/Unreal for future AR/VR expansion

#### AI/ML Layer
- **Local LLMs**: Llama.cpp, Ollama, Mistral (quantized models)
- **Autonomous Agent Frameworks**: LangChain, LangGraph, CrewAI for agent orchestration
- **Goal-Conditioned RL**: HER (Hindsight Experience Replay), GCPO for goal-oriented learning
- **Curiosity Algorithms**: RND (Random Network Distillation), ICM (Intrinsic Curiosity Module)
- **Planning Systems**: MCTS (Monte Carlo Tree Search), hierarchical planning algorithms
- **Behavior Trees**: Goal-oriented behavior modeling and execution
- **Emotion Models**: ONNX Runtime, OpenVINO for edge inference
- **Cloud Fallback**: OpenAI, Gemini adapters (full opt-in)
- **Voice Processing**: Whisper.cpp (STT), Coqui/Piper (TTS)

#### Data & Storage
- **Local Database**: SQLite, DuckDB for fast, private storage
- **Vector Database**: ChromaDB, Qdrant for embedding storage and similarity search
- **Encryption**: Encryption-at-rest for all personal data
- **Memory Store**: Episodic and semantic memory with lifecycle management
- **Embedding Models**: Sentence transformers for vector generation

#### Communication & Orchestration
- **Message Bus**: ZeroMQ or MQTT for inter-module communication
- **API Gateway**: FastAPI/gRPC for unified module access
- **Plugin System**: Hot-reloadable modules with well-documented APIs

#### Deployment & Distribution
- **Containerization**: Docker/Podman with optimized multi-stage builds
- **Size Optimization**: Alpine base images, shared layers, minimal footprint
- **Packaging**: One-click installers for Win/Mac/Linux
- **Automated Updates**: Configurable self-updating system with:
  - Delta updates for minimal bandwidth usage
  - Cryptographic signature verification
  - Atomic updates with rollback capabilities
  - User-configurable update schedules and approval levels
- **Self-Restart System**: Graceful restart management with:
  - State persistence across restarts
  - Health monitoring and automatic recovery
  - Zero-downtime updates for non-critical components
  - Conversation continuity preservation
- **CI/CD**: Rapid development, easy upgrades, continuous security review



## Privacy & Security

### Data Governance
- **Local-first**: All personal data stays on user's device by default
- **Explicit Consent**: Clear opt-in for any cloud features
- **Audit Logging**: Detailed, user-facing logs for transparency
- **Data Lifecycle**: User controls retention, deletion, and export

### Security Measures
- **Encryption-at-rest**: All local data encrypted
- **Homomorphic Encryption**: Privacy-preserving cloud computations
- **Differential Privacy**: Analytics while preserving individual privacy
- **Zero-knowledge Proofs**: Authentication without revealing data
- **Secure Multi-party Computation**: Collaborative learning without data sharing
- **Module Isolation**: Containerized components with limited permissions
- **API Security**: Authenticated local API access
- **Regular Security Reviews**: Continuous security assessment in CI/CD

## Extensibility

### Plugin Architecture
- **Well-documented APIs**: Clear interfaces for community development
- **Hot-reloadable Modules**: Update plugins without system restart
- **Sandboxed Execution**: Safe plugin execution environment
- **Community Marketplace**: Future plugin discovery and sharing

### Integration Points
- **Calendar/Email**: User-controlled data import
- **Smart Home**: Optional IoT device integration
- **External APIs**: Modular connectors for various services
- **Custom Skills**: User-defined behaviors and responses

---

*This architecture balances AICO's goals of privacy, embodiment, and extensibility while leveraging modern best practices in modular agents, edge AI, and user-centric design.*
