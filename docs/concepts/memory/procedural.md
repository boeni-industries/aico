# Procedural Memory: The Adaptive Learning System

## Executive Summary

**What It Does**: Procedural memory enables AICO to learn and adapt its interaction style based on user feedback, transforming from a static assistant into a personalized companion that evolves with each relationship.

**Value Proposition**: 
- **Personalization**: Each user gets a unique interaction style tailored to their preferences (concise vs. detailed, formal vs. casual, proactive vs. reactive)
- **Continuous Improvement**: System learns from every thumbs-up/down, becoming more aligned with user expectations over time
- **Multi-User Intelligence**: Handles family environments by learning distinct preferences for each person (Dad prefers brief answers, Sarah wants detailed explanations)
- **Zero Configuration**: No manual setup required—learns automatically from natural user feedback

**How It Works**: Instead of training neural networks (expensive, slow, opaque), the system learns **prompt templates**—text instructions that guide the existing conversation model. When a user gives feedback, the system adjusts which templates to use and how to apply them. Think of it as AICO learning "house rules" for each user rather than rewriting its brain.

**System Integration**:
- **Module Location**: Part of Memory System module in Intelligence & Memory domain
- **Enriches Conversation Engine**: Injects learned interaction preferences via message bus
- **Leverages Semantic Memory**: Uses existing embedding model and ChromaDB for skill matching
- **Complements Emotional Intelligence**: Learns preferred ways to express empathy and support
- **Supports Social Relationships**: Maintains distinct interaction profiles per family member
- **Feeds Knowledge Graph**: Interaction patterns become part of user relationship data
- **Message-Driven Communication**: All module interactions via ZeroMQ message bus with Protocol Buffers

**Storage Footprint**: ~10-50KB per user (vs. 4-8GB if we trained separate models)

**Performance**: <10ms skill selection overhead, no additional memory usage (reuses existing models)

---

## Core Function: Skill-Based Interaction

Procedural memory is modeled as a **Skill Store**, a library of discrete, context-aware procedures that AICO can learn and apply. This is more modular and interpretable than a monolithic set of learned patterns.

### What is a Skill?

A skill is a specialized, context-dependent procedure. Examples:
- `summarize_technical_document`: Provides concise, bulleted summaries.
- `casual_chat_evening`: Uses informal language and shows more proactivity.
- `code_review_feedback`: Delivers constructive feedback on code snippets politely.
- `empathy_expression_direct`: Uses explicit empathetic statements.
- `empathy_expression_subtle`: Suggests supportive actions rather than stating feelings.

### Skill Attributes

Each skill has:
- **Trigger Context**: Conditions that determine when the skill applies (user, topic, time of day, conversation state).
- **Procedure Template**: The action to take (e.g., a prompt template, response formatting rules).
- **Confidence Score**: A measure of how well the skill has performed (updated via feedback).
- **Usage Metadata**: Tracking when and how often the skill is applied.

---

## Learning System Architecture

### 1. Reinforcement Learning from Human Feedback (RLHF)

Explicit user feedback is the primary driver for skill acquisition and refinement. This provides a much stronger learning signal than relying on implicit pattern detection alone.

#### Conceptual Model

- **Feedback Mechanism**: After AICO applies a skill, the user is presented with a simple, non-intrusive feedback UI with three levels:
  1. **Primary**: Thumbs up/down (required, zero friction)
  2. **Secondary**: Optional dropdown with common reasons ("Too verbose", "Wrong tone", "Not helpful", "Incorrect info")
  3. **Tertiary**: Optional free text field (max 300 chars) for additional context
  
- **Reward Signal**: This feedback acts as a reward signal. Positive feedback reinforces the skill by increasing its confidence score, while negative feedback weakens it and encourages the system to try an alternative.

- **Multi-User Personalization**: For a multi-user environment like a family, the system learns a unique preference profile (a latent vector) for each user. This allows AICO to resolve conflicting preferences, learning that "Dad prefers concise answers" while "Sarah prefers detailed explanations."

- **What We Learn**: We learn **prompt templates** (text instructions), NOT neural network weights. This means:
  - Fast: Instant application, no training time
  - Interpretable: Can read/edit/debug learned patterns
  - Reversible: Easy to undo bad learning
  - Storage-efficient: ~10-50KB per user vs. 4-8GB for model checkpoints
  - Local-first friendly: Small text files, easy to sync/backup

#### Implementation Details

**Frontend UI Requirements**:
- Add thumbs up/down buttons to each AI message in the conversation view
- Buttons should be subtle and non-intrusive (icon-only, positioned near message)
- On click, show feedback dialog with:
  - Optional dropdown: "Too verbose", "Too brief", "Wrong tone", "Not helpful", "Incorrect info"
  - Optional free text field (max 300 chars)
  - Submit button sends to `POST /api/v1/memory/feedback`
- Use existing Flutter HTTP client (http/dio) for API calls

**Backend API Endpoint**: `POST /api/v1/memory/feedback`

**Following existing router.py patterns** (see `backend/api/conversation/router.py`):

**Request Schema** (`backend/api/memory/schemas.py`):
```python
from pydantic import BaseModel, Field
from typing import Optional

class FeedbackRequest(BaseModel):
    message_id: str = Field(..., description="UUID of the message being rated")
    skill_id: str = Field(..., description="UUID of the skill that was applied")
    reward: int = Field(..., ge=-1, le=1, description="Feedback: 1 (positive), -1 (negative), 0 (neutral)")
    reason: Optional[str] = Field(None, description="Structured reason from dropdown")
    free_text: Optional[str] = Field(None, max_length=300, description="Optional user explanation")

class FeedbackResponse(BaseModel):
    success: bool
    message: str
    skill_updated: bool
    new_confidence: float
```

**Router Implementation** (`backend/api/memory/router.py`):
```python
"""
Procedural Memory API Router

Provides REST endpoints for skill feedback and integrates with the message bus
for procedural memory processing. Follows AICO's message-driven architecture.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.proto.aico_memory_pb2 import FeedbackEvent  # Protocol Buffer schema
from backend.api.conversation.dependencies import get_current_user, get_message_bus_client
from backend.api.memory.schemas import FeedbackRequest, FeedbackResponse
from aico.ai.memory.procedural import SkillStore, update_skill_confidence

router = APIRouter()
logger = get_logger("backend", "api.memory")

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_skill_feedback(
    request: FeedbackRequest,
    current_user = Depends(get_current_user),
    bus_client = Depends(get_message_bus_client)
):
    """
    Submit feedback on AI response skill application.
    
    Follows AICO's message-driven architecture: publishes feedback event to message bus
    for processing by the Procedural Memory module.
    
    Args:
        request: Feedback data (skill_id, reward, reason, free_text)
        current_user: Authenticated user from dependency injection
        bus_client: Message bus client for publishing events
        
    Returns:
        FeedbackResponse with success status and updated confidence score
        
    Raises:
        HTTPException: 404 if skill not found, 500 on processing error
    """
    try:
        user_id = current_user['user_uuid']
        
        # Publish feedback event to message bus (message-driven architecture)
        feedback_event = FeedbackEvent(
            user_id=user_id,
            message_id=request.message_id,
            skill_id=request.skill_id,
            reward=request.reward,
            reason=request.reason or "",
            free_text=request.free_text or "",
            timestamp=int(datetime.utcnow().timestamp())
        )
        
        await bus_client.publish("memory/procedural/feedback/v1", feedback_event)
        
        # Retrieve skill from store for immediate response
        skill_store = SkillStore()
        skill = await skill_store.get_skill(request.skill_id, user_id)
        
        if not skill:
            raise HTTPException(
                status_code=404,
                detail=f"Skill {request.skill_id} not found for user"
            )
        
        # Update confidence score
        learning_rate = 0.1  # From config: core.memory.procedural.learning_rate
        old_confidence = skill.confidence_score
        new_confidence = old_confidence + learning_rate * request.reward
        new_confidence = max(0.0, min(1.0, new_confidence))  # Clamp to [0, 1]
        
        skill.confidence_score = new_confidence
        
        # Update feedback counters
        if request.reward > 0:
            skill.positive_feedback_count += 1
        elif request.reward < 0:
            skill.negative_feedback_count += 1
        
        skill.usage_count += 1
        
        # Persist to database
        await skill_store.update_skill(skill)
        
        # Log feedback event with performance metrics
        logger.info(
            "Skill feedback received",
            extra={
                "user_id": user_id,
                "skill_id": request.skill_id,
                "skill_name": skill.skill_name,
                "reward": request.reward,
                "reason": request.reason,
                "old_confidence": old_confidence,
                "new_confidence": new_confidence,
                "confidence_delta": new_confidence - old_confidence,
                "total_usage": skill.usage_count,
                "positive_rate": skill.positive_feedback_count / skill.usage_count if skill.usage_count > 0 else 0,
                "has_free_text": bool(request.free_text),
                "metric_type": "procedural_memory_feedback"
            }
        )
        
        # Note: Feedback event already published to message bus.
        # Procedural Memory module will handle trajectory logging asynchronously.
        
        return FeedbackResponse(
            success=True,
            message="Feedback recorded successfully",
            skill_updated=True,
            new_confidence=new_confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to process skill feedback: {e}",
            extra={
                "user_id": current_user.get('user_uuid'),
                "skill_id": request.skill_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to process feedback"
        )
```

### 2. Meta-Learning for Rapid Adaptation

To quickly adapt to new users or changing preferences, AICO uses a meta-learning approach. It learns *how to learn* interaction styles, rather than starting from scratch with each user.

#### Conceptual Model

- **How it Works**: The model's parameters are split into two parts:
    1. **Shared Parameters**: Capture general principles of good interaction, trained across all users.
    2. **Context Parameters**: A small, user-specific set of parameters that are quickly updated based on a few interactions.
- **Benefit**: This allows for extremely fast personalization and reduces the amount of data needed to learn a new user's preferences.

#### Implementation Details

**User Preference Vectors** (`shared/aico/ai/memory/user_preferences.py`):
- Each user has a latent preference vector (e.g., 16-32 dimensions) stored in the database.
- This vector is initialized with default values and updated based on feedback patterns.
- The vector encodes preferences like: formality, verbosity, proactivity tolerance, emotional expression style.

**Skill Matching Algorithm**:
```python
def select_skill(user_id: str, context: Dict[str, Any]) -> Skill:
    # 1. Get user's preference vector
    user_prefs = get_user_preferences(user_id)
    
    # 2. Query skills matching the context
    candidate_skills = skill_store.query(
        user_id=user_id,
        context_filters=context
    )
    
    # 3. Score each skill based on confidence + preference alignment
    for skill in candidate_skills:
        skill.score = (
            0.7 * skill.confidence_score +
            0.3 * cosine_similarity(skill.preference_profile, user_prefs)
        )
    
    # 4. Return highest scoring skill
    return max(candidate_skills, key=lambda s: s.score)
```

### 3. Self-Correction and Exploration (Agent Q Model)

