"""
Consolidation Scheduler

Detects idle periods and schedules memory consolidation jobs.
Integrates with AICO's backend scheduler for daily consolidation tasks.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio
import psutil

from aico.core.logging import get_logger

logger = get_logger("shared", "memory.consolidation.scheduler")


class IdleStatus(Enum):
    """System idle status."""
    ACTIVE = "active"
    IDLE = "idle"
    CONSOLIDATING = "consolidating"


@dataclass
class IdleDetector:
    """
    Detects when the system is idle and suitable for consolidation.
    
    Monitors CPU usage and user activity to determine idle periods.
    
    Attributes:
        cpu_threshold_percent: CPU usage threshold for idle detection
        idle_duration_seconds: Required idle duration before consolidation
        check_interval_seconds: How often to check idle status
    """
    cpu_threshold_percent: float = 20.0
    idle_duration_seconds: int = 300  # 5 minutes
    check_interval_seconds: int = 60  # 1 minute
    
    _idle_since: Optional[datetime] = field(default=None, init=False)
    _status: IdleStatus = field(default=IdleStatus.ACTIVE, init=False)
    
    def check_idle(self) -> bool:
        """
        Check if system is currently idle.
        
        Returns:
            True if system has been idle for required duration
        """
        # Get CPU usage over last second
        cpu_percent = psutil.cpu_percent(interval=1.0)
        
        is_currently_idle = cpu_percent < self.cpu_threshold_percent
        
        if is_currently_idle:
            if self._idle_since is None:
                self._idle_since = datetime.utcnow()
                logger.debug("System became idle", extra={
                    "cpu_percent": cpu_percent,
                    "threshold": self.cpu_threshold_percent
                })
            
            # Check if idle duration threshold met
            idle_duration = (datetime.utcnow() - self._idle_since).total_seconds()
            
            if idle_duration >= self.idle_duration_seconds:
                if self._status != IdleStatus.IDLE:
                    self._status = IdleStatus.IDLE
                    logger.info("System idle threshold met", extra={
                        "idle_duration_seconds": idle_duration,
                        "required_seconds": self.idle_duration_seconds
                    })
                return True
        else:
            # System is active, reset idle tracking
            if self._idle_since is not None:
                self._idle_since = None
                self._status = IdleStatus.ACTIVE
                logger.debug("System became active", extra={
                    "cpu_percent": cpu_percent
                })
        
        return False
    
    def mark_consolidating(self) -> None:
        """Mark that consolidation is in progress."""
        self._status = IdleStatus.CONSOLIDATING
    
    def mark_complete(self) -> None:
        """Mark that consolidation is complete."""
        self._status = IdleStatus.ACTIVE
        self._idle_since = None
    
    @property
    def status(self) -> IdleStatus:
        """Get current idle status."""
        return self._status


@dataclass
class ConsolidationJob:
    """
    A memory consolidation job for a specific user.
    
    Attributes:
        job_id: Unique job identifier
        user_id: User to consolidate
        scheduled_at: When job was scheduled
        started_at: When job started (None if not started)
        completed_at: When job completed (None if not completed)
        status: Current job status
        experiences_processed: Number of experiences processed
        errors: List of errors encountered
        metadata: Additional job metadata
    """
    job_id: str
    user_id: str
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    experiences_processed: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def start(self) -> None:
        """Mark job as started."""
        self.started_at = datetime.utcnow()
        self.status = "running"
    
    def complete(self, experiences_count: int) -> None:
        """Mark job as completed."""
        self.completed_at = datetime.utcnow()
        self.status = "completed"
        self.experiences_processed = experiences_count
    
    def fail(self, error: str) -> None:
        """Mark job as failed."""
        self.completed_at = datetime.utcnow()
        self.status = "failed"
        self.errors.append(error)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ConsolidationScheduler:
    """
    Schedules and manages memory consolidation jobs.
    
    Integrates with AICO's backend scheduler for daily consolidation.
    Implements 7-day user sharding to distribute load.
    """
    
    def __init__(
        self,
        idle_detector: Optional[IdleDetector] = None,
        max_concurrent_users: int = 4,
        max_duration_minutes: int = 60,
        user_sharding_cycle_days: int = 7
    ):
        """
        Initialize the consolidation scheduler.
        
        Args:
            idle_detector: Idle detector instance (creates default if None)
            max_concurrent_users: Maximum concurrent consolidation jobs
            max_duration_minutes: Maximum duration per user
            user_sharding_cycle_days: Days in user sharding cycle
        """
        self.idle_detector = idle_detector or IdleDetector()
        self.max_concurrent_users = max_concurrent_users
        self.max_duration_minutes = max_duration_minutes
        self.user_sharding_cycle_days = user_sharding_cycle_days
        
        self._active_jobs: Dict[str, ConsolidationJob] = {}
        self._job_history: List[ConsolidationJob] = []
        self._semaphore = asyncio.Semaphore(max_concurrent_users)
    
    def get_users_for_today(self, all_users: List[str]) -> List[str]:
        """
        Get users to consolidate today using round-robin sharding.
        
        Args:
            all_users: List of all user IDs
            
        Returns:
            List of user IDs to consolidate today
        """
        day_of_week = datetime.utcnow().weekday()  # 0 (Monday) to 6 (Sunday)
        
        # Assign users to days using modulo
        users_today = [
            user for i, user in enumerate(all_users)
            if i % self.user_sharding_cycle_days == day_of_week
        ]
        
        logger.info("Users selected for consolidation", extra={
            "day_of_week": day_of_week,
            "users_today": len(users_today),
            "total_users": len(all_users),
            "sharding_cycle_days": self.user_sharding_cycle_days
        })
        
        return users_today
    
    async def schedule_consolidation(
        self,
        users: List[str],
        require_idle: bool = True
    ) -> List[ConsolidationJob]:
        """
        Schedule consolidation for multiple users.
        
        Args:
            users: List of user IDs to consolidate
            require_idle: Whether to require system idle before starting
            
        Returns:
            List of consolidation jobs
        """
        # Check if system is idle (if required)
        if require_idle and not self.idle_detector.check_idle():
            logger.info("Consolidation skipped: system not idle")
            return []
        
        # Mark as consolidating
        self.idle_detector.mark_consolidating()
        
        # Create jobs
        jobs = []
        for user_id in users:
            job = ConsolidationJob(
                job_id=f"consolidation_{user_id}_{datetime.utcnow().isoformat()}",
                user_id=user_id,
                scheduled_at=datetime.utcnow()
            )
            jobs.append(job)
            self._active_jobs[job.job_id] = job
        
        logger.info("Consolidation jobs scheduled", extra={
            "job_count": len(jobs),
            "user_count": len(users)
        })
        
        return jobs
    
    async def run_consolidation_job(
        self,
        job: ConsolidationJob,
        consolidate_func
    ) -> ConsolidationJob:
        """
        Run a single consolidation job with timeout and error handling.
        
        Args:
            job: Consolidation job to run
            consolidate_func: Async function to perform consolidation
            
        Returns:
            Updated job with results
        """
        async with self._semaphore:  # Limit concurrent jobs
            try:
                job.start()
                
                logger.info("Consolidation job started", extra={
                    "job_id": job.job_id,
                    "user_id": job.user_id
                })
                
                # Run with timeout
                timeout_seconds = self.max_duration_minutes * 60
                result = await asyncio.wait_for(
                    consolidate_func(job.user_id),
                    timeout=timeout_seconds
                )
                
                # Mark complete
                experiences_count = result.get("experiences_processed", 0)
                job.complete(experiences_count)
                job.metadata = result
                
                logger.info("Consolidation job completed", extra={
                    "job_id": job.job_id,
                    "user_id": job.user_id,
                    "experiences_processed": experiences_count,
                    "duration_seconds": job.duration_seconds
                })
                
            except asyncio.TimeoutError:
                error_msg = f"Consolidation timeout after {self.max_duration_minutes} minutes"
                job.fail(error_msg)
                logger.error("Consolidation job timeout", extra={
                    "job_id": job.job_id,
                    "user_id": job.user_id,
                    "max_duration_minutes": self.max_duration_minutes
                })
                
            except Exception as e:
                error_msg = f"Consolidation error: {str(e)}"
                job.fail(error_msg)
                logger.error("Consolidation job failed", extra={
                    "job_id": job.job_id,
                    "user_id": job.user_id,
                    "error": str(e)
                }, exc_info=True)
            
            finally:
                # Move to history
                if job.job_id in self._active_jobs:
                    del self._active_jobs[job.job_id]
                self._job_history.append(job)
                
                # Keep only last 100 jobs in history
                if len(self._job_history) > 100:
                    self._job_history = self._job_history[-100:]
        
        return job
    
    async def run_batch_consolidation(
        self,
        jobs: List[ConsolidationJob],
        consolidate_func
    ) -> List[ConsolidationJob]:
        """
        Run multiple consolidation jobs in parallel (up to max_concurrent_users).
        
        Args:
            jobs: List of consolidation jobs
            consolidate_func: Async function to perform consolidation
            
        Returns:
            List of completed jobs
        """
        tasks = [
            self.run_consolidation_job(job, consolidate_func)
            for job in jobs
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Mark consolidation complete
        self.idle_detector.mark_complete()
        
        # Filter out exceptions and return successful jobs
        completed_jobs = [r for r in results if isinstance(r, ConsolidationJob)]
        
        logger.info("Batch consolidation complete", extra={
            "total_jobs": len(jobs),
            "completed": len(completed_jobs),
            "failed": len(jobs) - len(completed_jobs)
        })
        
        return completed_jobs
    
    def get_job_status(self, job_id: str) -> Optional[ConsolidationJob]:
        """Get status of a specific job."""
        # Check active jobs first
        if job_id in self._active_jobs:
            return self._active_jobs[job_id]
        
        # Check history
        for job in reversed(self._job_history):
            if job.job_id == job_id:
                return job
        
        return None
    
    def get_active_jobs(self) -> List[ConsolidationJob]:
        """Get all currently active jobs."""
        return list(self._active_jobs.values())
    
    def get_job_history(self, limit: int = 10) -> List[ConsolidationJob]:
        """Get recent job history."""
        return self._job_history[-limit:]
