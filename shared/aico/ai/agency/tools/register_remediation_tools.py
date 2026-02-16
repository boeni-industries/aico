"""Register Remediation Tools

Registers all remediation tools in the tool registry.
"""

from .registry import get_tool_registry, ToolDefinition, ToolParameter
from . import database_remediation
from . import service_remediation


def register_remediation_tools():
    """Register all remediation tools in the tool registry."""
    registry = get_tool_registry()
    
    # ========================================================================
    # PostgreSQL Remediation Tools
    # ========================================================================
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.postgres.get_table_sizes",
        name="PostgreSQL Get Table Sizes",
        description="Get table and index sizes for PostgreSQL database",
        domain="db",
        backend="postgres",
        capability_tags=["query_size", "analyze"],
        side_effect_tags=["reads_database"],
        safety_level="low",
        resource_profile="tiny",
        handler=database_remediation.tool_db_postgres_get_table_sizes,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.postgres.vacuum_analyze",
        name="PostgreSQL VACUUM ANALYZE",
        description="Run VACUUM and ANALYZE on PostgreSQL tables",
        domain="db",
        backend="postgres",
        capability_tags=["vacuum", "optimize", "maintenance"],
        side_effect_tags=["modifies_storage", "locks_tables"],
        safety_level="medium",
        resource_profile="medium",
        handler=database_remediation.tool_db_postgres_vacuum_analyze,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.postgres.archive_rows",
        name="PostgreSQL Archive Rows",
        description="Archive old rows from a table to an archive table",
        domain="db",
        backend="postgres",
        capability_tags=["archive", "cleanup", "maintenance"],
        side_effect_tags=["modifies_storage", "deletes_data"],
        safety_level="high",
        resource_profile="medium",
        handler=database_remediation.tool_db_postgres_archive_rows,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.postgres.delete_rows",
        name="PostgreSQL Delete Rows",
        description="Delete rows from a PostgreSQL table with safety checks",
        domain="db",
        backend="postgres",
        capability_tags=["delete", "cleanup"],
        side_effect_tags=["modifies_storage", "deletes_data"],
        safety_level="high",
        resource_profile="small",
        handler=database_remediation.tool_db_postgres_delete_rows,
    ))
    
    # ========================================================================
    # ChromaDB Remediation Tools
    # ========================================================================
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.chroma.get_collection_stats",
        name="ChromaDB Get Collection Stats",
        description="Get statistics for all ChromaDB collections",
        domain="db",
        backend="chroma",
        capability_tags=["query_stats", "analyze"],
        side_effect_tags=["reads_database"],
        safety_level="low",
        resource_profile="tiny",
        handler=database_remediation.tool_db_chroma_get_collection_stats,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.chroma.delete_vectors",
        name="ChromaDB Delete Vectors",
        description="Delete vectors from a ChromaDB collection",
        domain="db",
        backend="chroma",
        capability_tags=["delete", "cleanup"],
        side_effect_tags=["modifies_storage", "deletes_data"],
        safety_level="high",
        resource_profile="small",
        handler=database_remediation.tool_db_chroma_delete_vectors,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.chroma.compact_store",
        name="ChromaDB Compact Store",
        description="Trigger compaction for ChromaDB",
        domain="db",
        backend="chroma",
        capability_tags=["compact", "optimize"],
        side_effect_tags=["modifies_storage"],
        safety_level="low",
        resource_profile="small",
        handler=database_remediation.tool_db_chroma_compact_store,
    ))
    
    # ========================================================================
    # InfluxDB Remediation Tools
    # ========================================================================
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.influx.list_retention_policies",
        name="InfluxDB List Retention Policies",
        description="List retention policies for InfluxDB buckets",
        domain="db",
        backend="influx",
        capability_tags=["query_retention", "analyze"],
        side_effect_tags=["reads_database"],
        safety_level="low",
        resource_profile="tiny",
        handler=database_remediation.tool_db_influx_list_retention_policies,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.influx.apply_retention_policy",
        name="InfluxDB Apply Retention Policy",
        description="Apply or update retention policy for an InfluxDB bucket",
        domain="db",
        backend="influx",
        capability_tags=["update_retention", "maintenance"],
        side_effect_tags=["modifies_config"],
        safety_level="medium",
        resource_profile="tiny",
        handler=database_remediation.tool_db_influx_apply_retention_policy,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.influx.drop_measurement",
        name="InfluxDB Drop Measurement",
        description="Drop (delete) a measurement or time range from InfluxDB",
        domain="db",
        backend="influx",
        capability_tags=["delete", "cleanup"],
        side_effect_tags=["modifies_storage", "deletes_data"],
        safety_level="high",
        resource_profile="small",
        handler=database_remediation.tool_db_influx_drop_measurement,
    ))
    
    # ========================================================================
    # LMDB Remediation Tools
    # ========================================================================
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.lmdb.check_map_size",
        name="LMDB Check Map Size",
        description="Check LMDB map size usage",
        domain="db",
        backend="lmdb",
        capability_tags=["query_size", "analyze"],
        side_effect_tags=["reads_database"],
        safety_level="low",
        resource_profile="tiny",
        handler=database_remediation.tool_db_lmdb_check_map_size,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.lmdb.compact",
        name="LMDB Compact",
        description="Compact LMDB database by copying to a new file",
        domain="db",
        backend="lmdb",
        capability_tags=["compact", "optimize"],
        side_effect_tags=["modifies_storage", "requires_restart"],
        safety_level="medium",
        resource_profile="medium",
        handler=database_remediation.tool_db_lmdb_compact,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.db.lmdb.delete_keys_by_prefix",
        name="LMDB Delete Keys by Prefix",
        description="Delete keys from LMDB by prefix",
        domain="db",
        backend="lmdb",
        capability_tags=["delete", "cleanup"],
        side_effect_tags=["modifies_storage", "deletes_data"],
        safety_level="high",
        resource_profile="small",
        handler=database_remediation.tool_db_lmdb_delete_keys_by_prefix,
    ))
    
    # ========================================================================
    # Modelservice Remediation Tools
    # ========================================================================
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.modelservice.restart_workers",
        name="Modelservice Restart Workers",
        description="Restart modelservice worker processes",
        domain="modelservice",
        backend="zmq",
        capability_tags=["restart", "recover"],
        side_effect_tags=["restarts_service"],
        safety_level="high",
        resource_profile="small",
        handler=service_remediation.tool_modelservice_restart_workers,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.modelservice.clear_cache",
        name="Modelservice Clear Cache",
        description="Clear modelservice internal caches",
        domain="modelservice",
        backend="zmq",
        capability_tags=["clear_cache", "recover"],
        side_effect_tags=["clears_cache"],
        safety_level="low",
        resource_profile="tiny",
        handler=service_remediation.tool_modelservice_clear_cache,
    ))
    
    # ========================================================================
    # Agency Remediation Tools
    # ========================================================================
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.agency.retire_stalled_plans",
        name="Agency Retire Stalled Plans",
        description="Retire stalled agency plans",
        domain="agency",
        backend="postgres",
        capability_tags=["retire_plans", "cleanup"],
        side_effect_tags=["modifies_database", "updates_plans"],
        safety_level="medium",
        resource_profile="small",
        handler=service_remediation.tool_agency_retire_stalled_plans,
    ))
    
    registry.register_tool(ToolDefinition(
        tool_id="tool.agency.update_scheduler_config",
        name="Agency Update Scheduler Config",
        description="Update agency scheduler configuration",
        domain="agency",
        backend="python",
        capability_tags=["update_config", "rebalance"],
        side_effect_tags=["modifies_config"],
        safety_level="medium",
        resource_profile="tiny",
        handler=service_remediation.tool_agency_update_scheduler_config,
    ))


# Auto-register on import
register_remediation_tools()