AICO actively refines its skills by learning from both its successes and failures.

#### Conceptual Model

- **Exploration**: Occasionally, AICO will try a slightly different interaction style and ask for feedback (e.g., "I usually use bullet points, but would a paragraph be better here?"). This is a form of active learning to discover better procedures.
- **Self-Critique**: When an interaction receives negative feedback, the system logs it as an "unsuccessful trajectory."
- **Preference Optimization**: Using an algorithm like Direct Preference Optimization (DPO), the system learns to prefer successful interaction patterns over unsuccessful ones. This explicitly teaches the model what *not* to do, leading to more robust and reliable behavior.

#### Implementation Details

**Exploration Strategy** (`shared/aico/ai/memory/exploration.py`):
- With probability ε (e.g., 0.1), select a skill with lower confidence for exploration.
- Explicitly ask the user for feedback: "I'm trying a new approach—let me know if you prefer this style."
- Track exploration outcomes separately to measure learning effectiveness.

**Trajectory Logging** (`backend/services/trajectory_logger.py`):
- Log each conversation turn with: user input, selected skill, AI response, user feedback.
- Store successful trajectories (positive feedback) and unsuccessful ones (negative feedback).
- Use these trajectories for offline learning and skill refinement.

**Preference Optimization** (Phase 3 implementation):
- Periodically run a batch process that analyzes trajectories.
- Use DPO or similar algorithms to update skill templates based on preference pairs:
  - Preferred: Trajectories with positive feedback
  - Dispreferred: Trajectories with negative feedback
- Update the skill templates to increase the likelihood of preferred patterns.

---

## Data Model & Storage

### Database Schema (`shared/aico/data/schemas/procedural.py`)

**Skills Table**:
```sql
CREATE TABLE skills (
    skill_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    skill_type TEXT NOT NULL,  -- 'base', 'learned', 'user_created'
    trigger_context TEXT,  -- JSON: {topic, time_of_day, conversation_state}
    procedure_template TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.5,
    preference_profile TEXT,  -- JSON: latent vector for preference matching
    usage_count INTEGER DEFAULT 0,
    positive_feedback_count INTEGER DEFAULT 0,
    negative_feedback_count INTEGER DEFAULT 0,
    last_used_timestamp INTEGER,
    created_timestamp INTEGER NOT NULL,
    updated_timestamp INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_skills_user ON skills(user_id);
CREATE INDEX idx_skills_confidence ON skills(confidence_score DESC);
```

**User Preferences Table**:
```sql
CREATE TABLE user_preferences (
    user_id TEXT PRIMARY KEY,
    preference_vector TEXT NOT NULL,  -- JSON: latent vector
    learning_rate REAL DEFAULT 0.1,
    exploration_rate REAL DEFAULT 0.1,
    last_updated_timestamp INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

**Feedback Events Table**:
```sql
CREATE TABLE feedback_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    reward INTEGER NOT NULL,  -- -1, 0, or 1
    timestamp INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

CREATE INDEX idx_feedback_user ON feedback_events(user_id);
CREATE INDEX idx_feedback_skill ON feedback_events(skill_id);
```

### Python Data Classes (`shared/aico/ai/memory/procedural.py`)

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class Skill(BaseModel):
    skill_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    skill_name: str
    skill_type: str = "learned"  # 'base', 'learned', 'user_created'
    trigger_context: Dict[str, Any] = {}
    procedure_template: str
    confidence_score: float = 0.5
    preference_profile: Optional[list[float]] = None
    usage_count: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    last_used_timestamp: Optional[datetime] = None
    created_timestamp: datetime = Field(default_factory=datetime.utcnow)
    updated_timestamp: datetime = Field(default_factory=datetime.utcnow)

class UserPreferences(BaseModel):
    user_id: str
    preference_vector: list[float]
    learning_rate: float = 0.1
    exploration_rate: float = 0.1
    last_updated_timestamp: datetime = Field(default_factory=datetime.utcnow)

class FeedbackEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    message_id: str
    skill_id: str
    reward: int  # -1, 0, or 1
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

---

## Implementation Strategy

The procedural memory system will be implemented as a complete, integrated solution with all components working together from the start. This approach ensures consistency and avoids technical debt from incremental builds.

### Core Implementation Components

**1. Data Layer**
- Database schema for `skills`, `user_preferences`, and `feedback_events` tables
- ChromaDB collection for skill embeddings (`procedural_skills`)
- Python data classes (`Skill`, `UserPreferences`, `FeedbackEvent`)
- `SkillStore` class with CRUD operations and vector search integration

**2. Learning System**
- Real-time feedback processing via `POST /api/v1/memory/feedback` endpoint
- Confidence score updates using weighted learning
- User preference vector management with embedding-based updates
- Trajectory logging for successful/unsuccessful interactions

**3. Skill Selection Engine**
- Context extraction using existing NLP models (intent, entities, sentiment)
- Hybrid skill matching: confidence score + preference alignment
- ChromaDB vector search for similar skills
- Exploration strategy (ε-greedy) for discovering new patterns

**4. DPO Template Refinement Pipeline**
- Offline batch process (scheduled task, runs daily)
- Trajectory dataset preparation (preferred vs. dispreferred pairs)
- DPO-based template generation using TRL library
- Skill template updates in database (no model training)
- Performance metrics logging

**5. Integration Points**
- `ConversationEngine`: Apply selected skills during response generation
- `ContextAssembly`: Inject skill guidance into LLM prompts
- Frontend: Feedback UI components in message views
- Logging: Track all skill applications and feedback events

**6. Foundational Skills**
- 10-15 base skills covering common interaction patterns:
  - `concise_response`: Brief, bullet-point answers
  - `detailed_explanation`: In-depth explanations with examples
  - `casual_chat`: Informal, conversational tone
  - `technical_precision`: Formal, precise language for technical topics
  - `empathy_direct`: Explicit empathetic statements
  - `empathy_subtle`: Supportive actions without emotional statements
  - `proactive_suggestions`: Offer next steps and recommendations
  - `reactive_only`: Wait for explicit user requests
  - `code_review_constructive`: Polite, constructive code feedback
  - `summarize_key_points`: Extract and highlight main ideas

### Implementation Order

**Weeks 1-2**: Database schema, SkillStore, ChromaDB collection, base skills  
**Weeks 3-4**: Feedback API, UI components, confidence updates, skill selection  
**Weeks 5-6**: Preference vectors, context extraction, trajectory logging  
**Weeks 7-8**: DPO pipeline, exploration strategy, metrics dashboard

### Success Criteria

**Functional Requirements**:
- ✅ Users can provide feedback on AI responses
- ✅ Skill confidence scores update based on feedback
- ✅ System learns distinct preferences for different users
- ✅ ConversationEngine applies appropriate skills based on context
- ✅ New users receive personalized interactions within 5-10 exchanges
- ✅ Skill library grows organically through learning

**Performance Requirements**:
- ✅ Skill selection latency: <10ms
- ✅ Feedback processing: <5ms
- ✅ Context extraction: <30ms (reuses existing NLP pipeline)
- ✅ No additional memory overhead (reuses existing models)

**Quality Requirements**:
- ✅ Skill accuracy: >70% positive feedback rate
- ✅ User satisfaction: Measurable improvement over baseline
- ✅ System stability: No degradation in response quality
- ✅ Privacy: All data stored locally, encrypted at rest

---

## Technology Stack & Dependencies

This section details all AI models, libraries, and technologies required to implement the procedural memory system. **We maximize reuse of existing AICO infrastructure** to minimize dependencies and maintain consistency.

### Core AI & Machine Learning

#### 1. **Embedding Models** (for Preference Vector Similarity)

**Purpose**: Generate and compare user preference vectors for skill matching.

**Model**: **REUSE EXISTING** - `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- Already configured in `core.yaml` at `modelservice.transformers.models.embeddings`
- Already managed by `TransformersManager` in modelservice
- 768 dimensions (same as semantic memory for consistency)
- Multilingual support
- Already loaded in memory for semantic memory operations

**Why Reuse**: This model is already running for semantic memory. Using the same model for preference vectors:
- Eliminates additional memory overhead (~500MB saved)
- Ensures consistency across memory systems
- Leverages existing model management infrastructure
- No additional downloads or configuration needed

**Implementation**:
```python
from modelservice.core.transformers_manager import TransformersManager

# Use existing TransformersManager instance
embeddings_model = transformers_manager.get_model("embeddings")
preference_embedding = embeddings_model.encode(user_preference_description)
```

#### 2. **Reinforcement Learning Framework**

**Purpose**: Implement RLHF feedback loops with DPO (Direct Preference Optimization).

**Library**: **TRL (Transformer Reinforcement Learning)** by Hugging Face
- Provides production-ready DPO implementation
- Use case: Refine prompt templates based on successful vs. unsuccessful trajectories
- Runs offline as scheduled task (daily)
- Library: `trl>=0.7.0` (add to `pyproject.toml` under `[project.optional-dependencies.backend]`)

**Clarification**: DPO refines **prompt templates** (not model weights). Analyzes feedback trajectories to generate improved templates. Runs offline daily, fully reversible, storage-efficient.

**Implementation** (`backend/scheduler/tasks/dpo_refinement.py`):
```python
"""
DPO Template Refinement Task

Scheduled task that refines procedural memory skill templates using
Direct Preference Optimization (DPO) based on user feedback trajectories.

Follows AICO's message-driven architecture and privacy-by-design principles.
"""

from trl import DPOTrainer, DPOConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from aico.ai.memory.procedural import SkillStore, TrajectoryStore
from aico.core.logging import get_logger

logger = get_logger("backend", "scheduler.dpo_refinement")

async def refine_skill_templates():
    """
    Refine prompt templates using DPO based on user feedback trajectories.
    
    This task runs daily as a scheduled job. It analyzes recent user feedback
    to generate improved prompt templates that maximize user satisfaction.
    
    Privacy: All data is local and encrypted. No external API calls.
    """
    
    # Load trajectories from last 24 hours
    trajectory_store = TrajectoryStore()
    trajectories = await trajectory_store.get_recent_trajectories(hours=24)
    
    if len(trajectories) < 10:  # Need minimum data
        logger.info("Insufficient trajectories for DPO refinement")
        return
    
    # Prepare preference pairs
    preferred = [t for t in trajectories if t.feedback_reward > 0]
    dispreferred = [t for t in trajectories if t.feedback_reward < 0]
    
    # Use DPO to generate improved prompt templates
    # (This uses the model to analyze patterns, not to train it)
    improved_templates = await generate_improved_templates(
        preferred_examples=preferred,
        dispreferred_examples=dispreferred
    )
    
    # Update skill templates in database
    skill_store = SkillStore()
    for skill_id, new_template in improved_templates.items():
        await skill_store.update_skill_template(skill_id, new_template)
    
    logger.info(
        "DPO template refinement completed",
        extra={
            "trajectories_analyzed": len(trajectories),
            "templates_updated": len(improved_templates),
            "metric_type": "procedural_memory_dpo"
        }
    )
```

#### 3. **Meta-Learning Framework**

**Purpose**: Implement rapid adaptation to new users with minimal data.

**Approach**: **Lightweight custom implementation** using existing infrastructure
- Store user-specific preference vectors (768-dim, matching embedding model)
- Use cosine similarity for preference alignment
- No separate neural network needed - leverage existing embedding space

**Why Lightweight**: Uses preference vectors (768-dim) + text templates instead of neural network training. Simple vector math, <10ms selection, interpretable, ~10-50KB per user.

**Implementation** (`aico/ai/memory/procedural/preferences.py`):
```python
"""
User Preference Management

Manages user-specific preference vectors in embedding space for rapid
adaptation and personalization. Part of AICO's procedural memory system.

Follows AICO's privacy-by-design: all data stored locally and encrypted.
"""

import numpy as np
from scipy.spatial.distance import cosine
from aico.core.logging import get_logger

logger = get_logger("backend", "memory.procedural.preferences")

class UserPreferenceManager:
    """
    Manages user preference vectors for procedural memory personalization.
    
    Preference vectors are stored in the same 768-dimensional space as the
    embedding model, enabling fast similarity-based skill matching.
    
    Attributes:
        embedding_dim: Dimension of preference vectors (must match embedding model)
    """
    
    def __init__(self, embedding_dim=768):
        self.embedding_dim = embedding_dim
        
    def initialize_user_preferences(self, user_id: str) -> np.ndarray:
        """Initialize with neutral preference vector."""
        return np.zeros(self.embedding_dim)
    
    def update_preferences(self, user_prefs: np.ndarray, 
                          skill_embedding: np.ndarray, 
                          reward: float, 
                          learning_rate: float = 0.1) -> np.ndarray:
        """Update user preferences based on feedback."""
        # Move preference vector toward/away from skill embedding
        update = learning_rate * reward * skill_embedding
        new_prefs = user_prefs + update
        # Normalize to unit vector
        return new_prefs / (np.linalg.norm(new_prefs) + 1e-8)
    
    def compute_preference_alignment(self, user_prefs: np.ndarray, 
                                     skill_embedding: np.ndarray) -> float:
        """Compute how well a skill aligns with user preferences."""
        return 1 - cosine(user_prefs, skill_embedding)
```

### Data Storage & Retrieval

#### 4. **Database: libSQL (SQLite with Extensions)**

**Purpose**: Store skills, preferences, and feedback events.

**Library**: **REUSE EXISTING** - `libsql-client` (Python)
- Already used throughout AICO for encrypted local storage
- Supports JSON columns for flexible schema (trigger_context, preference_vector)
- Full-text search capabilities for skill descriptions
- Encryption at rest (already configured)

**Schema Features**:
- JSON storage for complex fields (trigger_context, preference_profile)
- Indexes for fast user-based and confidence-based queries
- Foreign key constraints for data integrity

#### 5. **Vector Similarity Search**

**Purpose**: Fast nearest-neighbor search for skill matching.

**Library**: **REUSE EXISTING** - **ChromaDB**
- Already configured in `core.yaml` for semantic memory at `memory.semantic`
- Already running for conversation segment retrieval
- Use case: Store skill embeddings for fast similarity-based retrieval
- Advantages: Local-first, persistent, optimized for similarity search
- Library: `chromadb` (Python)

**Why Reuse**: ChromaDB is already managing conversation embeddings. We can add a new collection for skill embeddings:
- Reuses existing ChromaDB instance (no additional process)
- Consistent vector search across memory systems
- Optimized for similarity queries (faster than NumPy for >100 skills)
- Already integrated with the embedding model

**Implementation**:
```python
# Add new collection to existing ChromaDB instance
skill_collection = chroma_client.create_collection(
    name="procedural_skills",
    embedding_function=embeddings_model,  # Reuse existing embedding model
    metadata={"hnsw:space": "cosine"}
)

# Query similar skills
results = skill_collection.query(
    query_texts=[user_preference_description],
    n_results=10,
    where={"user_id": user_id}
)
```

### Natural Language Processing

#### 6. **Intent Classification & Context Analysis**

**Purpose**: Extract trigger context from conversations (intent, entities, topics).

