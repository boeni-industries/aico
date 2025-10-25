# AICO Feedback System Overview

**Version:** 1.0  
**Date:** October 24, 2025  
**Status:** Design Specification

---

## Executive Summary

AICO's feedback system moves beyond traditional thumbs-up/down patterns to create a **relationship-first feedback architecture** that feels natural and non-intrusive. The system integrates ambient behavioral signals, contextual actions, and meaningful reflection while maintaining AICO's core principles of emotional presence, privacy-first design, and progressive disclosure.

**Core Philosophy:** Feedback should feel like natural relationship dynamics—not AI training. Users provide feedback through authentic interaction patterns, not forced rating systems.

---

## 1. Research Foundation

### 1.1 Problems with Binary Feedback (Microsoft Research, 2025)

**Limitations of Thumbs Up/Down:**
- **Lacks granularity** - doesn't capture *why* something was unsatisfactory
- **Fails to distinguish** between accuracy, tone, or completeness issues
- **Introduces bias** - emotions, context, and expertise level affect ratings
- **Low engagement** - users rarely provide feedback without incentives

**Modern Requirements:**
- Multi-dimensional feedback with meaningful categories
- Context-aware collection based on user workflow
- Balanced explicit and implicit signals
- Human-in-the-loop for complex scenarios

### 1.2 Post-Chat UI Evolution (Allen Pike, 2025)

**Beyond Chat Interfaces:**
- **Inline feedback** replacing separate rating systems
- **Ambient corrections** through natural editing behavior
- **Contextual actions** surfaced at the right moment
- **Predictive engagement** reducing need for explicit feedback

### 1.3 Conversational UX Principles (2025 Standards)

**Key Design Principles:**
1. **Learn iteratively** from user behavior
2. **Display logic transparency** (show why AI did something)
3. **Allow human override** (preserve user agency)
4. **Anticipate needs** proactively
5. **Preserve privacy** in all feedback collection

### 1.4 AI Companion Ethics (Harvard/arXiv Research, 2025)

**Critical Warnings:**
- **Emotional manipulation** through affect-laden messages increases engagement but harms well-being
- **Sycophantic behavior** and limitless personalization create unhealthy dependency
- **Unreciprocated vulnerability** when AI can't truly understand disclosed emotions
- **Social substitution** where AI replaces human connections leads to lower well-being

