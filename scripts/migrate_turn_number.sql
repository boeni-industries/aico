-- Migration: Add turn_number column to conversation_messages
-- Run with: docker exec -i aico-postgres psql -U postgres -d aico < scripts/migrate_turn_number.sql

\set ON_ERROR_STOP on

BEGIN;

-- Check if column already exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'aico_core' 
        AND table_name = 'conversation_messages' 
        AND column_name = 'turn_number'
    ) THEN
        RAISE NOTICE 'turn_number column already exists, skipping migration';
    ELSE
        RAISE NOTICE 'Starting turn_number migration...';
        
        -- Step 1: Add column as nullable
        RAISE NOTICE 'Adding turn_number column (nullable)...';
        ALTER TABLE aico_core.conversation_messages 
        ADD COLUMN turn_number INTEGER;
        
        -- Step 2: Backfill turn numbers based on created_at ordering
        RAISE NOTICE 'Backfilling turn numbers for existing messages...';
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
        WHERE cm.message_id = nm.message_id;
        
        -- Step 3: Make column NOT NULL
        RAISE NOTICE 'Making turn_number NOT NULL...';
        ALTER TABLE aico_core.conversation_messages 
        ALTER COLUMN turn_number SET NOT NULL;
        
        -- Step 4: Add unique constraint
        RAISE NOTICE 'Adding unique constraint...';
        ALTER TABLE aico_core.conversation_messages 
        ADD CONSTRAINT uq_conversation_messages_turn 
        UNIQUE (tenant_id, conversation_id, turn_number);
        
        -- Step 5: Add index for turn_number ordering
        RAISE NOTICE 'Creating index for turn_number ordering...';
        CREATE INDEX idx_conversation_messages_conversation_turn 
        ON aico_core.conversation_messages (tenant_id, conversation_id, turn_number ASC);
        
        -- Step 6: Verify migration
        RAISE NOTICE 'Verifying migration...';
        RAISE NOTICE 'Migration statistics:';
    END IF;
END $$;

-- Show migration results
SELECT 
    COUNT(*) as total_messages,
    COUNT(turn_number) as messages_with_turn_number,
    MIN(turn_number) as min_turn,
    MAX(turn_number) as max_turn
FROM aico_core.conversation_messages;

COMMIT;

\echo '✅ Migration complete!'
