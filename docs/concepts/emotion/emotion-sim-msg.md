# Emotion Simulation Message Formats

## Overview

This document defines the message schemas used by the Emotion Simulation module for integration with AICO's message bus system. These are **illustrative JSON structures** that demonstrate the expected data formats and field types for system integration.

> **Note**: These message formats are examples to illustrate the data structure and field types. Actual implementations may vary based on specific requirements and system constraints.

## Input Message Formats

> **Note**: In addition to the message formats described below, the Emotion Simulation module also consumes integration-specific messages such as `crisis/detection`, `agency/initiative`, `expression/coordination`, and `learning/coordination`. These formats are defined in integration documentation.

### `user/emotion/detected`

Emotional state information detected from user inputs across multiple modalities.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "emotion_recognition",
  "emotion": {
    "primary": "frustrated",
    "confidence": 0.85,
    "secondary": ["tired", "overwhelmed"],
    "valence": -0.6,
    "arousal": 0.7,
    "dominance": 0.3
  },
  "modalities": {
    "facial": ["furrowed_brow", "tight_lips"],
    "voice": ["elevated_pitch", "faster_speech"],
    "text": ["negative_sentiment", "complaint_indicators"]
  }
}
```

**Field Descriptions:**
- `emotion.primary`: Primary detected emotion (string)
- `emotion.confidence`: Detection confidence level (0.0-1.0)
- `emotion.secondary`: Additional detected emotions (array of strings)
- `emotion.valence`: Pleasure/displeasure dimension (-1.0 to 1.0)
- `emotion.arousal`: Activation/energy level (0.0-1.0)
- `emotion.dominance`: Control/power dimension (0.0-1.0)
- `modalities.*`: Indicators from different detection channels

### `conversation.message`

Current conversation message with analysis metadata.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "conversation_engine",
  "message": {
    "text": "I'm having a really tough day at work",
    "type": "user_input",
    "thread_id": "conv_12345",
    "turn_number": 15
  },
  "analysis": {
    "intent": "emotional_sharing",
    "urgency": "medium",
    "requires_response": true
  }
}
```

**Field Descriptions:**
- `message.text`: Actual message content (string)
- `message.type`: Message type (user_input, system_response, etc.)
- `message.thread_id`: Conversation thread identifier
- `message.turn_number`: Sequential turn number in conversation
- `analysis.intent`: Detected user intent (string)
- `analysis.urgency`: Message urgency level (low, medium, high)
- `analysis.requires_response`: Whether response is expected (boolean)

### `conversation.context`

Broader conversation context and relationship state information.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "context_manager",
  "context": {
    "current_topic": "work_stress",
    "conversation_phase": "problem_sharing",
    "session_duration_minutes": 15,
    "relationship_phase": "established_trust",
    "time_context": "evening_after_work",
    "crisis_indicators": false
  },
  "recent_history": {
    "last_5_topics": ["weekend_plans", "work_project", "family_call", "work_stress"],
    "emotional_trajectory": ["neutral", "positive", "neutral", "negative"]
  }
}
```

**Field Descriptions:**
- `context.current_topic`: Current conversation topic (string)
- `context.conversation_phase`: Phase of current conversation
- `context.session_duration_minutes`: Length of current session
- `context.relationship_phase`: Current relationship development stage
- `context.time_context`: Temporal/situational context
- `context.crisis_indicators`: Whether crisis situation detected (boolean)
- `recent_history.*`: Historical context for pattern recognition

### `personality.state`

Current personality configuration and mood state.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "personality_engine",
  "traits": {
    "extraversion": 0.6,
    "agreeableness": 0.8,
    "conscientiousness": 0.7,
    "neuroticism": 0.3,
    "openness": 0.9
  },
  "interaction_style": {
    "primary": "supportive_advisor",
    "communication_preference": "warm_direct",
    "emotional_expression_level": 0.7
  },
  "current_mood": {
    "baseline_valence": 0.2,
    "energy_level": 0.6,
    "social_engagement": 0.8
  }
}
```

**Field Descriptions:**
- `traits.*`: Big Five personality trait values (0.0-1.0)
- `interaction_style.primary`: Primary interaction approach
- `interaction_style.communication_preference`: Preferred communication style
- `interaction_style.emotional_expression_level`: Expression intensity (0.0-1.0)
- `current_mood.*`: Current mood state parameters

### `memory.relevant`

