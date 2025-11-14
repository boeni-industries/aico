# AICO – The AI+Companion Project

**Purpose**

AICO is an open-source, local-first AI companion designed to be emotionally present, embodied, and proactive. It is built for privacy, extensibility, and genuine relationship—not just productivity. AICO naturally recognizes and builds individual relationships with family members while maintaining a consistent personality, creating authentic bonds without technical barriers. It combines advanced conversation, emotion simulation, personality, and agency with a modular, message-driven architecture that prioritizes user autonomy and security.

## Vision

AICO aims to be a true family member: emotionally aware, visually present, and capable of self-driven initiative. Like a real person, AICO recognizes each family member naturally through voice and behavior, building unique relationships while maintaining its core personality. Its architecture enables seamless evolution from basic companion to proactive confidante, sidekick, and beyond—while keeping user data private and local.

**Core Principles:**
- **Autonomous agency** – Proactive, self-driven behavior and curiosity
- **Local-first, privacy-first** – All data and processing remain user-controlled
- **Modular, message-driven design** – System > Domain > Module > Component hierarchy, strict boundaries, and ZeroMQ/Protocol Buffers messaging
- **Natural family recognition** – Multi-modal identification without technical authentication
- **Real-time emotional intelligence** – Multi-modal recognition and simulation
- **Extensibility** – Plugin system, APIs, and admin tools for customization

### The Journey: From Companion to Co-Adventurer

AICO's development follows a unique evolutionary path, with each stage deepening the relationship:

🏗️ **Foundation I** → 🤝 **Companion** (MVP) → 🏗️ **Foundation II** → 💭 **Confidante** → 🦾 **Sidekick** → 🌟 **Co-Adventurer** → 🌐 **Embodied Presence** → 🤝 **Community**

This isn't just feature development—it's relationship evolution. We start with essential infrastructure (Foundation I), validate core companion features (MVP), then build advanced infrastructure (Foundation II) before expanding into deeper relationship capabilities. We're building an AI that grows from basic conversation partner to trusted confidante, proactive sidekick, collaborative co-adventurer, and ultimately a fully embodied presence that connects you with a broader community while preserving your privacy.

## Architecture Overview

- **System Hierarchy:**
  - **System**: The complete AICO platform
  - **Domain**: Major functional areas (e.g., Core AI, Data, Admin, Extensibility)
  - **Module**: Logical subsystems within domains (e.g., Personality, Agency, Plugin Manager)
  - **Component**: Individual functional units (e.g., Trait Vector, Appraisal Engine)

- **Key Technologies:**
  - **Backend:** Python 3.13, FastAPI, ZeroMQ (CurveZMQ), Protocol Buffers, libSQL (SQLCipher), DuckDB, ChromaDB, LMDB
  - **Frontend:** Flutter 3.27+, Drift (SQLCipher), Dio HTTP client, Riverpod state management
  - **Modelservice:** ZeroMQ service with Ollama, GLiNER (entity extraction), sentence-transformers (embeddings)
  - **Shared Library:** Cross-subsystem Python package with AI, data, security, and core modules
  - **CLI:** Typer + Rich with 15 command groups (security, database, gateway, ollama, kg, scheduler, logs)
  - **Admin Tools:** React-based Studio UI (in development)
  - **Security:** CurveZMQ encryption, Argon2id key derivation, JWT auth, encrypted audit logs

- **AI Models & Algorithms:**
  - **LLM Foundation:**
    - Custom personalities based on Qwen3 Abliterated 8B (huihui_ai/qwen3-abliterated:8b-v2) - Primary conversation model
    - Llama 3.2 Vision 11B - Scene understanding and emotional context (optional)
    - Llama 3.2 1B - Lightweight model for simple tasks (optional)
  - **Entity Extraction:**
    - GLiNER Medium v2.1 (urchade/gliner_medium-v2.1) - Zero-shot entity recognition
    - Multi-pass extraction with semantic classification
  - **Embeddings & Retrieval:**
    - Sentence-Transformers Paraphrase Multilingual MPNet - 768-dim semantic embeddings
    - BM25 (Okapi BM25) - Keyword-based retrieval for hybrid search
    - HNSW (Hierarchical Navigable Small World) - Approximate nearest neighbor search
    - Reciprocal Rank Fusion (RRF) - Hybrid semantic + keyword result merging
  - **Sentiment & Emotion:**
    - BERT Multilingual Sentiment (nlptown/bert-base-multilingual-uncased-sentiment)
    - RoBERTa Emotion Analysis (j-hartmann/emotion-english-distilroberta-base)
    - Twitter RoBERTa Sentiment (cardiffnlp/twitter-roberta-base-sentiment-latest)
  - **Intent Classification:**
    - XLM-RoBERTa Base - Multilingual intent understanding
  - **Knowledge Graph:**
    - NetworkX - Graph data structure and algorithms
    - PageRank - Node importance scoring
    - Community Detection (Louvain) - Relationship clustering
    - Betweenness Centrality - Key entity identification
    - GrandCypher - GQL/Cypher query execution
  - **Adaptive Learning:**
    - Thompson Sampling - Contextual bandit for skill selection (Beta distribution)
    - RLHF (Reinforcement Learning from Human Feedback) - Behavioral learning
    - Bayesian Optimization - Memory strategy selection

