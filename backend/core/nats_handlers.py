"""
NATS request handlers for core services.

Handles gateway→core requests via NATS request/reply pattern.
"""

import json
import os
from typing import Any, Dict
from aico.core.logging import get_logger
from google.protobuf.struct_pb2 import Struct
from opentelemetry import trace

logger = get_logger("backend.core.nats_handlers")
tracer = trace.get_tracer(__name__)


def trace_nats_handler(subject: str):
    """Decorator to add OpenTelemetry tracing to NATS handlers"""
    def decorator(func):
        async def wrapper(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
            with tracer.start_as_current_span(
                f"nats.handle.{subject}",
                kind=trace.SpanKind.SERVER,
                attributes={
                    "messaging.system": "nats",
                    "messaging.destination": subject,
                    "messaging.operation": "handle",
                }
            ) as span:
                try:
                    result = await func(self, request_data)
                    if result.get("error"):
                        span.set_status(trace.Status(trace.StatusCode.ERROR, result.get("message", "Unknown error")))
                        span.set_attribute("error.type", result.get("error"))
                    else:
                        span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator


class CoreNATSHandlers:
    """NATS request handlers for core services"""
    
    def __init__(self, service_container):
        self.container = service_container
        self.logger = logger
    
    @trace_nats_handler("scheduler.status")
    async def handle_scheduler_status_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scheduler status request from gateway"""
        try:
            scheduler = self.container.get_service("task_scheduler")
            if scheduler is None:
                return {
                    "error": "SCHEDULER_NOT_AVAILABLE",
                    "message": "Task scheduler not available"
                }
            
            status = scheduler.get_status()
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get scheduler status: {e}")
            return {
                "error": "SCHEDULER_ERROR",
                "message": str(e)
            }
    
    async def handle_scheduler_tasks_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scheduler tasks list request from gateway"""
        try:
            enabled_only = request_data.get("enabled_only", False)
            
            # Get scheduler service
            scheduler = self.container.get_service("task_scheduler")
            if scheduler is None:
                return {
                    "error": "SCHEDULER_NOT_AVAILABLE",
                    "message": "Task scheduler not available"
                }
            
            # Return task info matching TaskConfigResponse schema
            tasks = []
            for task_id, task_class in scheduler.task_registry.tasks.items():
                tasks.append({
                    "task_id": task_id,
                    "task_class": task_class.__name__ if hasattr(task_class, '__name__') else str(task_class),
                    "schedule": "* * * * *",
                    "config": {},
                    "enabled": True,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                })
            
            return {"tasks": tasks, "total_count": len(tasks)}
            
        except Exception as e:
            self.logger.error(f"Failed to list scheduler tasks: {e}", exc_info=True)
            return {
                "error": "SCHEDULER_ERROR",
                "message": str(e)
            }
    
    async def handle_emotion_current_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle current emotion state request from gateway"""
        try:
            # Get emotion engine service
            emotion_engine = self.container.get_service("emotion_engine")
            if emotion_engine is None:
                return {
                    "error": "EMOTION_ENGINE_UNAVAILABLE",
                    "message": "Emotion engine unavailable"
                }
            
            # Get current emotional state from engine
            current_state = emotion_engine.current_state
            
            if current_state is None:
                return {
                    "error": "EMOTION_STATE_NOT_AVAILABLE",
                    "message": "No emotional state available"
                }
            
            # Convert to response format matching EmotionStateResponse schema
            return {
                "timestamp": current_state.timestamp.isoformat() + "Z",
                "primary": current_state.subjective_feeling.value,
                "confidence": current_state.intensity,
                "valence": current_state.mood_valence,
                "arousal": current_state.mood_arousal,
                "dominance": 0.5  # Default neutral dominance (not yet implemented in CPM)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get current emotion: {e}", exc_info=True)
            return {
                "error": "EMOTION_ENGINE_ERROR",
                "message": str(e)
            }
    
    async def handle_emotion_history_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emotion history request from gateway"""
        try:
            # Extract query params
            limit = request_data.get("limit", 10)
            hours = request_data.get("hours", 24)
            
            # Get emotion engine service
            emotion_engine = self.container.get_service("emotion_engine")
            if emotion_engine is None:
                return {
                    "error": "EMOTION_ENGINE_UNAVAILABLE",
                    "message": "Emotion engine unavailable"
                }
            
            # Get emotion state history from engine
            history = await emotion_engine.get_state_history(limit=limit, hours=hours)
            self.logger.info(f"🎭 Emotion engine returned {len(history)} states (limit={limit}, hours={hours})")
            
            # Add metadata about data age and diversity
            metadata = {}
            if history:
                from datetime import datetime, UTC
                
                # Check data age
                try:
                    last_timestamp = datetime.fromisoformat(history[-1]["timestamp"].replace('Z', '+00:00'))
                    age_hours = (datetime.now(UTC) - last_timestamp).total_seconds() / 3600
                    metadata["oldest_record_age_hours"] = age_hours
                    metadata["newest_record_timestamp"] = history[-1]["timestamp"]
                    metadata["oldest_record_timestamp"] = history[0]["timestamp"]
                except Exception as e:
                    self.logger.warning(f"Could not parse timestamp for metadata: {e}")
                
                # Check diversity
                unique_feelings = len(set(h.get('feeling') for h in history))
                metadata["unique_feelings_count"] = unique_feelings
                
                self.logger.info(f"🎭 Data diversity: {unique_feelings} unique feelings, newest record age: {metadata.get('oldest_record_age_hours', 0):.1f}h")
            
            return {
                "count": len(history), 
                "history": history,
                "metadata": metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get emotion history: {e}", exc_info=True)
            return {
                "error": "EMOTION_ENGINE_ERROR",
                "message": str(e)
            }
    
    async def handle_memory_semantic_stats_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle semantic memory stats request from gateway"""
        try:
            from aico.ai import ai_registry
            from sqlalchemy import select, func, text
            from aico.data.tables import conversation_segments
            
            memory_manager = ai_registry.get("memory")
            if not memory_manager:
                return {
                    "error": "MEMORY_MANAGER_NOT_INITIALIZED",
                    "message": "Memory manager not initialized"
                }
            
            if not hasattr(memory_manager, '_semantic_store'):
                return {
                    "error": "SEMANTIC_MEMORY_NOT_INITIALIZED",
                    "message": "Semantic memory not initialized"
                }
            
            # Use exact same logic as original router.py - query database directly
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow_instance:
                stmt = select(func.count()).select_from(conversation_segments)
                total_vectors = (await uow_instance._session.execute(stmt)).scalar() or 0

                # Estimate storage size using Postgres relation size (includes table + indexes)
                index_size_mb = 0.0
                try:
                    size_stmt = text("SELECT pg_total_relation_size('aico_core.conversation_segments')")
                    size_bytes = (await uow_instance._session.execute(size_stmt)).scalar() or 0
                    index_size_mb = float(size_bytes) / (1024.0 * 1024.0)
                except Exception:
                    # If size query fails, keep 0 and fall back below
                    index_size_mb = 0.0

                # Guard: avoid 0 MB when vectors exist (Studio derives per-MB metrics)
                if int(total_vectors) > 0 and index_size_mb <= 0.0:
                    # Rough lower-bound estimate: vector payload only (768 float32)
                    index_size_mb = max(0.01, (int(total_vectors) * 768 * 4) / (1024.0 * 1024.0))
                
                collections = [
                    {"name": "conversation_segments", "count": int(total_vectors), "dimension": 768}
                ]
                
                return {
                    "total_vectors": int(total_vectors),
                    "collections": collections,
                    "index_size_mb": float(index_size_mb),
                    "avg_retrieval_latency_ms": 0.0,
                    "retrieval_quality_percent": 0.0
                }
            
        except Exception as e:
            self.logger.error(f"Failed to get semantic memory stats: {e}", exc_info=True)
            return {
                "error": "SEMANTIC_MEMORY_STATS_FAILED",
                "message": str(e)
            }
    
    async def handle_memory_working_stats_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle working memory stats request from gateway"""
        try:
            from aico.ai import ai_registry
            
            memory_manager = ai_registry.get("memory")
            if not memory_manager:
                return {
                    "error": "MEMORY_MANAGER_NOT_INITIALIZED",
                    "message": "Memory manager not initialized"
                }
            
            if not hasattr(memory_manager, '_working_store'):
                return {
                    "error": "WORKING_MEMORY_NOT_INITIALIZED",
                    "message": "Working memory not initialized"
                }
            
            working_store = memory_manager._working_store
            stats = await working_store.get_stats()
            
            # Use exact same logic as original router.py
            active_items = stats.get('active_items', 0)
            capacity = stats.get('capacity', max(10000, int(active_items) * 2 if isinstance(active_items, int) else 10000))
            utilization_percent = stats.get('utilization_percent')
            if utilization_percent is None:
                utilization_percent = (active_items / capacity) * 100 if capacity else 0.0
            
            return {
                "active_items": active_items,
                "capacity": capacity,
                "utilization_percent": float(utilization_percent),
                "ttl_utilization_percent": float(stats.get('ttl_utilization_percent', utilization_percent)),
                "eviction_rate_per_min": float(stats.get('eviction_rate_per_min', 0.0)),
                "recent_activity": stats.get('recent_activity', [])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get working memory stats: {e}", exc_info=True)
            return {
                "error": "WORKING_MEMORY_STATS_FAILED",
                "message": str(e)
            }
    
    async def handle_kg_stats_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG stats request from gateway - matches original router.py logic"""
        try:
            user_id = request_data.get("user_id")
            
            # Get UoW factory from service container
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            
            async with uow as uow_instance:
                # Get all nodes and edges for this user
                all_nodes = await uow_instance.kg_nodes.list(filters={"user_id": user_id}, limit=100000)
                all_edges = await uow_instance.kg_edges.list(filters={"user_id": user_id}, limit=100000)
                
                # Basic counts
                node_count = len(all_nodes)
                current_nodes = [n for n in all_nodes if n.is_current]
                current_node_count = len(current_nodes)
                historical_node_count = node_count - current_node_count
                
                edge_count = len(all_edges)
                current_edges = [e for e in all_edges if e.is_current]
                current_edge_count = len(current_edges)
                historical_edge_count = edge_count - current_edge_count
                
                # Node/edge type distributions
                import json
                node_types = {}
                for node in all_nodes:
                    label = node.label or "unknown"
                    node_types[label] = node_types.get(label, 0) + 1
                
                edge_types = {}
                for edge in all_edges:
                    rel_type = edge.relation_type or "unknown"
                    edge_types[rel_type] = edge_types.get(rel_type, 0) + 1
                
                # Total properties
                total_node_properties = 0
                for node in all_nodes:
                    if node.properties:
                        if isinstance(node.properties, str):
                            try:
                                props = json.loads(node.properties)
                                total_node_properties += len(props)
                            except:
                                pass
                        elif isinstance(node.properties, dict):
                            total_node_properties += len(node.properties)
                
                # Storage size estimation
                node_data_size = sum(
                    len(str(node.id or "")) + len(str(node.label or "")) + 
                    len(str(node.properties or "")) + len(str(node.source_text or ""))
                    for node in all_nodes
                )
                edge_data_size = sum(
                    len(str(edge.id or "")) + len(str(edge.relation_type or "")) + 
                    len(str(edge.properties or "")) + len(str(edge.source_text or ""))
                    for edge in all_edges
                )
                storage_size_mb = (node_data_size + edge_data_size) / (1024 * 1024) * 1.3
                
                # Health metrics
                avg_degree = current_edge_count / max(current_node_count, 1)
                isolated_nodes = sum(1 for node in current_nodes if not any(
                    e.source_id == node.id or e.target_id == node.id for e in current_edges
                ))
                
                return {
                    "total_nodes": node_count,
                    "current_nodes": current_node_count,
                    "historical_nodes": historical_node_count,
                    "total_edges": edge_count,
                    "current_edges": current_edge_count,
                    "historical_edges": historical_edge_count,
                    "total_node_properties": total_node_properties,
                    "node_types": node_types,
                    "edge_types": edge_types,
                    "storage_size_mb": round(storage_size_mb, 2),
                    "user_id": user_id,
                    "health": {
                        "orphaned_edges": 0,
                        "duplicate_nodes": 0,
                        "stale_nodes_count": 0,
                        "stale_nodes_percent": 0.0,
                        "property_completeness": total_node_properties / max(current_node_count, 1),
                        "nodes_added_24h": 0,
                        "edges_added_24h": 0
                    },
                    "duplicate_pairs": None,
                    "structure": {
                        "graph_density": current_edge_count / max((current_node_count * (current_node_count - 1)) / 2, 1) if current_node_count > 1 else 0.0,
                        "average_degree": avg_degree,
                        "max_degree": 0,
                        "min_degree": 0,
                        "isolated_nodes": isolated_nodes,
                        "connected_components": 1,
                        "largest_component_size": current_node_count
                    },
                    "temporal": {
                        "growth_rate_7d": 0.0,
                        "growth_rate_30d": 0.0,
                        "most_active_day": None,
                        "activity_by_day": {}
                    },
                    "centrality": {
                        "top_by_degree": [],
                        "top_by_pagerank": [],
                        "top_by_betweenness": []
                    },
                    "clustering": {
                        "global_clustering_coefficient": 0.0,
                        "average_clustering_coefficient": 0.0,
                        "communities_detected": 0,
                        "modularity_score": 0.0
                    }
                }
        except Exception as e:
            self.logger.error(f"Failed to get KG stats: {e}", exc_info=True)
            return {
                "error": "KG_STATS_FAILED",
                "message": str(e)
            }
    
    async def handle_kg_nodes_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG nodes request from gateway"""
        try:
            user_id = request_data.get("user_id")
            limit = request_data.get("limit", 1000)
            offset = request_data.get("offset", 0)
            limit = min(limit, 1000)
            
            # Get UoW factory from service container
            uow_factory = self.container.get_service("uow")
            
            # Query KG nodes from database
            uow = uow_factory()
            async with uow as uow_instance:
                nodes = await uow_instance.kg_nodes.list(filters={"user_id": user_id}, limit=limit, offset=offset)
                
                # Convert to dict format - match original router.py format
                import json
                nodes_list = []
                for node in nodes:
                    nodes_list.append({
                        "id": node.id,
                        "user_id": node.user_id,
                        "label": node.label,
                        "properties": json.loads(node.properties) if isinstance(node.properties, str) else (node.properties or {}),
                        "confidence": node.confidence,
                        "source_text": node.source_text,
                        "created_at": node.created_at.isoformat() if getattr(node, "created_at", None) else None,
                        "updated_at": node.updated_at.isoformat() if getattr(node, "updated_at", None) else None,
                        "valid_from": node.valid_from.isoformat() if getattr(node, "valid_from", None) else None,
                        "valid_until": node.valid_until.isoformat() if getattr(node, "valid_until", None) else None,
                        "is_current": bool(node.is_current),
                        "canonical_id": getattr(node, "canonical_id", None),
                        "aliases": json.loads(node.aliases_json) if isinstance(getattr(node, "aliases_json", None), str) else (getattr(node, "aliases_json", None) or []),
                    })
                
                return {
                    "nodes": nodes_list,
                    "total": len(nodes_list),
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            self.logger.error(f"Failed to get KG nodes: {e}", exc_info=True)
            return {
                "nodes": [],
                "total": 0,
                "limit": request_data.get("limit", 1000),
                "offset": request_data.get("offset", 0)
            }
    
    async def handle_kg_edges_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG edges request from gateway"""
        try:
            user_id = request_data.get("user_id")
            limit = request_data.get("limit", 1000)
            offset = request_data.get("offset", 0)
            limit = min(limit, 1000)
            
            # Get UoW factory from service container
            uow_factory = self.container.get_service("uow")
            
            # Query KG edges from database
            uow = uow_factory()
            async with uow as uow_instance:
                edges = await uow_instance.kg_edges.list(
                    filters={"user_id": user_id, "is_current": True},
                    limit=limit,
                    offset=offset,
                )
                
                # Convert to dict format - match original router.py format
                import json
                edges_list = []
                for edge in edges:
                    edges_list.append({
                        "id": edge.id,
                        "user_id": edge.user_id,
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "relation_type": edge.relation_type,
                        "properties": json.loads(edge.properties) if isinstance(edge.properties, str) else (edge.properties or {}),
                        "confidence": edge.confidence,
                        "source_text": edge.source_text,
                        "created_at": edge.created_at.isoformat() if getattr(edge, "created_at", None) else None,
                        "updated_at": edge.updated_at.isoformat() if getattr(edge, "updated_at", None) else None,
                        "valid_from": edge.valid_from.isoformat() if getattr(edge, "valid_from", None) else None,
                        "valid_until": edge.valid_until.isoformat() if getattr(edge, "valid_until", None) else None,
                        "is_current": bool(edge.is_current),
                    })
                
                return {
                    "edges": edges_list,
                    "total": len(edges_list),
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            self.logger.error(f"Failed to get KG edges: {e}", exc_info=True)
            return {
                "edges": [],
                "total": 0,
                "limit": request_data.get("limit", 1000),
                "offset": request_data.get("offset", 0)
            }

    async def handle_kg_schema_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG schema request from gateway"""
        try:
            user_id = request_data.get("user_id")

            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow_instance:
                nodes = await uow_instance.kg_nodes.list(filters={"user_id": user_id, "is_current": True}, limit=10000)
                edges = await uow_instance.kg_edges.list(filters={"user_id": user_id, "is_current": True}, limit=10000)

                node_labels = sorted(list(set(node.label for node in nodes if getattr(node, "label", None))))
                relationship_types = sorted(list(set(edge.relation_type for edge in edges if getattr(edge, "relation_type", None))))

                node_properties = [
                    "id", "label", "confidence", "source_text",
                    "created_at", "updated_at", "valid_from", "valid_until",
                    "is_current", "canonical_id", "language", "reason",
                ]

                relationship_properties = [
                    "id", "relation_type", "confidence", "source_text",
                    "created_at", "updated_at", "valid_from", "valid_until",
                    "is_current", "reason",
                ]

                return {
                    "nodeLabels": node_labels,
                    "relationshipTypes": relationship_types,
                    "nodeProperties": node_properties,
                    "relationshipProperties": relationship_properties,
                }

        except Exception as e:
            self.logger.error(f"Failed to get KG schema: {e}", exc_info=True)
            return {
                "error": "KG_SCHEMA_FAILED",
                "message": str(e),
            }

    async def handle_kg_changes_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG changes request from gateway"""
        try:
            user_id = request_data.get("user_id")
            from_timestamp = request_data.get("from_timestamp")
            to_timestamp = request_data.get("to_timestamp")
            limit = request_data.get("limit", 1000)

            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow_instance:
                import json
                from datetime import datetime

                def _parse_iso(ts: Any):
                    if ts is None:
                        return None
                    if isinstance(ts, datetime):
                        return ts
                    if isinstance(ts, str):
                        try:
                            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except Exception:
                            return None
                    return None

                from_dt = _parse_iso(from_timestamp)
                to_dt = _parse_iso(to_timestamp)

                def _in_range(value: Any) -> bool:
                    if value is None:
                        return False
                    if isinstance(value, datetime) and from_dt and to_dt:
                        return from_dt <= value <= to_dt
                    # Fallback: compare as strings (best-effort)
                    try:
                        return str(from_timestamp) <= str(value) <= str(to_timestamp)
                    except Exception:
                        return False

                changes: list[dict] = []

                all_nodes = await uow_instance.kg_nodes.list(filters={"user_id": user_id}, limit=100000)
                nodes_changed = [
                    n for n in all_nodes
                    if (_in_range(getattr(n, "created_at", None)) or _in_range(getattr(n, "updated_at", None)))
                ]
                nodes_changed.sort(key=lambda n: n.updated_at or n.created_at or "", reverse=True)
                nodes_changed = nodes_changed[:limit]

                for node in nodes_changed:
                    properties = getattr(node, "properties", None)
                    if properties is None:
                        properties = {}
                    elif isinstance(properties, dict):
                        properties = dict(properties)
                    else:
                        try:
                            properties = json.loads(str(properties))
                            if not isinstance(properties, dict):
                                properties = {}
                        except Exception:
                            properties = {}

                    created_at = getattr(node, "created_at", None)
                    updated_at = getattr(node, "updated_at", None)
                    valid_until = getattr(node, "valid_until", None)

                    if created_at and _in_range(created_at):
                        change_type = "node_created"
                    elif valid_until and _in_range(valid_until):
                        change_type = "node_deleted"
                    else:
                        change_type = "node_updated"

                    timestamp_val = updated_at or created_at
                    timestamp_str = timestamp_val.isoformat() if hasattr(timestamp_val, "isoformat") else str(timestamp_val)

                    changes.append(
                        {
                            "change_type": change_type,
                            "entity_type": "node",
                            "entity_id": node.id,
                            "entity_label": getattr(node, "label", None),
                            "timestamp": timestamp_str,
                            "properties_changed": list(properties.keys()) if change_type == "node_updated" else None,
                            "old_values": None,
                            "new_values": properties if change_type != "node_deleted" else None,
                            "source_text": getattr(node, "source_text", None),
                            "reason": None,
                        }
                    )

                all_edges = await uow_instance.kg_edges.list(filters={"user_id": user_id}, limit=100000)
                edges_changed = [
                    e for e in all_edges
                    if (_in_range(getattr(e, "created_at", None)) or _in_range(getattr(e, "updated_at", None)))
                ]
                edges_changed.sort(key=lambda e: e.updated_at or e.created_at or "", reverse=True)
                edges_changed = edges_changed[:limit]

                for edge in edges_changed:
                    properties = getattr(edge, "properties", None)
                    if properties is None:
                        properties = {}
                    elif isinstance(properties, dict):
                        properties = dict(properties)
                    else:
                        try:
                            properties = json.loads(str(properties))
                            if not isinstance(properties, dict):
                                properties = {}
                        except Exception:
                            properties = {}

                    created_at = getattr(edge, "created_at", None)
                    updated_at = getattr(edge, "updated_at", None)
                    valid_until = getattr(edge, "valid_until", None)

                    if created_at and _in_range(created_at):
                        change_type = "edge_created"
                    elif valid_until and _in_range(valid_until):
                        change_type = "edge_deleted"
                    else:
                        change_type = "edge_updated"

                    timestamp_val = updated_at or created_at
                    timestamp_str = timestamp_val.isoformat() if hasattr(timestamp_val, "isoformat") else str(timestamp_val)

                    changes.append(
                        {
                            "change_type": change_type,
                            "entity_type": "edge",
                            "entity_id": edge.id,
                            "entity_label": getattr(edge, "relation_type", None),
                            "timestamp": timestamp_str,
                            "properties_changed": list(properties.keys()) if change_type == "edge_updated" else None,
                            "old_values": None,
                            "new_values": properties if change_type != "edge_deleted" else None,
                            "source_text": getattr(edge, "source_text", None),
                            "reason": None,
                        }
                    )

                changes.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
                return {
                    "from_timestamp": from_timestamp,
                    "to_timestamp": to_timestamp,
                    "total_changes": len(changes),
                    "changes": changes[:limit],
                }

        except Exception as e:
            self.logger.error(f"Failed to get KG changes: {e}", exc_info=True)
            return {
                "error": "KG_CHANGES_FAILED",
                "message": str(e),
            }

    async def handle_kg_query_templates_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG query templates request from gateway"""
        try:
            from aico.core.paths import AICOPaths
            import json

            data_dir = AICOPaths.get_data_directory() / AICOPaths.get_data_subdirectory_from_config()
            templates_path = data_dir / "gql_query_templates.json"

            if not templates_path.exists():
                return {
                    "error": "KG_QUERY_TEMPLATES_NOT_INITIALIZED",
                    "message": "Query templates not initialized. Run 'aico config init' to set up templates.",
                }

            with open(templates_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return data

        except Exception as e:
            self.logger.error(f"Failed to get KG query templates: {e}", exc_info=True)
            return {
                "error": "KG_QUERY_TEMPLATES_LOAD_FAILED",
                "message": str(e),
            }

    async def handle_kg_query_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG GQL/Cypher query execution request from gateway"""
        try:
            user_id = request_data.get("user_id")
            query = request_data.get("query")
            output_format = request_data.get("format", "dict")
            limit = request_data.get("limit")

            # Create KG storage like backend.api.kg.dependencies.get_kg_storage
            from aico.ai.knowledge_graph import PropertyGraphStorage
            uow_factory = self.container.get_service("uow")
            kg_storage = PropertyGraphStorage(uow_factory)

            from aico.ai.knowledge_graph.query import GQLQueryExecutor
            max_results = limit or 1000
            executor = GQLQueryExecutor(
                kg_storage,
                max_results=max_results,
                timeout_seconds=30,
            )

            result = await executor.execute(query, user_id, format=output_format)
            return result

        except Exception as e:
            self.logger.error(f"Failed to execute KG query: {e}", exc_info=True)
            return {
                "error": "KG_QUERY_EXECUTION_FAILED",
                "message": str(e),
                "success": False,
            }
    
    async def handle_memory_album_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory album request from gateway"""
        try:
            user_uuid = request_data.get("user_uuid")
            category = request_data.get("category")
            favorites_only = request_data.get("favorites_only", False)
            limit = request_data.get("limit", 50)
            offset = request_data.get("offset", 0)
            
            # Get UoW factory from service container
            uow_factory = self.container.get_service("uow")
            
            # Query memory album from database
            uow = uow_factory()
            async with uow as uow_instance:
                from aico.ai.memory.memory_album import MemoryAlbumStore
                
                memory_store = MemoryAlbumStore()
                facts = await memory_store.get_user_curated_facts(
                    user_id=user_uuid,
                    category=category,
                    favorites_only=favorites_only,
                    limit=limit,
                    offset=offset,
                )
                
                # Enrich with user profile data
                enriched_facts = []
                for fact in facts:
                    user_profile = await uow_instance.users.get_by_id(fact['user_id'])
                    
                    fact_with_user = dict(fact)
                    if user_profile:
                        fact_with_user['user_uuid'] = user_profile.uuid
                        fact_with_user['user_full_name'] = user_profile.full_name
                        fact_with_user['user_nickname'] = user_profile.nickname
                    else:
                        fact_with_user['user_uuid'] = fact['user_id']
                        fact_with_user['user_full_name'] = 'Unknown'
                        fact_with_user['user_nickname'] = None
                    
                    enriched_facts.append(fact_with_user)
                
                # Convert to response format
                memories = []
                for fact in enriched_facts:
                    # Parse JSON fields
                    import json
                    tags = json.loads(fact.get('tags_json', '[]')) if fact.get('tags_json') else []
                    key_moments = json.loads(fact.get('key_moments_json', '[]')) if fact.get('key_moments_json') else []
                    
                    # Normalize datetime fields
                    created_at = fact['created_at']
                    if hasattr(created_at, 'isoformat'):
                        created_at = created_at.isoformat()
                    
                    updated_at = fact['updated_at']
                    if hasattr(updated_at, 'isoformat'):
                        updated_at = updated_at.isoformat()
                    
                    last_revisited = fact.get('last_revisited')
                    if last_revisited and hasattr(last_revisited, 'isoformat'):
                        last_revisited = last_revisited.isoformat()
                    
                    memories.append({
                        "fact_id": fact['fact_id'],
                        "content": fact['content'],
                        "content_type": fact.get('content_type', 'message'),
                        "category": fact['category'],
                        "fact_type": fact['fact_type'],
                        "user_note": fact.get('user_note'),
                        "tags": tags,
                        "is_favorite": bool(fact.get('is_favorite', 0)),
                        "emotional_tone": fact.get('emotional_tone'),
                        "memory_type": fact.get('memory_type'),
                        "source_conversation_id": fact['source_conversation_id'],
                        "source_message_id": fact.get('source_message_id'),
                        "revisit_count": fact.get('revisit_count', 0),
                        "last_revisited": last_revisited,
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "user_uuid": fact.get('user_uuid', fact['user_id']),
                        "user_full_name": fact.get('user_full_name', 'Unknown User'),
                        "user_nickname": fact.get('user_nickname'),
                        "conversation_title": fact.get('conversation_title'),
                        "conversation_summary": fact.get('conversation_summary'),
                        "turn_range": fact.get('turn_range'),
                        "key_moments": key_moments,
                    })
                
                return {
                    "memories": memories,
                    "total": len(memories),
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            self.logger.error(f"Failed to get memory album: {e}", exc_info=True)
            return {
                "memories": [],
                "total": 0,
                "limit": request_data.get("limit", 50),
                "offset": request_data.get("offset", 0)
            }
    
    async def handle_operations_databases_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle operations databases request from gateway"""
        try:
            # PostgreSQL metrics (minimal set required by aico-studio DatabaseStorage UI)
            # Note: core runs inside docker-compose network; `AICO_PG_HOST` points at the postgres service.
            import psycopg2

            host = os.environ.get("AICO_PG_HOST", "postgres")
            port = int(os.environ.get("AICO_PG_PORT", "5432"))
            db_name = os.environ.get("AICO_POSTGRES_DATABASE", "aico")
            user = os.environ.get("AICO_POSTGRES_USER", "postgres")

            password = None
            try:
                with open("/run/secrets/pg_password", "r", encoding="utf-8") as f:
                    password = f.read().strip()
            except Exception:
                password = os.environ.get("AICO_PG_PASSWORD")

            db_size = 0
            table_count = 0
            connection_count = 0
            wal_size = 0
            status = "healthy"
            error_details = None

            try:
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=db_name,
                    user=user,
                    password=password,
                    connect_timeout=5,
                )

                with conn.cursor() as cur:
                    # Table count (prefer aico_core schema; fall back to public)
                    try:
                        cur.execute(
                            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'aico_core' AND table_type = 'BASE TABLE'"
                        )
                        table_count = int(cur.fetchone()[0])
                    except Exception:
                        cur.execute(
                            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                        )
                        table_count = int(cur.fetchone()[0])

                    # Active connections
                    cur.execute(
                        "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database()"
                    )
                    connection_count = int(cur.fetchone()[0])

                    # Database size
                    cur.execute("SELECT pg_database_size(current_database())")
                    db_size = int(cur.fetchone()[0])

                    # Approximate WAL size (LSN diff from origin)
                    cur.execute("SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0')")
                    wal_size = int(float(cur.fetchone()[0]))

                conn.close()
            except psycopg2.OperationalError as e:
                status = "critical"
                error_details = str(e)
            except Exception as e:
                status = "degraded"
                error_details = str(e)

            databases = [
                {
                    "name": "PostgreSQL",
                    "type": "postgresql",
                    "size_bytes": db_size,
                    "status": status,
                    "location": f"{host}:{port}/{db_name}",
                    "error_details": error_details,
                    "table_count": table_count,
                    "connection_count": connection_count,
                    "wal_size_bytes": wal_size,
                    "database_name": db_name,
                    "host": host,
                    "port": port,
                }
            ]

            return {"databases": databases}
        except Exception as e:
            # Do NOT fail the UI. Always return a PostgreSQL entry with critical status.
            self.logger.error(f"Failed to get database operations: {e}", exc_info=True)
            host = os.environ.get("AICO_PG_HOST", "postgres")
            port = int(os.environ.get("AICO_PG_PORT", "5432"))
            db_name = os.environ.get("AICO_POSTGRES_DATABASE", "aico")
            return {
                "databases": [
                    {
                        "name": "PostgreSQL",
                        "type": "postgresql",
                        "size_bytes": 0,
                        "status": "critical",
                        "location": f"{host}:{port}/{db_name}",
                        "error_details": str(e),
                        "table_count": 0,
                        "connection_count": 0,
                        "wal_size_bytes": 0,
                        "database_name": db_name,
                        "host": host,
                        "port": port,
                    }
                ]
            }

    async def handle_operations_postgresql_schema_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PostgreSQL schema metadata request from gateway"""
        try:
            import psycopg2

            host = os.environ.get("AICO_PG_HOST", "postgres")
            port = int(os.environ.get("AICO_PG_PORT", "5432"))
            db_name = os.environ.get("AICO_POSTGRES_DATABASE", "aico")
            user = os.environ.get("AICO_POSTGRES_USER", "postgres")

            password = None
            try:
                with open("/run/secrets/pg_password", "r", encoding="utf-8") as f:
                    password = f.read().strip()
            except Exception:
                password = os.environ.get("AICO_PG_PASSWORD")

            conn = psycopg2.connect(
                host=host,
                port=port,
                database=db_name,
                user=user,
                password=password,
                connect_timeout=5,
            )

            tables: list[str] = []
            columns: dict[str, list[str]] = {}

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'aico_core' AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                )
                for (table_name,) in cur.fetchall():
                    tables.append(table_name)
                    try:
                        cur.execute(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_schema = 'aico_core' AND table_name = %s "
                            "ORDER BY ordinal_position",
                            (table_name,),
                        )
                        columns[table_name] = [row[0] for row in cur.fetchall()]
                    except Exception:
                        columns[table_name] = []

            conn.close()
            return {"tables": tables, "columns": columns}
        except Exception as e:
            self.logger.error(f"Failed to get schema metadata: {e}", exc_info=True)
            return {"tables": [], "columns": {}}

    async def handle_operations_postgresql_details_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import psycopg2

            host = os.environ.get("AICO_PG_HOST", "postgres")
            port = int(os.environ.get("AICO_PG_PORT", "5432"))
            db_name = os.environ.get("AICO_POSTGRES_DATABASE", "aico")
            user = os.environ.get("AICO_POSTGRES_USER", "postgres")

            password = None
            try:
                with open("/run/secrets/pg_password", "r", encoding="utf-8") as f:
                    password = f.read().strip()
            except Exception:
                password = os.environ.get("AICO_PG_PASSWORD")

            conn = psycopg2.connect(
                host=host,
                port=port,
                database=db_name,
                user=user,
                password=password,
                connect_timeout=5,
            )

            tables: list[dict[str, Any]] = []

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'aico_core' AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                )
                table_names = [row[0] for row in cur.fetchall()]

                for table_name in table_names:
                    row_count = 0
                    size_bytes = None
                    column_count = 0

                    try:
                        cur.execute(f'SELECT COUNT(*) FROM "aico_core"."{table_name}"')
                        row_count = int(cur.fetchone()[0])
                    except Exception:
                        row_count = 0

                    try:
                        cur.execute(
                            "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'aico_core' AND table_name = %s",
                            (table_name,),
                        )
                        column_count = int(cur.fetchone()[0])
                    except Exception:
                        column_count = 0

                    try:
                        cur.execute("SELECT pg_total_relation_size(%s)", (f"aico_core.{table_name}",))
                        size_bytes = int(cur.fetchone()[0])
                    except Exception:
                        size_bytes = None

                    tables.append(
                        {
                            "name": table_name,
                            "row_count": row_count,
                            "size_bytes": size_bytes,
                            "columns": column_count,
                        }
                    )

            conn.close()
            return {"database_type": "postgresql", "tables": tables}
        except Exception as e:
            self.logger.error(f"Failed to get PostgreSQL details: {e}", exc_info=True)
            return {"database_type": "postgresql", "tables": []}
    
    async def handle_operations_topology_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle operations topology request from gateway"""
        try:
            import time
            import asyncio
            import subprocess
            from datetime import datetime
            from backend.api.operations.router import start_time, format_uptime, get_backend_version, get_modelservice_version
            from backend.services.version_detector import get_version_detector
            
            # Get versions
            backend_version = get_backend_version()
            modelservice_version = get_modelservice_version()
            
            # Get database versions
            version_detector = get_version_detector()
            db_versions = await version_detector.get_all_versions()
            
            # Calculate backend uptime
            backend_uptime_seconds = time.time() - start_time
            backend_uptime_str = format_uptime(backend_uptime_seconds)
            
            # Get modelservice uptime
            modelservice_uptime_str = "N/A"
            try:
                from backend.services import get_modelservice_client
                from aico.core.config import ConfigurationManager
                config = ConfigurationManager()
                modelservice_client = get_modelservice_client(config)
                health_data = await modelservice_client.get_health()
                if health_data and health_data.get('success') and health_data.get('uptime_seconds'):
                    modelservice_uptime_str = format_uptime(health_data['uptime_seconds'])
            except Exception:
                pass
            
            # Get postgres uptime
            postgres_uptime_str = "N/A"
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "inspect", "--format={{.State.StartedAt}}", "aico-postgres"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    started_at = datetime.fromisoformat(result.stdout.strip().replace('Z', '+00:00'))
                    uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
                    postgres_uptime_str = format_uptime(uptime_seconds)
            except Exception:
                pass
            
            # Build services list with all services
            services = [
                {"id": "gateway", "name": "API Gateway", "type": "gateway", "status": "healthy", "version": backend_version, "host": "localhost", "port": 8771, "uptime": backend_uptime_str},
                {"id": "core", "name": "Backend Core", "type": "backend", "status": "healthy", "version": backend_version, "host": "localhost", "uptime": backend_uptime_str},
                {"id": "studio", "name": "Studio", "type": "studio", "status": "healthy", "version": "N/A", "host": "localhost", "port": 3000, "uptime": "N/A"},
                {"id": "modelservice", "name": "Model Service", "type": "modelservice", "status": "healthy", "version": modelservice_version, "host": "localhost", "port": 11434, "uptime": modelservice_uptime_str},
                {"id": "scheduler", "name": "Task Scheduler", "type": "scheduler", "status": "healthy", "version": backend_version, "host": "localhost", "uptime": backend_uptime_str},
                {"id": "nats", "name": "NATS", "type": "bus", "status": "healthy", "version": "2.10", "host": "localhost", "port": 4222, "uptime": "N/A"},
                {"id": "loki", "name": "Loki", "type": "logs", "status": "healthy", "version": "2.9.0", "host": "localhost", "port": 3100, "uptime": "N/A"},
                {"id": "grafana", "name": "Grafana", "type": "dashboard", "status": "healthy", "version": "12.1", "host": "localhost", "port": 3001, "uptime": "N/A"},
                {"id": "postgresql", "name": "PostgreSQL", "type": "database", "status": "healthy", "version": db_versions.get("PostgreSQL", "18.1"), "host": "localhost", "port": 5432, "uptime": postgres_uptime_str},
            ]
            
            # Build connections list with all connections
            connections = [
                {"from_service": "studio", "to_service": "gateway", "protocol": "HTTP/WebSocket", "status": "active"},
                {"from_service": "gateway", "to_service": "nats", "protocol": "NATS", "status": "active"},
                {"from_service": "nats", "to_service": "core", "protocol": "NATS", "status": "active"},
                {"from_service": "core", "to_service": "nats", "protocol": "NATS", "status": "active"},
                {"from_service": "core", "to_service": "postgresql", "protocol": "PostgreSQL", "status": "active"},
                {"from_service": "core", "to_service": "modelservice", "protocol": "ZMQ", "status": "active"},
                {"from_service": "core", "to_service": "loki", "protocol": "HTTP", "status": "active"},
                {"from_service": "grafana", "to_service": "loki", "protocol": "HTTP", "status": "active"},
                {"from_service": "grafana", "to_service": "postgresql", "protocol": "PostgreSQL", "status": "active"},
            ]
            
            return {
                "services": services,
                "connections": connections,
                "deployment_type": "docker-compose"
            }
        except Exception as e:
            self.logger.error(f"Failed to get operations topology: {e}", exc_info=True)
            return {
                "error": "OPERATIONS_TOPOLOGY_FAILED",
                "message": str(e)
            }
    
    async def handle_operations_create_backup_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle backup creation request from gateway"""
        try:
            from backend.api.operations.backup_sets import create_backup_set
            from backend.api.operations.schemas import BackupSetCreateRequest
            
            # Parse request
            backup_request = BackupSetCreateRequest(
                output_path=request_data.get("output_path"),
                include_influx=request_data.get("include_influx", False)
            )
            
            # Create backup
            response = await create_backup_set(backup_request)
            
            # Convert to dict
            return {
                "success": response.success,
                "backup_set": response.backup_set.model_dump() if response.backup_set else None,
                "message": response.message
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}", exc_info=True)
            return {
                "success": False,
                "backup_set": None,
                "message": str(e)
            }
    
    async def handle_operations_backup_sets_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle operations backup sets request from gateway"""
        try:
            import pathlib
            from datetime import datetime, UTC

            root = pathlib.Path("/var/lib/aico/artifacts/backups/backup_sets")
            if not root.exists():
                return {"backup_sets": [], "total_count": 0}

            backup_sets: list[dict[str, Any]] = []

            for entry in root.iterdir():
                if not entry.is_dir():
                    continue
                if entry.name == "archives":
                    continue

                manifest_path = entry / "manifest.json"
                created_at = None
                included = {"postgres": False, "chromadb": False}

                if manifest_path.exists():
                    try:
                        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                        created_at = manifest.get("created_at")
                        inc = manifest.get("included") or {}
                        included = {
                            "postgres": bool(inc.get("postgres")),
                            "chromadb": bool(inc.get("chromadb")),
                        }
                    except Exception:
                        created_at = None

                if not created_at:
                    try:
                        created_at = datetime.fromtimestamp(entry.stat().st_mtime, tz=UTC).isoformat()
                    except Exception:
                        created_at = datetime.now(UTC).isoformat()

                backup_sets.append(
                    {
                        "backup_id": entry.name,
                        "created_at": created_at,
                        "path": str(entry),
                        "included": included,
                    }
                )

            backup_sets.sort(key=lambda b: b.get("created_at") or "", reverse=True)
            return {"backup_sets": backup_sets, "total_count": len(backup_sets)}
        except Exception as e:
            self.logger.error(f"Failed to get backup sets: {e}", exc_info=True)
            return {
                "error": "OPERATIONS_BACKUP_SETS_FAILED",
                "message": str(e)
            }
    
    async def handle_scheduler_expected_runs_today_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scheduler expected runs today request from gateway"""
        try:
            # NOTE: This endpoint used to calculate expected runs from DB-backed task schedules.
            # In the current NATS-only core architecture, the request handler must be robust and
            # never time out the gateway. If DB-backed schedules are temporarily unavailable or
            # not wired here, return a minimal valid payload.
            from datetime import datetime, timedelta, UTC

            now = datetime.now(UTC)
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            return {
                "total_expected_runs": 0,
                "task_run_counts": {},
                "calculated_at": now.isoformat(),
                "period_start": day_start.isoformat(),
                "period_end": day_end.isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate expected runs: {e}", exc_info=True)
            return {
                "error": "SCHEDULER_EXPECTED_RUNS_FAILED",
                "message": str(e)
            }
    
    async def handle_system_metrics_all_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system metrics all request from gateway"""
        try:
            from backend.api.metrics.endpoints.gateway import get_gateway_metrics
            from backend.api.metrics.endpoints.modelservice import get_modelservice_metrics
            from backend.api.metrics.endpoints.memory import get_memory_metrics
            from backend.api.metrics.endpoints.scheduler import get_scheduler_metrics
            from backend.api.metrics.endpoints.messagebus import get_messagebus_metrics
            from backend.api.metrics.endpoints.system import get_system_health_metrics
            from datetime import datetime, UTC
            import asyncio
            
            # Get UoW from service container
            uow = self.container.get_service("uow")
            
            # Mock user dict for memory metrics (admin access already validated at gateway)
            user = {"uuid": "system", "role": "admin"}
            
            # Collect all metrics in parallel
            gateway, modelservice, memory, scheduler, message_bus, system_health = await asyncio.gather(
                get_gateway_metrics(),
                get_modelservice_metrics(),
                get_memory_metrics(user, uow),
                get_scheduler_metrics(),
                get_messagebus_metrics(),
                get_system_health_metrics(),
            )
            
            return {
                "timestamp": datetime.now(UTC).isoformat() + "Z",
                "gateway": gateway.model_dump(),
                "modelservice": modelservice.model_dump(),
                "memory": memory.model_dump(),
                "scheduler": scheduler.model_dump(),
                "message_bus": message_bus.model_dump(),
                "system_health": system_health.model_dump(),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}", exc_info=True)
            return {
                "error": "SYSTEM_METRICS_FAILED",
                "message": str(e)
            }
    
    async def handle_system_overview_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system overview request from gateway"""
        try:
            # Return stub overview data
            return {
                "version": "0.5.2",
                "uptime_seconds": 0,
                "status": "healthy"
            }
        except Exception as e:
            self.logger.error(f"Failed to get system overview: {e}", exc_info=True)
            return {
                "error": "SYSTEM_OVERVIEW_FAILED",
                "message": str(e)
            }
    
    async def handle_system_health_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system health request from gateway"""
        try:
            # Return health data with frontend-expected structure
            return {
                "status": "healthy",
                "uptime_seconds": 0,
                "summary": {
                    "critical_issues": 0,
                    "warnings": 0
                },
                "components": []
            }
        except Exception as e:
            self.logger.error(f"Failed to get system health: {e}", exc_info=True)
            return {
                "error": "SYSTEM_HEALTH_FAILED",
                "message": str(e)
            }
    
    async def handle_system_health_services_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system health services request from gateway"""
        try:
            # Return stub health services data
            return {
                "services": []
            }
        except Exception as e:
            self.logger.error(f"Failed to get health services: {e}", exc_info=True)
            return {
                "error": "HEALTH_SERVICES_FAILED",
                "message": str(e)
            }
    
    def _extract_request_data(self, request_envelope) -> Dict[str, Any]:
        """Extract JSON data from request envelope"""
        try:
            # Check if request has JSON data in attributes
            if hasattr(request_envelope, 'metadata') and hasattr(request_envelope.metadata, 'attributes'):
                json_data = request_envelope.metadata.attributes.get('json_data', '{}')
                return json.loads(json_data)
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to extract request data: {e}")
            return {}
    
    async def setup_handlers(self, message_bus_client):
        """Register all NATS request handlers using native NATS request/reply"""
        
        def make_handler(handler_func, response_type):
            """Create a NATS message handler that processes requests and sends replies"""
            async def handler(msg):
                try:
                    # Parse JSON request directly from bytes
                    request_data = json.loads(msg.data.decode('utf-8')) if msg.data else {}
                    
                    # Process request
                    response_data = await handler_func(request_data)
                    
                    # Send JSON response as plain bytes (simplest approach)
                    response_bytes = json.dumps(response_data).encode('utf-8')
                    
                    # Send reply using NATS built-in reply mechanism
                    await message_bus_client._nats.publish(
                        msg.reply,
                        response_bytes
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error in {response_type} handler: {e}", exc_info=True)
                    try:
                        if getattr(msg, "reply", None):
                            error_payload = {
                                "error": "NATS_HANDLER_ERROR",
                                "message": str(e),
                                "subject": getattr(msg, "subject", None),
                            }
                            await message_bus_client._nats.publish(
                                msg.reply,
                                json.dumps(error_payload).encode("utf-8"),
                            )
                    except Exception:
                        # If we can't reply, at least avoid crashing the subscription callback.
                        pass
            
            return handler
        
        # Register handlers using direct NATS subscriptions (not MessageBusClient.subscribe)
        # because we need access to the raw NATS message for the reply subject
        self.logger.info("Subscribing to scheduler.status...")
        sid1 = await message_bus_client._nats.subscribe(
            "scheduler.status",
            cb=make_handler(self.handle_scheduler_status_request, "scheduler.status.reply")
        )
        self.logger.info(f"✅ Subscribed to scheduler.status (sid={sid1})")
        
        self.logger.info("Subscribing to scheduler.tasks...")
        sid2 = await message_bus_client._nats.subscribe(
            "scheduler.tasks",
            cb=make_handler(self.handle_scheduler_tasks_request, "scheduler.tasks.reply")
        )
        self.logger.info(f"✅ Subscribed to scheduler.tasks (sid={sid2})")
        
        self.logger.info("Subscribing to emotion.current...")
        sid3 = await message_bus_client._nats.subscribe(
            "emotion.current",
            cb=make_handler(self.handle_emotion_current_request, "emotion.current.reply")
        )
        self.logger.info(f"✅ Subscribed to emotion.current (sid={sid3})")
        
        self.logger.info("Subscribing to emotion.history...")
        sid4 = await message_bus_client._nats.subscribe(
            "emotion.history",
            cb=make_handler(self.handle_emotion_history_request, "emotion.history.reply")
        )
        self.logger.info(f"✅ Subscribed to emotion.history (sid={sid4})")
        
        self.logger.info("Subscribing to memory.semantic.stats...")
        sid5 = await message_bus_client._nats.subscribe(
            "memory.semantic.stats",
            cb=make_handler(self.handle_memory_semantic_stats_request, "memory.semantic.stats.reply")
        )
        self.logger.info(f"✅ Subscribed to memory.semantic.stats (sid={sid5})")
        
        self.logger.info("Subscribing to memory.working.stats...")
        sid6 = await message_bus_client._nats.subscribe(
            "memory.working.stats",
            cb=make_handler(self.handle_memory_working_stats_request, "memory.working.stats.reply")
        )
        self.logger.info(f"✅ Subscribed to memory.working.stats (sid={sid6})")
        
        self.logger.info("Subscribing to kg.stats...")
        sid7 = await message_bus_client._nats.subscribe(
            "kg.stats",
            cb=make_handler(self.handle_kg_stats_request, "kg.stats.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.stats (sid={sid7})")
        
        self.logger.info("Subscribing to kg.nodes...")
        sid7a = await message_bus_client._nats.subscribe(
            "kg.nodes",
            cb=make_handler(self.handle_kg_nodes_request, "kg.nodes.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.nodes (sid={sid7a})")
        
        self.logger.info("Subscribing to kg.edges...")
        sid7b = await message_bus_client._nats.subscribe(
            "kg.edges",
            cb=make_handler(self.handle_kg_edges_request, "kg.edges.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.edges (sid={sid7b})")

        self.logger.info("Subscribing to kg.schema...")
        sid7c = await message_bus_client._nats.subscribe(
            "kg.schema",
            cb=make_handler(self.handle_kg_schema_request, "kg.schema.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.schema (sid={sid7c})")

        self.logger.info("Subscribing to kg.changes...")
        sid7d = await message_bus_client._nats.subscribe(
            "kg.changes",
            cb=make_handler(self.handle_kg_changes_request, "kg.changes.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.changes (sid={sid7d})")

        self.logger.info("Subscribing to kg.query-templates...")
        sid7e = await message_bus_client._nats.subscribe(
            "kg.query-templates",
            cb=make_handler(self.handle_kg_query_templates_request, "kg.query-templates.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.query-templates (sid={sid7e})")

        self.logger.info("Subscribing to kg.query...")
        sid7f = await message_bus_client._nats.subscribe(
            "kg.query",
            cb=make_handler(self.handle_kg_query_request, "kg.query.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.query (sid={sid7f})")
        
        self.logger.info("Subscribing to memory.album...")
        sid7g = await message_bus_client._nats.subscribe(
            "memory.album",
            cb=make_handler(self.handle_memory_album_request, "memory.album.reply")
        )
        self.logger.info(f"✅ Subscribed to memory.album (sid={sid7g})")
        
        self.logger.info("Subscribing to operations.databases...")
        sid8 = await message_bus_client._nats.subscribe(
            "operations.databases",
            cb=make_handler(self.handle_operations_databases_request, "operations.databases.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.databases (sid={sid8})")

        self.logger.info("Subscribing to operations.databases.postgresql.schema...")
        sid8b = await message_bus_client._nats.subscribe(
            "operations.databases.postgresql.schema",
            cb=make_handler(
                self.handle_operations_postgresql_schema_request,
                "operations.databases.postgresql.schema.reply",
            )
        )
        self.logger.info(f"✅ Subscribed to operations.databases.postgresql.schema (sid={sid8b})")

        self.logger.info("Subscribing to operations.databases.postgresql.details...")
        sid8c = await message_bus_client._nats.subscribe(
            "operations.databases.postgresql.details",
            cb=make_handler(
                self.handle_operations_postgresql_details_request,
                "operations.databases.postgresql.details.reply",
            )
        )
        self.logger.info(f"✅ Subscribed to operations.databases.postgresql.details (sid={sid8c})")
        
        self.logger.info("Subscribing to operations.topology...")
        sid9 = await message_bus_client._nats.subscribe(
            "operations.topology",
            cb=make_handler(self.handle_operations_topology_request, "operations.topology.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.topology (sid={sid9})")
        
        self.logger.info("Subscribing to operations.backup.create...")
        sid10a = await message_bus_client._nats.subscribe(
            "operations.backup.create",
            cb=make_handler(self.handle_operations_create_backup_request, "operations.backup.create.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.backup.create (sid={sid10a})")
        
        self.logger.info("Subscribing to operations.backup_sets...")
        sid10 = await message_bus_client._nats.subscribe(
            "operations.backup_sets",
            cb=make_handler(self.handle_operations_backup_sets_request, "operations.backup_sets.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.backup_sets (sid={sid10})")
        
        self.logger.info("Subscribing to scheduler.expected_runs_today...")
        sid11 = await message_bus_client._nats.subscribe(
            "scheduler.expected_runs_today",
            cb=make_handler(self.handle_scheduler_expected_runs_today_request, "scheduler.expected_runs_today.reply")
        )
        self.logger.info(f"✅ Subscribed to scheduler.expected_runs_today (sid={sid11})")
        
        self.logger.info("Subscribing to system.metrics.all...")
        sid12 = await message_bus_client._nats.subscribe(
            "system.metrics.all",
            cb=make_handler(self.handle_system_metrics_all_request, "system.metrics.all.reply")
        )
        self.logger.info(f"✅ Subscribed to system.metrics.all (sid={sid12})")
        
        self.logger.info("Subscribing to system.overview...")
        sid13 = await message_bus_client._nats.subscribe(
            "system.overview",
            cb=make_handler(self.handle_system_overview_request, "system.overview.reply")
        )
        self.logger.info(f"✅ Subscribed to system.overview (sid={sid13})")
        
        self.logger.info("Subscribing to system.health...")
        sid14 = await message_bus_client._nats.subscribe(
            "system.health",
            cb=make_handler(self.handle_system_health_request, "system.health.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health (sid={sid14})")
        
        self.logger.info("Subscribing to system.health.services...")
        sid15 = await message_bus_client._nats.subscribe(
            "system.health.services",
            cb=make_handler(self.handle_system_health_services_request, "system.health.services.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.services (sid={sid15})")
        
        self.logger.info("Core NATS request handlers registered (scheduler, emotion, memory, kg, operations, system)")
