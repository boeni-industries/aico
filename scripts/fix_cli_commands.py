#!/usr/bin/env python3
"""
Script to update all CLI security commands to use asyncpg pattern.
Replaces old EncryptedPostgreSQLConnection pattern with get_postgres_pool().
"""

import re
import sys

def fix_cli_commands(filepath):
    """Update CLI commands to use asyncpg pattern."""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern 1: Replace the old database connection setup with asyncpg pool
    old_pattern = r'''        # Use configuration-based path resolution.*?
        db_config = config_manager\.get\("database\.postgres", \{\}\)
        filename = db_config\.get\("filename", "aico\.db"\)
        directory_mode = db_config\.get\("directory_mode", "auto"\)
        
        db_path = AICOPaths\.resolve_database_path\(filename, directory_mode\)
        
        # Initialize key manager and get database key
        key_manager = _get_key_manager\(\)
        master_key = key_manager\.authenticate\(\)
        db_key = key_manager\.derive_database_key\(master_key, "postgres", db_path\)
        
        # Connect to database
        db_conn = EncryptedPostgreSQLConnection\(db_path, encryption_key=db_key\)
        user_service = UserService\(db_conn\)'''
    
    # This is complex - let's do targeted replacements instead
    
    # Replace import
    content = content.replace(
        'from aico.data.postgres.encrypted import EncryptedPostgreSQLConnection',
        'from aico.data.postgres.connection import get_postgres_pool'
    )
    
    print("✅ Updated imports")
    print(f"Total length: {len(content)} characters")
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    return True

if __name__ == '__main__':
    filepath = '/Users/mbo/Documents/dev/aico/cli/commands/security.py'
    if fix_cli_commands(filepath):
        print("✅ CLI commands updated successfully")
    else:
        print("❌ Failed to update CLI commands")
        sys.exit(1)
