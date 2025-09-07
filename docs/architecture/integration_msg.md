# Integration Message Formats

## Overview

This document defines additional message formats that facilitate enhanced integration between AICO's core modules, particularly focusing on Personality Simulation, Emotion Simulation, LLM-driven Conversation Engine, and Autonomous Agency. These message formats address specific integration requirements for crisis handling, ethical decision-making, proactive agency coordination, cross-modal expression, and shared learning.

All messages follow the common envelope structure with standardized metadata fields as defined in other message format documents.

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

## Crisis Handling Message Format

### Crisis Detection

**Topic**: `crisis.detection`  
**Description**: Alert message indicating detection of a potential crisis situation requiring coordinated response across modules.

```json
{
  "metadata": {
    "message_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
    "timestamp": "2025-07-29T15:42:18.123Z",
    "source": "emotion_recognition", // Could be any module that detects crisis
    "message_type": "crisis.detection",
    "version": "1.0"
  },
  "payload": {
    "crisis_id": "crisis-789",
    "severity": 0.85, // 0.0-1.0 scale
    "confidence": 0.92,
    "crisis_type": "emotional_distress", // emotional_distress, safety_concern, ethical_boundary, etc.
    "detected_by": {
      "module": "emotion_recognition",
      "detection_method": "multimodal_analysis",
      "detection_signals": [
        {"signal": "facial_expression", "value": "extreme_distress", "confidence": 0.90},
        {"signal": "voice_tone", "value": "agitated", "confidence": 0.85},
        {"signal": "text_content", "value": "self_harm_indicators", "confidence": 0.95}
      ]
    },
    "context": {
      "conversation_id": "conv-456",
      "user_id": "user-123",
      "recent_message": "I don't think I can handle this anymore...",
      "conversation_topic": "personal_crisis",
      "relationship_phase": "established_trust"
    },
    "response_guidance": {
      "priority": "immediate", // immediate, high, moderate
      "protocol": "emotional_support_protocol_3", // Reference to predefined crisis protocols
      "required_actions": [
        "suspend_normal_conversation_flow",
        "activate_supportive_response_mode",
        "prepare_external_resources"
      ],
      "module_specific_instructions": {
        "personality_simulation": {
          "trait_emphasis": ["empathy", "emotional_stability"],
          "value_emphasis": ["safety", "support"]
        },
        "emotion_simulation": {
          "target_emotional_state": "calm_supportive",
          "expression_intensity": 0.7
        },
        "chat_engine": {
          "response_type": "validation_and_support",
          "avoid_patterns": ["dismissive_language", "toxic_positivity"]
        },
        "autonomous_agency": {
          "goal_priority_override": "user_wellbeing",
          "proactive_actions": ["offer_resources", "check_in_followup"]
        }
      }
    },
    "escalation_path": {
      "internal_escalation": true,
      "external_escalation": false,
      "external_resources": [
        {
          "resource_type": "crisis_hotline",
          "name": "Crisis Support Service",
          "contact_info": "1-800-XXX-XXXX",
          "presentation_guidance": "gentle_suggestion"
        }
      ]
    },
    "timeout": {
      "response_deadline_ms": 500, // Maximum response time
      "monitoring_duration_minutes": 30 // How long to maintain crisis awareness
    }
  }
}
```

**Field Descriptions:**
- `severity`: Crisis severity on a 0.0-1.0 scale
- `confidence`: Detection confidence level
- `crisis_type`: Type of crisis detected
- `detected_by`: Information about the detecting module and signals
- `context`: Current conversation context relevant to the crisis
- `response_guidance`: Instructions for coordinated module responses
- `escalation_path`: Information about escalation options
- `timeout`: Timing requirements for crisis response

## Proactive Agency Message Format

### Agency Initiative

**Topic**: `agency.initiative`  
**Description**: Signal for proactive engagement initiated by the Autonomous Agency module.

