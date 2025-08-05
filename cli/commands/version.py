import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys

app = typer.Typer(help="Manage and synchronize versions across all AICO system parts.")
console = Console()

VERSIONS_PATH = Path(__file__).parent.parent.parent / "VERSIONS"
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

@app.command()
def show(part: str = typer.Argument(None, help="Which part to show (cli/backend/frontend/studio/all)", show_default=False)):
    """Print the current version of a part or all parts."""
    versions = read_versions()
    if part is None or part == "all":
        table = Table(title="AICO System Versions")
        table.add_column("Part")
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
