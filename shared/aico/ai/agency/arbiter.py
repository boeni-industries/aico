"""
Goal Arbiter - Central Decision-Making for Agency

Collects, scores, ranks, and filters goal candidates from various sources.
Maintains the "active intention set" and publishes changes to the message bus.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, UTC
from enum import Enum

from pydantic import BaseModel, Field

from aico.core.bus import MessageBusClient

from .models import Goal, GoalStatus, GoalOrigin, GoalPriority
from .arbiter_adaptive import AdaptiveScoringEngine, AdaptiveConfig
from .arbiter_context import ContextAwarePrioritization


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
        db: Any,  # Agency system being redesigned
        config=None,
        message_bus: Optional[MessageBusClient] = None,
        logger=None,
        enable_adaptive: bool = True,
        enable_context_aware: bool = True
    ):
        self.db = db
        self.message_bus = message_bus
        self.logger = logger
        self.config = config
        
        # Phase 6.5: Adaptive scoring and context-aware prioritization
        self.enable_adaptive = enable_adaptive
        self.enable_context_aware = enable_context_aware
        
        if enable_adaptive:
            adaptive_config = AdaptiveConfig()
            self.adaptive_engine = AdaptiveScoringEngine(db, adaptive_config, logger)
            if logger:
                logger.debug("[ARBITER] Phase 6.5: Adaptive scoring enabled")
        else:
            self.adaptive_engine = None
        
        if enable_context_aware:
            self.context_engine = ContextAwarePrioritization(db, logger)
            if logger:
                logger.debug("[ARBITER] Phase 6.5: Context-aware prioritization enabled")
        else:
            self.context_engine = None
        
        # Load scoring weights from config with validation
        if config:
            try:
                weights_config = config.get("core.services.agency.arbiter.scoring_weights", {})
                
                if not weights_config:
                    raise ValueError("core.services.agency.arbiter.scoring_weights not found in configuration")
                
                self.weights = {
                    "priority": float(weights_config.get("priority", 0.25)),
                    "origin": float(weights_config.get("origin", 0.20)),
                    "freshness": float(weights_config.get("freshness", 0.10)),
                    "curiosity_score": float(weights_config.get("curiosity_score", 0.15)),
                    "persistence": float(weights_config.get("persistence", 0.15)),
                    "personality_fit": float(weights_config.get("personality_fit", 0.10)),
                    "emotion_boost": float(weights_config.get("emotion_boost", 0.05)),
                }
                
                # Validate weights sum to approximately 1.0
                total_weight = sum(self.weights.values())
                
                if abs(total_weight - 1.0) > 0.01:
                    raise ValueError(
                        f"Arbiter scoring weights must sum to ~1.0, got {total_weight:.3f}. "
                        f"Check core.services.agency.arbiter.scoring_weights in configuration."
                    )
                if logger:
                    logger.debug(f"[ARBITER] Loaded scoring weights from config: {self.weights}")
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
        
        # Cache for lesson-based adjustments
        self._adjustments_cache: Dict[str, float] = {}
        self._adjustments_cache_time: Optional[datetime] = None
        self._adjustments_cache_ttl = 300  # 5 minutes
        
        # Only warn if config was actually None (not just missing weights)
        if not config and logger:
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
    # Lesson-Based Adjustments
    # ========================================================================
    
    def _load_adjustments(self, user_id: Optional[str] = None) -> Dict[str, float]:
        """
        Load active lesson-based adjustments from database.
        
        Args:
            user_id: Optional user ID for user-specific adjustments
            
        Returns:
            Dictionary of adjustment_key -> adjustment_value
        """
        # Check cache
        if self._adjustments_cache_time:
            age = (datetime.now(UTC) - self._adjustments_cache_time).total_seconds()
            if age < self._adjustments_cache_ttl:
                return self._adjustments_cache.copy()
        
        # Load from database
        adjustments = {}
        try:
            # Query active adjustments (global + user-specific)
            if user_id:
                rows = self.db.execute(
                    """SELECT adjustment_key, adjustment_value, confidence
                       FROM agency_arbiter_adjustments
                       WHERE active = 1 AND (user_id IS NULL OR user_id = ?)
                       ORDER BY confidence DESC""",
                    (user_id,)
                ).fetchall()
            else:
                rows = self.db.execute(
                    """SELECT adjustment_key, adjustment_value, confidence
                       FROM agency_arbiter_adjustments
                       WHERE active = 1 AND user_id IS NULL
                       ORDER BY confidence DESC"""
                ).fetchall()
            
            for row in rows:
                key = row["adjustment_key"]
                value = row["adjustment_value"]
                # Use highest confidence adjustment if multiple exist
                if key not in adjustments:
                    adjustments[key] = value
            
            # Update cache
            self._adjustments_cache = adjustments
            self._adjustments_cache_time = datetime.now(UTC)
            
            if adjustments and self.logger:
                self.logger.debug(
                    f"[ARBITER] Loaded {len(adjustments)} lesson-based adjustments"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[ARBITER] Failed to load adjustments: {e}")
        
        return adjustments
    
    def _get_adjusted_weight(self, weight_key: str, base_value: float, user_id: Optional[str] = None) -> float:
        """
        Get weight value with lesson-based adjustments applied.
        
        Args:
            weight_key: Weight key (e.g., "priority", "origin")
            base_value: Base weight value from config
            user_id: Optional user ID for user-specific adjustments
            
        Returns:
            Adjusted weight value
        """
        adjustments = self._load_adjustments(user_id)
        
        # Check for direct weight adjustment
        if weight_key in adjustments:
            return adjustments[weight_key]
        
        # Check for goal_type-specific adjustments
        # (handled in score_goal method)
        
        return base_value
    
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
        
        Phase 6.5: Now supports adaptive weights and context-aware adjustments.
        
        Args:
            goal: Goal to score
            context: Optional context (personality, emotion, system load)
            
        Returns:
            ScoredGoal with score and breakdown
        """
        context = context or {}
        breakdown = {}
        
        # Phase 6.5: Use adaptive weights if enabled
        if self.enable_adaptive and self.adaptive_engine:
            arm_id, adaptive_weights = self.adaptive_engine.select_arm(goal.user_id)
            # Store arm_id for later reward feedback
            context["selected_arm_id"] = arm_id
            # Use adaptive weights instead of fixed weights
            weights = adaptive_weights
            if self.logger:
                self.logger.debug(f"[ARBITER] Using adaptive weights from arm: {arm_id}")
        else:
            weights = self.weights
        
        # Load lesson-based adjustments for this user
        user_id = goal.user_id
        adjustments = self._load_adjustments(user_id)
        
        # Check for goal_type-specific adjustment from lessons
        goal_type_key = f"goal_type_{goal.goal_type}"
        goal_type_multiplier = adjustments.get(goal_type_key, 1.0)
        
        # Check for goal_type performance data from self-model
        # This can further adjust scoring based on historical success
        goal_type_performance = context.get("goal_type_performance", {})
        if goal.goal_type in goal_type_performance:
            perf_data = goal_type_performance[goal.goal_type]
            success_rate = perf_data.get("success_rate", 0.5)
            confidence = perf_data.get("confidence", 0.0)
            
            # Apply performance-based adjustment if we have confident data
            if confidence >= 0.5:
                # Boost or penalize based on success rate
                # success_rate 0.8+ = 1.1x boost, 0.2- = 0.9x penalty
                perf_multiplier = 0.9 + (success_rate * 0.2)
                goal_type_multiplier *= perf_multiplier
                
                if self.logger:
                    self.logger.debug(
                        f"[ARBITER] Applied performance multiplier {perf_multiplier:.2f} "
                        f"for {goal.goal_type} (success_rate={success_rate:.2f})"
                    )
        
        # 1. Priority score (0.0-1.0)
        priority_map = {
            GoalPriority.HIGH: 1.0,
            GoalPriority.NORMAL: 0.6,
            GoalPriority.LOW: 0.3,
        }
        priority_score = priority_map.get(goal.priority, 0.6)
        priority_weight = self._get_adjusted_weight("priority", self.weights["priority"], user_id)
        breakdown["priority"] = priority_score * priority_weight
        
        # 2. Origin score
        origin_score = self.origin_scores.get(goal.origin, 0.5)
        origin_weight = self._get_adjusted_weight("origin", self.weights["origin"], user_id)
        breakdown["origin"] = origin_score * origin_weight
        
        # 3. Freshness score (newer goals score higher)
        age_hours = (datetime.now(UTC) - goal.created_at).total_seconds() / 3600
        freshness_score = max(0.0, 1.0 - (age_hours / 168))  # Decay over 1 week
        freshness_weight = self._get_adjusted_weight("freshness", self.weights["freshness"], user_id)
        breakdown["freshness"] = freshness_score * freshness_weight
        
        # 4. Curiosity score (if from curiosity engine)
        curiosity_score = 0.0
        if goal.origin in [GoalOrigin.CURIOSITY, GoalOrigin.HOBBY]:
            curiosity_score = goal.metadata.get("curiosity_score", 0.5)
        curiosity_weight = self._get_adjusted_weight("curiosity_score", self.weights["curiosity_score"], user_id)
        breakdown["curiosity_score"] = curiosity_score * curiosity_weight
        
        # 5. Personality fit (Phase 2+)
        personality_fit = context.get("personality_fit", 0.5)
        personality_weight = self._get_adjusted_weight("personality_fit", self.weights["personality_fit"], user_id)
        breakdown["personality_fit"] = personality_fit * personality_weight
        
        # 6. Emotion boost (Phase 2+)
        emotion_boost = context.get("emotion_boost", 0.5)
        emotion_weight = self._get_adjusted_weight("emotion_boost", self.weights["emotion_boost"], user_id)
        breakdown["emotion_boost"] = emotion_boost * emotion_weight
        
        # 7. Persistence score (intent frequency/reinforcement)
        mention_count = goal.metadata.get("mention_count", 1)
        mention_frequency = goal.metadata.get("mention_frequency", 0.0)
        
        # Score based on mention count: 1 mention = 0.0, 2 = 0.3, 3+ = 0.6-1.0
        persistence_score = min(1.0, (mention_count - 1) * 0.3)
        
        # Boost if mentions are recent and frequent (>1 per day)
        if mention_frequency > 1.0:
            persistence_score = min(1.0, persistence_score * 1.2)
        
        persistence_weight = self._get_adjusted_weight("persistence", self.weights.get("persistence", 0.15), user_id)
        breakdown["persistence"] = persistence_score * persistence_weight
        
        if self.logger and mention_count > 1:
            self.logger.debug(
                f"[ARBITER] Goal {goal.goal_id} persistence: "
                f"mentions={mention_count}, frequency={mention_frequency:.2f}/day, score={persistence_score:.3f}"
            )
        
        # Calculate total score
        total_score = sum(breakdown.values())
        
        # Apply goal_type-specific multiplier from lessons
        if goal_type_multiplier != 1.0:
            total_score *= goal_type_multiplier
            if self.logger:
                self.logger.debug(
                    f"[ARBITER] Applied goal_type multiplier {goal_type_multiplier} "
                    f"to {goal.goal_type} (lesson-based adjustment)"
                )
        
        # Phase 6.5: Apply context-aware adjustments
        if self.enable_context_aware and self.context_engine:
            total_score, context_adjustments = self.context_engine.apply_contextual_adjustments(
                goal, total_score, user_id, context
            )
            # Store context adjustments as metadata (not in breakdown which expects floats)
            if self.logger:
                self.logger.debug(f"[ARBITER] Context adjustments: {context_adjustments}")
        
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
            SELECT * FROM agency_intention_set 
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
                activated_at=datetime.fromisoformat(row["activated_at"]).replace(tzinfo=UTC) if row["activated_at"] else None,
                deactivated_at=datetime.fromisoformat(row["deactivated_at"]).replace(tzinfo=UTC) if row["deactivated_at"] else None,
                created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
                updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC)
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
                if existing.status == IntentionStatus.ACTIVE:
                    # Already active, just update score if changed significantly
                    if abs(existing.arbiter_score - scored_goal.arbiter_score) > 0.1:
                        existing.arbiter_score = scored_goal.arbiter_score
                        existing.priority_band = scored_goal.priority_band
                        existing.updated_at = datetime.now(UTC)
                        await self._update_intention(existing)
                    continue
                
                # Intention exists but NOT active (dropped/proposed) → reactivation candidate
                if scored_goal.priority_band == PriorityBand.URGENT:
                    # Urgent goals always get reactivated
                    existing.status = IntentionStatus.ACTIVE
                    existing.arbiter_score = scored_goal.arbiter_score
                    existing.priority_band = scored_goal.priority_band
                    existing.activated_at = datetime.now(UTC)
                    existing.updated_at = datetime.now(UTC)
                    await self._update_intention(existing)
                    new_intentions.append(existing)
                    if self.logger:
                        self.logger.info(f"[ARBITER] Reactivated urgent intention: '{scored_goal.goal.title}'")
                elif scored_goal.priority_band == PriorityBand.NORMAL:
                    if active_count < intention_set.max_active:
                        # Reactivate if capacity available
                        existing.status = IntentionStatus.ACTIVE
                        existing.arbiter_score = scored_goal.arbiter_score
                        existing.priority_band = scored_goal.priority_band
                        existing.activated_at = datetime.now(UTC)
                        existing.updated_at = datetime.now(UTC)
                        await self._update_intention(existing)
                        new_intentions.append(existing)
                        active_count += 1
                        if self.logger:
                            self.logger.info(f"[ARBITER] Reactivated intention: '{scored_goal.goal.title}' (score={scored_goal.arbiter_score:.3f})")
                    else:
                        # At capacity: competitive replacement for reactivation
                        active_intentions = [i for i in intention_set.intentions if i.status == IntentionStatus.ACTIVE]
                        if active_intentions:
                            lowest = min(active_intentions, key=lambda i: i.arbiter_score)
                            if scored_goal.arbiter_score > lowest.arbiter_score:
                                # Replace: deactivate lowest, reactivate this one
                                await self.deactivate_intention(lowest.intention_id, reason="replaced_by_higher_score")
                                existing.status = IntentionStatus.ACTIVE
                                existing.arbiter_score = scored_goal.arbiter_score
                                existing.priority_band = scored_goal.priority_band
                                existing.activated_at = datetime.now(UTC)
                                existing.updated_at = datetime.now(UTC)
                                await self._update_intention(existing)
                                new_intentions.append(existing)
                                if self.logger:
                                    self.logger.info(
                                        f"[ARBITER] Competitive reactivation: '{scored_goal.goal.title}' "
                                        f"(score={scored_goal.arbiter_score:.3f}) replaced intention with score {lowest.arbiter_score:.3f}"
                                    )
                elif scored_goal.priority_band == PriorityBand.BACKGROUND:
                    # Update to proposed status
                    existing.status = IntentionStatus.PROPOSED
                    existing.arbiter_score = scored_goal.arbiter_score
                    existing.priority_band = scored_goal.priority_band
                    existing.updated_at = datetime.now(UTC)
                    await self._update_intention(existing)
                    new_intentions.append(existing)
                continue
            
            # No existing intention → create new
            if scored_goal.priority_band == PriorityBand.URGENT:
                # Urgent goals always get added
                intention = await self._create_intention(scored_goal, user_id)
                new_intentions.append(intention)
                if self.logger:
                    self.logger.info(f"[ARBITER] Created urgent intention: '{scored_goal.goal.title}'")
            elif scored_goal.priority_band == PriorityBand.NORMAL:
                if active_count < intention_set.max_active:
                    # Add if capacity available
                    intention = await self._create_intention(scored_goal, user_id)
                    new_intentions.append(intention)
                    active_count += 1
                    if self.logger:
                        self.logger.info(f"[ARBITER] Created intention: '{scored_goal.goal.title}' (score={scored_goal.arbiter_score:.3f})")
                else:
                    # At capacity: check if this goal scores higher than lowest active intention
                    active_intentions = [i for i in intention_set.intentions if i.status == IntentionStatus.ACTIVE]
                    if active_intentions:
                        lowest = min(active_intentions, key=lambda i: i.arbiter_score)
                        if scored_goal.arbiter_score > lowest.arbiter_score:
                            # Replace: deactivate lowest, activate new
                            await self.deactivate_intention(lowest.intention_id, reason="replaced_by_higher_score")
                            intention = await self._create_intention(scored_goal, user_id)
                            new_intentions.append(intention)
                            if self.logger:
                                self.logger.info(
                                    f"[ARBITER] Competitive replacement: '{scored_goal.goal.title}' "
                                    f"(score={scored_goal.arbiter_score:.3f}) replaced intention with score {lowest.arbiter_score:.3f}"
                                )
            elif scored_goal.priority_band == PriorityBand.BACKGROUND:
                # Background goals are proposed but not activated
                intention = await self._create_intention(scored_goal, user_id, activate=False)
                new_intentions.append(intention)
        
        # Enforce max_active capacity: deactivate lowest scorers if over limit
        intention_set = await self.get_intention_set(user_id)
        active_intentions = [i for i in intention_set.intentions if i.status == IntentionStatus.ACTIVE]
        
        if len(active_intentions) > intention_set.max_active:
            # Sort by score, keep top max_active, deactivate the rest
            sorted_active = sorted(active_intentions, key=lambda i: i.arbiter_score, reverse=True)
            to_deactivate = sorted_active[intention_set.max_active:]
            
            for intention in to_deactivate:
                await self.deactivate_intention(intention.intention_id, reason="capacity_limit")
                if self.logger:
                    self.logger.info(
                        f"[ARBITER] Deactivated intention (score={intention.arbiter_score:.3f}) - over capacity"
                    )
        
        # Refresh intention set after capacity enforcement
        intention_set = await self.get_intention_set(user_id)
        
        # Activate/deactivate plans based on ALL intention statuses
        await self._sync_plans_with_intentions(user_id, intention_set.intentions)
        
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
        intention.activated_at = datetime.now(UTC)
        intention.updated_at = datetime.now(UTC)
        
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
        intention.deactivated_at = datetime.now(UTC)
        intention.updated_at = datetime.now(UTC)
        
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
            activated_at=datetime.now(UTC) if activate else None
        )
        
        self.db.execute(
            """
            INSERT INTO agency_intention_set (
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
            UPDATE agency_intention_set 
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
            "SELECT * FROM agency_intention_set WHERE intention_id = ?",
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
            activated_at=datetime.fromisoformat(row["activated_at"]).replace(tzinfo=UTC) if row["activated_at"] else None,
            deactivated_at=datetime.fromisoformat(row["deactivated_at"]).replace(tzinfo=UTC) if row["deactivated_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
            updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC)
        )
    
    async def _sync_plans_with_intentions(
        self,
        user_id: str,
        new_intentions: List[Intention]
    ) -> None:
        """
        Sync plan status with intention status changes.
        Activate plans for newly active intentions, pause plans for deactivated ones.
        """
        from .models import PlanStatus
        
        for intention in new_intentions:
            try:
                # Get plan for this goal
                row = self.db.fetch_one(
                    "SELECT plan_id, status FROM agency_plans WHERE goal_id = ?",
                    (intention.goal_id,)
                )
                
                if not row:
                    continue
                
                plan_id = row["plan_id"]
                current_plan_status = row["status"]
                
                # Activate plan if intention is active and plan is draft
                if intention.status == IntentionStatus.ACTIVE and current_plan_status == "draft":
                    self.db.execute(
                        "UPDATE agency_plans SET status = ?, updated_at = ? WHERE plan_id = ?",
                        (PlanStatus.ACTIVE.value, datetime.now(UTC).isoformat(), plan_id)
                    )
                    self.db.commit()
                    
                    if self.logger:
                        self.logger.info(
                            f"[ARBITER] Activated plan {plan_id[:8]}... for intention {intention.intention_id[:8]}..."
                        )
                
                # Pause plan if intention is dropped/paused and plan is active
                elif intention.status in [IntentionStatus.DROPPED, IntentionStatus.PAUSED] and current_plan_status == "active":
                    self.db.execute(
                        "UPDATE agency_plans SET status = ?, updated_at = ? WHERE plan_id = ?",
                        (PlanStatus.PAUSED.value, datetime.now(UTC).isoformat(), plan_id)
                    )
                    self.db.commit()
                    
                    if self.logger:
                        self.logger.info(
                            f"[ARBITER] Paused plan {plan_id[:8]}... for intention {intention.intention_id[:8]}..."
                        )
                        
            except Exception as e:
                if self.logger:
                    self.logger.exception(
                        f"[ARBITER] Failed to sync plan for intention {intention.intention_id}: {e}"
                    )
    
    async def _publish_intention_set_update(self, intention_set: IntentionSet) -> None:
        """Publish intention set update to message bus."""
        if not self.message_bus:
            return
        
        # TODO: Message bus publishing requires protobuf message, not dict
        # For now, skip publishing - it's an optional feature for real-time UI updates
        # The intention_set is persisted in DB which is the critical path
        if self.logger:
            self.logger.debug(
                f"[ARBITER] Intention set updated for {intention_set.user_id} "
                f"({len(intention_set.active_intentions)} active, "
                f"{len(intention_set.proposed_intentions)} proposed)"
            )
    
    # ========================================================================
    # Phase 6.5: Adaptive Learning
    # ========================================================================
    
    async def record_goal_outcome(
        self,
        goal_id: str,
        outcome: str,
        success: bool,
        user_satisfaction: Optional[float] = None,
        completion_time_minutes: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Record goal outcome for adaptive learning.
        
        Args:
            goal_id: Goal ID
            outcome: Outcome type (completed, abandoned, failed, timeout)
            success: Whether the goal succeeded
            user_satisfaction: Optional user satisfaction score (0.0-1.0)
            completion_time_minutes: Time taken to complete
            metadata: Additional outcome metadata
        """
        if not self.enable_adaptive or not self.adaptive_engine:
            return
        
        try:
            import uuid
            
            # Calculate reward based on outcome
            reward = 0.0
            if outcome == "completed":
                reward = 0.8
                if user_satisfaction is not None:
                    reward = 0.5 + (user_satisfaction * 0.5)  # 0.5-1.0 range
            elif outcome == "abandoned":
                reward = 0.2
            elif outcome == "failed":
                reward = 0.1
            elif outcome == "timeout":
                reward = 0.3
            
            # Get the arm that was used for this goal
            arm_id = None
            if metadata and "selected_arm_id" in metadata:
                arm_id = metadata["selected_arm_id"]
            
            # Record outcome in database
            outcome_id = str(uuid.uuid4())
            self.db.execute(
                """
                INSERT INTO agency_goal_outcomes (
                    outcome_id, goal_id, user_id, arm_id, outcome,
                    success, reward, completion_time_minutes,
                    user_satisfaction, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome_id,
                    goal_id,
                    metadata.get("user_id") if metadata else None,
                    arm_id,
                    outcome,
                    1 if success else 0,
                    reward,
                    completion_time_minutes,
                    user_satisfaction,
                    json.dumps(metadata or {}),
                    datetime.now(UTC).isoformat()
                )
            )
            
            # Update adaptive engine
            if arm_id:
                self.adaptive_engine.update_arm(arm_id, reward, success, goal_id)
                
                if self.logger:
                    self.logger.info(
                        f"[ARBITER] Recorded outcome for goal {goal_id}: "
                        f"{outcome} (reward: {reward:.2f}, arm: {arm_id})"
                    )
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ARBITER] Failed to record goal outcome: {e}")
