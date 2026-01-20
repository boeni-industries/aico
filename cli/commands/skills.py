import sys
from pathlib import Path
from typing import Optional

import json
import asyncio
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
logger = get_logger("cli.skills")


def skills_callback(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit"),
) -> None:
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help

        subcommands = [
            ("ls", "List registered skills"),
            ("show", "Show detailed skill information"),
            ("run", "Run a skill and display its result"),
        ]

        examples = [
            "aico skills ls",
            "aico skills show maint.connectivity.full_scan",
            "aico skills run maint.connectivity.full_scan --format json",
        ]

        format_subcommand_help(
            console=console,
            command_name="skills",
            description="Agency skills inspection and live execution",
            subcommands=subcommands,
            examples=examples,
        )
        raise typer.Exit()


app = typer.Typer(
    help="Inspection and live execution of Agency skills (SkillRegistry-backed)",
    callback=skills_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []},
)


def _backend_post(path: str, payload: dict | None = None) -> dict:
    """Helper to POST to backend health API and return JSON.

    Uses the encrypted CLIBackendClient so this works in all environments
    where the backend API Gateway is running.
    """

    from httpx import HTTPError

    with get_backend_client() as client:
        try:
            return client.post(path, json=payload or {})  # type: ignore[arg-type]
        except HTTPError as exc:  # pragma: no cover - network
            console.print(f"[red]Backend API error: {exc}[/red]")
            raise typer.Exit(1)


@app.command("ls")
@sensitive
def list_skills(
    format_output: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
):
    """List all registered Agency skills."""
    response = _backend_post("/api/v1/agency/skills/list", payload={})
    # response is expected to be a list of SkillInfoResponse dicts
    skills = response or []

    if not skills:
        console.print("[yellow]No skills registered in SkillRegistry[/yellow]")
        raise typer.Exit(0)

    if format_output == "json":
        console.print(json.dumps(skills, indent=2))
        return

    table = Table(
        title="✨ Registered Agency Skills",
        box=box.SIMPLE_HEAD,
        title_justify="left",
        header_style="bold yellow",
    )
    table.add_column("Skill ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Category", style="magenta")
    table.add_column("Capabilities", style="bright_blue")
    table.add_column("Params", style="dim")

    for info in skills:
        params = info.get("parameters") or []
        param_summary = (
            "none" if not params else ", ".join(p["name"] for p in params)
        )
        table.add_row(
            info.get("skill_id", ""),
            info.get("name", ""),
            info.get("category", ""),
            ", ".join(info.get("capability_tags") or []) or "-",
            param_summary,
        )

    console.print()
    console.print(table)
    console.print()


@app.command("show")
@sensitive
def show_skill(
    skill_id: str = typer.Argument(..., help="Skill ID to show"),
    format_output: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
):
    """Show detailed information for a specific skill."""
    info = _backend_post(
        "/api/v1/agency/skills/info",
        payload={"skill_id": skill_id},
    ) or {}

    if format_output == "json":
        console.print(json.dumps(info, indent=2))
        return

    table = Table(
        title=f"✨ [bold cyan]Skill Details: {skill_id}[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Skill ID", info.get("skill_id", skill_id))
    table.add_row("Name", info.get("name", ""))
    table.add_row("Description", info.get("description", ""))
    table.add_row("Category", info.get("category", ""))
    table.add_row(
        "Timeout (s)", str(info.get("timeout_seconds", 30)),
    )
    table.add_row(
        "Capabilities", ", ".join(info.get("capability_tags") or []) or "-",
    )
    table.add_row(
        "Side Effects", ", ".join(info.get("side_effect_tags") or []) or "-",
    )
    table.add_row("Safety Level", info.get("safety_level", "low"))
    impl_tools = info.get("implementation_tools") or []
    table.add_row(
        "Implementation Tools", ", ".join(impl_tools) or "-",
    )

    console.print()
    console.print(table)

    params = info.get("parameters") or []
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
def run_skill(
    skill_id: str = typer.Argument(..., help="Skill ID to run"),
    user_id: str = typer.Option(
        "system_user",
        "--user-id",
        "-u",
        help="User ID to attribute the skill execution to",
    ),
    input_json: Optional[str] = typer.Option(
        None,
        "--input",
        "-i",
        help="JSON object with skill input parameters",
    ),
    format_output: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
):
    """Run a skill via AgencyEngine's SkillInvoker and print its result."""

    input_data = {}
    if input_json:
        try:
            input_data = json.loads(input_json)
            if not isinstance(input_data, dict):
                raise ValueError("Input JSON must be an object mapping parameter names to values")
        except Exception as exc:  # pragma: no cover - CLI validation
            console.print(f"[red]Invalid JSON for --input: {exc}[/red]")
            raise typer.Exit(1)

    # Use agency API skill invocation endpoint
    result = _backend_post(
        "/api/v1/agency/skills/invoke",
        payload={
            "skill_id": skill_id,
            "input": input_data,
            "context": {
                "trigger": "cli_skill_run",
                "initiator_type": "user",
                "source": "cli.skills",
                "user_id": user_id,
            },
        },
    )

    if format_output == "json":
        console.print(json.dumps(result, indent=2))
        return

    # health.skills.invoke currently returns the skill output directly
    output = result or {}

    table = Table(
        title=f"✨ [bold cyan]Skill Result: {skill_id}[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("success", json.dumps(success))

    # For connectivity and similar skills, try to surface summary_status if present
    if isinstance(output, dict) and "summary_status" in output:
        table.add_row("summary_status", str(output.get("summary_status")))

    table.add_row(
        "has_output", "yes" if bool(output) else "no",
    )

    console.print()
    console.print(table)

    if output:
        console.print("\n[bold cyan]Output:[/bold cyan]")
        console.print(json.dumps(output, indent=2))

    if error:
        console.print("\n[bold red]Error:[/bold red]")
        console.print(json.dumps(error, indent=2))

    console.print()