Relevant memory retrieval results for emotional context.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "memory_system",
  "query_context": {
    "user_emotional_state": "frustrated",
    "conversation_topic": "work_stress",
    "relationship_phase": "established_trust"
  },
  "relevant_memories": [
    {
      "memory_id": "mem_12345",
      "similarity_score": 0.89,
      "memory_type": "emotional_interaction",
      "context": "user_work_stress_previous",
      "successful_response": "gentle_encouragement_with_practical_advice",
      "outcome": "positive_user_feedback"
    },
    {
      "memory_id": "mem_67890",
      "similarity_score": 0.76,
      "memory_type": "relationship_pattern",
      "context": "user_prefers_validation_before_advice",
      "interaction_style": "listen_first_then_suggest",
      "effectiveness": "high"
    }
  ],
  "emotional_patterns": {
    "user_stress_triggers": ["work_deadlines", "team_conflicts"],
    "effective_support_styles": ["empathetic_listening", "practical_suggestions"],
    "relationship_preferences": ["gentle_approach", "respect_boundaries"]
  }
}
```

**Field Descriptions:**
- `query_context.*`: Context used for memory retrieval
- `relevant_memories[]`: Array of relevant past interactions
- `relevant_memories[].similarity_score`: Relevance score (0.0-1.0)
- `relevant_memories[].memory_type`: Type of memory (emotional_interaction, relationship_pattern, etc.)
- `emotional_patterns.*`: Learned patterns about user emotional responses

### `voice.analysis`

Voice analysis results providing emotional and prosodic information.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "voice_audio_system",
  "prosodic_features": {
    "pitch_mean": 180.5,
    "pitch_variance": 25.3,
    "speech_rate": 4.2,
    "volume_level": 0.7,
    "pause_frequency": 0.3
  },
  "emotional_indicators": {
    "stress_level": 0.8,
    "fatigue_indicators": 0.6,
    "confidence_level": 0.3,
    "emotional_stability": 0.4
  },
  "speech_quality": {
    "clarity": 0.9,
    "fluency": 0.7,
    "hesitation_markers": ["um", "uh", "like"],
    "speech_disruptions": 2
  },
  "contextual_analysis": {
    "urgency_detected": false,
    "question_intonation": false,
    "emotional_intensity": 0.7,
    "conversational_engagement": 0.8
  }
}
```

**Field Descriptions:**
- `prosodic_features.*`: Basic voice characteristics (pitch in Hz, rate in words/sec)
- `emotional_indicators.*`: Emotional state indicators (0.0-1.0)
- `speech_quality.*`: Speech production quality metrics
- `contextual_analysis.*`: Higher-level speech context analysis

## Output Message Formats

### `emotion.state.current`

Current emotional state generated by the emotion simulation system.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "emotion_simulation",
  "emotional_state": {
    "cognitive": {
      "appraisal_relevance": 0.9,
      "goal_impact": "supportive_opportunity",
      "control_assessment": "high_capability",
      "social_appropriateness": "empathetic_response"
    },
    "physiological": {
      "arousal_level": 0.7,
      "energy_state": "focused_calm"
    },
    "motivational": {
      "action_tendency": "provide_emotional_support",
      "approach_style": "gentle_but_confident"
    },
    "motor": {
      "expression_intensity": 0.6,
      "gesture_style": "reassuring_open",
      "posture_state": "attentive_forward_lean"
    },
    "subjective": {
      "feeling_state": "concerned_but_caring",
      "emotional_label": "empathetic_determination"
    }
  },
  "regulation": {
    "applied": true,
    "adjustments": ["reduced_intensity_for_user_state", "increased_warmth"]
  }
}
```

**Field Descriptions:**
- `emotional_state.cognitive.*`: Cognitive appraisal components
- `emotional_state.physiological.*`: Physiological arousal and energy
- `emotional_state.motivational.*`: Action tendencies and approach style
- `emotional_state.motor.*`: Physical expression parameters
- `emotional_state.subjective.*`: Conscious feeling state
- `regulation.applied`: Whether emotion regulation was applied (boolean)
- `regulation.adjustments`: List of regulation adjustments made

### `emotion.expression.voice`

Voice synthesis parameters derived from emotional state.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "emotion_simulation",
  "voice_parameters": {
    "prosody": {
      "pitch_base": 0.4,
      "pitch_variation": 0.3,
      "speech_rate": 0.6,
      "volume_level": 0.5
    },
    "emotional_coloring": {
      "warmth": 0.8,
      "concern_level": 0.6,
      "confidence": 0.7,
      "urgency": 0.2
    },
    "articulation": {
      "clarity": 0.9,
      "breath_pattern": "calm_steady",
      "pause_style": "thoughtful_supportive"
    }
  }
}
```

**Field Descriptions:**
- `voice_parameters.prosody.*`: Basic prosodic parameters (0.0-1.0)
- `voice_parameters.emotional_coloring.*`: Emotional tone parameters (0.0-1.0)
- `voice_parameters.articulation.*`: Speech articulation characteristics

### `emotion.expression.avatar`

Avatar animation parameters for visual emotional expression.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "emotion_simulation",
  "avatar_parameters": {
    "facial_expression": {
      "primary": "concerned_but_confident",
      "eyebrow_position": 0.3,
      "eye_openness": 0.8,
      "mouth_shape": "gentle_serious",
      "micro_expressions": ["slight_head_tilt", "soft_eye_contact"]
    },
    "body_language": {
      "posture": "attentive_forward_lean",
      "hand_position": "open_reassuring",
      "gesture_style": "minimal_supportive",
      "overall_tension": 0.4
    },
    "gaze_behavior": {
      "eye_contact_level": 0.8,
      "gaze_direction": "direct_caring",
      "blink_pattern": "natural_attentive"
    }
  }
}
```

**Field Descriptions:**
- `avatar_parameters.facial_expression.*`: Facial animation parameters
- `avatar_parameters.body_language.*`: Body posture and gesture parameters
- `avatar_parameters.gaze_behavior.*`: Eye movement and attention parameters

### `emotion.expression.text`

Text generation context and emotional guidance for LLM.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "emotion_simulation",
  "text_context": {
    "emotional_tone": "supportive_understanding",
    "response_approach": "validate_then_support",
    "communication_style": {
      "directness": 0.6,
      "warmth": 0.8,
      "formality": 0.3,
      "energy": 0.5
    },
    "content_guidance": {
      "primary_intent": "emotional_validation",
      "secondary_intent": "practical_support_offer",
      "avoid_patterns": ["dismissive_language", "overly_cheerful_tone"],
      "emphasize_patterns": ["acknowledgment", "understanding", "availability"]
    }
  }
}
```

**Field Descriptions:**
- `text_context.emotional_tone`: Overall emotional tone for response
- `text_context.response_approach`: Strategic approach to response
- `text_context.communication_style.*`: Communication style parameters (0.0-1.0)
- `text_context.content_guidance.*`: Content generation guidance

### `emotion.memory.store`

Emotional experience data for storage and learning.

```json
{
  "timestamp": "2025-07-29T15:34:48Z",
  "source": "emotion_simulation",
  "experience": {
    "situation": {
      "user_emotional_state": "frustrated_about_work",
      "conversation_context": "evening_stress_sharing",
      "relationship_phase": "established_trust"
    },
    "aico_response": {
      "emotional_state": "empathetic_determination",
      "approach_taken": "validate_then_support",
      "expression_coordination": "gentle_reassuring"
    },
    "outcome_tracking": {
      "user_feedback": null,
      "effectiveness_score": null,
      "learning_value": "high"
    }
  }
}
```

**Field Descriptions:**
- `experience.situation.*`: Situational context of the emotional interaction
- `experience.aico_response.*`: AICO's emotional response and approach
- `experience.outcome_tracking.*`: Tracking data for learning and improvement

## Message Bus Topics Summary

### Input Topics (Subscriptions)
- `user.emotion.detected` - User emotional state detection
- `conversation.message` - Current conversation messages
- `conversation.context` - Conversation and relationship context
- `personality.state` - Personality configuration and mood
- `memory.relevant` - Relevant memory retrieval results
- `voice.analysis` - Voice analysis results
- `crisis/detection` - Crisis detection and coordination
- `agency/initiative` - Proactive engagement coordination
- `expression/coordination` - Cross-modal expression synchronization
- `learning/coordination` - Shared learning between modules
- `llm/conversation/events` - Conversation events and feedback from LLM
- `llm/prompt/conditioning/request` - Requests for emotional conditioning parameters

### Output Topics (Publications)
- `emotion.state.current` - Current AICO emotional state
- `emotion.expression.voice` - Voice synthesis parameters
- `emotion.expression.avatar` - Avatar animation parameters
- `emotion.expression.text` - Text generation context
- `emotion.memory.store` - Emotional experiences for storage
- `crisis/detection` - Crisis detection (when detected by Emotion Simulation)
- `expression/coordination` - Cross-modal expression coordination
- `learning/coordination` - Learning feedback and coordination
- `llm/prompt/conditioning/response` - Emotional conditioning parameters for LLM prompts

## 2025 Messaging Considerations

To keep the messaging layer aligned with AICO's broader architecture and current best practices:

- **Compact, modality-agnostic payloads**: Outputs such as `emotion.state.current`, `emotion.expression.voice`, `emotion.expression.avatar`, and `emotion.expression.text` should favor small, abstract parameters (e.g., warmth, energy, engagement, focus) that downstream systems translate into concrete behavior.
- **Emotion–memory linkage**: Messages like `emotion.memory.store` should include identifiers (conversation_id, message_id, user_id) and concise emotional summaries so the memory system and AMS can correlate emotional strategies with outcomes.
- **Appraisal assistance from LLMs**: When `llm/prompt/conditioning/request` / `response` are used, the Emotion Simulation module treats LLM-derived appraisal information as advisory input, combined with rule-based appraisal and stored user/relationship context.
- **Safety and evaluation hooks**: Crisis-related and regulation-related fields should be designed so that safety filters and evaluation tools can reconstruct why a particular emotional strategy was chosen and how it performed over time.

## Implementation Notes

### Data Types
- **Timestamps**: ISO 8601 format (UTC)
- **Confidence/Probability Values**: Float (0.0-1.0)
- **Emotional Labels**: String identifiers (standardized vocabulary)
- **Arrays**: JSON arrays for multiple values
- **Nested Objects**: Hierarchical data organization

### Message Validation
- All messages should include `timestamp` and `source` fields
- Numeric values should be validated for expected ranges
- String fields should use standardized vocabularies where applicable
- Optional fields may be omitted but should not be null

### Performance Considerations
- Message sizes should be kept minimal for low-latency processing
- Complex nested structures should be avoided in high-frequency messages
- Binary data should be avoided in favor of parameter references
