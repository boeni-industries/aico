import sys
from pathlib import Path
from typing import Optional

import json
import typer
from rich.console import Console
from rich.table import Table
from rich import box

# Import decorators
decorators_path = Path(__file__).parent.parent / "decorators"
sys.path.insert(0, str(decorators_path))
from cli.decorators.sensitive import sensitive

# Add shared path for imports
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.logging import get_logger
from cli.utils.api_client import get_backend_client

console = Console()
logger = get_logger("cli.tools")


def _backend_post(path: str, payload: dict | None = None) -> dict:
    """Helper to POST to backend agency API and return JSON."""

    from httpx import HTTPError

    with get_backend_client() as client:
        try:
            return client.post(path, json=payload or {})  # type: ignore[arg-type]
        except HTTPError as exc:  # pragma: no cover - network
            console.print(f"[red]Backend API error: {exc}[/red]")
            raise typer.Exit(1)


def tools_callback(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit"),
) -> None:
    """Show help when no subcommand is given or --help is used."""

    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help

        subcommands = [
            ("ls", "List registered tools"),
            ("show", "Show detailed tool information"),
            ("run", "Run a tool and display its result"),
        ]

        examples = [
            "aico tools ls",
            "aico tools show tool.db.postgres.ping",
            "aico tools run tool.db.postgres.ping --format json",
        ]

        format_subcommand_help(
            console=console,
            command_name="tools",
            description="Agency tool inspection and live execution",
            subcommands=subcommands,
            examples=examples,
        )
        raise typer.Exit()


app = typer.Typer(
    help="Inspection and live execution of Agency tools (ToolRegistry-backed)",
    callback=tools_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []},
)


@app.command("ls")
@sensitive
def list_tools(
    format_output: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
):
    """List all registered Agency tools from the ToolRegistry."""
    response = _backend_post("/api/v1/agency/tools/list", payload={})
    tools = response or []

    if not tools:
        console.print("[yellow]No tools registered[/yellow]")
        raise typer.Exit(0)

    if format_output == "json":
        data = []
        console.print(json.dumps(tools, indent=2))
        return

    table = Table(
        title="✨ Registered Agency Tools",
        box=box.SIMPLE_HEAD,
        title_justify="left",
        header_style="bold yellow",
    )
    table.add_column("Tool ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Domain", style="magenta")
    table.add_column("Backend", style="blue")
    table.add_column("Capabilities", style="bright_blue")
    table.add_column("Params", style="dim")

    for t in tools:
        params = t.get("parameters") or []
        param_summary = (
            "none" if not params else ", ".join(p["name"] for p in params)
        )
        table.add_row(
            t.get("tool_id", ""),
            t.get("name", ""),
            t.get("domain", ""),
            t.get("backend", ""),
            ", ".join(t.get("capability_tags") or []) or "-",
            param_summary,
        )

    console.print()
    console.print(table)
    console.print()


@app.command("show")
@sensitive
def show_tool(
    tool_id: str = typer.Argument(..., help="Tool ID to show"),
    format_output: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
):
    """Show detailed information for a specific tool."""
    tool = _backend_post(
        "/api/v1/agency/tools/info",
        payload={"tool_id": tool_id},
    ) or {}

    if format_output == "json":
        console.print(json.dumps(tool, indent=2))
        return

    table = Table(
        title=f"✨ [bold cyan]Tool Details: {tool.tool_id}[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Tool ID", tool.get("tool_id", tool_id))
    table.add_row("Name", tool.get("name", ""))
    table.add_row("Description", tool.get("description", ""))
    table.add_row("Domain", tool.get("domain", ""))
    table.add_row("Backend", tool.get("backend", ""))
    table.add_row("Runtime Context", tool.get("runtime_context", ""))
    table.add_row("Capabilities", ", ".join(tool.get("capability_tags") or []) or "-")
    table.add_row("Side Effects", ", ".join(tool.get("side_effect_tags") or []) or "-")
    table.add_row("Safety Level", tool.get("safety_level", "low"))
    table.add_row("Resource Profile", tool.get("resource_profile", "tiny"))
    table.add_row(
        "Default Timeout (s)", str(tool.get("default_timeout_seconds", 5)),
    )

    console.print()
    console.print(table)

    params = tool.get("parameters") or []
    if params:
        param_table = Table(
            title="Parameters",
            title_justify="left",
            border_style="bright_blue",
            header_style="bold yellow",
            box=box.SIMPLE_HEAD,
            padding=(0, 1),
        )
        param_table.add_column("Name", style="cyan")
        param_table.add_column("Type", style="green")
        param_table.add_column("Required", style="magenta")
        param_table.add_column("Default", style="dim")
        param_table.add_column("Description", style="bright_blue")

        for p in params:
            param_table.add_row(
                p["name"],
                p["type"],
                "yes" if p.get("required", True) else "no",
                json.dumps(p.get("default")) if p.get("default") is not None else "-",
                p.get("description", ""),
            )

        console.print()
        console.print(param_table)

    console.print()


@app.command("run")
@sensitive
def run_tool(
    tool_id: str = typer.Argument(..., help="Tool ID to run"),
    input_json: Optional[str] = typer.Option(
        None,
        "--input",
        "-i",
        help="JSON object with tool input parameters (mapped to handler kwargs)",
    ),
    format_output: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
):
    """Run a tool from ToolRegistry and print its result."""

    kwargs = {}
    if input_json:
        try:
            kwargs = json.loads(input_json)
            if not isinstance(kwargs, dict):
                raise ValueError("Input JSON must be an object mapping parameter names to values")
        except Exception as exc:  # pragma: no cover - CLI validation
            console.print(f"[red]Invalid JSON for --input: {exc}[/red]")
            raise typer.Exit(1)

    result = _backend_post(
        "/api/v1/agency/tools/invoke",
        payload={
            "tool_id": tool_id,
            "input": kwargs,
        },
    )

    if format_output == "json":
        console.print(json.dumps(result, indent=2))
        return

    # Table view: show ok/data/error sections
    ok = result.get("ok")
    data = result.get("data") or {}
    error = result.get("error")

    table = Table(
        title=f"✨ [bold cyan]Tool Result: {tool_id}[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("ok", json.dumps(ok))
    table.add_row("status", str(data.get("status")))
    table.add_row("latency_ms", json.dumps(data.get("latency_ms")))
    table.add_row("error_message", data.get("error_message") or "-")

    console.print()
    console.print(table)

    if data.get("details"):
        console.print("\n[bold cyan]Details:[/bold cyan]")
        console.print(json.dumps(data["details"], indent=2))

    if error:
        console.print("\n[bold red]Error object:[/bold red]")
        console.print(json.dumps(error, indent=2))

    console.print()
