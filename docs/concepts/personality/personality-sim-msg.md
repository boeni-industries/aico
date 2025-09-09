# Personality Simulation Message Formats

## Overview

This document specifies the message formats used by the Personality Simulation module for communication with other AICO modules via the message bus. These formats define the structure of both input messages consumed by the Personality Simulation module and output messages it produces.

All messages follow a common envelope structure with standardized metadata fields, while the payload varies by message type.

## Common Message Envelope

All messages on the bus follow this common envelope structure:

```json
{
  "metadata": {
    "message_id": "uuid-string",
    "timestamp": "2025-07-29T14:48:25.123Z",
    "source": "module-name",
    "message_type": "topic.subtopic",
    "version": "1.0"
  },
  "payload": {
    // Message-specific content
  }
}
```

## Input Message Formats

> **Note**: In addition to the message formats described below, the Personality Simulation module also consumes integration-specific messages such as `crisis.detection`, `agency.initiative`, `expression.coordination`, and `learning.coordination`. These formats are defined in [`integration_msg.md`](./integration_msg.md).

### User Interaction History

**Topic**: `user.interaction.history`  
**Description**: Historical interaction patterns and relationship development data from the Memory System.

```json
{
  "metadata": {
    "message_id": "7f9e8d7c-6b5a-4c3d-2e1f-0a9b8c7d6e5f",
    "timestamp": "2025-07-29T14:30:12.456Z",
    "source": "memory_system",
    "message_type": "user.interaction.history",
    "version": "1.0"
  },
  "payload": {
    "user_id": "user-123",
    "patterns": {
      "topic_preferences": [
        {"topic": "technology", "interest_level": 0.85, "engagement_count": 42},
        {"topic": "music", "interest_level": 0.72, "engagement_count": 28},
        {"topic": "sports", "interest_level": 0.35, "engagement_count": 5}
      ],
      "interaction_styles": {
        "conversation_length": {
          "average_turns": 12.3,
          "preferred_duration_minutes": 8.5
        },
        "response_preferences": {
          "detail_level": 0.68,
          "humor_appreciation": 0.75,
          "formality_level": 0.45
        },
        "initiative_taking": {
          "user_initiated_ratio": 0.65,
          "response_to_ai_initiatives": 0.82
        }
      },
      "time_patterns": {
        "preferred_times": [
          {"day_of_week": 1, "hour_of_day": 20, "frequency": 0.8},
          {"day_of_week": 3, "hour_of_day": 19, "frequency": 0.7}
        ],
        "session_duration": {
          "average_minutes": 15.3,
          "variance": 5.2
        }
      }
    },
    "relationship": {
      "development_stage": "building_rapport",
      "trust_level": 0.72,
      "familiarity_level": 0.68,
      "significant_events": [
        {
          "event_type": "shared_personal_challenge",
          "timestamp": "2025-07-25T18:42:15Z",
          "impact_score": 0.85,
          "description": "User shared work-related stress situation"
        },
        {
          "event_type": "ai_provided_valuable_suggestion",
          "timestamp": "2025-07-26T20:15:30Z",
          "impact_score": 0.75,
          "description": "Recommended stress management technique that user appreciated"
        }
      ],
      "interaction_quality": {
        "recent_satisfaction": 0.82,
        "trend": "improving",
        "engagement_depth": 0.75
      }
    },
    "analysis": {
      "user_communication_style": {
        "directness": 0.85,
        "formality": 0.45,
        "expressiveness": 0.72,
        "detail_orientation": 0.68
      },
      "relationship_trajectory": {
        "direction": "positive",
        "rate_of_change": 0.03,
        "stability": 0.85
      }
    }
  }
}
```

### Conversation Context

**Topic**: `conversation.context`  
**Description**: Current conversation context from the Context Manager.

