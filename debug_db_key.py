#!/usr/bin/env python3
"""
Database Key Derivation Diagnostic Script

This script helps debug database encryption key issues by:
1. Testing key derivation with current password
2. Checking salt file integrity
3. Attempting database connection with derived key
4. Comparing with stored keyring key
"""

import sys
import os
from pathlib import Path

# Add shared module to path
shared_path = Path(__file__).parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.security import AICOKeyManager
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.core.paths import AICOPaths
import keyring
import getpass

def main():
    print("🔍 AICO Database Key Diagnostic Tool")
    print("=" * 50)
    
    # Initialize components
    key_manager = AICOKeyManager()
    paths = AICOPaths()
    db_path = paths.resolve_database_path("aico.db")
    
    print(f"Database path: {db_path}")
    print(f"Salt file: {db_path}.salt")
    
    # Check if setup exists
    if not key_manager.has_stored_key():
        print("❌ No stored key found. Run 'aico security setup' first.")
        return
    
    print("✅ Stored key found in keyring")
    
    # Check salt file
    salt_file = Path(f"{db_path}.salt")
    if not salt_file.exists():
        print("❌ Salt file missing!")
        return
    
    print(f"✅ Salt file exists ({salt_file.stat().st_size} bytes)")
    
    # Test 1: Get stored key from keyring
    print("\n📋 Test 1: Keyring stored key")
    try:
        stored_key_hex = keyring.get_password(key_manager.service_name, "master_key")
        if stored_key_hex:
            stored_key = bytes.fromhex(stored_key_hex)
            print(f"✅ Retrieved stored key: {len(stored_key)} bytes")
            print(f"   First 8 bytes: {stored_key[:8].hex()}")
        else:
            print("❌ No stored key in keyring")
            return
    except Exception as e:
        print(f"❌ Error retrieving stored key: {e}")
        return
    
    # Test 2: Derive database key from stored key
    print("\n📋 Test 2: Database key derivation from stored key")
    try:
        db_key_from_stored = key_manager.derive_database_key(stored_key, "libsql", str(db_path))
        print(f"✅ Derived database key: {len(db_key_from_stored)} bytes")
        print(f"   First 8 bytes: {db_key_from_stored[:8].hex()}")
    except Exception as e:
        print(f"❌ Error deriving database key: {e}")
        return
    
    # Test 3: Test database connection with derived key
    print("\n📋 Test 3: Database connection test")
    try:
        conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key_from_stored)
        # Try a simple query
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
        print("✅ Database connection successful!")
        if result:
            print(f"   Found table: {result[0]}")
        else:
            print("   Database is empty (no tables)")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   This suggests the key is wrong or database is corrupted")
    
    # Test 4: Interactive password test
    print("\n📋 Test 4: Interactive password verification")
    password = getpass.getpass("Enter your master password to test derivation: ")
    
    try:
        # Derive master key from password
        derived_master = key_manager._derive_key(password)
        print(f"✅ Derived master key from password: {len(derived_master)} bytes")
        print(f"   First 8 bytes: {derived_master[:8].hex()}")
        
        # Compare with stored key
        if derived_master == stored_key:
            print("✅ Password-derived key MATCHES stored key")
        else:
            print("❌ Password-derived key DOES NOT MATCH stored key")
            print("   This means either:")
            print("   - Wrong password entered")
            print("   - Salt file changed")
            print("   - Key derivation parameters changed")
        
        # Derive database key from password-derived master key
        db_key_from_password = key_manager.derive_database_key(derived_master, "libsql", str(db_path))
        
        if db_key_from_password == db_key_from_stored:
            print("✅ Database keys match")
        else:
            print("❌ Database keys DO NOT match")
            
    except Exception as e:
        print(f"❌ Error in password test: {e}")
    
    # Test 5: Check database file integrity
    print("\n📋 Test 5: Database file integrity")
    try:
        # Try to open as regular SQLite (should fail if encrypted)
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print("⚠️  Database opens as regular SQLite - NOT ENCRYPTED!")
            print("   This means the database was created without encryption")
        else:
            print("✅ Database appears to be encrypted (regular SQLite fails)")
            
    except sqlite3.DatabaseError as e:
        if "file is not a database" in str(e).lower():
            print("✅ Database is encrypted (regular SQLite can't read it)")
        else:
            print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n" + "=" * 50)
    print("Diagnostic complete!")

if __name__ == "__main__":
    main()
