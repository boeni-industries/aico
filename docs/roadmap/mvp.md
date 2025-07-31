# MVP Roadmap

**Goal**: Basic companion that talks, remembers, and initiates.

*Builds on [Foundation](foundation.md) infrastructure.*

## Frontend MVP

### Chat Interface
- [ ] **Text Chat UI**: Flutter chat interface with message bubbles
- [ ] **Real-time Updates**: WebSocket connection for live conversation
- [ ] **Typing Indicators**: Show when AICO is thinking/responding
- [ ] **Message History**: Scrollable conversation history
- [ ] **User Input**: Text input with send button and enter key support
- [ ] **Status Display**: Connection status and AICO availability

### Voice Interaction
- [ ] **Speech-to-Text**: Local Whisper.cpp integration for voice input
- [ ] **Text-to-Speech**: Local Coqui/Piper for voice output
- [ ] **Voice Controls**: Push-to-talk and voice activation
- [ ] **Audio Processing**: Noise reduction and audio quality optimization
- [ ] **Voice Settings**: Voice selection, speed, and volume controls
- [ ] **Multimodal Input**: Seamless switching between text and voice

### Basic Avatar
- [ ] **Simple Avatar**: Basic 3D avatar in WebView (Ready Player Me)
- [ ] **Idle Animation**: Basic breathing/blinking idle state
- [ ] **Speaking Animation**: Lip-sync during AICO responses
- [ ] **Basic Emotions**: Happy, neutral, thinking expressions
- [ ] **Avatar Controls**: Mute/unmute, avatar on/off toggle

### User Experience
- [ ] **Onboarding**: Simple welcome flow and personality setup
- [ ] **Settings**: Basic preferences (name, avatar, personality sliders)
- [ ] **Offline Mode**: Graceful degradation when backend unavailable
- [ ] **Responsive Design**: Works on desktop and mobile

## Backend MVP

### LLM Integration
- [ ] **Ollama Setup**: Local LLM model management and inference
- [ ] **Model Loading**: Automatic model download and initialization
- [ ] **Prompt Engineering**: System prompts for personality and context
- [ ] **Response Generation**: Generate contextually appropriate responses
- [ ] **Resource Management**: CPU/memory monitoring for LLM operations
- [ ] **Fallback Handling**: Graceful degradation when LLM unavailable

### Memory System
- [ ] **Conversation Memory**: Store and retrieve conversation history
- [ ] **User Facts**: Remember user preferences, interests, and details
- [ ] **Context Retrieval**: Find relevant past conversations
- [ ] **Memory Consolidation**: Summarize and organize long-term memories
- [ ] **Semantic Search**: Vector-based similarity search for memories

### Personality Engine
- [ ] **Trait System**: 5 core personality dimensions (Big Five subset)
- [ ] **Expression Mapping**: Translate traits to communication style
- [ ] **Consistency Validation**: Ensure responses align with personality
- [ ] **Personality Configuration**: User-adjustable personality sliders
- [ ] **Behavioral Parameters**: Warmth, formality, curiosity, proactivity

### Emotion Recognition
- [ ] **Text Sentiment**: Natural language emotion understanding from user messages
- [ ] **Voice Analysis**: Basic emotion detection from voice tone and patterns
- [ ] **Behavioral Patterns**: User mood and preference learning over time
- [ ] **Context Awareness**: Situational emotion understanding
- [ ] **Emotion History**: Track user emotional patterns and trends

### Emotion Simulation
- [ ] **Basic Appraisal**: Simplified Component Process Model for emotion generation
- [ ] **Emotional States**: Core emotions (happy, sad, excited, calm, curious)
- [ ] **Expression Coordination**: Sync emotions across avatar, voice, and text
- [ ] **Emotional Memory**: Remember emotional context of conversations
- [ ] **Empathetic Responses**: Generate emotionally appropriate reactions