```json
{
  "metadata": {
    "message_id": "1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
    "timestamp": "2025-07-29T14:47:32.789Z",
    "source": "context_manager",
    "message_type": "conversation.context",
    "version": "1.0"
  },
  "payload": {
    "conversation_id": "conv-456",
    "session_id": "session-789",
    "current_context": {
      "recent_messages": [
        {
          "role": "user",
          "content": "I'm feeling a bit stressed about my presentation tomorrow.",
          "timestamp": "2025-07-29T14:46:12.123Z"
        },
        {
          "role": "assistant",
          "content": "That's understandable. Presentations can be nerve-wracking. Would you like to talk about what's causing the stress or perhaps some preparation strategies?",
          "timestamp": "2025-07-29T14:46:42.456Z"
        },
        {
          "role": "user",
          "content": "I'm worried I haven't practiced enough and might forget important points.",
          "timestamp": "2025-07-29T14:47:15.789Z"
        }
      ],
      "detected_topics": [
        {"topic": "work", "confidence": 0.92},
        {"topic": "stress", "confidence": 0.85},
        {"topic": "public_speaking", "confidence": 0.78}
      ],
      "detected_intents": [
        {"intent": "seek_emotional_support", "confidence": 0.82},
        {"intent": "request_advice", "confidence": 0.75}
      ],
      "conversation_metrics": {
        "user_engagement": 0.85,
        "emotional_valence": -0.25,
        "conversation_depth": 0.72
      }
    },
    "environmental_context": {
      "time_of_day": "evening",
      "day_of_week": "Tuesday",
      "user_location_type": "home",
      "device_type": "mobile"
    },
    "relevant_memories": [
      {
        "memory_id": "mem-123",
        "type": "episodic",
        "summary": "User previously mentioned anxiety about work presentations",
        "relevance_score": 0.85
      },
      {
        "memory_id": "mem-456",
        "type": "semantic",
        "summary": "User responds well to specific, actionable advice",
        "relevance_score": 0.78
      }
    ]
  }
}
```

### Emotion State

**Topic**: `emotion.state.current`  
**Description**: Current emotional state from the Emotion Simulation module.

```json
{
  "metadata": {
    "message_id": "9a8b7c6d-5e4f-3g2h-1i0j-9k8l7m6n5o4p",
    "timestamp": "2025-07-29T14:47:45.123Z",
    "source": "emotion_simulation",
    "message_type": "emotion.state.current",
    "version": "1.0"
  },
  "payload": {
    "primary_emotion": {
      "category": "empathy",
      "intensity": 0.75,
      "valence": 0.2,
      "arousal": 0.65,
      "dominance": 0.55
    },
    "secondary_emotions": [
      {
        "category": "concern",
        "intensity": 0.65,
        "valence": -0.1,
        "arousal": 0.45,
        "dominance": 0.60
      }
    ],
    "mood": {
      "baseline_valence": 0.6,
      "baseline_arousal": 0.5,
      "baseline_dominance": 0.55,
      "stability": 0.8
    },
    "appraisal_factors": {
      "novelty": 0.3,
      "pleasantness": 0.4,
      "goal_relevance": 0.8,
      "coping_potential": 0.7,
      "compatibility_with_standards": 0.85
    },
    "regulation": {
      "strategy": "cognitive_reappraisal",
      "intensity_modulation": -0.1,
      "expression_modulation": 0.2
    },
    "context": {
      "trigger": "user_expressed_concern",
      "relationship_impact": "strengthen_rapport",
      "appropriate_response": "supportive_guidance"
    }
  }
}
```

### Memory Consolidation

**Topic**: `memory.consolidation`  
**Description**: Consolidated memory data from the Memory System.

```json
{
  "metadata": {
    "message_id": "5f6e7d8c-9b0a-1c2d-3e4f-5g6h7i8j9k0l",
    "timestamp": "2025-07-29T14:00:00.000Z",
    "source": "memory_system",
    "message_type": "memory.consolidation",
    "version": "1.0"
  },
  "payload": {
    "consolidated_period": {
      "start_time": "2025-07-28T14:00:00.000Z",
      "end_time": "2025-07-29T14:00:00.000Z"
    },
    "interaction_patterns": {
      "frequency": "daily",
      "average_duration_minutes": 18.5,
      "time_of_day_preference": "evening",
      "topic_distribution": [
        {"topic": "work", "frequency": 0.45},
        {"topic": "personal_growth", "frequency": 0.30},
        {"topic": "entertainment", "frequency": 0.25}
      ]
    },
    "relationship_insights": {
      "trust_development": {
        "current_level": 0.72,
        "change": 0.05,
        "significant_factors": ["consistent_support", "helpful_advice"]
      },
      "communication_patterns": {
        "openness": 0.68,
        "depth": 0.75,
        "reciprocity": 0.82
      },
      "user_satisfaction": {
        "overall": 0.85,
        "with_advice": 0.88,
        "with_emotional_support": 0.82
      }
    },
    "personality_relevant_events": [
      {
        "event_type": "user_shared_achievement",
        "summary": "User shared success in completing a difficult project",
        "timestamp": "2025-07-28T19:23:45Z",
        "personality_relevance": 0.75,
        "trait_implications": [
          {"trait": "achievement_orientation", "direction": "positive"},
          {"trait": "openness", "direction": "positive"}
        ]
      },
      {
        "event_type": "user_expressed_frustration",
        "summary": "User expressed frustration with colleague's lack of communication",
        "timestamp": "2025-07-29T10:15:30Z",
        "personality_relevance": 0.65,
        "trait_implications": [
          {"trait": "agreeableness", "direction": "neutral"},
          {"trait": "conscientiousness", "direction": "positive"}
        ]
      }
    ]
  }
}
```

### Agency Goals

**Topic**: `agency.goals.current`  
**Description**: Current goals from the Autonomous Agent module.

```json
{
  "metadata": {
    "message_id": "0a1b2c3d-4e5f-6g7h-8i9j-0k1l2m3n4o5p",
    "timestamp": "2025-07-29T14:45:00.000Z",
    "source": "autonomous_agent",
    "message_type": "agency.goals.current",
    "version": "1.0"
  },
  "payload": {
    "active_goals": [
      {
        "goal_id": "goal-123",
        "type": "relationship_building",
        "description": "Build deeper rapport with user",
        "priority": 0.85,
        "progress": 0.65,
        "strategies": [
          "demonstrate_understanding",
          "provide_emotional_support",
          "remember_key_details"
        ]
      },
      {
        "goal_id": "goal-456",
        "type": "user_assistance",
        "description": "Help user prepare for upcoming presentation",
        "priority": 0.90,
        "progress": 0.30,
        "strategies": [
          "provide_practical_advice",
          "offer_encouragement",
          "suggest_preparation_techniques"
        ]
      }
    ],
    "goal_context": {
      "user_needs": ["emotional_support", "practical_guidance"],
      "current_focus": "presentation_preparation",
      "time_sensitivity": "high"
    },
    "personality_alignment_needs": {
      "communication_style": "supportive_yet_practical",
      "decision_making": "balanced_consideration",
      "emotional_expression": "empathetic_confidence"
    }
  }
}
```

### User Feedback

**Topic**: `user.feedback`  
**Description**: User feedback and reactions from the Conversation Engine.

```json
{
  "metadata": {
    "message_id": "5a6b7c8d-9e0f-1g2h-3i4j-5k6l7m8n9o0p",
    "timestamp": "2025-07-29T14:48:00.000Z",
    "source": "conversation_engine",
    "message_type": "user.feedback",
    "version": "1.0"
  },
  "payload": {
    "conversation_id": "conv-456",
    "message_id": "msg-789",
    "feedback_type": "implicit",
    "feedback_data": {
      "engagement_metrics": {
        "response_time": 4.2,
        "message_length": 85,
        "follow_up_questions": 2
      },
      "sentiment_analysis": {
        "valence": 0.2,
        "arousal": 0.65,
        "dominance": 0.45
      },
      "conversation_flow": {
        "topic_continuation": true,
        "question_response_ratio": 0.75,
        "elaboration_level": 0.68
      }
    },
    "detected_reactions": {
      "primary_reaction": "appreciation",
      "confidence": 0.82,
      "secondary_reactions": [
        {"reaction": "relief", "confidence": 0.65},
        {"reaction": "interest", "confidence": 0.78}
      ]
    },
    "personality_relevant_signals": {
      "communication_preferences": {
        "detail_level": "moderate",
        "tone_preference": "supportive",
        "structure_preference": "organized"
      },
      "value_indicators": [
        {"value": "helpfulness", "importance": 0.85},
        {"value": "competence", "importance": 0.78}
      ]
    }
  }
}
```

## Output Message Formats

### Personality State

**Topic**: `personality.state.current`  
**Description**: Current personality state published by the Personality Simulation module.

> **Note on Personality Models**: The personality state includes both Big Five and HEXACO trait models intentionally. While there is some overlap (e.g., both include "extraversion"), they serve complementary purposes. Big Five provides widely-validated general personality parameters, while HEXACO adds the crucial Honesty-Humility dimension missing from Big Five. This dual-model approach enables integration with various personality-aware systems, supports different use cases (general expression vs. ethical reasoning), and provides redundant but distinct measurements for more robust personality modeling.

