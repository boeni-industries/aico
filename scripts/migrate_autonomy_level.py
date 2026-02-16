#!/usr/bin/env python3
"""
Database Migration: Rename proactive_behavior_level to autonomy_level

This script renames the column in the ethics_value_profiles table to match
the new consistent naming convention throughout the system.

Usage:
    python scripts/migrate_autonomy_level.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aico.data.postgres.connection import get_postgres_pool
from aico.core.logging import get_logger

logger = get_logger("migration.autonomy_level")


async def migrate_autonomy_level():
    """Rename proactive_behavior_level column to autonomy_level."""
    
    logger.info("Starting autonomy_level migration...")
    
    try:
        pool = await get_postgres_pool()
        
        async with pool.acquire() as conn:
            # Check if old column exists
            check_old = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'ethics_value_profiles' 
                AND column_name = 'proactive_behavior_level'
            """)
            
            # Check if new column exists
            check_new = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'ethics_value_profiles' 
                AND column_name = 'autonomy_level'
            """)
            
            if check_old == 0 and check_new == 1:
                logger.info("✅ Migration already completed - autonomy_level column exists")
                return True
            
            if check_old == 0 and check_new == 0:
                logger.error("❌ Neither column exists - database schema may be corrupted")
                return False
            
            if check_old == 1 and check_new == 1:
                logger.warning("⚠️  Both columns exist - dropping old column")
                await conn.execute("""
                    ALTER TABLE ethics_value_profiles 
                    DROP COLUMN proactive_behavior_level
                """)
                logger.info("✅ Dropped old proactive_behavior_level column")
                return True
            
            # Perform the migration
            logger.info("Renaming proactive_behavior_level to autonomy_level...")
            
            await conn.execute("""
                ALTER TABLE ethics_value_profiles 
                RENAME COLUMN proactive_behavior_level TO autonomy_level
            """)
            
            logger.info("✅ Successfully renamed column to autonomy_level")
            
            # Verify the migration
            count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM ethics_value_profiles
            """)
            
            logger.info(f"✅ Migration complete - {count} profiles updated")
            return True
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


async def main():
    """Main entry point."""
    success = await migrate_autonomy_level()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("The proactive_behavior_level column has been renamed to autonomy_level")
        sys.exit(0)
    else:
        print("\n❌ Migration failed - check logs for details")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