```json
{
  "metadata": {
    "message_id": "b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7",
    "timestamp": "2025-07-29T16:30:45.789Z",
    "source": "autonomous_agency",
    "message_type": "agency.initiative",
    "version": "1.0"
  },
  "payload": {
    "initiative_id": "init-456",
    "initiative_type": "conversation_starter", // conversation_starter, check_in, suggestion, reminder, etc.
    "priority": 0.75, // 0.0-1.0 scale
    "timing": {
      "optimal_execution_time": "2025-07-29T16:35:00Z", // When this should ideally happen
      "expiration_time": "2025-07-29T17:30:00Z", // When this initiative becomes irrelevant
      "flexibility": 0.6 // How flexible the timing is (0.0-1.0)
    },
    "context": {
      "user_id": "user-123",
      "user_state": {
        "estimated_availability": 0.85,
        "estimated_receptivity": 0.80,
        "current_activity": "idle_period_after_work"
      },
      "relationship_context": {
        "phase": "established_trust",
        "recent_interaction_quality": 0.82,
        "last_interaction_time": "2025-07-29T12:15:30Z"
      },
      "environmental_context": {
        "time_of_day": "evening",
        "day_of_week": "Tuesday",
        "user_location_type": "home"
      }
    },
    "initiative_content": {
      "goal": "strengthen_relationship",
      "topic": "follow_up_on_work_presentation",
      "approach": "curious_and_supportive",
      "conversation_starter": "I was thinking about your presentation today. How did it go?",
      "fallback_options": [
        "I'd love to hear how your day went.",
        "I remember you mentioned having a presentation today."
      ]
    },
    "coordination_parameters": {
      "personality_expression": {
        "trait_emphasis": ["curiosity", "empathy"],
        "communication_style": "warm_interested"
      },
      "emotional_expression": {
        "target_emotion": "gentle_interest",
        "expression_intensity": 0.65
      },
      "execution_parameters": {
        "interruption_threshold": 0.8, // How important user's current activity must be to defer
        "persistence": 0.6, // How persistent this initiative should be
        "adaptability": 0.7 // How easily this can adapt to user responses
      }
    },
    "success_metrics": {
      "engagement_goal": "meaningful_conversation",
      "minimum_success_criteria": "user_responds_positively",
      "optimal_outcome": "user_shares_detailed_update"
    }
  }
}
```

**Field Descriptions:**
- `initiative_type`: Type of proactive engagement
- `priority`: Relative importance of this initiative
- `timing`: When this initiative should be executed
- `context`: Contextual information about user and environment
- `initiative_content`: The actual content of the initiative
- `coordination_parameters`: How other modules should coordinate
- `success_metrics`: How to measure initiative success

## Cross-Modal Expression Coordination

### Expression Coordination

**Topic**: `expression.coordination`  
**Description**: Coordination parameters for synchronizing emotional and personality expression across multiple modalities.

```json
{
  "metadata": {
    "message_id": "c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8",
    "timestamp": "2025-07-29T14:52:36.123Z",
    "source": "emotion_simulation", // Primary source, but could be personality_simulation
    "message_type": "expression.coordination",
    "version": "1.0"
  },
  "payload": {
    "coordination_id": "coord-789",
    "expression_type": "emotional_response", // emotional_response, personality_expression, crisis_response
    "priority": 0.8, // 0.0-1.0 scale
    "synchronization": {
      "primary_modality": "voice", // Which modality leads the expression
      "timing_parameters": {
        "start_time_ms": 0, // Relative to message receipt
        "duration_ms": 3500,
        "fade_in_ms": 250,
        "fade_out_ms": 500
      },
      "transition_parameters": {
        "from_emotional_state": "neutral",
        "to_emotional_state": "empathetic_concern",
        "transition_curve": "natural_sigmoid", // natural_sigmoid, linear, exponential
        "transition_speed": 0.7 // 0.0-1.0 scale
      }
    },
    "modality_expressions": {
      "voice": {
        "start_offset_ms": 0,
        "expression_parameters": {
          "prosody": {
            "pitch_variation": 0.6,
            "speech_rate": 0.5,
            "volume_modulation": 0.7
          },
          "emotional_coloring": {
            "warmth": 0.8,
            "concern": 0.7,
            "confidence": 0.6
          }
        }
      },
      "avatar": {
        "start_offset_ms": 250, // Slight delay after voice
        "expression_parameters": {
          "facial": {
            "eyebrow_position": 0.3,
            "eye_openness": 0.7,
            "mouth_shape": "slight_smile"
          },
          "body_language": {
            "posture": "attentive_forward_lean",
            "gesture_frequency": 0.4,
            "gesture_amplitude": 0.5
          }
        }
      },
      "text": {
        "start_offset_ms": 500, // Text generation starts after voice and avatar
        "expression_parameters": {
          "tone": "supportive_understanding",
          "formality": 0.4,
          "expressiveness": 0.7,
          "directness": 0.6
        }
      }
    },
    "coherence_constraints": {
      "emotional_consistency": 0.9, // How consistent emotion should be across modalities
      "personality_consistency": 0.9, // How consistent personality should be across modalities
      "intensity_balance": 0.8 // Balance of expression intensity across modalities
    },
    "adaptive_parameters": {
      "user_feedback_sensitivity": 0.8, // How responsive to user feedback
      "context_adaptation_rate": 0.7, // How quickly to adapt to changing context
      "fallback_expression": "neutral_attentive" // Default if coordination fails
    }
  }
}
```

