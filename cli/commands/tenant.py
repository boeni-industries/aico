"""AICO CLI Tenant Management Commands

Tenant management is a first-class concept. Commands here are intentionally safe:
- no delete
- create generates a random UUID
- deactivate flips status

These commands require Postgres to be configured and reachable.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich import box

# Add shared module to path for CLI usage (mirrors database.py/pg.py pattern)
if getattr(sys, "frozen", False):
    shared_path = Path(sys._MEIPASS) / "shared"  # type: ignore[attr-defined]
else:
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from cli.utils.help_formatter import format_subcommand_help
from cli.utils.formatting import format_error, format_success, format_warning
from cli.utils.pg_connection import get_pg_connection

console = Console()


def tenant_callback(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit"),
):
    if ctx.invoked_subcommand is None or help:
        subcommands = [
            ("ls", "List tenants"),
            ("create", "Create tenant (random UUID)"),
            ("show", "Show tenant details"),
            ("member-add", "Add membership (tenant_id + user_id)"),
            ("deactivate", "Deactivate tenant (status=inactive)"),
        ]
        examples = [
            'aico tenant ls',
            'aico tenant create --display-name "Boeni Industries Ltd"',
            'aico tenant show --tenant-id <uuid>',
            'aico tenant member-add --tenant-id <uuid> --user-id <uuid> --role owner',
            'aico tenant deactivate --tenant-id <uuid>',
        ]

        format_subcommand_help(
            console=console,
            command_name="tenant",
            description="Tenant management (safe CRUD/list)",
            subcommands=subcommands,
            examples=examples,
        )
        raise typer.Exit()


app = typer.Typer(
    help="Tenant management",
    callback=tenant_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []},
)


def _require_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='aico_core'
              AND table_name IN ('tenants','tenant_memberships');
            """
        )
        rows = cur.fetchall()
        present = {r["table_name"] for r in rows}
    missing = {"tenants", "tenant_memberships"} - present
    if missing:
        raise RuntimeError(
            "Missing required tables in schema aico_core: "
            + ", ".join(sorted(missing))
            + ". Apply schema.sql to the database first."
        )


@app.command(help="List tenants")
def ls(limit: int = typer.Option(50, "--limit", help="Max rows")):
    try:
        conn = get_pg_connection()
    except Exception as e:
        console.print(format_error(str(e)))
        raise typer.Exit(1)

    try:
        _require_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tenant_id, display_name, tenant_type, status, created_at, updated_at
                FROM aico_core.tenants
                ORDER BY updated_at DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()

        if not rows:
            console.print(format_warning("No tenants found"))
            return

        table = Table(
            title="Tenants",
            border_style="bright_blue",
            header_style="bold yellow",
            box=box.SIMPLE_HEAD,
        )
        table.add_column("tenant_id", style="cyan")
        table.add_column("display_name")
        table.add_column("tenant_type")
        table.add_column("status")
        table.add_column("updated_at", style="dim")

        for r in rows:
            table.add_row(
                str(r["tenant_id"]),
                str(r["display_name"]),
                str(r["tenant_type"]),
                str(r["status"]),
                str(r.get("updated_at") or ""),
            )

        console.print(table)
    except Exception as e:
        console.print(format_error(str(e)))
        raise typer.Exit(1)
    finally:
        conn.close()


