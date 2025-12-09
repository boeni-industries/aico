"""
Goal Arbiter - Central Decision-Making for Agency

Collects, scores, ranks, and filters goal candidates from various sources.
Maintains the "active intention set" and publishes changes to the message bus.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from aico.data.libsql import EncryptedLibSQLConnection
from aico.core.bus import MessageBusClient

from .models import Goal, GoalStatus, GoalOrigin, GoalPriority


# ============================================================================
# Enums
# ============================================================================

class IntentionStatus(str, Enum):
    """Status of an intention in the active set."""
    PROPOSED = "proposed"
    ACTIVE = "active"
    PAUSED = "paused"
    DROPPED = "dropped"
    COMPLETED = "completed"


class PriorityBand(str, Enum):
    """Priority bands for intention scheduling."""
    URGENT = "urgent"
    NORMAL = "normal"
    BACKGROUND = "background"


# ============================================================================
# Data Models
# ============================================================================

class ScoredGoal(BaseModel):
    """Goal with arbiter scoring information."""
    
    goal: Goal
    arbiter_score: float
    priority_band: PriorityBand
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    reasons: List[str] = Field(default_factory=list)


class Intention(BaseModel):
    """Active intention in the intention set."""
    
    intention_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str
    user_id: str
    status: IntentionStatus = IntentionStatus.PROPOSED
    arbiter_score: float
    priority_band: PriorityBand
    reasons: List[str] = Field(default_factory=list)
    activated_at: Optional[datetime] = None
    deactivated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IntentionSet(BaseModel):
    """The active intention set - goals currently being pursued."""
    
    user_id: str
    intentions: List[Intention] = Field(default_factory=list)
    max_active: int = 3
    max_background: int = 5
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def active_intentions(self) -> List[Intention]:
        """Get currently active intentions."""
        return [i for i in self.intentions if i.status == IntentionStatus.ACTIVE]
    
    @property
    def proposed_intentions(self) -> List[Intention]:
        """Get proposed intentions awaiting activation."""
        return [i for i in self.intentions if i.status == IntentionStatus.PROPOSED]


# ============================================================================
# Goal Arbiter Service
# ============================================================================

class GoalArbiter:
    """
    Central decision-making component for agency.
    
    Responsibilities:
    - Score and rank goal candidates
    - Maintain active intention set
    - Balance user goals, curiosity, hobbies, and maintenance
    - Consider personality, emotion, values, and system load
    - Publish intention set changes to message bus
    """
    
    def __init__(
        self,
        db: EncryptedLibSQLConnection,
        config=None,
        message_bus: Optional[MessageBusClient] = None,
        logger=None
    ):
        self.db = db
        self.message_bus = message_bus
        self.logger = logger
        self.config = config
        
        # Load scoring weights from config with validation
        if config:
            try:
                print("🔧 [ARBITER DEBUG] Loading scoring weights from config...")
                weights_config = config.get("core.services.agency.arbiter.scoring_weights", {})
                print(f"🔧 [ARBITER DEBUG] Weights config: {weights_config}")
                
                if not weights_config:
                    raise ValueError("core.services.agency.arbiter.scoring_weights not found in configuration")
                
                self.weights = {
                    "priority": float(weights_config.get("priority", 0.30)),
                    "origin": float(weights_config.get("origin", 0.20)),
                    "freshness": float(weights_config.get("freshness", 0.15)),
                    "curiosity_score": float(weights_config.get("curiosity_score", 0.15)),
                    "personality_fit": float(weights_config.get("personality_fit", 0.10)),
                    "emotion_boost": float(weights_config.get("emotion_boost", 0.10)),
                }
                
                print(f"🔧 [ARBITER DEBUG] Loaded weights: {self.weights}")
                
                # Validate weights sum to approximately 1.0
                total_weight = sum(self.weights.values())
                print(f"🔧 [ARBITER DEBUG] Total weight: {total_weight:.3f}")
                
                if abs(total_weight - 1.0) > 0.01:
                    raise ValueError(
                        f"Arbiter scoring weights must sum to ~1.0, got {total_weight:.3f}. "
                        f"Check core.services.agency.arbiter.scoring_weights in configuration."
                    )
                
                print("✅ [ARBITER DEBUG] Scoring weights validated successfully!")
                if logger:
                    logger.info(f"[ARBITER] Loaded scoring weights from config: {self.weights}")
            except Exception as e:
                error_msg = f"Failed to load arbiter configuration: {e}"
                if logger:
                    logger.error(f"[ARBITER] {error_msg}")
                raise RuntimeError(error_msg)
        else:
            # Fallback defaults (should not happen in production)
            self.weights = {
                "priority": 0.30,
                "origin": 0.20,
                "freshness": 0.15,
                "curiosity_score": 0.15,
                "personality_fit": 0.10,
                "emotion_boost": 0.10,
            }
            if logger:
                logger.warning("[ARBITER] No config provided, using default scoring weights")
        
        # Origin priority scores (fixed, not configurable)
        self.origin_scores = {
            GoalOrigin.USER: 1.0,
            GoalOrigin.CURIOSITY: 0.7,
            GoalOrigin.HOBBY: 0.6,
            GoalOrigin.MAINTENANCE: 0.5,
            GoalOrigin.SYSTEM: 0.4,
        }
    
    # ========================================================================
    # Scoring & Ranking
    # ========================================================================
    
    def score_goal(
        self,
        goal: Goal,
        context: Optional[Dict[str, Any]] = None
    ) -> ScoredGoal:
        """
        Score a goal candidate using weighted factors.
        
        Args:
            goal: Goal to score
            context: Optional context (personality, emotion, system load)
            
        Returns:
            ScoredGoal with score and breakdown
        """
        context = context or {}
        breakdown = {}
        
        # 1. Priority score (0.0-1.0)
        priority_map = {
            GoalPriority.HIGH: 1.0,
            GoalPriority.NORMAL: 0.6,
            GoalPriority.LOW: 0.3,
        }
        priority_score = priority_map.get(goal.priority, 0.6)
        breakdown["priority"] = priority_score * self.weights["priority"]
        
        # 2. Origin score
        origin_score = self.origin_scores.get(goal.origin, 0.5)
        breakdown["origin"] = origin_score * self.weights["origin"]
        
        # 3. Freshness score (newer goals score higher)
        age_hours = (datetime.utcnow() - goal.created_at).total_seconds() / 3600
        freshness_score = max(0.0, 1.0 - (age_hours / 168))  # Decay over 1 week
        breakdown["freshness"] = freshness_score * self.weights["freshness"]
        
        # 4. Curiosity score (if from curiosity engine)
        curiosity_score = 0.0
        if goal.origin in [GoalOrigin.CURIOSITY, GoalOrigin.HOBBY]:
            curiosity_score = goal.metadata.get("curiosity_score", 0.5)
        breakdown["curiosity_score"] = curiosity_score * self.weights["curiosity_score"]
        
        # 5. Personality fit (Phase 2+)
        personality_fit = context.get("personality_fit", 0.5)
        breakdown["personality_fit"] = personality_fit * self.weights["personality_fit"]
        
        # 6. Emotion boost (Phase 2+)
        emotion_boost = context.get("emotion_boost", 0.5)
        breakdown["emotion_boost"] = emotion_boost * self.weights["emotion_boost"]
        
        # Calculate total score
        total_score = sum(breakdown.values())
        
        # Determine priority band
        if total_score >= 0.7:
            priority_band = PriorityBand.URGENT
        elif total_score >= 0.4:
            priority_band = PriorityBand.NORMAL
        else:
            priority_band = PriorityBand.BACKGROUND
        
        # Build reasons
        reasons = []
        if goal.priority == GoalPriority.HIGH:
            reasons.append("high_priority")
        if goal.origin == GoalOrigin.USER:
            reasons.append("user_requested")
        if curiosity_score > 0.7:
            reasons.append("high_curiosity")
        if freshness_score > 0.8:
            reasons.append("recently_created")
        
        if self.logger:
            self.logger.debug(
                f"[ARBITER] Scored goal {goal.goal_id}: {total_score:.3f} "
                f"({priority_band.value}) - {goal.title}"
            )
        
        return ScoredGoal(
            goal=goal,
            arbiter_score=total_score,
            priority_band=priority_band,
            score_breakdown=breakdown,
            reasons=reasons
        )
    
    def rank_goals(
        self,
        goals: List[Goal],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ScoredGoal]:
        """
        Score and rank a list of goals.
        
        Args:
            goals: Goals to rank
            context: Optional context for scoring
            
        Returns:
            List of ScoredGoal sorted by score (highest first)
        """
        scored_goals = [self.score_goal(goal, context) for goal in goals]
        scored_goals.sort(key=lambda sg: sg.arbiter_score, reverse=True)
        
        if self.logger:
            self.logger.info(
                f"[ARBITER] Ranked {len(scored_goals)} goals, "
                f"top score: {scored_goals[0].arbiter_score:.3f}" if scored_goals else "no goals"
            )
        
        return scored_goals
    
    # ========================================================================
    # Intention Set Management
    # ========================================================================
    
    async def get_intention_set(self, user_id: str) -> IntentionSet:
        """
        Get the current intention set for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            IntentionSet with current intentions
        """
        rows = self.db.fetch_all(
            """
            SELECT * FROM intention_set 
            WHERE user_id = ? AND status IN ('proposed', 'active', 'paused')
            ORDER BY arbiter_score DESC
            """,
            (user_id,)
        )
        
        intentions = []
        for row in rows:
            intentions.append(Intention(
                intention_id=row["intention_id"],
                goal_id=row["goal_id"],
                user_id=row["user_id"],
                status=IntentionStatus(row["status"]),
                arbiter_score=row["arbiter_score"],
                priority_band=PriorityBand(row["priority_band"]),
                reasons=json.loads(row["reasons_json"] or "[]"),
                activated_at=datetime.fromisoformat(row["activated_at"]) if row["activated_at"] else None,
                deactivated_at=datetime.fromisoformat(row["deactivated_at"]) if row["deactivated_at"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            ))
        
        return IntentionSet(user_id=user_id, intentions=intentions)
    
    async def update_intention_set(
        self,
        user_id: str,
        candidate_goals: List[Goal],
        context: Optional[Dict[str, Any]] = None
    ) -> IntentionSet:
        """
        Update the intention set with new goal candidates.
        
        This is the main arbiter operation:
        1. Score and rank all candidate goals
        2. Get current intention set
        3. Decide which goals to activate/deactivate
        4. Update database and publish changes
        
        Args:
            user_id: User ID
            candidate_goals: New goal candidates to consider
            context: Optional context for scoring
            
        Returns:
            Updated IntentionSet
        """
        # Get current intention set
        intention_set = await self.get_intention_set(user_id)
        
        # Score and rank candidates
        scored_candidates = self.rank_goals(candidate_goals, context)
        
        # Determine which goals to activate
        new_intentions = []
        active_count = len(intention_set.active_intentions)
        
        for scored_goal in scored_candidates:
            # Check if already in intention set
            existing = next(
                (i for i in intention_set.intentions if i.goal_id == scored_goal.goal.goal_id),
                None
            )
            
            if existing:
                # Update score if changed significantly
                if abs(existing.arbiter_score - scored_goal.arbiter_score) > 0.1:
                    existing.arbiter_score = scored_goal.arbiter_score
                    existing.priority_band = scored_goal.priority_band
                    existing.updated_at = datetime.utcnow()
                    await self._update_intention(existing)
                continue
            
            # Add new intention if we have capacity
            if scored_goal.priority_band == PriorityBand.URGENT:
                # Urgent goals always get added
                intention = await self._create_intention(scored_goal, user_id)
                new_intentions.append(intention)
            elif scored_goal.priority_band == PriorityBand.NORMAL and active_count < intention_set.max_active:
                intention = await self._create_intention(scored_goal, user_id)
                new_intentions.append(intention)
                active_count += 1
            elif scored_goal.priority_band == PriorityBand.BACKGROUND:
                # Background goals are proposed but not activated
                intention = await self._create_intention(scored_goal, user_id, activate=False)
                new_intentions.append(intention)
        
        # Refresh intention set
        intention_set = await self.get_intention_set(user_id)
        
        # Publish changes if message bus available
        if self.message_bus and new_intentions:
            await self._publish_intention_set_update(intention_set)
        
        if self.logger:
            self.logger.info(
                f"[ARBITER] Updated intention set for {user_id}: "
                f"{len(intention_set.active_intentions)} active, "
                f"{len(intention_set.proposed_intentions)} proposed"
            )
        
        return intention_set
    
    async def activate_intention(self, intention_id: str) -> Intention:
        """Activate a proposed intention."""
        intention = await self._get_intention(intention_id)
        if not intention:
            raise ValueError(f"Intention {intention_id} not found")
        
        intention.status = IntentionStatus.ACTIVE
        intention.activated_at = datetime.utcnow()
        intention.updated_at = datetime.utcnow()
        
        await self._update_intention(intention)
        
        if self.logger:
            self.logger.info(f"[ARBITER] Activated intention {intention_id}")
        
        return intention
    
    async def deactivate_intention(self, intention_id: str, reason: str = "dropped") -> Intention:
        """Deactivate an active intention."""
        intention = await self._get_intention(intention_id)
        if not intention:
            raise ValueError(f"Intention {intention_id} not found")
        
        intention.status = IntentionStatus.DROPPED if reason == "dropped" else IntentionStatus.PAUSED
        intention.deactivated_at = datetime.utcnow()
        intention.updated_at = datetime.utcnow()
        
        await self._update_intention(intention)
        
        if self.logger:
            self.logger.info(f"[ARBITER] Deactivated intention {intention_id}: {reason}")
        
        return intention
    
    # ========================================================================
    # Internal Helpers
    # ========================================================================
    
    async def _create_intention(
        self,
        scored_goal: ScoredGoal,
        user_id: str,
        activate: bool = True
    ) -> Intention:
        """Create a new intention in the database."""
        intention = Intention(
            goal_id=scored_goal.goal.goal_id,
            user_id=user_id,
            status=IntentionStatus.ACTIVE if activate else IntentionStatus.PROPOSED,
            arbiter_score=scored_goal.arbiter_score,
            priority_band=scored_goal.priority_band,
            reasons=scored_goal.reasons,
            activated_at=datetime.utcnow() if activate else None
        )
        
        self.db.execute(
            """
            INSERT INTO intention_set (
                intention_id, goal_id, user_id, status, arbiter_score,
                priority_band, reasons_json, activated_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                intention.intention_id,
                intention.goal_id,
                intention.user_id,
                intention.status.value,
                intention.arbiter_score,
                intention.priority_band.value,
                json.dumps(intention.reasons),
                intention.activated_at.isoformat() if intention.activated_at else None,
                intention.created_at.isoformat(),
                intention.updated_at.isoformat()
            )
        )
        
        return intention
    
    async def _update_intention(self, intention: Intention) -> None:
        """Update an existing intention in the database."""
        self.db.execute(
            """
            UPDATE intention_set 
            SET status = ?, arbiter_score = ?, priority_band = ?,
                reasons_json = ?, activated_at = ?, deactivated_at = ?,
                updated_at = ?
            WHERE intention_id = ?
            """,
            (
                intention.status.value,
                intention.arbiter_score,
                intention.priority_band.value,
                json.dumps(intention.reasons),
                intention.activated_at.isoformat() if intention.activated_at else None,
                intention.deactivated_at.isoformat() if intention.deactivated_at else None,
                intention.updated_at.isoformat(),
                intention.intention_id
            )
        )
    
    async def _get_intention(self, intention_id: str) -> Optional[Intention]:
        """Get an intention by ID."""
        row = self.db.fetch_one(
            "SELECT * FROM intention_set WHERE intention_id = ?",
            (intention_id,)
        )
        
        if not row:
            return None
        
        return Intention(
            intention_id=row["intention_id"],
            goal_id=row["goal_id"],
            user_id=row["user_id"],
            status=IntentionStatus(row["status"]),
            arbiter_score=row["arbiter_score"],
            priority_band=PriorityBand(row["priority_band"]),
            reasons=json.loads(row["reasons_json"] or "[]"),
            activated_at=datetime.fromisoformat(row["activated_at"]) if row["activated_at"] else None,
            deactivated_at=datetime.fromisoformat(row["deactivated_at"]) if row["deactivated_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
    
    async def _publish_intention_set_update(self, intention_set: IntentionSet) -> None:
        """Publish intention set update to message bus."""
        if not self.message_bus:
            return
        
        payload = {
            "user_id": intention_set.user_id,
            "active_count": len(intention_set.active_intentions),
            "proposed_count": len(intention_set.proposed_intentions),
            "intentions": [
                {
                    "intention_id": i.intention_id,
                    "goal_id": i.goal_id,
                    "status": i.status.value,
                    "score": i.arbiter_score,
                    "priority_band": i.priority_band.value,
                }
                for i in intention_set.intentions
            ],
            "updated_at": intention_set.updated_at.isoformat()
        }
        
        self.message_bus.publish(
            topic="agency.intention_set.updated",
            message=payload,
            priority=2
        )
        
        if self.logger:
            self.logger.debug(
                f"[ARBITER] Published intention set update for {intention_set.user_id}"
            )
