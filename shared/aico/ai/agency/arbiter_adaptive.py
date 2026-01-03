"""
Adaptive Scoring for Goal Arbiter - Phase 6.5

Implements multi-armed bandit and reinforcement learning for dynamic weight optimization.
Learns from goal outcomes to continuously improve scoring accuracy.
"""

from __future__ import annotations

import json
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass, field
from enum import Enum

from aico.data.libsql import EncryptedLibSQLConnection


# ============================================================================
# Data Models
# ============================================================================

class BanditAlgorithm(str, Enum):
    """Multi-armed bandit algorithms."""
    EPSILON_GREEDY = "epsilon_greedy"
    UCB1 = "ucb1"  # Upper Confidence Bound
    THOMPSON_SAMPLING = "thompson_sampling"
    EXP3 = "exp3"  # Exponential-weight algorithm for Exploration and Exploitation


@dataclass
class WeightArm:
    """Represents one arm in the multi-armed bandit (one weight configuration)."""
    
    arm_id: str
    weights: Dict[str, float]
    pulls: int = 0
    total_reward: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    last_pulled: Optional[datetime] = None
    
    @property
    def average_reward(self) -> float:
        """Calculate average reward for this arm."""
        return self.total_reward / self.pulls if self.pulls > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate for this arm."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive scoring."""
    
    algorithm: BanditAlgorithm = BanditAlgorithm.UCB1
    epsilon: float = 0.1  # For epsilon-greedy
    exploration_factor: float = 2.0  # For UCB1
    learning_rate: float = 0.1  # For weight updates
    min_pulls_per_arm: int = 10  # Minimum pulls before optimization
    evaluation_window_days: int = 7  # Window for calculating rewards
    enable_ab_testing: bool = True  # Enable A/B testing framework


# ============================================================================
# Adaptive Scoring Engine
# ============================================================================

