"""
Skill Invocation Service

Handles invocation of skills during plan execution with timeout, retry, and result capture.
"""

from __future__ import annotations

import uuid
import asyncio
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from aico.core.logging import get_logger
from .skills.registry import SkillRegistry


logger = get_logger("shared.ai.agency.skill_invoker")


class SkillInvoker:
    """
    Service for invoking skills during plan execution.
    
    Responsibilities:
    - Invoke skills with timeout and retry logic
    - Capture execution results
    - Record skill executions for feedback loop
    - Handle skill errors gracefully
    """
    
    def __init__(
        self,
        db: Any  # Agency system being redesigned,
        skill_registry: SkillRegistry,
        default_timeout: int = 30,
        max_retries: int = 2,
        logger=None,
    ):
        self.db = db
        self.skill_registry = skill_registry
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.logger = logger or globals()["logger"]
        
        self.logger.debug(
            f"🔧 [SKILL_INVOKER] Initialized with {len(skill_registry)} skills, "
            f"timeout={default_timeout}s, max_retries={max_retries}"
        )
    
    async def invoke_skill(
        self,
        skill_id: str,
        user_id: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Invoke a skill with timeout and retry logic.
        
        Args:
            skill_id: Skill to invoke
            user_id: User ID
            input_data: Input parameters for skill
            context: Execution context
            timeout: Timeout in seconds (default: 30)
            
        Returns:
            Dict with invocation_id, output, success, duration_ms
        """
        invocation_id = str(uuid.uuid4())
        start_time = datetime.now(UTC)
        timeout = timeout or self.default_timeout
        context = context or {}
        
        # Check if skill exists
        skill = self.skill_registry.get(skill_id)
        if not skill:
            error_msg = f"Skill '{skill_id}' not found in registry"
            self.logger.error(f"🔧 [SKILL_INVOKER] {error_msg}")
            return {
                "invocation_id": invocation_id,
                "output": {},
                "success": False,
                "error": error_msg,
                "duration_ms": 0,
            }
        
        # Validate inputs
        is_valid, validation_error = skill.validate_inputs(input_data)
        if not is_valid:
            self.logger.error(
                f"🔧 [SKILL_INVOKER] Input validation failed for skill '{skill_id}': {validation_error}"
            )
            return {
                "invocation_id": invocation_id,
                "output": {},
                "success": False,
                "error": f"Input validation failed: {validation_error}",
                "duration_ms": 0,
            }
        
        # Use skill's timeout if available
        timeout = skill.timeout_seconds
        
        self.logger.info(
            f"🔧 [SKILL_INVOKER] Starting invocation {invocation_id[:8]}... "
            f"skill='{skill_id}' ({skill.name}) user={user_id[:8]}... "
            f"timeout={timeout}s"
        )
        self.logger.debug(
            f"🔧 [SKILL_INVOKER] Input data: {json.dumps(input_data, indent=2)}"
        )
        
        # Record invocation start
        await self._record_invocation_start(
            invocation_id=invocation_id,
            skill_id=skill_id,
            user_id=user_id,
            input_data=input_data,
            context=context,
        )
        
        # Attempt invocation with retries
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                # Invoke skill with timeout
                result = await asyncio.wait_for(
                    self._invoke_skill_internal(
                        skill_id=skill_id,
                        user_id=user_id,
                        input_data=input_data,
                        context=context,
                    ),
                    timeout=timeout,
                )
                
                # Record successful invocation
                duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
                
                await self._record_invocation_complete(
                    invocation_id=invocation_id,
                    success=True,
                    output_data=result.to_dict() if hasattr(result, 'to_dict') else result,
                    duration_ms=duration_ms,
                )
                
                self.logger.info(
                    f"✅ [SKILL_INVOKER] Skill '{skill_id}' completed successfully in {duration_ms}ms "
                    f"(invocation: {invocation_id[:8]}...)"
                )
                self.logger.debug(
                    f"✅ [SKILL_INVOKER] Output: {json.dumps(result.to_dict() if hasattr(result, 'to_dict') else result, indent=2)}"
                )
                
                return {
                    "invocation_id": invocation_id,
                    "output": result.to_dict() if hasattr(result, 'to_dict') else result,
                    "success": True,
                    "duration_ms": duration_ms,
                }
                
            except asyncio.TimeoutError:
                last_error = f"Skill execution timed out after {timeout}s"
                self.logger.warning(
                    f"⏱️ [SKILL_INVOKER] Skill '{skill_id}' timed out "
                    f"(attempt {retry_count + 1}/{self.max_retries + 1}) "
                    f"invocation={invocation_id[:8]}..."
                )
                
            except Exception as e:
                last_error = str(e)
                self.logger.error(
                    f"❌ [SKILL_INVOKER] Skill '{skill_id}' failed: {e} "
                    f"(attempt {retry_count + 1}/{self.max_retries + 1}) "
                    f"invocation={invocation_id[:8]}..."
                )
                logger.exception(f"❌ [SKILL_INVOKER] Exception details:")
            
            retry_count += 1
            
            # Wait before retry (exponential backoff)
            if retry_count <= self.max_retries:
                await asyncio.sleep(2 ** retry_count)
        
        # All retries exhausted - record failure
        duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        
        await self._record_invocation_complete(
            invocation_id=invocation_id,
            success=False,
            error_message=last_error,
            duration_ms=duration_ms,
        )
        
        self.logger.error(
            f"❌ [SKILL_INVOKER] Skill '{skill_id}' failed after {retry_count} attempts: {last_error} "
            f"(invocation: {invocation_id[:8]}...)"
        )
        
        return {
            "invocation_id": invocation_id,
            "output": {},
            "success": False,
            "error": last_error,
            "duration_ms": duration_ms,
        }
    
    async def _invoke_skill_internal(
        self,
        skill_id: str,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Internal skill invocation logic.
        
        Looks up skill in registry and executes it.
        """
        skill = self.skill_registry.get(skill_id)
        if not skill:
            raise ValueError(f"Skill '{skill_id}' not found in registry")
        
        self.logger.debug(
            f"🔧 [SKILL_INVOKER] Executing skill '{skill_id}' ({skill.name}) "
            f"for user {user_id[:8]}..."
        )
        
        # Execute the skill
        result = await skill.execute(
            user_id=user_id,
            input_data=input_data,
            context=context,
        )
        
        if not result.success:
            raise RuntimeError(result.error or "Skill execution failed")
        
        return result
    
    async def _record_invocation_start(
        self,
        invocation_id: str,
        skill_id: str,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        """Record skill invocation start in database."""
        now = datetime.now(UTC).isoformat()
        
        self.logger.debug(
            f"💾 [SKILL_INVOKER] Recording invocation start: {invocation_id[:8]}... "
            f"skill='{skill_id}' user={user_id[:8]}..."
        )
        
        # Extract goal_id from context if available
        goal_id = context.get("goal_id") if context else None
        
        self.db.execute(
            """INSERT INTO agency_skill_executions (
                execution_id, skill_id, user_id, goal_id, outcome,
                context_json, created_at
            ) VALUES (?, ?, ?, ?, 'running', ?, ?)""",
            (
                invocation_id,
                skill_id,
                user_id,
                goal_id,
                json.dumps(context),
                now,
            )
        )
        self.db.commit()
    
    async def _record_invocation_complete(
        self,
        invocation_id: str,
        success: bool,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Record skill invocation completion."""
        now = datetime.now(UTC).isoformat()
        
        status = "completed" if success else "failed"
        self.logger.debug(
            f"💾 [SKILL_INVOKER] Recording invocation complete: {invocation_id[:8]}... "
            f"status={status} duration={duration_ms}ms"
        )
        
        self.db.execute(
            """UPDATE agency_skill_executions
               SET outcome = ?, error_message = ?, execution_time_ms = ?
               WHERE execution_id = ?""",
            (
                "completed" if success else "failed",
                error_message,
                duration_ms,
                invocation_id,
            )
        )
        self.db.commit()
