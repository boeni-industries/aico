"""One-off live DB migration: backfill tenant_id where NULL.

This script is intentionally NOT part of the CLI to avoid accidental use.

Safety properties:
- Default mode is DRY RUN (no writes)
- Apply mode updates only rows where tenant_id IS NULL
- No DROP/TRUNCATE/DELETE

Example:
  uv run python scripts/backfill_tenant_id_live_db.py \
    --tenant-id 03e34c91-7605-4984-950f-5deb1a947a36 \
    --dry-run

Apply:
  uv run python scripts/backfill_tenant_id_live_db.py \
    --tenant-id 03e34c91-7605-4984-950f-5deb1a947a36 \
    --apply
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path


DEFAULT_TABLES: list[str] = [
    "aico_core.conversations",
    "aico_core.conversation_messages",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="One-off: backfill tenant_id where NULL")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID to backfill")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (default): only print counts and planned updates",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply updates (writes): UPDATE ... WHERE tenant_id IS NULL",
    )

    parser.add_argument(
        "--tables",
        nargs="+",
        default=DEFAULT_TABLES,
        help="Fully qualified tables to include (default: conversations, conversation_messages)",
    )

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    tenant_id = args.tenant_id

    # Default to dry-run unless --apply is explicitly set
    dry_run = True
    if args.apply:
        dry_run = False

    # Validate UUID
    uuid.UUID(tenant_id)

    # Add shared module to path (mirrors other scripts)
    if getattr(sys, "frozen", False):
        shared_path = Path(sys._MEIPASS) / "shared"  # type: ignore[attr-defined]
    else:
        shared_path = Path(__file__).parent.parent / "shared"
    sys.path.insert(0, str(shared_path))

    from cli.utils.pg_connection import get_pg_connection

    conn = get_pg_connection()

    def _table_exists(table_fq: str) -> bool:
        schema, table = table_fq.split(".", 1)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema=%s AND table_name=%s
                """,
                (schema, table),
            )
            return cur.fetchone() is not None

    def _count_nulls(table_fq: str) -> int:
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) AS cnt FROM {table_fq} WHERE tenant_id IS NULL")
            row = cur.fetchone()
            return int(row["cnt"]) if row else 0

    def _count_total(table_fq: str) -> int:
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) AS cnt FROM {table_fq}")
            row = cur.fetchone()
            return int(row["cnt"]) if row else 0

    try:
        print(f"tenant_id: {tenant_id}")
        print(f"mode: {'DRY RUN' if dry_run else 'APPLY'}")
        print("")

        planned: list[tuple[str, int, int]] = []
        for table_fq in args.tables:
            if not _table_exists(table_fq):
                raise RuntimeError(f"Table does not exist: {table_fq}")
            total = _count_total(table_fq)
            nulls = _count_nulls(table_fq)
            planned.append((table_fq, total, nulls))

        print("Planned tables:")
        for table_fq, total, nulls in planned:
            print(f"- {table_fq}: total={total}, tenant_id IS NULL={nulls}")

        if dry_run:
            print("\nDRY RUN: no changes applied.")
            return 0

        # Apply updates inside a single transaction.
        with conn.cursor() as cur:
            cur.execute("BEGIN;")
            for table_fq, _, nulls in planned:
                if nulls == 0:
                    continue
                cur.execute(
                    f"UPDATE {table_fq} SET tenant_id=%s WHERE tenant_id IS NULL",
                    (tenant_id,),
                )
                print(f"Updated {table_fq}: {cur.rowcount} rows")
            cur.execute("COMMIT;")

        print("OK")
        return 0

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