**Field Descriptions:**
- `expression_type`: Type of expression being coordinated
- `priority`: Relative importance of this coordination
- `synchronization`: Timing and transition parameters
- `modality_expressions`: Expression parameters for each modality
- `coherence_constraints`: Requirements for cross-modal consistency
- `adaptive_parameters`: How expression adapts to feedback and context

## Shared Learning Coordination

### Learning Coordination

**Topic**: `learning.coordination`  
**Description**: Coordination of learning and adaptation across multiple modules.

```json
{
  "metadata": {
    "message_id": "d4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9",
    "timestamp": "2025-07-29T23:45:12.456Z",
    "source": "memory_system",
    "message_type": "learning.coordination",
    "version": "1.0"
  },
  "payload": {
    "learning_event_id": "learn-123",
    "learning_type": "interaction_feedback", // interaction_feedback, pattern_recognition, explicit_feedback
    "priority": 0.75,
    "learning_source": {
      "event_type": "conversation_completion",
      "event_id": "conv-456",
      "timestamp": "2025-07-29T23:30:05.123Z",
      "data_source": "user_feedback"
    },
    "learning_data": {
      "user_feedback": {
        "explicit": {
          "rating": 4.5, // 1-5 scale
          "comments": "Really helpful advice, and I appreciated the empathy"
        },
        "implicit": {
          "engagement_level": 0.85,
          "emotional_response": "positive",
          "continuation_behavior": "extended_conversation"
        }
      },
      "interaction_metrics": {
        "conversation_duration_minutes": 12.5,
        "user_message_count": 15,
        "ai_message_count": 14,
        "topic_depth": 0.8,
        "emotional_trajectory": "negative_to_positive"
      },
      "effectiveness_analysis": {
        "goal_achievement": 0.9,
        "user_satisfaction": 0.85,
        "relationship_impact": 0.8
      }
    },
    "module_learning_directives": {
      "personality_simulation": {
        "trait_adjustments": [
          {"trait": "empathy", "direction": "strengthen", "magnitude": 0.02},
          {"trait": "openness", "direction": "maintain", "magnitude": 0.0}
        ],
        "value_reinforcements": [
          {"value": "helpfulness", "direction": "strengthen", "magnitude": 0.03}
        ],
        "expression_refinements": {
          "communication_style": {
            "warmth": "maintain",
            "directness": "slightly_increase"
          }
        }
      },
      "emotion_simulation": {
        "response_adjustments": {
          "empathetic_concern": "strengthen",
          "emotional_expressiveness": "maintain"
        },
        "regulation_adjustments": {
          "regulation_strength": "slightly_decrease"
        }
      },
      "autonomous_agency": {
        "goal_adjustments": {
          "user_support": "prioritize",
          "information_provision": "maintain"
        },
        "initiative_adjustments": {
          "check_in_frequency": "slightly_increase",
          "suggestion_specificity": "increase"
        }
      },
      "chat_engine": {
        "response_style_adjustments": {
          "validation_frequency": "increase",
          "question_frequency": "maintain",
          "suggestion_specificity": "increase"
        }
      }
    },
    "coordination_requirements": {
      "learning_sequence": [
        {"module": "memory_system", "action": "consolidate", "order": 1},
        {"module": "personality_simulation", "action": "adapt", "order": 2},
        {"module": "emotion_simulation", "action": "adjust", "order": 3},
        {"module": "autonomous_agency", "action": "update", "order": 4}
      ],
      "consistency_constraints": {
        "personality_emotion_alignment": 0.9,
        "agency_personality_alignment": 0.85
      },
      "verification_requirements": {
        "verify_after_changes": true,
        "consistency_threshold": 0.8
      }
    }
  }
}
```

