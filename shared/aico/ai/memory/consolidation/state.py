"""
Consolidation State Tracking

Tracks consolidation progress and state for monitoring and recovery.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

from aico.core.logging import get_logger

logger = get_logger("shared", "memory.consolidation.state")


class ConsolidationStatus(Enum):
    """Status of consolidation process."""
    IDLE = "idle"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ConsolidationProgress:
    """
    Progress tracking for consolidation.
    
    Attributes:
        total_users: Total users to consolidate
        completed_users: Users completed
        failed_users: Users that failed
        total_experiences: Total experiences to process
        processed_experiences: Experiences processed
        current_user: Currently processing user
        started_at: When consolidation started
        estimated_completion: Estimated completion time
    """
    total_users: int
    completed_users: int = 0
    failed_users: int = 0
    total_experiences: int = 0
    processed_experiences: int = 0
    current_user: Optional[str] = None
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    @property
    def progress_percent(self) -> float:
        """Get progress percentage."""
        if self.total_users == 0:
            return 0.0
        return (self.completed_users / self.total_users) * 100.0
    
    @property
    def is_complete(self) -> bool:
        """Check if consolidation is complete."""
        return self.completed_users + self.failed_users >= self.total_users
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_users": self.total_users,
            "completed_users": self.completed_users,
            "failed_users": self.failed_users,
            "total_experiences": self.total_experiences,
            "processed_experiences": self.processed_experiences,
            "current_user": self.current_user,
            "progress_percent": self.progress_percent,
            "is_complete": self.is_complete,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None
        }


@dataclass
class ConsolidationState:
    """
    Complete state of consolidation system.
    
    Attributes:
        status: Current consolidation status
        progress: Progress tracking
        last_run: When consolidation last ran
        next_scheduled: When next consolidation is scheduled
        errors: Recent errors
        metadata: Additional state metadata
    """
    status: ConsolidationStatus
    progress: Optional[ConsolidationProgress] = None
    last_run: Optional[datetime] = None
    next_scheduled: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "progress": self.progress.to_dict() if self.progress else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_scheduled": self.next_scheduled.isoformat() if self.next_scheduled else None,
            "errors": self.errors,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConsolidationState":
        """Create from dictionary."""
        progress_data = data.get("progress")
        progress = None
        if progress_data:
            progress = ConsolidationProgress(
                total_users=progress_data["total_users"],
                completed_users=progress_data.get("completed_users", 0),
                failed_users=progress_data.get("failed_users", 0),
                total_experiences=progress_data.get("total_experiences", 0),
                processed_experiences=progress_data.get("processed_experiences", 0),
                current_user=progress_data.get("current_user"),
                started_at=datetime.fromisoformat(progress_data["started_at"]) if progress_data.get("started_at") else None,
                estimated_completion=datetime.fromisoformat(progress_data["estimated_completion"]) if progress_data.get("estimated_completion") else None
            )
        
        return cls(
            status=ConsolidationStatus(data["status"]),
            progress=progress,
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            next_scheduled=datetime.fromisoformat(data["next_scheduled"]) if data.get("next_scheduled") else None,
            errors=data.get("errors", []),
            metadata=data.get("metadata", {})
        )


class ConsolidationStateManager:
    """
    Manages consolidation state persistence and retrieval.
    
    Provides methods for tracking consolidation progress, storing state,
    and recovering from failures.
    """
    
    def __init__(self):
        """Initialize state manager."""
        self._current_state = ConsolidationState(
            status=ConsolidationStatus.IDLE
        )
        self._state_history: List[ConsolidationState] = []
    
    def get_current_state(self) -> ConsolidationState:
        """Get current consolidation state."""
        return self._current_state
    
    def start_consolidation(
        self,
        total_users: int,
        total_experiences: int
    ) -> None:
        """
        Mark consolidation as started.
        
        Args:
            total_users: Total users to consolidate
            total_experiences: Total experiences to process
        """
        self._current_state.status = ConsolidationStatus.RUNNING
        self._current_state.progress = ConsolidationProgress(
            total_users=total_users,
            total_experiences=total_experiences,
            started_at=datetime.utcnow()
        )
        
        logger.info("Consolidation started", extra={
            "total_users": total_users,
            "total_experiences": total_experiences
        })
    
    def update_progress(
        self,
        user_id: str,
        experiences_processed: int,
        success: bool = True
    ) -> None:
        """
        Update consolidation progress.
        
        Args:
            user_id: User that was processed
            experiences_processed: Number of experiences processed
            success: Whether processing was successful
        """
        if not self._current_state.progress:
            logger.warning("Cannot update progress: no active consolidation")
            return
        
        progress = self._current_state.progress
        progress.current_user = user_id
        progress.processed_experiences += experiences_processed
        
        if success:
            progress.completed_users += 1
        else:
            progress.failed_users += 1
        
        # Update estimated completion
        if progress.started_at and progress.completed_users > 0:
            elapsed = (datetime.utcnow() - progress.started_at).total_seconds()
            avg_time_per_user = elapsed / progress.completed_users
            remaining_users = progress.total_users - progress.completed_users - progress.failed_users
            estimated_seconds = remaining_users * avg_time_per_user
            progress.estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_seconds)
        
        logger.debug("Progress updated", extra={
            "user_id": user_id,
            "experiences_processed": experiences_processed,
            "success": success,
            "progress_percent": progress.progress_percent
        })
    
    def complete_consolidation(self) -> None:
        """Mark consolidation as completed."""
        if not self._current_state.progress:
            logger.warning("Cannot complete: no active consolidation")
            return
        
        self._current_state.status = ConsolidationStatus.COMPLETED
        self._current_state.last_run = datetime.utcnow()
        
        # Archive current state
        self._state_history.append(self._current_state)
        
        # Keep only last 10 states
        if len(self._state_history) > 10:
            self._state_history = self._state_history[-10:]
        
        logger.info("Consolidation completed", extra={
            "completed_users": self._current_state.progress.completed_users,
            "failed_users": self._current_state.progress.failed_users,
            "total_experiences": self._current_state.progress.processed_experiences
        })
        
        # Reset to idle
        self._current_state = ConsolidationState(
            status=ConsolidationStatus.IDLE,
            last_run=self._current_state.last_run
        )
    
    def fail_consolidation(self, error: str) -> None:
        """
        Mark consolidation as failed.
        
        Args:
            error: Error message
        """
        self._current_state.status = ConsolidationStatus.FAILED
        self._current_state.errors.append(error)
        self._current_state.last_run = datetime.utcnow()
        
        logger.error("Consolidation failed", extra={
            "error": error,
            "progress": self._current_state.progress.to_dict() if self._current_state.progress else None
        })
        
        # Archive failed state
        self._state_history.append(self._current_state)
        
        # Reset to idle
        self._current_state = ConsolidationState(
            status=ConsolidationStatus.IDLE,
            last_run=self._current_state.last_run
        )
    
    def pause_consolidation(self) -> None:
        """Pause consolidation."""
        if self._current_state.status == ConsolidationStatus.RUNNING:
            self._current_state.status = ConsolidationStatus.PAUSED
            logger.info("Consolidation paused")
    
    def resume_consolidation(self) -> None:
        """Resume paused consolidation."""
        if self._current_state.status == ConsolidationStatus.PAUSED:
            self._current_state.status = ConsolidationStatus.RUNNING
            logger.info("Consolidation resumed")
    
    def schedule_next(self, next_run: datetime) -> None:
        """
        Schedule next consolidation.
        
        Args:
            next_run: When next consolidation should run
        """
        self._current_state.next_scheduled = next_run
        logger.info("Next consolidation scheduled", extra={
            "next_run": next_run.isoformat()
        })
    
    def get_pending_items(self, user_id: str) -> List[str]:
        """
        Get items pending consolidation for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of pending item IDs
        """
        # This would query the working memory store
        # Placeholder implementation
        return []
    
    def mark_consolidated(self, item_ids: List[str]) -> None:
        """
        Mark items as consolidated.
        
        Args:
            item_ids: List of item IDs that were consolidated
        """
        # This would update the working memory store
        # Placeholder implementation
        logger.debug("Items marked as consolidated", extra={
            "count": len(item_ids)
        })
    
    def get_state_history(self, limit: int = 10) -> List[ConsolidationState]:
        """
        Get consolidation state history.
        
        Args:
            limit: Maximum number of states to return
            
        Returns:
            List of historical states
        """
        return self._state_history[-limit:]
    
    async def persist_state(self, storage) -> None:
        """
        Persist current state to storage.
        
        Args:
            storage: Storage backend (e.g., libSQL)
        """
        state_dict = self._current_state.to_dict()
        
        try:
            await storage.execute(
                """
                INSERT OR REPLACE INTO consolidation_state 
                (id, state_json, updated_at) 
                VALUES (?, ?, ?)
                """,
                ("current", str(state_dict), datetime.utcnow().isoformat())
            )
            
            logger.debug("State persisted to storage")
            
        except Exception as e:
            logger.error("Failed to persist state", extra={
                "error": str(e)
            }, exc_info=True)
    
    async def load_state(self, storage) -> None:
        """
        Load state from storage.
        
        Args:
            storage: Storage backend (e.g., libSQL)
        """
        try:
            result = await storage.execute(
                "SELECT state_json FROM consolidation_state WHERE id = ?",
                ("current",)
            )
            
            if result:
                import json
                state_dict = json.loads(result[0]["state_json"])
                self._current_state = ConsolidationState.from_dict(state_dict)
                
                logger.info("State loaded from storage", extra={
                    "status": self._current_state.status.value
                })
            
        except Exception as e:
            logger.error("Failed to load state", extra={
                "error": str(e)
            }, exc_info=True)


# Import timedelta for estimated_completion calculation
from datetime import timedelta
