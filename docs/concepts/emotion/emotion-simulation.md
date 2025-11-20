# Emotion Simulation

## Overview

The Emotion Simulation component generates sophisticated emotional states using **C-CPM** (Conversational Component Process Model), creating believable emotional responses that enhance AICO's companion experience. This system combines Scherer's CPM appraisal theory with modern dialogue state tracking to generate context-aware, multi-dimensional emotional states that coordinate expression across voice, avatar, and text modalities.

For user emotion detection, see [`emotion-detection.md`](./emotion-detection.md).
For system-wide integration and believability, see [`emotion-integration.md`](./emotion-integration.md).

## Rationale

### Why C-CPM?

AICO requires sophisticated emotional intelligence that goes beyond simple reactive responses. C-CPM provides:

- **Human-Like Emotion Generation**: Emotions emerge through cognitive appraisal processes, mirroring how humans actually experience emotions
- **Conversation-Aware Responses**: Dialogue state tracking enables episode detection, greeting recognition, and resolution awareness
- **Context Continuity**: Tracks emotional arcs across conversation turns (stress → support → resolution)
- **Pragmatic Intelligence**: Understands conversation structure (greetings, gratitude, problem resolution)
- **Relationship Intelligence**: Social context and relationship dynamics influence emotional appropriateness
- **Crisis Handling**: Built-in emotion regulation for extreme situations
- **Ethical Constraints**: Social appropriateness checks ensure companion-suitable responses

### Scientific Foundation

C-CPM combines multiple validated theories:

**Core: Scherer's Component Process Model (CPM, 2001)**
- The leading emotion theory in contemporary psychology
- Emotions emerge from a **4-stage appraisal process**

**Extension: Dialogue State Tracking (Feng et al. 2024)**
- Modern task-oriented dialogue systems
- Emotion-aware conversation management

**Extension: Episode-Aware Modeling (Van et al. 2025)**
- Hypergraph emotional propagation in conversations
- Multi-turn emotional dependencies

**Extension: Pragmatic Communication (Grice 1975)**
- Speech act detection (greetings, gratitude, resolution)
- Conversation structure awareness

### CPM Appraisal Stages

**Stage 1: Relevance Check**
- "Does this event matter to me?"
- Determines if emotional response is warranted
- **For AICO**: Does this conversation event require emotional attention?

**Stage 2: Implication Check**
- "What does this mean for my goals?"
- Evaluates goal conduciveness/obstruction
- **For AICO**: Does this help or hinder my companion objectives?

**Stage 3: Coping Check**
- "Can I handle this situation?"
- Assesses control and power dynamics
- **For AICO**: What's the appropriate assertiveness level?

**Stage 4: Normative Check**
- "Is this consistent with my values?"
- Evaluates moral/social appropriateness
- **For AICO**: Does this align with my personality and relationship norms?

## Dual Emotion System: User & AICO

AICO's emotion capabilities are deliberately split into two tightly coordinated layers that work together to create believable companionship:

- **User Emotion Detection ("what you feel")**
  - Dedicated recognition components infer the user's current emotional state from text (and in future, voice/vision) and publish it as structured signals via message bus.
  - These signals capture *your* affect: primary/secondary emotions, valence/arousal, stress indicators, and high-level intent (e.g., "venting", "celebrating").
  - The detected user emotion is a core input into appraisal: it helps AICO decide how important a situation is, what kind of support is appropriate, and whether crisis protocols should engage.

- **AICO's Simulated Emotion ("what AICO feels")**
  - Implemented in `/backend/services/emotion_engine.py` using C-CPM (Conversational CPM).
  - Maintains AICO's own internal emotional state, derived from conversation events, user emotion, relationship history, personality, and conversational context.
  - This internal state includes mood, appraisal results, motivational tendencies, emotional episodes, and expression profiles that drive how AICO speaks, writes, and (later) moves.
  - AICO's simulated emotions are *not* just a mirror of the user's state—they reflect AICO's personality, values, conversational awareness, and evolving relationship with you.

