#!/usr/bin/env python3
"""Fix schema v14 by dropping incomplete tables and re-applying migration."""

import sys
sys.path.insert(0, '/Users/mbo/Documents/dev/aico')

from pathlib import Path
from aico.core.paths import AICOPaths
from aico.security import AICOKeyManager
from aico.core.config import ConfigurationManager
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.data.schemas.core import CORE_SCHEMA
import traceback

print("=" * 60)
print("Fixing Schema v14 - Dropping Incomplete Tables")
print("=" * 60)

# Get database path
db_path = AICOPaths.resolve_database_path("aico.db")
print(f"\n📁 Database: {db_path}")

# Get encryption key
config = ConfigurationManager()
key_manager = AICOKeyManager(config)

try:
    # Get cached session
    cached_key = key_manager._get_cached_session()
    if not cached_key:
        print("❌ No cached session - run 'aico db status' first")
        sys.exit(1)
    
    db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
    
    # Connect to database
    conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
    print("✅ Connected to database")
    
    # Get schema v14 rollback statements
    schema_v14 = CORE_SCHEMA[14]
    
    print(f"\n🗑️  Dropping incomplete v14 tables and indexes:\n")
    
    # Execute rollback statements to clean up
    for stmt in schema_v14.rollback_statements:
        try:
            conn.execute(stmt)
            print(f"  ✅ {stmt}")
        except Exception as e:
            print(f"  ⚠️  {stmt} - {e}")
    
    conn.commit()
    
    print("\n✅ Cleanup complete")
    print("\n" + "=" * 60)
    print("Now run: aico db init")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"\nTraceback:\n{traceback.format_exc()}")
    sys.exit(1)
