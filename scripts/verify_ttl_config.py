#!/usr/bin/env python3
"""
Verify that TTL configuration is properly loaded from config file.
"""

import sys
sys.path.insert(0, '/Users/mbo/Documents/dev/aico')

from aico.core.config import ConfigurationManager

def verify_ttl():
    """Verify TTL configuration"""
    print("=" * 60)
    print("TTL Configuration Verification")
    print("=" * 60)
    
    # Initialize config manager
    config = ConfigurationManager()
    config.initialize()
    
    # Get TTL value
    ttl_seconds = config.get("core.memory.working.ttl_seconds", 86400)
    
    print(f"\n✓ Config loaded successfully")
    print(f"  TTL value: {ttl_seconds} seconds")
    print(f"  TTL in days: {ttl_seconds / 86400:.1f} days")
    print(f"  TTL in hours: {ttl_seconds / 3600:.1f} hours")
    
    # Verify it's the expected value
    expected_ttl = 2592000  # 30 days
    
    if ttl_seconds == expected_ttl:
        print(f"\n✅ SUCCESS: TTL is correctly set to 30 days ({expected_ttl} seconds)")
        return True
    elif ttl_seconds == 86400:
        print(f"\n❌ FAILURE: TTL is still 24 hours (86400 seconds)")
        print(f"   Expected: {expected_ttl} seconds (30 days)")
        print(f"   Action: Check if config file was saved and backend restarted")
        return False
    else:
        print(f"\n⚠️  WARNING: TTL is set to unexpected value: {ttl_seconds} seconds")
        print(f"   Expected: {expected_ttl} seconds (30 days)")
        return False

if __name__ == "__main__":
    success = verify_ttl()
    sys.exit(0 if success else 1)