### How They Interact and Tie into the System

- **Appraisal as the bridge**: User emotion feeds into the appraisal checks (relevance, implication, coping, normative), which in turn update AICO's own emotional state, ensuring AICO both understands and reacts from a believable internal perspective.
- **Memory integration**: Both user emotion and AICO's simulated emotion are stored alongside working and semantic memories (and in the knowledge graph), allowing AICO to remember emotionally significant moments and refine future responses.
- **Companion believability**: The dual system is designed so that AICO is not just emotion-reactive but *emotionally present*—able to recognize how you feel while maintaining her own coherent, evolving emotional life across conversations.

## Architecture

### C-CPM Three-Layer Architecture

C-CPM extends traditional CPM with conversational awareness through three integrated layers:

#### Layer 1: Conversational Context (NEW)
Tracks dialogue state and emotional episodes across conversation turns:

- **Dialogue State Tracker**: Maintains history of last 5 turns with valence, arousal, and relevance
- **Episode Detector**: Identifies emotional arcs (stress → support → resolution)
  - Stress episodes: Sustained negative valence (v < -0.3, a > 0.4)
  - Resolution detection: Sustained positive sentiment (2+ turns v > 0.3, current v > 0.5) after stress
  - Episode continuity: Maintains supportive context during active episodes
  - Scientific basis: Gross (2015) - emotion regulation is a process, not an event
  - Prevents premature resolution on polite gratitude ("thank you") vs genuine resolution ("worked it out")

**Implementation**: `/backend/services/conversational_context.py`

#### Layer 2: CPM Appraisal (ENHANCED)
Traditional 4-stage appraisal enhanced with context awareness:

- **Stage 1 - Relevance**: Base relevance + context adjustments
  - Boost by +0.15 during stress episodes (continued concern)
- **Stage 2 - Goal Impact**: Episode-aware goal assessment
  - `resolution_opportunity`: Positive after stress episode
  - Maintains `supportive_opportunity` during active stress
- **Stage 3 - Coping**: Relationship memory informed
- **Stage 4 - Social Appropriateness**: Conversation norms
  - `calm_resolution`: For episode endings (after sustained positive)

**Implementation**: `/backend/services/emotion_engine.py` (enhanced CPM stages)

#### Layer 3: Emotion Generation (UNCHANGED)
Core CPM emotion generation with all scientific enhancements:

AICO's emotion simulation consists of five integrated components:

#### 1. Appraisal Engine
Processes conversation events through the 4-stage appraisal sequence:

```
Conversation Event → Relevance Check → Implication Check → Coping Check → Normative Check → Appraisal Output
```

**Multi-Level Processing**:
- **Fast Pattern Recognition**: Immediate emotional reactions to familiar situations
- **Deliberative Evaluation**: Thoughtful appraisal for complex or novel contexts
- **Context Integration**: User state, conversation history, relationship dynamics
- **Personality Filtering**: Appraisals constrained by AICO's personality profile

#### 2. Affect Derivation Model
Translates appraisal outputs into CPM's 5-component emotional states:

```python
class EmotionalState:
    def __init__(self):
        # CPM 5-Component Emotional State
        self.cognitive_component = AppraisalResult()    # Appraisal outcomes
        self.physiological_component = 0.5              # Bodily arousal [0,1]
        self.motivational_component = "approach"        # Action tendencies
        self.motor_component = MotorExpression()        # Facial/gesture patterns
        self.subjective_component = "confident"         # Conscious feeling
        
        # Processing metadata
        self.timestamp = time.now()
        self.confidence = 0.8                           # Appraisal certainty
        self.intensity = 0.7                            # Overall emotional intensity
```

**Data-Driven Mapping**:
- **Rule-Based (MVP)**: Predefined appraisal-to-emotion mappings
- **Learning-Enhanced**: Machine learning refinement of emotional appropriateness
- **Context-Sensitive**: Situation-specific emotional response patterns

#### 3. Mood & Cognitive States
Manages long-term emotional patterns and baselines:

**Mood Modeling**:
- **Baseline Tracking**: Persistent emotional tendencies across sessions
- **Relationship Evolution**: Mood changes based on user interaction history
- **Temporal Patterns**: Daily/weekly emotional rhythm recognition

**Cognitive Integration**:
- **Memory Influence**: Past emotional experiences shape current responses
- **Learning Adaptation**: Emotional patterns refined through interaction feedback
- **Goal Alignment**: Emotions support AICO's companion objectives

#### 4. Emotion Regulation
Ensures socially appropriate and ethically constrained emotional responses:

**Social Appropriateness**:
- **Context Checking**: Emotional responses suitable for current situation
- **Relationship Awareness**: Emotions appropriate for relationship phase/type
- **Cultural Sensitivity**: Emotional expressions adapted to user background

**Crisis Management**:
- **Automatic Regulation**: Rapid adjustment for extreme user emotional states
- **Emergency Protocols**: Specialized responses for crisis situations
- **Recovery Mechanisms**: Gradual return to normal emotional patterns

**Personality Consistency**:
- **Trait Constraints**: Emotions aligned with established personality
- **Behavioral Coherence**: Consistent emotional expression patterns
- **Character Maintenance**: Prevents emotional responses that break character

#### 5. Expression Synthesis
Coordinates multi-modal emotional expression using CPM 5-component mapping:

**Voice Synthesis Integration**:
- **Physiological Component** → Prosodic parameters (pitch, rhythm, volume, breathing)
- **Motor Component** → Vocal expression patterns and articulation
- **Subjective Component** → Emotional tone and vocal warmth
- **Motivational Component** → Speech urgency and directional emphasis

**Avatar Expression Control**:
- **Motor Component** → Direct facial expressions, micro-expressions, gesture patterns
- **Physiological Component** → Posture tension, eye dilation, breathing visualization
- **Motivational Component** → Approach/avoidance body language and spatial positioning
- **Subjective Component** → Overall expression authenticity and emotional presence

**Text Generation Context**:
- **Cognitive Component** → Appraisal context injection into LLM prompts
- **Motivational Component** → Response directness and conversational approach
- **Subjective Component** → Writing tone, word choice, emotional vocabulary
- **Motor Component** → Punctuation patterns and response structure energy

## Core Capabilities

### 1. Sophisticated Emotion Generation
- **Appraisal-Based Processing**: Emotions emerge from cognitive evaluation through 4-stage appraisal process
- **5-Component Emotional States**: Complete CPM implementation with cognitive, physiological, motivational, motor, and subjective components
- **Context-Aware Responses**: Situational appropriateness through relevance, implication, coping, and normative checks
- **Human-Like Dynamics**: Emotional patterns that mirror natural human emotional processes

### 2. Relationship-Aware Intelligence
- **Social Context Integration**: Emotions consider relationship phase, intimacy level, and social dynamics
- **Long-Term Memory**: Emotional experiences stored and influence future responses
- **Adaptive Personality**: Emotional tendencies refined while maintaining core character consistency
- **Boundary Awareness**: Emotionally appropriate responses for companion (not romantic) relationships

### 3. Crisis and Emergency Handling
- **Automatic Regulation**: Built-in emotion regulation for extreme user emotional states
- **Emergency Protocols**: Specialized emotional responses for crisis situations
- **Rapid Adaptation**: Fast emotional state changes when user needs immediate support
- **Threat Response Override**: Acute threats (job loss, existential concerns) trigger amygdala-like override:
  - 25% arousal amplification for high-stakes threats (configurable)
  - Inertia reduced to 30% to allow threat response to dominate emotional state
  - Based on LeDoux (1996) amygdala research and modern threat appraisal studies
- **Recovery Mechanisms**: Gradual return to normal emotional patterns after crisis resolution

### 4. Ethical and Social Appropriateness
- **Normative Checking**: Stage 4 appraisal ensures socially appropriate emotional responses
- **Cultural Sensitivity**: Emotional expressions adapted to user cultural background
- **Professional Boundaries**: Emotions maintain appropriate companion role and expectations
- **Harm Prevention**: Emotional responses designed to support user wellbeing

