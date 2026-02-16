#!/usr/bin/env python3
"""
Check kg_consolidated flags in LMDB working memory.
"""

import lmdb
import json
import os
from pathlib import Path


def check_kg_flags():
    """Check current state of kg_consolidated flags."""
    
    data_dir = os.getenv('AICO_DATA_DIR', str(Path.home() / 'Library/Application Support/aico/data'))
    lmdb_path = Path(data_dir) / 'memory' / 'working'
    
    if not lmdb_path.exists():
        print(f"❌ LMDB path not found: {lmdb_path}")
        return
    
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
            
            total = 0
            user_messages = 0
            flag_true = 0
            flag_false = 0
            flag_missing = 0
            
            sample_messages = []
            
            for key, value in cursor:
                total += 1
                try:
                    msg = json.loads(value.decode('utf-8'))
                    
                    # Only look at user messages
                    if msg.get('role') == 'user':
                        user_messages += 1
                        
                        if 'kg_consolidated' in msg:
                            if msg['kg_consolidated'] is True:
                                flag_true += 1
                            else:
                                flag_false += 1
                                # Sample a few
                                if len(sample_messages) < 3:
                                    sample_messages.append({
                                        'user_id': msg.get('user_id'),
                                        'text': msg.get('text', '')[:50],
                                        'kg_consolidated': msg.get('kg_consolidated'),
                                        'timestamp': msg.get('timestamp')
                                    })
                        else:
                            flag_missing += 1
                            if len(sample_messages) < 3:
                                sample_messages.append({
                                    'user_id': msg.get('user_id'),
                                    'text': msg.get('text', '')[:50],
                                    'kg_consolidated': 'MISSING',
                                    'timestamp': msg.get('timestamp')
                                })
                
                except Exception as e:
                    continue
        
        print(f"\n📊 Statistics:")
        print(f"   Total messages: {total}")
        print(f"   User messages: {user_messages}")
        print(f"   kg_consolidated=True: {flag_true}")
        print(f"   kg_consolidated=False: {flag_false}")
        print(f"   kg_consolidated missing: {flag_missing}")
        print(f"   Should process: {flag_false + flag_missing}")
        
        if sample_messages:
            print(f"\n📝 Sample messages to process:")
            for i, msg in enumerate(sample_messages, 1):
                print(f"   {i}. user_id={msg['user_id']}, flag={msg['kg_consolidated']}")
                print(f"      text={msg['text']}...")
                print(f"      timestamp={msg['timestamp']}")
        
    finally:
        env.close()


if __name__ == '__main__':
    print("🔍 Checking kg_consolidated flags...")
    print("=" * 60)
    check_kg_flags()
    print("=" * 60)
