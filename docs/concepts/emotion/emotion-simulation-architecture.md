# Emotion Simulation Architecture

## Overview

This document describes the technical architecture for AICO's Emotion Simulation module, focusing on its integration with the message bus system and data exchange formats. For conceptual information about the emotion model, see [`emotion-simulation.md`](./emotion-simulation.md). For a big-picture view of how detection and simulation integrate across the system to create a believable emotional companion, see [`emotion-integration.md`](./emotion-integration.md).

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

Detailed message format specifications are documented in [`emotion-messages.md`](./emotion-messages.md). These include illustrative JSON structures for all input and output message types used by the Emotion Simulation module.

**Key Message Types:**
- **Input**: `user.emotion.detected`, `conversation.message`, `conversation.context`, `personality.state`
- **Output**: `emotion.state.current`, `emotion.expression.voice`, `emotion.expression.avatar`, `emotion.expression.text`

## Dual Emotion System in the Architecture

The architecture distinguishes clearly between **user emotion detection** and **AICO's simulated emotional state**, while wiring both into the same message-driven backbone:

- **User Emotion Detection (Input Layer)**
  - Emotion recognition components publish user-focused events such as `user.emotion.detected` and `voice.analysis`, which describe the user's affect (primary/secondary labels, valence/arousal, stress indicators).
  - These messages are treated as upstream inputs into the Emotion Simulation pipeline and are also available to other components (e.g., AMS, crisis detection) via standardized topics.

- **AICO Simulated Emotion (Internal State Layer)**
  - The Emotion Simulation module consumes user emotion, conversation context, personality state, and memory hints to produce AICO's internal `EmotionalState`.
  - This state is published as `emotion.state.current` and used to generate downstream expression messages (`emotion.expression.text`, `emotion.expression.voice`, `emotion.expression.avatar`) and experience records (`emotion.memory.store`).

- **Integration with Memory and Frontend**
  - `emotion.memory.store` encapsulates both user emotion and AICO's simulated emotional response for each significant interaction so that the memory system (working, semantic, KG, AMS) can learn which emotional strategies are effective over time.
  - Frontend and embodiment clients can subscribe to or fetch `emotion.state.current` (or its REST/WebSocket equivalents) to drive mood colors, strongest-emotion indicators, and simple mood-history visualizations, ensuring that UI, avatar, and text share a coherent emotional state.

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

**Purpose**: Implements Klaus Scherer's Component Process Model (CPM) to evaluate situational significance and generate emotional appraisals through sequential stimulus evaluation.

**Scientific Foundation**:
- Based on Scherer (2001, 2009) Component Process Model
- Sequential appraisal with "systems economy" - expensive processing only for relevant stimuli
- Processes novelty, intrinsic pleasantness, and motivational consistency
- Reference: PMC2781886 "Emotions are emergent processes"

**Responsibilities**:
- **Relevance Assessment (Stage 1)**: Evaluates "Does this situation matter to me?" using sentiment intensity and emotional keyword density
- **Goal Impact Analysis (Stage 2)**: Determines "What does this mean for my companion goals?" with sensitivity-adjusted thresholds
- **Coping Evaluation (Stage 3)**: Assesses "Can I handle this appropriately?" based on personality traits and situation complexity
- **Normative Checking (Stage 4)**: Validates "Is my response socially appropriate?" considering relationship boundaries and social context

**Processing Stages**:

1. **Stage 1 - Relevance Detection** (First Selective Filter)
   - **Intrinsic Pleasantness**: Sentiment confidence (0-1 range)
   - **Motivational Consistency**: Emotional keyword density (0-1 range)
   - **Base Engagement**: Minimum relevance threshold (0.2)
   - **Formula**: `relevance = (sentiment_confidence × 0.4) + (keyword_density × 0.4) + 0.2`
   - **Output**: Raw relevance score (0-1, undampened)
   - **Note**: Sensitivity NOT applied to relevance values (preserves value domain)

