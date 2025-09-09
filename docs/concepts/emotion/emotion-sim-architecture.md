# Emotion Simulation Architecture

## Overview

This document describes the technical architecture for AICO's Emotion Simulation module, focusing on its integration with the message bus system and data exchange formats. For conceptual information about the emotion model, see [`/docs/concepts/emotion/emotion-sim.md`](./emotion-sim.md).

## Bus Integration Architecture

### Message Bus Topics

The Emotion Simulation module participates in the following message bus topics:

#### Input Topics (Subscriptions)
```
- user.emotion.detected      # From Emotion Recognition
- conversation.message       # From Conversation Engine
- conversation.context       # From Context Manager
- personality.state         # From Personality Engine
- memory.relevant           # From Memory System
- voice.analysis           # From Voice & Audio
```

#### Output Topics (Publications)
```
- emotion.state.current     # Current emotional state
- emotion.expression.voice  # Voice synthesis parameters
- emotion.expression.avatar # Avatar animation parameters
- emotion.expression.text   # Text generation context
- emotion.memory.store      # Emotional experiences to store
```

## Message Schemas

Detailed message format specifications are documented in [`emotion_sim_msg.md`](./emotion-sim-msg.md). These include illustrative JSON structures for all input and output message types used by the Emotion Simulation module.

**Key Message Types:**
- **Input**: `user.emotion.detected`, `conversation.message`, `conversation.context`, `personality.state`
- **Output**: `emotion.state.current`, `emotion.expression.voice`, `emotion.expression.avatar`, `emotion.expression.text`
## Processing Pipeline

### 1. Input Aggregation

The Emotion Simulation module subscribes to multiple input topics and aggregates them into a unified context:

```python
class EmotionSimulationModule:
    def __init__(self, message_bus):
        self.bus = message_bus
        self.current_context = EmotionalContext()
        
        # Subscribe to input topics
        self.bus.subscribe("user.emotion.detected", self.on_user_emotion)
        self.bus.subscribe("conversation.message", self.on_conversation_message)
        self.bus.subscribe("conversation.context", self.on_conversation_context)
        self.bus.subscribe("personality.state", self.on_personality_state)
        
    def on_user_emotion(self, message):
        self.current_context.user_emotion = message['emotion']
        self.current_context.emotion_modalities = message['modalities']
        self.trigger_emotion_processing()
        
    def trigger_emotion_processing(self):
        if self.current_context.is_complete():
            emotional_state = self.process_emotional_response()
            self.publish_emotional_outputs(emotional_state)
```

### 2. Appraisal Processing

The core AppraisalCloudPCT algorithm processes the aggregated context:

```python
def process_emotional_response(self) -> EmotionalState:
    # Stage 1: Relevance Assessment
    relevance = self.assess_relevance(
        user_emotion=self.current_context.user_emotion,
        message_content=self.current_context.message,
        conversation_context=self.current_context.conversation
    )
    
    # Stage 2: Goal Impact Analysis
    goal_impact = self.analyze_goal_impact(
        relevance=relevance,
        relationship_phase=self.current_context.conversation['relationship_phase'],
        user_emotional_state=self.current_context.user_emotion
    )
    
    # Stage 3: Coping Assessment
    coping_strategy = self.determine_coping_strategy(
        goal_impact=goal_impact,
        personality_traits=self.current_context.personality,
        crisis_indicators=self.current_context.conversation.get('crisis_indicators', False)
    )
    
    # Stage 4: Social Appropriateness Check
    regulated_response = self.apply_social_regulation(
        raw_emotional_response=coping_strategy,
        relationship_context=self.current_context.conversation,
        personality_constraints=self.current_context.personality
    )
    
    return self.generate_cpm_emotional_state(regulated_response)
```

### 3. Output Generation

Generated emotional states are published to multiple output topics:

