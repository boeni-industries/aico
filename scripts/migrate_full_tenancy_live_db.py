"""One-off live DB migration: enforce tenant_id across all aico_core tables.

Goal:
- Add tenant_id to every table in aico_core where it is missing
- Backfill existing rows with a single deployment tenant_id
- Enforce NOT NULL
- Add an index on tenant_id for tenant-scoped filtering

Safety properties:
- No DELETE/TRUNCATE/DROP
- Default mode is dry-run (no writes)

Notes:
- This is a schema+data migration. It will take locks while ALTER TABLE runs.
- Designed for a single-tenant deployment migration.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlanItem:
    table_fq: str
    row_count: int
    has_tenant_id: bool
    null_tenant_id_count: int | None


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="One-off: add/backfill/enforce tenant_id across aico_core")
    p.add_argument("--tenant-id", required=True, help="Deployment tenant UUID to set")
    p.add_argument(
        "--set-default",
        action="store_true",
        help="Also set tenant_id DEFAULT to the provided tenant_id for all processed tables.",
    )

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Dry run (default): print plan only")
    mode.add_argument("--apply", action="store_true", help="Apply changes (schema + data)")

    p.add_argument(
        "--include",
        nargs="*",
        default=None,
        help="Optional allowlist of tables (unqualified names) to include. If omitted, processes all aico_core tables.",
    )
    p.add_argument(
        "--exclude",
        nargs="*",
        default=[
            "tenants",
            "tenant_memberships",
            "user_profiles",
            "auth_user_credentials",
            "auth_devices",
        ],
        help="Optional blocklist of tables (unqualified names) to exclude.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    # Default is dry-run unless --apply is explicitly set
    dry_run = not args.apply

    # Validate UUID
    uuid.UUID(args.tenant_id)

    # Add shared module to path (mirrors other scripts)
    if getattr(sys, "frozen", False):
        shared_path = Path(sys._MEIPASS) / "shared"  # type: ignore[attr-defined]
    else:
        shared_path = Path(__file__).parent.parent / "shared"
    sys.path.insert(0, str(shared_path))

    from cli.utils.pg_connection import get_pg_connection

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='aico_core' AND table_type='BASE TABLE'
                ORDER BY table_name;
                """
            )
            tables = [r["table_name"] for r in cur.fetchall()]

        include = set(args.include or []) if args.include else None
        exclude = set(args.exclude or [])

        selected: list[str] = []
        for t in tables:
            if include is not None and t not in include:
                continue
            if t in exclude:
                continue
            selected.append(t)

        plan: list[PlanItem] = []
        for t in selected:
            table_fq = f"aico_core.{t}"
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema='aico_core' AND table_name=%s AND column_name='tenant_id';
                    """,
                    (t,),
                )
                has_tenant_id = cur.fetchone() is not None

                cur.execute(f"SELECT count(*) AS cnt FROM {table_fq};")
                row_count = int(cur.fetchone()["cnt"])

                null_tenant_id_count: int | None = None
                if has_tenant_id:
                    cur.execute(f"SELECT count(*) AS cnt FROM {table_fq} WHERE tenant_id IS NULL;")
                    null_tenant_id_count = int(cur.fetchone()["cnt"])

            plan.append(
                PlanItem(
                    table_fq=table_fq,
                    row_count=row_count,
                    has_tenant_id=has_tenant_id,
                    null_tenant_id_count=null_tenant_id_count,
                )
            )

        print(f"tenant_id: {args.tenant_id}")
        print(f"mode: {'DRY RUN' if dry_run else 'APPLY'}")
        print(f"tables scanned: {len(plan)}")
        print("")

        missing = [p for p in plan if not p.has_tenant_id]
        already = [p for p in plan if p.has_tenant_id]

        print(f"Tables missing tenant_id: {len(missing)}")
        for pitem in missing:
            print(f"- {pitem.table_fq} (rows={pitem.row_count})")

        print("")
        print(f"Tables already having tenant_id: {len(already)}")
        null_existing = [p for p in already if (p.null_tenant_id_count or 0) > 0]
        if null_existing:
            print("\nTables with existing tenant_id but NULL values:")
            for pitem in null_existing:
                print(f"- {pitem.table_fq} (null_tenant_id_rows={pitem.null_tenant_id_count}, total_rows={pitem.row_count})")

        if dry_run:
            print("\nDRY RUN: no changes applied.")
            return 0

        # Apply in one transaction. This can be long-running.
        with conn.cursor() as cur:
            cur.execute("BEGIN;")

            for pitem in plan:
                tbl = pitem.table_fq
                short = tbl.split(".", 1)[1]

                # 1) Add tenant_id (nullable) if missing.
                if not pitem.has_tenant_id:
                    cur.execute(
                        f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS tenant_id TEXT;"
                    )

                # 2) Backfill any NULL tenant_id rows.
                cur.execute(
                    f"UPDATE {tbl} SET tenant_id = %s WHERE tenant_id IS NULL;",
                    (args.tenant_id,),
                )

                # 3) Enforce NOT NULL.
                cur.execute(
                    f"ALTER TABLE {tbl} ALTER COLUMN tenant_id SET NOT NULL;"
                )

                # 3b) Optionally set DEFAULT for legacy code paths that don't pass tenant_id.
                if args.set_default:
                    cur.execute(
                        f"ALTER TABLE {tbl} ALTER COLUMN tenant_id SET DEFAULT %s;",
                        (args.tenant_id,),
                    )

                # 4) Index for tenant-scoped queries.
                idx_name = f"idx_{short}_tenant_id"
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl} (tenant_id);"
                )

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
