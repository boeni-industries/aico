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

### Architectural Approach

#### Core Design Principles

- **Agency Over Pure Reactivity** - AICO initiates and acts, not just responds
- **Local-First by Default** - All personal data and core inference runs locally
- **Modular Architecture** - Decoupled components with clear interfaces
- **Message-Driven Integration** - Event-based communication via central message bus
- **Multi-Modal Embodiment** - Visual, auditory, and textual presence
- **Emotional Intelligence** - Sophisticated emotion recognition and simulation
- **Privacy by Design** - User control of all data and processing
- **Extensible Platform** - Plugin system for community extensions
- **Continuous Evolution** - Self-updating with personality development

#### Key Architectural Decisions

- **Hybrid Flutter + WebView UI** - Native app performance with web-based avatar
- **AppraisalCloudPCT for Emotion** - Component Process Model for sophisticated emotions
- **TraitEmergence for Personality** - Multi-dimensional trait-based modeling
- **Multi-Faceted Agency** - Goal generation, curiosity, planning, meta-cognition
- **Topic-Based Pub/Sub** - Standardized message formats with versioned schemas
- **JSON Message Format** - Human-readable, widely supported serialization
- **Plugin Manager as Gateway** - Mediated access for third-party extensions
- **Homomorphic Encryption** - Privacy-preserving cloud computations when needed
- **Sandboxed Plugin Execution** - Isolated environments with permission controls
- **Atomic Updates** - Reliable system updates with rollback capabilities

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

For a comprehensive overview of all technology decisions, please refer to the [Technology Stack](./tech_stack.md) document.

Key technology categories include:
- **Interface Layer**: UI frameworks and avatar technologies
- **AI/ML Layer**: Language models, agent frameworks, and emotion systems
- **Data & Storage Layer**: Databases, vector stores, and embedding models
- **Communication Layer**: Message bus, API frameworks, and protocols
- **Security & Privacy Layer**: Encryption and privacy-preserving technologies
- **Deployment & Distribution Layer**: Containerization and update systems
- **Development & Testing Layer**: Languages, frameworks, and CI/CD tools
  - Conversation continuity preservation
- **CI/CD**: Rapid development, easy upgrades, continuous security review



## Module Integration Architecture

AICO's modules communicate through a message bus system using standardized message formats. This integration architecture ensures coherent personality expression, emotional authenticity, and proactive agency across all system components.

### Core Integration Patterns

#### Message-Driven Communication
- **Topic-Based Pub/Sub**: All modules use a publish/subscribe pattern via ZeroMQ/MQTT
- **Standardized Envelopes**: Common message envelope structure with consistent metadata
- **Versioned Schemas**: Message formats evolve with proper versioning
- **JSON Format**: All messages use JSON for maximum interoperability

#### Key Integration Flows

##### Personality-Emotion-LLM Integration
1. **Personality → LLM**: Personality module publishes communication parameters to influence LLM responses
2. **Emotion → LLM**: Emotion module publishes emotional state to condition LLM output
3. **LLM → Personality/Emotion**: Conversation events feed back for personality/emotion adaptation

##### Proactive Agency Coordination
1. **Personality → Agency**: Decision parameters guide autonomous behavior
2. **Agency → All Modules**: Initiative signals coordinate proactive engagement
3. **All Modules → Agency**: Feedback on initiative effectiveness

##### Crisis Handling
1. **Any Module → All Modules**: Crisis detection alerts for coordinated response
2. **Personality/Emotion → LLM**: Enhanced guidance during crisis situations
3. **Agency → External Resources**: Escalation paths when needed

##### Cross-Modal Expression
1. **Emotion/Personality → All Output Modules**: Synchronized expression parameters
2. **Expression Coordination → Avatar/Voice/Text**: Timing and transition guidance

#### Integration Message Types

Detailed message formats for module integration are documented in:
- [`personality_sim_msg.md`](./personality_sim_msg.md): Personality simulation messages
- [`emotion_sim_msg.md`](./emotion_sim_msg.md): Emotion simulation messages
- [`integration_msg.md`](./integration_msg.md): Cross-module integration messages including:
  - Crisis detection and handling
  - Proactive agency coordination
  - Cross-modal expression synchronization
  - Shared learning coordination
  - Enhanced ethical decision framework

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
