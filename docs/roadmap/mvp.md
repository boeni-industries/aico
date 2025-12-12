# MVP Roadmap

**Goal**: Basic companion that talks, remembers, and initiates.

**Status**: 🚧 **IN PROGRESS** - Core conversation and memory features complete, voice and avatar integration pending.

## Frontend MVP

### Conversation Interface ✅ *Complete*
- [x] **Text Conversation UI**: Flutter conversation interface with glassmorphic design
- [x] **Real-time Updates**: WebSocket streaming for live token-by-token responses
- [x] **Typing Indicators**: Streaming response display with real-time updates
- [x] **Message History**: Scrollable conversation history with encrypted local cache (Drift)
- [x] **User Input**: Text input with send button and enter key support
- [x] **Status Display**: Connection status with health monitoring and retry logic
- [x] **Message Actions**: Hover toolbar (Copy, Remember, Regenerate, Feedback)

### Voice Interaction 🚧 *Planned*
- [ ] **Speech-to-Text**: Local Whisper.cpp integration for voice input
- [ ] **Text-to-Speech**: Local Coqui/Piper for voice output
- [ ] **Voice Controls**: Push-to-talk and voice activation
- [ ] **Audio Processing**: Noise reduction and audio quality optimization
- [ ] **Voice Settings**: Voice selection, speed, and volume controls
- [ ] **Multimodal Input**: Seamless switching between text and voice

### Basic Avatar ✅ *Complete*
- [x] **Architecture Defined**: InAppWebView + Three.js + Ready Player Me pattern
- [x] **InAppLocalhostServer**: Built-in HTTP server for ES6 modules
- [x] **Animation System**: GLB animation files with AnimationMixer and variation system
- [x] **Active Integration**: JavaScript bridge connects avatar to Flutter
- [x] **Idle Animation**: Base idle.glb with 7 natural variations (3-10s intervals)
- [x] **Natural Blinking**: ARKit morph targets with realistic blink curve (180ms, asymmetric)
- [x] **Emotion Expressions**: 12 canonical emotions via ARKit blend shapes with smooth transitions
- [x] **Emotion Integration**: Auto-syncs with EmotionProvider (2s polling)
- [x] **Eye Gaze**: Natural downward gaze for warm eye contact
- [x] **Speaking Animation**: Switch to talking.glb during AICO responses, driven by TTS speaking state
- [x] **Lip-sync**: Real-time Web Audio API frequency-based lip-sync with ARKit visemes (Phase 1); Rhubarb-based phoneme timing planned for Phase 2
- [ ] **Avatar Controls**: Mute/unmute, avatar on/off toggle (planned)

### User Experience 
- [x] **Offline Mode**: Cache-first loading with graceful degradation
- [x] **Responsive Design**: Works on macOS, iOS, Android, Linux, Windows
- [x] **Connection Management**: Automatic reconnection with exponential backoff
- [x] **Error Handling**: User-friendly error messages and retry logic
- [ ] **Onboarding**: Simple welcome flow and personality setup
- [ ] **Settings**: Basic preferences (name, avatar, personality sliders)

## Backend MVP

### LLM Integration 
- [x] **Model Configuration**: Qwen3 Abliterated 8B with Ollama auto-management
- [x] **Character Personalities**: Modelfile system with Eve as default character
- [x] **Prompt Engineering**: System prompts with memory context integration
- [x] **Response Generation**: Streaming completions via WebSocket
- [x] **Fallback Handling**: Graceful degradation with health monitoring
- [x] **Auto-Management**: Automatic Ollama installation and model pulling

