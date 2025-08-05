import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys

def version_callback(ctx: typer.Context):
    """Show help when no subcommand is given instead of showing an error."""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

app = typer.Typer(
    help="Manage and synchronize versions across all AICO system parts.",
    callback=version_callback,
    invoke_without_command=True
)

console = Console()

def get_versions_path():
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle: use sys.executable as base
        exe_path = Path(sys.executable).resolve()
        return (exe_path.parent.parent.parent / "VERSIONS").resolve()
    else:
        # Running from source: use this file's location
        return (Path(__file__).parent.parent.parent / "VERSIONS").resolve()

VERSIONS_PATH = get_versions_path()
PARTS = ["cli", "backend", "frontend", "studio"]


def read_versions():
    """Read the VERSIONS file and return a dict of part -> version."""
    versions = {}
    if not VERSIONS_PATH.exists():
        console.print(f"[red]VERSIONS file not found at {VERSIONS_PATH}")
        raise typer.Exit(1)
    with open(VERSIONS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                part, version = line.split(":", 1)
                versions[part.strip()] = version.strip()
    return versions

@app.command(
    help="""
Show the version for a system part, or all parts if no part is specified.

Examples:
  aico version show
  aico version show cli
  aico version show all
  aico version show backend
"""
)
def show(
    part: str = typer.Argument(
        None,
        help="Which part to show (cli/backend/frontend/studio/all). If omitted, shows all parts.",
        show_default=False
    )
):
    """
Show the version for a system part, or all parts if no part is specified.

- If [PART] is omitted or 'all', shows all parts' versions.
- Otherwise, shows the version for the specified part.
"""
    versions = read_versions()
    if part is None or part == "all":
        table = Table(title="AICO System Versions")
        table.add_column("Subsystem")
        table.add_column("Version")
        for p in PARTS:
            v = versions.get(p, "[red]not found")
            table.add_row(p, v)
        console.print(table)
    else:
        v = versions.get(part)
        if v:
            console.print(f"[bold]{part}[/bold]: [green]{v}")
        else:
            console.print(f"[red]No version found for part '{part}'")
            raise typer.Exit(1)

# TODO: Implement sync, bump, check, history, next commands
