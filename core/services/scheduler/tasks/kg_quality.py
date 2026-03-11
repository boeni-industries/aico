"""
KG Quality Validation Module

Provides quality validation and enhancement for knowledge graphs:
- Temporal update detection (property changes)
- Relationship gap detection (co-occurring entities)
- Quality metrics calculation

Used by kg_consolidation.py scheduler task.
"""

import asyncio
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict

from aico.core.logging import get_logger
from aico.ai.knowledge_graph.models import Node, Edge, PropertyGraph

logger = get_logger("backend.scheduler.tasks.kg_quality")


def _coerce_utc_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
            return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
        except Exception:
            return None
    return None


class KGQualityValidator:
    """
    Knowledge Graph quality validation and enhancement.
    
    Stateless design - uses timestamps instead of DB flags.
    """
    
    def __init__(self, memory_manager, modelservice_client):
        """
        Initialize quality validator.
        
        Args:
            memory_manager: Memory manager instance
            modelservice_client: Modelservice client for LLM calls
        """
        self.memory_manager = memory_manager
        self.modelservice = modelservice_client
        self.llm_timeout = 30.0
    
    async def validate_and_enhance(
        self,
        user_id: str,
        batch_window_minutes: int = 30,
        cleanup_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Run quality validation and enhancement on recent nodes.
        
        Uses time-based window to identify recently processed nodes
        (no DB state tracking needed).
        
        Args:
            user_id: User ID
            batch_window_minutes: Time window for recent nodes (default: 30 min)
            cleanup_existing: Whether to run smart cleanup on existing DB entries
            
        Returns:
            Dict with quality metrics and actions taken
        """
        start_time = time.time()
        
        print(f"\n🔍 [KG_QUALITY] Starting quality validation for user {user_id}")
        logger.info(f"Starting quality validation for user {user_id}")
        
        # Get all nodes for comprehensive analysis
        all_nodes = await self.memory_manager._kg_storage.get_user_nodes(user_id, current_only=True)
        
        # Get recent nodes (created in last N minutes)
        recent_cutoff_dt = datetime.now(UTC) - timedelta(minutes=batch_window_minutes)
        recent_nodes = []
        for n in all_nodes:
            created_at_dt = _coerce_utc_datetime(getattr(n, "created_at", None))
            if created_at_dt and created_at_dt >= recent_cutoff_dt:
                recent_nodes.append(n)
        
        print(f"🔍 [KG_QUALITY] Found {len(recent_nodes)} recent nodes (last {batch_window_minutes} min)")
        print(f"🔍 [KG_QUALITY] Total nodes: {len(all_nodes)}")
        
        # 1. Temporal update detection (property changes)
        temporal_stats = await self._detect_temporal_updates(user_id, recent_nodes, all_nodes)
        
        # 2. Relationship gap detection (recent nodes)
        relationship_stats = await self._detect_relationship_gaps(user_id, recent_nodes)
        
        # 3. Smart cleanup of existing DB entries (if enabled and nodes exist)
        cleanup_stats = {'fixed': 0}
        if cleanup_existing and len(all_nodes) > 0:
            cleanup_stats = await self._smart_cleanup_existing(user_id, all_nodes)
        
        # 4. Calculate quality metrics
        quality_metrics = await self._calculate_quality_metrics(user_id, all_nodes)
        
        total_time = time.time() - start_time
        
        print(f"🔍 [KG_QUALITY] ✅ Quality validation complete in {total_time:.2f}s")
        print(f"🔍 [KG_QUALITY]    Temporal updates: {temporal_stats['superseded']}")
        print(f"🔍 [KG_QUALITY]    Relationships added: {relationship_stats['added']}")
        print(f"🔍 [KG_QUALITY]    Cleanup fixes: {cleanup_stats['fixed']}")
        print(f"🔍 [KG_QUALITY]    Quality score: {quality_metrics['overall_score']:.1f}%")
        
        return {
            'recent_nodes': len(recent_nodes),
            'total_nodes': len(all_nodes),
            'temporal_updates': temporal_stats['superseded'],
            'relationships_added': relationship_stats['added'],
            'cleanup_fixes': cleanup_stats['fixed'],
            'quality_score': quality_metrics['overall_score'],
            'metrics': quality_metrics,
            'processing_time': total_time
        }
    
    async def _detect_temporal_updates(
        self,
        user_id: str,
        recent_nodes: List[Node],
        all_nodes: List[Node]
    ) -> Dict[str, int]:
        """
        Detect property changes and supersede old versions.
        
        Lightweight fusion - checks if same entity has different properties.
        
        Args:
            user_id: User ID
            recent_nodes: Recently created nodes
            all_nodes: All current nodes for user
            
        Returns:
            Dict with statistics
        """
        print(f"\n🔍 [TEMPORAL] Checking {len(recent_nodes)} recent nodes for property updates...")
        
        superseded_count = 0
        
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            for new_node in recent_nodes:
                # Find older nodes with same entity name and type
                for existing_node in all_nodes:
                    if (new_node.id == existing_node.id or
                        new_node.label != existing_node.label or
                        new_node.properties.get('name') != existing_node.properties.get('name')):
                        continue
                    
                    # Same entity (name + type), check if newer
                    new_created_at = _coerce_utc_datetime(getattr(new_node, "created_at", None))
                    existing_created_at = _coerce_utc_datetime(getattr(existing_node, "created_at", None))
                    if not new_created_at or not existing_created_at:
                        continue
                    if new_created_at <= existing_created_at:
                        continue
                    
                    # Check if properties changed (excluding metadata)
                    new_props = {k: v for k, v in new_node.properties.items() 
                                if k not in ['created_at', 'updated_at', 'kg_consolidated']}
                    old_props = {k: v for k, v in existing_node.properties.items() 
                                if k not in ['created_at', 'updated_at', 'kg_consolidated']}
                    
                    if new_props != old_props:
                        # Property change detected - supersede old version
                        print(f"🔍 [TEMPORAL] Property change: {existing_node.label}:{existing_node.properties.get('name')}")
                        print(f"              Old: {old_props}")
                        print(f"              New: {new_props}")
                        
                        # Mark old node as historical
                        existing_node.is_current = False
                        existing_node.valid_until = datetime.now(UTC).isoformat()
                        existing_node.updated_at = datetime.now(UTC).isoformat()
                        await uow.kg_nodes.update(existing_node)
                        
                        superseded_count += 1
                        break
            
            if superseded_count > 0:
                await uow.commit()
                print(f"🔍 [TEMPORAL] ✅ Superseded {superseded_count} nodes with property changes")
        
        return {'superseded': superseded_count}
    
    async def _detect_relationship_gaps(
        self,
        user_id: str,
        recent_nodes: List[Node]
    ) -> Dict[str, int]:
        """
        Detect missing relationships between co-occurring entities.
        
        Entities from the same source text should likely have relationships.
        
        Args:
            user_id: User ID
            recent_nodes: Recently created nodes
            
        Returns:
            Dict with statistics
        """
        print(f"\n🔍 [RELATIONSHIPS] Analyzing {len(recent_nodes)} nodes for missing relationships...")
        
        # Group nodes by source text
        source_groups = defaultdict(list)
        for node in recent_nodes:
            if node.source_text:
                source_groups[node.source_text].append(node)
        
        # Filter to groups with 2+ entities (potential relationships)
        candidate_groups = {src: nodes for src, nodes in source_groups.items() if len(nodes) >= 2}
        
        print(f"🔍 [RELATIONSHIPS] Found {len(candidate_groups)} source texts with multiple entities")
        
        if not candidate_groups:
            return {'added': 0}
        
        # Get existing edges for these nodes
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            recent_node_ids = {n.id for n in recent_nodes}
            existing_edges = await uow.kg_edges.list(
                filters={'user_id': user_id, 'is_current': True},
                limit=100000
            )
            
            # Build set of existing relationships
            existing_pairs = set()
            for edge in existing_edges:
                if edge.source_id in recent_node_ids or edge.target_id in recent_node_ids:
                    existing_pairs.add((edge.source_id, edge.target_id))
                    existing_pairs.add((edge.target_id, edge.source_id))  # Bidirectional
        
        # Infer missing relationships
        relationships_added = 0
        
        for source_text, nodes in candidate_groups.items():
            # Check all pairs for missing edges
            for i, node1 in enumerate(nodes):
                for node2 in nodes[i+1:]:
                    # Skip if relationship already exists
                    if (node1.id, node2.id) in existing_pairs:
                        continue
                    
                    # Infer relationship using LLM
                    inferred_edges = await self._infer_relationship(
                        node1, node2, source_text, user_id
                    )
                    
                    if inferred_edges:
                        async with UnitOfWork(session_factory) as uow:
                            for edge in inferred_edges:
                                await uow.kg_edges.create(edge)
                            await uow.commit()
                        
                        relationships_added += len(inferred_edges)
                        existing_pairs.add((node1.id, node2.id))
                        existing_pairs.add((node2.id, node1.id))
        
        if relationships_added > 0:
            print(f"🔍 [RELATIONSHIPS] ✅ Added {relationships_added} inferred relationships")
        
        return {'added': relationships_added}
    
    async def _infer_relationship(
        self,
        node1: Node,
        node2: Node,
        source_text: str,
        user_id: str
    ) -> List[Edge]:
        """
        Infer relationship between two entities using LLM.
        
        Args:
            node1: First entity
            node2: Second entity
            source_text: Original text containing both entities
            user_id: User ID
            
        Returns:
            List of inferred edges (may be empty)
        """
        try:
            prompt = f"""Given the following text and two entities, determine if there is a meaningful relationship between them.

Text: "{source_text}"

Entity 1: {node1.label} - {node1.properties.get('name')}
Entity 2: {node2.label} - {node2.properties.get('name')}

RELATIONSHIP TYPES:
World Knowledge: WORKS_FOR, WORKS_AT, LIVES_IN, LOCATED_IN, KNOWS, PART_OF, HAPPENED_IN, CREATED_BY, OWNS
Personal Graph: WORKING_ON, HAS_GOAL, CONTRIBUTES_TO, DEPENDS_ON, INTERESTED_IN, PRIORITIZES, COMPLETED, STARTED

If there is a clear relationship, return JSON:
{{"has_relationship": true, "source": "entity_name", "relation_type": "TYPE", "target": "entity_name", "properties": {{}}}}

If no clear relationship exists, return:
{{"has_relationship": false}}

Return valid JSON only."""

            response = await asyncio.wait_for(
                self.modelservice.generate_completion(
                    prompt=prompt,
                    temperature=0.2,
                    max_tokens=256
                ),
                timeout=self.llm_timeout
            )
            
            raw_response = response.get("text", "")
            
            # Parse response
            import json
            from aico.core.json_sanitizer import LLMJsonSanitizer
            sanitizer = LLMJsonSanitizer(strict=False, log_repairs=True)
            result = sanitizer.sanitize(raw_response)
            
            if not result.get('has_relationship', False):
                return []
            
            # Create edge
            source_name = result.get('source')
            target_name = result.get('target')
            
            # Map names to node IDs
            source_id = node1.id if node1.properties.get('name') == source_name else node2.id
            target_id = node2.id if node2.properties.get('name') == target_name else node1.id
            
            if source_id == target_id:
                return []  # Self-referential
            
            edge = Edge.create(
                user_id=user_id,
                source_id=source_id,
                target_id=target_id,
                relation_type=result.get('relation_type', 'RELATED_TO'),
                properties=result.get('properties', {}),
                confidence=0.7,
                source_text=source_text
            )
            
            print(f" [RELATIONSHIPS] Inferred: {node1.properties.get('name')} -> {result.get('relation_type')} -> {node2.properties.get('name')}")
            
            return [edge]
            
        except Exception as e:
            logger.info(f"Rule-based inference generated {len(relationships)} relationships from {len(entities)} entities")
        return relationships
    
    async def _smart_cleanup_existing(
        self,
        user_id: str,
        all_nodes: List[Node]
    ) -> Dict[str, int]:
        """
        Smart cleanup of existing DB entries without duplication.
        
        Applies intelligent fixes:
        1. Normalize entity types (ORG→ORGANIZATION, GPE→LOCATION)
        2. Fix corrupted properties (lists instead of strings)
        3. Remove low-confidence isolated nodes (confidence < 0.3, no edges)
        4. Merge exact duplicates (same label + name)
        
        Args:
            user_id: User ID
            all_nodes: All current nodes
            
        Returns:
            Dict with cleanup statistics
        """
        print(f"\n [CLEANUP] Starting smart cleanup for {len(all_nodes)} nodes...")
        
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        
        session_factory = await get_session_factory()
        fixes_applied = 0
        
        async with UnitOfWork(session_factory) as uow:
            # 1. Normalize entity types (reuse existing normalization logic)
            type_fixes = 0
            for node in all_nodes:
                old_label = node.label
                # Normalize using same logic as extractor
                if old_label in ['ORG', 'ORGANISATION']:
                    node.label = 'ORGANIZATION'
                    type_fixes += 1
                elif old_label in ['GPE', 'LOC', 'PLACE']:
                    node.label = 'LOCATION'
                    type_fixes += 1
                elif old_label == 'MENTION':
                    # MENTION is usually low-quality, convert to ENTITY
                    node.label = 'ENTITY'
                    type_fixes += 1
                
                if old_label != node.label:
                    node.updated_at = datetime.now(UTC).isoformat()
                    await uow.kg_nodes.update(node)
            
            if type_fixes > 0:
                print(f" [CLEANUP] Normalized {type_fixes} entity types")
                fixes_applied += type_fixes
            
            # 2. Fix corrupted properties (name as list instead of string)
            property_fixes = 0
            for node in all_nodes:
                name = node.properties.get('name')
                if isinstance(name, list):
                    # Take first element if list
                    node.properties['name'] = name[0] if name else 'Unknown'
                    node.updated_at = datetime.now(UTC).isoformat()
                    await uow.kg_nodes.update(node)
                    property_fixes += 1
            
            if property_fixes > 0:
                print(f" [CLEANUP] Fixed {property_fixes} corrupted properties")
                fixes_applied += property_fixes
            
            # 3. Remove low-confidence isolated nodes (garbage cleanup)
            # Get all edges to identify isolated nodes
            all_edges = await uow.kg_edges.list(
                filters={'user_id': user_id, 'is_current': True},
                limit=100000
            )
            
            connected_node_ids = set()
            for edge in all_edges:
                connected_node_ids.add(edge.source_id)
                connected_node_ids.add(edge.target_id)
            
            garbage_removed = 0
            for node in all_nodes:
                # Remove if: isolated + low confidence + generic type
                is_isolated = node.id not in connected_node_ids
                is_low_confidence = node.confidence < 0.3
                is_generic = node.label in ['ENTITY', 'MENTION', 'THING']
                
                if is_isolated and is_low_confidence and is_generic:
                    await uow.kg_nodes.delete(node.id)
                    garbage_removed += 1
            
            if garbage_removed > 0:
                print(f" [CLEANUP] Removed {garbage_removed} low-quality isolated nodes")
                fixes_applied += garbage_removed
            
            # 4. Merge exact duplicates (same label + name, case-insensitive)
            # Group by (label, name_lower)
            from collections import defaultdict
            duplicates_map = defaultdict(list)
            for node in all_nodes:
                name = node.properties.get('name', '')
                if isinstance(name, str):
                    key = (node.label, name.lower().strip())
                    duplicates_map[key].append(node)
            
            # Find groups with duplicates
            duplicate_groups = {k: v for k, v in duplicates_map.items() if len(v) > 1}
            
            duplicates_merged = 0
            for (label, name_lower), nodes in duplicate_groups.items():
                # Keep the one with highest confidence
                nodes_sorted = sorted(nodes, key=lambda n: n.confidence, reverse=True)
                canonical = nodes_sorted[0]
                duplicates = nodes_sorted[1:]
                
                print(f" [CLEANUP] Merging {len(duplicates)} duplicates of {label}:{canonical.properties.get('name')}")
                
                # Rewire edges from duplicates to canonical
                for dup in duplicates:
                    # Update edges where duplicate is source
                    dup_edges = await uow.kg_edges.list(
                        filters={'source_id': dup.id, 'is_current': True},
                        limit=10000
                    )
                    for edge in dup_edges:
                        try:
                            edge.source_id = canonical.id
                            edge.updated_at = datetime.now(UTC).isoformat()
                            await uow.kg_edges.update(edge)
                        except Exception:
                            # Duplicate edge, delete it
                            await uow.kg_edges.delete(edge.id)
                    
                    # Update edges where duplicate is target
                    dup_edges = await uow.kg_edges.list(
                        filters={'target_id': dup.id, 'is_current': True},
                        limit=10000
                    )
                    for edge in dup_edges:
                        try:
                            edge.target_id = canonical.id
                            edge.updated_at = datetime.now(UTC).isoformat()
                            await uow.kg_edges.update(edge)
                        except Exception:
                            # Duplicate edge, delete it
                            await uow.kg_edges.delete(edge.id)
                    
                    # Mark duplicate as historical
                    dup.is_current = False
                    dup.valid_until = datetime.now(UTC).isoformat()
                    dup.updated_at = datetime.now(UTC).isoformat()
                    await uow.kg_nodes.update(dup)
                    
                    duplicates_merged += 1
            
            if duplicates_merged > 0:
                print(f" [CLEANUP] Merged {duplicates_merged} exact duplicates")
                fixes_applied += duplicates_merged
            
            await uow.commit()
        
        print(f" [CLEANUP] Smart cleanup complete: {fixes_applied} fixes applied")
        return {'fixed': fixes_applied}
    
    async def _calculate_quality_metrics(
        self,
        user_id: str,
        all_nodes: List[Node]
    ) -> Dict[str, Any]:
        """
        Calculate quality metrics for the knowledge graph.
        
        Args:
            user_id: User ID
            all_nodes: All current nodes
            
        Returns:
            Dict with quality metrics
        """
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            all_edges = await uow.kg_edges.list(
                filters={'user_id': user_id, 'is_current': True},
                limit=100000
            )
        
        total_nodes = len(all_nodes)
        total_edges = len(all_edges)
        
        if total_nodes == 0:
            return {'overall_score': 100.0}
        
        # Calculate metrics
        
        # 1. Connectivity (% of nodes with at least 1 edge)
        connected_nodes = set()
        for edge in all_edges:
            connected_nodes.add(edge.source_id)
            connected_nodes.add(edge.target_id)
        
        connectivity_rate = len(connected_nodes) / total_nodes * 100
        
        # 2. Graph density (actual edges / possible edges)
        max_edges = total_nodes * (total_nodes - 1)
        density = (total_edges / max_edges * 100) if max_edges > 0 else 0
        
        # 3. Average confidence
        avg_confidence = sum(n.confidence for n in all_nodes) / total_nodes * 100
        
        # 4. Type diversity (% of entity types used)
        unique_labels = len(set(n.label for n in all_nodes))
        expected_labels = 15  # Approximate number of useful entity types
        type_diversity = min(unique_labels / expected_labels * 100, 100)
        
        # Overall score (weighted average)
        overall_score = (
            connectivity_rate * 0.4 +  # Most important
            avg_confidence * 0.3 +
            type_diversity * 0.2 +
            min(density * 10, 10) * 0.1  # Density scaled down (too sparse normally)
        )
        
        return {
            'overall_score': overall_score,
            'connectivity_rate': connectivity_rate,
            'graph_density': density,
            'avg_confidence': avg_confidence,
            'type_diversity': type_diversity,
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'connected_nodes': len(connected_nodes),
            'isolated_nodes': total_nodes - len(connected_nodes)
        }