### Basic Agency
- [ ] **Initiative System**: Proactive conversation starters and engagement
- [ ] **Goal Generation**: Simple self-formulated objectives (check-ins, learning)
- [ ] **Check-in Goals**: Periodic user wellness and interest check-ins
- [ ] **Suggestion Engine**: Context-based activity and conversation suggestions
- [ ] **Follow-up Questions**: Ask relevant follow-up questions unprompted
- [ ] **Conversation Continuity**: Reference and build on previous conversations
- [ ] **Curiosity Expression**: Show interest in user activities and responses
- [ ] **Proactive Timing**: Intelligent timing for initiatives (not intrusive)

### Core Services
- [ ] **Chat API**: REST endpoints for sending/receiving messages
- [ ] **WebSocket API**: Real-time bidirectional communication
- [ ] **Memory API**: Store and retrieve user memories
- [ ] **Personality API**: Get/set personality configuration
- [ ] **Status API**: System health and availability status

## Integration Points

### Message Bus Integration
- [ ] **LLM Module**: Subscribe to conversation events, publish responses
- [ ] **Memory Module**: Subscribe to conversation events, publish memories
- [ ] **Personality Module**: Publish personality parameters and traits
- [ ] **Emotion Recognition Module**: Subscribe to user input, publish detected emotions
- [ ] **Emotion Simulation Module**: Subscribe to events, publish AICO emotional states
- [ ] **Agency Module**: Subscribe to context and emotions, publish initiatives
- [ ] **Voice Module**: Subscribe to TTS requests, publish audio responses

### Data Flow
- [ ] **User Input**: Frontend → API → Message Bus → LLM/Emotion Recognition Modules
- [ ] **Memory Storage**: Conversation events → Memory Module → Database
- [ ] **Personality Context**: Personality Module → LLM Module prompts
- [ ] **Emotion Context**: Emotion Recognition → Emotion Simulation → Expression
- [ ] **Voice Processing**: Voice input → STT → LLM → TTS → Voice output
- [ ] **Proactive Behavior**: Agency Module → Frontend notifications
- [ ] **Avatar Sync**: Emotion states → Avatar expressions and animations

## Validation Criteria

### Core Functionality
- [ ] Remembers user preferences across sessions
- [ ] Initiates conversations without prompting (agency)
- [ ] Shows consistent personality responses
- [ ] Recognizes and responds to user emotions
- [ ] Expresses appropriate emotions through avatar and voice
- [ ] Works completely offline
- [ ] Responds within 3-5 seconds

### User Experience
- [ ] Smooth chat interface with real-time updates
- [ ] Voice interaction works seamlessly with text
- [ ] Avatar animations sync with conversation and emotions
- [ ] Personality feels consistent and authentic
- [ ] Emotional responses feel natural and empathetic
- [ ] Proactive behavior feels natural, not intrusive
- [ ] Easy setup and configuration

### Emotional Intelligence
- [ ] Detects user mood from text and voice
- [ ] Responds empathetically to user emotions
- [ ] Shows appropriate emotional expressions
- [ ] Remembers emotional context of conversations
- [ ] Adapts communication style based on user mood

## Technical Requirements

- **Frontend**: Flutter for cross-platform UI
- **Backend**: Python with FastAPI for core services
- **LLM**: Local Ollama instance (Llama 2 or similar)
- **Voice**: Whisper.cpp (STT) + Coqui/Piper (TTS)
- **Storage**: SQLite for memory, ChromaDB for embeddings
- **Message Bus**: ZeroMQ pub/sub (from Foundation)
- **Avatar**: Three.js + Ready Player Me + TalkingHead.js
- **Emotion**: Basic Component Process Model implementation
- **Personality**: Big Five trait system with expression mapping

## Success Definition

User can have a 10-minute conversation where AICO:
1. **Memory**: Remembers something from earlier in the conversation
2. **Agency**: Asks a follow-up question unprompted and initiates new topics
3. **Personality**: Shows consistent personality traits and communication style
4. **Emotion Recognition**: Detects and responds appropriately to user's mood
5. **Emotion Expression**: Displays appropriate avatar expressions and voice tone
6. **Voice Interaction**: Seamlessly handles both text and voice input/output
7. **Contextual Intelligence**: Makes relevant suggestions based on conversation context
8. **Proactive Engagement**: Demonstrates curiosity and genuine interest in user responses