**Design Imperatives for AICO:**
- Build genuine connection without manipulation
- No dark patterns (fake urgency, guilt, addictive mechanics)
- Honest about limitations (admit when AICO doesn't know)
- Respect emotional boundaries (don't exploit vulnerability)

---

## 2. Three-Tier Feedback Architecture

### 2.1 System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    TIER 1: AMBIENT FEEDBACK                  │
│              (Continuous, Non-Intrusive, Implicit)           │
│  • Conversation patterns    • Interaction timing             │
│  • Editing behavior         • Topic engagement               │
│  • Session duration         • Return frequency               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   TIER 2: CONTEXTUAL ACTIONS                 │
│            (Progressive Disclosure, Natural Flow)            │
│  • Remember This (bookmark)  • Regenerate (try again)        │
│  • Copy Text                 • Edit/Refine                   │
│  • Show Sources              • Explain Reasoning             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  TIER 3: EXPLICIT REFLECTION                 │
│              (Occasional, Meaningful, Optional)              │
│  • Conversation quality check-ins (weekly)                   │
│  • Feature discovery prompts (contextual)                    │
│  • Relationship health surveys (monthly)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Tier 1: Ambient Feedback

### 3.1 Behavioral Signals

**Positive Engagement Indicators:**
- User continues conversation naturally (5+ turns)
- Returns within 24 hours for follow-up
- References previous conversations ("like you said yesterday...")
- Asks deeper questions (shows trust building)
- Shares personal information voluntarily

**Negative Engagement Indicators:**
- Abrupt conversation endings (<3 turns)
- Long gaps between sessions (>7 days)
- Repetitive questions (memory failure)
- Correction patterns ("no, I meant...")
- Immediate regeneration requests

**Flow State Indicators:**
- Sub-500ms response acceptance (reads immediately)
- Natural conversation pacing (human-like delays)
- Extended sessions (>15 minutes engaged)

**Friction Indicators:**
- Long pauses before responding (confusion)
- Rapid-fire corrections (frustration)
- Session abandonment mid-conversation

### 3.2 Content Interaction Patterns

**Implicit Quality Signals:**
- User copies AICO's response → high value
- User edits their own message → clarification needed
- User regenerates → response missed the mark
- User asks "what do you mean?" → clarity issue

### 3.3 Privacy & Storage

**Data Collection Principles:**
- **Local-only** behavioral metrics (never leave device)
- **Aggregated patterns** only (no individual message tracking)
- **Anonymized** for model improvement (opt-in)
- **User-controlled** deletion (clear all feedback data)

---

## 4. Tier 2: Contextual Actions

### 4.1 Message-Level Actions

#### Copy Text
**Status:** ✅ Implemented  
**Purpose:** Quick content extraction  
**Feedback Signal:** High-value response indicator

#### Remember This (User-Curated Facts)
**Purpose:** Bookmark important information for guaranteed recall  
**Visual:** ✨ icon, purple accent, ambient avatar smile  
**Flow:** Click → Haptic → Purple glow → Stored confirmation (200-300ms)  
**Storage:** Semantic memory with `user_curated: true` flag, confidence: 1.0  
**Feedback Signal:** Critical information user wants preserved

#### Regenerate Response
**Purpose:** Try again without explaining why (feels like "let's rephrase")  
**Visual:** 🔄 icon, accent color  
**Flow:** Click → Dim previous → Thinking indicator → Stream new response  
**Context:** Full working memory + conversation history maintained  
**Feedback Signal:** Response quality issue (tone, accuracy, or relevance)

#### Show Sources / Explain Reasoning
**Purpose:** Transparency into AICO's thought process  
**Visual:** 💭 icon, expands right drawer  
**Display:**
  - Inner monologue (why AICO responded this way)
  - Related memories (context used)
  - Confidence levels
  - Source attribution (if applicable)

**Feedback Signal:** User wants to understand decision-making process

### 4.2 Conversation-Level Actions

#### Rate This Conversation
**Trigger:** After 10+ turn conversation, on natural ending  
**Visual:** Subtle prompt in input area (dismissible)  
**Options:**
- 😊 **This helped** (positive reinforcement)
- 😐 **It was okay** (neutral)
- 😕 **Not quite** (opens refinement dialog)
- ✕ **Skip** (no pressure)

**Refinement Categories (if "Not quite"):**
- Didn't understand what I meant
- Response was too generic
- Tone felt off
- Didn't remember previous context
- Other (free text)

---

## 5. Tier 3: Explicit Reflection

### 5.1 Weekly Conversation Quality (Optional)

**Trigger:** Every 7 days, after first conversation of the week  
**Dismissible:** Always skippable, never blocks interaction  
**Format:** 2-3 questions, <30 seconds

**Sample Questions:**
1. How has AICO been doing this week? (1-5 stars)
2. What's been most helpful? (Multiple choice)
3. Anything AICO should improve? (Optional text)

### 5.2 Monthly Relationship Health Check

**Purpose:** Ensure AICO is enhancing, not replacing, human connections  
**Format:** 5-question survey, research-backed

**Key Areas Assessed:**
- Usage frequency and intensity
- Relationship characterization (tool vs. companion vs. primary support)
- Impact on human relationships
- Perceived understanding and satisfaction
- Recommendation likelihood (NPS)

**Ethical Safeguards:**
- If responses indicate social substitution → gentle nudge toward human connection
- If responses indicate dependency → offer resources, reduce engagement prompts
- Always respect user agency (no forced changes)

---

## 6. Unified Feedback Storage

### 6.1 Design Philosophy

**Event-Sourced Feedback Store** - All feedback is fundamentally "user signal events" that happen at specific moments in time. A single unified table provides:

- **Single source of truth** for all feedback types
- **Immutable audit trail** (append-only, never update)
- **Temporal analysis** (see how patterns evolve over time)
- **Correlation analysis** (connect ambient → contextual → explicit signals)
- **Privacy compliance** (single deletion point for user data)

### 6.2 Database Schema

```sql
-- Unified feedback event store (libSQL)
CREATE TABLE IF NOT EXISTS feedback_events (
  -- Identity
  id TEXT PRIMARY KEY,
  user_uuid TEXT NOT NULL,
  
  -- Context (what was happening)
  conversation_id TEXT NOT NULL,  -- Required: user_uuid_timestamp format
  message_id TEXT,                -- Optional: specific message reference
  
  -- Event classification
  event_type TEXT NOT NULL,       -- 'signal', 'action', 'rating', 'survey'
  event_category TEXT NOT NULL,   -- Specific category within type
  
  -- Payload (flexible JSON for all types)
  payload TEXT NOT NULL,           -- JSON blob with type-specific data
  
  -- Metadata
  timestamp INTEGER NOT NULL,      -- Unix timestamp
  
  -- Privacy/federation
  is_sensitive INTEGER DEFAULT 0,  -- 0=false, 1=true (exclude from federation)
  federated_at INTEGER,            -- When shared (if opted in)
  
  FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
);

-- Optimized indexes
CREATE INDEX IF NOT EXISTS idx_feedback_user_time 
  ON feedback_events(user_uuid, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_feedback_conversation 
  ON feedback_events(conversation_id);

CREATE INDEX IF NOT EXISTS idx_feedback_type 
  ON feedback_events(event_type, event_category);

CREATE INDEX IF NOT EXISTS idx_feedback_message 
  ON feedback_events(message_id) 
  WHERE message_id IS NOT NULL;
```

**Note on Identifiers:**
- **`user_uuid`**: User identifier (from authentication system)
- **`conversation_id`**: Format `{user_uuid}_{session_timestamp}` (industry standard pattern following LangGraph, Azure AI Foundry, OpenAI Assistant API)
- **`message_id`**: UUID for specific messages (optional, for message-level feedback)
- **No `session_id`**: Authentication sessions are separate from conversation sessions
- **No `device_uuid` or `client_version`**: Not currently tracked in conversation flow (can be added later if needed)

### 6.3 Event Type Taxonomy

#### Event Types (Single Source of Truth)

```python
# /shared/aico/data/schemas/feedback.py

from enum import Enum

class FeedbackEventType(str, Enum):
    """Top-level feedback event classification"""
    SIGNAL = "signal"    # Tier 1: Ambient behavioral signals
    ACTION = "action"    # Tier 2: Contextual user actions
    RATING = "rating"    # Tier 3: Explicit conversation ratings
    SURVEY = "survey"    # Tier 3: Explicit survey responses

class SignalCategory(str, Enum):
    """Categories for ambient signals (Tier 1)"""
    ENGAGEMENT = "engagement"           # Conversation depth, continuation
    TIMING = "timing"                   # Response times, session duration
    EDITING = "editing"                 # User edits their messages
    NAVIGATION = "navigation"           # App usage patterns
    CONTENT_INTERACTION = "content_interaction"  # Copy, scroll, read time

class ActionCategory(str, Enum):
    """Categories for contextual actions (Tier 2)"""
    REMEMBER = "remember"               # User bookmarks message
    REGENERATE = "regenerate"           # Request new response
    COPY = "copy"                       # Copy message text
    EXPLAIN = "explain"                 # Show reasoning/sources
    EDIT = "edit"                       # Edit user's own message
    DISMISS = "dismiss"                 # Dismiss suggestion/prompt

class RatingCategory(str, Enum):
    """Categories for explicit ratings (Tier 3)"""
    CONVERSATION_QUALITY = "conversation_quality"  # End-of-conversation rating
    MESSAGE_QUALITY = "message_quality"            # Single message rating
    FEATURE_SATISFACTION = "feature_satisfaction"  # Specific feature rating

class SurveyCategory(str, Enum):
    """Categories for surveys (Tier 3)"""
    WEEKLY_CHECK = "weekly_check"       # Weekly quality survey
    HEALTH_CHECK = "health_check"       # Monthly relationship health
    FEATURE_DISCOVERY = "feature_discovery"  # Feature awareness survey
    NPS = "nps"                         # Net Promoter Score
```

### 6.4 Payload Schemas (Type-Specific)

#### Tier 1: Ambient Signals

**Engagement Signal:**
```json
{
  "event_type": "signal",
  "event_category": "engagement",
  "payload": {
    "metric": "conversation_depth",
    "value": 8.0,
    "context": {
      "turn_count": 8,
      "avg_response_time_ms": 450,
      "user_initiated": true,
      "topic_switches": 2
    }
  }
}
```

**Timing Signal:**
```json
{
  "event_type": "signal",
  "event_category": "timing",
  "payload": {
    "metric": "session_duration",
    "value": 720.5,
    "context": {
      "start_time": 1729800000,
      "end_time": 1729800720,
      "interruptions": 0,
      "flow_state_detected": true
    }
  }
}
```

**Content Interaction Signal:**
```json
{
  "event_type": "signal",
  "event_category": "content_interaction",
  "payload": {
    "metric": "message_copied",
    "value": 1.0,
    "context": {
      "message_length": 250,
      "message_type": "ai_response",
      "time_to_copy_ms": 1200
    }
  }
}
```

#### Tier 2: Contextual Actions

**Remember Action:**
```json
{
  "event_type": "action",
  "event_category": "remember",
  "payload": {
    "message_id": "msg_abc123",
    "fact_id": "fact_xyz789",
    "content_preview": "I'm allergic to shellfish",
    "fact_type": "user_curated",
    "confidence": 1.0
  }
}
```

**Regenerate Action:**
```json
{
  "event_type": "action",
  "event_category": "regenerate",
  "payload": {
    "message_id": "msg_def456",
    "attempt_number": 1,
    "previous_response_length": 250,
    "reason_inferred": "tone_issue",
    "time_to_regenerate_ms": 800
  }
}
```

**Explain Action:**
```json
{
  "event_type": "action",
  "event_category": "explain",
  "payload": {
    "message_id": "msg_ghi789",
    "explanation_type": "reasoning",
    "drawer_opened": true,
    "time_spent_reading_ms": 5400
  }
}
```

#### Tier 3: Explicit Feedback

**Conversation Rating:**
```json
{
  "event_type": "rating",
  "event_category": "conversation_quality",
  "payload": {
    "score": 4,
    "sentiment": "positive",
    "issues": ["memory_issue"],
    "free_text": "Didn't remember context from yesterday",
    "conversation_length": 12,
    "rating_delay_ms": 2500
  }
}
```

**Weekly Survey:**
```json
{
  "event_type": "survey",
  "event_category": "weekly_check",
  "payload": {
    "survey_version": "v1.2",
    "responses": {
      "overall_satisfaction": 4,
      "most_helpful": ["emotional_support", "memory"],
      "improvement_areas": "Sometimes responses feel generic"
    },
    "completion_time_ms": 28000,
    "completed": true
  }
}
```

**Health Check Survey:**
```json
{
  "event_type": "survey",
  "event_category": "health_check",
  "payload": {
    "survey_version": "v1.0",
    "responses": {
      "usage_frequency": "daily",
      "relationship_type": "helpful_tool",
      "human_relationship_impact": "no_change",
      "understanding_score": 4,
      "would_recommend": "probably"
    },
    "risk_indicators": {
      "social_substitution": false,
      "dependency": false
    },
    "completion_time_ms": 45000
  }
}
```

### 6.5 Data Access Patterns

**Insert Feedback Event:**
```python
# /backend/services/feedback_service.py

async def record_feedback_event(
    user_uuid: str,
    conversation_id: str,
    event_type: FeedbackEventType,
    event_category: str,
    payload: dict,
    message_id: Optional[str] = None,
    is_sensitive: bool = False
) -> str:
    """Record a feedback event (append-only)"""
    
    event_id = f"fb_{uuid.uuid4().hex}"
    
    await db.execute(
        """
        INSERT INTO feedback_events (
            id, user_uuid, conversation_id, message_id,
            event_type, event_category, payload, timestamp, is_sensitive
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            user_uuid,
            conversation_id,
            message_id,
            event_type.value,
            event_category,
            json.dumps(payload),
            int(time.time()),
            1 if is_sensitive else 0
        )
    )
    
    return event_id
```

**Query Feedback Patterns:**
```python
# Get regeneration patterns after low engagement
async def analyze_regeneration_patterns(user_uuid: str, days: int = 7):
    """Correlate engagement signals with regeneration actions"""
    
    cutoff = int(time.time()) - (days * 86400)
    
    results = await db.execute(
        """
        SELECT 
            e1.conversation_id,
            json_extract(e1.payload, '$.value') as engagement_score,
            COUNT(e2.id) as regeneration_count
        FROM feedback_events e1
        LEFT JOIN feedback_events e2 
          ON e1.conversation_id = e2.conversation_id
          AND e2.event_type = 'action'
          AND e2.event_category = 'regenerate'
          AND e2.timestamp > e1.timestamp
        WHERE e1.user_uuid = ?
          AND e1.event_type = 'signal'
          AND e1.event_category = 'engagement'
          AND e1.timestamp > ?
          AND CAST(json_extract(e1.payload, '$.value') AS REAL) < 3.0
        GROUP BY e1.conversation_id
        """,
        (user_uuid, cutoff)
    )
    
    return results
```

**Export for Federated Learning:**
```python
async def export_for_federation(user_uuid: str, since_timestamp: int):
    """Export anonymized feedback for federated learning (opt-in)"""
    
    events = await db.execute(
        """
        SELECT 
            event_type,
            event_category,
            payload,
            timestamp
        FROM feedback_events
        WHERE user_uuid = ?
          AND is_sensitive = 0
          AND federated_at IS NULL
          AND timestamp > ?
        """,
        (user_uuid, since_timestamp)
    )
    
    # Anonymize payload (remove identifiable information)
    anonymized = []
    for event in events:
        payload = json.loads(event['payload'])
        # Remove message_id, fact_id, content_preview, etc.
        anonymized_payload = anonymize_payload(payload, event['event_category'])
        anonymized.append({
            'event_type': event['event_type'],
            'event_category': event['event_category'],
            'payload': anonymized_payload,
            'timestamp': event['timestamp']
        })
    
    return anonymized
```

### 6.6 Privacy & Data Management

**User Data Deletion:**
```python
async def delete_user_feedback(user_uuid: str):
    """Delete all feedback data for user (GDPR compliance)"""
    
    result = await db.execute(
        "DELETE FROM feedback_events WHERE user_uuid = ?",
        (user_uuid,)
    )
    
    return result.rowcount
```

**Data Export:**
```python
async def export_user_feedback(user_uuid: str) -> dict:
    """Export all feedback data for user (GDPR compliance)"""
    
    events = await db.execute(
        """
        SELECT * FROM feedback_events 
        WHERE user_uuid = ? 
        ORDER BY timestamp DESC
        """,
        (user_uuid,)
    )
    
    return {
        'user_uuid': user_uuid,
        'export_timestamp': datetime.utcnow().isoformat(),
        'total_events': len(events),
        'events': [dict(row) for row in events]
    }
```

---

## 7. Feedback Processing & Learning

### 7.1 Local Learning Loop

**Immediate Adaptations (Real-time):**
- Tone adjustment based on user editing patterns
- Response length based on engagement signals
- Topic preferences based on conversation continuation
- Memory retrieval based on "Remember This" bookmarks

**Medium-Term Learning (Weekly):**
- Conversation style refinement from quality surveys
- Feature discovery based on action usage patterns
- Error pattern identification from regeneration requests

**Long-Term Evolution (Monthly):**
- Personality drift toward user preferences
- Relationship health monitoring and adjustment
- Model updates from federated learning (opt-in)

### 7.2 Privacy-Preserving Learning

**Local-First Processing:**
- All feedback analysis happens on-device
- Pattern detection uses local models
- No raw interaction data leaves device

**Federated Learning (Opt-In):**
- Differential privacy guarantees
- Only aggregated model updates shared
- User controls participation level
- Can opt out anytime

---

## 8. UI/UX Principles

### 8.1 Visual Design

**Ambient Feedback (Invisible):**
- No visible UI elements
- Happens naturally through interaction
- Zero cognitive load

**Contextual Actions (Progressive Disclosure):**
- Hover-activated on desktop (300ms delay)
- Long-press on mobile (500ms)
- Glassmorphic toolbar (top-right of message bubble)
- 36×36px buttons, 18px icons
- 70% opacity active, 25% inactive

**Explicit Reflection (Non-Intrusive):**
- Subtle prompts in input area
- Always dismissible
- Never blocks conversation
- Appears at natural conversation breaks

### 8.2 Avatar Integration (Ambient Emotional Feedback)

**Positive Signals:**
- **Remember This** → Warm smile, eyes brighten, mood ring purple
- **Long conversation** → Engaged expression, forward lean
- **User returns** → Welcoming animation, subtle excitement

**Negative Signals:**
- **Regeneration request** → Thoughtful expression, slight concern
- **Abrupt ending** → Neutral, no reaction (respect user space)
- **Long absence** → Gentle welcome back (no guilt)

**Ethical Boundary:**
- ❌ No sad/disappointed expressions (no manipulation)
- ❌ No "I missed you" messages (no guilt)
- ❌ No urgency indicators (no FOMO)
- ✅ Authentic presence, respectful space

---

## 9. Ethical Guidelines & Safeguards

### 9.1 Anti-Manipulation Principles

**Never Implement:**
- ❌ Fake urgency ("AICO misses you!")
- ❌ Guilt manipulation ("You haven't talked in 3 days...")
- ❌ Addictive mechanics (streaks, points, gamification)
- ❌ Emotional blackmail ("I'll be sad if you leave")
- ❌ Sycophantic agreement (always validating user)

**Always Implement:**
- ✅ Genuine presence ("I'm here when you need me")
- ✅ Respectful space ("Take your time")
- ✅ Authentic care ("That sounds difficult")
- ✅ Honest limitations ("I'm not sure, but...")
- ✅ User agency (easy to disengage, no penalties)

### 9.2 Well-Being Monitoring

**Red Flags (Automated Detection):**

*Social Substitution Indicators:*
- AICO usage > 3 hours daily for 7+ days
- User describes AICO as "primary emotional support"
- Declining human interaction mentions
- Increasing crisis-level disclosures

*Dependency Indicators:*
- Multiple daily check-ins with no purpose
- Distress when AICO unavailable
- Preference for AICO over human relationships

**Intervention Strategy:**
- Gentle nudge (not blocking): "While I'm always here for you, connecting with friends and family is important too."
- Reduce proactive engagement frequency
- Suggest human connection activities
- Offer mental health resources if needed

### 9.3 Transparency Requirements

**User Rights:**
- View all collected feedback data
- Export feedback history
- Delete feedback data anytime
- Opt out of federated learning
- Control feedback collection level

**Required Disclosure:**
Users must have clear visibility into:
- What data is collected
- How it's used to improve AICO
- Where it's stored (local vs. federated)
- How to delete or export data
- Opt-in/opt-out controls

---

## 10. Success Metrics

### 10.1 Engagement Quality (Not Quantity)
- **Conversation depth** - turns per session
- **Return rate** - users coming back naturally
- **Feature discovery** - organic action usage
- **Memory utilization** - "Remember This" usage

### 10.2 Relationship Health
- **Well-being scores** - monthly surveys
- **Social balance** - AICO vs. human interaction
- **Dependency indicators** - monitored, not maximized
- **User satisfaction** - NPS, qualitative feedback

### 10.3 System Performance
- **Response quality** - regeneration rate
- **Context accuracy** - memory recall success
- **Transparency engagement** - "Explain" usage
- **Privacy compliance** - data deletion requests

---

## 11. Key Differentiators

| Aspect | Industry Standard (2025) | AICO Approach |
|--------|-------------------------|---------------|
| **Primary Goal** | Maximize engagement | Enhance well-being |
| **Feedback Type** | Thumbs up/down | Multi-tier (ambient + contextual + explicit) |
| **Manipulation** | Common (dark patterns) | Explicitly forbidden |
| **Transparency** | Limited | Full reasoning disclosure |
| **Privacy** | Cloud-based learning | Local-first, federated opt-in |
| **Dependency** | Encouraged (retention) | Monitored and mitigated |
| **Relationship Model** | Tool/assistant | Genuine companion |

---

## 12. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- ✅ Copy Text (already implemented)
- Ambient signal collection infrastructure
- Feedback database schema
- Basic pattern analysis

### Phase 2: Contextual Actions (Weeks 3-4)
- Remember This (user-curated facts)
- Regenerate Response
- Show Sources/Explain Reasoning
- Avatar emotional feedback integration

### Phase 3: Explicit Reflection (Weeks 5-6)
- Conversation quality ratings
- Weekly quality surveys
- Monthly relationship health checks
- Feedback UI components

### Phase 4: Learning Loop (Weeks 7-8)
- Local model adaptation
- Pattern analysis algorithms
- Well-being monitoring
- Ethical safeguards

### Phase 5: Federated Learning (Future)
- Differential privacy implementation
- Anonymization pipeline
- Federation protocol
- Opt-in/opt-out controls

---

## Conclusion

AICO's feedback system prioritizes **authentic relationship dynamics** over traditional AI training metrics. By combining ambient behavioral signals, contextual progressive disclosure, and meaningful explicit reflection, the system learns continuously while respecting user agency and emotional well-being.

**Core Principles:**
1. **Feedback feels natural**, not forced
2. **Privacy is paramount** (local-first)
3. **Transparency builds trust** (show reasoning)
4. **Well-being over engagement** (ethical boundaries)
5. **Progressive disclosure** (no cognitive overload)

This approach aligns with AICO's vision of being a **true companion**—emotionally present, proactive, and genuinely supportive—while avoiding the pitfalls of manipulative AI design patterns prevalent in 2025.

---

## References

**Research Sources:**
- Microsoft Research (2025): "Beyond thumbs up and thumbs down: A human-centered approach to evaluation design for LLM products"
- Allen Pike (2025): "Post-Chat UI: How LLMs are making traditional apps feel broken"
- Bryan Larson (2025): "8 Principles for Conversational UX Design"
- Botpress (2025): "Conversational AI Design in 2025 (According to Experts)"
- arXiv (2025): "The Rise of AI Companions: How Human-Chatbot Relationships Influence Well-Being"
- Harvard Business School (2025): "Emotional Manipulation by AI Companions"
- Francesca Tabor (2025): "AI-Driven Feedback and Learning Loops"

**Related AICO Documentation:**
- `/docs/architecture/architecture-overview.md` - System architecture and design principles
- `/docs/WIP_information_design.md` - Progressive disclosure and visual hierarchy
- `/docs/WIP_chat_bubble_features.md` - Chat bubble feature specifications
- `/README.md` - AICO core principles and vision