### Memory System 
- [x] **Three-Tier Architecture**: Working (LMDB) + Semantic (ChromaDB) + Knowledge Graph (DuckDB)
- [x] **Conversation Memory**: 24-hour working memory with sub-millisecond access
- [x] **User Facts**: Knowledge graph with 204 nodes, 27 edges, 552 properties
- [x] **Context Retrieval**: Hybrid Search V3 (semantic + BM25 + IDF + RRF)
- [x] **Memory Consolidation**: AMS with background consolidation tasks
- [x] **Semantic Search**: ChromaDB with 768-dim multilingual embeddings
- [x] **Memory Album**: User-curated conversation and message-level memories
- [x] **Entity Extraction**: GLiNER zero-shot NER + LLM relationship extraction
- [x] **Entity Resolution**: 3-step deduplication with semantic blocking

### Personality Engine 
- [x] **Character System**: Ollama Modelfiles for custom personalities
- [x] **Eve Character**: Warm, curious, contemplative default personality
- [x] **Expression Mapping**: System prompts define communication style
- [x] **Consistency**: Model parameters ensure character consistency
- [x] **Thinking Process**: Ollama 0.12+ native thinking API
- [ ] **Trait System**: Formal Big Five/HEXACO implementation (future)
- [ ] **Personality Configuration**: User-adjustable personality sliders (future)

### Emotion Recognition 
- [x] **Text Sentiment**: BERT Multilingual sentiment classification
- [x] **Emotion Analysis**: RoBERTa 6-emotion classification
- [x] **Intent Classification**: XLM-RoBERTa multilingual intent understanding
- [x] **Memory Album Integration**: Automatic emotional tone detection
- [ ] **Voice Analysis**: Basic emotion detection from voice (planned)
- [ ] **Behavioral Patterns**: User mood learning over time (planned)
- [ ] **Emotion History**: Track emotional patterns (planned)

### Emotion Simulation 
- [x] **Canonical Emotion Labels**: 12 emotions (neutral, calm, curious, playful, warm_concern, protective, focused, encouraging, reassuring, apologetic, tired, reflective)
- [x] **Avatar Expression**: Emotion-driven facial expressions via ARKit blend shapes
- [x] **Smooth Transitions**: 5% interpolation per frame for natural emotion changes
- [x] **Emotional Memory**: Memory Album tracks emotional tone
- [ ] **Basic Appraisal**: Simplified Component Process Model for emotion generation (planned)
- [ ] **Voice Coordination**: Sync emotions across avatar and voice (planned)
- [ ] **Empathetic Responses**: Generate emotionally appropriate reactions (planned)

### Basic Agency 
- [x] **Task Scheduler**: Cron-based scheduler with resource awareness
- [x] **Background Tasks**: Log cleanup, key rotation, health checks, database vacuum
- [x] **AMS Tasks**: Memory consolidation, feedback classification, Thompson sampling
- [x] **KG Tasks**: Graph consolidation, entity resolution, relationship inference
- [x] **Conversation Continuity**: Memory system enables referencing past conversations
- [ ] **Initiative System**: Proactive conversation starters (planned)
- [ ] **Goal Generation**: Self-formulated objectives (planned)
- [ ] **Suggestion Engine**: Context-based suggestions (planned)
- [ ] **Proactive Timing**: Intelligent initiative timing (planned)

### Core Services 
- [x] **Conversation API**: REST + WebSocket endpoints with streaming
- [x] **Memory API**: Store and retrieve memories (Memory Album)
- [x] **Knowledge Graph API**: GQL/Cypher queries via CLI
- [x] **Modelservice API**: ZeroMQ-based LLM, embeddings, NER, sentiment
- [x] **Health API**: System health and status monitoring

## AI Feature Integration

### Module Coordination 
- [x] **LLM-Memory Integration**: Context assembly from three-tier memory system
- [x] **Personality-LLM Integration**: Modelfile system defines character behavior
- [x] **Emotion Recognition Integration**: Sentiment analysis for Memory Album
- [x] **Agency-Memory Integration**: Task scheduler uses memory for consolidation
- [x] **Knowledge Graph Integration**: Entity extraction and relationship modeling
- [x] **Emotion-Avatar Integration**: Real-time facial expressions sync with emotion state
- [x] **Voice-Avatar Sync**: Basic voice-activated talking animation and Web Audio API lip-sync implemented; higher-accuracy phoneme timing via Rhubarb planned

