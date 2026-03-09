#!/usr/bin/env python3
"""
Comprehensive KG Data Quality Verification Script

Checks:
1. Duplicate nodes (current only)
2. Duplicate edges (current only)
3. Orphaned edges
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
    
    pg_cfg = config.get("postgres", {})
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
    
    # 3. Check orphaned edges
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
