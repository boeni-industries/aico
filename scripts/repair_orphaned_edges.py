#!/usr/bin/env python3
"""
Repair Orphaned Edges in Knowledge Graph

This script identifies and repairs edges pointing to historical (merged) nodes.
It UPDATES edges to point to canonical nodes, preserving knowledge.
Only deletes edges when no canonical node can be found.

Run this after any consolidation to ensure data quality.
"""

from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.core.paths import AICOPaths
import sys
import json

def main():
    db_path = AICOPaths.resolve_database_path("aico.db", "auto")
    db = EncryptedLibSQLConnection(db_path=str(db_path))
    
    print("=" * 80)
    print("🔧 REPAIRING ORPHANED EDGES")
    print("=" * 80)
    
    # Find orphaned edges with details
    print("\n🔍 Scanning for orphaned edges...")
    cursor = db.execute("""
        SELECT DISTINCT e.id, e.source_id, e.target_id, e.relation_type, e.user_id,
               CASE WHEN ns.is_current = 0 OR ns.id IS NULL THEN 1 ELSE 0 END as source_historical,
               CASE WHEN nt.is_current = 0 OR nt.id IS NULL THEN 1 ELSE 0 END as target_historical
        FROM kg_edges e
        LEFT JOIN kg_nodes ns ON e.source_id = ns.id
        LEFT JOIN kg_nodes nt ON e.target_id = nt.id
        WHERE e.is_current = 1
        AND (ns.is_current = 0 OR ns.id IS NULL OR nt.is_current = 0 OR nt.id IS NULL)
    """)
    
    orphaned_edges = cursor.fetchall()
    
    if not orphaned_edges:
        print("✅ No orphaned edges found - database is clean!")
        db.close()
        return 0
    
    print(f"⚠️  Found {len(orphaned_edges)} orphaned edges")
    
    # Repair orphaned edges
    print("\n🔧 Repairing orphaned edges...")
    fixed_count = 0
    deleted_count = 0
    
    for edge_id, source_id, target_id, relation_type, user_id, source_hist, target_hist in orphaned_edges:
        print(f"\n   Edge {edge_id[:12]}... ({relation_type})")
        fixed = False
        
        # If source is historical/missing, find canonical replacement
        if source_hist:
            cursor = db.execute("""
                SELECT id, label, properties FROM kg_nodes WHERE id = ?
            """, (source_id,))
            source_node = cursor.fetchone()
            
            if source_node:
                label, properties = source_node[1], source_node[2]
                print(f"      Source historical: {label} ({json.loads(properties).get('name', 'N/A')})")
                
                # Find canonical node with same label and properties
                cursor = db.execute("""
                    SELECT id FROM kg_nodes
                    WHERE user_id = ? AND label = ? AND properties = ? AND is_current = 1
                    LIMIT 1
                """, (user_id, label, properties))
                
                canonical = cursor.fetchone()
                if canonical:
                    try:
                        db.execute(
                            "UPDATE kg_edges SET source_id = ?, updated_at = datetime('now') WHERE id = ?",
                            (canonical[0], edge_id)
                        )
                        print(f"      ✅ Updated source to canonical node {canonical[0][:12]}...")
                        fixed_count += 1
                        fixed = True
                    except Exception as e:
                        if "UNIQUE constraint failed" in str(e):
                            print(f"      ⚠️  Update would create duplicate - deleting edge")
                            db.execute("DELETE FROM kg_edges WHERE id = ?", (edge_id,))
                            deleted_count += 1
                            fixed = True
        
        # If target is historical/missing, find canonical replacement
        if target_hist and not fixed:
            cursor = db.execute("""
                SELECT id, label, properties FROM kg_nodes WHERE id = ?
            """, (target_id,))
            target_node = cursor.fetchone()
            
            if target_node:
                label, properties = target_node[1], target_node[2]
                print(f"      Target historical: {label} ({json.loads(properties).get('name', 'N/A')})")
                
                # Find canonical node with same label and properties
                cursor = db.execute("""
                    SELECT id FROM kg_nodes
                    WHERE user_id = ? AND label = ? AND properties = ? AND is_current = 1
                    LIMIT 1
                """, (user_id, label, properties))
                
                canonical = cursor.fetchone()
                if canonical:
                    try:
                        db.execute(
                            "UPDATE kg_edges SET target_id = ?, updated_at = datetime('now') WHERE id = ?",
                            (canonical[0], edge_id)
                        )
                        print(f"      ✅ Updated target to canonical node {canonical[0][:12]}...")
                        fixed_count += 1
                        fixed = True
                    except Exception as e:
                        if "UNIQUE constraint failed" in str(e):
                            print(f"      ⚠️  Update would create duplicate - deleting edge")
                            db.execute("DELETE FROM kg_edges WHERE id = ?", (edge_id,))
                            deleted_count += 1
                            fixed = True
        
        # Last resort: delete if no canonical node found
        if not fixed:
            print(f"      ❌ No canonical node found - deleting edge")
            db.execute("DELETE FROM kg_edges WHERE id = ?", (edge_id,))
            deleted_count += 1
    
    db.commit()
    
    # Verify cleanup
    print("\n🔍 Verifying repair...")
    cursor = db.execute("""
        SELECT COUNT(*)
        FROM kg_edges e
        WHERE e.is_current = 1
        AND (
            NOT EXISTS (SELECT 1 FROM kg_nodes n WHERE n.id = e.source_id AND n.is_current = 1)
            OR NOT EXISTS (SELECT 1 FROM kg_nodes n WHERE n.id = e.target_id AND n.is_current = 1)
        )
    """)
    
    remaining = cursor.fetchone()[0]
    
    if remaining == 0:
        print("✅ All orphaned edges repaired successfully!")
    else:
        print(f"⚠️  {remaining} orphaned edges still remain")
    
    db.close()
    
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    print(f"Edges fixed (updated to canonical): {fixed_count}")
    print(f"Edges deleted (no canonical found):  {deleted_count}")
    print(f"Database status: {'✅ Clean' if remaining == 0 else '⚠️  Issues remain'}")
    
    return 0 if remaining == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
