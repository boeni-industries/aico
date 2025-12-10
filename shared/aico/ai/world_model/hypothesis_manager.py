"""
Hypothesis Management for World Model

Generates, tests, and tracks hypotheses about user state and patterns.
Phase 6.4: Hypothesis Generation & Testing implementation.

Uses Bayesian updating for confidence calculation.
"""

import uuid
import math
from typing import List, Dict, Any, Optional
from datetime import datetime

from aico.core.logging import get_logger

from .models import Hypothesis, HypothesisTestResult


logger = get_logger("shared", "world_model.hypothesis_manager")


class HypothesisManager:
    """Manages hypothesis lifecycle with Bayesian updating."""
    
    def __init__(
        self,
        prior_confidence: float = 0.5,
        confirmation_threshold: float = 0.8,
        rejection_threshold: float = 0.2
    ):
        """Initialize hypothesis manager.
        
        Args:
            prior_confidence: Default prior confidence for new hypotheses
            confirmation_threshold: Confidence threshold for confirmation
            rejection_threshold: Confidence threshold for rejection
        """
        self.prior_confidence = prior_confidence
        self.confirmation_threshold = confirmation_threshold
        self.rejection_threshold = rejection_threshold
        self.hypotheses: Dict[str, Hypothesis] = {}
        
        logger.info(
            f"[HYPOTHESIS_MGR] Initialized (prior={prior_confidence}, "
            f"confirm={confirmation_threshold}, reject={rejection_threshold})"
        )
    
    def generate_hypothesis(
        self,
        user_id: str,
        description: str,
        hypothesis_type: str,
        affected_entities: List[str],
        initial_evidence: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Hypothesis:
        """Generate a new hypothesis.
        
        Args:
            user_id: User ID
            description: Human-readable description
            hypothesis_type: Type (state_change, pattern, relationship, behavioral)
            affected_entities: List of affected entity IDs
            initial_evidence: Optional initial evidence IDs
            metadata: Optional metadata
            
        Returns:
            New Hypothesis
        """
        hypothesis = Hypothesis(
            hypothesis_id=str(uuid.uuid4()),
            user_id=user_id,
            description=description,
            hypothesis_type=hypothesis_type,
            affected_entities=affected_entities,
            confidence=self.prior_confidence,
            status="open",
            evidence=initial_evidence or [],
            metadata=metadata or {},
        )
        
        self.hypotheses[hypothesis.hypothesis_id] = hypothesis
        
        logger.info(
            f"[HYPOTHESIS_MGR] Generated hypothesis {hypothesis.hypothesis_id}: "
            f"{description} (type={hypothesis_type})"
        )
        
        return hypothesis
    
    def test_hypothesis(
        self,
        hypothesis_id: str,
        test_type: str,
        supports_hypothesis: bool,
        evidence_ids: Optional[List[str]] = None,
        likelihood_ratio: Optional[float] = None,
        notes: Optional[str] = None
    ) -> HypothesisTestResult:
        """Test hypothesis with new evidence.
        
        Uses Bayesian updating: P(H|E) = P(E|H) * P(H) / P(E)
        
        Args:
            hypothesis_id: Hypothesis ID
            test_type: Type of test (evidence_check, pattern_match, user_confirmation)
            supports_hypothesis: Whether evidence supports hypothesis
            evidence_ids: Optional evidence IDs
            likelihood_ratio: Optional custom likelihood ratio (default: 2.0 or 0.5)
            notes: Optional notes
            
        Returns:
            HypothesisTestResult
        """
        if hypothesis_id not in self.hypotheses:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")
        
        hypothesis = self.hypotheses[hypothesis_id]
        
        # Calculate likelihood ratio
        if likelihood_ratio is None:
            # Default: supporting evidence doubles odds, counter-evidence halves it
            likelihood_ratio = 2.0 if supports_hypothesis else 0.5
        
        # Bayesian update
        old_confidence = hypothesis.confidence
        new_confidence = self._bayesian_update(old_confidence, likelihood_ratio)
        confidence_delta = new_confidence - old_confidence
        
        # Update hypothesis
        hypothesis.confidence = new_confidence
        hypothesis.updated_at = datetime.utcnow()
        
        if evidence_ids:
            if supports_hypothesis:
                hypothesis.evidence.extend(evidence_ids)
            else:
                hypothesis.counter_evidence.extend(evidence_ids)
        
        # Check status transitions
        self._update_hypothesis_status(hypothesis)
        
        # Create test result
        result = HypothesisTestResult(
            hypothesis_id=hypothesis_id,
            test_type=test_type,
            supports_hypothesis=supports_hypothesis,
            confidence_delta=confidence_delta,
            evidence_ids=evidence_ids or [],
            notes=notes,
        )
        
        logger.info(
            f"[HYPOTHESIS_MGR] Tested {hypothesis_id}: "
            f"confidence {old_confidence:.2f} → {new_confidence:.2f} "
            f"(delta={confidence_delta:+.2f}, status={hypothesis.status})"
        )
        
        return result
    
    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Get hypothesis by ID."""
        return self.hypotheses.get(hypothesis_id)
    
    def get_hypotheses_for_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        hypothesis_type: Optional[str] = None
    ) -> List[Hypothesis]:
        """Get hypotheses for a user.
        
        Args:
            user_id: User ID
            status: Optional status filter
            hypothesis_type: Optional type filter
            
        Returns:
            List of matching hypotheses
        """
        results = []
        
        for hypothesis in self.hypotheses.values():
            if hypothesis.user_id != user_id:
                continue
            if status and hypothesis.status != status:
                continue
            if hypothesis_type and hypothesis.hypothesis_type != hypothesis_type:
                continue
            
            results.append(hypothesis)
        
        return results
    
    def get_open_hypotheses(self, user_id: Optional[str] = None) -> List[Hypothesis]:
        """Get all open hypotheses, optionally filtered by user."""
        results = []
        
        for hypothesis in self.hypotheses.values():
            if hypothesis.status == "open":
                if user_id is None or hypothesis.user_id == user_id:
                    results.append(hypothesis)
        
        return results
    
    def confirm_hypothesis(
        self,
        hypothesis_id: str,
        confirmation_source: str = "system"
    ) -> Hypothesis:
        """Manually confirm a hypothesis.
        
        Args:
            hypothesis_id: Hypothesis ID
            confirmation_source: Source of confirmation (system, user, external)
            
        Returns:
            Updated Hypothesis
        """
        if hypothesis_id not in self.hypotheses:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")
        
        hypothesis = self.hypotheses[hypothesis_id]
        hypothesis.status = "confirmed"
        hypothesis.confidence = 1.0
        hypothesis.confirmed_at = datetime.utcnow()
        hypothesis.updated_at = datetime.utcnow()
        hypothesis.metadata["confirmation_source"] = confirmation_source
        
        logger.info(
            f"[HYPOTHESIS_MGR] Confirmed hypothesis {hypothesis_id} "
            f"(source={confirmation_source})"
        )
        
        return hypothesis
    
    def reject_hypothesis(
        self,
        hypothesis_id: str,
        rejection_reason: Optional[str] = None
    ) -> Hypothesis:
        """Manually reject a hypothesis.
        
        Args:
            hypothesis_id: Hypothesis ID
            rejection_reason: Optional reason for rejection
            
        Returns:
            Updated Hypothesis
        """
        if hypothesis_id not in self.hypotheses:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")
        
        hypothesis = self.hypotheses[hypothesis_id]
        hypothesis.status = "rejected"
        hypothesis.confidence = 0.0
        hypothesis.updated_at = datetime.utcnow()
        
        if rejection_reason:
            hypothesis.metadata["rejection_reason"] = rejection_reason
        
        logger.info(
            f"[HYPOTHESIS_MGR] Rejected hypothesis {hypothesis_id} "
            f"(reason={rejection_reason})"
        )
        
        return hypothesis
    
    def generate_from_pattern(
        self,
        user_id: str,
        pattern: Dict[str, Any]
    ) -> Optional[Hypothesis]:
        """Generate hypothesis from detected pattern.
        
        Args:
            user_id: User ID
            pattern: Pattern dictionary with type, entities, confidence, etc.
            
        Returns:
            Generated Hypothesis or None if pattern is weak
        """
        pattern_type = pattern.get("type", "unknown")
        pattern_confidence = pattern.get("confidence", 0.5)
        
        # Only generate hypothesis if pattern is strong enough
        if pattern_confidence < 0.6:
            logger.debug(
                f"[HYPOTHESIS_MGR] Pattern too weak for hypothesis: "
                f"confidence={pattern_confidence}"
            )
            return None
        
        # Map pattern type to hypothesis type
        hypothesis_type_map = {
            "temporal": "behavioral",
            "frequency": "pattern",
            "relationship": "relationship",
            "state": "state_change",
        }
        hypothesis_type = hypothesis_type_map.get(pattern_type, "pattern")
        
        # Generate description
        description = pattern.get("description", f"Pattern detected: {pattern_type}")
        
        # Extract affected entities
        affected_entities = pattern.get("entities", [])
        
        # Generate hypothesis
        hypothesis = self.generate_hypothesis(
            user_id=user_id,
            description=description,
            hypothesis_type=hypothesis_type,
            affected_entities=affected_entities,
            metadata={
                "pattern": pattern,
                "generated_from": "pattern_detection",
            }
        )
        
        # Adjust initial confidence based on pattern strength
        hypothesis.confidence = pattern_confidence
        
        logger.info(
            f"[HYPOTHESIS_MGR] Generated hypothesis from pattern: "
            f"{description} (confidence={pattern_confidence:.2f})"
        )
        
        return hypothesis
    
    # Private helper methods
    
    def _bayesian_update(
        self,
        prior: float,
        likelihood_ratio: float
    ) -> float:
        """Apply Bayesian update to confidence.
        
        Uses odds form: posterior_odds = prior_odds * likelihood_ratio
        Then converts back to probability.
        
        Args:
            prior: Prior probability (0.0-1.0)
            likelihood_ratio: Likelihood ratio (>1 supports, <1 opposes)
            
        Returns:
            Posterior probability (0.0-1.0)
        """
        # Convert probability to odds
        prior_odds = prior / (1 - prior) if prior < 1.0 else float('inf')
        
        # Update odds
        posterior_odds = prior_odds * likelihood_ratio
        
        # Convert back to probability
        posterior = posterior_odds / (1 + posterior_odds)
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, posterior))
    
    def _update_hypothesis_status(self, hypothesis: Hypothesis) -> None:
        """Update hypothesis status based on confidence."""
        if hypothesis.status in ["confirmed", "rejected"]:
            # Don't change terminal states
            return
        
        if hypothesis.confidence >= self.confirmation_threshold:
            hypothesis.status = "confirmed"
            hypothesis.confirmed_at = datetime.utcnow()
            logger.info(
                f"[HYPOTHESIS_MGR] Auto-confirmed hypothesis {hypothesis.hypothesis_id} "
                f"(confidence={hypothesis.confidence:.2f})"
            )
        elif hypothesis.confidence <= self.rejection_threshold:
            hypothesis.status = "rejected"
            logger.info(
                f"[HYPOTHESIS_MGR] Auto-rejected hypothesis {hypothesis.hypothesis_id} "
                f"(confidence={hypothesis.confidence:.2f})"
            )
        elif hypothesis.confidence >= 0.7 and hypothesis.status == "open":
            # High confidence but not confirmed - needs user confirmation
            hypothesis.status = "needs_user_confirmation"
            logger.info(
                f"[HYPOTHESIS_MGR] Hypothesis {hypothesis.hypothesis_id} needs user confirmation "
                f"(confidence={hypothesis.confidence:.2f})"
            )
