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

AICO follows a **modular, message-driven architecture** designed for local-first privacy, extensibility, and autonomous behavior. The system is organized into a clear hierarchical structure that enables loose coupling and real-time, event-driven interactions through a central message bus.

### Hierarchical System Structure

```
System: AICO AI Companion
├── Domain: Core Infrastructure
│   ├── Module: Message Bus
│   │   ├── Component: ZeroMQ/MQTT Broker
│   │   ├── Component: Topic Management
│   │   ├── Component: Message Validation
│   │   └── Component: JSON Schema Validation
│   ├── Module: Plugin Manager
│   │   ├── Component: Extension Loader
│   │   ├── Component: Sandbox Environment
│   │   └── Component: Permission Broker
│   ├── Module: Configuration System
│   │   ├── Component: Settings Management
│   │   └── Component: Runtime Configuration
│   ├── Module: API Gateway
│   │   ├── Component: External Interfaces
│   │   └── Component: Protocol Adapters
│   └── Module: Update System
│       ├── Component: Version Management
│       └── Component: Atomic Updates
├── Domain: Autonomous Agency
│   ├── Module: Goal System
│   │   ├── Component: Goal Generation
│   │   ├── Component: Goal Prioritization
│   │   └── Component: Goal Tracking
│   ├── Module: Planning System
│   │   ├── Component: MCTS Planner
│   │   ├── Component: Action Selection
│   │   └── Component: Path Planning
│   ├── Module: Curiosity Engine
│   │   ├── Component: RND Algorithm
│   │   ├── Component: ICM Algorithm
│   │   └── Component: Exploration Driver
│   └── Module: Initiative Manager
│       ├── Component: Proactive Engagement
│       └── Component: Conversation Starter
├── Domain: Personality & Emotion
│   ├── Module: Personality Simulation
│   │   ├── Component: Trait Vector System
│   │   ├── Component: Value System
│   │   ├── Component: Expression Mapper
│   │   └── Component: Consistency Validator
│   ├── Module: Emotion Simulation
│   │   ├── Component: Appraisal Engine
│   │   ├── Component: Affect Derivation
│   │   └── Component: Expression Synthesis
│   └── Module: Emotion Recognition
│       ├── Component: Facial Analysis
│       ├── Component: Voice Analysis
│       └── Component: Text Analysis
├── Domain: Self-Awareness
│   ├── Module: State Monitoring
│   │   ├── Component: System Health
│   │   └── Component: Performance Metrics
│   └── Module: Meta-Cognition
│       ├── Component: Reflection Engine
│       └── Component: Self-Assessment
├── Domain: Intelligence & Memory
│   ├── Module: Chat Engine
│   │   ├── Component: LLM Interface
│   │   ├── Component: Prompt Conditioning
│   │   └── Component: Response Generation
│   ├── Module: Memory System
│   │   ├── Component: Episodic Memory
│   │   ├── Component: Semantic Memory
│   │   ├── Component: Procedural Memory
│   │   └── Component: Memory Consolidation
│   └── Module: Learning System
│       ├── Component: Continual Learning
│       └── Component: Skill Acquisition
├── Domain: User Interface
│   ├── Module: Context Manager
│   │   ├── Component: Conversation State
│   │   └── Component: User Context
│   └── Module: Presentation Layer
│       ├── Component: Flutter UI
│       ├── Component: Avatar System
│       └── Component: Voice & Audio
└── Domain: Privacy & Security
    ├── Module: Consent Manager
    │   ├── Component: Permission Control
    │   └── Component: Data Governance
    ├── Module: Encryption System
    │   ├── Component: Data Encryption
    │   └── Component: Secure Communication
    └── Module: Audit System
        ├── Component: Activity Logging
        └── Component: Compliance Monitoring
```

### Core Design Principles

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
