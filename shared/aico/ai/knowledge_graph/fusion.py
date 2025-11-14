"""
Graph Fusion

Fuses new knowledge graph with existing graph, handling conflicts and discovering novel information.
Based on Graphusion algorithm (ACL 2024).
"""

from typing import List, Dict, Any, Optional, Set
import asyncio
import json
from datetime import datetime, timezone

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager

from .models import Node, Edge, PropertyGraph

logger = get_logger("shared", "ai.knowledge_graph.fusion")


class GraphFusion:
    """
    Graph fusion engine for integrating new knowledge with existing graph.
    
    Handles:
    - Conflict resolution (contradictory facts)
    - Temporal updates (facts that change over time)
    - Novel information discovery
    """
    
    def __init__(
        self,
        modelservice_client: Any,
        config: ConfigurationManager
    ):
        """
        Initialize graph fusion engine.
        
        Args:
            modelservice_client: Client for modelservice API
            config: Configuration manager
        """
        self.modelservice = modelservice_client
        self.config = config
        
        # Get config settings
        kg_config = config.get("core.memory.semantic.knowledge_graph", {})
        self.llm_timeout = kg_config.get("llm_timeout_seconds", 30.0)
        
        logger.info("GraphFusion initialized")
    
    async def fuse(
        self,
        new_graph: PropertyGraph,
        existing_graph: PropertyGraph
    ) -> PropertyGraph:
        """
        Fuse new graph with existing graph.
        
        Args:
            new_graph: Newly extracted and resolved graph
            existing_graph: Existing knowledge graph
            
        Returns:
            Fused graph with conflicts resolved
        """
        if not new_graph.nodes and not new_graph.edges:
            return existing_graph
        
        if not existing_graph.nodes and not existing_graph.edges:
            return new_graph
        
        logger.info(
            f"Fusing graphs: new=({len(new_graph.nodes)} nodes, {len(new_graph.edges)} edges), "
            f"existing=({len(existing_graph.nodes)} nodes, {len(existing_graph.edges)} edges)"
        )
        
        # Start with existing graph
        fused_graph = PropertyGraph()
        fused_graph.nodes = existing_graph.nodes.copy()
        fused_graph.edges = existing_graph.edges.copy()
        
        # Track which nodes/edges were added or updated
        added_nodes = 0
        updated_nodes = 0
        added_edges = 0
        updated_edges = 0
        
        # Fuse nodes
        existing_node_ids = {node.id for node in existing_graph.nodes}
        existing_canonical_ids = {
            node.canonical_id: node for node in existing_graph.nodes
            if node.canonical_id
        }
        
        for new_node in new_graph.nodes:
            # Check if node already exists (by ID or canonical_id)
            existing_node = None
            
            if new_node.id in existing_node_ids:
                existing_node = existing_graph.get_node_by_id(new_node.id)
            elif new_node.canonical_id and new_node.canonical_id in existing_canonical_ids:
                existing_node = existing_canonical_ids[new_node.canonical_id]
            
            if existing_node:
                # Node exists - check for conflicts and update
                updated_node = await self._fuse_node(new_node, existing_node)
                
                # Replace in fused graph
                fused_graph.nodes = [
                    updated_node if n.id == existing_node.id else n
                    for n in fused_graph.nodes
                ]
                updated_nodes += 1
            else:
                # New node - add to graph
                fused_graph.add_node(new_node)
                added_nodes += 1
        
        # Fuse edges
        existing_edge_signatures = {
            self._edge_signature(edge): edge
            for edge in existing_graph.edges
        }
        
        for new_edge in new_graph.edges:
            sig = self._edge_signature(new_edge)
            
            if sig in existing_edge_signatures:
                # Edge exists - check for conflicts and update
                existing_edge = existing_edge_signatures[sig]
                updated_edge = await self._fuse_edge(new_edge, existing_edge)
                
                # Replace in fused graph
                fused_graph.edges = [
                    updated_edge if e.id == existing_edge.id else e
                    for e in fused_graph.edges
                ]
                updated_edges += 1
            else:
                # New edge - add to graph
                fused_graph.add_edge(new_edge)
                added_edges += 1
        
        logger.info(
            f"Fusion complete: added {added_nodes} nodes, updated {updated_nodes} nodes, "
            f"added {added_edges} edges, updated {updated_edges} edges"
        )
        
        return fused_graph
    
    async def _fuse_node(
        self,
        new_node: Node,
        existing_node: Node
    ) -> Node:
        """
        Fuse two nodes, resolving conflicts.
        
        Args:
            new_node: Newly extracted node
            existing_node: Existing node
            
        Returns:
            Fused node
        """
        # Check for property conflicts
        conflicts = self._find_property_conflicts(
            new_node.properties,
            existing_node.properties
        )
        
        if not conflicts:
            # No conflicts - merge properties
            merged_properties = {**existing_node.properties, **new_node.properties}
            
            # Update node
            existing_node.properties = merged_properties
            existing_node.updated_at = datetime.now(timezone.utc).isoformat()
            existing_node.confidence = max(existing_node.confidence, new_node.confidence)
            
            return existing_node
        
        # Conflicts detected - use LLM for resolution
        logger.debug(f"Conflicts detected in node {existing_node.id}: {conflicts}")
        
        resolved_properties = await self._resolve_conflicts_llm(
            new_node,
            existing_node,
            conflicts
        )
        
        # Check if this is a temporal update (fact changed over time)
        is_temporal_update = await self._is_temporal_update(
            new_node,
            existing_node,
            conflicts
        )
        
        if is_temporal_update:
            # Mark existing node as historical
            existing_node.is_current = 0
            existing_node.valid_until = datetime.now(timezone.utc).isoformat()
            
            # Create new node with updated properties
            updated_node = Node.create(
                user_id=new_node.user_id,
                label=new_node.label,
                properties=resolved_properties,
                confidence=new_node.confidence,
                source_text=new_node.source_text,
                canonical_id=existing_node.canonical_id or existing_node.id,
                aliases=existing_node.aliases
            )
            
            logger.info(f"Temporal update: {existing_node.id} -> {updated_node.id}")
            
            return updated_node
        else:
            # Not temporal - just update properties
            existing_node.properties = resolved_properties
            existing_node.updated_at = datetime.now(timezone.utc).isoformat()
            existing_node.confidence = max(existing_node.confidence, new_node.confidence)
            
            return existing_node
    
    async def _fuse_edge(
        self,
        new_edge: Edge,
        existing_edge: Edge
    ) -> Edge:
        """
        Fuse two edges, resolving conflicts.
        
        Args:
            new_edge: Newly extracted edge
            existing_edge: Existing edge
            
        Returns:
            Fused edge
        """
        # Check for property conflicts
        conflicts = self._find_property_conflicts(
            new_edge.properties,
            existing_edge.properties
        )
        
        if not conflicts:
            # No conflicts - merge properties
            merged_properties = {**existing_edge.properties, **new_edge.properties}
            
            existing_edge.properties = merged_properties
            existing_edge.updated_at = datetime.now(timezone.utc).isoformat()
            existing_edge.confidence = max(existing_edge.confidence, new_edge.confidence)
            
            return existing_edge
        
        # Conflicts detected - resolve
        resolved_properties = await self._resolve_conflicts_llm(
            new_edge,
            existing_edge,
            conflicts
        )
        
        # Check if temporal update
        is_temporal_update = await self._is_temporal_update(
            new_edge,
            existing_edge,
            conflicts
        )
        
        if is_temporal_update:
            # Mark existing edge as historical
            existing_edge.is_current = 0
            existing_edge.valid_until = datetime.now(timezone.utc).isoformat()
            
            # Create new edge
            updated_edge = Edge.create(
                user_id=new_edge.user_id,
                source_id=new_edge.source_id,
                target_id=new_edge.target_id,
                relation_type=new_edge.relation_type,
                properties=resolved_properties,
                confidence=new_edge.confidence,
                source_text=new_edge.source_text
            )
            
            return updated_edge
        else:
            existing_edge.properties = resolved_properties
            existing_edge.updated_at = datetime.now(timezone.utc).isoformat()
            existing_edge.confidence = max(existing_edge.confidence, new_edge.confidence)
            
            return existing_edge
    
    def _find_property_conflicts(
        self,
        new_props: Dict[str, Any],
        existing_props: Dict[str, Any]
    ) -> List[str]:
        """
        Find conflicting properties between two property dictionaries.
        
        Args:
            new_props: New properties
            existing_props: Existing properties
            
        Returns:
            List of conflicting property keys
        """
        conflicts = []
        
        for key in new_props:
            if key in existing_props:
                if new_props[key] != existing_props[key]:
                    conflicts.append(key)
        
        return conflicts
    
    async def _resolve_conflicts_llm(
        self,
        new_item: Any,  # Node or Edge
        existing_item: Any,  # Node or Edge
        conflicts: List[str]
    ) -> Dict[str, Any]:
        """
        Use LLM to resolve property conflicts.
        
        Args:
            new_item: New node or edge
            existing_item: Existing node or edge
            conflicts: List of conflicting property keys
            
        Returns:
            Resolved properties dictionary
        """
        try:
            prompt = f"""Resolve conflicts between existing and new information.

Existing properties:
{json.dumps(existing_item.properties, indent=2)}
Source: {existing_item.source_text[:200]}
Created: {existing_item.created_at}

New properties:
{json.dumps(new_item.properties, indent=2)}
Source: {new_item.source_text[:200]}

Conflicting keys: {conflicts}

Determine which values are correct. Consider:
1. Which source is more reliable?
2. Is this a temporal change (fact changed over time)?
3. Is there a way to reconcile both values?

Return JSON with:
- "resolved_properties": the final property dictionary
- "reasoning": explanation of decisions

Return valid JSON only."""
            
            response = await asyncio.wait_for(
                self.modelservice.generate_completion(
                    prompt=prompt,
                    model="eve",
                    temperature=0.2,
                    max_tokens=512
                ),
                timeout=self.llm_timeout
            )
            
            result = self._parse_json_response(response.get("text", ""))
            
            resolved = result.get("resolved_properties", existing_item.properties)
            reasoning = result.get("reasoning", "")
            
            logger.debug(f"Conflict resolution: {reasoning[:100]}")
            
            return resolved
            
        except Exception as e:
            logger.error(f"LLM conflict resolution failed: {e}, keeping existing properties")
            return existing_item.properties
    
    async def _is_temporal_update(
        self,
        new_item: Any,
        existing_item: Any,
        conflicts: List[str]
    ) -> bool:
        """
        Determine if conflicts represent a temporal update (fact changed over time).
        
        Args:
            new_item: New node or edge
            existing_item: Existing node or edge
            conflicts: List of conflicting property keys
            
        Returns:
            True if this is a temporal update
        """
        if not conflicts:
            return False
        
        try:
            prompt = f"""Determine if this represents a temporal change (fact changed over time) or a conflict/error.

Existing: {json.dumps(existing_item.properties, indent=2)}
Created: {existing_item.created_at}

New: {json.dumps(new_item.properties, indent=2)}

Conflicting keys: {conflicts}

Examples of temporal changes:
- "Sarah was my girlfriend" -> "Sarah is my wife" (relationship changed)
- "I live in SF" -> "I live in NYC" (moved)
- "Project status: active" -> "Project status: completed" (status changed)

Return JSON with:
- "is_temporal": true/false
- "reasoning": explanation

Return valid JSON only."""
            
            response = await asyncio.wait_for(
                self.modelservice.generate_completion(
                    prompt=prompt,
                    model="eve",
                    temperature=0.2,
                    max_tokens=256
                ),
                timeout=self.llm_timeout
            )
            
            result = self._parse_json_response(response.get("text", ""))
            
            is_temporal = result.get("is_temporal", False)
            reasoning = result.get("reasoning", "")
            
            logger.debug(f"Temporal check: is_temporal={is_temporal}, reasoning={reasoning[:100]}")
            
            return is_temporal
            
        except Exception as e:
            logger.error(f"Temporal check failed: {e}, assuming not temporal")
            return False
    
    def _edge_signature(self, edge: Edge) -> str:
        """
        Generate signature for edge to detect duplicates.
        
        Args:
            edge: Edge
            
        Returns:
            Signature string
        """
        return f"{edge.source_id}|{edge.relation_type}|{edge.target_id}"
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON response from LLM."""
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return {}
