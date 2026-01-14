#!/usr/bin/env python3
"""
Backfill temporal metadata for existing knowledge graph nodes and edges.

This script updates all nodes and edges that have NULL valid_from to use their created_at timestamp.
This allows the temporal scrubber to work correctly with historical data.

Usage:
    python backfill_temporal_metadata.py [--user-id USER_ID] [--dry-run]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))



def get_db_connection():
    """Get database connection."""
    db_path = None  # PostgreSQL migration()
    conn = None      return conn.connect()


def backfill_temporal_metadata(user_id: str = None, dry_run: bool = False):
    """
    Backfill valid_from timestamps for nodes and edges.
    
    Args:
        user_id: Optional user ID to filter by (None = all users)
        dry_run: If True, only show what would be updated without making changes
    """
    db = get_db_connection()
    
    # Build WHERE clause
    where_clause = "WHERE valid_from IS NULL"
    params = []
    if user_id:
        where_clause += " AND user_id = ?"
        params.append(user_id)
    
    # Count nodes to update
    cursor = db.execute(f"SELECT COUNT(*) FROM kg_nodes {where_clause}", params)
    node_count = cursor.fetchone()[0]
    
    # Count edges to update
    cursor = db.execute(f"SELECT COUNT(*) FROM kg_edges {where_clause}", params)
    edge_count = cursor.fetchone()[0]
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Temporal Metadata Backfill")
    print("=" * 60)
    print(f"Nodes to update: {node_count}")
    print(f"Edges to update: {edge_count}")
    
    if node_count == 0 and edge_count == 0:
        print("\n✅ No records need updating - all temporal metadata is already set!")
        return
    
    if dry_run:
        print("\n[DRY RUN] No changes will be made.")
        
        # Show sample of what would be updated
        if node_count > 0:
            print("\nSample nodes that would be updated:")
            cursor = db.execute(
                f"""
                SELECT id, label, created_at 
                FROM kg_nodes {where_clause}
                LIMIT 5
                """,
                params
            )
            for row in cursor.fetchall():
                print(f"  - {row[1]} ({row[0][:8]}...) created_at: {row[2]}")
        
        if edge_count > 0:
            print("\nSample edges that would be updated:")
            cursor = db.execute(
                f"""
                SELECT id, relation_type, created_at 
                FROM kg_edges {where_clause}
                LIMIT 5
                """,
                params
            )
            for row in cursor.fetchall():
                print(f"  - {row[1]} ({row[0][:8]}...) created_at: {row[2]}")
        
        return
    
    # Perform the update
    print("\nUpdating records...")
    
    with db:
        # Update nodes: set valid_from = created_at where valid_from is NULL
        db.execute(
            f"""
            UPDATE kg_nodes 
            SET valid_from = created_at,
                updated_at = ?
            {where_clause}
            """,
            [datetime.now(timezone.utc).isoformat()] + params
        )
        
        # Update edges: set valid_from = created_at where valid_from is NULL
        db.execute(
            f"""
            UPDATE kg_edges 
            SET valid_from = created_at,
                updated_at = ?
            {where_clause}
            """,
            [datetime.now(timezone.utc).isoformat()] + params
        )
        
        db.commit()
    
    print(f"\n✅ Successfully updated:")
    print(f"   - {node_count} nodes")
    print(f"   - {edge_count} edges")
    print(f"\nAll nodes and edges now have valid_from timestamps!")
    print("The temporal scrubber will now show nodes/edges appearing at their creation time.")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill temporal metadata for knowledge graph"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="Only update records for this user ID (default: all users)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    
    args = parser.parse_args()
    
    try:
        backfill_temporal_metadata(
            user_id=args.user_id,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
