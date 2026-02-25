#!/usr/bin/env python3
"""
Schema Migration to Truth Script

Brings the live PostgreSQL database into alignment with schema.sql.
Handles:
1. Missing columns (like autonomy_level - already fixed)
2. Extra columns (like proactive_behavior_level)
3. Type mismatches (TEXT → TIMESTAMPTZ)
4. Data migration with proper type conversion
"""

import subprocess
import sys
from typing import List, Tuple


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
    print("\n🔧 AICO Schema Migration to Truth")
    print("=" * 70)
    print("This will align the live database with schema.sql")
    print("=" * 70)
    
    migrations = []
    
    # ========================================================================
    # 1. Fix ethics_value_profiles
    # ========================================================================
    
    migrations.append((
        "Drop extra proactive_behavior_level column",
        """
        ALTER TABLE aico_core.ethics_value_profiles 
        DROP COLUMN IF EXISTS proactive_behavior_level;
        """
    ))
    
    # ========================================================================
    # 2. Fix TIMESTAMPTZ columns (most critical)
    # ========================================================================
    
    # Helper function to convert TEXT to TIMESTAMPTZ
    timestamp_migrations = [
        # arbiter tables
        ("arbiter_ab_tests", ["created_at", "updated_at", "start_date", "end_date"]),
        ("arbiter_bandit_arms", ["created_at", "updated_at", "last_pulled"]),
        
        # consent tables
        ("consent_audit_log", ["created_at"]),
        ("consent_user_consents", ["created_at", "updated_at", "granted_at", "expires_at", "revoked_at"]),
        
        # emotion tables
        ("emotion_history", ["created_at", "timestamp"]),
        ("emotion_state", ["timestamp", "updated_at"]),
        
        # ethics tables
        ("ethics_decisions_cache", ["cached_at", "expires_at", "last_hit_at"]),
        ("ethics_gate_audit", ["created_at"]),
        
        # kg tables
        ("kg_edges", ["created_at", "updated_at", "valid_from", "valid_until"]),
        ("kg_nodes", ["created_at", "updated_at", "valid_from", "valid_until"]),
        
        # system tables
        ("system_event_metrics", ["bucket_start", "created_at"]),
        ("system_event_replay_sessions", ["created_at", "started_at", "completed_at", "start_time", "end_time"]),
        ("system_events", ["timestamp"]),
        
        # user tables
        ("user_feedback_requests", ["created_at", "responded_at"]),
        ("user_proactive_preferences", ["updated_at"]),
        ("user_time_preferences", ["created_at", "updated_at"]),
        
        # workflow tables
        ("workflow_executions", ["created_at", "updated_at", "started_at", "completed_at"]),
        ("workflow_stages", ["created_at", "started_at", "completed_at"]),
    ]
    
    for table, columns in timestamp_migrations:
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
    # 3. Fix VARCHAR length mismatches
    # ========================================================================
    
    migrations.append((
        "Fix remediation_executions.skill_id type",
        """
        ALTER TABLE aico_core.remediation_executions 
        ALTER COLUMN skill_id TYPE VARCHAR(200);
        """
    ))
    
    migrations.append((
        "Fix remediation_executions.executed_by type",
        """
        ALTER TABLE aico_core.remediation_executions 
        ALTER COLUMN executed_by TYPE VARCHAR(100);
        """
    ))
    
    migrations.append((
        "Fix system_health_checks.status type",
        """
        ALTER TABLE aico_core.system_health_checks 
        ALTER COLUMN status TYPE VARCHAR(20);
        """
    ))
    
    migrations.append((
        "Fix system_health_checks.parent_check_id type",
        """
        ALTER TABLE aico_core.system_health_checks 
        ALTER COLUMN parent_check_id TYPE VARCHAR(100);
        """
    ))
    
    migrations.append((
        "Fix system_issues types",
        """
        ALTER TABLE aico_core.system_issues 
        ALTER COLUMN issue_id TYPE VARCHAR(100),
        ALTER COLUMN service TYPE VARCHAR(100),
        ALTER COLUMN severity TYPE VARCHAR(20),
        ALTER COLUMN status TYPE VARCHAR(20);
        """
    ))
    
    # ========================================================================
    # 4. Add missing columns
    # ========================================================================
    
    migrations.append((
        "Add auth_sessions.session_type if missing",
        """
        ALTER TABLE aico_core.auth_sessions 
        ADD COLUMN IF NOT EXISTS session_type VARCHAR(50) DEFAULT 'unified';
        """
    ))
    
    migrations.append((
        "Add ethics_gate_audit.check_level if missing",
        """
        ALTER TABLE aico_core.ethics_gate_audit 
        ADD COLUMN IF NOT EXISTS check_level VARCHAR(50);
        """
    ))
    
    migrations.append((
        "Add system_health_checks.check_id if missing",
        """
        ALTER TABLE aico_core.system_health_checks 
        ADD COLUMN IF NOT EXISTS check_id VARCHAR(100);
        """
    ))
    
    # ========================================================================
    # 5. Handle ams_user_memories extra columns (Memory Album feature)
    # ========================================================================
    
    # These are legitimate feature additions - keep them but document
    print("\n⚠️  Note: ams_user_memories has 13 extra columns (Memory Album feature)")
    print("   These are intentional feature additions and will be kept.")
    print("   TODO: Update schema.sql to include these columns.")
    
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
        print("\n🎉 All migrations completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Run validation script: python scripts/validate_schema.py")
        print("   2. Update schema.sql with Memory Album columns")
        print("   3. Restart backend containers: docker restart aico-gateway aico-core")
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
