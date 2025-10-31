"""
Test KG retrieval to simulate what would be injected into conversation context.
"""
import asyncio
import json
import sys
import os

# Suppress all warnings and logging
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
import warnings
warnings.filterwarnings('ignore')

# Mock logger before any AICO imports
from unittest.mock import MagicMock
mock_logger = MagicMock()
sys.modules['aico.core.logging'] = MagicMock(get_logger=lambda *args: mock_logger)

from aico.core.paths import AICOPaths
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.ai.knowledge_graph import PropertyGraphStorage
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


async def test_kg_retrieval(user_id: str, query: str):
    """Simulate KG context retrieval for a conversation."""
    
    # Initialize storage
    db_path = AICOPaths.resolve_database_path("aico.db", "auto")
    
    # Get database connection (simplified - assumes key is available)
    from aico.core.config import ConfigurationManager
    from aico.security import AICOKeyManager
    import keyring
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    key_manager = AICOKeyManager(config)
    
    stored_key = keyring.get_password(key_manager.service_name, "master_key")
    if not stored_key:
        print("Error: Master key not found")
        return
    
    master_key = bytes.fromhex(stored_key)
    db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
    db_connection = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
    db_connection.connect()
    
    # Initialize ChromaDB
    chromadb_path = AICOPaths.get_semantic_memory_path()
    chromadb_client = chromadb.PersistentClient(
        path=str(chromadb_path),
        settings=Settings(anonymized_telemetry=False, allow_reset=True)
    )
    
    # Generate query embedding
    embedding_model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
    query_embedding = embedding_model.encode(query).tolist()
    
    # Query ChromaDB for relevant nodes
    collection = chromadb_client.get_collection("kg_nodes")
    where_filter = {"$and": [{"user_id": user_id}, {"is_current": 1}]}
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where=where_filter
    )
    
    # Fetch full nodes from LibSQL
    storage = PropertyGraphStorage(db_connection, chromadb_client, None)
    nodes = []
    if results["ids"] and results["ids"][0]:
        for node_id in results["ids"][0]:
            node = await storage.get_node(node_id)
            if node:
                nodes.append(node)
    
    # Get edges connecting these nodes
    node_ids = [node.id for node in nodes]
    edges = []
    if node_ids:
        placeholders = ','.join(['?' for _ in node_ids])
        edge_query = f"""
            SELECT 
                e.id, e.relation_type, e.confidence,
                n1.properties as source_props,
                n2.properties as target_props
            FROM kg_edges e
            JOIN kg_nodes n1 ON e.source_id = n1.id
            JOIN kg_nodes n2 ON e.target_id = n2.id
            WHERE e.user_id = ? 
            AND e.is_current = 1
            AND (e.source_id IN ({placeholders}) OR e.target_id IN ({placeholders}))
        """
        
        params = [user_id] + node_ids + node_ids
        edge_results = db_connection.execute(edge_query, params).fetchall()
        
        for row in edge_results:
            source_props = json.loads(row[3])
            target_props = json.loads(row[4])
            edges.append({
                "relation": row[1],
                "source": source_props.get("name", "?"),
                "target": target_props.get("name", "?"),
                "confidence": row[2]
            })
    
    # Format as conversation context
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print(f"{'='*60}\n")
    
    print("📊 KNOWLEDGE GRAPH CONTEXT:\n")
    
    if nodes:
        print("Entities:")
        for node in nodes:
            name = node.properties.get("name", "?")
            print(f"  • {name} ({node.label}) - confidence: {node.confidence:.2f}")
    
    if edges:
        print("\nRelationships:")
        for edge in edges:
            print(f"  • {edge['source']} {edge['relation']} {edge['target']} - confidence: {edge['confidence']:.2f}")
    
    # Show formatted prompt context
    print(f"\n{'='*60}")
    print("FORMATTED FOR LLM PROMPT:")
    print(f"{'='*60}\n")
    
    context_lines = []
    if nodes:
        context_lines.append("Known facts about the user:")
        for node in nodes:
            name = node.properties.get("name", "?")
            context_lines.append(f"- {name} is a {node.label}")
    
    if edges:
        context_lines.append("\nRelationships:")
        for edge in edges:
            context_lines.append(f"- {edge['source']} {edge['relation']} {edge['target']}")
    
    print("\n".join(context_lines))
    print()


if __name__ == "__main__":
    user_id = "1e69de47-a3af-4343-8dba-dbf5dcf5f160"
    
    # Test different queries
    queries = [
        "where do I work",
        "tell me about myself",
        "who am I",
    ]
    
    for query in queries:
        asyncio.run(test_kg_retrieval(user_id, query))
        print("\n")