## Validation Criteria

### Core Functionality
- [x] Remembers user preferences across sessions (three-tier memory)
- [x] Shows consistent personality responses (Eve character via Modelfile)
- [x] Recognizes user emotions (sentiment analysis)
- [x] Works completely offline (local-first architecture)
- [x] Responds within 3-5 seconds (streaming with <500ms first token)
- [ ] Initiates conversations without prompting (planned)
- [ ] Expresses emotions through avatar and voice (planned)

### User Experience
- [x] Smooth conversation interface with real-time streaming
- [x] Personality feels consistent and authentic (Eve character)
- [x] Encrypted local storage with fast load times (<200ms)
- [x] Offline-first with graceful degradation
- [x] Cross-platform support (macOS, iOS, Android, Linux, Windows)
- [ ] Voice interaction works seamlessly with text (planned)
- [ ] Avatar animations sync with conversation (planned)
- [ ] Proactive behavior feels natural (planned)
- [ ] Easy setup and configuration (partially complete)

### Emotional Intelligence
- [x] Detects user mood from text (BERT, RoBERTa)
- [x] Remembers emotional context (Memory Album with tone)
- [x] Shows emotional expressions via avatar (12 canonical emotions with ARKit blend shapes)
- [x] Natural micro-expressions (realistic blinking, eye gaze)
- [ ] Detects mood from voice (planned)
- [ ] Responds empathetically to emotions (planned)
- [ ] Adapts communication style based on mood (planned)

## Technical Requirements

*Note: Core infrastructure provided by Foundation I (complete)*

**Implemented:**
- **LLM**: Qwen3 Abliterated 8B via Ollama with Modelfile system
- **Memory**: Three-tier (LMDB + ChromaDB + DuckDB) with Hybrid Search V3
- **Knowledge Graph**: NetworkX + DuckDB with GQL/Cypher queries
- **Entity Extraction**: GLiNER Medium v2.1 + sentence-transformers
- **Sentiment**: BERT Multilingual + RoBERTa emotion + XLM-RoBERTa intent
- **Personality**: Modelfile-based character system (Eve)

**Implemented:**
- **Avatar**: InAppWebView + Three.js + Ready Player Me with emotion expressions
- **Facial Expressions**: 12 canonical emotions via ARKit blend shapes (52 morph targets)
- **Natural Behaviors**: Realistic blinking (180ms asymmetric), eye gaze, idle variations
- **Lip-sync (Phase 1)**: Web Audio API frequency-based viseme detection and ARKit blend shape mapping for real-time avatar lip-sync; Rhubarb Lip Sync integration planned for Phase 2

**Planned:**
- **Voice**: Whisper.cpp (STT) + Coqui/Piper (TTS) integration
- **Emotion Simulation**: AppraisalCloudPCT implementation
- **Formal Personality**: Big Five/HEXACO trait system

## Success Definition

User can have a 10-minute conversation where AICO:
1. **Memory**: Remembers something from earlier (three-tier memory system)
2. **Personality**: Shows consistent personality traits (Eve character via Modelfile)
3. **Emotion Recognition**: Detects user mood from text (BERT, RoBERTa)
4. **Contextual Intelligence**: Uses memory context for relevant responses
5. **Knowledge Graph**: Builds relationship understanding from conversations
6. **Emotion Expression**: Displays 12 canonical emotions via avatar facial expressions
7. **Agency**: Asks follow-up questions unprompted (planned)
8. **Voice Interaction**: Handles text and voice input/output (planned)

**Current Status**: Items 1-6 complete and operational. Items 7-8 pending voice integration and proactive behavior.

**Status**: 🚧 **MVP IN PROGRESS** - Core conversation and memory complete, voice and avatar pending.

**Next**: Complete voice and avatar integration, then proceed to [Foundation II](foundation-II.md) for advanced infrastructure.