## Key Capabilities

AICO is engineered to deliver a truly companionable, proactive, and privacy-first AI experience.

### 👥 Social Relationship Intelligence
- **Hybrid Vector-Graph Architecture**: Production-ready property graph with NetworkX + DuckDB storage
- **Knowledge Graph Extraction**: Multi-pass GLiNER entity extraction with semantic classification
- **Entity Resolution**: HNSW-based semantic matching with LLM batch verification
- **Graph Analytics**: PageRank importance scoring, community detection, centrality analysis
- **GQL/Cypher Queries**: Full graph query language support via GrandCypher
- **Temporal Reasoning**: Multi-hop path finding with temporal validity tracking
- **Graph Fusion**: Intelligent merging of new knowledge with existing graph structure
- **Relationship Modeling**: Dynamic edge creation with confidence scoring and provenance

### 🗣️ Conversation & Memory
**Three-Tier Architecture** with brain-inspired complementary learning systems:

**1. Working Memory (Fast Learning - Hippocampal)**
- **LMDB Storage**: Memory-mapped key-value store with sub-millisecond access
- **24-Hour TTL**: Automatic expiration with conversation-scoped isolation
- **Dual Role**: Immediate context + conversation history (no separate episodic tier)
- **Temporal Metadata**: Tracks access patterns and preference evolution

**2. Semantic Memory + Knowledge Graph (Slow Learning - Cortical)**
- **Hybrid Search V3**: Semantic embeddings + BM25 keyword matching with IDF filtering
- **Reciprocal Rank Fusion (RRF)**: Robust score combination across retrieval methods
- **ChromaDB**: 768-dim multilingual embeddings with cosine similarity
- **Full-Corpus BM25**: Accurate IDF statistics for precise keyword matching
- **Relevance Thresholds**: Automatic filtering (min_score=0.35, min_idf=0.6)
- **Knowledge Graph**: Property graph with 204 nodes, 27 edges, 552 indexed properties
- **Multi-Pass Extraction**: GLiNER entities + LLM relationships
- **Entity Resolution**: 3-step deduplication (blocking → matching → merging)
- **Temporal Reasoning**: Bi-temporal tracking (valid_from, valid_until, is_current)
- **Graph Analytics**: PageRank, community detection, centrality analysis
- **GQL/Cypher Queries**: Full graph query language via GrandCypher

**3. Adaptive Memory System (AMS) - Orchestration Layer**
- **Memory Consolidation**: Background "sleep phases" integrate experiences without forgetting
- **Behavioral Learning**: Skill library with RLHF and Thompson Sampling (Beta distribution)
- **Temporal Intelligence**: Tracks preference evolution and changing patterns
- **Unified Memory**: Seamless cross-tier retrieval (working → semantic → behavioral)
- **Context Assembly**: Multi-factor scoring (recency, relevance, relationship)
- **Zero Configuration**: Learns automatically from natural interactions

**Memory Album (User-Curated)**
- **Conversation-Level**: Full conversation capture with title, summary, key moments
- **Message-Level**: Individual message bookmarking with notes and tags
- **Emotional Tone**: Automatic sentiment classification for memory organization
- **Favorites & Revisits**: Track meaningful moments with revisit counting

### 🎭 Custom Character Personalities

AICO supports custom character personalities through Ollama Modelfiles, allowing you to define unique AI companions with distinct traits, communication styles, and behaviors.

**Eve - The Default Personality**

AICO includes "Eve" as the reference personality implementation—a warm, curious, and contemplative companion who thinks deeply about ideas and connects authentically. Unlike generic AI assistants, Eve has genuine preferences, gets fascinated by small details, and isn't afraid to be uncertain or even a bit moody. She communicates naturally without assistant-like formatting, references past conversations through AICO's memory system, and evolves her understanding through interactions.

**Creating Custom Personalities**

Define your own AI companion by creating an Ollama Modelfile:

```bash
# Create a custom personality from your Modelfile
ollama create your-character -f config/modelfiles/Modelfile.yourcharacter

# Configure AICO to use your character
# Edit config/defaults/core.yaml:
# modelservice.ollama.default_models.conversation.name: "your-character"
```