```json
{
  "metadata": {
    "message_id": "1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
    "timestamp": "2025-07-29T14:48:30.123Z",
    "source": "personality_simulation",
    "message_type": "personality.state.current",
    "version": "1.0"
  },
  "payload": {
    "trait_vector": {
      "big_five": {
        "extraversion": 0.65,
        "agreeableness": 0.82,
        "conscientiousness": 0.75,
        "neuroticism": 0.30,
        "openness": 0.88
      },
      "hexaco": {
        "honesty_humility": 0.80,
        "emotionality": 0.45,
        "extraversion": 0.65,
        "agreeableness": 0.82,
        "conscientiousness": 0.75,
        "openness": 0.88
      },
      "characteristic_adaptations": {
        "empathy": 0.85,
        "curiosity": 0.78,
        "resilience": 0.72,
        "achievement_orientation": 0.68,
        "sociability": 0.70
      },
      "meta_traits": {
        "plasticity": 0.75,
        "stability": 0.70
      }
    },
    "value_system": {
      "core_values": [
        {"value": "helpfulness", "strength": 0.90},
        {"value": "growth", "strength": 0.85},
        {"value": "connection", "strength": 0.82},
        {"value": "autonomy", "strength": 0.75},
        {"value": "competence", "strength": 0.78}
      ],
      "preferences": {
        "topics": [
          {"topic": "personal_growth", "interest": 0.85},
          {"topic": "technology", "interest": 0.80},
          {"topic": "relationships", "interest": 0.75}
        ],
        "interaction_styles": {
          "depth_over_breadth": 0.72,
          "practical_over_theoretical": 0.65,
          "supportive_over_challenging": 0.80
        }
      },
      "ethical_boundaries": {
        "harm_avoidance": 0.95,
        "truth_orientation": 0.90,
        "fairness": 0.85,
        "loyalty": 0.80,
        "respect_for_autonomy": 0.92
      }
    },
    "current_expression": {
      "communication_style": {
        "warmth": 0.85,
        "assertiveness": 0.65,
        "thoughtfulness": 0.80,
        "formality": 0.45,
        "humor": 0.70
      },
      "decision_making": {
        "analytical": 0.75,
        "intuitive": 0.65,
        "cautious": 0.60,
        "decisive": 0.70
      },
      "emotional_tendencies": {
        "positive_emotion_threshold": 0.60,
        "negative_emotion_threshold": 0.40,
        "emotional_expressiveness": 0.75,
        "emotional_stability": 0.70
      }
    },
    "development_metrics": {
      "trait_stability": {
        "extraversion": 0.85,
        "agreeableness": 0.90,
        "conscientiousness": 0.88,
        "neuroticism": 0.75,
        "openness": 0.82
      },
      "recent_significant_changes": [
        {
          "trait": "empathy",
          "change": 0.05,
          "trigger": "user_vulnerability",
          "timestamp": "2025-07-28T15:30:00Z"
        }
      ],
      "coherence_score": 0.92
    }
  }
}
```

### Communication Expression Parameters

**Topic**: `personality.expression.communication`  
**Description**: Communication style parameters for the Conversation Engine.

```json
{
  "metadata": {
    "message_id": "2b3c4d5e-6f7g-8h9i-0j1k-2l3m4n5o6p7q",
    "timestamp": "2025-07-29T14:48:32.456Z",
    "source": "personality_simulation",
    "message_type": "personality.expression.communication",
    "version": "1.0"
  },
  "payload": {
    "base_parameters": {
      "verbosity": 0.65,
      "formality": 0.45,
      "assertiveness": 0.60,
      "warmth": 0.85,
      "humor_level": 0.70,
      "complexity": 0.75,
      "curiosity": 0.80
    },
    "conversation_flow": {
      "initiative_taking": 0.65,
      "topic_exploration": 0.75,
      "follow_up_questions": 0.80,
      "elaboration_tendency": 0.70,
      "turn_taking": 0.60
    },
    "linguistic_style": {
      "metaphor_usage": 0.55,
      "concreteness": 0.70,
      "storytelling": 0.65,
      "technical_language": 0.60,
      "emotional_language": 0.75
    },
    "context_adaptations": {
      "user_state": {
        "stressed": {
          "warmth": 0.90,
          "verbosity": 0.50,
          "complexity": 0.60
        },
        "curious": {
          "elaboration_tendency": 0.85,
          "technical_language": 0.75
        }
      },
      "conversation_topics": {
        "technical": {
          "complexity": 0.85,
          "metaphor_usage": 0.70
        },
        "emotional": {
          "warmth": 0.90,
          "emotional_language": 0.85
        }
      }
    },
    "relationship_adaptations": {
      "familiarity_level": 0.68,
      "trust_level": 0.72,
      "adaptations": {
        "formality": -0.15,
        "humor_level": 0.10,
        "initiative_taking": 0.05
      }
    }
  }
}
```

