#!/usr/bin/env python3
"""
Manual Consolidation Trigger

Manually triggers memory consolidation for testing purposes.
Bypasses idle detection and runs consolidation immediately.
"""

import asyncio
import sys
from datetime import datetime, timezone

from pathlib import Path

from aico.core.config import ConfigurationManager
from aico.core.logging import initialize_cli_logging
from aico.core.paths import AICOPaths
from aico.data.libsql.encrypted import EncryptedLibSQLConnection


async def check_services():
    """Check if required services are available."""
    print("🔍 Checking required services...")
    
    # Check if modelservice is available (needed for embeddings)
    try:
        from backend.services import get_modelservice_client
        from aico.core.config import ConfigurationManager
        
        config = ConfigurationManager()
        config.initialize()
        
        modelservice = get_modelservice_client(config)
        # Try a simple health check
        # Note: This is a basic check, actual health check would need async
        print("   ✅ ModelService client available")
        return True
    except Exception as e:
        print(f"   ❌ ModelService not available: {e}")
        print()
        print("⚠️  CONSOLIDATION REQUIRES MODELSERVICE TO BE RUNNING!")
        print("   Start the backend with: uv run aico start")
        print()
        return False

async def main():
    """Main consolidation trigger function."""
    print("=" * 80)
    print("🧠 MANUAL MEMORY CONSOLIDATION TRIGGER")
    print("=" * 80)
    print()
    
    # Check services first
    if not await check_services():
        print("❌ Cannot proceed without required services")
        return
    
    print()
    
    # Initialize configuration
    print("📋 Initializing configuration...")
    config = ConfigurationManager()
    config.initialize()
    
    # Get database connection
    print("🔌 Connecting to database...")
    db_config = config.get("database.libsql", {})
    filename = db_config.get("filename", "aico.db")
    directory_mode = db_config.get("directory_mode", "auto")
    db_path = AICOPaths.resolve_database_path(filename, directory_mode)
    db_connection = EncryptedLibSQLConnection(db_path)
    
    # Initialize logging
    print("📋 Initializing logging...")
    initialize_cli_logging(config, db_connection)
    
    # NOW import memory manager (after logging is initialized)
    from aico.ai.memory.manager import MemoryManager
    
    # Get memory manager
    print("🧠 Initializing memory manager...")
    memory_manager = MemoryManager(config, db_connection=db_connection)
    
    # Ensure memory manager is initialized
    if not memory_manager._initialized:
        print("   Initializing memory manager components...")
        await memory_manager.initialize()
    
    print("✅ Memory manager ready")
    print()
    
    # Check if AMS is enabled
    if not memory_manager._ams_enabled:
        print("❌ AMS components not enabled!")
        print("   Enable consolidation in config/defaults/core.yaml:")
        print("   memory.consolidation.enabled: true")
        return 1
    
    print("✅ AMS components enabled")
    print()
    
    # Get consolidation scheduler
    scheduler = memory_manager._consolidation_scheduler
    if not scheduler:
        print("❌ Consolidation scheduler not available!")
        return 1
    
    print("📊 Consolidation Configuration:")
    print(f"   Max concurrent users: {scheduler.max_concurrent_users}")
    print(f"   Max duration: {scheduler.max_duration_minutes} minutes")
    print(f"   User sharding cycle: {scheduler.user_sharding_cycle_days} days")
    print()
    
    # Get all users
    print("👥 Fetching users...")
    result = db_connection.execute("SELECT DISTINCT user_id FROM ams_user_memories").fetchall()
    all_users = [row[0] for row in result]
    
    if not all_users:
        print("⚠️  No users found in database")
        return 0
    
    print(f"   Found {len(all_users)} user(s)")
    print()
    
    # Consolidate all users (non-interactive mode)
    users_to_consolidate = all_users
    print(f"✅ Will consolidate all {len(users_to_consolidate)} users")
    print()
    
    print()
    print("=" * 80)
    print("🚀 STARTING CONSOLIDATION")
    print("=" * 80)
    print()
    
    # Run consolidation for each user
    results = {
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "errors": []
    }
    
    start_time = datetime.now(timezone.utc)
    
    for i, user_id in enumerate(users_to_consolidate, 1):
        print(f"[{i}/{len(users_to_consolidate)}] Processing user: {user_id}")
        
        try:
            # Get working memory for this user
            messages = await memory_manager._working_store.retrieve_user_history(user_id, limit=100)
            
            if not messages:
                print(f"   ⚠️  No working memory found - skipping")
                results["skipped"] += 1
                continue
            
            print(f"   📋 Found {len(messages)} messages in working memory")
            
            # Trigger consolidation using the new method
            print(f"   🔄 Running consolidation...")
            
            result = await scheduler.consolidate_user_memories(
                user_id=user_id,
                working_store=memory_manager._working_store,
                semantic_store=memory_manager._semantic_store,
                db_connection=db_connection,
                max_messages=100
            )
            
            if result.get("success"):
                print(f"   ✅ Success: {result['messages_retrieved']} messages → {result['memories_created']} memories")
                if result.get('errors'):
                    print(f"   ⚠️  Warnings: {'; '.join(result['errors'])}")
                results["successful"] += 1
            else:
                print(f"   ❌ Failed: {'; '.join(result.get('errors', ['Unknown error']))}")
                results["failed"] += 1
                results["errors"].append(f"{user_id}: {'; '.join(result.get('errors', []))}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["failed"] += 1
            results["errors"].append(f"{user_id}: {str(e)}")
        
        print()
    
    # Summary
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()
    
    print("=" * 80)
    print("📊 CONSOLIDATION SUMMARY")
    print("=" * 80)
    print(f"Duration: {duration:.2f} seconds")
    print(f"✅ Successful: {results['successful']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"⚠️  Skipped: {results['skipped']}")
    print()
    
    if results["errors"]:
        print("Errors:")
        for error in results["errors"]:
            print(f"  - {error}")
        print()
    
    print("=" * 80)
    
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