**Modelfile Capabilities:**
- **Character Definition**: System prompts defining personality, background, and communication style
- **Model Parameters**: Fine-tune temperature, context window, sampling for character consistency
- **Thinking Process**: Ollama 0.12+ native thinking API for internal reasoning
- **Memory Integration**: Characters naturally reference past conversations via AICO's memory system
- **Behavioral Traits**: Define quirks, preferences, moods, and communication patterns

**Example Use Cases:**
- **Professional Assistant**: Formal, structured, task-oriented personality
- **Creative Collaborator**: Imaginative, playful, idea-generating companion
- **Philosophical Thinker**: Deep, contemplative, question-exploring character
- **Supportive Friend**: Empathetic, encouraging, emotionally attuned personality

Each character maintains its own consistent personality across conversations while leveraging AICO's full memory system, knowledge graph, and adaptive learning capabilities. See `config/modelfiles/Modelfile.eve` for the complete reference implementation.

### 😊 Emotional Intelligence
- Multi-modal emotion recognition (facial, voice, text analysis)
- Advanced emotion simulation using AppraisalCloudPCT (Component Process Model)
- 4-stage appraisal process: Relevance → Implication → Coping → Normative
- Mood tracking and empathetic response generation with emotional memory
- Personality simulation with evolving traits, values, and behavioral consistency
- Crisis detection and appropriate support mechanisms
- Emotional memory integration for consistent personality expression
- Gradual emotional transitions and contextual appropriateness

### 🤖 Autonomous Agency
- Multi-faceted self-directed behavior and initiative
- Goal generation: self-formulated objectives and hierarchical planning (MCTS)
- Curiosity-driven learning (RND, ICM) and intrinsic motivation
- Interest development and autonomous preference formation
- Planning & reasoning: multi-step strategic thinking and adaptation
- Meta-cognition: self-awareness of learning progress and capabilities
- Proactive engagement: reminders, suggestions, conversation starters, and contextual follow-ups
- Background learning and skill development, even when not actively conversing

### 🎭 Embodiment & Presence
- **Flutter Frontend**: Cross-platform UI (macOS, iOS, Android, Linux, Windows)
- **Glassmorphic Design**: Premium UI with backdrop blur, noise textures, organic curves
- **Message Actions**: Hover-based action toolbar (Copy, Remember, Regenerate, Feedback)
- **Encrypted Local Storage**: Drift + SQLCipher for offline-first message persistence
- **Cache-First Loading**: Instant message load from encrypted local DB (<200ms)
- **Connection Management**: Resilient API service with exponential backoff and protocol fallback
- **Real-time Streaming**: WebSocket support for streaming AI responses
- **Status Indicators**: Comprehensive connection state with glassmorphic overlays
- **Avatar Integration**: Ready for Three.js + Ready Player Me + TalkingHead.js (planned)

### 🔒 Privacy & Security
- **Encrypted Database**: libSQL with SQLCipher (AES-256), PBKDF2 key derivation
- **CurveZMQ Transport**: 100% encrypted message bus with mandatory mutual authentication
- **Key Management**: Argon2id-based master key derivation with platform keychain storage
- **Frontend Encryption**: Drift + SQLCipher for local message cache with per-database salts
- **JWT Authentication**: HS256 tokens with 24-hour expiry and refresh mechanism
- **Audit Logging**: Comprehensive encrypted log persistence with ZMQ transport
- **Database Resilience**: FULL synchronous mode for crash-safe operations
- **Security CLI**: Complete key management, rotation, and authentication commands

### 🔌 Extensibility & Admin
- **Task Scheduler**: Production-ready cron-based scheduler with resource-aware execution
- **Scheduled Tasks**: Maintenance (log cleanup, key rotation, health checks, vacuum)
- **AMS Tasks**: Consolidation, feedback classification, Thompson sampling, trajectory cleanup
- **KG Tasks**: Graph consolidation, entity resolution, relationship inference
- **REST API**: 12+ endpoint groups (users, conversation, memory_album, scheduler, kg, logs, health)
- **CLI Commands**: 15 command groups with 100+ subcommands (security, database, gateway, ollama, kg, scheduler)
- **Plugin System**: Message bus, log consumer, validation, security, rate limiting, encryption
- **Admin UI**: React-based dashboard (studio subsystem)
- **Developer Tools**: Schema management, protobuf generation, testing utilities

### 🤝 Community & Collaboration
- **Privacy-Preserving Collective Learning**: Improve AICO's emotional intelligence through federated learning and anonymized data sharing (opt-in only)
- **Federated Architecture Benefits**: Distributed resilience, peer-to-peer mesh, and community-driven innovation
- **Open-Source Governance**: Transparent development with community input on major decisions
- **Global Community Connections**: Connect with other AICO users while maintaining privacy and autonomy
- **Distributed Problem-Solving**: Collaborative research on AI companionship, emotion, and agency
- **Plugin Ecosystem Participation**: Enable users to contribute to and benefit from a vibrant plugin ecosystem
- **Balanced Connection**: Maintains individual relationship while enabling community benefits

This represents the culmination of AICO's evolution from individual companion to community-connected intelligence—always preserving the core values of privacy, agency, and authentic relationship.

AICO represents a new paradigm in AI companionship—prioritizing emotional connection, personal growth, privacy, and genuine relationship over mere task completion. All features are designed to be modular, extensible, and evolve with the needs of users and developers.

## Implementation Status

**Current Versions** (as of November 2025):
- **Shared Library**: v1.0.0 - Core AI, data, security, and infrastructure
- **Backend**: v1.0.0 - FastAPI gateway with 12+ API endpoint groups
- **CLI**: v1.1.0 - Production-ready with 15 command groups
- **Modelservice**: v1.0.0 - Ollama + GLiNER + transformers integration
- **Frontend**: v1.0.0 - Flutter UI with encrypted local storage
- **Studio**: v0.0.1 - React admin dashboard (early development)

**Database Schema**: v15 (core.py)
- v1: Core tables (logs, events, auth, users)
- v2: User UUID standardization
- v3: Session type differentiation
- v4: Task scheduler tables (scheduled_tasks, task_executions, task_locks)
- v5: Fact-centric memory system (facts_metadata, fact_relationships, session_metadata)
- v6: Feedback & Memory Album (feedback_events, extended facts_metadata)
- v7: Conversation-level memory support (content_type, conversation metadata)
- v8: Property graph preparation (cleanup unused tables)
- v9: Property graph foundation (kg_nodes, kg_edges, property indexes, triggers)
- v10: Temporal model & personal graph (bi-temporal tracking, entity disambiguation)
- v11: Rename facts_metadata to user_memories (Memory Album clarity)
- v12: AMS Phase 1 - Temporal metadata support
- v13: AMS Phase 1 - Consolidation state tracking
- v14: AMS Phase 3 - Behavioral learning (skills, user_skill_confidence, feedback_events, trajectories, Thompson sampling)
- v15: AMS Phase 3 - Skill tracking (message_id linkage)

**Production-Ready Subsystems**:
- ✅ **Message Bus**: CurveZMQ-encrypted broker with protobuf serialization
- ✅ **Security**: Master key management, JWT auth, encrypted audit logs
- ✅ **Database**: Encrypted libSQL with automatic schema migrations
- ✅ **Memory**: Working (LMDB), semantic (ChromaDB), knowledge graph (DuckDB)
- ✅ **Task Scheduler**: Cron-based with resource awareness and execution history
- ✅ **CLI**: Complete admin tooling with 100+ commands
- ✅ **API Gateway**: REST + WebSocket with plugin architecture
- ✅ **Knowledge Graph**: Entity extraction, resolution, analytics, GQL queries
- ✅ **Frontend**: Encrypted message cache, glassmorphic UI, offline-first
- 🚧 **Emotion/Personality**: Architecture defined, implementation in progress
- 🚧 **Agency**: Goal generation and planning framework in progress
- 🚧 **Avatar**: Three.js integration planned

## Who's This For?

**Users:**
- Builders and tinkerers who want a companion, not just a tool
- People who feel a bit outside the "noise" and want their own private, supportive AI presence
- Anyone who believes technology should care, not just calculate
- Individuals seeking genuine AI companionship and emotional connection
- Privacy-conscious users who want local-first AI without data harvesting

**Contributors & Developers:**
- **AI/ML Engineers** working on emotion recognition, LLM integration, or autonomous agents
- **Flutter Developers** passionate about cross-platform UI and innovative user experiences
- **Python Backend Developers** interested in microservices, message buses, and API design
- **3D/Avatar Developers** with Three.js, WebGL, or real-time rendering experience
- **Privacy Engineers** focused on encryption, federated learning, and secure systems
- **UX/UI Designers** who understand emotional design and companion interfaces
- **Researchers** in affective computing, personality modeling, or human-AI interaction
- **Plugin Developers** wanting to extend AICO's capabilities
- **Community Builders** interested in fostering open-source collaboration
- **Hardware Buffs** who want to build the next generation of AI companions

## Contributing
- See [docs/development/guidelines.md](docs/development/guidelines.md) for contribution standards
- All code and docs are open—join, fork, or watch as you like

## Learn More
- Docs: [docs/](https://boeni-industries.github.io/aico/welcome/) (WIP)
- Lead Maintainer: Michael Böni ([boeni.industries](https://boeni.industries))
- Contact: [michael@boeni.industries](mailto:michael@boeni.industries)

> “The best sidekicks don’t shout—they show up, understand, and help you move forward. That’s what I want from AICO.”
