# Communication Skills

AICO-initiated conversation skills for proactive user interaction.

## Skills

### 1. AskUserSkill
**Purpose**: Ask targeted questions to fill information gaps

**Use Cases**:
- Clarify ambiguous user preferences
- Gather missing context for goal execution
- Confirm assumptions before taking action
- Request approval for decisions

**Parameters**:
- `question` (required): The question to ask
- `context` (optional): Why you're asking
- `urgency`: low/medium/high
- `expected_answer_type`: text/yes_no/choice/number

**Example**:
```python
result = await ask_user_skill.execute(
    user_id="user123",
    input_data={
        "question": "What time do you prefer for morning reminders?",
        "context": "I'm setting up your daily goal review",
        "urgency": "medium",
        "expected_answer_type": "text"
    },
    context={}
)
```

### 2. InitiateConversationSkill
**Purpose**: Start open-ended dialogue about topics or concerns

**Use Cases**:
- Share observations or concerns
- Discuss interesting patterns noticed
- Express curiosity about user behavior
- Proactive relationship building

**Parameters**:
- `topic` (required): Subject to discuss
- `message` (required): Opening message
- `reason` (optional): Why initiating
- `emotional_context`: curious/concerned/excited/thoughtful

**Example**:
```python
result = await initiate_skill.execute(
    user_id="user123",
    input_data={
        "topic": "goal_progress",
        "message": "I noticed you've been working on your fitness goal consistently. How are you feeling about the progress?",
        "reason": "pattern_observation",
        "emotional_context": "curious"
    },
    context={}
)
```

## Learning System

### State-of-the-Art Learning

AICO uses **advanced learning techniques** from 2024 research in proactive conversational AI:

**Algorithms**:
- **Contextual Multi-Armed Bandit** with Thompson Sampling
- **Human-centered PCA dimensions**: Intelligence, Adaptivity, Civility
- **Real-time context-aware** decision making
- **Uncertainty quantification** and calibration

**What It Learns**:
1. **Optimal Timing**: 11-dimensional contextual features (hour, day, user state, engagement)
2. **Strategy Selection**: 11 bandit arms (time/topic/urgency combinations)
3. **Adaptivity**: Patience, Timing Sensitivity, Self-awareness (ECE)
4. **Civility**: Boundary respect, Emotional intelligence

**Key Features**:
- **Thompson Sampling**: Bayesian exploration-exploitation with Beta distributions
- **Contextual Features**: Hour, day, response rate, engagement, pending initiations, etc.
- **Multi-dimensional Scoring**: Adaptivity (60%) + Civility (40%)
- **Automatic Learning**: Updates from every user response
- **Fast Convergence**: 20-50 trials for reliable estimates

**Example**:
```python
from aico.ai.agency.skills.communication.learning import (
    ContextualBanditLearner,
    extract_contextual_features
)

# Initialize learner
learner = ContextualBanditLearner(db)

# Extract context
context = extract_contextual_features(db, user_id)

# Select optimal strategy
strategy_id, expected_reward = learner.select_strategy(context)
print(f"Strategy: {strategy_id}, Expected reward: {expected_reward:.3f}")

# After user responds, update bandit
learner.update_from_outcome(
    strategy_id="time_evening",
    context=context,
    outcome="answered",
    response_time=120.0  # seconds
)

# Get arm statistics
stats = learner.get_arm_statistics()
for arm_id, arm_stats in stats.items():
    print(f"{arm_id}: E[reward]={arm_stats['expected_reward']:.3f}")
```

**Research Foundation**:
- "Towards Human-centered Proactive Conversational Agents" (2024)
- Thompson Sampling for Multi-Armed Bandits (Stanford)
- Contextual Bandits for Personalization

See [COMMUNICATION_SKILLS_LEARNING.md](../../../../docs/concepts/agency/COMMUNICATION_SKILLS_LEARNING.md) for complete technical details.

## Database Schema

### aico_conversation_initiations

Tracks all AICO-initiated conversations for learning:

```sql
CREATE TABLE aico_conversation_initiations (
    initiation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    trigger_source TEXT NOT NULL,        -- 'skill', 'agency', 'scheduler'
    trigger_reason TEXT,                 -- Why initiated
    question TEXT,                       -- Question/message
    context TEXT,                        -- Additional context
    urgency TEXT DEFAULT 'medium',       -- low/medium/high
    expected_answer_type TEXT,           -- text/yes_no/choice/number
    initiated_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,               -- When user responded
    resolution_status TEXT,              -- pending/answered/dismissed
    user_response_time INTEGER,          -- Seconds to respond
    engagement_score REAL,               -- Quality of engagement
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Indexes**:
- `user_id` - Fast user lookups
- `conversation_id` - Link to conversations
- `resolution_status` - Filter by status
- `initiated_at` - Time-based queries

## Integration

### Message Bus

Skills publish to: `conversation/aico/initiate/v1`

ConversationEngine subscribes and handles AICO-initiated messages.

### Memory System

AICO-initiated conversations stored in Working Memory (LMDB) like user-initiated:
- Same `conversation_id` pattern: `{user_id}_{timestamp}`
- Same 24hr TTL
- Semantic memory extracts facts from both

### Agency Integration

Skills can be invoked by:
- Plan execution steps
- Goal-driven actions
- Scheduler tasks
- Manual triggers

## Learning Metrics

**Success Indicators**:
- Response rate > 70%: High engagement
- Response rate 40-70%: Moderate engagement
- Response rate < 40%: Review strategy

**Optimization**:
- Time of day patterns (confidence > 0.5)
- Topic effectiveness rankings
- Urgency level preferences
- Response time expectations

## Best Practices

1. **Don't Spam**: Max 1 pending initiation per hour
2. **Respect Timing**: Use learned time-of-day patterns
3. **Be Relevant**: Only initiate when genuinely useful
4. **Learn Continuously**: Track all outcomes
5. **Adapt**: Adjust based on user response patterns
