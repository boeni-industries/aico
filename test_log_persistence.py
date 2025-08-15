#!/usr/bin/env python3
"""
Direct test to verify log persistence without CLI interference.
"""
import sys
from pathlib import Path

# Add shared to path
shared_path = Path(__file__).parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths
from aico.security.key_manager import AICOKeyManager
from aico.data.libsql.encrypted import EncryptedLibSQLConnection

def main():
    # Initialize components
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    
    key_manager = AICOKeyManager()
    paths = AICOPaths()
    db_path = paths.resolve_database_path("aico.db")
    
    # Get cached session key
    cached_key = key_manager._get_cached_session()
    if not cached_key:
        print("No cached session found")
        return
    
    # Derive database key
    db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
    
    # Connect to database
    conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
    
    # Count logs
    result = conn.execute("SELECT COUNT(*) as count FROM logs").fetchone()
    print(f"Current log count: {result[0] if result else 'N/A'}")
    
    # Show recent logs
    recent = conn.execute("""
        SELECT created_at, level, subsystem, module, message 
        FROM logs 
        ORDER BY created_at DESC 
        LIMIT 3
    """).fetchall()
    
    print("\nRecent logs:")
    for row in recent:
        print(f"  {row[0]} | {row[1]} | {row[2]}.{row[3]} | {row[4]}")

if __name__ == "__main__":
    main()
