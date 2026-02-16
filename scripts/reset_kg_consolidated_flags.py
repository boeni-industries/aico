#!/usr/bin/env python3
"""
Reset kg_consolidated flags in LMDB working memory.

This script resets the kg_consolidated flag to False for all messages
in working memory, allowing the KG consolidation task to reprocess them.

Usage:
    python scripts/reset_kg_consolidated_flags.py
"""

import lmdb
import json
import os
from pathlib import Path


def reset_kg_consolidated_flags():
    """Reset kg_consolidated flags to False in LMDB working memory."""
    
    # Get LMDB path from environment or use default
    data_dir = os.getenv('AICO_DATA_DIR', str(Path.home() / 'Library/Application Support/aico/data'))
    lmdb_path = Path(data_dir) / 'memory' / 'working'
    
    if not lmdb_path.exists():
        print(f"❌ LMDB path not found: {lmdb_path}")
        return
    
    print(f"📂 Opening LMDB at: {lmdb_path}")
    
    # Open LMDB environment with named databases
    env = lmdb.open(
        str(lmdb_path),
        map_size=10 * 1024 * 1024 * 1024,  # 10GB
        max_dbs=10,
        readonly=False
    )
    
    total_messages = 0
    reset_count = 0
    already_false = 0
    
    try:
        # Open the session_memory database
        session_db = env.open_db(b'session_memory')
        
        with env.begin(write=True, db=session_db) as txn:
            cursor = txn.cursor()
            
            for key, value in cursor:
                try:
                    # Decode key and value
                    key_str = key.decode('utf-8')
                    
                    total_messages += 1
                    
                    # Parse message
                    msg = json.loads(value.decode('utf-8'))
                    
                    # Check if it has kg_consolidated flag
                    if 'kg_consolidated' in msg:
                        if msg['kg_consolidated'] is True:
                            # Reset the flag
                            msg['kg_consolidated'] = False
                            if 'kg_consolidated_at' in msg:
                                del msg['kg_consolidated_at']
                            
                            # Write back to LMDB
                            txn.put(key, json.dumps(msg).encode('utf-8'))
                            reset_count += 1
                            
                            # Show progress every 100 messages
                            if reset_count % 100 == 0:
                                print(f"  Reset {reset_count} messages...")
                        else:
                            already_false += 1
                
                except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                    print(f"⚠️  Failed to process key {key}: {e}")
                    continue
        
        print(f"\n✅ Reset complete!")
        print(f"   Total messages scanned: {total_messages}")
        print(f"   Flags reset (True → False): {reset_count}")
        print(f"   Already False: {already_false}")
        print(f"   Unchanged: {total_messages - reset_count - already_false}")
        
    finally:
        env.close()


if __name__ == '__main__':
    print("🔄 Resetting kg_consolidated flags in LMDB working memory...")
    print("=" * 60)
    reset_kg_consolidated_flags()
    print("=" * 60)
    print("✅ Done! You can now run: aico scheduler trigger ams.kg_consolidation")
