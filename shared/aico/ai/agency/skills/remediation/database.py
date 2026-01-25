"""Database Remediation Skills

Skills for database maintenance and remediation actions.
"""

from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime, UTC

from aico.core.logging import get_logger
from ...tools import get_tool_registry
from ..registry import Skill, SkillParameter, SkillParameterType, SkillResult


logger = get_logger("shared.ai.agency.skills.remediation.database")


class RemediationPostgresVacuumSkill(Skill):
    """Run VACUUM and ANALYZE on PostgreSQL database."""
    
    def __init__(self, session_factory: Any):
        self._session_factory = session_factory
    
    @property
    def skill_id(self) -> str:
        return "maint.db.postgres.vacuum_and_analyze"
    
    @property
    def name(self) -> str:
        return "PostgreSQL Vacuum and Analyze"
    
    @property
    def description(self) -> str:
        return "Run VACUUM and ANALYZE on PostgreSQL to reclaim space and update statistics."
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["database_maintenance", "vacuum", "optimize"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["modifies_storage", "locks_tables"]
    
    @property
    def safety_level(self) -> str:
        return "medium"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.db.postgres.vacuum_analyze"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="table_name",
                type=SkillParameterType.STRING,
                description="Specific table to vacuum (None = all tables)",
                required=False,
            ),
            SkillParameter(
                name="full",
                type=SkillParameterType.BOOLEAN,
                description="Whether to run VACUUM FULL (more thorough but locks table)",
                required=False,
                default=False,
            ),
            SkillParameter(
                name="analyze",
                type=SkillParameterType.BOOLEAN,
                description="Whether to run ANALYZE after vacuum",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description="If true, only report what would be done",
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
        """Execute PostgreSQL vacuum."""
        logger.info("[REMEDIATION_POSTGRES] Running vacuum")
        
        try:
            from aico.ai.agency.tools.database_remediation import tool_db_postgres_vacuum_analyze
            
            table_name = input_data.get("table_name")
            full = input_data.get("full", False)
            analyze = input_data.get("analyze", True)
            dry_run = input_data.get("dry_run", True)
            
            logger.info(f"[REMEDIATION_POSTGRES] Skill received input_data: {input_data}")
            logger.info(f"[REMEDIATION_POSTGRES] Extracted dry_run={dry_run}")
            
            result = await tool_db_postgres_vacuum_analyze(
                self._session_factory,
                table_name=table_name,
                full=full,
                analyze=analyze,
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
            logger.error("[REMEDIATION_POSTGRES] Vacuum failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )


class RemediationPostgresArchiveSkill(Skill):
    """Archive old data from PostgreSQL tables."""
    
    def __init__(self, session_factory: Any):
        self._session_factory = session_factory
    
    @property
    def skill_id(self) -> str:
        return "maint.db.postgres.archive_old_data"
    
    @property
    def name(self) -> str:
        return "PostgreSQL Archive Old Data"
    
    @property
    def description(self) -> str:
        return "Archive old data from PostgreSQL tables to reduce disk usage."
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["database_maintenance", "archive", "cleanup"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["modifies_storage", "deletes_data"]
    
    @property
    def safety_level(self) -> str:
        return "high"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.db.postgres.archive_rows"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="table_name",
                type=SkillParameterType.STRING,
                description="Source table name",
                required=True,
            ),
            SkillParameter(
                name="archive_table_name",
                type=SkillParameterType.STRING,
                description="Destination archive table name",
                required=True,
            ),
            SkillParameter(
                name="where_clause",
                type=SkillParameterType.STRING,
                description="SQL WHERE clause to select rows to archive",
                required=True,
            ),
            SkillParameter(
                name="max_rows",
                type=SkillParameterType.INTEGER,
                description="Maximum number of rows to archive",
                required=False,
                default=1000,
            ),
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description="If true, only count rows that would be archived",
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
        """Execute PostgreSQL archival."""
        logger.info("[REMEDIATION_POSTGRES] Running archive")
        
        try:
            from aico.ai.agency.tools.database_remediation import tool_db_postgres_archive_rows
            
            result = await tool_db_postgres_archive_rows(
                self._session_factory,
                table_name=input_data["table_name"],
                archive_table_name=input_data["archive_table_name"],
                where_clause=input_data["where_clause"],
                max_rows=input_data.get("max_rows", 1000),
                dry_run=input_data.get("dry_run", True),
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
            logger.error("[REMEDIATION_POSTGRES] Archive failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )


class RemediationDatabaseDiskPressureSkill(Skill):
    """Comprehensive database disk pressure remediation."""
    
    def __init__(self, session_factory: Any):
        self._session_factory = session_factory
    
    @property
    def skill_id(self) -> str:
        return "maint.db.reduce_disk_pressure"
    
    @property
    def name(self) -> str:
        return "Reduce Database Disk Pressure"
    
    @property
    def description(self) -> str:
        return "Comprehensive disk pressure remediation: analyze tables, vacuum, and optionally archive old data."
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["database_maintenance", "disk_cleanup", "optimize"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["modifies_storage", "deletes_data"]
    
    @property
    def safety_level(self) -> str:
        return "high"
    
    @property
    def implementation_tools(self) -> List[str]:
        return [
            "tool.db.postgres.get_table_sizes",
            "tool.db.postgres.vacuum_analyze",
            "tool.db.postgres.archive_rows",
        ]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="vacuum",
                type=SkillParameterType.BOOLEAN,
                description="Whether to run VACUUM",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="archive_old_data",
                type=SkillParameterType.BOOLEAN,
                description="Whether to archive old data",
                required=False,
                default=False,
            ),
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description="If true, only report what would be done",
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
        """Execute comprehensive disk pressure remediation."""
        logger.info("[REMEDIATION_DB] Running disk pressure remediation")
        
        try:
            from aico.ai.agency.tools.database_remediation import (
                tool_db_postgres_get_table_sizes,
                tool_db_postgres_vacuum_analyze,
            )
            
            dry_run = input_data.get("dry_run", True)
            results = {}
            
            # Step 1: Get table sizes
            sizes_result = await tool_db_postgres_get_table_sizes(self._session_factory)
            results["table_sizes"] = sizes_result.get("data", {})
            
            # Step 2: Vacuum if requested
            if input_data.get("vacuum", True):
                vacuum_result = await tool_db_postgres_vacuum_analyze(
                    self._session_factory,
                    table_name=None,
                    full=False,
                    analyze=True,
                    dry_run=dry_run,
                )
                results["vacuum"] = vacuum_result.get("data", {})
            
            # Step 3: Archive old data if requested (placeholder)
            if input_data.get("archive_old_data", False):
                results["archive"] = {
                    "message": "Archive functionality requires table-specific configuration",
                    "dry_run": dry_run,
                }
            
            return SkillResult(
                success=True,
                output={
                    "summary_status": "healthy",
                    "results": results,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=None,
            )
        
        except Exception as exc:
            logger.error("[REMEDIATION_DB] Disk pressure remediation failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )


class RemediationChromaCompactSkill(Skill):
    """Compact ChromaDB collections."""
    
    @property
    def skill_id(self) -> str:
        return "maint.db.chroma.compact"
    
    @property
    def name(self) -> str:
        return "ChromaDB Compact"
    
    @property
    def description(self) -> str:
        return "Compact ChromaDB collections to reclaim space."
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["database_maintenance", "compact", "optimize"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["modifies_storage"]
    
    @property
    def safety_level(self) -> str:
        return "low"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.db.chroma.compact_store"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return []
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute ChromaDB compaction."""
        logger.info("[REMEDIATION_CHROMA] Running compaction")
        
        try:
            from aico.ai.agency.tools.database_remediation import tool_db_chroma_compact_store
            
            result = await tool_db_chroma_compact_store()
            
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
            logger.error("[REMEDIATION_CHROMA] Compaction failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )


class RemediationLmdbCompactSkill(Skill):
    """Compact LMDB database."""
    
    @property
    def skill_id(self) -> str:
        return "maint.db.lmdb.compact_store"
    
    @property
    def name(self) -> str:
        return "LMDB Compact"
    
    @property
    def description(self) -> str:
        return "Compact LMDB database to reclaim space."
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["database_maintenance", "compact", "optimize"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["modifies_storage", "requires_restart"]
    
    @property
    def safety_level(self) -> str:
        return "medium"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.db.lmdb.compact"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description="If true, only report what would be done",
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
        """Execute LMDB compaction."""
        logger.info("[REMEDIATION_LMDB] Running compaction")
        
        try:
            from aico.ai.agency.tools.database_remediation import tool_db_lmdb_compact
            
            result = await tool_db_lmdb_compact(
                dry_run=input_data.get("dry_run", True)
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
            logger.error("[REMEDIATION_LMDB] Compaction failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )


class RemediationLmdbCleanupSkill(Skill):
    """Cleanup obsolete entries from LMDB."""
    
    @property
    def skill_id(self) -> str:
        return "maint.db.lmdb.cleanup_obsolete_entries"
    
    @property
    def name(self) -> str:
        return "LMDB Cleanup Obsolete Entries"
    
    @property
    def description(self) -> str:
        return "Delete obsolete entries from LMDB by key prefix."
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["database_maintenance", "cleanup", "delete"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["modifies_storage", "deletes_data"]
    
    @property
    def safety_level(self) -> str:
        return "high"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.db.lmdb.delete_keys_by_prefix"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="db_name",
                type=SkillParameterType.STRING,
                description="Name of the LMDB sub-database",
                required=True,
            ),
            SkillParameter(
                name="prefix",
                type=SkillParameterType.STRING,
                description="Key prefix to match for deletion",
                required=True,
            ),
            SkillParameter(
                name="max_keys",
                type=SkillParameterType.INTEGER,
                description="Maximum number of keys to delete",
                required=False,
                default=1000,
            ),
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description="If true, only count keys that would be deleted",
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
        """Execute LMDB cleanup."""
        logger.info("[REMEDIATION_LMDB] Running cleanup")
        
        try:
            from aico.ai.agency.tools.database_remediation import tool_db_lmdb_delete_keys_by_prefix
            
            result = await tool_db_lmdb_delete_keys_by_prefix(
                db_name=input_data["db_name"],
                prefix=input_data["prefix"],
                max_keys=input_data.get("max_keys", 1000),
                dry_run=input_data.get("dry_run", True),
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
            logger.error("[REMEDIATION_LMDB] Cleanup failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )
