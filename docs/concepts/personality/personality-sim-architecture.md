# Personality Simulation Architecture

## Overview

This document describes the technical architecture for AICO's Personality Simulation module, focusing on its integration with the message bus system and data exchange formats. For conceptual information about the personality model, see [`/docs/concepts/personality/personality_sim.md`](../concepts/personality/personality_sim.md).

## Bus Integration Architecture

### Message Bus Topics

The Personality Simulation module participates in the following message bus topics:

#### Input Topics (Subscriptions)
```
- user.interaction.history     # From Memory System
- conversation.context        # From Context Manager
- emotion.state.current       # From Emotion Simulation
- memory.consolidation        # From Memory System
- agency.goals.current        # From Autonomous Agent
- user.feedback               # From Conversation Engine
```

#### Output Topics (Publications)
```
- personality.state.current   # Current personality state
- personality.expression.communication  # Communication style parameters
- personality.expression.decision       # Decision-making parameters
- personality.expression.emotional      # Emotional tendency parameters
- personality.memory.store             # Personality experiences to store
```

## Message Schemas

Detailed message format specifications are documented in [`personality_sim_msg.md`](./personality_sim_msg.md). These include illustrative JSON structures for all input and output message types used by the Personality Simulation module.

**Key Message Types:**
- **Input**: `user.interaction.history`, `conversation.context`, `emotion.state.current`
- **Output**: `personality.state.current`, `personality.expression.communication`, `personality.expression.decision`

## Processing Pipeline

### 1. Input Aggregation

The Personality Simulation module subscribes to multiple input topics and aggregates them into a unified context:

```python
class PersonalitySimulationModule:
    def __init__(self, message_bus):
        self.bus = message_bus
        self.current_context = PersonalityContext()
        self.trait_vector = TraitVector()
        self.value_system = ValueSystem()
        
        # Subscribe to input topics
        self.bus.subscribe("user.interaction.history", self.on_interaction_history)
        self.bus.subscribe("conversation.context", self.on_conversation_context)
        self.bus.subscribe("emotion.state.current", self.on_emotion_state)
        self.bus.subscribe("memory.consolidation", self.on_memory_consolidation)
        self.bus.subscribe("user.feedback", self.on_user_feedback)
        
    def on_interaction_history(self, message):
        self.current_context.interaction_patterns = message['patterns']
        self.current_context.relationship_data = message['relationship']
        self.trigger_personality_processing()
        
    def trigger_personality_processing(self):
        if self.current_context.is_complete():
            personality_state = self.process_personality_state()
            self.publish_personality_outputs(personality_state)
```

### 2. Trait Processing

The core TraitEmergence algorithm processes the aggregated context:

```python
def process_personality_state(self) -> PersonalityState:
    # Update trait vector based on significant experiences
    if self.current_context.has_significant_experiences():
        self.personality_evolution.process_experiences(
            self.current_context.get_significant_experiences()
        )
    
    # Generate current personality state
    personality_state = PersonalityState(
        trait_vector=self.trait_vector.get_current(),
        value_system=self.value_system.get_current(),
        interaction_style=self.expression_mapper.generate_communication_style(
            self.current_context.conversation
        ),
        emotional_tendencies=self.expression_mapper.generate_emotional_tendencies(),
        decision_weights=self.expression_mapper.generate_decision_weights()
    )
    
    # Validate for consistency with past behavior
    personality_state = self.consistency_validator.validate_state(
        personality_state,
        self.current_context.conversation
    )
    
    return personality_state
```

### 3. Output Generation

Generated personality states are published to multiple output topics:

```python
def publish_personality_outputs(self, personality_state: PersonalityState):
    # Publish current personality state
    self.bus.publish("personality.state.current", {
        "timestamp": datetime.utcnow().isoformat(),
        "source": "personality_simulation",
        "personality_state": personality_state.to_dict()
    })
    
    # Generate and publish communication style parameters
    comm_params = self.generate_communication_parameters(personality_state)
    self.bus.publish("personality.expression.communication", comm_params)
    
    # Generate and publish decision-making parameters
    decision_params = self.generate_decision_parameters(personality_state)
    self.bus.publish("personality.expression.decision", decision_params)
    
    # Generate and publish emotional tendency parameters
    emotional_params = self.generate_emotional_parameters(personality_state)
    self.bus.publish("personality.expression.emotional", emotional_params)
    
    # Store personality experience for learning
    experience = self.create_personality_experience(personality_state)
    self.bus.publish("personality.memory.store", experience)
```

## Component Integration

### Downstream Consumers

#### Conversation Engine
- **Subscribes to**: `personality.expression.communication`
- **Uses**: Communication style, topic preferences, interaction patterns
- **Integration**: LLM prompt injection with personality context

#### Emotion Simulation
- **Subscribes to**: `personality.state.current`
- **Uses**: Trait-based emotional tendencies, regulation parameters
- **Integration**: Personality-influenced appraisal processing

#### Autonomous Agent
- **Subscribes to**: `personality.expression.decision`
- **Uses**: Decision weights, goal alignment, value priorities
- **Integration**: Personality-aligned goal generation and planning

#### Memory System
- **Subscribes to**: `personality.memory.store`
- **Uses**: Personality experiences for learning and pattern recognition
- **Integration**: Encrypted storage of personality development patterns

### Upstream Providers

#### Memory System
- **Provides**: Interaction history and relationship development data
- **Message Rate**: Periodic updates + significant event triggers
- **Latency Requirement**: <200ms for history updates

#### Emotion Simulation
- **Provides**: Current emotional state and experience data
- **Message Rate**: ~5Hz during active interaction
- **Latency Requirement**: <100ms for emotional state updates

#### Conversation Engine
- **Provides**: User feedback and conversation context
- **Message Rate**: Per conversation turn
- **Latency Requirement**: <50ms for context updates

## Performance Requirements

### Latency Targets
- **End-to-end personality processing**: <300ms from input to output
- **Communication parameter generation**: <100ms for conversation flow
- **Decision parameter generation**: <150ms for agent decision-making
- **Emotional parameter generation**: <100ms for emotion simulation

### Throughput Requirements
- **Concurrent users**: Single-user system (local processing)
- **Message processing rate**: 50+ messages/second during active interaction
- **Memory usage**: <256MB for personality processing components

### Reliability Requirements
- **Availability**: 99.9% uptime during user sessions
- **Graceful degradation**: Fallback to baseline personality on processing failures
- **Recovery time**: <1 second for component restart

## Module Components

The Personality Simulation module consists of five core components that work together to process personality expression:

### 1. Trait Vector System

**Purpose**: Maintains the multi-dimensional representation of personality traits and their interrelationships.

**Responsibilities**:
- **Trait Representation**: Maintains numerical values for all personality dimensions
- **Trait Relationships**: Manages correlations and constraints between traits
- **Trait Stability**: Ensures appropriate resistance to rapid trait changes
- **Framework Conversion**: Maps between different personality frameworks as needed
- **Trait Retrieval**: Provides current trait values for downstream components

**Key Features**:
- **Extended Dimensions**: Support for Big Five + HEXACO + characteristic adaptations
- **Coherence Constraints**: Psychologically plausible trait combinations
- **Metadata Tracking**: Trait stability and confidence metrics

**Output**: `TraitVector` object containing all current trait values and metadata

### 2. Value System

**Purpose**: Manages ethical principles, preferences, and interaction priorities.

**Responsibilities**:
- **Value Representation**: Maintains numerical values for core values and principles
- **Preference Management**: Tracks and updates interaction and topic preferences
- **Ethical Boundary Enforcement**: Defines behavioral constraints based on values
- **Value Conflicts**: Resolves competing values based on priority hierarchy
- **Preference Learning**: Updates preferences based on user feedback and interactions

**Key Features**:
- **Hierarchical Values**: Prioritized value structure with conflict resolution
- **Contextual Activation**: Context-dependent value importance weighting
- **Preference History**: Tracking of preference development over time

**Output**: `ValueSystem` object containing current values, preferences, and boundaries

### 3. Expression Mapper

**Purpose**: Translates abstract personality traits into concrete behavioral parameters.

**Responsibilities**:
- **Communication Mapping**: Converts traits to communication style parameters
- **Decision Mapping**: Converts traits to decision-making weights and priorities
- **Emotional Mapping**: Converts traits to emotional tendency parameters
- **Context Adaptation**: Adjusts expression based on situational context
- **Relationship Adaptation**: Modifies expression based on relationship development

**Processing Stages**:
1. **Trait Retrieval**: Gets current trait vector and value system
2. **Context Analysis**: Analyzes current conversation and relationship context
3. **Parameter Generation**: Calculates expression parameters based on traits and context
4. **Consistency Check**: Validates parameters against historical patterns