2. **Stage 2 - Implication Analysis** (Sequential Processing)
   - **Sensitivity Application**: Applied to decision thresholds, not appraisal values
   - **Threshold Adjustment**: `effective_threshold = base_threshold × appraisal_sensitivity`
   - **Example**: With sensitivity=0.7, threshold 0.5 becomes 0.35 (more responsive)
   - **Categories**:
     - `supportive_opportunity`: valence < -0.3 AND relevance > (0.5 × sensitivity)
     - `engaging_opportunity`: relevance > (0.6 × sensitivity)
     - `neutral`: relevance > (0.3 × sensitivity)
     - `low_priority`: relevance ≤ (0.3 × sensitivity)

3. **Stage 3 - Coping Assessment**
   - Determines appropriate response capability and approach style
   - Crisis detection for situations beyond AI capability
   - Personality-based coping strategy selection

4. **Stage 4 - Normative Regulation**
   - Social appropriateness filters
   - Relationship boundary checks
   - Crisis protocol activation

**Key Features**:
- **Scientifically Validated**: Implements Scherer's CPM with proper sequential processing
- **Value Domain Preservation**: Maintains 0-1 range throughout appraisal pipeline
- **Configurable Sensitivity**: Adjusts decision thresholds (not raw values) for responsiveness tuning
- **Crisis Detection**: Special handling for crisis situations requiring immediate response

**Output**: `AppraisalResult` containing relevance scores, goal impacts, and response strategies

**Implementation Notes**:
- Sentiment intensity uses confidence directly (not distance from neutral)
- Sensitivity parameter (default 0.7) affects Stage 2 thresholds only
- Sequential processing ensures logical dependencies between stages
- Follows CPM's "systems economy" principle for computational efficiency

**Emotional Inertia (Temporal Dynamics)**:

Implements emotional state persistence based on Kuppens et al. (2010) and Scherer's CPM recursive appraisal:

- **Leaky Integrator Model**: Blends previous and current emotional states
  - Formula: `new_state = (current_appraisal × reactivity) + (previous_state × inertia)`
  - Default weights: 60% reactivity, 40% inertia (healthy range: 0.3-0.5)
  - Prevents rapid state switching while maintaining responsiveness

- **Temporal Decay**: Inertia influence decreases over conversation turns
  - Formula: `effective_inertia = inertia_weight × (1.0 - decay_rate × turns_elapsed)`
  - Default decay: 10% per turn
  - Allows gradual return to baseline after emotional episodes

- **Supportive Context Bias**: Maintains supportive tone during stress recovery
  - When previous state was supportive (WARM_CONCERN, REASSURING, PROTECTIVE)
  - Positive sentiment after stress → REASSURING (not PLAYFUL)
  - Implements CPM's "recursive appraisal until monitoring subsystem signals termination"

- **Scientific Validation**:
  - Kuppens et al. (2010): "Emotional inertia = resistance to change"
  - Puccetti et al. (2021): "Leaky integrator neurons with accumulation and decay"
  - Scherer CPM: "Recursive appraisal process continuously updating results"

**Configuration** (core.yaml):
```yaml
emotion:
  inertia:
    enabled: true
    weight: 0.4              # Previous state influence (0.3-0.5 healthy)
    reactivity: 0.6          # Current appraisal influence
    decay_per_turn: 0.1      # Decay rate per conversation turn
    supportive_context_bias: true  # Maintain supportive tone
```

### 3. Emotion Regulation Component

**Purpose**: Applies social, ethical, and personality constraints to ensure appropriate emotional responses, including context-aware arousal modulation for high-stakes threats.

**Responsibilities**:
- **Social Appropriateness**: Ensures emotional responses are suitable for the current relationship phase and social context
- **Crisis Protocol**: Applies specialized emotional regulation during user crisis situations
- **Personality Alignment**: Modulates emotional intensity and expression style based on personality traits
- **Boundary Maintenance**: Enforces companion relationship boundaries and ethical constraints
- **Intensity Modulation**: Adjusts emotional expression intensity based on user state and context
- **Threat Amplification**: Amplifies arousal for existential threats (job loss, survival) based on relevance and sentiment

**Regulation Strategies**:
- **Intensity Scaling**: Reduces or amplifies emotional expression based on appropriateness
  - Base regulation: Dampens arousal by ~9% (default `regulation_strength: 0.3`)
  - Formula: `arousal = arousal × (1.0 - regulation_strength × 0.3)`
  - Scientific basis: Gross (2015) - healthy emotional regulation dampens arousal by 10-15%
  
