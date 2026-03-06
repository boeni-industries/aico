"""One-off live DB migration: seed a tenant and owner membership, then backfill tenant_id.

This script is intentionally NOT part of the CLI to avoid accidental use.

Safety properties:
- No DROP/TRUNCATE/DELETE
- INSERT uses ON CONFLICT DO NOTHING
- Backfill uses UPDATE ... WHERE tenant_id IS NULL

Usage (example):
  uv run python scripts/seed_tenant_live_db.py \
    --tenant-id <uuid> \
    --display-name "Boeni Industries Ltd" \
    --owner-user-id 1e69de47-a3af-4343-8dba-dbf5dcf5f160

Notes:
- Requires access to the running Postgres container (docker exec).
- Uses AICO keyring credentials (same as `aico pg` commands).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-off: seed tenant + membership and backfill tenant_id for existing live DB",
    )
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID to seed")
    parser.add_argument("--display-name", required=True, help="Tenant display name")
    parser.add_argument("--owner-user-id", required=True, help="User ID to create owner membership for")
    parser.add_argument(
        "--tenant-type",
        default="deployment",
        help="Tenant type (default: deployment)",
    )
    parser.add_argument(
        "--shadow",
        action="store_true",
        help="Use shadow Postgres container (aico-postgres-shadow)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    # Match CLI pattern: add shared module to path
    if getattr(sys, "frozen", False):
        shared_path = Path(sys._MEIPASS) / "shared"  # type: ignore[attr-defined]
    else:
        shared_path = Path(__file__).parent.parent / "shared"
    sys.path.insert(0, str(shared_path))

    from aico.core.config import ConfigurationManager
    from aico.security.key_manager import AICOKeyManager

    import subprocess
    import uuid

    config = ConfigurationManager()
    config.initialize(lightweight=True)
    cfg_key = "postgres_shadow" if args.shadow else "postgres"
    pg_cfg = config.get(cfg_key, {}) or {}
    if not pg_cfg:
        raise RuntimeError(f"No {cfg_key} configuration found")

    host = pg_cfg.get("host", "127.0.0.1")
    port = int(pg_cfg.get("port", 5432))
    db_name = pg_cfg.get("db_name", "aico")
    user = pg_cfg.get("user", "postgres")

    key_manager = AICOKeyManager(config)
    password = key_manager.get_database_password("postgres", username=user)
    if not password:
        raise RuntimeError("Postgres password not found in keyring. Run 'aico deploy pg'")

    # Validate UUID format early
    uuid.UUID(args.tenant_id)
    uuid.UUID(args.owner_user_id)

    safe_display_name = args.display_name.replace("'", "''")
    safe_tenant_type = args.tenant_type.replace("'", "''")

    membership_id = str(uuid.uuid4())

    sql = f"""
    BEGIN;

    INSERT INTO aico_core.tenants (
        tenant_id,
        tenant_type,
        display_name,
        status,
        primary_language,
        metadata_json,
        created_at,
        updated_at
    ) VALUES (
        '{args.tenant_id}',
        '{safe_tenant_type}',
        '{safe_display_name}',
        'active',
        NULL,
        NULL,
        NOW(),
        NOW()
    ) ON CONFLICT (tenant_id) DO NOTHING;

    INSERT INTO aico_core.tenant_memberships (
        membership_id,
        tenant_id,
        user_id,
        role,
        created_at
    ) VALUES (
        '{membership_id}',
        '{args.tenant_id}',
        '{args.owner_user_id}',
        'owner',
        NOW()
    ) ON CONFLICT (tenant_id, user_id) DO NOTHING;

    UPDATE aico_core.conversations
    SET tenant_id = '{args.tenant_id}'
    WHERE tenant_id IS NULL;

    UPDATE aico_core.conversation_messages
    SET tenant_id = '{args.tenant_id}'
    WHERE tenant_id IS NULL;

    COMMIT;
    """

    container = "aico-postgres-shadow" if args.shadow else "aico-postgres"

    cmd = [
        "docker",
        "exec",
        "-i",
        "-e",
        f"PGPASSWORD={password}",
        container,
        "psql",
        "-h",
        "localhost",
        "-U",
        user,
        "-d",
        db_name,
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql,
    ]

    # Explicitly log target (but never print password)
    print(f"Target DB: {user}@{host}:{port}/{db_name} (container: {container})")
    print(f"Seeding tenant_id: {args.tenant_id}")
    print(f"Tenant display_name: {args.display_name}")
    print(f"Owner user_id: {args.owner_user_id}")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(result.stderr)
        return result.returncode

    if result.stdout.strip():
        print(result.stdout)

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
