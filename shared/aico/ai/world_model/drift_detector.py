"""
Drift and Contradiction Detection for World Model

Detects temporal changes, contradictions, and applies confidence decay.
Phase 6.4: Drift & Contradiction Detection implementation.

Uses sliding windows and exponential decay for temporal analysis.
"""

import uuid
import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, UTC
from collections import defaultdict

from aico.core.logging import get_logger

from .models import DriftReport, Contradiction, ConfidenceDecayConfig


logger = get_logger("shared.world_model.drift_detector")


class DriftDetector:
    """Detects drift and contradictions in world model data."""
    
    def __init__(
        self,
        decay_config: Optional[ConfidenceDecayConfig] = None,
        drift_threshold: float = 0.5
    ):
        """Initialize drift detector.
        
        Args:
            decay_config: Configuration for confidence decay
            drift_threshold: Threshold for significant drift (0.0-1.0)
        """
        self.decay_config = decay_config or ConfidenceDecayConfig()
        self.drift_threshold = drift_threshold
        
        logger.info(
            f"[DRIFT_DETECTOR] Initialized (half_life={self.decay_config.half_life_days}d, "
            f"threshold={drift_threshold})"
        )
    
    def detect_drift(
        self,
        entity_id: str,
        entity_type: str,
        historical_states: List[Dict[str, Any]],
        window_days: int = 30
    ) -> Optional[DriftReport]:
        """Detect drift in entity state over time.
        
        Args:
            entity_id: Entity ID
            entity_type: Entity type
            historical_states: List of historical state snapshots with timestamps
            window_days: Window size for drift detection
            
        Returns:
            DriftReport if significant drift detected, None otherwise
        """
        if len(historical_states) < 2:
            return None
        
        # Sort by timestamp
        sorted_states = sorted(
            historical_states,
            key=lambda s: s.get("timestamp", datetime.min)
        )
        
        # Define windows
        now = datetime.now(UTC)
        window_start = now - timedelta(days=window_days)
        
        # Split into old and new states
        old_states = [s for s in sorted_states if s.get("timestamp", now) < window_start]
        new_states = [s for s in sorted_states if s.get("timestamp", now) >= window_start]
        
        if not old_states or not new_states:
            return None
        
        # Aggregate states
        old_aggregate = self._aggregate_states(old_states)
        new_aggregate = self._aggregate_states(new_states)
        
        # Calculate drift
        drift_score = self._calculate_drift_score(old_aggregate, new_aggregate)
        
        if drift_score < self.drift_threshold:
            return None
        
        # Determine drift type
        drift_type = self._classify_drift_type(old_aggregate, new_aggregate)
        
        # Create drift report
        report = DriftReport(
            drift_id=str(uuid.uuid4()),
            entity_id=entity_id,
            entity_type=entity_type,
            drift_type=drift_type,
            severity=drift_score,
            old_state=old_aggregate,
            new_state=new_aggregate,
            window_start=window_start,
            window_end=now,
            description=f"Detected {drift_type} drift in {entity_type} (severity={drift_score:.2f})",
        )
        
        logger.info(
            f"[DRIFT_DETECTOR] Drift detected for {entity_id}: "
            f"type={drift_type}, severity={drift_score:.2f}"
        )
        
        return report
    
    def detect_contradictions(
        self,
        facts: List[Dict[str, Any]]
    ) -> List[Contradiction]:
        """Detect contradictions between facts.
        
        Args:
            facts: List of facts with id, subject, predicate, object, confidence, timestamp
            
        Returns:
            List of detected Contradictions
        """
        contradictions = []
        
        # Group facts by (subject, predicate)
        fact_groups = defaultdict(list)
        for fact in facts:
            key = (fact.get("subject"), fact.get("predicate"))
            fact_groups[key].append(fact)
        
        # Check each group for contradictions
        for (subject, predicate), group_facts in fact_groups.items():
            if len(group_facts) < 2:
                continue
            
            # Sort by timestamp (most recent first)
            sorted_facts = sorted(
                group_facts,
                key=lambda f: f.get("timestamp", datetime.min),
                reverse=True
            )
            
            # Check for conflicting values
            for i in range(len(sorted_facts)):
                for j in range(i + 1, len(sorted_facts)):
                    fact1 = sorted_facts[i]
                    fact2 = sorted_facts[j]
                    
                    if self._are_contradictory(fact1, fact2):
                        contradiction = self._create_contradiction(fact1, fact2)
                        contradictions.append(contradiction)
        
        logger.info(f"[DRIFT_DETECTOR] Detected {len(contradictions)} contradictions")
        
        return contradictions
    
    def apply_confidence_decay(
        self,
        confidence: float,
        age_days: float
    ) -> float:
        """Apply confidence decay based on age.
        
        Args:
            confidence: Current confidence (0.0-1.0)
            age_days: Age in days
            
        Returns:
            Decayed confidence (0.0-1.0)
        """
        if age_days <= 0:
            return confidence
        
        if self.decay_config.decay_function == "exponential":
            # Exponential decay: C(t) = C0 * (0.5)^(t/half_life)
            decay_factor = math.pow(0.5, age_days / self.decay_config.half_life_days)
            decayed = confidence * decay_factor
        elif self.decay_config.decay_function == "linear":
            # Linear decay
            decay_rate = 0.5 / self.decay_config.half_life_days
            decayed = confidence - (decay_rate * age_days)
        else:
            # No decay
            decayed = confidence
        
        # Apply minimum confidence floor
        decayed = max(decayed, self.decay_config.min_confidence)
        
        return min(decayed, 1.0)
    
    def resolve_contradiction(
        self,
        contradiction: Contradiction,
        facts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Resolve contradiction using configured strategy.
        
        Args:
            contradiction: Contradiction to resolve
            facts: Full fact list for context
            
        Returns:
            Resolution dictionary with preferred_fact_id and reasoning
        """
        # Get the conflicting facts
        conflicting_facts = [
            f for f in facts if f.get("id") in contradiction.fact_ids
        ]
        
        if not conflicting_facts:
            return {"error": "Facts not found"}
        
        strategy = contradiction.resolution_strategy
        
        if strategy == "favor_recent":
            # Choose most recent fact
            sorted_facts = sorted(
                conflicting_facts,
                key=lambda f: f.get("timestamp", datetime.min),
                reverse=True
            )
            preferred = sorted_facts[0]
            reasoning = "Selected most recent fact"
        
        elif strategy == "favor_confident":
            # Choose highest confidence fact
            sorted_facts = sorted(
                conflicting_facts,
                key=lambda f: f.get("confidence", 0.0),
                reverse=True
            )
            preferred = sorted_facts[0]
            reasoning = "Selected highest confidence fact"
        
        elif strategy == "ask_user":
            # No automatic resolution
            return {
                "requires_user_input": True,
                "conflicting_facts": [f.get("id") for f in conflicting_facts],
                "reasoning": "User confirmation required for resolution"
            }
        
        elif strategy == "open_hypothesis":
            # Create hypothesis instead of resolving
            return {
                "create_hypothesis": True,
                "conflicting_facts": [f.get("id") for f in conflicting_facts],
                "reasoning": "Contradiction requires hypothesis for investigation"
            }
        
        else:
            # Default: favor recent
            sorted_facts = sorted(
                conflicting_facts,
                key=lambda f: f.get("timestamp", datetime.min),
                reverse=True
            )
            preferred = sorted_facts[0]
            reasoning = "Default: selected most recent fact"
        
        return {
            "preferred_fact_id": preferred.get("id"),
            "superseded_fact_ids": [
                f.get("id") for f in conflicting_facts if f.get("id") != preferred.get("id")
            ],
            "reasoning": reasoning,
            "strategy": strategy,
        }
    
    # Private helper methods
    
    def _aggregate_states(self, states: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate multiple states into representative state."""
        if not states:
            return {}
        
        # For now, use most recent state as representative
        # Could be enhanced with averaging, mode, etc.
        sorted_states = sorted(
            states,
            key=lambda s: s.get("timestamp", datetime.min),
            reverse=True
        )
        
        return sorted_states[0].get("state", {})
    
    def _calculate_drift_score(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> float:
        """Calculate drift score between two states."""
        if not old_state or not new_state:
            return 0.0
        
        # Calculate field-level differences
        all_keys = set(old_state.keys()) | set(new_state.keys())
        
        if not all_keys:
            return 0.0
        
        differences = []
        for key in all_keys:
            old_val = old_state.get(key)
            new_val = new_state.get(key)
            
            if old_val is None or new_val is None:
                # Missing key = significant drift
                differences.append(1.0)
            elif isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                # Numerical difference
                max_val = max(abs(old_val), abs(new_val), 1.0)
                diff = abs(old_val - new_val) / max_val
                differences.append(min(diff, 1.0))
            elif old_val != new_val:
                # Different values
                differences.append(1.0)
            else:
                # Same value
                differences.append(0.0)
        
        # Average difference
        return sum(differences) / len(differences)
    
    def _classify_drift_type(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> str:
        """Classify type of drift."""
        # Simple heuristic classification
        # Could be enhanced with more sophisticated logic
        
        new_keys = set(new_state.keys()) - set(old_state.keys())
        missing_keys = set(old_state.keys()) - set(new_state.keys())
        
        if new_keys or missing_keys:
            return "contextual"  # Structure changed
        
        # Check for temporal patterns (would need more data)
        # For now, default to behavioral
        return "behavioral"
    
    def _are_contradictory(
        self,
        fact1: Dict[str, Any],
        fact2: Dict[str, Any]
    ) -> bool:
        """Check if two facts are contradictory."""
        # Same subject and predicate, different objects
        if fact1.get("subject") != fact2.get("subject"):
            return False
        if fact1.get("predicate") != fact2.get("predicate"):
            return False
        
        obj1 = fact1.get("object")
        obj2 = fact2.get("object")
        
        # Different objects = contradiction
        return obj1 != obj2
    
    def _create_contradiction(
        self,
        fact1: Dict[str, Any],
        fact2: Dict[str, Any]
    ) -> Contradiction:
        """Create contradiction from two conflicting facts."""
        # Determine severity based on confidence and recency
        conf1 = fact1.get("confidence", 0.5)
        conf2 = fact2.get("confidence", 0.5)
        severity = (conf1 + conf2) / 2  # Higher confidence = more severe
        
        # Determine resolution strategy
        time1 = fact1.get("timestamp", datetime.min)
        time2 = fact2.get("timestamp", datetime.min)
        time_diff = abs((time1 - time2).days) if time1 and time2 else 0
        
        if time_diff < 7:
            # Recent contradiction - ask user
            strategy = "ask_user"
        elif abs(conf1 - conf2) > 0.3:
            # Clear confidence difference - favor confident
            strategy = "favor_confident"
        else:
            # Default - favor recent
            strategy = "favor_recent"
        
        description = (
            f"Contradiction: {fact1.get('subject')} {fact1.get('predicate')} "
            f"{fact1.get('object')} vs {fact2.get('object')}"
        )
        
        return Contradiction(
            contradiction_id=str(uuid.uuid4()),
            fact_ids=[fact1.get("id"), fact2.get("id")],
            description=description,
            severity=severity,
            resolution_strategy=strategy,
        )