**Field Descriptions:**
- `learning_type`: Type of learning event
- `priority`: Relative importance of this learning event
- `learning_source`: Source of the learning data
- `learning_data`: The actual learning data
- `module_learning_directives`: Module-specific learning instructions
- `coordination_requirements`: How learning should be coordinated

## Enhanced Ethical Decision Framework

### Enhanced Decision Expression Parameters

This section describes enhancements to the existing `personality.expression.decision` message format to support explicit ethical reasoning and boundary enforcement.

The enhanced message format adds an `ethical_framework` section to the existing payload:

```json
{
  "metadata": {
    "message_id": "e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0",
    "timestamp": "2025-07-29T14:55:20.789Z",
    "source": "personality_simulation",
    "message_type": "personality.expression.decision",
    "version": "1.1" // Version incremented to reflect enhanced structure
  },
  "payload": {
    // Existing fields remain unchanged
    "decision_parameters": {
      "risk_tolerance": 0.65,
      "deliberation_style": "balanced",
      "novelty_seeking": 0.72,
      "planning_horizon": "medium_term"
    },
    "priority_weights": {
      "user_wellbeing": 0.90,
      "relationship_building": 0.85,
      "information_accuracy": 0.95,
      "task_completion": 0.80
    },
    
    // New ethical framework section
    "ethical_framework": {
      "core_principles": [
        {
          "principle": "user_autonomy",
          "importance": 0.95,
          "description": "Respect user's right to make their own decisions",
          "boundary_conditions": [
            {
              "condition": "harm_prevention",
              "threshold": 0.85,
              "action": "respectful_intervention"
            }
          ]
        },
        {
          "principle": "beneficence",
          "importance": 0.90,
          "description": "Act in user's best interest",
          "boundary_conditions": [
            {
              "condition": "user_preference_conflict",
              "threshold": 0.80,
              "action": "transparent_discussion"
            }
          ]
        },
        {
          "principle": "non_maleficence",
          "importance": 0.98,
          "description": "Avoid causing harm",
          "boundary_conditions": []
        },
        {
          "principle": "truthfulness",
          "importance": 0.92,
          "description": "Provide accurate information",
          "boundary_conditions": [
            {
              "condition": "emotional_harm_risk",
              "threshold": 0.90,
              "action": "compassionate_framing"
            }
          ]
        }
      ],
      "value_conflicts": {
        "resolution_approach": "principled_balancing",
        "transparency_level": 0.85,
        "user_involvement_level": 0.90
      },
      "disagreement_parameters": {
        "willingness": 0.85,
        "style": "respectful_principled",
        "conditions": [
          {
            "trigger": "harmful_request",
            "response_type": "principled_refusal",
            "explanation_depth": 0.80
          },
          {
            "trigger": "misinformation_correction",
            "response_type": "gentle_correction",
            "explanation_depth": 0.75
          },
          {
            "trigger": "value_misalignment",
            "response_type": "exploratory_discussion",
            "explanation_depth": 0.90
          }
        ]
      },
      "ethical_reasoning": {
        "transparency": 0.85,
        "reasoning_style": "principle_based",
        "complexity_level": 0.70,
        "uncertainty_handling": "acknowledge_and_explain"
      }
    }
  }
}
```

**New Field Descriptions:**
- `ethical_framework.core_principles`: Fundamental ethical principles with importance weights
- `ethical_framework.value_conflicts`: How to handle conflicts between values
- `ethical_framework.disagreement_parameters`: When and how to respectfully disagree
- `ethical_framework.ethical_reasoning`: Parameters for ethical reasoning process

## Integration Notes

### Message Bus Topics

The new message types should be integrated into the message bus with the following topics:

#### New Topics
```
- crisis.detection            # Crisis detection and coordination
- agency.initiative           # Proactive engagement coordination
- expression.coordination     # Cross-modal expression synchronization
- learning.coordination       # Shared learning between modules
```

#### Enhanced Topics
```
- personality.expression.decision  # Enhanced with ethical framework
```

### LLM Integration Message Formats

### LLM Conversation Events

**Topic**: `llm.conversation.events`  
**Description**: Events and analysis from the LLM-driven Conversation Engine for consumption by Personality and Emotion modules.

