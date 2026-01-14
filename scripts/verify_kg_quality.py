#!/usr/bin/env python3
"""
Comprehensive KG Data Quality Verification Script

Checks:
1. Duplicate nodes (current only)
2. Duplicate edges (current only)
3. ChromaDB sync with libSQL
4. Orphaned edges
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from aico.core.paths import AICOPaths
from pathlib import Path
import sys

def main():
    # Use AICOPaths to get correct paths (same as CLI and backend)
    db_path = AICOPaths.resolve_database_path("aico.db", "auto")
    # Connect to PostgreSQL
    from aico.core.config import ConfigurationManager
    from aico.security import AICOKeyManager
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    key_manager = AICOKeyManager(config)
    
    pg_cfg = config.get("core.database.postgres", {})
    password = key_manager.get_database_password("postgres", username=pg_cfg.get("user", "postgres"))
    
    db = psycopg2.connect(
        host=pg_cfg.get("host", "127.0.0.1"),
        port=int(pg_cfg.get("port", 5432)),
        dbname=pg_cfg.get("db_name", "aico"),
        user=pg_cfg.get("user", "postgres"),
        password=password,
        cursor_factory=RealDictCursor
    )
    
    print("=" * 80)
    print("🔍 KNOWLEDGE GRAPH DATA QUALITY VERIFICATION")
    print("=" * 80)
    
    # 1. Check duplicate nodes
    print("\n📊 Checking for duplicate nodes...")
    cursor = db.execute("""
        SELECT label, properties, COUNT(*) as count 
        FROM kg_nodes 
        WHERE is_current = 1 
        GROUP BY label, properties 
        HAVING count > 1
        ORDER BY count DESC
    """)
    duplicate_nodes = cursor.fetchall()
    
    if duplicate_nodes:
        print(f"❌ FAIL: Found {len(duplicate_nodes)} duplicate node groups:")
        for row in duplicate_nodes[:5]:
            print(f"   - {row[0]}: {row[2]} duplicates")
    else:
        print("✅ PASS: No duplicate nodes")
    
    # 2. Check duplicate edges
    print("\n📊 Checking for duplicate edges...")
    cursor = db.execute("""
        SELECT source_id, target_id, relation_type, COUNT(*) as count 
        FROM kg_edges 
        WHERE is_current = 1 
        GROUP BY source_id, target_id, relation_type 
        HAVING count > 1
        ORDER BY count DESC
    """)
    duplicate_edges = cursor.fetchall()
    
    if duplicate_edges:
        print(f"❌ FAIL: Found {len(duplicate_edges)} duplicate edge groups:")
        for row in duplicate_edges[:5]:
            print(f"   - {row[2]}: {row[3]} duplicates")
    else:
        print("✅ PASS: No duplicate edges")
    
    # 3. Check ChromaDB sync
    print("\n📊 Checking ChromaDB sync...")
    
    # Get libSQL counts
    cursor = db.execute("SELECT COUNT(*) FROM kg_nodes WHERE is_current = 1")
    libsql_nodes = cursor.fetchone()[0]
    
    cursor = db.execute("SELECT COUNT(*) FROM kg_edges WHERE is_current = 1")
    libsql_edges = cursor.fetchone()[0]
    
    # Get ChromaDB counts
    try:
        import chromadb
        from chromadb.config import Settings
        
        # Use AICOPaths to get correct ChromaDB path
        chromadb_path = AICOPaths.get_semantic_memory_path()
        
        client = chromadb.PersistentClient(
            path=str(chromadb_path),
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        
        try:
            node_collection = client.get_collection("kg_nodes")
            chromadb_nodes = node_collection.count()
        except:
            chromadb_nodes = 0
        
        try:
            edge_collection = client.get_collection("kg_edges")
            chromadb_edges = edge_collection.count()
        except:
            chromadb_edges = 0
        
        # Compare
        nodes_match = libsql_nodes == chromadb_nodes
        edges_match = libsql_edges == chromadb_edges
        
        print(f"   Nodes: libSQL={libsql_nodes}, ChromaDB={chromadb_nodes} {'✅' if nodes_match else '❌'}")
        print(f"   Edges: libSQL={libsql_edges}, ChromaDB={chromadb_edges} {'✅' if edges_match else '❌'}")
        
        if not nodes_match:
            diff = chromadb_nodes - libsql_nodes
            if diff > 0:
                print(f"   ⚠️  ChromaDB has {diff} stale node embeddings")
            else:
                print(f"   ⚠️  ChromaDB is missing {abs(diff)} node embeddings")
        
        if not edges_match:
            diff = chromadb_edges - libsql_edges
            if diff > 0:
                print(f"   ⚠️  ChromaDB has {diff} stale edge embeddings")
            else:
                print(f"   ⚠️  ChromaDB is missing {abs(diff)} edge embeddings")
        
        if nodes_match and edges_match:
            print("✅ PASS: ChromaDB perfectly synced")
        else:
            print("❌ FAIL: ChromaDB out of sync")
    
    except Exception as e:
        print(f"⚠️  Could not check ChromaDB: {e}")
        nodes_match = edges_match = False
    
    # 4. Check orphaned edges
    print("\n📊 Checking for orphaned edges...")
    cursor = db.execute("""
        SELECT COUNT(*) 
        FROM kg_edges e 
        WHERE e.is_current = 1 
        AND (
            NOT EXISTS (SELECT 1 FROM kg_nodes n WHERE n.id = e.source_id AND n.is_current = 1)
            OR NOT EXISTS (SELECT 1 FROM kg_nodes n WHERE n.id = e.target_id AND n.is_current = 1)
        )
    """)
    orphaned_edges = cursor.fetchone()[0]
    
    if orphaned_edges > 0:
        print(f"❌ FAIL: Found {orphaned_edges} orphaned edges")
    else:
        print("✅ PASS: No orphaned edges")
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    
    all_passed = (
        len(duplicate_nodes) == 0 and
        len(duplicate_edges) == 0 and
        nodes_match and edges_match and
        orphaned_edges == 0
    )
    
    if all_passed:
        print("✅ ALL CHECKS PASSED - 100% DATA QUALITY")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - DATA QUALITY ISSUES DETECTED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
