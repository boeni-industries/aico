#!/usr/bin/env python3
"""
Clean up duplicate hobby goals from the database.

This script removes duplicate goals created by the curiosity scan task,
keeping only the most recent goal for each title.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aico.data.libsql import EncryptedLibSQLConnection
from aico.core.config import ConfigurationManager

def cleanup_duplicate_goals(user_id: str, dry_run: bool = True):
    """Clean up duplicate goals for a user.
    
    Args:
        user_id: User ID to clean up goals for
        dry_run: If True, only show what would be deleted
    """
    config = ConfigurationManager()
    db = EncryptedLibSQLConnection(config)
    
    # Get all goals grouped by title
    goals = db.execute(
        """SELECT goal_id, title, created_at, status 
           FROM agency_goals 
           WHERE user_id = ? 
           ORDER BY title, created_at DESC""",
        (user_id,)
    ).fetchall()
    
    # Group by title
    by_title = {}
    for goal in goals:
        title = goal['title']
        if title not in by_title:
            by_title[title] = []
        by_title[title].append(goal)
    
    # Find duplicates
    to_keep = []
    to_delete = []
    
    for title, goal_list in by_title.items():
        if len(goal_list) > 1:
            # Keep the most recent (first in list due to DESC order)
            to_keep.append(goal_list[0])
            to_delete.extend(goal_list[1:])
            print(f"\n📋 {title}:")
            print(f"   Total: {len(goal_list)}")
            print(f"   ✅ Keep: {goal_list[0]['goal_id'][:8]}... (created {goal_list[0]['created_at']})")
            print(f"   ❌ Delete: {len(goal_list) - 1} duplicates")
        else:
            to_keep.append(goal_list[0])
    
    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  Total goals: {len(goals)}")
    print(f"  To keep: {len(to_keep)}")
    print(f"  To delete: {len(to_delete)}")
    print(f"{'='*80}\n")
    
    if not to_delete:
        print("✅ No duplicates found!")
        return
    
    if dry_run:
        print("🔍 DRY RUN - No changes made")
        print("Run with --execute to actually delete duplicates")
        return
    
    # Delete intentions referencing duplicate goals first
    print("\n🗑️  Deleting intentions for duplicate goals...")
    deleted_intentions = 0
    for goal in to_delete:
        result = db.execute(
            "DELETE FROM intention_set WHERE goal_id = ?",
            (goal['goal_id'],)
        )
        deleted_intentions += result.rowcount if hasattr(result, 'rowcount') else 0
    
    print(f"   Deleted {deleted_intentions} intentions")
    
    # Delete duplicate goals
    print("\n🗑️  Deleting duplicate goals...")
    deleted_goals = 0
    for goal in to_delete:
        db.execute(
            "DELETE FROM agency_goals WHERE goal_id = ?",
            (goal['goal_id'],)
        )
        deleted_goals += 1
    
    db.commit()
    
    print(f"   Deleted {deleted_goals} goals")
    print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up duplicate hobby goals")
    parser.add_argument("--user", required=True, help="User ID")
    parser.add_argument("--execute", action="store_true", help="Actually delete (default is dry run)")
    
    args = parser.parse_args()
    
    cleanup_duplicate_goals(args.user, dry_run=not args.execute)