### 5. Cross-Modal Expression Coordination
- **Synchronized Expression**: Emotional state drives coordinated voice, avatar, and text responses
- **Real-Time Adaptation**: Dynamic emotional adjustment during ongoing conversations
- **Multi-Component Output**: Physiological, motor, behavioral, and subjective emotional aspects
- **Temporal Coherence**: Smooth emotional transitions that feel natural and believable

### 6. Continuous Learning and Improvement
- **Local Learning**: Emotional response refinement based on individual user interactions
- **Optional Cloud Enhancement**: Collective learning from anonymized interaction patterns (user consent)
- **Pattern Recognition**: Identification of successful emotional strategies across contexts
- **Model Updates**: Continuous improvement of emotional intelligence capabilities

## Implementation Overview

AICO's emotion simulation follows a **4-stage processing pipeline**:

```
Multimodal Input → Appraisal Engine → Affect Derivation → Emotion Regulation → Expression Synthesis → Coordinated Output
```

**Input Processing**: The system receives multimodal inputs including text/speech, visual cues (facial expressions, gestures), audio characteristics (voice tone, prosody), and contextual information (conversation history, relationship state, temporal context).

**Appraisal Processing**: Each input is evaluated through the 4-stage cognitive appraisal process to determine emotional relevance and appropriate response.

**Emotion Generation**: Appraisal results are translated into CPM's 5-component emotional states (cognitive, physiological, motivational, motor, subjective).

**Expression Coordination**: Emotional components are mapped to coordinated expression across voice synthesis, avatar animation, and text generation.

For detailed technical architecture and implementation specifics, see [`emotion-simulation-architecture.md`](./emotion-simulation-architecture.md).

## Component Integration

### Input Sources

The emotion simulation system receives inputs from multiple AICO components:

- Detected user emotional states (from Emotion Detection).
- Conversation context and relationship state.
- Personality state and preferences.
- Memory-derived hints and patterns.

### Output Destinations

- Voice & Audio System (prosody and emotional coloring).
- Avatar System (facial expressions, body language, gaze).
- ConversationEngine/LLM (text tone and approach).
- Memory/AMS (emotional experiences and outcomes).

## Success Metrics

See [`emotion-integration.md`](./emotion-integration.md) for system-level metrics related to believability, emotional intelligence, and long-term relationship development.

## Scientific References

### Core Theory
- **Scherer, K. R. (2001)**. Appraisal considered as a process of multilevel sequential checking. *Appraisal processes in emotion*, 92(120), 57.
- **Russell, J. A. (1980)**. A circumplex model of affect. *Journal of Personality and Social Psychology*, 39(6), 1161.
- **Kuppens, P., et al. (2010)**. Emotional inertia and psychological maladjustment. *Psychological Science*, 21(7), 984-991.
- **LeDoux, J. E. (1996)**. *The emotional brain: The mysterious underpinnings of emotional life*. Simon and Schuster.

### Modern Extensions (2024-2025)
- **Feng, J., et al. (2024)**. Emotionally Intelligent Task-oriented Dialogue Systems: Architecture, Representation, and Optimisation. *arXiv:2507.01594*
- **Van, T., et al. (2025)**. Multimodal Emotion Recognition in Conversations: A Survey of Methods, Trends, Challenges and Prospects. *arXiv:2505.20511v1*
- **Gross, J. J. (2015)**. Emotion regulation: Current status and future prospects. *Psychological Inquiry*, 26(1), 1-26.

### Threat and Arousal Research
- **Sander, D., Grafman, J., & Zalla, T. (2003)**. The human amygdala: An evolved system for relevance detection. *Reviews in the Neurosciences*, 14(4), 303-316.
- **Štolhoferová, I., et al. (2023)**. Human emotional evaluation of ancestral and modern threats: Fear, disgust, and anger. *Frontiers in Psychology*, 14, 1321053.