**Key Features**:
- **Multi-domain Mapping**: Separate mappings for different behavioral domains
- **Contextual Modulation**: Context-specific expression adjustments
- **Relationship Awareness**: Expression adapted to relationship development stage

**Output**: Expression parameter sets for communication, decision-making, and emotional tendencies

### 4. Consistency Validator

**Purpose**: Ensures behavioral coherence over time and across different contexts.

**Responsibilities**:
- **Pattern Tracking**: Monitors behavioral patterns across interactions
- **Consistency Checking**: Validates proposed behaviors against historical patterns
- **Anomaly Detection**: Identifies potentially inconsistent behaviors
- **Adjustment Generation**: Modifies inconsistent behaviors to maintain coherence
- **Memory Integration**: Records behavioral patterns for future validation

**Validation Strategies**:
- **Historical Comparison**: Compares with past behaviors in similar contexts
- **Trait Alignment**: Ensures behaviors align with current trait profile
- **Narrative Coherence**: Maintains consistent character development
- **Contextual Allowance**: Permits appropriate variation based on context

**Key Features**:
- **Configurable Strictness**: Adjustable consistency requirements
- **Context Sensitivity**: Different consistency thresholds for different contexts
- **Memory Leveraging**: Uses episodic and semantic memory for validation

**Output**: Validated or adjusted personality expression parameters

### 5. Personality Evolution System

**Purpose**: Manages gradual personality development over time based on experiences.

**Responsibilities**:
- **Experience Analysis**: Evaluates experiences for personality impact
- **Trait Updating**: Modifies traits based on significant experiences
- **Evolution Rate Control**: Manages pace of personality development
- **Coherence Maintenance**: Ensures trait changes maintain psychological plausibility
- **Development Tracking**: Records personality development over time

**Evolution Processes**:
- **Significance Assessment**: Determines which experiences warrant trait changes
- **Impact Calculation**: Computes trait impacts for significant experiences
- **Constrained Application**: Applies changes within stability constraints
- **Coherence Enforcement**: Maintains plausible trait relationships

**Key Features**:
- **Configurable Evolution Rate**: Adjustable pace of personality development
- **Experience Weighting**: Different weights for different experience types
- **User Influence**: User feedback affects evolution direction and rate

**Output**: Updated trait vector and value system reflecting personality development

## Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Memory          │    │ Conversation    │    │ Emotion         │
│ System          │───▶│ Context         │───▶│ Simulation      │
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
│                  Personality Simulation Module                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │ Trait       │  │ Expression  │  │ Consistency │  │ Output  │ │
│  │ Processing  │─▶│ Mapping     │─▶│ Validation  │─▶│ Generation│ │
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
│ Conversation    │    │ Emotion         │    │ Autonomous      │
│ Engine          │    │ Simulation      │    │ Agent           │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Configuration

Example module configuration:

### Module Configuration
```yaml
personality_simulation:
  processing:
    trait_stability: 0.8
    evolution_rate: 0.01
    consistency_threshold: 0.7
    
  performance:
    max_processing_latency_ms: 300
    batch_size: 1
    thread_pool_size: 2
    
  message_bus:
    broker_url: "tcp://localhost:5555"
    input_topics:
      - "user.interaction.history"
      - "conversation.context"
      - "emotion.state.current"
      - "memory.consolidation"
      - "user.feedback"
    output_topics:
      - "personality.state.current"
      - "personality.expression.communication"
      - "personality.expression.decision"
      - "personality.expression.emotional"
      
  cloud_enhancement:
    enabled: false
    anonymization_level: "high"
    learning_participation: false
    
  initial_traits:
    extraversion: 0.6
    agreeableness: 0.8
    conscientiousness: 0.7
    neuroticism: 0.3
    openness: 0.9
    honesty_humility: 0.7
```

## Error Handling

### Fault Tolerance
- **Input timeout**: Default to baseline personality after 1000ms without required inputs
- **Processing failure**: Fallback to last known stable personality state
- **Output delivery failure**: Retry with exponential backoff, max 3 attempts
- **Component crash**: Automatic restart with state recovery from last checkpoint

### Monitoring
- **Health checks**: Periodic processing pipeline validation
- **Performance metrics**: Latency, throughput, error rates
- **Personality coherence**: Validation of trait stability and coherence
- **User experience impact**: Correlation with user satisfaction metrics