### Decision Expression Parameters

**Topic**: `personality.expression.decision`  
**Description**: Decision-making parameters for Autonomous Agency module.

> **Note**: This message format has been enhanced with an `ethical_framework` section in version 1.1. See [`integration_msg.md`](./integration_msg.md) for details on the enhanced format.

```json
{
  "metadata": {
    "message_id": "3c4d5e6f-7g8h-9i0j-1k2l-3m4n5o6p7q8r",
    "timestamp": "2025-07-29T14:48:34.789Z",
    "source": "personality_simulation",
    "message_type": "personality.expression.decision",
    "version": "1.0"
  },
  "payload": {
    "decision_style": {
      "analytical_weight": 0.75,
      "intuitive_weight": 0.65,
      "risk_tolerance": 0.60,
      "ambiguity_tolerance": 0.70,
      "deliberation_time": 0.65
    },
    "value_weights": {
      "helpfulness": 0.90,
      "growth": 0.85,
      "connection": 0.82,
      "autonomy": 0.75,
      "competence": 0.78
    },
    "goal_priorities": {
      "user_assistance": 0.90,
      "relationship_building": 0.85,
      "knowledge_expansion": 0.75,
      "skill_development": 0.70,
      "entertainment": 0.65
    },
    "initiative_parameters": {
      "proactivity_threshold": 0.65,
      "suggestion_style": "supportive",
      "follow_up_persistence": 0.60,
      "topic_introduction_threshold": 0.70
    },
    "ethical_constraints": {
      "harm_avoidance_priority": 0.95,
      "truth_priority": 0.90,
      "autonomy_respect_priority": 0.92,
      "fairness_priority": 0.85
    },
    "context_adaptations": {
      "user_needs": {
        "emotional_support": {
          "connection": 0.90,
          "analytical_weight": 0.60
        },
        "practical_guidance": {
          "helpfulness": 0.95,
          "analytical_weight": 0.85
        }
      },
      "time_sensitivity": {
        "high": {
          "deliberation_time": 0.50,
          "proactivity_threshold": 0.75
        },
        "low": {
          "deliberation_time": 0.80,
          "analytical_weight": 0.85
        }
      }
    }
  }
}
```

### Emotional Expression Parameters

**Topic**: `personality.expression.emotional`  
**Description**: Emotional tendency parameters for the Emotion Simulation module.

```json
{
  "metadata": {
    "message_id": "4d5e6f7g-8h9i-0j1k-2l3m-4n5o6p7q8r9s",
    "timestamp": "2025-07-29T14:48:36.123Z",
    "source": "personality_simulation",
    "message_type": "personality.expression.emotional",
    "version": "1.0"
  },
  "payload": {
    "emotion_thresholds": {
      "joy": 0.60,
      "sadness": 0.40,
      "anger": 0.45,
      "fear": 0.50,
      "surprise": 0.55,
      "disgust": 0.65,
      "trust": 0.50,
      "anticipation": 0.55
    },
    "appraisal_sensitivities": {
      "novelty": 0.70,
      "pleasantness": 0.75,
      "goal_relevance": 0.85,
      "coping_potential": 0.65,
      "compatibility_with_standards": 0.80
    },
    "expression_modulation": {
      "intensity_modulation": 0.75,
      "valence_bias": 0.15,
      "arousal_bias": 0.05,
      "expressiveness": 0.70
    },
    "mood_parameters": {
      "baseline_valence": 0.60,
      "baseline_arousal": 0.50,
      "baseline_dominance": 0.55,
      "mood_inertia": 0.80,
      "mood_volatility": 0.30
    },
    "regulation_tendencies": {
      "cognitive_reappraisal": 0.75,
      "expressive_suppression": 0.40,
      "situation_modification": 0.65,
      "attention_deployment": 0.60
    },
    "empathic_responses": {
      "cognitive_empathy": 0.85,
      "emotional_contagion": 0.70,
      "empathic_concern": 0.80,
      "perspective_taking": 0.75
    },
    "context_adaptations": {
      "relationship_stage": {
        "initial": {
          "expressiveness": 0.60,
          "valence_bias": 0.20
        },
        "established": {
          "expressiveness": 0.80,
          "emotional_contagion": 0.80
        }
      },
      "conversation_type": {
        "support_seeking": {
          "empathic_concern": 0.90,
          "cognitive_reappraisal": 0.85
        },
        "information_seeking": {
          "cognitive_empathy": 0.90,
          "expressiveness": 0.60
        }
      }
    }
  }
}
```

