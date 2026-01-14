"""
Context-Aware Prioritization for Goal Arbiter - Phase 6.5

Implements time-of-day awareness, user state detection, deadline urgency,
and dependency-aware scheduling for intelligent goal prioritization.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, UTC, time
from dataclasses import dataclass
from enum import Enum

from .models import Goal, GoalPriority


# ============================================================================
# Enums & Data Models
# ============================================================================

class UserState(str, Enum):
    """User's current state affecting goal prioritization."""
    BUSY = "busy"
    FOCUSED = "focused"
    RELAXED = "relaxed"
    STRESSED = "stressed"
    ENERGETIC = "energetic"
    TIRED = "tired"
    UNKNOWN = "unknown"


class TimeOfDayPeriod(str, Enum):
    """Time of day periods for context-aware scoring."""
    EARLY_MORNING = "early_morning"  # 5-8 AM
    MORNING = "morning"  # 8-12 PM
    AFTERNOON = "afternoon"  # 12-5 PM
    EVENING = "evening"  # 5-9 PM
    NIGHT = "night"  # 9 PM-5 AM


@dataclass
class ContextualFactors:
    """Contextual factors affecting goal prioritization."""
    
    time_of_day: TimeOfDayPeriod
    user_state: UserState
    day_of_week: str  # monday, tuesday, etc.
    is_weekend: bool
    is_holiday: bool = False
    current_load: float = 0.5  # 0.0-1.0, system/cognitive load
    available_time_minutes: Optional[int] = None
    location: Optional[str] = None


@dataclass
class DeadlineInfo:
    """Deadline information for urgency calculation."""
    
    goal_id: str
    deadline: datetime
    estimated_duration_minutes: Optional[int] = None
    is_hard_deadline: bool = True  # Hard vs soft deadline
    buffer_hours: int = 2  # Safety buffer before deadline


@dataclass
class DependencyInfo:
    """Dependency information for scheduling."""
    
    goal_id: str
    depends_on: List[str]  # Goal IDs this goal depends on
    blocks: List[str]  # Goal IDs that depend on this goal
    can_parallelize: bool = True


# ============================================================================
# Context-Aware Prioritization Engine
# ============================================================================

