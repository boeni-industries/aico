"""
Property Graph Storage

Hybrid storage backend using pgvector (semantic search) and PostgreSQL (relational queries).
Embeddings stored in Postgres for unified data management.
"""

from typing import List, Optional, Dict, Any
import json
import asyncio
from datetime import datetime, timezone, UTC
import time

from aico.core.logging import get_logger

from .models import Node, Edge, PropertyGraph

logger = get_logger("shared.ai.knowledge_graph.storage")


class PropertyGraphStorage:
    """
    Hybrid storage backend for property graphs.
    
    Uses pgvector for semantic search and PostgreSQL for fast filtering/traversal.
    All data stored in Postgres for unified management.
    """
    
    def __init__(
        self,
        uow_factory,  # UnitOfWork factory for PostgreSQL
        modelservice_client: Any = None  # ModelserviceClient for embeddings
    ):
        """
        Initialize storage with UoW factory.
        
        Args:
            uow_factory: Unit of Work factory for PostgreSQL access
            modelservice_client: Modelservice client for embedding generation
        """
        self.uow_factory = uow_factory
        self.modelservice = modelservice_client
    
    async def save_node(self, node: Node) -> None:
        """
        Save node to PostgreSQL with pgvector embedding.
        
        Args:
            node: Node to save
        """
        try:
            # Save to PostgreSQL via UoW
            async with self.uow_factory() as uow:
                await uow.kg_nodes.create(node)
                await uow.commit()
            
            # Generate embedding and save to pgvector
            doc = node.to_document()
            
            # Generate embedding via modelservice
            embedding_result = await self.modelservice.generate_embeddings([doc["document"]])
            embeddings = embedding_result.get("embeddings", [])
            
            if embeddings:
                embedding_str = '[' + ','.join(str(x) for x in embeddings[0]) + ']'
                
                # Save to pgvector table
                async with self.uow_factory() as uow:
                    await uow.session.execute(
                        """
                        INSERT INTO aico_core.kg_node_embeddings (node_id, embedding, document)
                        VALUES (:node_id, :embedding::vector, :document)
                        ON CONFLICT (node_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            document = EXCLUDED.document,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        {
                            'node_id': node.id,
                            'embedding': embedding_str,
                            'document': doc["document"]
                        }
                    )
                    await uow.commit()
            
            logger.debug(f"Saved node {node.id} (label={node.label})")
            
        except Exception as e:
            logger.error(f"Failed to save node {node.id}: {e}")
            raise
    
    async def save_edge(self, edge: Edge) -> None:
        """
        Save edge to PostgreSQL with pgvector embedding.
        
        Args:
            edge: Edge to save
        """
        try:
            # Save to PostgreSQL via UoW
            async with self.uow_factory() as uow:
                await uow.kg_edges.create(edge)
                await uow.commit()
            
            # Generate embedding and save to pgvector
            doc = edge.to_document()
            embedding_result = await self.modelservice.generate_embeddings([doc["document"]])
            embeddings = embedding_result.get("embeddings", [])
            
            if embeddings:
                embedding_str = '[' + ','.join(str(x) for x in embeddings[0]) + ']'
                
                # Save to pgvector table
                async with self.uow_factory() as uow:
                    await uow.session.execute(
                        """
                        INSERT INTO aico_core.kg_edge_embeddings (edge_id, embedding, document)
                        VALUES (:edge_id, :embedding::vector, :document)
                        ON CONFLICT (edge_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            document = EXCLUDED.document,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        {
                            'edge_id': edge.id,
                            'embedding': embedding_str,
                            'document': doc["document"]
                        }
                    )
                    await uow.commit()
            
            logger.debug(f"Saved edge {edge.id} (type={edge.relation_type})")
            
        except Exception as e:
            logger.error(f"Failed to save edge {edge.id}: {e}")
            raise
    
    async def save_graph(self, graph: PropertyGraph, superseded_node_ids: set = None) -> None:
        """
        Save property graph to PostgreSQL with pgvector embeddings.
        
        Args:
            graph: PropertyGraph to save
            superseded_node_ids: Set of node IDs that should be marked as historical (is_current=False)
        """
        storage_start = time.time()
        
        if superseded_node_ids is None:
            superseded_node_ids = set()
        
        # Mark superseded nodes as historical (if any from resolution)
        if superseded_node_ids:
            async with self.uow_factory() as uow:
                for node_id in superseded_node_ids:
                    # Mark node as historical
                    await uow.kg_nodes.mark_as_superseded(node_id, None)
                    
                    # Mark edges pointing to/from this node as historical to prevent orphans
                    # Get all edges for this node
                    edges = await uow.kg_edges.list(filters={'source_id': node_id, 'is_current': True})
                    for edge in edges:
                        edge.is_current = False
                        edge.updated_at = datetime.now(UTC)
                        await uow.kg_edges.update(edge)
                    
                    edges = await uow.kg_edges.list(filters={'target_id': node_id, 'is_current': True})
                    for edge in edges:
                        edge.is_current = False
                        edge.updated_at = datetime.now(UTC)
                        await uow.kg_edges.update(edge)
                
                await uow.commit()
        
        # Cleanup handled by PostgreSQL CASCADE on kg_nodes/kg_edges foreign keys
        
        # Save nodes and edges to PostgreSQL
        postgres_start = time.time()
        
        node_id_mapping = {}  # attempted_id -> actual_id for deduplication
        
        async with self.uow_factory() as uow:
            # Save nodes with deduplication handling
            for node in graph.nodes:
                try:
                    # Use a savepoint so a single failed insert doesn't abort the
                    # entire transaction (which would break the deduplication query
                    # below with InFailedSQLTransactionError).
                    async with uow._session.begin_nested():
                        await uow.kg_nodes.create(node)
                    node_id_mapping[node.id] = node.id
                except Exception as e:
                    # Check if node already exists (deduplication)
                    existing_nodes = await uow.kg_nodes.list(
                        filters={
                            'user_id': node.user_id,
                            'label': node.label,
                            'is_current': True
                        },
                        limit=100
                    )
                    
                    # Find exact match by properties
                    existing_node = None
                    for candidate in existing_nodes:
                        if candidate.properties == node.properties:
                            existing_node = candidate
                            break
                    
                    if existing_node:
                        node_id_mapping[node.id] = existing_node.id
                        logger.info(f"[NODE_DEDUP] Node already exists: label={node.label}, existing_id={existing_node.id}, attempted_id={node.id}")
                        
                        # Update confidence if new one is higher
                        if node.confidence > existing_node.confidence:
                            existing_node.confidence = node.confidence
                            existing_node.updated_at = node.updated_at
                            await uow.kg_nodes.update(existing_node)
                            print(f"  💾 [STORAGE] 🔄 Updated node confidence: {node.label} ({existing_node.id})")
                        else:
                            print(f"  💾 [STORAGE] ✅ Node exists with higher confidence: {node.label} ({existing_node.id})")
                    else:
                        # Different error - re-raise
                        logger.error(f"Failed to save node {node.id}: {e}")
                        raise
            
            # Save edges with node ID remapping and deduplication
            for edge in graph.edges:
                # Update edge node references if nodes were deduplicated
                actual_source_id = node_id_mapping.get(edge.source_id, edge.source_id)
                actual_target_id = node_id_mapping.get(edge.target_id, edge.target_id)
                
                if actual_source_id != edge.source_id or actual_target_id != edge.target_id:
                    print(f"  💾 [STORAGE] 🔄 Remapping edge references: source {edge.source_id[:8]}→{actual_source_id[:8]}, target {edge.target_id[:8]}→{actual_target_id[:8]}")
                    edge.source_id = actual_source_id
                    edge.target_id = actual_target_id
                
                # Check if duplicate edge already exists
                existing_edges = await uow.kg_edges.list(
                    filters={
                        'source_id': actual_source_id,
                        'target_id': actual_target_id,
                        'is_current': True
                    },
                    limit=10
                )
                
                # Find exact match by relation_type
                existing_edge = None
                for candidate in existing_edges:
                    if candidate.relation_type == edge.relation_type:
                        existing_edge = candidate
                        break
                
                if existing_edge:
                    # Update confidence if new one is higher
                    if edge.confidence > existing_edge.confidence:
                        existing_edge.confidence = edge.confidence
                        existing_edge.updated_at = edge.updated_at
                        await uow.kg_edges.update(existing_edge)
                        print(f"  💾 [STORAGE] 🔄 Updated edge confidence: {edge.relation_type} ({existing_edge.id})")
                    else:
                        print(f"  💾 [STORAGE] ✅ Edge exists: {edge.relation_type} ({existing_edge.id})")
                else:
                    # New edge - insert
                    try:
                        async with uow._session.begin_nested():
                            await uow.kg_edges.create(edge)
                    except Exception as e:
                        logger.error(f"Failed to save edge {edge.id}: {e}")
                        raise
            
            await uow.commit()
        
        postgres_time = time.time() - postgres_start
        
        # Final summary
        total_storage_time = time.time() - storage_start
        print(f"\n  💾 [STORAGE] ✅ STORAGE COMPLETE in {total_storage_time:.2f}s")
        print(f"  💾 [STORAGE]    Saved: {len(graph.nodes)} nodes, {len(graph.edges)} edges to PostgreSQL + pgvector")
    
    async def get_node(self, node_id: str) -> Optional[Node]:
        """
        Get node by ID from PostgreSQL.
        
        Args:
            node_id: Node ID
            
        Returns:
            Node if found, None otherwise
        """
        async with self.uow_factory() as uow:
            return await uow.kg_nodes.get_by_id(node_id)
    
    async def get_user_nodes(
        self,
        user_id: str,
        label: Optional[str] = None,
        current_only: bool = True
    ) -> List[Node]:
        """
        Get all nodes for a user, optionally filtered by label.
        
        Args:
            user_id: User ID
            label: Optional label filter (PERSON, EVENT, etc.)
            current_only: Only return current facts (is_current=True)
            
        Returns:
            List of nodes
        """
        filters = {'user_id': user_id}
        if label:
            filters['label'] = label
        if current_only:
            filters['is_current'] = True
        
        async with self.uow_factory() as uow:
            return await uow.kg_nodes.list(filters=filters, limit=10000)
    
    async def search_nodes(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        label: Optional[str] = None
    ) -> List[Node]:
        """
        Semantic search for nodes using PostgreSQL + pgvector.
        
        Args:
            query: Search query
            user_id: User ID
            top_k: Number of results to return
            label: Optional label filter
            
        Returns:
            List of nodes ranked by semantic similarity
        """
        # Generate query embedding via modelservice
        if not self.modelservice:
            # Fallback: return all nodes if no modelservice available
            return await self.get_user_nodes(user_id, label=label, current_only=True)
        
        embedding_result = await self.modelservice.generate_embeddings([query])
        query_embedding = embedding_result.get("embeddings", [[]])[0]
        
        if not query_embedding:
            return []
        
        # Search pgvector with cosine similarity
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
        
        # Build WHERE clause
        where_parts = ["n.user_id = :user_id", "n.is_current = TRUE"]
        params = {'user_id': user_id, 'embedding': embedding_str, 'limit': top_k}
        
        if label:
            where_parts.append("n.label = :label")
            params['label'] = label
        
        where_clause = " AND ".join(where_parts)
        
        async with self.uow_factory() as uow:
            result = await uow.session.execute(
                f"""
                SELECT n.id, n.user_id, n.label, n.properties, n.confidence, n.source_text,
                       n.created_at, n.updated_at, n.language, n.valid_from, n.valid_until,
                       n.is_current, n.canonical_id, n.aliases_json, n.reason,
                       1 - (e.embedding <=> :embedding::vector) as similarity
                FROM aico_core.kg_nodes n
                JOIN aico_core.kg_node_embeddings e ON n.id = e.node_id
                WHERE {where_clause}
                ORDER BY e.embedding <=> :embedding::vector
                LIMIT :limit
                """,
                params
            )
            rows = result.fetchall()
        
        # Convert rows to Node objects
        nodes = []
        for row in rows:
            import json
            node = Node(
                id=row[0],
                user_id=row[1],
                label=row[2],
                properties=json.loads(row[3]) if row[3] else {},
                confidence=row[4],
                source_text=row[5],
                created_at=row[6],
                updated_at=row[7],
                language=row[8],
                valid_from=row[9],
                valid_until=row[10],
                is_current=row[11],
                canonical_id=row[12],
                aliases_json=row[13],
                reason=row[14]
            )
            nodes.append(node)
        
        return nodes
    
    async def get_edges_for_node(
        self,
        node_id: str,
        direction: str = "both"  # "outgoing", "incoming", "both"
    ) -> List[Edge]:
        """
        Get all edges connected to a node.
        
        Args:
            node_id: Node ID
            direction: Edge direction filter
            
        Returns:
            List of edges
        """
        async with self.uow_factory() as uow:
            if direction == "outgoing":
                return await uow.kg_edges.list(filters={'source_id': node_id, 'is_current': True}, limit=10000)
            elif direction == "incoming":
                return await uow.kg_edges.list(filters={'target_id': node_id, 'is_current': True}, limit=10000)
            else:  # both
                outgoing = await uow.kg_edges.list(filters={'source_id': node_id, 'is_current': True}, limit=10000)
                incoming = await uow.kg_edges.list(filters={'target_id': node_id, 'is_current': True}, limit=10000)
                # Combine and deduplicate
                edge_dict = {edge.id: edge for edge in outgoing}
                for edge in incoming:
                    edge_dict[edge.id] = edge
                return list(edge_dict.values())
    
    async def get_user_graph(
        self,
        user_id: str,
        current_only: bool = True
    ) -> PropertyGraph:
        """
        Get entire graph for a user.
        
        Args:
            user_id: User ID
            current_only: Only return current facts
            
        Returns:
            PropertyGraph containing all user's nodes and edges
        """
        nodes = await self.get_user_nodes(user_id, current_only=current_only)
        
        filters = {'user_id': user_id}
        if current_only:
            filters['is_current'] = True
        
        async with self.uow_factory() as uow:
            edges = await uow.kg_edges.list(filters=filters, limit=100000)
        
        return PropertyGraph(nodes=nodes, edges=edges)