```python
def publish_emotional_outputs(self, emotional_state: EmotionalState):
    # Publish current emotional state
    self.bus.publish("emotion.state.current", {
        "timestamp": datetime.utcnow().isoformat(),
        "source": "emotion_simulation",
        "emotional_state": emotional_state.to_dict()
    })
    
    # Generate and publish voice parameters
    voice_params = self.generate_voice_parameters(emotional_state)
    self.bus.publish("emotion.expression.voice", voice_params)
    
    # Generate and publish avatar parameters
    avatar_params = self.generate_avatar_parameters(emotional_state)
    self.bus.publish("emotion.expression.avatar", avatar_params)
    
    # Generate and publish text context
    text_context = self.generate_text_context(emotional_state)
    self.bus.publish("emotion.expression.text", text_context)
    
    # Store emotional experience for learning
    experience = self.create_emotional_experience(emotional_state)
    self.bus.publish("emotion.memory.store", experience)
## Component Integration

### Downstream Consumers

#### Voice & Audio System
- **Subscribes to**: `emotion.expression.voice`
- **Uses**: Prosody parameters, emotional coloring, articulation style
- **Integration**: Direct parameter mapping to TTS engine settings

#### Avatar System
- **Subscribes to**: `emotion.expression.avatar`
- **Uses**: Facial expressions, body language, gaze behavior
- **Integration**: Real-time animation parameter updates via WebView JavaScript bridge

#### Conversation Engine
- **Subscribes to**: `emotion.expression.text`
- **Uses**: Emotional tone, response approach, content guidance
- **Integration**: LLM prompt injection with emotional context

#### Memory System
- **Subscribes to**: `emotion.memory.store`
- **Uses**: Emotional experiences for learning and pattern recognition
- **Integration**: Encrypted storage of emotional interaction patterns

### Upstream Providers

#### Emotion Recognition
- **Provides**: Real-time user emotional state detection
- **Message Rate**: ~10Hz during active interaction
- **Latency Requirement**: <100ms for real-time responsiveness

#### Context Manager
- **Provides**: Conversation context and relationship state
- **Message Rate**: Per conversation turn + periodic updates
- **Latency Requirement**: <50ms for context updates

#### Personality Engine
- **Provides**: Current personality state and interaction preferences
- **Message Rate**: On personality changes + periodic state broadcasts
- **Latency Requirement**: <200ms for personality updates

## Performance Requirements

### Latency Targets
- **End-to-end emotion processing**: <200ms from input to output
- **Voice parameter generation**: <50ms for real-time speech synthesis
- **Avatar parameter generation**: <33ms for 30fps animation updates
- **Text context generation**: <100ms for conversation flow

### Throughput Requirements
- **Concurrent users**: Single-user system (local processing)
- **Message processing rate**: 100+ messages/second during active interaction
- **Memory usage**: <512MB for emotion processing components

### Reliability Requirements
- **Availability**: 99.9% uptime during user sessions
- **Graceful degradation**: Fallback to neutral emotional state on processing failures
- **Recovery time**: <1 second for component restart

## Module Components

The Emotion Simulation module consists of four core components that work together to process emotional responses:

### 1. Input Aggregation Component

**Purpose**: Collects and synchronizes inputs from multiple message bus topics into a unified emotional context.

**Responsibilities**:
- **Message Subscription**: Subscribes to all input topics (`user.emotion.detected`, `conversation.message`, `conversation.context`, `personality.state`)
- **Context Assembly**: Aggregates incoming messages into a complete emotional processing context
- **Temporal Synchronization**: Ensures all inputs are temporally aligned for coherent processing
- **Completeness Validation**: Determines when sufficient context is available to trigger emotion processing
- **Timeout Management**: Handles missing or delayed inputs with appropriate fallback strategies

**Key Features**:
- **Buffering**: Short-term message buffering to handle timing variations
- **Priority Handling**: Prioritizes critical inputs (e.g., crisis indicators) for immediate processing
- **State Tracking**: Maintains current context state across multiple processing cycles

**Output**: Unified `EmotionalContext` object containing all necessary input data

### 2. Appraisal Processing Component

**Purpose**: Implements the core AppraisalCloudPCT algorithm to evaluate situational significance and generate emotional appraisals.

**Responsibilities**:
- **Relevance Assessment**: Evaluates "Does this situation matter to me?" based on user emotional state and context
- **Goal Impact Analysis**: Determines "What does this mean for my companion goals?" considering relationship phase and user needs
- **Coping Evaluation**: Assesses "Can I handle this appropriately?" based on personality traits and situation complexity
- **Normative Checking**: Validates "Is my response socially appropriate?" considering relationship boundaries and social context

**Processing Stages**:
1. **Stage 1 - Relevance**: Calculates relevance score (0.0-1.0) based on user emotional intensity and interaction context
2. **Stage 2 - Implication**: Analyzes impact on companion relationship goals (supportive, neutral, challenging)
3. **Stage 3 - Coping**: Determines appropriate response capability and approach style
4. **Stage 4 - Normative**: Applies social appropriateness filters and relationship boundary checks

**Key Features**:
- **Configurable Sensitivity**: Adjustable appraisal sensitivity parameters
- **Context Weighting**: Different weights for various contextual factors
- **Crisis Detection**: Special handling for crisis situations requiring immediate response

**Output**: `AppraisalResult` containing relevance scores, goal impacts, and response strategies

### 3. Emotion Regulation Component

**Purpose**: Applies social, ethical, and personality constraints to ensure appropriate emotional responses.

**Responsibilities**:
- **Social Appropriateness**: Ensures emotional responses are suitable for the current relationship phase and social context
- **Crisis Protocol**: Applies specialized emotional regulation during user crisis situations
- **Personality Alignment**: Modulates emotional intensity and expression style based on personality traits
- **Boundary Maintenance**: Enforces companion relationship boundaries and ethical constraints
- **Intensity Modulation**: Adjusts emotional expression intensity based on user state and context

**Regulation Strategies**:
- **Intensity Scaling**: Reduces or amplifies emotional expression based on appropriateness
- **Style Adaptation**: Modifies expression style (e.g., more gentle, more confident) based on context
- **Crisis Override**: Special protocols for handling user emotional crises
- **Relationship Respect**: Maintains appropriate emotional distance based on relationship development

**Key Features**:
- **Configurable Constraints**: Adjustable regulation strength and personality influence
- **Multi-layered Filtering**: Multiple regulation passes for different constraint types
- **Context Sensitivity**: Different regulation strategies for different situational contexts

**Output**: Regulated `EmotionalState` with appropriate constraints applied

### 4. Output Synthesis Component

**Purpose**: Transforms the regulated emotional state into coordinated expression parameters for different modalities.

**Responsibilities**:
- **Voice Parameter Generation**: Creates prosodic and emotional coloring parameters for speech synthesis
- **Avatar Parameter Generation**: Generates facial expression, body language, and gaze behavior parameters
- **Text Context Generation**: Produces emotional tone and content guidance for LLM text generation
- **Memory Experience Creation**: Formats emotional experiences for storage and learning
- **Multi-modal Coordination**: Ensures consistent emotional expression across all output channels

**Synthesis Processes**:
- **CPM Component Mapping**: Maps 5-component emotional state to specific expression parameters
- **Modality Translation**: Converts abstract emotional components to concrete expression parameters
- **Synchronization**: Ensures temporal alignment of expression parameters across modalities
- **Intensity Calibration**: Adjusts expression intensity for each modality's characteristics

**Output Channels**:
- **Voice**: Prosody, emotional coloring, articulation parameters
- **Avatar**: Facial expressions, body language, gaze behavior
- **Text**: Emotional tone, response approach, content guidance
- **Memory**: Structured emotional experience data

**Key Features**:
- **Modality-Specific Optimization**: Tailored parameter generation for each expression channel
- **Real-time Performance**: Optimized for low-latency parameter generation
- **Consistency Maintenance**: Ensures coherent emotional expression across all modalities

## Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Emotion         │    │ Conversation    │    │ Personality     │
│ Recognition     │───▶│ Context         │───▶│ Engine          │
│                 │    │ Manager         │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Message Bus (ZeroMQ/MQTT)                    │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Emotion Simulation Module                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │ Input       │  │ Appraisal   │  │ Emotion     │  │ Output  │ │
│  │ Aggregation │─▶│ Processing  │─▶│ Regulation  │─▶│ Synthesis│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Message Bus (ZeroMQ/MQTT)                    │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Voice & Audio   │    │ Avatar System   │    │ Conversation    │
│ System          │    │                 │    │ Engine          │
│ System          │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Configuration

Example module configuration:

### Module Configuration
```yaml
emotion_simulation:
  processing:
    appraisal_sensitivity: 0.7
    regulation_strength: 0.8
    personality_influence: 0.6
    
  performance:
    max_processing_latency_ms: 200
    batch_size: 1
    thread_pool_size: 4
    
  message_bus:
    broker_url: "tcp://localhost:5555"
    input_topics:
      - "user.emotion.detected"
      - "conversation.message"
      - "conversation.context"
      - "personality.state"
    output_topics:
      - "emotion.state.current"
      - "emotion.expression.voice"
      - "emotion.expression.avatar"
      - "emotion.expression.text"
      
  cloud_enhancement:
    enabled: false
    anonymization_level: "high"
    learning_participation: false
```

## Error Handling

### Fault Tolerance
- **Input timeout**: Default to neutral emotional state after 500ms without required inputs
- **Processing failure**: Fallback to last known stable emotional state
- **Output delivery failure**: Retry with exponential backoff, max 3 attempts
- **Component crash**: Automatic restart with state recovery from last checkpoint

### Monitoring
- **Health checks**: Periodic processing pipeline validation
- **Performance metrics**: Latency, throughput, error rates
- **Emotional coherence**: Validation of emotional state transitions
- **User experience impact**: Correlation with user satisfaction metrics
