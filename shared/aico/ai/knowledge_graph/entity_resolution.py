"""
Entity Resolution (Deduplication)

Implements semantic entity resolution using 3-step process:
1. Semantic Blocking: Cluster similar entities using embeddings
2. LLM Matching: Use LLM to determine if entities are duplicates
3. LLM Merging: Merge duplicate entities with conflict resolution
"""

from typing import List, Dict, Any, Tuple, Optional
import asyncio
import json
import numpy as np
from collections import defaultdict

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager

from .models import Node, PropertyGraph

logger = get_logger("shared", "ai.knowledge_graph.entity_resolution")


class EntityResolver:
    """
    Semantic entity resolution for deduplication.
    
    Uses embeddings for blocking and LLM for matching/merging.
    """
    
    def __init__(
        self,
        modelservice_client: Any,
        config: ConfigurationManager
    ):
        """
        Initialize entity resolver.
        
        Args:
            modelservice_client: Client for modelservice API
            config: Configuration manager
        """
        self.modelservice = modelservice_client
        self.config = config
        
        # Get config settings
        kg_config = config.get("core.memory.semantic.knowledge_graph", {})
        er_config = kg_config.get("entity_resolution", {})
        
        self.similarity_threshold = er_config.get("similarity_threshold", 0.85)
        self.use_llm_matching = er_config.get("use_llm_matching", True)
        self.use_llm_merging = er_config.get("use_llm_merging", True)
        self.llm_timeout = kg_config.get("llm_timeout_seconds", 30.0)
        
        logger.info(
            f"EntityResolver initialized (threshold={self.similarity_threshold}, "
            f"llm_matching={self.use_llm_matching}, llm_merging={self.use_llm_merging})"
        )
    
    async def resolve(
        self,
        new_graph: PropertyGraph,
        user_id: str,
        existing_nodes: Optional[List[Node]] = None
    ) -> PropertyGraph:
        """
        Resolve entities in new graph against existing nodes.
        
        Args:
            new_graph: Newly extracted graph
            user_id: User ID
            existing_nodes: Existing nodes to check for duplicates
            
        Returns:
            PropertyGraph with resolved entities (duplicates merged)
        """
        if not new_graph.nodes:
            return new_graph
        
        logger.info(f"Resolving {len(new_graph.nodes)} new entities")
        
        # If no existing nodes provided, only deduplicate within new graph
        if existing_nodes is None:
            existing_nodes = []
        
        # Step 1: Semantic blocking - find candidate duplicates
        candidates = await self._semantic_blocking(new_graph.nodes, existing_nodes)
        
        if not candidates:
            logger.info("No duplicate candidates found")
            return new_graph
        
        logger.info(f"Found {len(candidates)} candidate duplicate pairs")
        
        # Step 2: LLM matching - determine which are actual duplicates
        duplicates = await self._llm_matching(candidates)
        
        if not duplicates:
            logger.info("No confirmed duplicates found")
            return new_graph
        
        logger.info(f"Confirmed {len(duplicates)} duplicate pairs")
        
        # Step 3: LLM merging - merge duplicates with conflict resolution
        resolved_graph = await self._merge_duplicates(new_graph, duplicates)
        
        logger.info(f"Resolution complete: {len(resolved_graph.nodes)} nodes after merging")
        
        return resolved_graph
    
    async def _semantic_blocking(
        self,
        new_nodes: List[Node],
        existing_nodes: List[Node]
    ) -> List[Tuple[Node, Node]]:
        """
        Step 1: Semantic blocking using embeddings.
        
        Find candidate duplicate pairs using cosine similarity.
        
        Args:
            new_nodes: New nodes to check
            existing_nodes: Existing nodes to check against
            
        Returns:
            List of candidate duplicate pairs
        """
        try:
            # Combine all nodes for embedding
            all_nodes = new_nodes + existing_nodes
            
            if not all_nodes:
                return []
            
            # Generate embeddings for all nodes
            texts = [self._node_to_text(node) for node in all_nodes]
            
            response = await self.modelservice.generate_embeddings(texts=texts)
            embeddings = np.array(response.get("embeddings", []))
            
            if len(embeddings) == 0:
                logger.warning("No embeddings generated")
                return []
            
            # Group nodes by label (only compare same types)
            label_groups = defaultdict(list)
            for i, node in enumerate(all_nodes):
                label_groups[node.label].append((i, node))
            
            candidates = []
            
            # Find similar pairs within each label group
            for label, nodes_with_idx in label_groups.items():
                if len(nodes_with_idx) < 2:
                    continue
                
                # Compute pairwise similarities
                for i, (idx1, node1) in enumerate(nodes_with_idx):
                    for idx2, node2 in nodes_with_idx[i+1:]:
                        # Compute cosine similarity
                        sim = self._cosine_similarity(
                            embeddings[idx1],
                            embeddings[idx2]
                        )
                        
                        if sim >= self.similarity_threshold:
                            # Only include pairs where at least one is from new_nodes
                            if node1 in new_nodes or node2 in new_nodes:
                                candidates.append((node1, node2))
                                logger.debug(
                                    f"Candidate pair: {node1.properties.get('name')} <-> "
                                    f"{node2.properties.get('name')} (sim={sim:.3f})"
                                )
            
            return candidates
            
        except Exception as e:
            logger.error(f"Semantic blocking failed: {e}")
            return []
    
    async def _llm_matching(
        self,
        candidates: List[Tuple[Node, Node]]
    ) -> List[Tuple[Node, Node]]:
        """
        Step 2: LLM matching with chain-of-thought reasoning.
        
        Use LLM to determine if candidate pairs are actual duplicates.
        
        Args:
            candidates: Candidate duplicate pairs
            
        Returns:
            List of confirmed duplicate pairs
        """
        if not self.use_llm_matching:
            # If LLM matching disabled, accept all candidates
            return candidates
        
        duplicates = []
        
        # Process candidates in parallel (with concurrency limit)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent LLM calls
        
        async def check_pair(node1: Node, node2: Node) -> Optional[Tuple[Node, Node]]:
            async with semaphore:
                is_duplicate = await self._llm_match_pair(node1, node2)
                if is_duplicate:
                    return (node1, node2)
                return None
        
        tasks = [check_pair(n1, n2) for n1, n2 in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, tuple):
                duplicates.append(result)
            elif isinstance(result, Exception):
                logger.error(f"LLM matching error: {result}")
        
        return duplicates
    
    async def _llm_match_pair(
        self,
        node1: Node,
        node2: Node
    ) -> bool:
        """
        Use LLM to determine if two nodes are duplicates.
        
        Args:
            node1: First node
            node2: Second node
            
        Returns:
            True if nodes are duplicates
        """
        try:
            prompt = f"""Determine if these two entities refer to the same real-world entity.

Entity 1:
- Type: {node1.label}
- Properties: {json.dumps(node1.properties, indent=2)}
- Context: {node1.source_text[:200]}

Entity 2:
- Type: {node2.label}
- Properties: {json.dumps(node2.properties, indent=2)}
- Context: {node2.source_text[:200]}

Think step-by-step:
1. Compare the properties and context
2. Consider if they could refer to the same entity
3. Make a final decision

Return JSON with:
- "is_match": true/false
- "confidence": 0.0-1.0
- "reasoning": your explanation

Return valid JSON only."""
            
            response = await asyncio.wait_for(
                self.modelservice.generate_completion(
                    prompt=prompt,
                    model="eve",  # Use reasoning model
                    temperature=0.2,  # Low temp for consistency
                    max_tokens=512
                ),
                timeout=self.llm_timeout
            )
            
            result = self._parse_json_response(response.get("text", ""))
            
            is_match = result.get("is_match", False)
            confidence = result.get("confidence", 0.0)
            reasoning = result.get("reasoning", "")
            
            logger.debug(
                f"LLM match: {node1.properties.get('name')} <-> {node2.properties.get('name')}: "
                f"is_match={is_match}, confidence={confidence:.2f}, reasoning={reasoning[:100]}"
            )
            
            return is_match and confidence >= 0.7
            
        except asyncio.TimeoutError:
            logger.error(f"LLM matching timed out after {self.llm_timeout}s")
            return False
        except Exception as e:
            logger.error(f"LLM matching failed: {e}")
            return False
    
    async def _merge_duplicates(
        self,
        graph: PropertyGraph,
        duplicates: List[Tuple[Node, Node]]
    ) -> PropertyGraph:
        """
        Step 3: Merge duplicate entities with conflict resolution.
        
        Args:
            graph: Original graph
            duplicates: List of duplicate pairs to merge
            
        Returns:
            PropertyGraph with duplicates merged
        """
        # Build merge groups (transitive closure)
        merge_groups = self._build_merge_groups(duplicates)
        
        # Merge each group
        merged_nodes = {}
        for group in merge_groups:
            merged_node = await self._merge_node_group(group)
            for node in group:
                merged_nodes[node.id] = merged_node
        
        # Build new graph with merged nodes
        new_graph = PropertyGraph()
        
        # Add nodes (merged or original)
        seen_ids = set()
        for node in graph.nodes:
            if node.id in merged_nodes:
                merged = merged_nodes[node.id]
                if merged.id not in seen_ids:
                    new_graph.add_node(merged)
                    seen_ids.add(merged.id)
            else:
                new_graph.add_node(node)
        
        # Update edges to point to merged nodes
        for edge in graph.edges:
            source_id = merged_nodes[edge.source_id].id if edge.source_id in merged_nodes else edge.source_id
            target_id = merged_nodes[edge.target_id].id if edge.target_id in merged_nodes else edge.target_id
            
            # Create new edge with updated IDs
            new_edge = Edge.create(
                user_id=edge.user_id,
                source_id=source_id,
                target_id=target_id,
                relation_type=edge.relation_type,
                properties=edge.properties,
                confidence=edge.confidence,
                source_text=edge.source_text,
                valid_from=edge.valid_from
            )
            new_edge.id = edge.id  # Preserve edge ID
            new_graph.add_edge(new_edge)
        
        return new_graph
    
    async def _merge_node_group(
        self,
        nodes: List[Node]
    ) -> Node:
        """
        Merge a group of duplicate nodes using LLM for conflict resolution.
        
        Args:
            nodes: List of duplicate nodes to merge
            
        Returns:
            Merged node
        """
        if len(nodes) == 1:
            return nodes[0]
        
        if not self.use_llm_merging:
            # If LLM merging disabled, just pick first node
            return nodes[0]
        
        try:
            # Prepare node data for LLM
            node_data = [
                {
                    "id": node.id,
                    "properties": node.properties,
                    "confidence": node.confidence,
                    "created_at": node.created_at
                }
                for node in nodes
            ]
            
            prompt = f"""Merge these duplicate entities into a single entity. Resolve any conflicts by choosing the most accurate/complete information.

Entities to merge:
{json.dumps(node_data, indent=2)}

Return JSON with:
- "merged_properties": the merged property dictionary
- "canonical_id": which entity ID to use as canonical
- "aliases": list of alternative names
- "reasoning": explanation of merge decisions

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
            
            # Create merged node
            base_node = nodes[0]
            merged_node = Node.create(
                user_id=base_node.user_id,
                label=base_node.label,
                properties=result.get("merged_properties", base_node.properties),
                confidence=max(n.confidence for n in nodes),
                source_text=" | ".join(n.source_text[:100] for n in nodes),
                canonical_id=result.get("canonical_id", base_node.id),
                aliases=result.get("aliases", [])
            )
            
            # Use canonical ID
            merged_node.id = result.get("canonical_id", base_node.id)
            
            logger.debug(f"Merged {len(nodes)} nodes into {merged_node.id}")
            
            return merged_node
            
        except Exception as e:
            logger.error(f"LLM merging failed: {e}, using first node")
            return nodes[0]
    
    def _build_merge_groups(
        self,
        duplicates: List[Tuple[Node, Node]]
    ) -> List[List[Node]]:
        """
        Build transitive closure of duplicate pairs.
        
        If A=B and B=C, then merge A, B, C into one group.
        
        Args:
            duplicates: List of duplicate pairs
            
        Returns:
            List of merge groups
        """
        # Build adjacency list
        graph = defaultdict(set)
        all_nodes = {}
        
        for node1, node2 in duplicates:
            graph[node1.id].add(node2.id)
            graph[node2.id].add(node1.id)
            all_nodes[node1.id] = node1
            all_nodes[node2.id] = node2
        
        # Find connected components (merge groups)
        visited = set()
        groups = []
        
        def dfs(node_id: str, group: List[Node]):
            if node_id in visited:
                return
            visited.add(node_id)
            group.append(all_nodes[node_id])
            for neighbor_id in graph[node_id]:
                dfs(neighbor_id, group)
        
        for node_id in all_nodes:
            if node_id not in visited:
                group = []
                dfs(node_id, group)
                if group:
                    groups.append(group)
        
        return groups
    
    def _node_to_text(self, node: Node) -> str:
        """Convert node to text for embedding."""
        props_text = " ".join(f"{k}:{v}" for k, v in node.properties.items())
        return f"{node.label} {props_text}"
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
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