class ContextAwarePrioritization:
    """
    Implements context-aware goal prioritization.
    
    Adjusts goal scores based on:
    - Time of day (morning person vs night owl patterns)
    - User state (busy, focused, relaxed, etc.)
    - Deadlines (urgency increases as deadline approaches)
    - Dependencies (schedule based on prerequisite completion)
    """
    
    def __init__(
        self,
        db: Any  # Agency system being redesigned,
        logger=None
    ):
        self.db = db
        self.logger = logger
        
        # Load user preferences for time-of-day patterns
        self.time_preferences: Dict[str, Dict[TimeOfDayPeriod, float]] = {}
        self._load_time_preferences()
    
    # ========================================================================
    # Time-of-Day Awareness
    # ========================================================================
    
    def get_time_of_day_period(self, dt: Optional[datetime] = None) -> TimeOfDayPeriod:
        """Determine current time of day period."""
        dt = dt or datetime.now()
        hour = dt.hour
        
        if 5 <= hour < 8:
            return TimeOfDayPeriod.EARLY_MORNING
        elif 8 <= hour < 12:
            return TimeOfDayPeriod.MORNING
        elif 12 <= hour < 17:
            return TimeOfDayPeriod.AFTERNOON
        elif 17 <= hour < 21:
            return TimeOfDayPeriod.EVENING
        else:
            return TimeOfDayPeriod.NIGHT
    
    def _load_time_preferences(self) -> None:
        """Load user time-of-day preferences from database."""
        try:
            rows = self.db.fetch_all(
                """
                SELECT user_id, time_period, productivity_score
                FROM user_time_preferences
                WHERE active = 1
                """
            )
            
            for row in rows:
                user_id = row["user_id"]
                if user_id not in self.time_preferences:
                    self.time_preferences[user_id] = {}
                
                period = TimeOfDayPeriod(row["time_period"])
                self.time_preferences[user_id][period] = row["productivity_score"]
            
            if self.logger and self.time_preferences:
                self.logger.info(
                    f"[CONTEXT] Loaded time preferences for {len(self.time_preferences)} users"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[CONTEXT] Failed to load time preferences: {e}")
    
    def get_time_of_day_multiplier(
        self,
        goal: Goal,
        context: ContextualFactors,
        user_id: str
    ) -> float:
        """
        Calculate time-of-day multiplier for goal score.
        
        Args:
            goal: Goal to score
            context: Current contextual factors
            user_id: User ID
            
        Returns:
            Multiplier (0.5-1.5) based on time preferences
        """
        # Get user's productivity score for current time period
        user_prefs = self.time_preferences.get(user_id, {})
        productivity = user_prefs.get(context.time_of_day, 1.0)
        
        # Check goal metadata for time preferences
        goal_time_pref = goal.metadata.get("preferred_time_of_day")
        if goal_time_pref:
            if goal_time_pref == context.time_of_day.value:
                # Goal matches preferred time - boost
                productivity *= 1.2
            elif goal_time_pref in ["morning", "afternoon"] and context.time_of_day == TimeOfDayPeriod.NIGHT:
                # Daytime goal at night - penalize
                productivity *= 0.7
        
        # Weekend/weekday adjustments
        if context.is_weekend:
            # Boost hobby/personal goals on weekends
            if goal.goal_type in ["hobby", "personal_development", "wellness"]:
                productivity *= 1.15
            # Reduce work goals on weekends
            elif goal.goal_type in ["work", "professional"]:
                productivity *= 0.85
        
        # Clamp to reasonable range
        return max(0.5, min(1.5, productivity))
    
    # ========================================================================
    # User State Awareness
    # ========================================================================
    
    def detect_user_state(
        self,
        user_id: str,
        context: Optional[Dict] = None
    ) -> UserState:
        """
        Detect user's current state from various signals.
        
        Args:
            user_id: User ID
            context: Optional context with emotion, activity, etc.
            
        Returns:
            Detected user state
        """
        context = context or {}
        
        # Check emotion state
        emotion = context.get("emotion_state", {})
        if emotion:
            valence = emotion.get("valence", 0.0)
            arousal = emotion.get("arousal", 0.0)
            stress = emotion.get("stress", 0.0)
            
            if stress > 0.7:
                return UserState.STRESSED
            elif arousal > 0.7 and valence > 0.5:
                return UserState.ENERGETIC
            elif arousal < 0.3:
                return UserState.TIRED
            elif valence > 0.6 and stress < 0.3:
                return UserState.RELAXED
        
        # Check calendar/activity
        current_load = context.get("current_load", 0.5)
        if current_load > 0.8:
            return UserState.BUSY
        elif current_load < 0.3:
            return UserState.RELAXED
        
        # Check recent activity patterns
        try:
            recent_goals = self.db.fetch_all(
                """
                SELECT COUNT(*) as active_count
                FROM agency_goals
                WHERE user_id = ? AND status = 'active'
                AND updated_at > datetime('now', '-1 hour')
                """,
                (user_id,)
            )
            
            if recent_goals and recent_goals[0]["active_count"] > 3:
                return UserState.FOCUSED
                
        except Exception as e:
            if self.logger:
                self.logger.debug(f"[CONTEXT] Failed to check recent activity: {e}")
        
        return UserState.UNKNOWN
    
    def get_user_state_multiplier(
        self,
        goal: Goal,
        user_state: UserState
    ) -> float:
        """
        Calculate user state multiplier for goal score.
        
        Args:
            goal: Goal to score
            user_state: Current user state
            
        Returns:
            Multiplier (0.5-1.5) based on state compatibility
        """
        # Define goal type compatibility with user states
        compatibility = {
            UserState.BUSY: {
                "quick_task": 1.3,
                "maintenance": 0.7,
                "hobby": 0.5,
                "deep_work": 0.6,
            },
            UserState.FOCUSED: {
                "deep_work": 1.4,
                "learning": 1.3,
                "creative": 1.2,
                "quick_task": 0.8,
            },
            UserState.RELAXED: {
                "hobby": 1.4,
                "personal_development": 1.3,
                "social": 1.2,
                "work": 0.9,
            },
            UserState.STRESSED: {
                "wellness": 1.5,
                "break": 1.4,
                "quick_task": 1.1,
                "deep_work": 0.6,
            },
            UserState.ENERGETIC: {
                "physical": 1.4,
                "creative": 1.3,
                "social": 1.2,
                "maintenance": 1.1,
            },
            UserState.TIRED: {
                "break": 1.5,
                "light_task": 1.2,
                "deep_work": 0.5,
                "physical": 0.6,
            },
        }
        
        goal_type = goal.goal_type
        multipliers = compatibility.get(user_state, {})
        
        return multipliers.get(goal_type, 1.0)
    
    # ========================================================================
    # Deadline Urgency
    # ========================================================================
    
    def calculate_deadline_urgency(
        self,
        goal: Goal,
        deadline_info: Optional[DeadlineInfo] = None
    ) -> float:
        """
        Calculate urgency multiplier based on deadline proximity.
        
        Args:
            goal: Goal to evaluate
            deadline_info: Deadline information
            
        Returns:
            Urgency multiplier (1.0-2.0)
        """
        # Check goal metadata for deadline
        deadline_str = goal.metadata.get("deadline")
        if not deadline_str and not deadline_info:
            return 1.0  # No deadline
        
        try:
            if deadline_info:
                deadline = deadline_info.deadline
                buffer_hours = deadline_info.buffer_hours
                estimated_duration = deadline_info.estimated_duration_minutes or 60
                is_hard = deadline_info.is_hard_deadline
            else:
                deadline = datetime.fromisoformat(deadline_str).replace(tzinfo=UTC)
                buffer_hours = 2
                estimated_duration = goal.metadata.get("estimated_duration_minutes", 60)
                is_hard = goal.metadata.get("is_hard_deadline", True)
            
            # Calculate time until deadline
            now = datetime.now(UTC)
            time_until_deadline = (deadline - now).total_seconds() / 3600  # hours
            
            # Calculate urgency based on time remaining vs estimated duration
            duration_hours = estimated_duration / 60
            time_needed = duration_hours + buffer_hours
            
            if time_until_deadline < 0:
                # Past deadline
                return 2.0 if is_hard else 1.5
            elif time_until_deadline < time_needed:
                # Within critical window
                urgency = 1.5 + (0.5 * (1 - time_until_deadline / time_needed))
                return min(2.0, urgency)
            elif time_until_deadline < time_needed * 2:
                # Approaching deadline
                return 1.3
            elif time_until_deadline < time_needed * 4:
                # Deadline visible but not urgent
                return 1.1
            else:
                # Plenty of time
                return 1.0
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[CONTEXT] Failed to calculate deadline urgency: {e}")
            return 1.0
    
    # ========================================================================
    # Dependency-Aware Scheduling
    # ========================================================================
    
    def get_dependency_info(self, goal_id: str) -> DependencyInfo:
        """Get dependency information for a goal."""
        try:
            # Get goals this goal depends on
            depends_on = self.db.fetch_all(
                """
                SELECT prerequisite_goal_id
                FROM agency_goal_dependencies
                WHERE goal_id = ? AND active = 1
                """,
                (goal_id,)
            )
            
            # Get goals that depend on this goal
            blocks = self.db.fetch_all(
                """
                SELECT goal_id
                FROM agency_goal_dependencies
                WHERE prerequisite_goal_id = ? AND active = 1
                """,
                (goal_id,)
            )
            
            return DependencyInfo(
                goal_id=goal_id,
                depends_on=[row["prerequisite_goal_id"] for row in depends_on],
                blocks=[row["goal_id"] for row in blocks],
                can_parallelize=len(depends_on) == 0  # Can parallelize if no dependencies
            )
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[CONTEXT] Failed to get dependencies for {goal_id}: {e}")
            return DependencyInfo(goal_id=goal_id, depends_on=[], blocks=[])
    
    def calculate_dependency_multiplier(
        self,
        goal: Goal,
        dependency_info: DependencyInfo,
        completed_goals: Optional[List[str]] = None
    ) -> float:
        """
        Calculate multiplier based on dependency status.
        
        Args:
            goal: Goal to evaluate
            dependency_info: Dependency information
            completed_goals: List of completed goal IDs
            
        Returns:
            Multiplier (0.0-1.5)
        """
        completed_goals = completed_goals or []
        
        # Check if prerequisites are met
        unmet_dependencies = [
            dep for dep in dependency_info.depends_on
            if dep not in completed_goals
        ]
        
        if unmet_dependencies:
            # Has unmet dependencies - significantly reduce priority
            return 0.3
        
        # All dependencies met
        if dependency_info.blocks:
            # This goal blocks others - boost priority
            return 1.3
        
        return 1.0
    
    # ========================================================================
    # Combined Context Scoring
    # ========================================================================
    
    def apply_contextual_adjustments(
        self,
        goal: Goal,
        base_score: float,
        user_id: str,
        context: Optional[Dict] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Apply all contextual adjustments to a goal score.
        
        Args:
            goal: Goal to score
            base_score: Base arbiter score
            user_id: User ID
            context: Optional context dictionary
            
        Returns:
            Tuple of (adjusted_score, adjustment_breakdown)
        """
        context = context or {}
        adjustments = {}
        
        # Build contextual factors
        contextual_factors = ContextualFactors(
            time_of_day=self.get_time_of_day_period(),
            user_state=self.detect_user_state(user_id, context),
            day_of_week=datetime.now().strftime("%A").lower(),
            is_weekend=datetime.now().weekday() >= 5,
            current_load=context.get("current_load", 0.5),
            available_time_minutes=context.get("available_time_minutes"),
            location=context.get("location")
        )
        
        # Time of day adjustment
        time_multiplier = self.get_time_of_day_multiplier(goal, contextual_factors, user_id)
        adjustments["time_of_day"] = time_multiplier
        
        # User state adjustment
        state_multiplier = self.get_user_state_multiplier(goal, contextual_factors.user_state)
        adjustments["user_state"] = state_multiplier
        
        # Deadline urgency
        deadline_multiplier = self.calculate_deadline_urgency(goal)
        adjustments["deadline_urgency"] = deadline_multiplier
        
        # Dependency adjustment
        dependency_info = self.get_dependency_info(goal.goal_id)
        completed_goals = context.get("completed_goals", [])
        dependency_multiplier = self.calculate_dependency_multiplier(
            goal, dependency_info, completed_goals
        )
        adjustments["dependencies"] = dependency_multiplier
        
        # Calculate final score
        final_score = base_score
        for key, multiplier in adjustments.items():
            final_score *= multiplier
        
        # Clamp to valid range
        final_score = max(0.0, min(1.0, final_score))
        
        if self.logger:
            self.logger.debug(
                f"[CONTEXT] Goal {goal.goal_id}: {base_score:.3f} → {final_score:.3f} "
                f"(time: {time_multiplier:.2f}, state: {state_multiplier:.2f}, "
                f"deadline: {deadline_multiplier:.2f}, deps: {dependency_multiplier:.2f})"
            )
        
        return final_score, adjustments
