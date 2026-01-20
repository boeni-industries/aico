"""
Property Graph Storage

Hybrid storage backend using ChromaDB (semantic search) and PostgreSQL (relational queries).
Implements dual-write pattern for consistency.
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
    
    Uses ChromaDB for semantic search and PostgreSQL for fast filtering/traversal.
    All operations are dual-write to maintain consistency.
    """
    
    def __init__(
        self,
        uow_factory,  # UnitOfWork factory for PostgreSQL
        chromadb_client: Any,  # chromadb.Client
        modelservice_client: Any = None  # ModelserviceClient for embeddings
    ):
        """
        Initialize storage with UoW factory and ChromaDB client.
        
        Args:
            uow_factory: Unit of Work factory for PostgreSQL access
            chromadb_client: ChromaDB client for semantic search
            modelservice_client: Modelservice client for embedding generation
        """
        self.uow_factory = uow_factory
        self.chromadb = chromadb_client
        self.modelservice = modelservice_client
        
        # Get or create collections
        # NOTE: We provide embeddings manually (via modelservice) to avoid ChromaDB auto-generation
        # which would block the thread pool. This follows the same pattern as semantic memory.
        self._node_collection = self.chromadb.get_or_create_collection(
            name="kg_nodes",
            metadata={"hnsw:space": "cosine"}
        )
        self._edge_collection = self.chromadb.get_or_create_collection(
            name="kg_edges",
            metadata={"hnsw:space": "cosine"}
        )
    
    async def save_node(self, node: Node) -> None:
        """
        Save node to both ChromaDB and PostgreSQL.
        
        Args:
            node: Node to save
        """
        try:
            # Save to PostgreSQL via UoW
            async with self.uow_factory() as uow:
                await uow.kg_nodes.create(node)
                await uow.commit()
            # Generate embedding and save to ChromaDB
            doc = node.to_chromadb_document()
            
            # Generate embedding via modelservice
            embedding_result = await self.modelservice.generate_embeddings([doc["document"]])
            embeddings = embedding_result.get("embeddings", [])
            
            def _sync_save_to_chroma():
                """Synchronous ChromaDB write - runs in thread pool"""
                self._node_collection.upsert(
                    ids=[doc["id"]],
                    embeddings=[embeddings[0]],
                    documents=[doc["document"]],
                    metadatas=[doc["metadata"]]
                )
            
            await asyncio.to_thread(_sync_save_to_chroma)
            
            logger.debug(f"Saved node {node.id} (label={node.label})")
            
        except Exception as e:
            logger.error(f"Failed to save node {node.id}: {e}")
            raise
    
    async def save_edge(self, edge: Edge) -> None:
        """
        Save edge to both ChromaDB and PostgreSQL.
        
        Args:
            edge: Edge to save
        """
        try:
            # Save to PostgreSQL via UoW
            async with self.uow_factory() as uow:
                await uow.kg_edges.create(edge)
                await uow.commit()
            
            # Generate embedding and save to ChromaDB
            doc = edge.to_chromadb_document()
            embedding_result = await self.modelservice.generate_embeddings([doc["document"]])
            embeddings = embedding_result.get("embeddings", [])
            
            def _sync_save_to_chroma():
                self._edge_collection.upsert(
                    ids=[doc["id"]],
                    embeddings=[embeddings[0]],
                    documents=[doc["document"]],
                    metadatas=[doc["metadata"]]
                )
            await asyncio.to_thread(_sync_save_to_chroma)
            
            logger.debug(f"Saved edge {edge.id} (type={edge.relation_type})")
            
        except Exception as e:
            logger.error(f"Failed to save edge {edge.id}: {e}")
            raise
    
    async def save_graph(self, graph: PropertyGraph, superseded_node_ids: set = None) -> None:
        """
        Save property graph to both PostgreSQL and ChromaDB.
        
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
                        edge.updated_at = datetime.now(UTC).isoformat()
                        await uow.kg_edges.update(edge)
                    
                    edges = await uow.kg_edges.list(filters={'target_id': node_id, 'is_current': True})
                    for edge in edges:
                        edge.is_current = False
                        edge.updated_at = datetime.now(UTC).isoformat()
                        await uow.kg_edges.update(edge)
                
                await uow.commit()
        
        # Clean up ChromaDB embeddings
        async with self.uow_factory() as uow:
            current_nodes = await uow.kg_nodes.list(filters={'is_current': True}, limit=100000)
            current_node_ids = set(node.id for node in current_nodes)
            
            current_edges = await uow.kg_edges.list(filters={'is_current': True}, limit=100000)
            current_edge_ids = set(edge.id for edge in current_edges)
        
        def _sync_cleanup_chromadb():
            # Get all node IDs from ChromaDB
            try:
                chroma_nodes = self._node_collection.get()
                chroma_node_ids = set(chroma_nodes['ids']) if chroma_nodes['ids'] else set()
            except Exception as e:
                logger.warning(f"Failed to get ChromaDB node IDs: {e}")
                chroma_node_ids = set()
            
            orphaned_node_ids = chroma_node_ids - current_node_ids
            
            # Delete orphaned node embeddings
            if orphaned_node_ids:
                try:
                    self._node_collection.delete(ids=list(orphaned_node_ids))
                    logger.info(f"Deleted {len(orphaned_node_ids)} orphaned node embeddings from ChromaDB")
                except Exception as e:
                    logger.warning(f"Failed to delete orphaned node embeddings: {e}")
            
            # Get all edge IDs from ChromaDB
            try:
                chroma_edges = self._edge_collection.get()
                chroma_edge_ids = set(chroma_edges['ids']) if chroma_edges['ids'] else set()
            except Exception as e:
                logger.warning(f"Failed to get ChromaDB edge IDs: {e}")
                chroma_edge_ids = set()
            
            orphaned_edge_ids = chroma_edge_ids - current_edge_ids
            
            # Delete orphaned edge embeddings
            if orphaned_edge_ids:
                try:
                    self._edge_collection.delete(ids=list(orphaned_edge_ids))
                    logger.info(f"Deleted {len(orphaned_edge_ids)} orphaned edge embeddings from ChromaDB")
                except Exception as e:
                    logger.warning(f"Failed to delete orphaned edge embeddings: {e}")
        
        await asyncio.to_thread(_sync_cleanup_chromadb)
        
        # Save nodes and edges to PostgreSQL
        postgres_start = time.time()
        
        node_id_mapping = {}  # attempted_id -> actual_id for deduplication
        
        async with self.uow_factory() as uow:
            # Save nodes with deduplication handling
            for node in graph.nodes:
                try:
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
                        await uow.kg_edges.create(edge)
                    except Exception as e:
                        logger.error(f"Failed to save edge {edge.id}: {e}")
                        raise
            
            await uow.commit()
        
        postgres_time = time.time() - postgres_start
        print(f"  💾 [STORAGE] ✅ PostgreSQL complete in {postgres_time:.2f}s")
        
        # Save to ChromaDB (semantic search) - reuse cached embeddings from resolution
        node_docs = [node.to_chromadb_document() for node in graph.nodes]
        
        # Separate nodes with/without cached embeddings
        nodes_with_embeddings = [(i, node) for i, node in enumerate(graph.nodes) if node.embedding is not None]
        nodes_without_embeddings = [(i, node) for i, node in enumerate(graph.nodes) if node.embedding is None]
        
        # Initialize embeddings list
        embeddings = [None] * len(graph.nodes)
        
        # Use cached embeddings
        for i, node in nodes_with_embeddings:
            embeddings[i] = node.embedding
        
        # Generate embeddings only for nodes without cache (fallback)
        print(f"\n  💾 [STORAGE] Preparing ChromaDB save: {len(nodes_with_embeddings)} cached, {len(nodes_without_embeddings)} need generation")
        embedding_start = time.time()
        
        if nodes_without_embeddings:
            indices_to_generate = [i for i, _ in nodes_without_embeddings]
            texts_to_generate = [node_docs[i]["document"] for i in indices_to_generate]
            
            print(f"  💾 [STORAGE] Generating embeddings for {len(texts_to_generate)} nodes...")
            embedding_result = await self.modelservice.generate_embeddings(texts_to_generate)
            generated_embeddings = embedding_result.get("embeddings", [])
            
            for idx, embedding in zip(indices_to_generate, generated_embeddings):
                embeddings[idx] = embedding
        
        embedding_time = time.time() - embedding_start
        print(f"  💾 [STORAGE] ✅ Embeddings ready in {embedding_time:.2f}s ({len(nodes_with_embeddings)} cached, {len(nodes_without_embeddings)} generated)")
        
        # Only save to ChromaDB if we have nodes (avoid empty embeddings list error)
        if node_docs:
            chroma_nodes_start = time.time()
            def _sync_save_nodes_to_chroma():
                self._node_collection.upsert(
                    ids=[doc["id"] for doc in node_docs],
                    embeddings=embeddings,
                    documents=[doc["document"] for doc in node_docs],
                    metadatas=[doc["metadata"] for doc in node_docs]
                )
            
            await asyncio.to_thread(_sync_save_nodes_to_chroma)
            chroma_nodes_time = time.time() - chroma_nodes_start
            print(f"  💾 [STORAGE] ✅ ChromaDB nodes saved in {chroma_nodes_time:.2f}s")
        else:
            print(f"  💾 [STORAGE] ⏭️  No new nodes to save to ChromaDB (edge-only graph)")
        
        # Save edges to ChromaDB
        if graph.edges:
            print(f"\n  💾 [STORAGE] Processing {len(graph.edges)} edges...")
            edge_start = time.time()
            
            edge_docs = [edge.to_chromadb_document() for edge in graph.edges]
            edge_texts = [doc["document"] for doc in edge_docs]
            
            edge_embedding_start = time.time()
            edge_embedding_result = await self.modelservice.generate_embeddings(edge_texts)
            edge_embeddings = edge_embedding_result.get("embeddings", [])
            edge_embedding_time = time.time() - edge_embedding_start
            print(f"  💾 [STORAGE] ✅ Edge embeddings generated in {edge_embedding_time:.2f}s")
            
            chroma_edges_start = time.time()
            def _sync_save_edges_to_chroma():
                self._edge_collection.upsert(
                    ids=[doc["id"] for doc in edge_docs],
                    embeddings=edge_embeddings,
                    documents=[doc["document"] for doc in edge_docs],
                    metadatas=[doc["metadata"] for doc in edge_docs]
                )
            
            await asyncio.to_thread(_sync_save_edges_to_chroma)
            chroma_edges_time = time.time() - chroma_edges_start
            edge_total_time = time.time() - edge_start
            print(f"  💾 [STORAGE] ✅ ChromaDB edges saved in {chroma_edges_time:.2f}s (total: {edge_total_time:.2f}s)")
        
        # Final summary
        total_storage_time = time.time() - storage_start
        print(f"\n  💾 [STORAGE] ✅ STORAGE COMPLETE in {total_storage_time:.2f}s")
        print(f"  💾 [STORAGE]    PostgreSQL: {postgres_time:.2f}s ({postgres_time/total_storage_time*100:.1f}%)")
        print(f"  💾 [STORAGE]    ChromaDB:   {total_storage_time - postgres_time:.2f}s ({(total_storage_time - postgres_time)/total_storage_time*100:.1f}%)")
        print(f"  💾 [STORAGE]    Saved: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    
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
        Semantic search for nodes using ChromaDB.
        
        Args:
            query: Search query
            user_id: User ID
            top_k: Number of results to return
            label: Optional label filter
            
        Returns:
            List of nodes ranked by semantic similarity
        """
        # Build ChromaDB filter with $and operator
        where_conditions = [
            {"user_id": user_id},
            {"is_current": 1}
        ]
        if label:
            where_conditions.append({"label": label})
        
        where_filter = {"$and": where_conditions} if len(where_conditions) > 1 else where_conditions[0]
        
        # Generate query embedding via modelservice (768-dim)
        if not self.modelservice:
            # Fallback: return all nodes if no modelservice available
            return await self.get_user_nodes(user_id, label=label, current_only=True)
        
        embedding_result = await self.modelservice.generate_embeddings([query])
        query_embedding = embedding_result.get("embeddings", [[]])[0]
        
        if not query_embedding:
            return []
        
        # Search ChromaDB with pre-generated embedding
        results = self._node_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )
        
        if not results["ids"] or not results["ids"][0]:
            return []
        
        node_ids = results["ids"][0]
        nodes = []
        for node_id in node_ids:
            node = await self.get_node(node_id)
            if node:
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
