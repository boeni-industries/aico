#!/usr/bin/env python3
"""
Database Migration: Add turn_number to conversation_messages

This migration adds the turn_number column to the conversation_messages table
and backfills existing messages with sequential turn numbers based on created_at.

IMPORTANT: Run this migration during a maintenance window as it will:
1. Add NOT NULL column (requires backfill)
2. Add unique constraint on (tenant_id, conversation_id, turn_number)
3. Create new index for turn_number ordering

Usage:
    python scripts/migrate_add_turn_number.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from aico.data.postgres.connection import get_async_session_factory
from aico.core.logging import get_logger

logger = get_logger("migration.add_turn_number")


async def migrate():
    """Add turn_number column and backfill existing data."""
    
    logger.info("Starting turn_number migration...")
    
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Step 1: Check if column already exists
            logger.info("Checking if turn_number column exists...")
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'aico_core' 
                AND table_name = 'conversation_messages' 
                AND column_name = 'turn_number'
            """))
            
            if result.fetchone():
                logger.info("turn_number column already exists, skipping migration")
                return
            
            # Step 2: Add column as nullable first (to allow backfill)
            logger.info("Adding turn_number column (nullable)...")
            await session.execute(text("""
                ALTER TABLE aico_core.conversation_messages 
                ADD COLUMN IF NOT EXISTS turn_number INTEGER
            """))
            await session.commit()
            
            # Step 3: Backfill turn numbers based on created_at ordering
            logger.info("Backfilling turn numbers for existing messages...")
            await session.execute(text("""
                WITH numbered_messages AS (
                    SELECT 
                        message_id,
                        ROW_NUMBER() OVER (
                            PARTITION BY tenant_id, conversation_id 
                            ORDER BY created_at ASC, message_id ASC
                        ) as turn_num
                    FROM aico_core.conversation_messages
                    WHERE turn_number IS NULL
                )
                UPDATE aico_core.conversation_messages cm
                SET turn_number = nm.turn_num
                FROM numbered_messages nm
                WHERE cm.message_id = nm.message_id
            """))
            await session.commit()
            
            # Step 4: Make column NOT NULL
            logger.info("Making turn_number NOT NULL...")
            await session.execute(text("""
                ALTER TABLE aico_core.conversation_messages 
                ALTER COLUMN turn_number SET NOT NULL
            """))
            await session.commit()
            
            # Step 5: Add unique constraint
            logger.info("Adding unique constraint on (tenant_id, conversation_id, turn_number)...")
            await session.execute(text("""
                ALTER TABLE aico_core.conversation_messages 
                ADD CONSTRAINT uq_conversation_messages_turn 
                UNIQUE (tenant_id, conversation_id, turn_number)
            """))
            await session.commit()
            
            # Step 6: Add index for turn_number ordering
            logger.info("Creating index for turn_number ordering...")
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_turn 
                ON aico_core.conversation_messages (tenant_id, conversation_id, turn_number ASC)
            """))
            await session.commit()
            
            # Step 7: Verify migration
            logger.info("Verifying migration...")
            result = await session.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(turn_number) as with_turn_number,
                       MIN(turn_number) as min_turn,
                       MAX(turn_number) as max_turn
                FROM aico_core.conversation_messages
            """))
            row = result.fetchone()
            
            logger.info(
                f"Migration complete! "
                f"Total messages: {row.total}, "
                f"With turn_number: {row.with_turn_number}, "
                f"Turn range: {row.min_turn}-{row.max_turn}"
            )
            
            if row.total != row.with_turn_number:
                logger.error(
                    f"Migration incomplete! {row.total - row.with_turn_number} messages missing turn_number"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            await session.rollback()
            raise


async def main():
    """Run migration."""
    try:
        success = await migrate()
        if success:
            logger.info("✅ Migration completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Migration failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
