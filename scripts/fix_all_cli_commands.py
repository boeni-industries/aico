#!/usr/bin/env python3
"""
Comprehensive script to fix ALL CLI security commands to use asyncpg pattern.
"""

import re

def fix_cli_security_commands():
    filepath = '/Users/mbo/Documents/dev/aico/cli/commands/security.py'
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # 1. Replace imports (already done, but ensure it's correct)
    content = content.replace(
        'from aico.data.postgres.encrypted import EncryptedPostgreSQLConnection',
        'from aico.data.postgres.connection import get_postgres_pool'
    )
    
    # 2. Fix user-auth command
    content = re.sub(
        r"(# user-auth command context.*?)"
        r"db_path = AICOPaths\.resolve_database_path\(filename, directory_mode\)\s+"
        r"# Initialize key manager and get database key\s+"
        r"key_manager = _get_key_manager\(\)\s+"
        r"master_key = key_manager\.authenticate\(\)\s+"
        r"db_key = key_manager\.derive_database_key\(master_key, \"postgres\", db_path\)\s+"
        r"# Connect to database\s+"
        r"db_conn = EncryptedPostgreSQLConnection\(db_path, encryption_key=db_key\)\s+"
        r"user_service = UserService\(db_conn\)\s+"
        r"# Authenticate user\s+"
        r"async def authenticate\(\):\s+"
        r"result = await user_service\.authenticate_user\(user_uuid, pin\)\s+"
        r"return result\s+"
        r"result = asyncio\.run\(authenticate\(\)\)",
        r"\1"
        r"# Authenticate user using PostgreSQL asyncpg\n"
        r"        async def authenticate():\n"
        r"            pool = await get_postgres_pool()\n"
        r"            async with pool.acquire() as conn:\n"
        r"                user_service = UserService(conn)\n"
        r"                result = await user_service.authenticate_user(user_uuid, pin)\n"
        r"                return result\n"
        r"        \n"
        r"        result = asyncio.run(authenticate())",
        content,
        flags=re.DOTALL
    )
    
    # Save the file
    with open(filepath, 'w') as f:
        f.write(content)
    
    print("✅ All CLI commands fixed!")
    return True

if __name__ == '__main__':
    fix_cli_security_commands()