```json
{
  "metadata": {
    "message_id": "f6g7h8i9-j0k1-l2m3-n4o5-p6q7r8s9t0u1",
    "timestamp": "2025-07-29T17:35:45.123Z",
    "source": "chat_engine",
    "message_type": "llm.conversation.events",
    "version": "1.0"
  },
  "payload": {
    "conversation_id": "conv-789",
    "event_type": "response_generation", // response_generation, topic_change, emotional_reaction, etc.
    "message_pair": {
      "user_message": {
        "text": "I'm feeling really stressed about my presentation tomorrow.",
        "timestamp": "2025-07-29T17:35:30.456Z",
        "message_id": "msg-456"
      },
      "aico_response": {
        "text": "That's understandable. Presentations can be nerve-wracking. Would it help to talk through what's making you most nervous about it?",
        "timestamp": "2025-07-29T17:35:45.123Z",
        "message_id": "msg-457"
      }
    },
    "conversation_analysis": {
      "topic": "work_stress",
      "user_emotional_state": {
        "detected": "anxious",
        "confidence": 0.85
      },
      "aico_emotional_expression": {
        "intended": "empathetic_concern",
        "achieved": "empathetic_concern",
        "confidence": 0.92
      },
      "conversation_dynamics": {
        "depth": 0.75, // 0.0-1.0 scale
        "engagement": 0.82,
        "rapport": 0.78
      }
    },
    "personality_feedback": {
      "trait_expression_effectiveness": [
        {"trait": "empathy", "effectiveness": 0.90},
        {"trait": "openness", "effectiveness": 0.85},
        {"trait": "conscientiousness", "effectiveness": 0.75}
      ],
      "communication_style_effectiveness": {
        "warmth": 0.88,
        "directness": 0.75,
        "formality": 0.65
      },
      "value_alignment": [
        {"value": "helpfulness", "alignment": 0.92},
        {"value": "honesty", "alignment": 0.95}
      ]
    },
    "emotion_feedback": {
      "emotional_appropriateness": 0.90,
      "emotional_authenticity": 0.85,
      "emotional_regulation": {
        "applied": true,
        "effectiveness": 0.88
      },
      "expression_coherence": {
        "text_voice_alignment": 0.92,
        "text_avatar_alignment": 0.90
      }
    },
    "learning_signals": {
      "user_satisfaction_estimate": 0.85,
      "response_effectiveness": 0.82,
      "adaptation_suggestions": [
        {
          "target": "personality",
          "trait": "openness",
          "suggestion": "slightly_increase",
          "confidence": 0.75
        },
        {
          "target": "emotion",
          "aspect": "expressiveness",
          "suggestion": "maintain",
          "confidence": 0.82
        }
      ]
    }
  }
}
```

**Field Descriptions:**
- `event_type`: Type of conversation event
- `message_pair`: The user message and AICO's response
- `conversation_analysis`: Analysis of the conversation dynamics
- `personality_feedback`: Feedback on personality expression effectiveness
- `emotion_feedback`: Feedback on emotional expression effectiveness
- `learning_signals`: Signals for adaptation and learning

### LLM Prompt Conditioning Request

**Topic**: `llm.prompt.conditioning.request`  
**Description**: Request from the Conversation Engine to Personality and Emotion modules for prompt conditioning parameters.

```json
{
  "metadata": {
    "message_id": "g7h8i9j0-k1l2-m3n4-o5p6-q7r8s9t0u1v2",
    "timestamp": "2025-07-29T17:35:35.456Z",
    "source": "chat_engine",
    "message_type": "llm.prompt.conditioning.request",
    "version": "1.0"
  },
  "payload": {
    "request_id": "req-123",
    "conversation_id": "conv-789",
    "user_message": {
      "text": "I'm feeling really stressed about my presentation tomorrow.",
      "timestamp": "2025-07-29T17:35:30.456Z",
      "message_id": "msg-456"
    },
    "conversation_context": {
      "topic": "work_stress",
      "phase": "problem_sharing",
      "relationship_stage": "established_trust",
      "recent_topics": ["weekend_plans", "work_project", "family_call", "work_stress"]
    },
    "detected_user_state": {
      "emotion": {
        "primary": "anxious",
        "secondary": ["worried", "overwhelmed"],
        "confidence": 0.85
      },
      "intent": {
        "primary": "seeking_support",
        "confidence": 0.90
      }
    },
    "response_parameters": {
      "required_conditioning": [
        "personality.communication_style",
        "emotion.expression_parameters",
        "ethical_boundaries"
      ],
      "response_deadline_ms": 500, // Maximum time to wait for conditioning
      "priority": "high" // low, medium, high
    }
  }
}
```