**Model**: **REUSE EXISTING** - `xlm-roberta-base`
- Already configured in `core.yaml` at `modelservice.transformers.models.intent_classification`
- Already managed by `TransformersManager`
- Multilingual support (matches AICO's multilingual design)
- Use case: Classify user intent to determine appropriate skill category

**Entity Extraction**: **REUSE EXISTING** - `urchade/gliner_medium-v2.1`
- Already configured in `core.yaml` at `modelservice.transformers.models.entity_extraction`
- Already managed by `TransformersManager`
- Generalist entity extraction (can extract any entity type)
- Use case: Extract topics, subjects, and context from conversations

**Implementation**:
```python
from modelservice.core.transformers_manager import TransformersManager

# Use existing models
intent_model = transformers_manager.get_model("intent_classification")
entity_model = transformers_manager.get_model("entity_extraction")

def extract_context(text: str) -> dict:
    # Extract intent
    intent = intent_model.classify(text)
    
    # Extract entities (topics, subjects)
    entities = entity_model.extract(text, labels=["topic", "subject", "activity"])
    
    return {
        "intent": intent,
        "entities": entities,
        "time_of_day": get_time_of_day()
    }
```

#### 7. **Sentiment Analysis** (for Emotional Context)

**Purpose**: Detect user sentiment to inform skill selection.

**Model**: **REUSE EXISTING** - `nlptown/bert-base-multilingual-uncased-sentiment`
- Already configured in `core.yaml` at `modelservice.transformers.models.sentiment_multilingual`
- Already managed by `TransformersManager` (priority 1, required)
- Multilingual support
- Use case: Determine if user is frustrated, happy, neutral to select appropriate interaction style

**Alternative** (if more nuanced emotion detection needed):
- `cardiffnlp/twitter-roberta-base-sentiment-latest` (already in DEFAULT_MODELS as `sentiment_english`)
- `j-hartmann/emotion-english-distilroberta-base` (already in DEFAULT_MODELS as `emotion_analysis`)

**Implementation**:
```python
from modelservice.core.transformers_manager import TransformersManager

# Use existing sentiment model
sentiment_model = transformers_manager.get_model("sentiment_multilingual")

def detect_sentiment(text: str) -> str:
    result = sentiment_model(text)
    return result[0]['label']  # e.g., "positive", "negative", "neutral"
```

### Utilities & Supporting Libraries

#### 8. **Data Validation & Serialization**

**Library**: **REUSE EXISTING** - **Pydantic** (v2.0+)
- Already used throughout AICO for data validation
- Use case: Validate skill data, API payloads, database models
- Advantages: Type safety, automatic validation, JSON serialization

#### 9. **Numerical Computing**

**Libraries**: **REUSE EXISTING**
- **NumPy**: Already a dependency, use for array operations, vector math, confidence score updates
- **SciPy**: Already a dependency, use for cosine similarity, statistical functions

#### 10. **Logging & Monitoring**

**Infrastructure**: **REUSE EXISTING** - AICO's unified logging system
- Already configured in `core.yaml` at `logging`
- ZeroMQ message bus for log transport
- Use case: Track skill applications, feedback events, learning metrics
- Subsystem: Add `procedural_memory` to logging configuration

**Implementation**:
```python
from shared.aico.core.logging import get_logger

logger = get_logger("backend", "procedural_memory")
logger.info("Skill applied", extra={
    "skill_id": skill.skill_id,
    "user_id": user_id,
    "confidence": skill.confidence_score
})
```

### Frontend Integration

#### 11. **Flutter/Dart Libraries**

**Purpose**: Capture and send user feedback from the mobile/desktop UI.

**Frontend Requirements**:
- Use existing HTTP client (http/dio) to send feedback to `POST /api/v1/memory/feedback`
- Integrate thumbs up/down buttons into message UI components
- Maintain message_id and skill_id association for feedback submission

### Development & Testing

#### 12. **Testing Frameworks**

**Libraries**: **REUSE EXISTING**
- **pytest**: Already used for AICO backend tests
- **pytest-asyncio**: Already used for async endpoint tests
- **pytest-mock**: For mocking message bus and database interactions
- Use case: Unit tests for skill selection, preference updates, feedback processing

**Test Structure** (following AICO patterns):
```
tests/
├── unit/
│   ├── memory/
│   │   ├── test_skill_store.py
│   │   ├── test_preference_manager.py
│   │   └── test_confidence_updates.py
│   └── api/
│       └── test_memory_router.py
├── integration/
│   ├── test_feedback_flow.py
│   └── test_skill_selection.py
└── fixtures/
    ├── skills.py
    └── trajectories.py
```

**Example Tests** (see `tests/unit/memory/test_skill_store.py`):
```python
import pytest
from aico.ai.memory.procedural import Skill, update_skill_confidence

def test_positive_feedback_increases_confidence():
    skill = Skill(user_id="test", skill_name="concise", 
                  procedure_template="Be brief.", confidence_score=0.5)
    updated = update_skill_confidence(skill, reward=1, learning_rate=0.1)
    assert updated.confidence_score == 0.6

@pytest.mark.asyncio
async def test_feedback_endpoint(test_client, mock_bus_client):
    response = await test_client.post("/api/v1/memory/feedback",
        json={"message_id": "msg_123", "skill_id": "skill_456", "reward": 1})
    assert response.status_code == 200
    mock_bus_client.publish.assert_called_once()
```

### Configuration Management

#### 13. **Configuration**

**System**: **REUSE EXISTING** - Add to `config/defaults/core.yaml` under the `memory:` section

**Location**: After `memory.semantic.knowledge_graph` (around line 342), add:

```yaml
memory:
  # ... existing working and semantic config ...
  
  # Procedural Memory - Adaptive interaction learning
  procedural:
    enabled: true
    
    # Learning parameters
    learning_rate: 0.1  # How quickly confidence scores adjust to feedback
    exploration_rate: 0.1  # Probability of trying lower-confidence skills
    
    # Skill management
    max_skills_per_user: 100  # Maximum learned skills per user
    skill_selection_timeout_ms: 10  # Max time for skill selection
    min_confidence_threshold: 0.3  # Don't use skills below this confidence
    
    # Preference vectors (must match embedding model dimensions)
    preference_vector_dim: 768  # Matches paraphrase-multilingual-mpnet-base-v2
    
    # Feedback collection
    feedback:
      require_thumbs: true  # Thumbs up/down required
      enable_reason_dropdown: true  # Optional structured reason
      enable_free_text: true  # Optional free text explanation
      free_text_max_chars: 300
      
      # Dropdown options for structured feedback
      reason_options:
        - too_verbose
        - too_brief
        - wrong_tone
        - not_helpful
        - incorrect_info
        - perfect  # For positive feedback
    
    # DPO template refinement (offline batch process)
    dpo:
      enabled: true
      batch_size: 4
      learning_rate: 5e-7
      beta: 0.1  # KL penalty coefficient
      max_length: 512
      training_interval_hours: 24  # Run template refinement daily
      min_trajectories: 10  # Minimum trajectories needed to run refinement
    
    # Trajectory logging for learning
    trajectory_logging:
      enabled: true
      max_trajectory_length: 20  # Number of turns to store per trajectory
      retention_days: 90  # Keep trajectories for 3 months
    
    # ChromaDB collection for skill embeddings
    chroma:
      collection_name: "procedural_skills"  # Separate collection from conversation_segments
      distance_metric: "cosine"  # Same as semantic memory
    
    # Performance monitoring
    metrics:
      log_skill_selection: true  # Log every skill selection with timing
      log_feedback_events: true  # Log all user feedback
      log_confidence_changes: true  # Track confidence score evolution
      aggregate_interval_minutes: 60  # Aggregate metrics every hour
```

### Protocol Buffer Schemas

**New File**: `proto/aico_memory.proto` with messages:
- `FeedbackEvent`: user_id, message_id, skill_id, reward, reason, free_text, timestamp
- `SkillSelectionRequest`: user_id, conversation_id, message_text, context_tags, timestamp
- `SkillSelectionResponse`: request_id, skill_id, skill_name, procedure_template, confidence_score, preference_alignment, is_exploration, selection_time_ms
- `SkillApplicationEvent`: user_id, message_id, skill_id, skill_name, confidence_score, timestamp

**Topics**: `memory/procedural/{feedback,skill_request,skill_response,skill_applied}/v1`

### Complete Technology Stack Summary

**All components leverage existing AICO infrastructure:**

| Component | Technology | Status | Purpose |
|-----------|-----------|--------|---------|
| **Embeddings** | `paraphrase-multilingual-mpnet-base-v2` | ✅ Existing | Preference vectors, skill embeddings |
| **Intent Classification** | `xlm-roberta-base` | ✅ Existing | Context extraction |
| **Entity Extraction** | `gliner_medium-v2.1` | ✅ Existing | Topic/subject detection |
| **Sentiment Analysis** | `bert-base-multilingual-uncased-sentiment` | ✅ Existing | Emotional context |
| **Vector Store** | ChromaDB | ✅ Existing | Skill similarity search |
| **Database** | libSQL | ✅ Existing | Skill/preference storage |
| **RLHF/DPO** | TRL (Hugging Face) | ➕ New | Preference optimization |
| **Logging** | ZeroMQ message bus | ✅ Existing | Unified logging |
| **Config** | YAML | ✅ Existing | Configuration management |
| **Validation** | Pydantic v2 | ✅ Existing | Data validation |
| **Numerical** | NumPy, SciPy | ✅ Existing | Vector operations |
| **Frontend** | Flutter/Dart | ✅ Existing | Feedback UI |
| **Testing** | pytest | ✅ Existing | Unit/integration tests |

### New Dependencies

**Only ONE new dependency required:**

**Add to `pyproject.toml`** under `[project.optional-dependencies.backend]`:
```toml
[project.optional-dependencies]
backend = [
    "duckdb>=1.3.2",
    "fastapi>=0.116.1",
    "httpx>=0.28.1",
    "libsql==0.1.8",
    "pydantic>=2.11.7",
    "pyjwt>=2.10.1",
    "uvicorn>=0.35.0",
    "trl>=0.7.0",  # ADD THIS: Transformer Reinforcement Learning for DPO template refinement
]
```

**Installation with UV**:
```bash
# Install backend dependencies including procedural memory
uv pip install -e ".[backend]"

# Or install all optional dependencies
uv pip install -e ".[backend,modelservice,cli,test]"
```

**All other dependencies are already present in AICO.**

### Resource Requirements

**Disk Space**:
- No additional models to download (all models already in use)
- Per-user skill storage: <1MB (target: 100 skills × ~10KB each)
- Trajectory logs: ~5-10MB per user per month

**Memory**:
- No additional runtime memory (reusing existing models)
- DPO training (offline): ~2-4GB during batch training (runs daily, not real-time)

**Compute**:
- Skill selection: <10ms (vector similarity lookup in ChromaDB)
- Context extraction: ~20-30ms (already happening for conversations)
- Feedback processing: <5ms (simple confidence update)
- DPO training: Runs offline as scheduled task (not user-facing)

**All operations run locally on CPU; no GPU required.**

---

## Privacy & Security Considerations

**AICO's procedural memory system follows strict privacy-by-design principles:**

### Local-First Architecture
- **All data stored locally**: Skills, preferences, and trajectories stored in encrypted libSQL database
- **No cloud dependencies**: System operates entirely on-device
- **Encrypted at rest**: SQLCipher encryption for all procedural memory data
- **Secure key management**: Uses AICO's key derivation system (`aico.security.AICOKeyManager`)

### User Control & Transparency
- **Explicit opt-in**: Users must enable procedural learning (disabled by default)
- **Full visibility**: Users can view all learned skills and preferences via UI
- **Edit capabilities**: Users can modify or delete any learned skill
- **Explanation system**: UI shows why each skill was applied (confidence score, preference alignment)
- **Disable anytime**: Users can turn off procedural learning without data loss

### Data Governance & Compliance
- **No external sharing**: Data never leaves device, no telemetry
- **User export**: JSON format for full data portability
- **Audit logging**: All skill applications logged for review
- **Message bus security**: CurveZMQ encryption, topic isolation, access control
- **GDPR-ready**: Full access, modify, delete, export rights
- **Privacy-preserving**: DPO uses aggregated patterns, not raw messages

---

## Performance Metrics & Monitoring

The system logs comprehensive metrics to track learning effectiveness and system performance over time. All metrics are logged via AICO's unified logging system with `metric_type` tags for easy filtering and aggregation.

### Learning Effectiveness Metrics

**Logged on every feedback event** (`metric_type: "procedural_memory_feedback"`):
```python
logger.info("Skill feedback received", extra={
    "user_id": user_id,
    "skill_id": skill_id,
    "skill_name": skill.skill_name,
    "reward": reward,  # 1, 0, or -1
    "reason": reason,  # Dropdown selection
    "old_confidence": old_confidence,
    "new_confidence": new_confidence,
    "confidence_delta": new_confidence - old_confidence,
    "total_usage": skill.usage_count,
    "positive_rate": skill.positive_feedback_count / skill.usage_count,
    "negative_rate": skill.negative_feedback_count / skill.usage_count,
    "has_free_text": bool(free_text),
    "metric_type": "procedural_memory_feedback"
})
```

**Aggregated hourly** (`metric_type: "procedural_memory_aggregate"`):
- **Skill Accuracy**: Percentage of skills receiving positive feedback (target: >70%)
- **User Satisfaction**: Average reward per user (target: >0.5)
- **Adaptation Speed**: Number of interactions to reach 70% positive rate for new users (target: <10)
- **Skill Retention**: Confidence score stability over time (low variance = good)

### System Performance Metrics

**Logged on every skill selection** (`metric_type: "procedural_memory_selection"`):
```python
logger.info("Skill selected", extra={
    "user_id": user_id,
    "skill_id": selected_skill.skill_id,
    "skill_name": selected_skill.skill_name,
    "confidence_score": selected_skill.confidence_score,
    "preference_alignment": alignment_score,
    "selection_time_ms": selection_time_ms,  # Target: <10ms
    "context_extraction_time_ms": context_time_ms,  # Target: <30ms
    "total_candidates": len(candidate_skills),
    "exploration_mode": is_exploration,  # True if ε-greedy selected low-confidence skill
    "metric_type": "procedural_memory_selection"
})
```

**Aggregated hourly** (`metric_type: "procedural_memory_performance"`):
- **Response Time**: P50, P95, P99 skill selection latency (target: P95 <10ms)
- **Memory Usage**: Current skill storage per user (target: <1MB)
- **Processing Overhead**: Average skill selection time (target: <10ms)
- **Scalability**: Performance with increasing user count and skill library size

### DPO Template Refinement Metrics

**Logged after each batch refinement** (`metric_type: "procedural_memory_dpo"`):
```python
logger.info("DPO template refinement completed", extra={
    "trajectories_analyzed": len(trajectories),
    "preferred_count": len(preferred),
    "dispreferred_count": len(dispreferred),
    "templates_updated": len(improved_templates),
    "avg_confidence_improvement": avg_improvement,
    "refinement_duration_seconds": duration,
    "metric_type": "procedural_memory_dpo"
})
```

### Monitoring Dashboard Queries

**Example queries** (filter by `metric_type` in logs):
- **Skill accuracy**: `AVG(CASE WHEN reward > 0 THEN 1.0 ELSE 0.0 END)` grouped by hour
- **Slow skills**: Skills with `AVG(selection_time_ms) > 10ms`
- **User adaptation**: Positive rate over time per user
- **Exploration effectiveness**: Compare confidence scores for explored vs. exploited skills

### Success Criteria

**Learning Effectiveness**:
- ✅ **Skill Accuracy**: >70% positive feedback rate across all skills
- ✅ **User Satisfaction**: Average reward >0.5 per user
- ✅ **Adaptation Speed**: New users reach 70% positive rate within 10 interactions
- ✅ **Skill Retention**: Confidence scores remain stable (variance <0.1) after 50 uses

**System Performance**:
- ✅ **Response Time**: P95 skill selection latency <10ms
- ✅ **Memory Usage**: <1MB storage per user (100 skills × 10KB)
- ✅ **Processing Overhead**: <30ms total (context extraction + skill selection)
- ✅ **Scalability**: Linear performance up to 1000 users, 100 skills each

---

## Appendix: Foundational Research

The architecture described in this document is inspired by several key research papers in the fields of AI agency, reinforcement learning, and meta-learning.

- **Modular AI Architecture**:
  - [Procedural Memory Is Not All You Need: Bridging Cognitive Gaps in LLM-Based Agents](https://arxiv.org/abs/2505.03434)
  - This paper advocates for augmenting LLMs with modular semantic and associative memory systems, which inspires our skill-based architecture.

- **Personalized Reinforcement Learning**:
  - [Personalizing Reinforcement Learning from Human Feedback with Variational Preference Learning](https://arxiv.org/abs/2408.10075)
  - This work provides the foundation for our multi-user personalization, using latent variables to model diverse user preferences.

- **Meta-Learning for Fast Adaptation**:
  - [Fast Context Adaptation via Meta-Learning (CAVIA)](https://arxiv.org/abs/1810.03642)
  - This paper's approach to partitioning model parameters informs our strategy for rapid adaptation to new users with minimal data.

- **Agent Self-Correction**:
  - [Agent Q: Advanced Reasoning and Learning for Autonomous AI Agents](https://arxiv.org/abs/2408.07199)
  - This research inspires our self-correction and exploration mechanism, particularly the use of preference optimization (like DPO) to learn from both successful and unsuccessful interactions.
