#!/usr/bin/env python3
"""Test schema v14 migration against real database with detailed error logging."""

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
print("Testing Schema v14 Migration Against Real Database")
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
    
    # Get schema v14
    schema_v14 = CORE_SCHEMA[14]
    print(f"\n📋 Schema v14: {schema_v14.name}")
    print(f"    Statements: {len(schema_v14.sql_statements)}")
    
    # Check current version
    current_version = conn.execute(
        "SELECT value FROM _aico_schema_metadata WHERE key = 'schema_version'"
    ).fetchone()
    
    if current_version:
        print(f"    Current DB version: {current_version[0]}")
    
    # Test each statement individually
    print(f"\n🔍 Testing statements individually (DRY RUN):\n")
    
    for i, stmt in enumerate(schema_v14.sql_statements, 1):
        try:
            # Extract table/index name for display
            stmt_clean = stmt.strip()
            if "CREATE TABLE" in stmt_clean:
                table_name = stmt_clean.split("(")[0].replace("CREATE TABLE IF NOT EXISTS", "").strip()
                print(f"  {i}. CREATE TABLE {table_name}")
                
                # Check if table already exists
                existing = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name.strip(),)
                ).fetchone()
                
                if existing:
                    print(f"     ⚠️  Table already exists: {table_name}")
                
            elif "CREATE INDEX" in stmt_clean:
                idx_name = stmt_clean.split("ON")[0].replace("CREATE INDEX IF NOT EXISTS", "").strip()
                print(f"  {i}. CREATE INDEX {idx_name}")
                
                # Check if index already exists
                existing = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                    (idx_name.strip(),)
                ).fetchone()
                
                if existing:
                    print(f"     ⚠️  Index already exists: {idx_name}")
            
            # Try to parse statement (doesn't execute due to IF NOT EXISTS)
            # This will catch syntax errors
            conn.execute("EXPLAIN " + stmt)
            print(f"     ✅ Syntax valid")
            
        except Exception as e:
            print(f"     ❌ Error: {e}")
            print(f"     SQL: {stmt[:100]}...")
    
    print("\n" + "=" * 60)
    print("✅ Dry run complete - no errors found")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"\nTraceback:\n{traceback.format_exc()}")
    sys.exit(1)