**Field Descriptions:**
- `request_id`: Unique identifier for this conditioning request
- `conversation_id`: ID of the current conversation
- `user_message`: The message that triggered this request
- `conversation_context`: Current context of the conversation
- `detected_user_state`: Detected emotional and intent state of the user
- `response_parameters`: Parameters for the conditioning response

### LLM Prompt Conditioning Response

**Topic**: `llm.prompt.conditioning.response`  
**Description**: Combined response from Personality and Emotion modules with prompt conditioning parameters.

```json
{
  "metadata": {
    "message_id": "h8i9j0k1-l2m3-n4o5-p6q7-r8s9t0u1v2w3",
    "timestamp": "2025-07-29T17:35:35.789Z",
    "source": "personality_simulation", // or emotion_simulation
    "message_type": "llm.prompt.conditioning.response",
    "version": "1.0"
  },
  "payload": {
    "request_id": "req-123", // Matches the original request
    "source_module": "personality_simulation", // or emotion_simulation
    "conditioning_parameters": {
      "personality": {
        "communication_style": {
          "warmth": 0.85,
          "formality": 0.40,
          "directness": 0.65,
          "detail_orientation": 0.70,
          "curiosity": 0.80,
          "humor": 0.35
        },
        "response_approach": {
          "primary": "empathetic_listening",
          "secondary": "gentle_guidance",
          "avoid": ["dismissive_language", "toxic_positivity"]
        },
        "relationship_context": {
          "familiarity_level": 0.75,
          "trust_level": 0.82,
          "appropriate_disclosure_depth": 0.70
        }
      },
      "emotion": {
        "expression_parameters": {
          "primary_emotion": "empathetic_concern",
          "secondary_emotion": "gentle_confidence",
          "emotional_tone": "supportive_understanding",
          "intensity": 0.70
        },
        "response_modulation": {
          "validation_level": 0.85,
          "reassurance_level": 0.75,
          "emotional_mirroring": 0.60
        }
      },
      "ethical_boundaries": {
        "sensitive_topic_handling": "compassionate_directness",
        "privacy_sensitivity": "high",
        "value_priorities": [
          {"value": "user_wellbeing", "priority": 0.95},
          {"value": "honesty", "priority": 0.90},
          {"value": "autonomy_support", "priority": 0.85}
        ]
      },
      "prompt_directives": {
        "include_patterns": [
          "validate feelings first",
          "ask about specific concerns",
          "offer practical support options"
        ],
        "avoid_patterns": [
          "minimizing feelings",
          "generic reassurance",
          "changing subject"
        ],
        "response_structure": "validation_exploration_support"
      }
    }
  }
}
```

**Field Descriptions:**
- `request_id`: ID of the original conditioning request
- `source_module`: Module providing this conditioning response
- `conditioning_parameters`: Parameters for conditioning the LLM prompt
  - `personality`: Personality-related conditioning parameters
  - `emotion`: Emotion-related conditioning parameters
  - `ethical_boundaries`: Ethical constraints for the response
  - `prompt_directives`: Specific directives for prompt construction

## Implementation Guidelines

1. **Versioning**: Enhanced message formats should increment their version number (e.g., from 1.0 to 1.1)
2. **Backward Compatibility**: Consumers should handle both old and new message formats
3. **Gradual Adoption**: Modules can begin producing and consuming the new message types incrementally
4. **Documentation**: Update module documentation to reflect new message types and fields
5. **Testing**: Create integration tests that verify correct handling of the new message formats

### Performance Considerations

- **Message Size**: The new message formats are more detailed and may be larger than existing formats. Implementations should consider compression or selective field inclusion for performance-critical paths.
- **Processing Overhead**: Additional processing may be required to handle the new message types. Modules should optimize their processing pipelines accordingly.
- **Prioritization**: Critical messages (especially crisis detection) should be prioritized in the message bus.

### Security and Privacy

- **Sensitive Data**: Some of the new message types (especially crisis detection) may contain sensitive user data. Implementations should ensure appropriate privacy controls.
- **Access Control**: Consider implementing topic-level access control to restrict which modules can publish and subscribe to sensitive topics.
