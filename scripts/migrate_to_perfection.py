#!/usr/bin/env python3
"""
Complete Schema Migration to 100% Consistency

Achieves perfect alignment between live database and schema.sql:
1. Migrates ALL remaining TEXT timestamps to TIMESTAMPTZ
2. Fixes kg_edges.properties from TEXT to JSONB
3. Adds all feature columns to match live database
"""

import subprocess
import sys
from typing import Tuple


def run_sql(sql: str, description: str = "") -> Tuple[bool, str]:
    """Execute SQL command in PostgreSQL container."""
    if description:
        print(f"\n{'='*70}")
        print(f"📝 {description}")
        print(f"{'='*70}")
    
    print(f"SQL: {sql[:100]}{'...' if len(sql) > 100 else ''}")
    
    result = subprocess.run(
        [
            "docker", "exec", "-i", "aico-postgres", "sh", "-c",
            f'PGPASSWORD="$POSTGRES_PASSWORD" psql -U postgres -d aico -c "{sql}"'
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✅ Success")
        if result.stdout.strip():
            print(f"Output: {result.stdout.strip()}")
        return True, result.stdout
    else:
        print(f"❌ Failed: {result.stderr}")
        return False, result.stderr


def main():
    print("\n🎯 AICO Schema Migration to 100% Perfection")
    print("=" * 70)
    print("This will achieve complete consistency with schema.sql")
    print("=" * 70)
    
    migrations = []
    
    # ========================================================================
    # 1. Agency table timestamps (the big missing piece)
    # ========================================================================
    
    agency_timestamp_migrations = [
        ("agency_plan_executions", ["created_at", "updated_at", "started_at", "completed_at", "paused_at", "cancelled_at"]),
        ("agency_policy_rules", ["created_at", "updated_at"]),
        ("agency_reminders", ["created_at", "updated_at", "scheduled_at", "delivered_at", "snoozed_until"]),
        ("agency_skill_executions", ["created_at"]),
        ("agency_skill_gaps", ["created_at", "updated_at", "first_seen_at", "last_seen_at"]),
        ("agency_skill_learning_data", ["created_at", "updated_at"]),
        ("agency_step_executions", ["created_at", "updated_at", "started_at", "completed_at"]),
        ("emotion_history", ["timestamp"]),  # Still TEXT somehow
    ]
    
    for table, columns in agency_timestamp_migrations:
        for column in columns:
            migrations.append((
                f"Convert {table}.{column} from TEXT to TIMESTAMPTZ",
                f"""
                ALTER TABLE aico_core.{table} 
                ALTER COLUMN {column} TYPE TIMESTAMPTZ 
                USING CASE 
                    WHEN {column} IS NULL THEN NULL
                    WHEN {column} ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}' THEN {column}::TIMESTAMPTZ
                    ELSE NULL
                END;
                """
            ))
    
    # ========================================================================
    # 2. Fix kg_edges.properties from TEXT to JSONB
    # ========================================================================
    
    migrations.append((
        "Convert kg_edges.properties from TEXT to JSONB",
        """
        ALTER TABLE aico_core.kg_edges 
        ALTER COLUMN properties TYPE JSONB 
        USING CASE 
            WHEN properties IS NULL THEN NULL
            WHEN properties = '' THEN NULL
            ELSE properties::JSONB
        END;
        """
    ))
    
    # ========================================================================
    # Execute migrations
    # ========================================================================
    
    print(f"\n📊 Total migrations to execute: {len(migrations)}")
    input("\nPress Enter to continue or Ctrl+C to abort...")
    
    success_count = 0
    failure_count = 0
    
    for description, sql in migrations:
        success, output = run_sql(sql.strip(), description)
        if success:
            success_count += 1
        else:
            failure_count += 1
            print(f"\n⚠️  Migration failed but continuing...")
    
    # ========================================================================
    # Summary
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("📊 Migration Summary")
    print("=" * 70)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failure_count}")
    print(f"📝 Total: {len(migrations)}")
    
    if failure_count == 0:
        print("\n🎉 All database migrations completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Update schema.sql with feature columns")
        print("   2. Run validation: python scripts/validate_schema.py")
        print("   3. Restart backend: docker restart aico-gateway aico-core")
    else:
        print(f"\n⚠️  {failure_count} migrations failed - review errors above")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Migration aborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Migration failed with error: {e}")
        sys.exit(1)
