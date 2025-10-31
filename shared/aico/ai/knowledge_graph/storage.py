"""
Property Graph Storage

Hybrid storage backend using ChromaDB (semantic search) and libSQL (relational queries).
Implements dual-write pattern for consistency.
"""

from typing import List, Optional, Dict, Any
import json
import asyncio

from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.core.logging import get_logger

from .models import Node, Edge, PropertyGraph

logger = get_logger("shared", "ai.knowledge_graph.storage")


class PropertyGraphStorage:
    """
    Hybrid storage backend for property graphs.
    
    Uses ChromaDB for semantic search and libSQL for fast filtering/traversal.
    All operations are dual-write to maintain consistency.
    """
    
    def __init__(
        self,
        db_connection: EncryptedLibSQLConnection,
        chromadb_client: Any,  # chromadb.Client
        modelservice_client: Any = None  # ModelserviceClient for embeddings
    ):
        """
        Initialize storage with encrypted database and ChromaDB client.
        
        Args:
            db_connection: Encrypted LibSQL connection (injected)
            chromadb_client: ChromaDB client for semantic search
            modelservice_client: Modelservice client for embedding generation
        """
        self.db = db_connection
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
        Save node to both ChromaDB and libSQL.
        
        Args:
            node: Node to save
        """
        import asyncio
        
        def _sync_save_to_db():
            """Synchronous database write - runs in thread pool"""
            try:
                print(f"🕸️ [STORAGE_DB] Executing INSERT for node {node.id}...")
                with self.db:
                    self.db.execute(
                        """
                        INSERT INTO kg_nodes (
                            id, user_id, label, properties, confidence, source_text,
                            created_at, updated_at, valid_from, valid_until, is_current,
                            canonical_id, aliases_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            properties = excluded.properties,
                            confidence = excluded.confidence,
                            updated_at = excluded.updated_at,
                            valid_until = excluded.valid_until,
                            is_current = excluded.is_current
                        """,
                        node.to_libsql_tuple()
                    )
                    self.db.commit()
                print(f"🕸️ [STORAGE_DB] INSERT committed for node {node.id}")
            except Exception as e:
                print(f"🕸️ [STORAGE_DB] ❌ Database write FAILED: {e}")
                import traceback
                print(f"🕸️ [STORAGE_DB] Traceback:\n{traceback.format_exc()}")
                raise
        
        try:
            print(f"🕸️ [STORAGE] Saving node {node.id} (label={node.label})...")
            
            # Run blocking database operations in thread pool to avoid blocking event loop
            print(f"🕸️ [STORAGE] Executing database INSERT in thread pool...")
            await asyncio.to_thread(_sync_save_to_db)
            print(f"🕸️ [STORAGE] Database INSERT complete")
            
            # Generate embedding and save to ChromaDB
            print(f"🕸️ [STORAGE] Generating embedding for node...")
            doc = node.to_chromadb_document()
            
            # Generate embedding via modelservice
            embedding_result = await self.modelservice.generate_embeddings([doc["document"]])
            embeddings = embedding_result.get("embeddings", [])
            
            print(f"🕸️ [STORAGE] Saving to ChromaDB with embedding...")
            
            def _sync_save_to_chroma():
                """Synchronous ChromaDB write - runs in thread pool"""
                self._node_collection.upsert(
                    ids=[doc["id"]],
                    embeddings=[embeddings[0]],
                    documents=[doc["document"]],
                    metadatas=[doc["metadata"]]
                )
            
            await asyncio.to_thread(_sync_save_to_chroma)
            print(f"🕸️ [STORAGE] ChromaDB upsert complete")
            
            logger.debug(f"Saved node {node.id} (label={node.label})")
            print(f"🕸️ [STORAGE] ✅ Node {node.id} saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save node {node.id}: {e}")
            raise
    
    async def save_edge(self, edge: Edge) -> None:
        """
        Save edge to both ChromaDB and libSQL.
        
        Args:
            edge: Edge to save
        """
        import asyncio
        
        def _sync_save_to_db():
            """Synchronous database write - runs in thread pool"""
            with self.db:
                self.db.execute(
                    """
                    INSERT INTO kg_edges (
                        id, user_id, source_id, target_id, relation_type, properties,
                        confidence, source_text, created_at, updated_at,
                        valid_from, valid_until, is_current
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        properties = excluded.properties,
                        confidence = excluded.confidence,
                        updated_at = excluded.updated_at,
                        valid_until = excluded.valid_until,
                        is_current = excluded.is_current
                    """,
                    edge.to_libsql_tuple()
                )
        
        def _sync_save_to_chroma():
            """Synchronous ChromaDB write - runs in thread pool"""
            doc = edge.to_chromadb_document()
            self._edge_collection.upsert(
                ids=[doc["id"]],
                documents=[doc["document"]],
                metadatas=[doc["metadata"]]
            )
        
        try:
            # Run blocking database operations in thread pool
            await asyncio.to_thread(_sync_save_to_db)
            
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
    
    async def save_graph(self, graph: PropertyGraph) -> None:
        """
        Save entire graph (batch operation).
        
        Args:
            graph: PropertyGraph to save
        """
        logger.info(f"Saving graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        
        # Batch all database writes in single transaction to avoid lock contention
        def _sync_save_all():
            """Save all nodes and edges in single transaction"""
            print(f"🕸️ [STORAGE_DB] Starting batch transaction for {len(graph.nodes)} nodes, {len(graph.edges)} edges...")
            with self.db:
                # Insert all nodes
                for node in graph.nodes:
                    self.db.execute(
                        """
                        INSERT INTO kg_nodes (
                            id, user_id, label, properties, confidence, source_text,
                            created_at, updated_at, valid_from, valid_until, is_current,
                            canonical_id, aliases_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            properties = excluded.properties,
                            confidence = excluded.confidence,
                            updated_at = excluded.updated_at,
                            valid_until = excluded.valid_until,
                            is_current = excluded.is_current
                        """,
                        node.to_libsql_tuple()
                    )
                
                # Insert all edges
                for edge in graph.edges:
                    self.db.execute(
                        """
                        INSERT INTO kg_edges (
                            id, user_id, source_id, target_id, relation_type,
                            properties, confidence, source_text,
                            created_at, updated_at, valid_from, valid_until, is_current
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            properties = excluded.properties,
                            confidence = excluded.confidence,
                            updated_at = excluded.updated_at,
                            valid_until = excluded.valid_until,
                            is_current = excluded.is_current
                        """,
                        edge.to_libsql_tuple()
                    )
                
                self.db.commit()
            print(f"🕸️ [STORAGE_DB] Batch transaction committed")
        
        # Execute batch transaction in thread pool
        await asyncio.to_thread(_sync_save_all)
        
        # Generate embeddings and save to ChromaDB (in parallel)
        print(f"🕸️ [STORAGE] Generating embeddings for {len(graph.nodes)} nodes...")
        node_docs = [node.to_chromadb_document() for node in graph.nodes]
        node_texts = [doc["document"] for doc in node_docs]
        
        embedding_result = await self.modelservice.generate_embeddings(node_texts)
        embeddings = embedding_result.get("embeddings", [])
        
        print(f"🕸️ [STORAGE] Saving {len(graph.nodes)} nodes to ChromaDB...")
        
        def _sync_save_nodes_to_chroma():
            self._node_collection.upsert(
                ids=[doc["id"] for doc in node_docs],
                embeddings=embeddings,
                documents=[doc["document"] for doc in node_docs],
                metadatas=[doc["metadata"] for doc in node_docs]
            )
        
        await asyncio.to_thread(_sync_save_nodes_to_chroma)
        
        # Save edges to ChromaDB
        if graph.edges:
            print(f"🕸️ [STORAGE] Generating embeddings for {len(graph.edges)} edges...")
            edge_docs = [edge.to_chromadb_document() for edge in graph.edges]
            edge_texts = [doc["document"] for doc in edge_docs]
            
            edge_embedding_result = await self.modelservice.generate_embeddings(edge_texts)
            edge_embeddings = edge_embedding_result.get("embeddings", [])
            
            print(f"🕸️ [STORAGE] Saving {len(graph.edges)} edges to ChromaDB...")
            
            def _sync_save_edges_to_chroma():
                self._edge_collection.upsert(
                    ids=[doc["id"] for doc in edge_docs],
                    embeddings=edge_embeddings,
                    documents=[doc["document"] for doc in edge_docs],
                    metadatas=[doc["metadata"] for doc in edge_docs]
                )
            
            await asyncio.to_thread(_sync_save_edges_to_chroma)
        
        logger.info("Graph saved successfully")
    
    async def get_node(self, node_id: str) -> Optional[Node]:
        """
        Get node by ID from libSQL.
        
        Args:
            node_id: Node ID
            
        Returns:
            Node if found, None otherwise
        """
        with self.db:
            result = self.db.execute(
                "SELECT * FROM kg_nodes WHERE id = ?",
                (node_id,)
            ).fetchone()
        
        if not result:
            return None
        
        return self._row_to_node(result)
    
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
            current_only: Only return current facts (is_current=1)
            
        Returns:
            List of nodes
        """
        query = "SELECT * FROM kg_nodes WHERE user_id = ?"
        params = [user_id]
        
        if label:
            query += " AND label = ?"
            params.append(label)
        
        if current_only:
            query += " AND is_current = 1"
        
        query += " ORDER BY created_at DESC"
        
        with self.db:
            results = self.db.execute(query, params).fetchall()
        
        return [self._row_to_node(row) for row in results]
    
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
        
        # Fetch full nodes from libSQL
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
        if direction == "outgoing":
            query = "SELECT * FROM kg_edges WHERE source_id = ? AND is_current = 1"
        elif direction == "incoming":
            query = "SELECT * FROM kg_edges WHERE target_id = ? AND is_current = 1"
        else:  # both
            query = "SELECT * FROM kg_edges WHERE (source_id = ? OR target_id = ?) AND is_current = 1"
            with self.db:
                results = self.db.execute(query, (node_id, node_id)).fetchall()
            return [self._row_to_edge(row) for row in results]
        
        with self.db:
            results = self.db.execute(query, (node_id,)).fetchall()
        
        return [self._row_to_edge(row) for row in results]
    
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
        
        # Get all edges
        query = "SELECT * FROM kg_edges WHERE user_id = ?"
        params = [user_id]
        
        if current_only:
            query += " AND is_current = 1"
        
        with self.db:
            results = self.db.execute(query, params).fetchall()
        
        edges = [self._row_to_edge(row) for row in results]
        
        return PropertyGraph(nodes=nodes, edges=edges)
    
    def _row_to_node(self, row: tuple) -> Node:
        """Convert database row to Node object."""
        return Node(
            id=row[0],
            user_id=row[1],
            label=row[2],
            properties=json.loads(row[3]),
            confidence=row[4],
            source_text=row[5],
            created_at=row[6],
            updated_at=row[7],
            valid_from=row[8],
            valid_until=row[9],
            is_current=row[10],
            canonical_id=row[11],
            aliases=json.loads(row[12]) if row[12] else []
        )
    
    def _row_to_edge(self, row: tuple) -> Edge:
        """Convert database row to Edge object."""
        return Edge(
            id=row[0],
            user_id=row[1],
            source_id=row[2],
            target_id=row[3],
            relation_type=row[4],
            properties=json.loads(row[5]),
            confidence=row[6],
            source_text=row[7],
            created_at=row[8],
            updated_at=row[9],
            valid_from=row[10],
            valid_until=row[11],
            is_current=row[12]
        )
