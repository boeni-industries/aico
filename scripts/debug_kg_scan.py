#!/usr/bin/env python3
"""
Debug KG consolidation message scanning.
Simulates what the task does to find messages.
"""

import lmdb
import json
import os
from pathlib import Path


def debug_scan():
    """Debug the message scanning logic."""
    
    data_dir = os.getenv('AICO_DATA_DIR', str(Path.home() / 'Library/Application Support/aico/data'))
    lmdb_path = Path(data_dir) / 'memory' / 'working'
    
    print(f"📂 Opening LMDB at: {lmdb_path}")
    
    env = lmdb.open(
        str(lmdb_path),
        map_size=10 * 1024 * 1024 * 1024,
        max_dbs=10,
        readonly=True
    )
    
    try:
        session_db = env.open_db(b'session_memory')
        
        with env.begin(db=session_db) as txn:
            cursor = txn.cursor()
            
            users_with_pending = {}
            total_keys = 0
            message_count = 0
            skipped_role = 0
            skipped_consolidated = 0
            skipped_no_user = 0
            
            for key, value in cursor:
                total_keys += 1
                try:
                    msg = json.loads(value.decode('utf-8'))
                    
                    # Check 1: Only process user messages
                    if msg.get('role') != 'user':
                        skipped_role += 1
                        continue
                    
                    # Check 2: Check if message has been consolidated
                    if msg.get('kg_consolidated', False):
                        skipped_consolidated += 1
                        continue
                    
                    # Check 3: Get user_id
                    user_id = msg.get('user_id')
                    if not user_id:
                        skipped_no_user += 1
                        continue
                    
                    # Add to pending messages
                    if user_id not in users_with_pending:
                        users_with_pending[user_id] = []
                    
                    users_with_pending[user_id].append(msg)
                    message_count += 1
                    
                except Exception as e:
                    print(f"⚠️  Failed to parse: {e}")
                    continue
        
        print(f"\n📊 Scan Results (simulating task logic):")
        print(f"   Total keys scanned: {total_keys}")
        print(f"   Skipped (not user role): {skipped_role}")
        print(f"   Skipped (kg_consolidated=True): {skipped_consolidated}")
        print(f"   Skipped (no user_id): {skipped_no_user}")
        print(f"   ✅ Found unconsolidated user messages: {message_count}")
        print(f"   Users with pending messages: {len(users_with_pending)}")
        
        if users_with_pending:
            print(f"\n👥 Users found:")
            for user_id, messages in users_with_pending.items():
                print(f"   - {user_id}: {len(messages)} messages")
                # Show first message sample
                if messages:
                    sample = messages[0]
                    print(f"     Sample: {sample.get('text', '')[:50]}...")
        else:
            print(f"\n❌ No users with pending messages found!")
            print(f"   This explains why the task didn't process anything.")
        
    finally:
        env.close()


if __name__ == '__main__':
    print("🔍 Debugging KG consolidation message scan...")
    print("=" * 60)
    debug_scan()
    print("=" * 60)