class AdaptiveScoringEngine:
    """
    Implements adaptive scoring using multi-armed bandit algorithms.
    
    Learns optimal weight configurations by treating each weight set as an "arm"
    and using goal outcomes as rewards. Continuously explores new configurations
    while exploiting known good ones.
    """
    
    def __init__(
        self,
        db: EncryptedLibSQLConnection,
        config: Optional[AdaptiveConfig] = None,
        logger=None
    ):
        self.db = db
        self.config = config or AdaptiveConfig()
        self.logger = logger
        
        # Initialize arms (weight configurations)
        self.arms: Dict[str, WeightArm] = {}
        self._load_arms()
        
        # If no arms exist, create default configurations
        if not self.arms:
            self._initialize_default_arms()
    
    # ========================================================================
    # Arm Management
    # ========================================================================
    
    def _load_arms(self) -> None:
        """Load existing arms from database."""
        try:
            rows = self.db.fetch_all(
                """
                SELECT arm_id, weights_json, pulls, total_reward,
                       success_count, failure_count, last_pulled
                FROM arbiter_bandit_arms
                WHERE active = 1
                """
            )
            
            for row in rows:
                self.arms[row["arm_id"]] = WeightArm(
                    arm_id=row["arm_id"],
                    weights=json.loads(row["weights_json"]),
                    pulls=row["pulls"],
                    total_reward=row["total_reward"],
                    success_count=row["success_count"],
                    failure_count=row["failure_count"],
                    last_pulled=datetime.fromisoformat(row["last_pulled"]).replace(tzinfo=UTC) if row["last_pulled"] else None
                )
            
            if self.logger and self.arms:
                self.logger.debug(f"[ADAPTIVE] Loaded {len(self.arms)} bandit arms")
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[ADAPTIVE] Failed to load arms: {e}")
    
    def _initialize_default_arms(self) -> None:
        """Initialize default arm configurations."""
        # Default balanced configuration
        default_weights = {
            "priority": 0.30,
            "origin": 0.20,
            "freshness": 0.15,
            "curiosity_score": 0.15,
            "personality_fit": 0.10,
            "emotion_boost": 0.10,
        }
        
        # Create variations to explore
        arm_configs = [
            ("balanced", default_weights),
            ("priority_focused", {**default_weights, "priority": 0.40, "freshness": 0.10, "curiosity_score": 0.10}),
            ("curiosity_focused", {**default_weights, "curiosity_score": 0.25, "priority": 0.25, "origin": 0.15}),
            ("user_focused", {**default_weights, "origin": 0.30, "priority": 0.25, "freshness": 0.10}),
            ("emotion_aware", {**default_weights, "emotion_boost": 0.20, "personality_fit": 0.15, "priority": 0.25}),
        ]
        
        for arm_id, weights in arm_configs:
            arm = WeightArm(arm_id=arm_id, weights=weights)
            self.arms[arm_id] = arm
            self._save_arm(arm)
        
        if self.logger:
            self.logger.debug(f"[ADAPTIVE] Initialized {len(arm_configs)} default arms")
    
    def _save_arm(self, arm: WeightArm) -> None:
        """Save or update an arm in the database."""
        try:
            now = datetime.now(UTC).isoformat()
            self.db.execute(
                """
                INSERT OR REPLACE INTO arbiter_bandit_arms (
                    arm_id, weights_json, pulls, total_reward,
                    success_count, failure_count, last_pulled, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    arm.arm_id,
                    json.dumps(arm.weights),
                    arm.pulls,
                    arm.total_reward,
                    arm.success_count,
                    arm.failure_count,
                    arm.last_pulled.isoformat() if arm.last_pulled else None,
                    now,
                    now
                )
            )
            self.db.commit()  # Ensure changes are committed
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ADAPTIVE] Failed to save arm {arm.arm_id}: {e}")
    
    # ========================================================================
    # Bandit Algorithms
    # ========================================================================
    
    def select_arm(self, user_id: Optional[str] = None) -> Tuple[str, Dict[str, float]]:
        """
        Select an arm (weight configuration) using the configured algorithm.
        
        Args:
            user_id: Optional user ID for user-specific selection
            
        Returns:
            Tuple of (arm_id, weights)
        """
        if self.config.algorithm == BanditAlgorithm.EPSILON_GREEDY:
            return self._epsilon_greedy()
        elif self.config.algorithm == BanditAlgorithm.UCB1:
            return self._ucb1()
        elif self.config.algorithm == BanditAlgorithm.THOMPSON_SAMPLING:
            return self._thompson_sampling()
        else:
            # Default to UCB1
            return self._ucb1()
    
    def _epsilon_greedy(self) -> Tuple[str, Dict[str, float]]:
        """
        Epsilon-greedy algorithm: explore with probability epsilon, exploit otherwise.
        """
        import random
        
        if random.random() < self.config.epsilon:
            # Explore: random arm
            arm = random.choice(list(self.arms.values()))
            if self.logger:
                self.logger.debug(f"[ADAPTIVE] Exploring arm: {arm.arm_id}")
        else:
            # Exploit: best arm
            arm = max(self.arms.values(), key=lambda a: a.average_reward)
            if self.logger:
                self.logger.debug(f"[ADAPTIVE] Exploiting arm: {arm.arm_id} (avg reward: {arm.average_reward:.3f})")
        
        return arm.arm_id, arm.weights
    
    def _ucb1(self) -> Tuple[str, Dict[str, float]]:
        """
        UCB1 algorithm: Upper Confidence Bound.
        Balances exploration and exploitation using confidence bounds.
        """
        total_pulls = sum(arm.pulls for arm in self.arms.values())
        
        if total_pulls == 0:
            # No data yet, pick randomly
            import random
            arm = random.choice(list(self.arms.values()))
            return arm.arm_id, arm.weights
        
        # Calculate UCB score for each arm
        best_arm = None
        best_score = float('-inf')
        
        for arm in self.arms.values():
            if arm.pulls == 0:
                # Unpulled arms get infinite score (explore first)
                return arm.arm_id, arm.weights
            
            # UCB1 formula: avg_reward + c * sqrt(ln(total_pulls) / pulls)
            exploration_bonus = self.config.exploration_factor * math.sqrt(
                math.log(total_pulls) / arm.pulls
            )
            ucb_score = arm.average_reward + exploration_bonus
            
            if ucb_score > best_score:
                best_score = ucb_score
                best_arm = arm
        
        if self.logger:
            self.logger.debug(
                f"[ADAPTIVE] UCB1 selected {best_arm.arm_id} "
                f"(score: {best_score:.3f}, pulls: {best_arm.pulls})"
            )
        
        return best_arm.arm_id, best_arm.weights
    
    def _thompson_sampling(self) -> Tuple[str, Dict[str, float]]:
        """
        Thompson Sampling: Bayesian approach using Beta distribution.
        Samples from posterior distribution of each arm's success probability.
        """
        import random
        
        best_arm = None
        best_sample = float('-inf')
        
        for arm in self.arms.values():
            # Beta distribution parameters (success + 1, failure + 1)
            alpha = arm.success_count + 1
            beta = arm.failure_count + 1
            
            # Sample from Beta(alpha, beta)
            sample = random.betavariate(alpha, beta)
            
            if sample > best_sample:
                best_sample = sample
                best_arm = arm
        
        if self.logger:
            self.logger.debug(
                f"[ADAPTIVE] Thompson sampling selected {best_arm.arm_id} "
                f"(sample: {best_sample:.3f})"
            )
        
        return best_arm.arm_id, best_arm.weights
    
    # ========================================================================
    # Reward & Learning
    # ========================================================================
    
    def update_arm(
        self,
        arm_id: str,
        reward: float,
        success: bool,
        goal_id: Optional[str] = None
    ) -> None:
        """
        Update an arm with outcome feedback.
        
        Args:
            arm_id: ID of the arm that was used
            reward: Reward value (0.0-1.0, based on goal outcome)
            success: Whether the goal succeeded
            goal_id: Optional goal ID for tracking
        """
        if arm_id not in self.arms:
            if self.logger:
                self.logger.warning(f"[ADAPTIVE] Unknown arm: {arm_id}")
            return
        
        arm = self.arms[arm_id]
        arm.pulls += 1
        arm.total_reward += reward
        arm.last_pulled = datetime.now(UTC)
        
        if success:
            arm.success_count += 1
        else:
            arm.failure_count += 1
        
        self._save_arm(arm)
        
        if self.logger:
            self.logger.info(
                f"[ADAPTIVE] Updated arm {arm_id}: reward={reward:.3f}, "
                f"avg_reward={arm.average_reward:.3f}, success_rate={arm.success_rate:.3f}"
            )
        
        # Check if we should optimize weights
        if arm.pulls >= self.config.min_pulls_per_arm:
            self._maybe_optimize_weights()
    
    def _maybe_optimize_weights(self) -> None:
        """
        Periodically optimize weights based on accumulated data.
        Creates new arm configurations based on successful patterns.
        """
        # Only optimize if all arms have minimum pulls
        if not all(arm.pulls >= self.config.min_pulls_per_arm for arm in self.arms.values()):
            return
        
        # Find best performing arm
        best_arm = max(self.arms.values(), key=lambda a: a.average_reward)
        
        if self.logger:
            self.logger.info(
                f"[ADAPTIVE] Best arm: {best_arm.arm_id} "
                f"(avg_reward: {best_arm.average_reward:.3f}, "
                f"success_rate: {best_arm.success_rate:.3f})"
            )
        
        # Create variation of best arm (gradient-based exploration)
        # This is a simple approach; more sophisticated methods could be used
        if best_arm.average_reward > 0.6 and len(self.arms) < 10:
            self._create_arm_variation(best_arm)
    
    def _create_arm_variation(self, base_arm: WeightArm) -> None:
        """Create a new arm as variation of a successful arm."""
        import random
        
        # Create small random variations
        new_weights = {}
        for key, value in base_arm.weights.items():
            # Add small random perturbation
            perturbation = random.uniform(-0.05, 0.05)
            new_weights[key] = max(0.0, min(1.0, value + perturbation))
        
        # Normalize to sum to 1.0
        total = sum(new_weights.values())
        new_weights = {k: v / total for k, v in new_weights.items()}
        
        # Create new arm
        arm_id = f"optimized_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        new_arm = WeightArm(arm_id=arm_id, weights=new_weights)
        self.arms[arm_id] = new_arm
        self._save_arm(new_arm)
        
        if self.logger:
            self.logger.info(f"[ADAPTIVE] Created new arm variation: {arm_id}")
    
    # ========================================================================
    # A/B Testing Framework
    # ========================================================================
    
    def start_ab_test(
        self,
        test_name: str,
        arm_a_id: str,
        arm_b_id: str,
        duration_days: int = 7
    ) -> str:
        """
        Start an A/B test comparing two arms.
        
        Args:
            test_name: Name of the test
            arm_a_id: First arm to test
            arm_b_id: Second arm to test
            duration_days: Test duration in days
            
        Returns:
            Test ID
        """
        import uuid
        
        test_id = str(uuid.uuid4())
        end_date = datetime.now(UTC) + timedelta(days=duration_days)
        
        try:
            self.db.execute(
                """
                INSERT INTO arbiter_ab_tests (
                    test_id, test_name, arm_a_id, arm_b_id,
                    start_date, end_date, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
                """,
                (
                    test_id,
                    test_name,
                    arm_a_id,
                    arm_b_id,
                    datetime.now(UTC).isoformat(),
                    end_date.isoformat(),
                    datetime.now(UTC).isoformat()
                )
            )
            
            if self.logger:
                self.logger.info(
                    f"[ADAPTIVE] Started A/B test '{test_name}': "
                    f"{arm_a_id} vs {arm_b_id} (duration: {duration_days} days)"
                )
            
            return test_id
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ADAPTIVE] Failed to start A/B test: {e}")
            raise
    
    def get_ab_test_results(self, test_id: str) -> Dict:
        """Get results of an A/B test."""
        try:
            test = self.db.fetch_one(
                "SELECT * FROM arbiter_ab_tests WHERE test_id = ?",
                (test_id,)
            )
            
            if not test:
                return {"error": "Test not found"}
            
            arm_a = self.arms.get(test["arm_a_id"])
            arm_b = self.arms.get(test["arm_b_id"])
            
            if not arm_a or not arm_b:
                return {"error": "Arms not found"}
            
            return {
                "test_id": test_id,
                "test_name": test["test_name"],
                "status": test["status"],
                "arm_a": {
                    "arm_id": arm_a.arm_id,
                    "pulls": arm_a.pulls,
                    "average_reward": arm_a.average_reward,
                    "success_rate": arm_a.success_rate,
                },
                "arm_b": {
                    "arm_id": arm_b.arm_id,
                    "pulls": arm_b.pulls,
                    "average_reward": arm_b.average_reward,
                    "success_rate": arm_b.success_rate,
                },
                "winner": arm_a.arm_id if arm_a.average_reward > arm_b.average_reward else arm_b.arm_id,
                "confidence": abs(arm_a.average_reward - arm_b.average_reward)
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ADAPTIVE] Failed to get A/B test results: {e}")
            return {"error": str(e)}
