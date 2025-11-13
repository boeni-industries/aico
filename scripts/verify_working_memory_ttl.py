#!/usr/bin/env python3
"""
Verify that WorkingMemoryStore is using the correct TTL from config.
"""

import sys
sys.path.insert(0, '/Users/mbo/Documents/dev/aico')

from aico.core.config import ConfigurationManager

def verify_working_memory_ttl():
    """Verify WorkingMemoryStore TTL"""
    print("=" * 60)
    print("WorkingMemoryStore TTL Verification")
    print("=" * 60)
    
    # Initialize config manager
    config = ConfigurationManager()
    config.initialize()
    
    # Simulate what WorkingMemoryStore does in __init__
    ttl_seconds = config.get("core.memory.working.ttl_seconds", 86400)
    
    print(f"\n✓ WorkingMemoryStore initialized")
    print(f"  TTL value: {ttl_seconds} seconds")
    print(f"  TTL in days: {ttl_seconds / 86400:.1f} days")
    
    # Verify it's the expected value
    expected_ttl = 2592000  # 30 days
    
    if ttl_seconds == expected_ttl:
        print(f"\n✅ SUCCESS: WorkingMemoryStore is using 30-day TTL ({expected_ttl} seconds)")
        print(f"   Messages will be retained for 30 days")
        return True
    elif ttl_seconds == 86400:
        print(f"\n❌ FAILURE: WorkingMemoryStore is using 24-hour TTL (86400 seconds)")
        print(f"   Expected: {expected_ttl} seconds (30 days)")
        print(f"   This means the config change didn't take effect!")
        return False
    else:
        print(f"\n⚠️  WARNING: WorkingMemoryStore is using unexpected TTL: {ttl_seconds} seconds")
        print(f"   Expected: {expected_ttl} seconds (30 days)")
        return False

if __name__ == "__main__":
    success = verify_working_memory_ttl()
    sys.exit(0 if success else 1)
