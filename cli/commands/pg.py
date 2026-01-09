"""AICO CLI Postgres Commands

Command group for managing the Postgres/Timescale backend that will replace LibSQL.

This module is intentionally minimal for now and will be extended as the
Postgres migration is implemented. It follows the same patterns as the
existing `database` command group (aico db ...).
"""

import sys
import socket
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich import box

# Add shared module to path for CLI usage (mirrors database.py pattern)
if getattr(sys, "frozen", False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / "shared"
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths

from cli.utils.help_formatter import format_subcommand_help
from cli.utils.formatting import (
    format_error,
    format_success,
    format_warning,
    format_info,
)

console = Console()


def pg_callback(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit"),
):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        subcommands = [
            ("status", "Show Postgres backend configuration and basic reachability"),
            ("doctor", "Run detailed environment checks for Postgres"),
        ]

        examples = [
            "aico pg status",
            "aico pg doctor",
        ]

        format_subcommand_help(
            console=console,
            command_name="pg",
            description="Postgres/Timescale backend management (scaffold)",
            subcommands=subcommands,
            examples=examples,
        )
        raise typer.Exit()


app = typer.Typer(
    help="Postgres backend management (experimental)",
    callback=pg_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []},
)


@app.command(help="Show Postgres backend status and basic reachability")
def status():
    """Show configuration and perform a lightweight reachability check."""


    config = ConfigurationManager()
    # Lightweight init is enough to read config defaults
    config.initialize(lightweight=True)
    # ConfigurationManager prepends "core." to keys, so we must include it
    pg_cfg = config.get("core.database.postgres", {}) or {}

    table = Table(
        title="✨ [bold cyan]Postgres Backend Status[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("Property", style="cyan", justify="left")
    table.add_column("Value", style="green", justify="left")

    if not pg_cfg:
        table.add_row(
            "Configuration",
            "[red]No core.database.postgres configuration found in core.yaml[/red]",
        )
    else:
        # Basic connection info
        host = pg_cfg.get("host", "127.0.0.1")
        port = pg_cfg.get("port", 5432)
        db_name = pg_cfg.get("db_name", "aico")
        user = pg_cfg.get("user", "aico")
        sslmode = pg_cfg.get("sslmode", "prefer")
        core_schema = pg_cfg.get("core_schema", "aico_core")

        table.add_row("Host", str(host))
        table.add_row("Port", str(port))
        table.add_row("Database", str(db_name))
        table.add_row("User", str(user))
        table.add_row("SSL Mode", str(sslmode))
        table.add_row("Core Schema", str(core_schema))

        # Show an example DSN without password
        dsn = f"postgresql://{user}:***@{host}:{port}/{db_name}?sslmode={sslmode}"
        table.add_row("Example DSN", dsn)

        # Lightweight reachability (TCP only)
        try:
            with socket.create_connection((host, int(port)), timeout=2.0):
                reachable = "[green]reachable (TCP connect OK)[/green]"
        except OSError as exc:  # pragma: no cover - best-effort diagnostic
            reachable = f"[red]unreachable ({exc.__class__.__name__}: {exc})[/red]"

        table.add_row("Network Reachability", reachable)

    console.print(table)


@app.command(help="Run detailed environment checks for Postgres/Timescale")
def doctor():
    """Run a series of checks to validate the Postgres environment.

    This command assumes Postgres is installed by the OS (or via Docker) and
    focuses on verifying that AICO can talk to it and that basic tools are
    available:

    - core.database.postgres configuration presence.
    - TCP connectivity to host:port.
    """

    console.rule("[bold cyan]Postgres / Timescale Doctor[/bold cyan]")

    config = ConfigurationManager()
    config.initialize(lightweight=True)
    pg_cfg = config.get("core.database.postgres", {}) or {}

    if not pg_cfg:
        console.print(
            format_error(
                "No core.database.postgres configuration found in core.yaml. "
                "Please configure host/port/db_name/user before running 'aico pg doctor'."
            )
        )
        raise typer.Exit(code=1)

    host = pg_cfg.get("host", "127.0.0.1")
    port = int(pg_cfg.get("port", 5432))
    db_name = pg_cfg.get("db_name", "aico")
    user = pg_cfg.get("user", "aico")
    sslmode = pg_cfg.get("sslmode", "prefer")

    table = Table(
        title="✨ [bold cyan]Environment Checks[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("Check", style="cyan", justify="left")
    table.add_column("Result", style="green", justify="left")
    table.add_column("Details", style="white", justify="left")

    # 1) Config present
    table.add_row(
        "Configuration",
        "[green]OK[/green]",
        f"host={host}, port={port}, db={db_name}, user={user}, sslmode={sslmode}",
    )

    # 2) TCP connectivity
    try:
        with socket.create_connection((host, port), timeout=3.0):
            table.add_row(
                "TCP connectivity",
                "[green]OK[/green]",
                f"Successfully connected to {host}:{port}",
            )
            tcp_ok = True
    except OSError as exc:  # pragma: no cover - best-effort diagnostic
        table.add_row(
            "TCP connectivity",
            "[red]FAILED[/red]",
            f"Could not connect to {host}:{port} ({exc.__class__.__name__}: {exc})",
        )
        tcp_ok = False

    console.print(table)

    console.print(
        "\n[blue]Next steps:[/blue] If TCP connectivity or psql checks failed, "
        "ensure your Postgres server is running, listening on the configured "
        "host/port, and that client tools are installed. Once these checks "
        "pass, run 'aico pg init' to finalize the AICO database schema."
    )
