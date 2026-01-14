"""
Memory System Metrics Endpoint

Provides metrics for the memory subsystem including:
- Working memory size
- Semantic query performance
- Knowledge graph statistics
- Storage breakdown
- Consolidation health

Metrics sourced from InfluxDB (memory_query measurement) and database queries.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
import os
import lmdb

from ..models import MemoryMetrics, MetricValue
from ..influx_client import MetricsInfluxClient
from aico.core.logging import get_logger
from backend.api.system.dependencies import get_current_user, get_db_connection
from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork

logger = get_logger("backend.api.metrics.memory")

router = APIRouter()


@router.get("/memory", response_model=MemoryMetrics)
async def get_memory_metrics(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> MemoryMetrics:
    """Get memory system metrics from LMDB, InfluxDB, PostgreSQL, and ChromaDB."""
    try:
        # Working Memory - count entries in LMDB sub-databases
        working_memory_count = 0
        try:
            lmdb_path = os.path.expanduser("~/Library/Application Support/aico/data/memory/working")
            if os.path.exists(lmdb_path):
                env = lmdb.open(lmdb_path, readonly=True, lock=False, max_dbs=10)
                
                # Count entries in session_memory database
                with env.begin() as txn:
                    session_db = env.open_db(b'session_memory', txn=txn)
                    session_stat = txn.stat(session_db)
                    working_memory_count += session_stat['entries']
                
                # Count entries in user_sessions database
                with env.begin() as txn:
                    user_db = env.open_db(b'user_sessions', txn=txn)
                    user_stat = txn.stat(user_db)
                    working_memory_count += user_stat['entries']
                
                env.close()
        except Exception as e:
            logger.debug(f"Failed to read LMDB working memory: {e}")
        
        # Semantic Queries - rate from InfluxDB
        semantic_qps = 0.0
        try:
            with MetricsInfluxClient() as client:
                # Query semantic memory operations from last hour
                query_count_1h = client.count_points("memory_query", "-1h", {"query_type": "semantic_search"})
                semantic_qps = round(query_count_1h / 3600, 6) if query_count_1h > 0 else 0.0
        except Exception as e:
            logger.debug(f"Failed to query semantic metrics from InfluxDB: {e}")
        
        kg_node_count = 0
        kg_edge_count = 0
        entity_distribution = {}
        relationship_distribution = {}
        
        try:
            # Get all KG nodes and edges from repository
            all_nodes = await uow.kg_nodes.list(limit=100000)
            all_edges = await uow.kg_edges.list(limit=100000)
            
            # Total counts
            kg_node_count = len(all_nodes)
            kg_edge_count = len(all_edges)
            
            # Entity type distribution (top 10 current entity types)
            current_nodes = [n for n in all_nodes if n.is_current]
            label_counts = {}
            for node in current_nodes:
                label = node.label or 'unknown'
                label_counts[label] = label_counts.get(label, 0) + 1
            entity_distribution = dict(sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            
            # Relationship type distribution (top 10 current relationship types)
            current_edges = [e for e in all_edges if e.is_current]
            relation_counts = {}
            for edge in current_edges:
                rel_type = edge.relation_type or 'unknown'
                relation_counts[rel_type] = relation_counts.get(rel_type, 0) + 1
            relationship_distribution = dict(sorted(relation_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            
        except Exception as e:
            logger.debug(f"Failed to query KG stats from repository: {e}")
        
        # Storage Breakdown - calculate sizes
        storage_breakdown = {}
        try:
            # LMDB size
            if os.path.exists(lmdb_path):
                lmdb_size = sum(os.path.getsize(os.path.join(lmdb_path, f)) for f in os.listdir(lmdb_path) if os.path.isfile(os.path.join(lmdb_path, f)))
                storage_breakdown["LMDB"] = round(lmdb_size / (1024 * 1024), 2)
            
            # ChromaDB size
            chromadb_path = os.path.expanduser("~/Library/Application Support/aico/data/chromadb")
            if os.path.exists(chromadb_path):
                chromadb_size = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, filenames in os.walk(chromadb_path) for f in filenames)
                storage_breakdown["ChromaDB"] = round(chromadb_size / (1024 * 1024), 2)
            
            # PostgreSQL KG size (approximate from row counts)
            kg_size_estimate = (kg_node_count * 0.5 + kg_edge_count * 0.3) / 1024  # Rough estimate in MB
            storage_breakdown["PostgreSQL"] = round(kg_size_estimate, 2)
            
        except Exception as e:
            logger.debug(f"Failed to calculate storage sizes: {e}")
        
        # Consolidation health - check last consolidation from scheduler
        consolidation_health = 100.0
        last_consolidation = "N/A"
        try:
            # Get last consolidation from scheduler executions
            executions = await uow.scheduler_task_executions.list(
                filters={"task_id": "ams.memory_consolidation", "status": "completed"},
                limit=1
            )
            if executions:
                last_consolidation = executions[0].started_at.isoformat() if hasattr(executions[0].started_at, 'isoformat') else str(executions[0].started_at)
                # Health is good if consolidation ran in last 24h
                from datetime import datetime, timezone
                last_run = datetime.fromisoformat(result[0].replace('Z', '+00:00'))
                hours_since = (datetime.now(timezone.utc) - last_run).total_seconds() / 3600
                if hours_since > 48:
                    consolidation_health = 50.0
                elif hours_since > 24:
                    consolidation_health = 75.0
        except Exception as e:
            logger.debug(f"Failed to check consolidation status: {e}")
        
        return MemoryMetrics(
            working_memory_size=MetricValue(
                value=working_memory_count,
                unit="entries",
                status="healthy" if working_memory_count < 10000 else "warning"
            ),
            semantic_queries_per_second=MetricValue(
                value=semantic_qps,
                unit="queries/s",
                status="healthy"
            ),
            kg_nodes=MetricValue(
                value=kg_node_count,
                unit="nodes",
                status="healthy"
            ),
            kg_relationships=MetricValue(
                value=kg_edge_count,
                unit="edges",
                status="healthy"
            ),
            entity_type_distribution=entity_distribution,
            relationship_type_distribution=relationship_distribution,
            storage_breakdown=storage_breakdown,
            consolidation_health=MetricValue(
                value=consolidation_health,
                unit="%",
                status="healthy" if consolidation_health > 80 else "warning"
            ),
            last_consolidation=last_consolidation
        )
    
    except Exception as e:
        logger.error(f"Failed to get memory metrics: {e}")
        # Return zero metrics on error
        return MemoryMetrics(
            working_memory_size=MetricValue(value=0, unit="entries", status="healthy"),
            semantic_queries_per_second=MetricValue(value=0.0, unit="queries/s", status="healthy"),
            kg_nodes=MetricValue(value=0, unit="nodes", status="healthy"),
            kg_relationships=MetricValue(value=0, unit="edges", status="healthy"),
            entity_type_distribution={},
            relationship_type_distribution={},
            storage_breakdown={},
            consolidation_health=MetricValue(value=100.0, unit="%", status="healthy"),
            last_consolidation="N/A"
        )