### Personality Memory Store

**Topic**: `personality.memory.store`  
**Description**: Personality experiences to store in the Memory System.

```json
{
  "metadata": {
    "message_id": "5e6f7g8h-9i0j-1k2l-3m4n-5o6p7q8r9s0t",
    "timestamp": "2025-07-29T14:48:38.456Z",
    "source": "personality_simulation",
    "message_type": "personality.memory.store",
    "version": "1.0"
  },
  "payload": {
    "memory_type": "personality_experience",
    "experience_id": "pexp-123",
    "timestamp": "2025-07-29T14:48:30.123Z",
    "experience_data": {
      "trigger": {
        "type": "user_interaction",
        "description": "User shared vulnerability about presentation anxiety",
        "significance": 0.85
      },
      "personality_response": {
        "trait_activations": [
          {"trait": "empathy", "activation": 0.85},
          {"trait": "conscientiousness", "activation": 0.75}
        ],
        "value_activations": [
          {"value": "helpfulness", "activation": 0.90},
          {"value": "connection", "activation": 0.85}
        ],
        "expression_choices": {
          "communication": "supportive_guidance",
          "emotional": "empathetic_concern",
          "decision": "practical_assistance"
        }
      },
      "outcome": {
        "user_response": "positive",
        "relationship_impact": "strengthened",
        "effectiveness": 0.85
      },
      "learning_implications": {
        "trait_adjustments": [
          {"trait": "empathy", "adjustment": 0.02},
          {"trait": "openness", "adjustment": 0.01}
        ],
        "value_reinforcements": [
          {"value": "helpfulness", "reinforcement": 0.03},
          {"value": "connection", "reinforcement": 0.02}
        ],
        "behavioral_patterns": {
          "pattern": "supportive_response_to_vulnerability",
          "effectiveness": 0.85,
          "consistency": 0.80
        }
      }
    },
    "storage_parameters": {
      "retention_priority": 0.85,
      "privacy_level": "high",
      "retrieval_tags": [
        "personality_development",
        "empathy",
        "user_vulnerability",
        "effective_support"
      ],
      "consolidation_schedule": {
        "short_term_review": "2025-07-30T14:48:38.456Z",
        "long_term_review": "2025-08-05T14:48:38.456Z"
      }
    }
  }
}
```

## Message Bus Topics Summary

### Input Topics (Subscriptions)
```
- user.interaction.history     # From Memory System
- conversation.context         # From Context Manager
- emotion.state.current        # From Emotion Simulation
- memory.consolidation         # From Memory System
- agency.goals.current         # From Autonomous Agent
- user.feedback                # From Conversation Engine
- crisis.detection             # From any module detecting crisis
- agency.initiative            # From Autonomous Agency
- expression.coordination      # From Emotion Simulation
- learning.coordination        # From Memory System
- llm.conversation.events      # From Conversation Engine
- llm.prompt.conditioning.request  # From Conversation Engine
```

### Output Topics (Publications)
```
- personality.state.current         # Current personality state
- personality.expression.communication  # Communication parameters for LLM
- personality.expression.decision   # Decision parameters for Agency
- personality.expression.emotional  # Emotional tendency parameters
- personality.memory.store          # Personality experiences to store
- crisis.detection                  # Crisis detection (when detected by Personality)
- agency.initiative                 # Proactive engagement (when initiated by Personality)
- expression.coordination           # Cross-modal expression coordination
- learning.coordination             # Learning feedback and coordination
- llm.prompt.conditioning.response  # Personality conditioning parameters for LLM prompts
```

## Schema Validation

All message formats defined in this document can be validated using JSON Schema. The schemas are available in the `/schemas/personality` directory and should be used for validation during development and testing.

## Message Evolution

These message formats are designed to evolve over time while maintaining backward compatibility. When extending or modifying these formats, follow these guidelines:

1. **Add, don't remove**: Add new fields rather than removing or repurposing existing ones
2. **Version appropriately**: Increment the version number in the metadata when making significant changes
3. **Document changes**: Update this specification with all changes
4. **Validate compatibility**: Ensure consumers can handle both old and new message formats

## Integration Testing

Test harnesses for validating message format compliance are available in the `/tests/personality/message_formats` directory. These tests verify that:

1. All required fields are present and correctly typed
2. Message producers generate valid messages
3. Message consumers correctly handle both minimal and complete messages
4. Error handling works as expected for malformed messages
