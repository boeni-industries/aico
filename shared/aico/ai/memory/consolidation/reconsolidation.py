"""
Memory Reconsolidation

Updates existing memories with new information while preventing catastrophic forgetting.
Implements confidence-weighted conflict resolution and variant management.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from aico.core.logging import get_logger

logger = get_logger("shared", "memory.consolidation.reconsolidation")


class ConflictType(Enum):
    """Types of memory conflicts."""
    CONTRADICTION = "contradiction"  # Direct contradiction
    REFINEMENT = "refinement"  # New info refines existing
    ALTERNATIVE = "alternative"  # Alternative interpretation
    SUPERSEDED = "superseded"  # Old info replaced by new


@dataclass
class ConflictResolution:
    """
    Result of conflict resolution between memories.
    
    Attributes:
        conflict_type: Type of conflict detected
        existing_id: ID of existing memory
        new_id: ID of new memory
        resolution_strategy: Strategy used to resolve conflict
        confidence_change: Change in confidence score
        action_taken: Action taken (update, create_variant, discard, supersede)
        metadata: Additional resolution metadata
    """
    conflict_type: ConflictType
    existing_id: str
    new_id: str
    resolution_strategy: str
    confidence_change: float
    action_taken: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "conflict_type": self.conflict_type.value,
            "existing_id": self.existing_id,
            "new_id": self.new_id,
            "resolution_strategy": self.resolution_strategy,
            "confidence_change": self.confidence_change,
            "action_taken": self.action_taken,
            "metadata": self.metadata
        }


class VariantManager:
    """
    Manages memory variants to prevent fact bloat.
    
    Limits the number of variants per fact and implements cleanup strategies.
    """
    
    def __init__(self, max_variants: int = 3, cleanup_days: int = 90):
        """
        Initialize variant manager.
        
        Args:
            max_variants: Maximum variants per fact
            cleanup_days: Days before cleaning up low-confidence variants
        """
        self.max_variants = max_variants
        self.cleanup_days = cleanup_days
    
    async def get_variant_count(
        self,
        fact_id: str,
        semantic_store
    ) -> int:
        """
        Get number of variants for a fact.
        
        Args:
            fact_id: Fact ID
            semantic_store: Semantic memory store instance
            
        Returns:
            Number of variants
        """
        # Query semantic store for variants
        variants = await semantic_store.query_variants(fact_id)
        return len(variants)
    
    async def get_weakest_variant(
        self,
        fact_id: str,
        semantic_store
    ) -> Optional[Dict[str, Any]]:
        """
        Get the weakest variant (lowest confidence).
        
        Args:
            fact_id: Fact ID
            semantic_store: Semantic memory store instance
            
        Returns:
            Weakest variant or None
        """
        variants = await semantic_store.query_variants(fact_id)
        
        if not variants:
            return None
        
        # Sort by confidence (ascending)
        variants.sort(key=lambda v: v.get("confidence", 0.0))
        return variants[0]
    
    async def should_create_variant(
        self,
        fact_id: str,
        new_confidence: float,
        semantic_store
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if a new variant should be created.
        
        Args:
            fact_id: Fact ID
            new_confidence: Confidence of new information
            semantic_store: Semantic memory store instance
            
        Returns:
            Tuple of (should_create, variant_to_replace_id)
        """
        variant_count = await self.get_variant_count(fact_id, semantic_store)
        
        if variant_count < self.max_variants:
            # Room for new variant
            return True, None
        
        # Check if new variant is stronger than weakest existing
        weakest = await self.get_weakest_variant(fact_id, semantic_store)
        
        if weakest and new_confidence > weakest.get("confidence", 0.0):
            # Replace weakest variant
            return True, weakest.get("id")
        
        # New variant too weak, don't create
        return False, None
    
    async def cleanup_old_variants(
        self,
        semantic_store,
        min_confidence: float = 0.3
    ) -> int:
        """
        Clean up old, low-confidence variants.
        
        Args:
            semantic_store: Semantic memory store instance
            min_confidence: Minimum confidence to keep
            
        Returns:
            Number of variants cleaned up
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.cleanup_days)
        
        # Query for old, low-confidence variants
        old_variants = await semantic_store.query_old_variants(
            cutoff_date=cutoff_date,
            max_confidence=min_confidence
        )
        
        cleaned = 0
        for variant in old_variants:
            try:
                await semantic_store.delete(variant["id"])
                cleaned += 1
            except Exception as e:
                logger.error("Failed to delete variant", extra={
                    "variant_id": variant["id"],
                    "error": str(e)
                })
        
        logger.info("Variant cleanup complete", extra={
            "cleaned_count": cleaned,
            "cutoff_date": cutoff_date.isoformat(),
            "min_confidence": min_confidence
        })
        
        return cleaned


class MemoryReconsolidator:
    """
    Handles memory reconsolidation - updating existing memories with new information.
    
    Implements confidence-weighted conflict resolution to prevent catastrophic forgetting
    while allowing memory updates.
    """
    
    def __init__(
        self,
        variant_manager: Optional[VariantManager] = None,
        similarity_threshold: float = 0.85
    ):
        """
        Initialize memory reconsolidator.
        
        Args:
            variant_manager: Variant manager instance
            similarity_threshold: Threshold for detecting related memories
        """
        self.variant_manager = variant_manager or VariantManager()
        self.similarity_threshold = similarity_threshold
    
    async def identify_conflicts(
        self,
        new_fact: Dict[str, Any],
        semantic_store
    ) -> List[Dict[str, Any]]:
        """
        Identify existing memories that conflict with new information.
        
        Args:
            new_fact: New fact to check
            semantic_store: Semantic memory store instance
            
        Returns:
            List of conflicting memories
        """
        # Query for similar memories
        similar = await semantic_store.query_similar(
            text=new_fact.get("text", ""),
            user_id=new_fact.get("user_id"),
            top_k=5,
            min_similarity=self.similarity_threshold
        )
        
        conflicts = []
        for memory in similar:
            # Check if memories actually conflict
            if self._is_conflicting(new_fact, memory):
                conflicts.append(memory)
        
        logger.debug("Conflicts identified", extra={
            "new_fact_id": new_fact.get("id"),
            "conflict_count": len(conflicts)
        })
        
        return conflicts
    
    def _is_conflicting(
        self,
        fact1: Dict[str, Any],
        fact2: Dict[str, Any]
    ) -> bool:
        """
        Determine if two facts conflict.
        
        Args:
            fact1: First fact
            fact2: Second fact
            
        Returns:
            True if facts conflict
        """
        # Simple heuristic: high similarity but different content
        # In production, this would use more sophisticated NLP
        
        text1 = fact1.get("text", "").lower()
        text2 = fact2.get("text", "").lower()
        
        # Check for negation patterns
        negation_words = ["not", "no", "never", "don't", "doesn't", "didn't"]
        
        has_negation_1 = any(word in text1 for word in negation_words)
        has_negation_2 = any(word in text2 for word in negation_words)
        
        # If one has negation and other doesn't, likely conflicting
        if has_negation_1 != has_negation_2:
            return True
        
        # Check for contradictory values (numbers, dates, etc.)
        # This is a simplified check
        return False
    
    async def reconsolidate_fact(
        self,
        new_fact: Dict[str, Any],
        existing_fact: Dict[str, Any],
        semantic_store
    ) -> ConflictResolution:
        """
        Reconsolidate a new fact with existing memory.
        
        Args:
            new_fact: New fact to integrate
            existing_fact: Existing fact in memory
            semantic_store: Semantic memory store instance
            
        Returns:
            ConflictResolution with action taken
        """
        new_confidence = new_fact.get("confidence", 0.5)
        existing_confidence = existing_fact.get("confidence", 0.5)
        
        # Determine conflict type
        conflict_type = self._determine_conflict_type(new_fact, existing_fact)
        
        # High confidence new fact - update existing
        if new_confidence > existing_confidence:
            await self._update_existing(
                new_fact,
                existing_fact,
                semantic_store
            )
            
            resolution = ConflictResolution(
                conflict_type=conflict_type,
                existing_id=existing_fact["id"],
                new_id=new_fact["id"],
                resolution_strategy="update_existing",
                confidence_change=new_confidence - existing_confidence,
                action_taken="updated",
                metadata={
                    "old_confidence": existing_confidence,
                    "new_confidence": new_confidence
                }
            )
        
        # Low confidence new fact - consider variant
        else:
            should_create, replace_id = await self.variant_manager.should_create_variant(
                existing_fact["id"],
                new_confidence,
                semantic_store
            )
            
            if should_create:
                if replace_id:
                    # Replace weakest variant
                    await semantic_store.delete(replace_id)
                    await self._create_variant(
                        new_fact,
                        existing_fact,
                        semantic_store
                    )
                    action = "replaced_variant"
                else:
                    # Create new variant
                    await self._create_variant(
                        new_fact,
                        existing_fact,
                        semantic_store
                    )
                    action = "created_variant"
                
                resolution = ConflictResolution(
                    conflict_type=conflict_type,
                    existing_id=existing_fact["id"],
                    new_id=new_fact["id"],
                    resolution_strategy="create_variant",
                    confidence_change=0.0,
                    action_taken=action,
                    metadata={
                        "replaced_id": replace_id
                    }
                )
            else:
                # Discard new fact (too weak)
                resolution = ConflictResolution(
                    conflict_type=conflict_type,
                    existing_id=existing_fact["id"],
                    new_id=new_fact["id"],
                    resolution_strategy="discard_new",
                    confidence_change=0.0,
                    action_taken="discarded",
                    metadata={
                        "reason": "confidence_too_low"
                    }
                )
        
        logger.info("Fact reconsolidated", extra=resolution.to_dict())
        
        return resolution
    
    def _determine_conflict_type(
        self,
        new_fact: Dict[str, Any],
        existing_fact: Dict[str, Any]
    ) -> ConflictType:
        """
        Determine the type of conflict between facts.
        
        Args:
            new_fact: New fact
            existing_fact: Existing fact
            
        Returns:
            ConflictType
        """
        # Simplified conflict type determination
        # In production, use more sophisticated NLP
        
        if self._is_conflicting(new_fact, existing_fact):
            return ConflictType.CONTRADICTION
        
        # Check if new fact refines existing
        new_text = new_fact.get("text", "")
        existing_text = existing_fact.get("text", "")
        
        if len(new_text) > len(existing_text) * 1.5:
            return ConflictType.REFINEMENT
        
        return ConflictType.ALTERNATIVE
    
    async def _update_existing(
        self,
        new_fact: Dict[str, Any],
        existing_fact: Dict[str, Any],
        semantic_store
    ) -> None:
        """
        Update existing fact with new information.
        
        Args:
            new_fact: New fact
            existing_fact: Existing fact to update
            semantic_store: Semantic memory store instance
        """
        # Mark existing as superseded
        existing_fact["superseded_by"] = new_fact["id"]
        existing_fact["superseded_at"] = datetime.utcnow().isoformat()
        
        await semantic_store.update(existing_fact)
        
        # Store new fact
        new_fact["supersedes"] = existing_fact["id"]
        await semantic_store.store(new_fact)
    
    async def _create_variant(
        self,
        new_fact: Dict[str, Any],
        existing_fact: Dict[str, Any],
        semantic_store
    ) -> None:
        """
        Create a variant of existing fact.
        
        Args:
            new_fact: New fact to store as variant
            existing_fact: Existing fact
            semantic_store: Semantic memory store instance
        """
        # Mark as variant
        new_fact["is_variant"] = True
        new_fact["variant_of"] = existing_fact["id"]
        new_fact["created_at"] = datetime.utcnow().isoformat()
        
        await semantic_store.store(new_fact)
    
    async def merge_memories(
        self,
        fact1: Dict[str, Any],
        fact2: Dict[str, Any],
        semantic_store
    ) -> Dict[str, Any]:
        """
        Merge two related memories into one.
        
        Args:
            fact1: First fact
            fact2: Second fact
            semantic_store: Semantic memory store instance
            
        Returns:
            Merged fact
        """
        # Combine texts
        merged_text = f"{fact1.get('text', '')} {fact2.get('text', '')}"
        
        # Average confidences weighted by access count
        access1 = fact1.get("access_count", 1)
        access2 = fact2.get("access_count", 1)
        total_access = access1 + access2
        
        merged_confidence = (
            fact1.get("confidence", 0.5) * access1 +
            fact2.get("confidence", 0.5) * access2
        ) / total_access
        
        # Create merged fact
        merged = {
            "id": f"merged_{fact1['id']}_{fact2['id']}",
            "text": merged_text,
            "confidence": merged_confidence,
            "user_id": fact1.get("user_id"),
            "merged_from": [fact1["id"], fact2["id"]],
            "created_at": datetime.utcnow().isoformat(),
            "access_count": total_access
        }
        
        # Store merged fact
        await semantic_store.store(merged)
        
        # Mark originals as superseded
        fact1["superseded_by"] = merged["id"]
        fact2["superseded_by"] = merged["id"]
        await semantic_store.update(fact1)
        await semantic_store.update(fact2)
        
        logger.info("Memories merged", extra={
            "fact1_id": fact1["id"],
            "fact2_id": fact2["id"],
            "merged_id": merged["id"]
        })
        
        return merged