@app.command(help="Create tenant (random UUID)")
def create(
    display_name: str = typer.Option(..., "--display-name", help="Tenant display name"),
    tenant_type: str = typer.Option("deployment", "--tenant-type", help="Tenant type"),
    primary_language: str = typer.Option(None, "--primary-language", help="Optional primary language"),
):
    tenant_id = str(uuid.uuid4())

    try:
        conn = get_pg_connection()
    except Exception as e:
        console.print(format_error(str(e)))
        raise typer.Exit(1)

    try:
        _require_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO aico_core.tenants (
                    tenant_id, tenant_type, display_name, status, primary_language, metadata_json, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, 'active', %s, NULL, NOW(), NOW()
                );
                """,
                (tenant_id, tenant_type, display_name, primary_language),
            )
        conn.commit()
        console.print(format_success(f"Created tenant {tenant_id}"))
    except Exception as e:
        conn.rollback()
        console.print(format_error(str(e)))
        raise typer.Exit(1)
    finally:
        conn.close()


@app.command(help="Show tenant details")
def show(tenant_id: str = typer.Option(..., "--tenant-id", help="Tenant UUID")):
    try:
        uuid.UUID(tenant_id)
    except Exception:
        console.print(format_error("Invalid tenant_id UUID"))
        raise typer.Exit(1)

    try:
        conn = get_pg_connection()
    except Exception as e:
        console.print(format_error(str(e)))
        raise typer.Exit(1)

    try:
        _require_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tenant_id, display_name, tenant_type, status, primary_language, created_at, updated_at
                FROM aico_core.tenants
                WHERE tenant_id = %s;
                """,
                (tenant_id,),
            )
            tenant = cur.fetchone()

            if not tenant:
                console.print(format_warning("Tenant not found"))
                return

            cur.execute(
                """
                SELECT user_id, role, created_at
                FROM aico_core.tenant_memberships
                WHERE tenant_id = %s
                ORDER BY created_at ASC;
                """,
                (tenant_id,),
            )
            members = cur.fetchall()

        console.rule("Tenant")
        console.print(f"tenant_id: {tenant['tenant_id']}")
        console.print(f"display_name: {tenant['display_name']}")
        console.print(f"tenant_type: {tenant['tenant_type']}")
        console.print(f"status: {tenant['status']}")
        console.print(f"primary_language: {tenant.get('primary_language')}")
        console.print(f"created_at: {tenant.get('created_at')}")
        console.print(f"updated_at: {tenant.get('updated_at')}")

        if members:
            table = Table(
                title="Memberships",
                border_style="bright_blue",
                header_style="bold yellow",
                box=box.SIMPLE_HEAD,
            )
            table.add_column("user_id", style="cyan")
            table.add_column("role")
            table.add_column("created_at", style="dim")
            for m in members:
                table.add_row(str(m["user_id"]), str(m["role"]), str(m.get("created_at") or ""))
            console.print(table)
    except Exception as e:
        console.print(format_error(str(e)))
        raise typer.Exit(1)
    finally:
        conn.close()


@app.command(help="Add membership (tenant_id + user_id)")
def member_add(
    tenant_id: str = typer.Option(..., "--tenant-id", help="Tenant UUID"),
    user_id: str = typer.Option(..., "--user-id", help="User UUID"),
    role: str = typer.Option("member", "--role", help="Role (e.g. owner, admin, member)"),
):
    try:
        uuid.UUID(tenant_id)
        uuid.UUID(user_id)
    except Exception:
        console.print(format_error("Invalid UUID for tenant_id or user_id"))
        raise typer.Exit(1)

    membership_id = str(uuid.uuid4())

    try:
        conn = get_pg_connection()
    except Exception as e:
        console.print(format_error(str(e)))
        raise typer.Exit(1)

    try:
        _require_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO aico_core.tenant_memberships (
                    membership_id, tenant_id, user_id, role, created_at
                ) VALUES (
                    %s, %s, %s, %s, NOW()
                ) ON CONFLICT (tenant_id, user_id) DO UPDATE SET role = EXCLUDED.role;
                """,
                (membership_id, tenant_id, user_id, role),
            )
        conn.commit()
        console.print(format_success("Membership upserted"))
    except Exception as e:
        conn.rollback()
        console.print(format_error(str(e)))
        raise typer.Exit(1)
    finally:
        conn.close()


@app.command(help="Deactivate tenant (status=inactive)")
def deactivate(tenant_id: str = typer.Option(..., "--tenant-id", help="Tenant UUID")):
    try:
        uuid.UUID(tenant_id)
    except Exception:
        console.print(format_error("Invalid tenant_id UUID"))
        raise typer.Exit(1)

    try:
        conn = get_pg_connection()
    except Exception as e:
        console.print(format_error(str(e)))
        raise typer.Exit(1)

    try:
        _require_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE aico_core.tenants
                SET status='inactive', updated_at=NOW()
                WHERE tenant_id=%s;
                """,
                (tenant_id,),
            )
            if cur.rowcount == 0:
                console.print(format_warning("Tenant not found"))
                conn.rollback()
                return
        conn.commit()
        console.print(format_success("Tenant deactivated"))
    except Exception as e:
        conn.rollback()
        console.print(format_error(str(e)))
        raise typer.Exit(1)
    finally:
        conn.close()