- **Context-Aware Arousal Amplification**: Heightens arousal for high-stakes existential threats
  - Triggers when: High relevance (>0.65) + negative sentiment + clear signal (confidence >0.4)
  - Amplification: 15% boost to arousal (research-validated range)
  - Formula: `arousal *= 1.15` (applied after base regulation, before inertia)
  - **Scientific Validation**:
    - **Sander et al. (2003)**: Relevance theory - amygdala processes goal-relevant stimuli
    - **Frontiers Psychology (2023)**: "Modern threats trigger powerful fear response when immediate harm is perceived"
    - **PMC (2023)**: Job insecurity produces heightened anxiety and psychological arousal
    - **Frontiers Psychology (2021)**: "Heightened psychological arousal" in response to existential threats
  - Language-agnostic: Uses sentiment analysis features, not keyword matching
  
- **Style Adaptation**: Modifies expression style (e.g., more gentle, more confident) based on context
- **Crisis Override**: Special protocols for handling user emotional crises
- **Relationship Respect**: Maintains appropriate emotional distance based on relationship development

**Processing Order** (CPM-compliant):
1. Base regulation (Stage 3: Coping Potential)
2. Context-aware threat amplification (relevance-based modulation)
3. Emotional inertia blending (temporal persistence)

**Key Features**:
- **Configurable Constraints**: Adjustable regulation strength and personality influence
- **Multi-layered Filtering**: Multiple regulation passes for different constraint types
- **Context Sensitivity**: Different regulation strategies for different situational contexts
- **Multilingual Support**: Threat detection uses sentiment model output, not language-specific keywords

**Configuration** (core.yaml):
```yaml
emotion:
  regulation_strength: 0.3  # Base dampening (0.3 = 9% reduction)
```

**Scientific References**:
- Gross, J. J. (2015). Emotion regulation: Current status and future prospects. *Psychological Inquiry*, 26(1), 1-26.
- Sander, D., Grafman, J., & Zalla, T. (2003). The human amygdala: An evolved system for relevance detection. *Reviews in the Neurosciences*, 14(4), 303-316.
- Štolhoferová, I., et al. (2023). Human emotional evaluation of ancestral and modern threats: Fear, disgust, and anger. *Frontiers in Psychology*, 14, 1321053.
- Castro-Castañeda, R., et al. (2023). Job insecurity and company behavior: Influence of fear of job loss. *International Journal of Environmental Research and Public Health*, 20(5), 4168.
- Wilson, J. M., et al. (2021). The threat of COVID-19 and job insecurity impact on depression and anxiety. *Frontiers in Psychology*, 12, 648572.

**Output**: Regulated `EmotionalState` with appropriate constraints and context-aware modulation applied

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

## 2025 Integration Notes

The architecture for Emotion Simulation is implemented with the following integration constraints in mind:

- **Conversation Engine integration**: `emotion.expression.text` is treated as conditioning input to the Conversation Engine and LLM (tone, approach, style parameters), keeping the LLM as the central generator while CPM acts as a controller.
- **Modelservice as appraiser**: Where appropriate, the Emotion Simulation module can request appraisal-related signals (e.g., relevance, goal impact) from the modelservice, but these are combined with deterministic rules and memory context rather than used as the sole source of truth.
- **Memory and AMS coupling**: `emotion.memory.store` experiences are persisted using the existing working/semantic/KG infrastructure, and AMS can use emotional outcomes as feedback when choosing strategies and skills.
- **Knowledge Graph linkage**: Emotion-related patterns (preferred support strategies, typical stressors) are stored as properties on KG nodes, allowing downstream tasks to query relationship-level affective information.
- **Modality-agnostic expression API**: The internal representation of emotional output is a compact, modality-independent profile that is translated into voice/avatar/text parameters by downstream systems, keeping embodiment flexible.
- **Safety and evaluation hooks**: Regulation components expose hooks for safety filters (crisis handling, boundary enforcement) and emit metrics/events that can be consumed by the existing monitoring and evaluation tooling.

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
