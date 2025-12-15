"""
Plan Execution Engine

Core service for executing agency plans by invoking skills, tracking progress,
handling errors, and managing execution state.
"""

from __future__ import annotations

import uuid
import json
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from aico.core.logging import get_logger
from aico.data.libsql import EncryptedLibSQLConnection

from .models import Plan, PlanStep, StepStatus, PlanStatus
from .store import PlanStore


logger = get_logger("shared", "ai.agency.executor")


class ExecutionStatus(str, Enum):
    """Status of plan execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepExecutionStatus(str, Enum):
    """Status of individual step execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class PlanExecution:
    """Represents an execution instance of a plan."""
    
    def __init__(
        self,
        execution_id: str,
        plan_id: str,
        goal_id: str,
        user_id: str,
        status: ExecutionStatus = ExecutionStatus.PENDING,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        paused_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        current_step_id: Optional[str] = None,
        steps_completed: int = 0,
        steps_total: int = 0,
        progress_percentage: float = 0.0,
        execution_context: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        cancellation_reason: Optional[str] = None,
        retry_count: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.execution_id = execution_id
        self.plan_id = plan_id
        self.goal_id = goal_id
        self.user_id = user_id
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.paused_at = paused_at
        self.cancelled_at = cancelled_at
        self.current_step_id = current_step_id
        self.steps_completed = steps_completed
        self.steps_total = steps_total
        self.progress_percentage = progress_percentage
        self.execution_context = execution_context or {}
        self.error_message = error_message
        self.cancellation_reason = cancellation_reason
        self.retry_count = retry_count
        self.created_at = created_at or datetime.now(UTC)
        self.updated_at = updated_at or datetime.now(UTC)


class StepExecution:
    """Represents execution of a single plan step."""
    
    def __init__(
        self,
        step_execution_id: str,
        execution_id: str,
        step_id: str,
        step_order: int,
        status: StepExecutionStatus = StepExecutionStatus.PENDING,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        skill_id: Optional[str] = None,
        skill_invocation_id: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        blocked_reason: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.step_execution_id = step_execution_id
        self.execution_id = execution_id
        self.step_id = step_id
        self.step_order = step_order
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_ms = duration_ms
        self.skill_id = skill_id
        self.skill_invocation_id = skill_invocation_id
        self.input_data = input_data or {}
        self.output_data = output_data or {}
        self.error_message = error_message
        self.retry_count = retry_count
        self.blocked_reason = blocked_reason
        self.created_at = created_at or datetime.now(UTC)
        self.updated_at = updated_at or datetime.now(UTC)


class PlanExecutor:
    """
    Core plan execution engine.
    
    Responsibilities:
    - Execute plans by invoking skills for each step
    - Track execution progress and state
    - Handle errors and retries
    - Support pause/resume/cancel operations
    - Manage step dependencies
    - Record execution results for feedback loop
    """
    
    def __init__(
        self,
        db: EncryptedLibSQLConnection,
        plan_store: PlanStore,
        skill_invoker: Optional[Any] = None,
        logger=None,
    ):
        self.db = db
        self.plan_store = plan_store
        self.skill_invoker = skill_invoker
        self.logger = logger or globals()["logger"]
    
    async def start_execution(
        self,
        plan_id: str,
        goal_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PlanExecution:
        """
        Start executing a plan.
        
        Args:
            plan_id: Plan to execute
            goal_id: Associated goal
            user_id: User ID
            context: Execution context (personality, emotion, resources)
            
        Returns:
            PlanExecution instance
        """
        # Get plan
        plan = await self.plan_store.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Create execution record
        execution = PlanExecution(
            execution_id=str(uuid.uuid4()),
            plan_id=plan_id,
            goal_id=goal_id,
            user_id=user_id,
            status=ExecutionStatus.PENDING,
            steps_total=len(plan.steps),
            execution_context=context or {},
        )
        
        # Persist execution
        await self._save_execution(execution)
        
        # Create step execution records
        for step in plan.steps:
            step_exec = StepExecution(
                step_execution_id=str(uuid.uuid4()),
                execution_id=execution.execution_id,
                step_id=step.step_id,
                step_order=step.order,
            )
            await self._save_step_execution(step_exec)
        
        self.logger.info(
            f"[EXECUTOR] Started execution {execution.execution_id} "
            f"for plan {plan_id} ({len(plan.steps)} steps)"
        )
        
        return execution
    
    async def execute_next_step(
        self,
        execution_id: str,
    ) -> Tuple[bool, Optional[StepExecution]]:
        """
        Execute the next pending step in a plan execution.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Tuple of (has_more_steps, step_execution)
        """
        # Get execution
        execution = await self._get_execution(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        # Check if execution is in valid state
        if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            self.logger.warning(
                f"[EXECUTOR] Cannot execute step: execution {execution_id} "
                f"is in {execution.status} state"
            )
            return False, None
        
        # Get next pending step
        step_exec = await self._get_next_pending_step(execution_id)
        if not step_exec:
            # No more steps - mark execution as completed
            await self._complete_execution(execution_id)
            return False, None
        
        # Update execution status to running
        if execution.status == ExecutionStatus.PENDING:
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(UTC)
            await self._save_execution(execution)
        
        # Execute the step
        try:
            step_exec = await self._execute_step(execution, step_exec)
            
            # Update execution progress
            if step_exec.status == StepExecutionStatus.COMPLETED:
                execution.steps_completed += 1
                execution.progress_percentage = (
                    execution.steps_completed / execution.steps_total * 100.0
                )
                execution.current_step_id = step_exec.step_id
                await self._save_execution(execution)
            
            # Check if there are more steps
            has_more = await self._has_pending_steps(execution_id)
            
            return has_more, step_exec
            
        except Exception as e:
            self.logger.error(
                f"[EXECUTOR] Step execution failed: {e}",
                exc_info=True
            )
            
            # Mark step as failed
            step_exec.status = StepExecutionStatus.FAILED
            step_exec.error_message = str(e)
            step_exec.completed_at = datetime.now(UTC)
            await self._save_step_execution(step_exec)
            
            # Mark execution as failed
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"Step {step_exec.step_order} failed: {e}"
            execution.completed_at = datetime.now(UTC)
            await self._save_execution(execution)
            
            return False, step_exec
    
    async def pause_execution(
        self,
        execution_id: str,
    ) -> PlanExecution:
        """Pause an execution."""
        execution = await self._get_execution(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        if execution.status != ExecutionStatus.RUNNING:
            raise ValueError(
                f"Cannot pause execution in {execution.status} state"
            )
        
        # Save state snapshot
        await self._save_state_snapshot(execution, "pause")
        
        execution.status = ExecutionStatus.PAUSED
        execution.paused_at = datetime.now(UTC)
        await self._save_execution(execution)
        
        self.logger.info(f"[EXECUTOR] Paused execution {execution_id}")
        
        return execution
    
    async def resume_execution(
        self,
        execution_id: str,
    ) -> PlanExecution:
        """Resume a paused execution."""
        execution = await self._get_execution(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        if execution.status != ExecutionStatus.PAUSED:
            raise ValueError(
                f"Cannot resume execution in {execution.status} state"
            )
        
        execution.status = ExecutionStatus.RUNNING
        execution.paused_at = None
        await self._save_execution(execution)
        
        self.logger.info(f"[EXECUTOR] Resumed execution {execution_id}")
        
        return execution
    
    async def cancel_execution(
        self,
        execution_id: str,
        reason: Optional[str] = None,
    ) -> PlanExecution:
        """Cancel an execution."""
        execution = await self._get_execution(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        if execution.status in [ExecutionStatus.COMPLETED, ExecutionStatus.CANCELLED]:
            raise ValueError(
                f"Cannot cancel execution in {execution.status} state"
            )
        
        execution.status = ExecutionStatus.CANCELLED
        execution.cancelled_at = datetime.now(UTC)
        execution.cancellation_reason = reason
        await self._save_execution(execution)
        
        self.logger.info(
            f"[EXECUTOR] Cancelled execution {execution_id}: {reason}"
        )
        
        return execution
    
    async def get_execution_status(
        self,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get detailed execution status."""
        execution = await self._get_execution(execution_id)
        if not execution:
            return None
        
        # Get step executions
        step_execs = await self._get_step_executions(execution_id)
        
        return {
            "execution_id": execution.execution_id,
            "plan_id": execution.plan_id,
            "goal_id": execution.goal_id,
            "status": execution.status.value,
            "progress_percentage": execution.progress_percentage,
            "steps_completed": execution.steps_completed,
            "steps_total": execution.steps_total,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "error_message": execution.error_message,
            "steps": [
                {
                    "step_execution_id": se.step_execution_id,
                    "step_order": se.step_order,
                    "status": se.status.value,
                    "duration_ms": se.duration_ms,
                    "error_message": se.error_message,
                }
                for se in step_execs
            ],
        }
    
    # ========================================================================
    # Internal Helpers
    # ========================================================================
    
    async def _execute_step(
        self,
        execution: PlanExecution,
        step_exec: StepExecution,
    ) -> StepExecution:
        """Execute a single step."""
        start_time = datetime.now(UTC)
        
        # Update step status to running
        step_exec.status = StepExecutionStatus.RUNNING
        step_exec.started_at = start_time
        await self._save_step_execution(step_exec)
        
        self.logger.info(
            f"🎬 [EXECUTOR] Starting step {step_exec.step_order} "
            f"execution={execution.execution_id[:8]}... "
            f"plan={execution.plan_id[:8]}... "
            f"goal={execution.goal_id[:8]}..."
        )
        
        try:
            # Get plan and step details
            plan = await self.plan_store.get_plan(execution.plan_id)
            step = next((s for s in plan.steps if s.step_id == step_exec.step_id), None)
            
            if not step:
                raise ValueError(f"Step {step_exec.step_id} not found in plan")
            
            self.logger.info(
                f"🎬 [EXECUTOR] Step {step_exec.step_order}: {step.description[:80]}..."
            )
            
            # Invoke skill if specified
            if self.skill_invoker and step_exec.skill_id:
                self.logger.info(
                    f"🎬 [EXECUTOR] Invoking skill '{step_exec.skill_id}' for step {step_exec.step_order}"
                )
                self.logger.debug(
                    f"🎬 [EXECUTOR] Step input data: {json.dumps(step_exec.input_data, indent=2)}"
                )
                
                result = await self.skill_invoker.invoke_skill(
                    skill_id=step_exec.skill_id,
                    user_id=execution.user_id,
                    input_data=step_exec.input_data,
                    context={
                        **execution.execution_context,
                        "execution_id": execution.execution_id,
                        "plan_id": execution.plan_id,
                        "goal_id": execution.goal_id,
                        "step_order": step_exec.step_order,
                    },
                )
                
                if result.get("success"):
                    self.logger.info(
                        f"✅ [EXECUTOR] Skill '{step_exec.skill_id}' completed successfully "
                        f"for step {step_exec.step_order} (duration: {result.get('duration_ms')}ms)"
                    )
                    self.logger.debug(
                        f"✅ [EXECUTOR] Skill output: {json.dumps(result.get('output', {}), indent=2)}"
                    )
                else:
                    self.logger.error(
                        f"❌ [EXECUTOR] Skill '{step_exec.skill_id}' failed for step {step_exec.step_order}: "
                        f"{result.get('error', 'Unknown error')}"
                    )
                
                step_exec.output_data = result.get("output", {})
                step_exec.skill_invocation_id = result.get("invocation_id")
            else:
                # No skill - mark as completed (placeholder step)
                self.logger.info(
                    f"🎬 [EXECUTOR] Step {step_exec.step_order} has no skill - marking as completed"
                )
                step_exec.output_data = {"status": "completed", "note": "No skill invocation"}
            
            # Mark step as completed
            step_exec.status = StepExecutionStatus.COMPLETED
            step_exec.completed_at = datetime.now(UTC)
            step_exec.duration_ms = int(
                (step_exec.completed_at - start_time).total_seconds() * 1000
            )
            
            await self._save_step_execution(step_exec)
            
            self.logger.info(
                f"✅ [EXECUTOR] Completed step {step_exec.step_order}/{execution.steps_total} "
                f"in {step_exec.duration_ms}ms "
                f"(progress: {(step_exec.step_order / execution.steps_total * 100):.1f}%)"
            )
            
            return step_exec
            
        except Exception as e:
            # Mark step as failed
            step_exec.status = StepExecutionStatus.FAILED
            step_exec.error_message = str(e)
            step_exec.completed_at = datetime.now(UTC)
            step_exec.duration_ms = int(
                (step_exec.completed_at - start_time).total_seconds() * 1000
            )
            
            await self._save_step_execution(step_exec)
            
            self.logger.error(
                f"❌ [EXECUTOR] Step {step_exec.step_order} failed after {step_exec.duration_ms}ms: {e}",
                exc_info=True
            )
            
            raise
    
    async def _complete_execution(self, execution_id: str) -> None:
        """Mark execution as completed."""
        execution = await self._get_execution(execution_id)
        if not execution:
            return
        
        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = datetime.now(UTC)
        execution.progress_percentage = 100.0
        
        await self._save_execution(execution)
        
        self.logger.info(
            f"[EXECUTOR] Completed execution {execution_id} "
            f"({execution.steps_completed}/{execution.steps_total} steps)"
        )
    
    async def _get_next_pending_step(
        self,
        execution_id: str,
    ) -> Optional[StepExecution]:
        """Get next pending step in order."""
        row = self.db.fetch_one(
            """SELECT * FROM step_executions
               WHERE execution_id = ? AND status = 'pending'
               ORDER BY step_order ASC
               LIMIT 1""",
            (execution_id,)
        )
        
        if not row:
            return None
        
        return self._row_to_step_execution(row)
    
    async def _has_pending_steps(self, execution_id: str) -> bool:
        """Check if execution has pending steps."""
        row = self.db.fetch_one(
            """SELECT COUNT(*) as count FROM step_executions
               WHERE execution_id = ? AND status = 'pending'""",
            (execution_id,)
        )
        
        return row["count"] > 0 if row else False
    
    async def _save_execution(self, execution: PlanExecution) -> None:
        """Save execution to database."""
        now = datetime.now(UTC).isoformat()
        
        self.db.execute(
            """INSERT OR REPLACE INTO plan_executions (
                execution_id, plan_id, goal_id, user_id, status,
                started_at, completed_at, paused_at, cancelled_at,
                current_step_id, steps_completed, steps_total,
                progress_percentage, execution_context, error_message,
                cancellation_reason, retry_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                execution.execution_id,
                execution.plan_id,
                execution.goal_id,
                execution.user_id,
                execution.status.value,
                execution.started_at.isoformat() if execution.started_at else None,
                execution.completed_at.isoformat() if execution.completed_at else None,
                execution.paused_at.isoformat() if execution.paused_at else None,
                execution.cancelled_at.isoformat() if execution.cancelled_at else None,
                execution.current_step_id,
                execution.steps_completed,
                execution.steps_total,
                execution.progress_percentage,
                json.dumps(execution.execution_context),
                execution.error_message,
                execution.cancellation_reason,
                execution.retry_count,
                execution.created_at.isoformat(),
                now,
            )
        )
        self.db.commit()
    
    async def _save_step_execution(self, step_exec: StepExecution) -> None:
        """Save step execution to database."""
        now = datetime.now(UTC).isoformat()
        
        self.db.execute(
            """INSERT OR REPLACE INTO step_executions (
                step_execution_id, execution_id, step_id, step_order, status,
                started_at, completed_at, duration_ms, skill_id,
                skill_invocation_id, input_data, output_data, error_message,
                retry_count, blocked_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                step_exec.step_execution_id,
                step_exec.execution_id,
                step_exec.step_id,
                step_exec.step_order,
                step_exec.status.value,
                step_exec.started_at.isoformat() if step_exec.started_at else None,
                step_exec.completed_at.isoformat() if step_exec.completed_at else None,
                step_exec.duration_ms,
                step_exec.skill_id,
                step_exec.skill_invocation_id,
                json.dumps(step_exec.input_data),
                json.dumps(step_exec.output_data),
                step_exec.error_message,
                step_exec.retry_count,
                step_exec.blocked_reason,
                step_exec.created_at.isoformat(),
                now,
            )
        )
        self.db.commit()
    
    async def _get_execution(self, execution_id: str) -> Optional[PlanExecution]:
        """Get execution from database."""
        row = self.db.fetch_one(
            "SELECT * FROM plan_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        if not row:
            return None
        
        return PlanExecution(
            execution_id=row["execution_id"],
            plan_id=row["plan_id"],
            goal_id=row["goal_id"],
            user_id=row["user_id"],
            status=ExecutionStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]).replace(tzinfo=UTC) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]).replace(tzinfo=UTC) if row["completed_at"] else None,
            paused_at=datetime.fromisoformat(row["paused_at"]).replace(tzinfo=UTC) if row["paused_at"] else None,
            cancelled_at=datetime.fromisoformat(row["cancelled_at"]).replace(tzinfo=UTC) if row["cancelled_at"] else None,
            current_step_id=row["current_step_id"],
            steps_completed=row["steps_completed"],
            steps_total=row["steps_total"],
            progress_percentage=row["progress_percentage"],
            execution_context=json.loads(row["execution_context"]) if row["execution_context"] else {},
            error_message=row["error_message"],
            cancellation_reason=row["cancellation_reason"],
            retry_count=row["retry_count"],
            created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
            updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC),
        )
    
    async def _get_step_executions(
        self,
        execution_id: str,
    ) -> List[StepExecution]:
        """Get all step executions for an execution."""
        rows = self.db.fetch_all(
            """SELECT * FROM step_executions
               WHERE execution_id = ?
               ORDER BY step_order ASC""",
            (execution_id,)
        )
        
        return [self._row_to_step_execution(row) for row in rows]
    
    def _row_to_step_execution(self, row: Dict[str, Any]) -> StepExecution:
        """Convert database row to StepExecution."""
        return StepExecution(
            step_execution_id=row["step_execution_id"],
            execution_id=row["execution_id"],
            step_id=row["step_id"],
            step_order=row["step_order"],
            status=StepExecutionStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]).replace(tzinfo=UTC) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]).replace(tzinfo=UTC) if row["completed_at"] else None,
            duration_ms=row["duration_ms"],
            skill_id=row["skill_id"],
            skill_invocation_id=row["skill_invocation_id"],
            input_data=json.loads(row["input_data"]) if row["input_data"] else {},
            output_data=json.loads(row["output_data"]) if row["output_data"] else {},
            error_message=row["error_message"],
            retry_count=row["retry_count"],
            blocked_reason=row["blocked_reason"],
            created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
            updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC),
        )
    
    async def _save_state_snapshot(
        self,
        execution: PlanExecution,
        snapshot_type: str,
    ) -> None:
        """Save execution state snapshot."""
        snapshot_id = str(uuid.uuid4())
        
        state_data = {
            "execution": {
                "status": execution.status.value,
                "steps_completed": execution.steps_completed,
                "current_step_id": execution.current_step_id,
                "progress_percentage": execution.progress_percentage,
            },
            "context": execution.execution_context,
        }
        
        self.db.execute(
            """INSERT INTO execution_state_snapshots (
                snapshot_id, execution_id, snapshot_type, state_data, created_at
            ) VALUES (?, ?, ?, ?, ?)""",
            (
                snapshot_id,
                execution.execution_id,
                snapshot_type,
                json.dumps(state_data),
                datetime.now(UTC).isoformat(),
            )
        )
        self.db.commit()
