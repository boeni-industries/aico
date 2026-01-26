"""InfluxDB Remediation Skills

Implements remediation skills for InfluxDB maintenance including retention
policy management and measurement cleanup.
"""

from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime, UTC

from aico.core.logging import get_logger
from ..registry import Skill, SkillParameter, SkillParameterType, SkillResult


logger = get_logger("shared.ai.agency.skills.remediation.influx")


# ============================================================================
# InfluxDB Remediation Skills
# ============================================================================

class RemediationInfluxGetMeasurementsSkill(Skill):
    """List all measurements in InfluxDB with size estimates.
    
    Useful for understanding what data exists before applying retention policies.
    """
    
    def __init__(self, config: Any):
        self._config = config
    
    @property
    def skill_id(self) -> str:
        return "maint.db.influx.get_measurements"
    
    @property
    def name(self) -> str:
        return "InfluxDB List Measurements"
    
    @property
    def description(self) -> str:
        return "List all measurements in InfluxDB bucket with size estimates"
    
    @property
    def category(self) -> str:
        return "diagnostics"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["database", "diagnostics", "influx", "read_only"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return []
    
    @property
    def safety_level(self) -> str:
        return "low"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.db.influx.get_measurements"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="measurement_filter",
                type=SkillParameterType.STRING,
                description="Optional regex filter for measurement names",
                required=False,
                default=None,
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute InfluxDB measurement listing."""
        logger.info("[REMEDIATION_INFLUX] Listing measurements")
        
        try:
            from aico.ai.agency.tools.database_remediation import tool_db_influx_get_measurements
            
            measurement_filter = input_data.get("measurement_filter")
            
            logger.info(f"[REMEDIATION_INFLUX] measurement_filter={measurement_filter}")
            
            result = await tool_db_influx_get_measurements(
                config=self._config,
                measurement_filter=measurement_filter,
            )
            
            success = result.get("ok", False)
            data = result.get("data", {})
            
            return SkillResult(
                success=success,
                output={
                    "summary_status": "healthy" if success else "unhealthy",
                    "result": data,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=result.get("error", {}).get("message") if not success else None,
            )
        
        except Exception as exc:
            logger.error("[REMEDIATION_INFLUX] List measurements failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )


class RemediationInfluxApplyRetentionSkill(Skill):
    """Apply retention policies to InfluxDB measurements.
    
    Deletes data older than configured retention periods. Can target specific
    measurements or apply all configured retention policies.
    """
    
    def __init__(self, config: Any):
        self._config = config
    
    @property
    def skill_id(self) -> str:
        return "maint.db.influx.apply_retention"
    
    @property
    def name(self) -> str:
        return "InfluxDB Apply Retention Policy"
    
    @property
    def description(self) -> str:
        return "Apply retention policies to delete old data from InfluxDB measurements (logs, metrics)"
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["database", "cleanup", "retention", "influx"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["modifies_storage", "deletes_data"]
    
    @property
    def safety_level(self) -> str:
        return "high"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.db.influx.apply_retention"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="measurement",
                type=SkillParameterType.STRING,
                description="Specific measurement to clean (None = apply all configured policies)",
                required=False,
                default=None,
            ),
            SkillParameter(
                name="retention_days",
                type=SkillParameterType.INTEGER,
                description="Days to retain (overrides config, None = use config)",
                required=False,
                default=None,
            ),
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description="If true, only report what would be deleted",
                required=False,
                default=True,
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute InfluxDB retention policy."""
        logger.info("[REMEDIATION_INFLUX] Applying retention policy")
        
        try:
            from aico.ai.agency.tools.database_remediation import tool_db_influx_apply_retention
            
            measurement = input_data.get("measurement")
            retention_days = input_data.get("retention_days")
            dry_run = input_data.get("dry_run", True)
            
            print(f"\n{'='*80}")
            print(f"[INFLUX SKILL] Received input_data")
            print(f"{'='*80}")
            print(f"Full input_data: {input_data}")
            print(f"Extracted measurement: {measurement}")
            print(f"Extracted retention_days: {retention_days}")
            print(f"Extracted dry_run: {dry_run} (type: {type(dry_run).__name__})")
            print(f"Calling tool with dry_run={dry_run}")
            print(f"{'='*80}\n")
            
            logger.info(f"[REMEDIATION_INFLUX] input_data={input_data}")
            logger.info(f"[REMEDIATION_INFLUX] measurement={measurement}, retention_days={retention_days}, dry_run={dry_run}, type={type(dry_run)}")
            
            result = await tool_db_influx_apply_retention(
                config=self._config,
                measurement=measurement,
                retention_days=retention_days,
                dry_run=dry_run,
            )
            
            print(f"\n{'='*80}")
            print(f"[INFLUX SKILL] Tool returned result")
            print(f"{'='*80}")
            print(f"Result ok: {result.get('ok')}")
            print(f"Result details dry_run: {result.get('data', {}).get('details', {}).get('dry_run')}")
            print(f"{'='*80}\n")
            
            success = result.get("ok", False)
            data = result.get("data", {})
            
            # Extract dry_run from the result details
            details = data.get("details", {})
            was_dry_run = details.get("dry_run", dry_run)
            
            return SkillResult(
                success=success,
                output={
                    "summary_status": "healthy" if success else "unhealthy",
                    "dry_run": was_dry_run,
                    "result": data,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=result.get("error", {}).get("message") if not success else None,
            )
        
        except Exception as exc:
            logger.error("[REMEDIATION_INFLUX] Retention apply failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )


class RemediationInfluxDropMeasurementSkill(Skill):
    """Drop an entire measurement from InfluxDB.
    
    WARNING: This deletes ALL data for the specified measurement.
    Use with extreme caution.
    """
    
    def __init__(self, config: Any):
        self._config = config
    
    @property
    def skill_id(self) -> str:
        return "maint.db.influx.drop_measurement"
    
    @property
    def name(self) -> str:
        return "InfluxDB Drop Measurement"
    
    @property
    def description(self) -> str:
        return "Drop an entire measurement from InfluxDB (deletes ALL data)"
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["database", "cleanup", "drop", "influx"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["modifies_storage", "deletes_data", "destructive"]
    
    @property
    def safety_level(self) -> str:
        return "privileged"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.db.influx.drop_measurement"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="measurement",
                type=SkillParameterType.STRING,
                description="Measurement name to drop",
                required=True,
            ),
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description="If true, only report what would be deleted",
                required=False,
                default=True,
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute InfluxDB measurement drop."""
        logger.info("[REMEDIATION_INFLUX] Dropping measurement")
        
        try:
            from aico.ai.agency.tools.database_remediation import tool_db_influx_drop_measurement
            
            measurement = input_data["measurement"]
            dry_run = input_data.get("dry_run", True)
            
            logger.info(f"[REMEDIATION_INFLUX] measurement={measurement}, dry_run={dry_run}")
            
            result = await tool_db_influx_drop_measurement(
                config=self._config,
                measurement=measurement,
                dry_run=dry_run,
            )
            
            success = result.get("ok", False)
            data = result.get("data", {})
            
            # Extract dry_run from the result details
            details = data.get("details", {})
            was_dry_run = details.get("dry_run", dry_run)
            
            return SkillResult(
                success=success,
                output={
                    "summary_status": "healthy" if success else "unhealthy",
                    "dry_run": was_dry_run,
                    "result": data,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=result.get("error", {}).get("message") if not success else None,
            )
        
        except Exception as exc:
            logger.error("[REMEDIATION_INFLUX] Drop measurement failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )
